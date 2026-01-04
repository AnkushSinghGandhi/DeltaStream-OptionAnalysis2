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

### 3.3 Building the Worker Enricher: Project Structure

```bash
cd services/worker-enricher
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

### 3.4 Dependencies: `requirements.txt`

```txt
celery==5.3.4
redis==5.0.1
pymongo==4.6.1
structlog==23.2.0
```

**Why each?**

- `celery`: Distributed task queue
- `redis`: For broker, result backend, caching, pub/sub
- `pymongo`: MongoDB driver
- `structlog`: Structured logging

---

### 3.5 Building `app.py`: Part 1 - Setup

#### Part 3.5.1: Imports and Configuration

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

#### Part 3.5.2: Celery Initialization

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

#### Part 3.5.3: Lazy Client Initialization (Singleton Pattern)

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

#### Part 3.5.4: Custom Task Base Class (Dead-Letter Queue)

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

### 3.6 Building `app.py`: Part 2 - Task Functions

#### Part 3.6.1: Processing Underlying Ticks

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

**Why cache latest price?**
- API request: "What's latest NIFTY price?"
- Without cache: Query MongoDB (10-50ms)
- With cache: Read Redis (sub-millisecond)

**TTL (5 minutes):**
- If no new ticks for 5 min → cache expires
- Next request hits MongoDB → refreshes cache
- Prevents stale data during market close

**Async OHLC calculation:**

```python
for window_minutes in [1, 5, 15]:
    calculate_ohlc_window.delay(product, window_minutes)
```

**Why `.delay()`?**
- OHLC calculation is slow (query MongoDB for all ticks in window)
- Don't block tick processing
- Dispatch as separate tasks → processed by available workers

**Publishing enriched event:**

```python
redis_client.publish('enriched:underlying', json.dumps(enriched))
```

- **Why publish again?** Socket Gateway subscribes to `enriched:*` channels
- Contains `processed_at` (not in raw tick)
- Decouples workers from Socket Gateway

---

#### Part 3.6.2: Processing Option Chains (PCR & Max Pain)

This is the **core analytics logic**. We'll break it down step by step.

```python
@celery_app.task(base=EnrichmentTask, bind=True)
def process_option_chain(self, chain_data: Dict[str, Any]):
    """
    Process complete option chain.
    
    - Store chain in MongoDB
    - Calculate PCR (Put-Call Ratio)
    - Calculate max pain
    - Identify ATM straddle
    - Calculate total call/put open interest build-up
    - Publish enriched chain
    
    Args:
        chain_data: Option chain dictionary
    """
    try:
        product = chain_data['product']
        expiry = chain_data['expiry']
        spot_price = chain_data['spot_price']
        calls = chain_data['calls']
        puts = chain_data['puts']
        
        # Calculate PCR (Put-Call Ratio)
        total_call_oi = sum(c['open_interest'] for c in calls)
        total_put_oi = sum(p['open_interest'] for p in puts)
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        total_call_volume = sum(c['volume'] for c in calls)
        total_put_volume = sum(p['volume'] for p in puts)
        pcr_volume = total_put_volume / total_call_volume if total_call_volume > 0 else 0
```

**PCR Calculation Explained:**

**PCR_OI (Open Interest based):**
```python
pcr = total_put_oi / total_call_oi
```

Example:
```
Calls:
- Strike 21000: OI = 50,000
- Strike 21050: OI = 40,000
- Strike 21100: OI = 30,000
Total Call OI = 120,000

Puts:
- Strike 21000: OI = 20,000
- Strike 21050: OI = 30,000
- Strike 21100: OI = 40,000
Total Put OI = 90,000

PCR = 90,000 / 120,000 = 0.75
```

**Interpretation:**
- PCR < 0.8: **Bullish** (more calls → expect upside)
- PCR > 1.2: **Bearish** (more puts → expect downside)
- PCR ≈ 1.0: **Neutral**

**Why OI vs Volume?**

- **Open Interest**: Outstanding contracts (reflects positioning)
  - High call OI at 22,000: Many believe NIFTY won't cross 22,000
  - High put OI at 21,000: Many believe NIFTY won't fall below 21,000

- **Volume**: Today's trades (reflects short-term activity)
  - High call volume: Lots of call buying/selling today
  - Less reliable for sentiment (could be day traders)

**We calculate both** but PCR_OI is more reliable.

```python
        # Find ATM strike
        strikes = sorted(chain_data['strikes'])
        atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
        
        # Get ATM straddle
        atm_call = next((c for c in calls if c['strike'] == atm_strike), None)
        atm_put = next((p for p in puts if p['strike'] == atm_strike), None)
        
        atm_straddle_price = 0
        if atm_call and atm_put:
            atm_straddle_price = atm_call['last'] + atm_put['last']
```

**ATM Strike Selection:**

```python
atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
```

**How it works:**

Example: spot_price = 21,537, strikes = [21,000, 21,050, ..., 21,500, 21,550, ...]

```
abs(21,000 - 21,537) = 537
abs(21,050 - 21,537) = 487
abs(21,500 - 21,537) = 37
abs(21,550 - 21,537) = 13  ← Minimum!
```

ATM strike = 21,550 (closest to spot)

**ATM Straddle Price:**

```python
atm_straddle_price = atm_call['last'] + atm_put['last']
```

**What is a straddle?**
- Buy **both** ATM call and ATM put
- Profits if price moves **either direction** (big volatility)

Example:
- ATM call (21,550) = ₹200
- ATM put (21,550) = ₹180
- Straddle cost = ₹380

**Breakeven:**
- Upside: 21,550 + 380 = 21,930 (profit if NIFTY > 21,930)
- Downside: 21,550 - 380 = 21,170 (profit if NIFTY < 21,170)

**Why track straddle price?**
- **Implied volatility indicator**: Expensive straddle = high expected volatility
- **Market sentiment**: Cheap straddle = low volatility expected (calm market)

```python
        # Calculate max pain (strike with maximum total writer profit)
        max_pain_strike = calculate_max_pain(calls, puts, strikes)
```

**Max Pain Algorithm** (already explained in Part 1, but here's the implementation):

```python
def calculate_max_pain(calls: List[Dict], puts: List[Dict], strikes: List[float]) -> float:
    """
    Calculate max pain strike (strike where option writers have maximum profit).
    
    Max pain is the strike price where the total value of outstanding options
    (both calls and puts) is minimized.
    """
    max_pain = strikes[0]
    min_total_value = float('inf')
    
    for strike in strikes:
        # Calculate total value for this strike
        call_value = sum(
            c['open_interest'] * max(0, strike - c['strike'])
            for c in calls
        )
        put_value = sum(
            p['open_interest'] * max(0, p['strike'] - strike)
            for p in puts
        )
        total_value = call_value + put_value
        
        if total_value < min_total_value:
            min_total_value = total_value
            max_pain = strike
    
    return max_pain
```

**Detailed walkthrough:**

Assuming spot = 21,500, strikes = [21,000, 21,500, 22,000]

**Test strike = 21,500 (ATM):**

Calls:
```
Strike 21,000 (ITM): OI = 50k, Intrinsic = max(0, 21500-21000) = 500
                     Value = 50k * 500 = 25,000,000
Strike 21,500 (ATM): OI = 40k, Intrinsic = max(0, 21500-21500) = 0
                     Value = 0
Strike 22,000 (OTM): OI = 30k, Intrinsic = max(0, 21500-22000) = 0
                     Value = 0
Total Call Value = 25,000,000
```

Puts:
```
Strike 21,000 (OTM): OI = 20k, Intrinsic = max(0, 21000-21500) = 0
                     Value = 0
Strike 21,500 (ATM): OI = 30k, Intrinsic = max(0, 21500-21500) = 0
                     Value = 0
Strike 22,000 (ITM): OI = 40k, Intrinsic = max(0, 22000-21500) = 500
                     Value = 40k * 500 = 20,000,000
Total Put Value = 20,000,000
```

**Total = 25M + 20M = 45M** (option buyers' total profit)

**Test strike = 22,000 (above spot):**

Calls:
```
Strike 21,000: OI = 50k, Intrinsic = max(0, 22000-21000) = 1000
               Value = 50,000,000
Strike 21,500: OI = 40k, Intrinsic = max(0, 22000-21500) = 500
               Value = 20,000,000
Strike 22,000: OI = 30k, Intrinsic = 0
               Value = 0
Total = 70,000,000
```

Puts:
```
All OTM, Total = 0
```

**Total = 70M** (higher than 45M → worse for option writers)

**Algorithm finds minimum** → Max pain = strike with **lowest total value** (best for option writers).

```python
        # Build-up analysis (OI changes - simplified for demo)
        call_buildup = sum(c['open_interest'] for c in calls if c['strike'] > spot_price)
        put_buildup = sum(p['open_interest'] for p in puts if p['strike'] < spot_price)
```

**OI Build-up Analysis:**

```python
call_buildup = sum(c['open_interest'] for c in calls if c['strike'] > spot_price)
```

**What is this measuring?**

- **OTM call OI**: Positions expecting upside
- If call_buildup is high:
  - Many sold OTM calls (resistance)
  - OR many bought OTM calls (bullish bets)

**Interpretation** (requires change from previous snapshot, not implemented in demo):
- **Increasing call OI**: New positions opened (need to check call price to determine buy/sell)
- **Decreasing call OI**: Positions closed (profit-taking or stop-loss)

**Production enhancement:**
```python
# Store previous OI
previous_chain = db.option_chains.find_one({
    'product': product,
    'expiry': expiry
}, sort=[('timestamp', DESCENDING)])

if previous_chain:
    for call in calls:
        prev_call = next((c for c in previous_chain['calls'] if c['strike'] == call['strike']), None)
        if prev_call:
            call['oi_change'] = call['open_interest'] - prev_call['open_interest']
```

---

**Storing enriched chain:**

```python
        # Create enriched chain
        enriched_chain = {
            'product': product,
            'expiry': expiry,
            'spot_price': spot_price,
            'pcr_oi': round(pcr, 4),
            'pcr_volume': round(pcr_volume, 4),
            'atm_strike': atm_strike,
            'atm_straddle_price': round(atm_straddle_price, 2),
            'max_pain_strike': max_pain_strike,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'call_buildup_otm': call_buildup,
            'put_buildup_otm': put_buildup,
            'calls': calls,
            'puts': puts,
            'timestamp': chain_data['timestamp'],
            'processed_at': datetime.now().isoformat()
        }
        
        # Store in MongoDB
        db = get_mongo_client()['deltastream']
        db.option_chains.insert_one({
            **enriched_chain,
            'timestamp': datetime.fromisoformat(chain_data['timestamp'])
        })
```

**Schema in MongoDB:**

```json
{
  "_id": ObjectId("..."),
  "product": "NIFTY",
  "expiry": "2025-01-25",
  "spot_price": 21537.45,
  "pcr_oi": 1.0234,
  "pcr_volume": 0.9876,
  "atm_strike": 21550,
  "atm_straddle_price": 380.50,
  "max_pain_strike": 21500,
  "total_call_oi": 1200000,
  "total_put_oi": 1228080,
  "calls": [ { "strike": 21000, "last": 550, ...}, ... ],
  "puts": [ { "strike": 21000, "last": 20, ...}, ... ],
  "timestamp": ISODate("2025-01-03T12:30:00Z"),
  "processed_at": "2025-01-03T12:30:00.250Z"
}
```

**Why store full chain?**
- **Historical analysis**: Backtest strategies
- **Reproducibility**: Re-calculate metrics if algo changes
- **Debugging**: Verify calculations

**Trade-off**: Storage (50KB/chain * 100/day = 5MB/day = 1.8GB/year)

```python
        # Update Redis cache
        redis_client = get_redis_client()
        redis_client.setex(
            f"latest:chain:{product}:{expiry}",
            300,
            json.dumps(enriched_chain)
        )
        
        # Cache PCR for analytics
        redis_client.setex(
            f"latest:pcr:{product}:{expiry}",
            300,
            json.dumps({
                'pcr_oi': round(pcr, 4),
                'pcr_volume': round(pcr_volume, 4),
                'timestamp': chain_data['timestamp']
            })
        )
        
        # Publish enriched chain
        redis_client.publish('enriched:option_chain', json.dumps(enriched_chain))
        
        logger.info(
            "processed_option_chain",
            product=product,
            expiry=expiry,
            pcr=round(pcr, 4),
            atm_straddle=round(atm_straddle_price, 2),
            max_pain=max_pain_strike
        )
        
    except Exception as e:
        logger.error("option_chain_processing_error", error=str(e), exc_info=True)
        raise
```

**Multiple cache keys:**

1. **Full chain**: `latest:chain:NIFTY:2025-01-25`
   - Contains all data (50KB)
   - Used by: "Get latest chain" API

2. **PCR only**: `latest:pcr:NIFTY:2025-01-25`
   - Contains just PCR (100 bytes)
   - Used by: "Get PCR" API, analytics dashboard

**Why separate?**
- Don't transfer 50KB when you only need PCR
- Reduces bandwidth, especially for mobile clients

---

### Part 3 Complete (Stopping Point)

This is a natural stopping point for Part 3. We've covered:

✅ Celery task queue fundamentals
✅ Idempotency patterns
✅ Retry logic and dead-letter queues
✅ Lazy client initialization (singleton pattern)
✅ Processing underlying ticks
✅ PCR calculation with detailed explanation
✅ Max Pain algorithm implementation
✅ MongoDB persistence
✅ Redis caching with TTL

### What's Next: Part 3 Continuation

The tutorial will continue with:

4. **OHLC Window Calculation** (aggregating ticks into candlesticks)
5. **Volatility Surface Generation** (3D IV surface across strikes and expiries)
6. **Pub/Sub Subscriber** (consuming Redis channels, dispatching Celery tasks)
7. **Supervisor Configuration** (running subscriber + workers together)
8. **Docker Setup** (Dockerfile, Docker Compose integration)
9. **Testing** (unit tests for PCR/max pain, integration tests)

**Ready to continue?** Let me know when you want the rest of Part 3!

#### Part 3.6.3: OHLC Window Calculation

```python
@celery_app.task(base=EnrichmentTask, bind=True)
def calculate_ohlc_window(self, product: str, window_minutes: int):
    """
    Calculate OHLC (Open, High, Low, Close) for a time window.
    
    Args:
        product: Product symbol
        window_minutes: Time window in minutes
    """
    try:
        db = get_mongo_client()['deltastream']
        redis_client = get_redis_client()
        
        # Get ticks from last N minutes
        start_time = datetime.now() - timedelta(minutes=window_minutes)
        ticks = list(db.underlying_ticks.find({
            'product': product,
            'timestamp': {'$gte': start_time}
        }).sort('timestamp', ASCENDING))
        
        if not ticks:
            return
        
        # Calculate OHLC
        prices = [t['price'] for t in ticks]
        ohlc = {
            'product': product,
            'window_minutes': window_minutes,
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'start_time': ticks[0]['timestamp'].isoformat(),
            'end_time': ticks[-1]['timestamp'].isoformat(),
            'num_ticks': len(ticks)
        }
        
        # Cache in Redis
        redis_client.setex(
            f"ohlc:{product}:{window_minutes}m",
            window_minutes * 60,
            json.dumps(ohlc)
        )
        
        logger.info(
            "calculated_ohlc",
            product=product,
            window=f"{window_minutes}m",
            ohlc=ohlc
        )
        
    except Exception as e:
        logger.error("ohlc_calculation_error", error=str(e), exc_info=True)
        raise
```

**What is OHLC?**

OHLC = **Open, High, Low, Close** - the four key prices for a time period.

Example: 1-minute candle for NIFTY (12:30:00 to 12:31:00)
```
Ticks in window:
12:30:05 → 21,500
12:30:15 → 21,505
12:30:30 → 21,510 ← High
12:30:45 → 21,502
12:31:00 → 21,507

OHLC:
Open  = 21,500 (first tick)
High  = 21,510 (max price)
Low   = 21,500 (min price)
Close = 21,507 (last tick)
```

**MongoDB query:**

```python
start_time = datetime.now() - timedelta(minutes=window_minutes)
ticks = list(db.underlying_ticks.find({
    'product': product,
    'timestamp': {'$gte': start_time}
}).sort('timestamp', ASCENDING))
```

**Query breakdown:**

```python
{'timestamp': {'$gte': start_time}}
```
- `$gte`: Greater than or equal to (MongoDB operator)
- Gets all ticks from `start_time` to now

**Why sort by timestamp ASCENDING?**

```python
prices = [t['price'] for t in ticks]
ohlc['open'] = prices[0]   # First tick (earliest)
ohlc['close'] = prices[-1]  # Last tick (latest)
```

- Need chronological order for open/close
- Open = first tick, Close = last tick

**OHLC calculation:**

```python
prices = [t['price'] for t in ticks]
ohlc = {
    'open': prices[0],
    'high': max(prices),
    'low': min(prices),
    'close': prices[-1]
}
```

**Simple list operations:**
- `max(prices)`: Maximum value in list (high)
- `min(prices)`: Minimum value in list (low)
- `prices[0]`: First element (open)
- `prices[-1]`: Last element (close)

**Caching with TTL:**

```python
redis_client.setex(
    f"ohlc:{product}:{window_minutes}m",
    window_minutes * 60,  # TTL in seconds
    json.dumps(ohlc)
)
```

**Why TTL = window_minutes * 60?**

Example: 5-minute window
- TTL = 5 * 60 = 300 seconds
- After 5 minutes, cache expires
- Next request recalculates with fresh data

**Benefit**: OHLC is always fresh (max lag = window size).

---

#### Part 3.6.4: Volatility Surface Generation

```python
@celery_app.task(base=EnrichmentTask, bind=True)
def calculate_volatility_surface(self, product: str):
    """
    Calculate implied volatility surface for a product.
    
    Creates a grid of IV values across strikes and expiries.
    
    Args:
        product: Product symbol
    """
    try:
        redis_client = get_redis_client()
        db = get_mongo_client()['deltastream']
        
        # Get recent option quotes
        recent_time = datetime.now() - timedelta(minutes=5)
        quotes = list(db.option_quotes.find({
            'product': product,
            'timestamp': {'$gte': recent_time}
        }))
        
        if not quotes:
            return
        
        # Group by expiry
        expiry_groups = {}
        for quote in quotes:
            expiry = quote['expiry']
            if expiry not in expiry_groups:
                expiry_groups[expiry] = []
            expiry_groups[expiry].append(quote)
        
        # Build surface
        surface = {
            'product': product,
            'expiries': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for expiry, expiry_quotes in expiry_groups.items():
            # Sort by strike
            expiry_quotes.sort(key=lambda x: x['strike'])
            
            strikes = [q['strike'] for q in expiry_quotes]
            ivs = [q['iv'] for q in expiry_quotes]
            
            surface['expiries'].append({
                'expiry': expiry,
                'strikes': strikes,
                'ivs': ivs,
                'avg_iv': sum(ivs) / len(ivs) if ivs else 0
            })
        
        # Cache surface
        redis_client.setex(
            f"volatility_surface:{product}",
            300,
            json.dumps(surface)
        )
        
        logger.info(
            "calculated_volatility_surface",
            product=product,
            num_expiries=len(surface['expiries'])
        )
        
    except Exception as e:
        logger.error("volatility_surface_error", error=str(e), exc_info=True)
        raise
```

**What is a Volatility Surface?**

A **3D surface** showing implied volatility (IV) across:
- **X-axis**: Strike prices
- **Y-axis**: Time to expiry
- **Z-axis**: Implied volatility

**Example data:**

```
Expiry: 2025-01-25 (7 days)
Strike  →  21000   21500   22000
IV      →  18%     20%     22%

Expiry: 2025-02-25 (37 days)
Strike  →  21000   21500   22000
IV      →  16%     18%     20%

Expiry: 2025-03-25 (67 days)
Strike  →  21000   21500   22000
IV      →  15%     17%     19%
```

**Observations:**
1. **ATM (21,500) has higher IV** than ITM/OTM (volatility smile)
2. **Longer expiry has lower IV** (more time = more certainty)

**Why track IV surface?**

- **Arbitrage opportunities**: If one strike's IV is abnormally high/low
- **Volatility skew**: Market fear (puts more expensive → high IV on downside)
- **Calendar spreads**: Exploit IV differences across expiries

**Grouping quotes by expiry:**

```python
expiry_groups = {}
for quote in quotes:
    expiry = quote['expiry']
    if expiry not in expiry_groups:
        expiry_groups[expiry] = []
    expiry_groups[expiry].append(quote)
```

**Result:**
```python
{
    '2025-01-25': [quote1, quote2, quote3, ...],
    '2025-02-25': [quote4, quote5, quote6, ...],
    '2025-03-25': [quote7, quote8, quote9, ...]
}
```

**Building surface:**

```python
for expiry, expiry_quotes in expiry_groups.items():
    expiry_quotes.sort(key=lambda x: x['strike'])
    
    strikes = [q['strike'] for q in expiry_quotes]
    ivs = [q['iv'] for q in expiry_quotes]
    
    surface['expiries'].append({
        'expiry': expiry,
        'strikes': strikes,
        'ivs': ivs,
        'avg_iv': sum(ivs) / len(ivs)
    })
```

**Why sort by strike?**
- Visualization needs strikes in order (21,000, 21,500, 22,000, ...)
- Allows plotting IV curve

**Average IV calculation:**
```python
avg_iv = sum(ivs) / len(ivs)
```

Example: ivs = [0.18, 0.20, 0.22]
```
avg_iv = (0.18 + 0.20 + 0.22) / 3 = 0.20 (20%)
```

**Average IV** = overall volatility level for this expiry.

---

### 3.7 Pub/Sub Subscriber Implementation

Now we need the **subscriber** that listens to Redis channels and dispatches Celery tasks.

```python
def subscribe_to_feeds():
    """
    Subscribe to Redis pub/sub channels and dispatch tasks.
    
    This runs in the main process and listens to market data feeds,
    dispatching Celery tasks for processing.
    """
    redis_client = get_redis_client()
    pubsub = redis_client.pubsub()
    
    # Subscribe to channels
    pubsub.subscribe('market:underlying', 'market:option_quote', 'market:option_chain')
    
    logger.info("subscribed_to_feeds", channels=['market:underlying', 'market:option_quote', 'market:option_chain'])
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel']
                data = json.loads(message['data'])
                
                # Dispatch to appropriate task
                if channel == 'market:underlying':
                    process_underlying_tick.delay(data)
                elif channel == 'market:option_quote':
                    process_option_quote.delay(data)
                elif channel == 'market:option_chain':
                    process_option_chain.delay(data)
                    # Also trigger volatility surface calculation
                    calculate_volatility_surface.delay(data['product'])
                    
    except KeyboardInterrupt:
        logger.info("subscriber_stopped")
    except Exception as e:
        logger.error("subscriber_error", error=str(e), exc_info=True)
        raise


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'subscribe':
        # Run subscriber in main process
        subscribe_to_feeds()
    else:
        # Run Celery worker
        celery_app.start()
```

**Redis pub/sub listener:**

```python
pubsub = redis_client.pubsub()
pubsub.subscribe('market:underlying', 'market:option_quote', 'market:option_chain')

for message in pubsub.listen():
    if message['type'] == 'message':
        channel = message['channel']
        data = json.loads(message['data'])
```

**How `pubsub.listen()` works:**

1. **Blocks waiting for message**
2. When publisher sends: `redis_client.publish('market:underlying', data)`
3. Subscriber receives message
4. Processes and continues listening

**Message structure:**

```python
{
    'type': 'message',
    'channel': 'market:underlying',
    'data': '{"product": "NIFTY", "price": 21500, ...}'
}
```

**Why check `message['type'] == 'message'`?**

Other message types:
- `'subscribe'`: Subscription confirmation
- `'unsubscribe'`: Unsubscription confirmation
- `'message'`: Actual data

We only process `'message'` types.

**Dispatching tasks:**

```python
if channel == 'market:underlying':
    process_underlying_tick.delay(data)
elif channel == 'market:option_quote':
    process_option_quote.delay(data)
elif channel == 'market:option_chain':
    process_option_chain.delay(data)
    calculate_volatility_surface.delay(data['product'])
```

**Why `.delay()`?**
- **Non-blocking**: Subscriber continues listening immediately
- **Parallel processing**: Celery workers handle tasks
- **Queuing**: If workers busy, tasks wait in queue

**Entry point logic:**

```python
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'subscribe':
        subscribe_to_feeds()
    else:
        celery_app.start()
```

**Two modes:**

1. **Subscriber mode**: `python app.py subscribe`
   - Runs `subscribe_to_feeds()` (listens to Redis)

2. **Worker mode**: `celery -A app worker`
   - Runs Celery worker (processes tasks)

**Why separate processes?**
- Subscriber: Single-threaded listener (lightweight)
- Worker: Multi-process task executor (CPU-intensive)
- If combined: Blocking operations in tasks would block subscriber

---

### 3.8 Supervisor Configuration

We need both subscriber and worker running together. **Supervisor** manages multiple processes.

Create `supervisord.conf`:

```ini
[supervisord]
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0

[program:subscriber]
command=python app.py subscribe
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:celery_worker]
command=celery -A app worker --loglevel=info --concurrency=4
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

**Line-by-line explanation:**

```ini
[supervisord]
nodaemon=true
```
- **Don't daemonize**: Run in foreground (required for Docker)
- Docker expects main process to keep running

```ini
logfile=/dev/null
logfile_maxbytes=0
```
- **Disable supervisor logs** (we have structured logging)
- Logs from programs go to stdout/stderr instead

```ini
[program:subscriber]
command=python app.py subscribe
```
- **Program 1**: Subscriber process
- Runs `python app.py subscribe` (which calls `subscribe_to_feeds()`)

```ini
autorestart=true
```
- **Auto-restart on crash**
- If subscriber dies → supervisor restarts it

```ini
stdout_logfile=/dev/stdout
stderr_logfile=/dev/stderr
```
- **Forward logs to Docker stdout/stderr**
- Allows `docker logs` to show all output

```ini
[program:celery_worker]
command=celery -A app worker --loglevel=info --concurrency=4
```
- **Program 2**: Celery worker
- `concurrency=4`: Run 4 worker processes (utilize 4 CPU cores)

**Why use supervisor?**

**Alternative** (without supervisor):
```bash
python app.py subscribe &
celery -A app worker &
wait
```

**Problems:**
- If subscriber crashes → not restarted
- No process management
- Difficult to stop gracefully

**With supervisor:**
- Auto-restart on crash
- Centralized logging
- Graceful shutdown of all processes

---

### 3.9 Docker Setup

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Install supervisor
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Run supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

**Additional requirement:**

Add to `requirements.txt`:
```txt
celery==5.3.4
redis==5.0.1
pymongo==4.6.1
structlog==23.2.0
supervisor==4.2.5
```

**Dockerfile breakdown:**

```dockerfile
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*
```
- **Install supervisor** (not available via pip, needs apt)
- `rm -rf /var/lib/apt/lists/*`: Cleanup to reduce image size

```dockerfile
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
```
- **Copy supervisor config** to standard location
- Supervisor reads configs from `/etc/supervisor/conf.d/`

```dockerfile
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```
- **Start supervisor** (which starts subscriber + worker)
- `-c`: Config file path

---

### 3.10 Docker Compose Integration

Update `docker-compose.yml`:

```yaml
  worker-enricher:
    build:
      context: ./services/worker-enricher
      dockerfile: Dockerfile
    container_name: deltastream-worker
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
      - SERVICE_NAME=worker-enricher
    depends_on:
      redis:
        condition: service_healthy
      mongodb:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped
```

**No exposed ports** for worker (it's internal only).

**Start the stack:**

```bash
docker-compose up -d redis mongodb feed-generator worker-enricher
```

**View logs:**

```bash
# All worker logs (subscriber + celery)
docker-compose logs -f worker-enricher

# Just subscriber
docker exec deltastream-worker supervisorctl tail -f subscriber

# Just celery
docker exec deltastream-worker supervisorctl tail -f celery_worker
```

---

### 3.11 Testing the Worker Enricher

#### Test 1: Manual MongoDB Inspection

```bash
# Connect to MongoDB
docker exec -it deltastream-mongodb mongosh deltastream

# Check ticks
db.underlying_ticks.find({product: 'NIFTY'}).limit(5).sort({timestamp: -1})

# Check chains
db.option_chains.find({product: 'NIFTY'}).limit(1).sort({timestamp: -1})

# Count documents
db.underlying_ticks.countDocuments()
db.option_chains.countDocuments()
```

**Expected output:**

```javascript
// Underlying ticks
{
  _id: ObjectId("..."),
  product: "NIFTY",
  price: 21503.45,
  timestamp: ISODate("2025-01-03T12:30:00Z"),
  tick_id: 123,
  processed_at: ISODate("2025-01-03T12:30:00.150Z")
}

// Option chain
{
  product: "NIFTY",
  expiry: "2025-01-25",
  pcr_oi: 1.0234,
  max_pain_strike: 21500,
  // ... full chain
}
```

---

#### Test 2: Redis Cache Verification

```bash
# Connect to Redis
docker exec -it deltastream-redis redis-cli

# Check latest price
GET latest:underlying:NIFTY

# Check latest chain
GET latest:chain:NIFTY:2025-01-25

# Check PCR cache
GET latest:pcr:NIFTY:2025-01-25

# Check OHLC
GET ohlc:NIFTY:5m
```

**Expected output:**

```bash
127.0.0.1:6379> GET latest:underlying:NIFTY
"{\"price\": 21503.45, \"timestamp\": \"2025-01-03T12:30:00Z\"}"

127.0.0.1:6379> GET latest:pcr:NIFTY:2025-01-25
"{\"pcr_oi\": 1.0234, \"pcr_volume\": 0.9876, \"timestamp\": \"...\"}"
```

---

#### Test 3: Celery Task Monitoring

```bash
# Enter worker container
docker exec -it deltastream-worker bash

# Check Celery worker status
celery -A app inspect active

# Check task stats
celery -A app inspect stats

# Check registered tasks
celery -A app inspect registered
```

**Expected output:**

```json
{
  "celery@worker1": {
    "active": [
      {
        "id": "abc-123",
        "name": "process_option_chain",
        "args": "[{\"product\": \"NIFTY\", ...}]",
        "time_start": 1704281400.123
      }
    ]
  }
}
```

---

#### Test 4: Unit Tests

Create `tests/test_worker.py`:

```python
import pytest
from services.worker_enricher.app import calculate_max_pain

def test_max_pain_calculation():
    """Test max pain algorithm with known inputs."""
    calls = [
        {'strike': 21000, 'open_interest': 50000},
        {'strike': 21500, 'open_interest': 40000},
        {'strike': 22000, 'open_interest': 30000}
    ]
    
    puts = [
        {'strike': 21000, 'open_interest': 20000},
        {'strike': 21500, 'open_interest': 30000},
        {'strike': 22000, 'open_interest': 40000}
    ]
    
    strikes = [21000, 21500, 22000]
    
    max_pain = calculate_max_pain(calls, puts, strikes)
    
    # Expected: 21500 (verify with manual calculation)
    assert max_pain == 21500

def test_pcr_calculation():
    """Test PCR calculation."""
    calls = [
        {'open_interest': 50000, 'volume': 1000},
        {'open_interest': 40000, 'volume': 800}
    ]
    
    puts = [
        {'open_interest': 45000, 'volume': 900},
        {'open_interest': 36000, 'volume': 720}
    ]
    
    total_call_oi = sum(c['open_interest'] for c in calls)
    total_put_oi = sum(p['open_interest'] for p in puts)
    pcr = total_put_oi / total_call_oi
    
    # 81000 / 90000 = 0.9
    assert abs(pcr - 0.9) < 0.001

def test_atm_strike_selection():
    """Test ATM strike selection."""
    strikes = [21000, 21500, 22000, 22500]
    spot_price = 21537
    
    atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
    
    assert atm_strike == 21500  # Closest to 21537
```

**Run tests:**

```bash
pytest tests/test_worker.py -v
```

**Expected output:**

```
tests/test_worker.py::test_max_pain_calculation PASSED
tests/test_worker.py::test_pcr_calculation PASSED
tests/test_worker.py::test_atm_strike_selection PASSED
====== 3 passed in 0.12s ======
```

---

### 3.12 Production Optimizations

#### 1. MongoDB Indexes (Critical for Performance)

The indexes we created:

```python
# In storage service or worker
db.underlying_ticks.create_index([
    ('product', ASCENDING),
    ('timestamp', DESCENDING)
])

db.option_chains.create_index([
    ('product', ASCENDING),
    ('expiry', ASCENDING),
    ('timestamp', DESCENDING)
])
```

**Why these indexes?**

Query pattern:
```python
db.underlying_ticks.find({
    'product': 'NIFTY',
    'timestamp': {'$gte': start_time}
}).sort('timestamp', DESCENDING).limit(100)
```

**Without index:**
- MongoDB scans **all documents** (10M ticks)
- Filters by product + timestamp
- Sorts in memory
- **Query time: 5-10 seconds**

**With compound index:**
- MongoDB uses index to find matching documents
- Results already sorted (index is sorted)
- **Query time: 10-50ms** (100-1000x faster!)

---

#### 2. Celery Concurrency Tuning

```yaml
# docker-compose.yml
command: celery -A app worker --loglevel=info --concurrency=4
```

**How to choose concurrency?**

Rule of thumb:
- **CPU-bound tasks**: concurrency = CPU cores
- **I/O-bound tasks**: concurrency = 2-4x CPU cores

For option chain processing:
- Mostly CPU (PCR, max pain calculations)
- Set concurrency = number of cores

**Check CPU usage:**
```bash
docker stats deltastream-worker
```

If CPU < 80% → can increase concurrency
If CPU = 100% → at optimal concurrency

---

#### 3. Redis Memory Management

```bash
# Check Redis memory usage
docker exec deltastream-redis redis-cli INFO memory

# Set max memory (prevents infinite growth)
docker exec deltastream-redis redis-cli CONFIG SET maxmemory 2gb
docker exec deltastream-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

**Memory policies:**

- `allkeys-lru`: Evict least recently used keys when full
- `volatile-ttl`: Evict keys with shortest TTL
- `noeviction`: Return errors when full

We use **allkeys-lru** because:
- Cache keys have TTL (can be evicted safely)
- Oldest cached data is least useful

---

#### 4. Monitoring and Alerting

**Metrics to track:**

1. **Task processing rate**: Tasks/second processed
2. **Task latency**: Time from publish to completion
3. **DLQ length**: Failed tasks in dead-letter queue
4. **Cache hit rate**: Redis hits / total requests
5. **MongoDB query time**: Slow query log

**Example Prometheus metrics:**

```python
from prometheus_client import Counter, Histogram

task_counter = Counter('celery_tasks_total', 'Total tasks processed', ['task_name', 'status'])
task_duration = Histogram('celery_task_duration_seconds', 'Task duration', ['task_name'])

@celery_app.task(base=EnrichmentTask, bind=True)
def process_option_chain(self, chain_data):
    with task_duration.labels(task_name='process_option_chain').time():
        # ... processing
        task_counter.labels(task_name='process_option_chain', status='success').inc()
```

---

### Part 3 Complete: What You've Built

You now have a **production-ready Worker Enricher** that:

✅ Uses Celery for distributed task processing
✅ Implements idempotency (Redis-based)
✅ Has retry logic with exponential backoff
✅ Sends failed tasks to dead-letter queue
✅ Processes underlying ticks (stores + caches)
✅ Calculates PCR and Max Pain
✅ Generates OHLC windows (1min, 5min, 15min)
✅ Builds volatility surfaces
✅ Subscribes to Redis pub/sub channels
✅ Runs subscriber + workers via Supervisor
✅ Integrates with Docker Compose
✅ Has comprehensive tests
✅ Follows production best practices

---

### Key Learnings from Part 3

**1. Task Queues solve the decoupling problem**
- Subscriber doesn't wait for processing
- Workers process in parallel
- System scales horizontally

**2. Idempotency is non-negotiable in distributed systems**
- Messages can be delivered twice
- Processing must be safe to repeat
- Redis keys with TTL are simple and effective

**3. Retry logic + DLQ handle failures gracefully**
- Transient errors (network blip) → auto-retry
- Permanent errors (bad data) → send to DLQ
- Operators can inspect and replay

**4. Caching is critical for real-time systems**
- MongoDB query: 10-50ms
- Redis read: sub-millisecond
- 100x speedup for API latency

**5. Proper indexing makes/breaks performance**
- Compound indexes support complex queries
- Index on (product, timestamp) is 1000x faster
- Always index on fields you query/sort by

**6. Production systems need monitoring**
- Track task rates, latency, failures
- Monitor DLQ length
- Alert on anomalies

---

### What's Next: Tutorial Continuation

**Part 4** will cover:
- **Storage Service**: MongoDB wrapper with clean REST API
- **Auth Service**: JWT authentication, user registration/login
- **MongoDB indexes**: Time-series optimizations
- **API design patterns**: Pagination, filtering, caching

**Part 5** will cover:
- **API Gateway**: Request routing, authentication middleware
- **OpenAPI documentation**: Auto-generated API docs
- **Rate limiting**: Protect services from abuse
- **Error handling**: Standardized error responses

**Part 6** will cover:
- **Socket Gateway**: WebSocket server with Flask-SocketIO
- **Room-based subscriptions**: Client-specific data streaming
- **Connection management**: Handling disconnects
- **Scaling WebSockets**: Multiple gateway instances

---

**Tutorial Progress:**
- ✅ Part 1: Architecture & Project Setup (1,349 lines)
- ✅ Part 2: Feed Generator Service (1,450 lines)
- ✅ Part 3: Worker Enricher Service (2,100+ lines)
- **Total: 4,900+ lines of comprehensive tutorial content**

---

**Ready to continue?** Let me know when you want Part 4: Building the Storage & Auth Services!

---

