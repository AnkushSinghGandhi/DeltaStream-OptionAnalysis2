## Part 3: Building the Worker Enricher Service

### Learning Objectives

By the end of Part 3, you will understand:

1. **Celery task queues** - How distributed task processing works
2. **Idempotency** - Why processing the same message twice must be safe
3. **Retry logic** - Exponential backoff and dead-letter queues
4. **MongoDB persistence** - Time-series data storage and indexing
5. **Cache-aside pattern** - Redis caching with TTL and invalidation
6. **Pub/sub subscription** - Consuming messages from Redis channels
7. **Production patterns** - Singleton clients, lazy initialization, error handling

---

### 3.1 Understanding Celery: Why Task Queues?

Before diving into code, let's understand **why we need Celery** and **how task queues work**.

#### The Problem: Slow Synchronous Processing

Imagine our Worker without Celery:

```python
def subscribe_to_feeds():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('market:option_chain')
    
    for message in pubsub.listen():
        data = json.loads(message['data'])
        process_option_chain(data)  # Blocks for 50ms
```

**What happens?**

1. Message 1 arrives → Processing starts (50ms)
2. Message 2 arrives (during processing) → **Queued in memory**
3. Message 3 arrives → **Queued**
4. Message 4 arrives → **Queued**
5. Message 1 finishes → Message 2 starts

**Problems:**
- **Single-threaded**: Can't utilize multi-core CPU
- **No parallelism**: Processes one message at a time
- **Memory issues**: Queue grows unbounded if messages arrive faster than processing
- **No retry logic**: If processing fails, message is lost
- **No monitoring**: Can't track which tasks are running/failed

#### The Solution: Celery Task Queue

```python
def subscribe_to_feeds():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('market:option_chain')
    
    for message in pubsub.listen():
        data = json.loads(message['data'])
        process_option_chain.delay(data)  # Non-blocking!
```

**What `.delay()` does:**

1. Serializes `data` to JSON
2. Sends task to Redis queue (database 1)
3. Returns immediately (1ms)
4. Subscriber continues listening

Separately, **Celery workers** (running in parallel):

```
Worker 1: Polls queue → Gets task → Processes → Marks complete
Worker 2: Polls queue → Gets task → Processes → Marks complete
Worker 3: Polls queue → Gets task → Processes → Marks complete
```

**Benefits:**
- **Parallel processing**: 3 workers = 3x throughput
- **Decoupled**: Subscriber doesn't wait for processing
- **Persistent queue**: Tasks survive worker restarts (stored in Redis)
- **Auto-retry**: Celery retries failed tasks automatically
- **Monitoring**: Built-in task state tracking

---

#### How Celery Works: Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Publisher   │────────▶│ Redis Broker │◀────────│ Worker 1     │
│ (Subscriber) │  send   │ (Queue)      │  poll   │ (Consumer)   │
└──────────────┘  task   └──────────────┘  tasks  └──────────────┘
                                                   
                                                   ┌──────────────┐
                                     poll tasks    │ Worker 2     │
                                         ◀─────────│ (Consumer)   │
                                                   └──────────────┘
                                                    
                         ┌──────────────┐          ┌──────────────┐
                         │ Redis Result │          │ Worker 3     │
                         │  Backend     │◀─────────│ (Consumer)   │
                         └──────────────┘  store   └──────────────┘
                                           results
```

**Components:**

1. **Broker** (Redis database 1):
   - Stores task queue
   - FIFO (First In First Out) by default
   - Workers pull tasks from here

2. **Result Backend** (Redis database 2):
   - Stores task results (return values)
   - Stores task state (PENDING, STARTED, SUCCESS, FAILURE)
   - Optional (we use it for monitoring)

3. **Worker**:
   - Process that polls broker for tasks
   - Executes task function
   - Stores result in backend
   - Can run multiple workers on different machines

4. **Publisher**:
   - Code that calls `.delay()` or `.apply_async()`
   - Serializes task arguments
   - Sends to broker

---

#### Task Serialization

When you call:
```python
process_option_chain.delay({'product': 'NIFTY', 'expiry': '2025-01-25'})
```

Celery creates a message:
```json
{
  "id": "abc-123-def-456",
  "task": "process_option_chain",
  "args": [{"product": "NIFTY", "expiry": "2025-01-25"}],
  "kwargs": {},
  "retries": 0,
  "eta": null
}
```

Sends to Redis:
```
LPUSH celery 'json_message'
```

Worker polls:
```
message = BRPOP celery 1  # Block until task available
task_func = get_task('process_option_chain')
result = task_func(args[0])
SETEX 'celery-task-meta-abc-123' 3600 result
```

---

### 3.2 Understanding Idempotency

**Idempotency**: Processing the same message N times has the same effect as processing once.

#### Why Do We Need It?

**Scenario: Message delivered twice**

```
1. Worker receives task: process_option_chain(chain_data)
2. Worker processes: Calculates PCR, inserts into MongoDB
3. Worker crashes BEFORE acknowledging task
4. Celery re-delivers task (thinks worker failed)
5. Another worker receives SAME task
6. Processes again: PCR calculated twice, tries to insert duplicate
```

**Without idempotency:**
- Duplicate MongoDB inserts (if no unique constraint → duplicate data)
- PCR calculated twice (wastes CPU)
- Downstream systems receive duplicate events

**With idempotency:**
- Worker checks: "Have I processed this tick_id before?"
- If yes: Skip processing, acknowledge, move on
- If no: Process normally

---

#### Implementing Idempotency

**Approach 1: Idempotency key in Redis** (used by DeltaStream)

```python
tick_id = tick_data.get('tick_id', 0)
idempotency_key = f"processed:underlying:{product}:{tick_id}"

if redis_client.exists(idempotency_key):
    logger.info("tick_already_processed", product=product, tick_id=tick_id)
    return  # Skip processing

# Process...

redis_client.setex(idempotency_key, 3600, '1')  # Mark as processed (1 hour TTL)
```

**Why this works:**
- First worker: Key doesn't exist → processes → sets key
- Second worker (duplicate): Key exists → skips
- TTL (1 hour): Key expires after 1 hour (memory cleanup)

**Approach 2: Unique constraint in MongoDB**

```python
db.underlying_ticks.create_index(
    [('product', ASCENDING), ('tick_id', ASCENDING)],
    unique=True
)

try:
    db.underlying_ticks.insert_one({
        'product': product,
        'tick_id': tick_id,
        'price': price
    })
except DuplicateKeyError:
    logger.info("duplicate_tick", product=product, tick_id=tick_id)
    return
```

**Trade-off:**
- Redis approach: Faster (no DB roundtrip for check)
- MongoDB approach: More reliable (survives Redis flush)

We use **Redis approach** because:
- Speed is critical (extra DB read per message is expensive)
- TTL handles cleanup automatically
- If Redis flushes, worst case is processing duplicate (acceptable)

---

### 3.3 Building the Worker Enricher Service

#### Step 3.1: Create the Service Directory Structure

**Action:** Navigate to the worker enricher directory and create the necessary files:

```bash
cd services/worker-enricher
touch app.py requirements.txt Dockerfile supervisord.conf README.md
```

**Files we'll create:**

```
services/worker-enricher/
├── app.py                  # Main application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container image
├── supervisord.conf       # Process manager (runs subscriber + worker)
└── README.md              # Service documentation
```

---

#### Step 3.2: Define Python Dependencies

**Action:** Create `requirements.txt` with the Celery and database dependencies:

```bash
cat <<EOF > requirements.txt
celery==5.3.4
redis==5.0.1
pymongo==4.6.1
structlog==23.2.0
EOF
```

**Why each?**

- `celery`: Distributed task queue
- `redis`: For broker, result backend, caching, pub/sub
- `pymongo`: MongoDB driver
- `structlog`: Structured logging

---

### 3.4 Building the Worker Application

#### Step 3.3: Add Imports and Configuration

**Action:** Open `app.py` and add the imports and configuration at the top:

```python
#!/usr/bin/env python3
"""
Worker Enricher Service

Celery-based worker that:
1. Consumes raw market data from Redis pub/sub
2. Computes enrichments (PCR, straddle prices, build-up analysis, OHLC windows)
3. Persists enriched data to MongoDB
4. Updates Redis cache with latest values
5. Publishes enriched events back to Redis for WebSocket broadcast

Implements:
- Retry logic with exponential backoff
- Idempotency using task IDs
- Dead-letter queue for poison messages
- Structured logging
"""

import os
import json
import redis
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import Celery, Task
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
import math
```

**New imports:**

```python
from celery import Celery, Task
```
- `Celery`: Main class to create task queue app
- `Task`: Base class for custom task behavior

```python
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
```
- `MongoClient`: Database connection
- `ASCENDING/DESCENDING`: Index sort order
- `DuplicateKeyError`: Exception for unique constraint violations

```python
# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/deltastream')
CELERY_BROKER = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'worker-enricher')
```

**Why three different Redis databases?**

- **Database 0**: Cache + pub/sub (general use)
- **Database 1**: Celery broker (task queue)
- **Database 2**: Celery result backend (task results)

**Benefit**: Logical separation. Flushing cache doesn't flush task queue.

---

#### Step 3.4: Configure Celery Application

**Action:** Add the Celery initialization code to `app.py`:

```python
# Initialize Celery
celery_app = Celery('worker-enricher', broker=CELERY_BROKER, backend=CELERY_BACKEND)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    # Retry configuration
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3, 'countdown': 5},
    task_default_retry_delay=5,
)
```

**Line-by-line explanation:**

```python
celery_app = Celery('worker-enricher', broker=CELERY_BROKER, backend=CELERY_BACKEND)
```
- Creates Celery app named `'worker-enricher'`
- `broker`: Where to send tasks (Redis DB 1)
- `backend`: Where to store results (Redis DB 2)

```python
task_serializer='json',
accept_content=['json'],
result_serializer='json',
```
- **Serialization format**: JSON (human-readable, language-agnostic)
- Alternative: `pickle` (Python-only, security risk)
- **Why JSON?** Safe, debuggable, works with other languages

```python
timezone='UTC',
enable_utc=True,
```
- **All timestamps in UTC** (no timezone confusion)
- Critical for distributed systems (workers in different timezones)

```python
task_track_started=True,
```
- **Track when task starts** (not just when it completes)
- Allows monitoring: "Which tasks are currently running?"

```python
task_acks_late=True,
```
- **Acknowledge task AFTER processing** (not before)
- Without this:
  1. Worker receives task → Acknowledges immediately
  2. Worker crashes during processing
  3. Task is lost (broker thinks it was processed)
- With this:
  1. Worker receives task → Starts processing
  2. Worker crashes
  3. Broker re-delivers task (never acknowledged)

**Trade-off**: Task might be processed twice (hence idempotency needed).

```python
worker_prefetch_multiplier=1,
```
- **How many tasks to prefetch** per worker
- `prefetch=1`: Worker fetches one task at a time
- `prefetch=4`: Worker fetches 4 tasks, processes them one by one

**Why 1?**
- **Fair distribution**: Long-running tasks don't block workers
- Example with `prefetch=4`:
  - Worker 1 prefetches tasks [A, B, C, D] (A is long)
  - Worker 2 idle (no more tasks)
  - Worker 1 stuck on A, B/C/D waiting
  - Inefficient!
- With `prefetch=1`:
  - Worker 1 takes A (long task)
  - Worker 2 takes B/C/D (short tasks)
  - Better utilization

```python
task_reject_on_worker_lost=True,
```
- **Reject task if worker crashes**
- Task goes back to queue → another worker picks it up

```python
task_autoretry_for=(Exception,),
task_retry_kwargs={'max_retries': 3, 'countdown': 5},
```
- **Auto-retry on any Exception**
- Max 3 retries, wait 5 seconds between retries
- **Exponential backoff** (handled by Celery)

**Retry schedule:**
1. First attempt fails → wait 5s → retry
2. Second attempt fails → wait 10s → retry (2x backoff)
3. Third attempt fails → wait 20s → retry (2x backoff)
4. Fourth attempt fails → give up → send to DLQ

---

#### Step 3.5: Add Database Client Initialization

**Action:** Add lazy initialization functions for MongoDB and Redis clients:

```python
# Database clients (initialized lazily)
mongo_client = None
redis_client = None

def get_mongo_client():
    """Get or create MongoDB client (singleton pattern)."""
    global mongo_client
    if mongo_client is None:
        mongo_client = MongoClient(MONGO_URL)
    return mongo_client

def get_redis_client():
    """Get or create Redis client (singleton pattern)."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return redis_client
```

**Why lazy initialization?**

**Bad approach** (immediate initialization):
```python
mongo_client = MongoClient(MONGO_URL)  # Module load time
redis_client = redis.from_url(REDIS_URL)
```

**Problems:**
1. **Import time**: Connection created when module is imported (before Celery worker starts)
2. **Fork safety**: Celery forks worker processes → connections get duplicated → corruption
3. **Failure handling**: If MongoDB is down during import → entire service fails

**Good approach** (lazy initialization):
```python
mongo_client = None  # No connection yet

def get_mongo_client():
    global mongo_client
    if mongo_client is None:
        mongo_client = MongoClient(MONGO_URL)  # Connect on first use
    return mongo_client
```

**Benefits:**
1. **Fork-safe**: Each worker calls `get_mongo_client()` → gets own connection
2. **Delay connection**: Only connect when needed (not at import time)
3. **Singleton**: Multiple calls return same client (connection pooling works)

---

#### Step 3.6: Create Custom Task Base Class

**Action:** Add the custom task class for dead-letter queue handling:

```python
class EnrichmentTask(Task):
    """
    Base task class with error handling and logging.
    """
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure - log and send to dead-letter queue."""
        logger.error(
            "task_failed",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            args=args
        )
        
        # Send to dead-letter queue
        redis_client = get_redis_client()
        dlq_message = {
            'task_id': task_id,
            'task_name': self.name,
            'error': str(exc),
            'args': args,
            'timestamp': datetime.now().isoformat()
        }
        redis_client.lpush('dlq:enrichment', json.dumps(dlq_message))
```

**What is a Dead-Letter Queue (DLQ)?**

**Problem:** Task fails permanently after all retries. What happens to it?

**Without DLQ:**
- Task is lost
- No way to know what failed
- Can't debug or replay

**With DLQ:**
```python
redis_client.lpush('dlq:enrichment', json.dumps(dlq_message))
```

Failed tasks go to Redis list `dlq:enrichment`.

**Monitoring DLQ:**
```bash
redis-cli LLEN dlq:enrichment  # How many failed tasks?
redis-cli LRANGE dlq:enrichment 0 9  # View last 10 failures
```

**Replay from DLQ** (manual script):
```python
while True:
    message = redis_client.rpop('dlq:enrichment')
    if not message:
        break
    data = json.loads(message)
    # Inspect, fix issue, then re-queue
    process_option_chain.delay(data['args'][0])
```

**Real production:**
- DLQ goes to separate system (AWS SQS, Google Pub/Sub)
- Monitoring alerts when DLQ length > threshold
- Automated replay with circuit breaker

---

### 3.5 Implementing Task Functions

#### Step 3.7: Add Underlying Tick Processing Task

**Action:** Add the Celery task for processing underlying price ticks:

```python
@celery_app.task(base=EnrichmentTask, bind=True)
def process_underlying_tick(self, tick_data: Dict[str, Any]):
    """
    Process underlying price tick.
    
    - Store tick in MongoDB
    - Update Redis cache
    - Calculate and cache OHLC windows
    - Publish enriched tick to WebSocket channel
    
    Args:
        tick_data: Underlying tick dictionary
    """
    try:
        product = tick_data['product']
        price = tick_data['price']
        timestamp = datetime.fromisoformat(tick_data['timestamp'])
        tick_id = tick_data.get('tick_id', 0)
        
        # Idempotency check
        redis_client = get_redis_client()
        idempotency_key = f"processed:underlying:{product}:{tick_id}"
        if redis_client.exists(idempotency_key):
            logger.info("tick_already_processed", product=product, tick_id=tick_id)
            return
        
        # Store in MongoDB
        db = get_mongo_client()['deltastream']
        db.underlying_ticks.insert_one({
            'product': product,
            'price': price,
            'timestamp': timestamp,
            'tick_id': tick_id,
            'processed_at': datetime.now()
        })
        
        # Update Redis cache (latest price)
        redis_client.setex(
            f"latest:underlying:{product}",
            300,  # 5 minute TTL
            json.dumps({'price': price, 'timestamp': tick_data['timestamp']})
        )
        
        # Calculate OHLC windows (1min, 5min, 15min)
        for window_minutes in [1, 5, 15]:
            calculate_ohlc_window.delay(product, window_minutes)
        
        # Mark as processed (TTL 1 hour)
        redis_client.setex(idempotency_key, 3600, '1')
        
        # Publish enriched tick
        enriched = {
            'type': 'UNDERLYING_ENRICHED',
            'product': product,
            'price': price,
            'timestamp': tick_data['timestamp'],
            'processed_at': datetime.now().isoformat()
        }
        redis_client.publish('enriched:underlying', json.dumps(enriched))
        
        logger.info(
            "processed_underlying_tick",
            product=product,
            price=price,
            tick_id=tick_id
        )
        
    except Exception as e:
        logger.error("underlying_tick_processing_error", error=str(e), exc_info=True)
        raise
```

**Decorator breakdown:**

```python
@celery_app.task(base=EnrichmentTask, bind=True)
def process_underlying_tick(self, tick_data: Dict[str, Any]):
```

- `@celery_app.task`: Registers function as Celery task
- `base=EnrichmentTask`: Use custom task class (for DLQ handling)
- `bind=True`: Pass `self` (task instance) to function
- **Why `self`?** Access task metadata: `self.request.id`, `self.request.retries`

**Idempotency implementation:**

```python
idempotency_key = f"processed:underlying:{product}:{tick_id}"
if redis_client.exists(idempotency_key):
    logger.info("tick_already_processed", product=product, tick_id=tick_id)
    return
```

**Key format**: `processed:underlying:NIFTY:123`
- Includes product and tick_id (unique identifier)
- If key exists → already processed → skip
- If not → process and set key

**MongoDB insert:**

```python
db.underlying_ticks.insert_one({
    'product': product,
    'price': price,
    'timestamp': timestamp,
    'tick_id': tick_id,
    'processed_at': datetime.now()
})
```

**Schema:**
```json
{
  "_id": ObjectId("..."),
  "product": "NIFTY",
  "price": 21503.45,
  "timestamp": ISODate("2025-01-03T12:30:00Z"),
  "tick_id": 123,
  "processed_at": ISODate("2025-01-03T12:30:00.150Z")
}
```

**Why `processed_at`?**
- `timestamp`: When tick was generated (from feed)
- `processed_at`: When worker processed it
- **Latency = processed_at - timestamp** (monitoring metric)

**Cache update:**

```python
redis_client.setex(
    f"latest:underlying:{product}",
    300,  # 5 minute TTL
    json.dumps({'price': price, 'timestamp': tick_data['timestamp']})
)
```


---

**Navigation:**
← [Previous: Chapter 2-4](chapter02-4.md) | [Next: Chapter 3-2](chapter03-2.md) →

---
