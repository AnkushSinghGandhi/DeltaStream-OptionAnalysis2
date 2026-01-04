# DeltaStream: Building a Production-Grade Option Trading Analytics Platform

**A Hands-On Tutorial to Rebuild This Project From Scratch**

---

## What This Tutorial Is

This is a **guided implementation tutorial** that teaches you how to build a production-grade, microservices-based option trading analytics platform from the ground up. You'll learn not just the "how," but the "why" behind every architectural decision, every line of non-trivial code, and every production engineering choice.

This tutorial follows **real-world development flow**:
- Start with MVP (Minimum Viable Product)
- Add core features incrementally
- Build enhancements progressively
- Add advanced features
- Optimize for production

---

## Prerequisites

Before starting this tutorial, you should have:

- **Basic Python knowledge**: Variables, functions, classes, error handling
- **Basic understanding of APIs**: What REST APIs are and how HTTP works
- **Basic command line skills**: Running commands, navigating directories
- **Docker installed**: We'll explain Docker concepts, but you need it installed
- **Curiosity and patience**: This is a complex, production-ready system

What you **don't** need to know (we'll teach you):
- Microservices architecture
- Message queues and pub/sub patterns
- WebSocket programming
- Celery task queues
- Redis caching strategies
- MongoDB database design
- Docker Compose orchestration
- Production logging and observability

---

## Part 1: Architecture & Project Setup

### Learning Objectives

By the end of Part 1, you will understand:

1. **Why microservices?** The architectural philosophy and trade-offs
2. **System design principles** for real-time data processing platforms
3. **The complete architecture** of DeltaStream and how components interact
4. **Infrastructure setup** with Docker, Redis, and MongoDB
5. **Project structure** and development environment

---

### 1.1 Understanding the Problem Domain

#### What Are We Building?

**DeltaStream** is a **real-time option trading analytics platform** that:

- Streams live market data (option prices, underlying prices)
- Processes and enriches this data with calculations (PCR, max pain, volatility surface)
- Stores historical data for analysis
- Provides REST APIs for data access
- Broadcasts real-time updates via WebSockets

#### Real-World Use Case

Imagine you're an options trader. You need to:

1. **Monitor** real-time option prices for NIFTY, BANKNIFTY
2. **Analyze** Put-Call Ratio (PCR) to gauge market sentiment
3. **Calculate** max pain strikes to understand where market makers want expiry
4. **Visualize** implied volatility surfaces to spot anomalies
5. **Get alerts** when specific conditions are met

**Why is this complex?**

- **Volume**: Thousands of option contracts updating every second
- **Speed**: Traders need sub-second latency
- **Computation**: Greeks, IV calculations, aggregations are CPU-intensive
- **Reliability**: Missing data = lost opportunities = lost money
- **Scalability**: Must handle market hours (high load) and off-hours gracefully

This complexity demands a **microservices architecture**.

---

### 1.2 Microservices Architecture: The "Why"

#### The Monolith Alternative

We could build this as a **single monolithic application**:

```
┌─────────────────────────────────────┐
│     Single Flask App                │
│  ┌───────────────────────────────┐  │
│  │ Feed Generation               │  │
│  │ Data Processing               │  │
│  │ REST API                      │  │
│  │ WebSocket Server              │  │
│  │ Analytics Calculations        │  │
│  │ Authentication                │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Problems with this approach:**

1. **Scaling bottleneck**: CPU-heavy analytics slow down API responses
2. **Single point of failure**: If one part crashes, everything goes down
3. **Deployment risk**: Deploying a bug in analytics breaks the API
4. **Resource inefficiency**: Can't scale workers independently of API
5. **Technology lock-in**: Everything must use same language/framework
6. **Team collaboration**: Multiple developers can't work independently

#### The Microservices Solution

Instead, we **decompose** the system into independent services:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Feed Generator │────▶│  Redis Pub/Sub   │────▶│ Worker Enricher │
│  (Dummy Data)   │     │                  │     │   (Celery)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  API Gateway    │────▶│  Storage Service │◀────│    MongoDB      │
│  (REST API)     │     │  (Data Access)   │     │  (Persistence)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                                │
         │                                                ▼
         │              ┌──────────────────┐     ┌─────────────────┐
         └─────────────▶│  Auth Service    │     │ Redis (Cache)   │
                        │     (JWT)        │     │   & Broker      │
                        └──────────────────┘     └─────────────────┘
                                                           │
┌─────────────────┐     ┌──────────────────┐            │
│  Clients        │◀────│ Socket Gateway   │◀───────────┘
│  (WebSocket)    │     │  (Flask-SocketIO)│
└─────────────────┘     └──────────────────┘
         ▲
         │              ┌──────────────────┐
         └──────────────│  Analytics       │
                        │  (Aggregation)   │
                        └──────────────────┘
```

**Benefits we gain:**

1. **Independent scaling**: Scale workers without scaling API servers
2. **Fault isolation**: Worker crash doesn't break API
3. **Independent deployment**: Deploy analytics service without touching auth
4. **Technology flexibility**: Could use Go for high-performance workers
5. **Team autonomy**: Different teams own different services
6. **Easier testing**: Test each service in isolation

**Trade-offs we accept:**

1. **Operational complexity**: Managing 8+ services instead of 1
2. **Network latency**: Services communicate over network (microseconds added)
3. **Data consistency**: Distributed data requires careful design
4. **Debugging difficulty**: Tracing requests across services is harder
5. **Infrastructure cost**: More containers, more resources

**Why the trade-off is worth it for DeltaStream:**

- **Real-time requirement**: We need to decouple slow computations from fast API responses
- **Scaling pattern**: Workers need 10x scaling during market hours, API needs 2x
- **Reliability**: Feed generator failure shouldn't break historical data APIs
- **Production readiness**: We can upgrade services with zero downtime

---

### 1.3 Service Breakdown: What Each Service Does

Let me walk you through each service, explaining **what it does**, **why it exists**, and **what would break if we removed it**.

#### 1. Feed Generator Service

**What it does:**
- Generates synthetic option market data (in production: connects to real data feeds)
- Simulates underlying price movements using geometric Brownian motion
- Publishes data to Redis pub/sub channels

**Why it exists:**
- **Decoupling**: Data ingestion is separate from data processing
- **Testability**: We can test the entire pipeline without real market data
- **Flexibility**: Swap this out for real NSE/BSE feeds without touching other services

**What breaks without it:**
- No new data flows into the system (but historical APIs still work)

**Key insight:**
In production systems, you **always** want to decouple data sources from data consumers. Markets are unreliable (exchanges go down, APIs get rate-limited). By using pub/sub, downstream services don't care if the feed is live or replayed.

---

#### 2. Worker Enricher Service (Celery)

**What it does:**
- Subscribes to Redis pub/sub for raw market data
- Dispatches Celery tasks for processing
- Performs CPU-intensive calculations:
  - Put-Call Ratio (PCR)
  - Max pain strike calculation
  - OHLC window aggregations
  - Implied volatility surface
- Persists enriched data to MongoDB
- Updates Redis cache
- Publishes enriched events back to Redis

**Why it exists:**
- **Horizontal scaling**: Can run 10 worker processes during market hours, 2 during off-hours
- **Retry logic**: If a calculation fails, Celery retries with exponential backoff
- **Idempotency**: Same data processed twice produces same result (no duplicate inserts)
- **Priority queues**: Critical calculations can have higher priority

**What breaks without it:**
- Data enters the system but never gets processed
- No analytics, no PCR, no max pain
- WebSockets receive raw data but no enrichments

**Key insight:**
The worker is the "brains" of the system. It implements the **cache-aside pattern**:
1. Check Redis cache first (fast)
2. If miss, compute and store in MongoDB (slow)
3. Update cache for next request
4. Set TTL so stale data expires

This pattern is **critical** for real-time systems. Without it, every API call would hit MongoDB, adding 10-50ms latency.

---

#### 3. API Gateway Service

**What it does:**
- Single entry point for all REST API requests
- Routes requests to appropriate backend services
- Proxies authentication requests to Auth service
- Proxies data requests to Storage service
- Proxies analytics requests to Analytics service
- Provides OpenAPI documentation

**Why it exists:**
- **Unified interface**: Clients only know one URL (`http://api.deltastream.com`)
- **Security boundary**: Single place to enforce rate limiting, CORS, API keys
- **Backend abstraction**: Backend services can move/change without affecting clients
- **Request transformation**: Can modify requests/responses (e.g., add headers)

**What breaks without it:**
- Clients must know URLs of all internal services (security risk)
- CORS must be configured on every service
- No single place to add API monitoring

**Key insight:**
The API Gateway implements the **Backend for Frontend (BFF)** pattern. In large systems, you might have:
- One BFF for web clients (needs verbose responses)
- One BFF for mobile clients (needs compact responses)
- One BFF for internal services (needs no auth)

For DeltaStream, we use a single gateway, but it's designed to be extended.

---

#### 4. Storage Service

**What it does:**
- Wraps MongoDB with a clean REST API
- Provides data access layer for:
  - Underlying price ticks
  - Option quotes
  - Option chains
  - Available products and expiries
- Creates and manages MongoDB indexes
- Handles datetime serialization (MongoDB stores datetime, API returns ISO strings)

**Why it exists:**
- **Abstraction**: Other services don't need to know MongoDB query syntax
- **Security**: Database credentials only exist in one service
- **Consistency**: All datetime handling is in one place
- **Performance**: Index creation is centralized
- **Testing**: Can mock the entire database with a fake Storage service

**What breaks without it:**
- No way to retrieve historical data
- Every service needs MongoDB connection (tight coupling)
- Duplicate index creation logic across services

**Key insight:**
This is the **Repository Pattern**. In DDD (Domain-Driven Design), you never let domain logic (API Gateway) directly touch the database. Always go through a repository (Storage Service).

**Why?**
- Tomorrow, you might want to switch from MongoDB to PostgreSQL
- Only one service needs to change (Storage)
- Zero changes to API Gateway, Analytics, Workers

This is **dependency inversion** in action.

---

#### 5. Auth Service

**What it does:**
- User registration with password hashing (bcrypt)
- User login with JWT token generation
- Token verification for protected routes
- Token refresh for extending sessions

**Why it exists:**
- **Single source of truth**: All auth logic in one place
- **Security isolation**: JWT secret only exists in this service
- **Stateless authentication**: Tokens can be verified without database lookup
- **Easy to upgrade**: Add OAuth, 2FA, SSO without touching other services

**What breaks without it:**
- No user accounts
- No protected routes
- API is public (anyone can access)

**Key insight:**
JWT (JSON Web Token) is **stateless authentication**. Here's how it works:

1. User logs in → Auth service generates token
2. Token contains `{user_id, email, exp}` encrypted with `JWT_SECRET`
3. User sends token with every request
4. Any service with `JWT_SECRET` can verify token **without database call**

**Why is this powerful?**
- API Gateway can verify tokens without calling Auth service
- Zero database load for authentication
- Scales infinitely (no session storage)

**Trade-off:**
- Can't instantly revoke tokens (must wait for expiry)
- Solution: Short expiry (24h) + refresh tokens

---

#### 6. Socket Gateway Service

**What it does:**
- WebSocket server using Flask-SocketIO
- Subscribes to Redis pub/sub for enriched data
- Broadcasts real-time updates to connected clients
- Manages WebSocket rooms (product-specific subscriptions)
- Handles client events (subscribe, unsubscribe, get_products)

**Why it exists:**
- **Real-time communication**: REST APIs require polling (inefficient)
- **Decoupled broadcasting**: Workers publish to Redis, Socket Gateway handles delivery
- **Connection management**: Tracks which clients want which data
- **Scalability**: Multiple Socket Gateway instances can run behind load balancer

**What breaks without it:**
- Clients must poll REST API every second (wastes bandwidth, increases latency)
- No real-time dashboards
- Poor user experience

**Key insight:**
WebSockets are **bi-directional persistent connections**. Unlike HTTP:

- HTTP: Client opens connection → sends request → gets response → closes connection
- WebSocket: Client opens connection → connection stays open → server can push data anytime

**Why use Redis pub/sub as the middle layer?**

Without Redis:
```
Worker → Socket Gateway (directly)
```
**Problem**: Worker needs to know which Socket Gateway instances exist. Tight coupling.

With Redis:
```
Worker → Redis Pub/Sub → Socket Gateway (subscribes)
```
**Benefit**: Worker doesn't care who's listening. Socket Gateway can scale independently.

---

#### 7. Analytics Service

**What it does:**
- Aggregation queries (e.g., "PCR for last 7 days")
- Complex calculations that combine multiple data sources
- Volatility surface generation
- Max pain analysis across expiries
- Reads from MongoDB for historical data
- Reads from Redis for latest data

**Why it exists:**
- **Separation of concerns**: Read-heavy analytics separate from write-heavy storage
- **Performance**: Can cache expensive aggregations
- **Business logic**: Domain-specific calculations live here
- **Future growth**: ML models, backtesting, alerts will live here

**What breaks without it:**
- Can only get raw data, no analysis
- Every client must implement analytics (duplicate logic)
- No caching of expensive calculations

**Key insight:**
This service implements **CQRS** (Command Query Responsibility Segregation):

- **Commands** (writes): Feed → Worker → Storage
- **Queries** (reads): Client → API Gateway → Analytics/Storage

Why separate?
- Writes need to be fast and reliable (priority: consistency)
- Reads can be eventually consistent (priority: performance)
- Can scale reads independently from writes

---

#### 8. Logging Service

**What it does:**
- Centralized log ingestion
- Receives structured JSON logs from all services
- Write logs to files (can be shipped to Loki, Elasticsearch)
- Provides log query APIs (future)

**Why it exists:**
- **Debugging distributed systems**: Trace a request across 5 services
- **Observability**: What's slow? What's failing? How often?
- **Compliance**: Audit logs for regulated industries
- **Production monitoring**: Alert when error rate spikes

**What breaks without it:**
- Each service logs to its own stdout (can't correlate)
- No way to trace requests across services
- Production debugging is near impossible

**Key insight:**
Structured logging is **critical** for microservices. Compare:

**Unstructured:**
```
[2025-01-03 18:18:32] ERROR: Failed to process chain for NIFTY
```
**Structured:**
```json
{
  "timestamp": "2025-01-03T18:18:32Z",
  "service": "worker-enricher",
  "level": "error",
  "event": "chain_processing_failed",
  "product": "NIFTY",
  "task_id": "abc-123",
  "error": "DivisionByZero"
}
```

Why is structured better?
- Can query: "Show all errors for NIFTY in the last hour"
- Can aggregate: "How many `chain_processing_failed` events?"
- Can trace: "Show all logs for `task_id=abc-123`"

In production, ship to **Loki** (free, Grafana) or **Elasticsearch** (powerful, expensive).

---

### 1.4 Data Flow: Following a Tick Through the System

Let's trace a single option chain from generation to client display:

#### Step 1: Feed Generator creates data

```python
# services/feed-generator/app.py (simplified)
option_chain = {
    'product': 'NIFTY',
    'expiry': '2025-01-25',
    'spot_price': 21500,
    'strikes': [21000, 21050, 21100, ...],
    'calls': [/* 21 call options */],
    'puts': [/* 21 put options */]
}
redis_client.publish('market:option_chain', json.dumps(option_chain))
```

**Why Redis pub/sub?**
- **Fire-and-forget**: Feed doesn't wait for processing
- **Multiple subscribers**: Worker + logging + any future consumers
- **Decoupling**: Feed doesn't know who's listening

---

#### Step 2: Worker receives and dispatches

```python
# services/worker-enricher/app.py
# Main subscriber process
def subscribe_to_feeds():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('market:option_chain')
    
    for message in pubsub.listen():
        data = json.loads(message['data'])
        process_option_chain.delay(data)  # Dispatch to Celery
```

**Why Celery task queue?**
- Subscriber is single-threaded (can't block)
- Celery workers run in parallel (utilize all CPU cores)
- Built-in retry logic, dead-letter queues, monitoring

**What is `.delay()`?**
- `process_option_chain.delay(data)` → Sends task to Redis queue
- Celery worker picks it up → Executes `process_option_chain(data)`
- Non-blocking: Subscriber continues listening immediately

---

#### Step 3: Worker processes and enriches

```python
@celery_app.task
def process_option_chain(chain_data):
    # 3.1: Calculate PCR (Put-Call Ratio)
    total_call_oi = sum(c['open_interest'] for c in calls)
    total_put_oi = sum(p['open_interest'] for p in puts)
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
```

**What is PCR?**
- **Put-Call Ratio**: Ratio of put open interest to call open interest
- **Interpretation**:
  - PCR \u003e 1.2 → Bearish sentiment (more puts = market expects down move)
  - PCR \u003c 0.8 → Bullish sentiment (more calls = market expects up move)
  - PCR ≈ 1.0 → Neutral

**Why calculate OI ratio, not volume ratio?**
- Open Interest = outstanding contracts (reflects positioning)
- Volume = today's trades (reflects short-term activity)
- OI is more reliable for sentiment analysis

```python
    # 3.2: Calculate max pain
    max_pain_strike = calculate_max_pain(calls, puts, strikes)
```

**What is max pain?**
- The strike price where **option writers** (sellers) have maximum profit
- Calculated by: For each strike, sum the loss for all option buyers (call + put)
- The strike with **minimum total buyer value** is max pain

**Why does market gravitate toward max pain?**
- Option writers (mostly market makers) have more capital
- They delta-hedge to push price toward max pain strike
- On expiry day, price often settles near max pain

**Algorithm:**
```python
def calculate_max_pain(calls, puts, strikes):
    min_total_value = float('inf')
    max_pain = strikes[0]
    
    for test_strike in strikes:
        # If spot settles at test_strike:
        # - Calls below test_strike are ITM (buyers win)
        # - Puts above test_strike are ITM (buyers win)
        call_value = sum(
            c['open_interest'] * max(0, test_strike - c['strike'])
            for c in calls
        )
        put_value = sum(
            p['open_interest'] * max(0, p['strike'] - test_strike)
            for p in puts
        )
        total_value = call_value + put_value
        
        if total_value < min_total_value:
            min_total_value = total_value
            max_pain = test_strike
    
    return max_pain
```

**Line-by-line explanation:**

- `for test_strike in strikes`: Test each strike as potential settlement price
- `max(0, test_strike - c['strike'])`: Intrinsic value if spot = test_strike
  - Call at 21000, test_strike = 21100 → intrinsic = max(0, 21100-21000) = 100
  - Call at 21200, test_strike = 21100 → intrinsic = max(0, 21100-21200) = 0 (OTM)
- `c['open_interest'] * intrinsic`: Total payout to call buyers at this strike
- Sum across all calls + all puts = total payout to option buyers
- Strike with **minimum payout** = max pain (writers keep most premium)

```python
    # 3.3: Store in MongoDB
    db.option_chains.insert_one({
        'product': product,
        'expiry': expiry,
        'spot_price': spot_price,
        'pcr_oi': round(pcr, 4),
        'atm_straddle_price': round(atm_straddle_price, 2),
        'max_pain_strike': max_pain_strike,
        'calls': calls,
        'puts': puts,
        'timestamp': datetime.fromisoformat(chain_data['timestamp'])
    })
```

**Why store entire chain, not just PCR?**
- **Replayability**: Can re-calculate if algo changes
- **Historical analysis**: Backtesting strategies needs full chain
- **Auditability**: Regulatory requirement for some use cases

**Trade-off**: Storage cost (each chain ≈ 50KB, 100 chains/day ≈ 5MB/day ≈ 1.8GB/year)

```python
    # 3.4: Update Redis cache
    redis_client.setex(
        f"latest:chain:{product}:{expiry}",
        300,  # TTL = 5 minutes
        json.dumps(enriched_chain)
    )
```

**Why cache with TTL?**

- **Performance**: Next API request reads from Redis (sub-millisecond) instead of MongoDB (10-50ms)
- **Staleness control**: After 5 minutes, cache expires → next request hits MongoDB → cache refreshes
- **Memory efficiency**: Redis doesn't grow unbounded

**Cache-aside pattern flow:**

1. Client requests chain → API Gateway → Storage Service
2. Storage checks Redis: `GET latest:chain:NIFTY:2025-01-25`
3. If found → return immediately (cache hit)
4. If not found → query MongoDB → store in Redis → return (cache miss)

**TTL choice (5 minutes):**
- Too short (30s): Cache misses often → heavy MongoDB load
- Too long (1 hour): Stale data shown during volatile markets
- 5 minutes: Good balance for option data (doesn't change that fast)

```python
    # 3.5: Publish enriched event
    redis_client.publish('enriched:option_chain', json.dumps(enriched_chain))
```

**Why publish again after enriching?**
- Subscribers on `market:option_chain` get raw data
- Subscribers on `enriched:option_chain` get processed data (PCR, max pain)
- Socket Gateway subscribes to `enriched:*` channels to broadcast to clients

---

#### Step 4: Socket Gateway broadcasts to clients

```python
# services/socket-gateway/app.py
def subscribe_to_enriched_feeds():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('enriched:option_chain')
    
    for message in pubsub.listen():
        data = json.loads(message['data'])
        product = data['product']
        
        # Broadcast to all clients in this product's room
        socketio.emit(
            'chain_summary',
            {
                'product': product,
                'expiry': data['expiry'],
                'pcr_oi': data['pcr_oi'],
                'max_pain': data['max_pain_strike']
            },
            room=f'chain:{product}'
        )
```

**What is a "room"?**
- WebSocket abstraction: A named group of clients
- Client subscribes: `socket.emit('subscribe', {type: 'chain', symbol: 'NIFTY'})`
- Server adds client to room: `join_room(f'chain:NIFTY')`
- Broadcast to room: Only clients in that room receive the event

**Why use rooms instead of broadcasting to all clients?**
- **Efficiency**: Client watching BANKNIFTY doesn't need NIFTY updates
- **Bandwidth**: Mobile clients have limited bandwidth
- **Scalability**: 10,000 clients watching 100 products → 1000x fewer messages

---

#### Step 5: Client receives and displays

```javascript
// Client (browser)
const socket = io('http://localhost:8002');

// Subscribe to NIFTY chains
socket.emit('subscribe', {type: 'chain', symbol: 'NIFTY'});

// Receive updates
socket.on('chain_summary', (data) => {
    console.log(`NIFTY PCR: ${data.pcr_oi}`);
    console.log(`Max Pain: ${data.max_pain}`);
    // Update UI
});
```

---

### Complete Flow Summary

```
1. Feed Generator
   ↓ (publishes to Redis: market:option_chain)
   
2. Worker Enricher (Subscriber)
   ↓ (dispatches Celery task)
   
3. Celery Worker
   ↓ (calculates PCR, max pain)
   ↓ (stores in MongoDB)
   ↓ (updates Redis cache)
   ↓ (publishes to Redis: enriched:option_chain)
   
4. Socket Gateway
   ↓ (broadcasts to WebSocket clients in room)
   
5. Client Browser
   (displays PCR, max pain on dashboard)
```

**Latency breakdown:**
- Feed publishes: 0ms (baseline)
- Redis pub/sub: +1ms
- Celery dispatch: +5ms
- Worker calculation: +50ms (CPU-bound)
- MongoDB insert: +10ms
- Redis cache update: +1ms
- Publish enriched: +1ms
- Socket broadcast: +2ms
- Client receives: +5ms (network)

**Total: ~75ms** from data generation to client display.

**Production optimization:**
- Use Redis Streams instead of pub/sub (exactly-once delivery)
- Use connection pooling (reduce connection overhead)
- Pre-compute max pain for common expiries (reduce CPU)
- Use CDN for WebSocket connections (reduce network latency)

---

### 1.5 Infrastructure: Redis and MongoDB

#### Why Redis?

**Redis is used for THREE purposes in DeltaStream:**

**1. Pub/Sub Message Broker**
```python
redis_client.publish('market:underlying', json.dumps(tick))
```
- Fast (in-memory, single-digit microseconds)
- Supports pattern subscriptions (`enriched:*`)
- Fire-and-forget (publisher doesn't wait)

**2. Cache (Cache-Aside Pattern)**
```python
redis_client.setex('latest:chain:NIFTY', 300, json.dumps(chain))
```
- Sub-millisecond reads
- TTL support (automatic expiration)
- LRU eviction (when memory full, remove least recently used)

**3. Celery Broker + Result Backend**
```python
CELERY_BROKER_URL = 'redis://localhost:6379/1'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/2'
```
- Broker: Stores task queue (workers pull from here)
- Result backend: Stores task results (for task status tracking)

**Why use different Redis databases (0, 1, 2)?**
- Database 0: Cache + Pub/Sub
- Database 1: Celery broker (task queue)
- Database 2: Celery results

**Benefit**: Logical separation. Flushing cache doesn't flush task queue.

---

#### Why MongoDB?

**MongoDB is the persistent data store** for:
- Underlying price ticks (time-series data)
- Option quotes (individual options)
- Option chains (full chain snapshots)
- User accounts (auth data)

**Why MongoDB instead of PostgreSQL?**

**Reasons favoring MongoDB:**
1. **Schema flexibility**: Option chain structure might evolve (new Greeks, new fields)
2. **Horizontal scaling**: Sharding is easier (partition by product)
3. **Document model**: Option chain is naturally a nested document (calls\[\], puts\[\])
4. **Write performance**: Can handle high write throughput (500+ writes/sec)

**Reasons favoring PostgreSQL:**
1. **ACID transactions**: Strong consistency guarantees
2. **Complex queries**: JOINs, aggregations, window functions
3. **Data integrity**: Foreign keys, constraints, triggers

**For DeltaStream, MongoDB wins because:**
- We don't need JOINs (each collection is independent)
- Write throughput is critical (market data is high-volume)
- Schema evolution is likely (new analytics, new Greeks)

**In production:**
- Consider TimescaleDB (PostgreSQL extension for time-series) for tick data
- Consider PostgreSQL for user accounts (ACID for consistency)
- Hybrid approach: MongoDB for market data, PostgreSQL for operational data

---

#### MongoDB Indexes

**Why indexes matter:**

Without index:
```python
db.underlying_ticks.find({'product': 'NIFTY'})
# MongoDB scans ALL documents (10 million ticks) → 5 seconds
```

With index:
```python
db.underlying_ticks.create_index([('product', ASCENDING)])
db.underlying_ticks.find({'product': 'NIFTY'})
# MongoDB uses index → binary search → 10ms
```

**Indexes in Storage Service:**
```python
# Underlying ticks
db.underlying_ticks.create_index([
    ('product', ASCENDING),
    ('timestamp', DESCENDING)
])
```

**Why compound index (product + timestamp)?**
- Query pattern: "Get last 100 ticks for NIFTY, sorted by time"
- Compound index supports: `find({'product': 'NIFTY'}).sort('timestamp', -1)`
- Single-field index on `product` would require in-memory sort (slow)

**Index direction:**
- `ASCENDING`: Sort A→Z, 0→9, old→new
- `DESCENDING`: Sort Z→A, 9→0, new→old

We use `DESCENDING` on timestamp because queries want **latest** data first.

```python
# Option chains
db.option_chains.create_index([
    ('product', ASCENDING),
    ('expiry', ASCENDING),
    ('timestamp', DESCENDING)
])
```

**Why 3-field compound index?**
- Query: "Get latest chains for NIFTY expiring on 2025-01-25"
- Supports: `find({'product': 'NIFTY', 'expiry': '2025-01-25'}).sort('timestamp', -1).limit(1)`

**Index trade-offs:**
- **Pro**: Fast reads (10ms instead of 5sec)
- **Con**: Slower writes (must update index on every insert)
- **Con**: Storage overhead (indexes consume disk space, ~20% of data size)

**Rule of thumb:**
- Index the fields you query/sort by
- Don't over-index (every index slows writes)
- Monitor slow queries and add indexes as needed

---

### 1.6 Project Structure

Let's set up the directory structure:

```
deltastream-option-analysis/
├── services/                   # All microservices
│   ├── feed-generator/         # Data generation service
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── worker-enricher/        # Celery workers
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── supervisord.conf   # Runs subscriber + Celery worker
│   ├── auth/                   # Authentication service
│   ├── api-gateway/            # REST API gateway
│   ├── storage/                # MongoDB wrapper
│   ├── analytics/              # Analytics computations
│   ├── socket-gateway/         # WebSocket server
│   └── logging-service/        # Centralized logging
├── docker-compose.yml          # Orchestrates all services
├── .env.example                # Environment variables template
├── Makefile                    # Development shortcuts
├── README.md                   # Project documentation
└── tests/                      # Integration tests
    ├── conftest.py
    └── test_integration.py
```

**Why this structure?**

1. **Service isolation**: Each service is self-contained (can run independently)
2. **Docker-first**: Each service has its own Dockerfile
3. **Monorepo**: All services in one repository (easier for small teams)
4. **Shared nothing**: No shared code between services (enforces decoupling)

**Alternative: Polyrepo** (one git repo per service)
- **Pro**: True independence, separate CI/CD, different teams
- **Con**: Harder to coordinate changes, more overhead

For DeltaStream, **monorepo** is the right choice (single team, coordinated releases).

---

### 1.7 Setting Up the Development Environment

#### Prerequisites

Install the following:

1. **Docker Desktop** (includes Docker + Docker Compose)
   - Mac: `brew install --cask docker`
   - Windows: Download from docker.com
   - Linux: `sudo apt-get install docker.io docker-compose`

2. **Python 3.9+** (for local development)
   - Mac: `brew install python@3.9`
   - Windows: Download from python.org
   - Linux: `sudo apt-get install python3.9`

3. **Git**
   - Mac: `brew install git`
   - Linux: `sudo apt-get install git`

4. **Code editor** (VS Code recommended)

---

#### Initialize Project

```bash
# Create project directory
mkdir deltastream-option-analysis
cd deltastream-option-analysis

# Initialize git
git init

# Create .gitignore
cat <<EOF > .gitignore
__pycache__/
*.pyc
*.pyo
.env
*.log
.pytest_cache/
.DS_Store
logs/
EOF
```

---

#### Create `.env.example`

```bash
cat <<EOF > .env.example
# Redis
REDIS_URL=redis://redis:6379/0

# MongoDB
MONGO_URL=mongodb://mongodb:27017/deltastream

# JWT Secret (change in production!)
JWT_SECRET=your-secret-key-change-in-production

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
EOF
```

**Why `.env.example` instead of `.env`?**
- `.env` contains secrets (not committed to git)
- `.env.example` shows required variables (committed to git)
- Developers copy: `cp .env.example .env` and fill in their secrets

---

#### Create Directory Structure

```bash
# Create service directories
mkdir -p services/{feed-generator,worker-enricher,auth,api-gateway,storage,analytics,socket-gateway,logging-service}

# Create test directory
mkdir -p tests

# Create other directories
mkdir -p examples scripts k8s observability
```

---

#### Create `docker-compose.yml`

This file orchestrates all services. We'll build it incrementally in later parts, but here's the foundation:

```yaml
version: '3.8'

services:
  # Infrastructure
  redis:
    image: redis/redis-stack:latest
    container_name: deltastream-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - deltastream-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mongodb:
    image: mongo:6
    container_name: deltastream-mongodb
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: deltastream
    volumes:
      - mongo_data:/data/db
    networks:
      - deltastream-network
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/deltastream --quiet
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  redis_data:
  mongo_data:

networks:
  deltastream-network:
    driver: bridge
```

**Line-by-line explanation:**

```yaml
version: '3.8'
```
- Docker Compose file format version
- 3.8 supports health checks, build secrets, other modern features

```yaml
services:
```
- Defines all containers (services) in this application

```yaml
  redis:
    image: redis/redis-stack:latest
```
- `redis`: Service name (used for DNS inside Docker network)
- `image`: Use pre-built Redis image from Docker Hub
- `redis-stack`: Includes Redis + RedisInsight (web UI for debugging)

```yaml
    container_name: deltastream-redis
```
- Container name (shows in `docker ps`)
- Without this, Docker generates random name like `deltastream_redis_1`

```yaml
    ports:
      - "6379:6379"
```
- Port mapping: `host:container`
- Exposes Redis on `localhost:6379` (so you can connect from host machine)

```yaml
    command: redis-server --appendonly yes
```
- Overrides default command
- `--appendonly yes`: Enable AOF (Append-Only File) persistence
- **Why?** Without this, Redis is in-memory only (data lost on restart)
- **AOF vs RDB**: AOF logs every write (safer), RDB snapshots periodically (faster)

```yaml
    volumes:
      - redis_data:/data
```
- Mount Docker volume `redis_data` to container path `/data`
- **Why?** Persist data across container restarts
- Without volume: Container deleted → all data lost

```yaml
    networks:
      - deltastream-network
```
- Attach to custom network `deltastream-network`
- **Why?** Services on same network can resolve each other by name (`redis`, `mongodb`)
- Example: Worker connects to `redis://redis:6379` (not `localhost:6379`)

```yaml
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```
- **Health check**: How Docker knows if container is healthy
- `test`: Run `redis-cli ping` (returns `PONG` if healthy)
- `interval`: Check every 5 seconds
- `timeout`: Fail if command takes \u003e3 seconds
- `retries`: Mark unhealthy after 5 failed checks

**Why health checks matter:**

```yaml
  auth:
    depends_on:
      redis:
        condition: service_healthy
```

- Without health check: Auth starts immediately (Redis might not be ready → auth crashes)
- With health check: Docker waits until Redis is healthy before starting Auth

```yaml
  mongodb:
    environment:
      MONGO_INITDB_DATABASE: deltastream
```
- Creates database `deltastream` on first run
- Without this: MongoDB starts with no databases

```yaml
volumes:
  redis_data:
  mongo_data:
```
- Declares named volumes (Docker manages storage location)
- Alternative: Bind mounts (`./data:/data`) tie to host filesystem

```yaml
networks:
  deltastream-network:
    driver: bridge
```
- Creates custom network with bridge driver (default, suitable for single host)
- Alternative drivers: `host` (container uses host network), `overlay` (multi-host)

---

### 1.8 Verifying the Setup

Start just the infrastructure:

```bash
# Start Redis and MongoDB
docker-compose up -d redis mongodb

# Check status
docker-compose ps

# Should show:
# NAME                    STATUS              PORTS
# deltastream-redis       Up (healthy)        0.0.0.0:6379->6379/tcp
# deltastream-mongodb     Up (healthy)        0.0.0.0:27017->27017/tcp
```

**Test Redis:**

```bash
# Connect to Redis CLI
docker exec -it deltastream-redis redis-cli

# Inside Redis CLI:
127.0.0.1:6379> PING
PONG

127.0.0.1:6379> SET test "Hello DeltaStream"
OK

127.0.0.1:6379> GET test
"Hello DeltaStream"

127.0.0.1:6379> exit
```

**Test MongoDB:**

```bash
# Connect to MongoDB shell
docker exec -it deltastream-mongodb mongosh deltastream

# Inside Mongo shell:
test> db.test.insertOne({message: "Hello DeltaStream"})
{ acknowledged: true, insertedId: ObjectId('...') }

test> db.test.find()
[ { _id: ObjectId('...'), message: 'Hello DeltaStream' } ]

test> exit
```

---

### 1.9 Development Tools: Makefile

Create `Makefile` for common commands:

```makefile
.PHONY: help build up down logs test clean

help:
	@echo "DeltaStream Development Commands"
	@echo "================================="
	@echo "make build    - Build Docker images"
	@echo "make up       - Start all services"
	@echo "make down     - Stop all services"
	@echo "make logs     - Tail logs"
	@echo "make test     - Run tests"
	@echo "make clean    - Remove all containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "API Gateway: http://localhost:8000"
	@echo "Socket Gateway: http://localhost:8002"

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	pytest tests/ -v

clean:
	docker-compose down -v
	docker system prune -f
```

**Usage:**

```bash
make up     # Start services
make logs   # Watch logs
make down   # Stop services
```

---

### Part 1 Complete: What You've Learned

You now understand:

✅ **Why microservices** for this problem (scalability, fault isolation, independent deployment)

✅ **The architecture** (8 services, their roles, why each exists)

✅ **Data flow** (from feed generation to client display, with latency breakdown)

✅ **Infrastructure** (Redis for pub/sub + cache + queue, MongoDB for persistence)

✅ **Project structure** (monorepo with service isolation)

✅ **Docker Compose orchestration** (networks, volumes, health checks)

✅ **Development environment** (Docker, Makefile, env variables)

---

### What's Next: Part 2 Preview

In **Part 2: Building the Feed Generator**, we'll:

1. Create the Feed Generator service from scratch
2. Understand geometric Brownian motion for price simulation
3. Implement option pricing (simplified Black-Scholes)
4. Build the Redis publisher
5. Add structured logging
6. Containerize with Docker
7. Test the feed generation pipeline

**You'll write every line of code**, with explanations for:
- Why we calculate Greeks this way
- How option pricing works (time value, intrinsic value, moneyness)
- What realistic market data looks like
- How to publish to Redis pub/sub correctly
- How to structure a production Python service

---

### Mindset for Part 2

We're not just copying code. We're **understanding production engineering**:

- Why use `structlog` instead of `print()`?
- Why validate data before publishing?
- Why use environment variables for configuration?
- How to handle errors gracefully?
- How to make code testable?

**Remember**: The goal is not to finish quickly. The goal is to **deeply understand** every decision, so you can build systems like this yourself.

---

**End of Part 1**

---

---

