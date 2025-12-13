# 🎯 TECHNICAL DISCUSSION INTERVIEW QUESTIONS (NO CODING)

---

## 📚 **SECTION 11: ARCHITECTURE & DESIGN DECISIONS**

---

### **Q22: Why did you choose Flask over FastAPI for your microservices?**

**Answer:**
"Actually, in hindsight, FastAPI would have been a better choice, but let me explain the trade-offs:

**Why we used Flask:**
1. **Familiarity**: Team knew Flask well, faster development
2. **Ecosystem**: Flask-SocketIO for WebSocket support
3. **Simplicity**: Less boilerplate for simple REST APIs
4. **Flexibility**: Unopinionated framework

**Why FastAPI would be better:**

**1. Performance:**
- FastAPI: Async/await support, built on Starlette (async framework)
- Flask: Synchronous by default, WSGI-based
- For I/O-bound operations (database calls, Redis), FastAPI is 2-3x faster

**2. Type Safety:**
```python
# Flask - no validation
@app.route('/api/data/chain/<product>')
def get_chain(product):
    expiry = request.args.get('expiry')  # Could be None, could be invalid
    # Manual validation needed
    
# FastAPI - automatic validation
@app.get('/api/data/chain/{product}')
def get_chain(product: str, expiry: str = Query(..., regex=r'\d{4}-\d{2}-\d{2}')):
    # Automatic validation, type conversion, error messages
```

**3. Auto-generated Documentation:**
- FastAPI: OpenAPI/Swagger UI out-of-the-box
- Flask: Manual documentation

**4. Async Support:**
```python
# Flask - blocks on database call
def get_chain(product):
    chain = db.find_one(...)  # Blocks entire thread
    
# FastAPI - non-blocking
async def get_chain(product):
    chain = await db_async.find_one(...)  # Doesn't block
```

**Trade-offs:**

| Feature | Flask | FastAPI |
|---------|-------|---------|
| Learning curve | Low | Medium |
| Community | Huge | Growing |
| WebSocket | Flask-SocketIO | Requires Starlette/WebSockets |
| Performance | Good | Excellent |
| Type safety | Manual | Automatic |
| Async | Limited | Native |

**Our use case:**
- Trading platform with I/O-bound operations (MongoDB, Redis)
- Need low latency (<100ms)
- **FastAPI would have been 30-40% faster**

**Why we stuck with Flask:**
- Already built most of the system
- Flask-SocketIO integration for WebSocket was mature
- Performance was acceptable (<100ms achieved)

**For new projects, I'd choose FastAPI:**
- Better performance
- Type safety reduces bugs
- Modern Python features (async/await)
- Auto-generated docs

**When to use Flask:**
- Small projects, simple APIs
- Team unfamiliar with async programming
- Need Flask-specific plugins

**When to use FastAPI:**
- High-performance APIs
- Type safety important
- Async I/O operations
- Auto-generated docs needed"

---

### **Q23: Explain your decision to use MongoDB over PostgreSQL for storing trading data.**

**Answer:**
"This was a deliberate architectural decision based on our data model and access patterns.

**Why MongoDB:**

**1. Schema Flexibility:**
```javascript
// Option chain document (varies by product)
{
  product: "NIFTY",
  expiry: "2025-01-25",
  strikes: [21000, 21050, 21100, ...],  // Variable length
  calls: [
    {strike: 21000, bid: 120, ask: 122, oi: 50000, greeks: {...}},
    // 21 strikes for NIFTY, 41 for BANKNIFTY
  ],
  puts: [...],
  metadata: {
    pcr: 1.05,
    max_pain: 21500,
    custom_indicators: {...}  // Can add new fields without migration
  }
}
```

**With PostgreSQL:**
- Need separate tables: chains, strikes, greeks
- Joins required to reconstruct full chain
- Schema migrations for new fields
- More complex queries

**2. Write-Heavy Workload:**
```
Market data: 1000 ticks/second
Each tick: Insert into underlying_ticks
Option chains: 100 chains/second

MongoDB: O(1) inserts, no locks
PostgreSQL: Row-level locks, more overhead
```

**3. Document-Oriented:**
- Option chain is naturally a document
- MongoDB returns complete chain in one query
- No N+1 query problem

**4. Horizontal Scaling:**
```
MongoDB: Shard by product (NIFTY, BANKNIFTY)
- Automatic data distribution
- Add shards as data grows

PostgreSQL: Sharding is complex
- Manual partitioning
- Complex application logic
- Limited tooling
```

**5. Time-Series Optimization:**
```javascript
// MongoDB 5.0+ has time-series collections
db.createCollection("underlying_ticks", {
  timeseries: {
    timeField: "timestamp",
    metaField: "product",
    granularity: "seconds"
  }
});

// Automatic optimization:
- Columnar storage
- Better compression (10x)
- Faster time-range queries
```

**Trade-offs We Accepted:**

**1. No ACID Transactions:**
- MongoDB: No multi-document transactions (pre-4.0)
- **Impact**: Not critical for us, each document is atomic
- Trading data doesn't need cross-document transactions

**2. No Complex Joins:**
- MongoDB: Limited join support
- **Impact**: Designed for denormalized documents, not an issue

**3. No Strong Consistency:**
- MongoDB: Eventual consistency in replica sets
- **Impact**: Acceptable for real-time data (5-second freshness OK)

**When PostgreSQL Would Be Better:**

**1. Relational Data:**
```sql
-- User portfolios (many-to-many relationships)
users ← user_portfolios → positions → trades
      ↑ Complex joins needed
```

**2. ACID Requirements:**
- Financial transactions (debits/credits must be atomic)
- Order placement (money deduction + position creation)

**3. Complex Analytics:**
```sql
-- Multi-table aggregations
SELECT u.name, SUM(p.value) as portfolio_value
FROM users u
JOIN portfolios p ON u.id = p.user_id
JOIN positions pos ON p.id = pos.portfolio_id
GROUP BY u.id
HAVING portfolio_value > 100000
```

**4. Strong Consistency:**
- Banking systems
- Accounting systems

**Our Hybrid Approach (If I Could Redesign):**

```
MongoDB:
- Market data (ticks, chains) - high write, document-like
- Analytics results - flexible schema

PostgreSQL:
- User accounts - relational
- Portfolios & positions - ACID needed
- Trade history - complex queries

Redis:
- Hot cache - latest prices
- Session data - fast access
```

**Performance Comparison (Our Use Case):**

| Operation | MongoDB | PostgreSQL |
|-----------|---------|------------|
| Insert tick | 1ms | 2-3ms |
| Get latest chain | 10ms | 15-20ms (joins) |
| Time-range query | 20ms | 30ms |
| Horizontal scaling | Easy | Complex |

**Conclusion:**
MongoDB was the right choice for **market data** (time-series, document-oriented, write-heavy). For a complete trading platform, I'd use both:
- MongoDB for market data
- PostgreSQL for transactional data (user accounts, orders)

This is polyglot persistence - using the right database for the right job."

---

### **Q24: Why Redis Pub/Sub instead of Kafka for your event streaming?**

**Answer:**
"This was a pragmatic choice balancing simplicity vs features. Let me break down the decision:

**Why we chose Redis Pub/Sub:**

**1. Simplicity:**
```python
# Redis Pub/Sub - 3 lines
redis_client = redis.from_url(REDIS_URL)
redis_client.publish('market:underlying', json.dumps(data))

# Kafka - 15+ lines
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',
    retries=3,
    max_in_flight_requests_per_connection=5,
    compression_type='gzip',
    linger_ms=10
)
producer.send('market.underlying', data)
producer.flush()
```

**2. Latency:**
```
Redis Pub/Sub: <1ms (in-memory)
Kafka: 5-10ms (disk writes, network overhead)

For real-time trading: Every millisecond matters
```

**3. Infrastructure:**
```
Redis Pub/Sub: 1 Redis instance (already using for cache)
Kafka: 3 brokers + Zookeeper (3 nodes) = 6 servers minimum
```

**4. Operational Complexity:**
```
Redis: 
- Start: docker run redis
- Monitor: redis-cli info
- Backup: redis-cli save

Kafka:
- Setup: Configure brokers, Zookeeper, topics, partitions
- Monitor: JMX metrics, consumer lag, rebalancing
- Ops: Partition reassignment, broker failures, replication issues
```

**5. Development Speed:**
- Redis Pub/Sub: Developed pub/sub in 1 day
- Kafka: Would take 3-5 days (learning curve, setup, testing)

**Trade-offs We Accepted:**

**1. No Persistence:**
```
Redis Pub/Sub:
- Message published → Delivered to subscribers → Gone
- If subscriber offline, message lost

Kafka:
- Message published → Stored on disk for 7 days (configurable)
- New consumer can read from beginning
- Can replay messages
```

**Impact:** Acceptable because:
- Market data is ephemeral (new tick every second)
- Historical data stored in MongoDB
- Losing 1-2 seconds of data during restart is OK

**2. No Message Ordering Guarantees:**
```
Redis Pub/Sub:
- Message order not guaranteed under heavy load
- Network issues can cause reordering

Kafka:
- Strict ordering within partition
- Offset-based consumption
```

**Impact:** Not critical for our use case:
- Option chains are complete snapshots (not deltas)
- Idempotency handles duplicates/reordering

**3. No Consumer Groups:**
```
Redis Pub/Sub:
- All subscribers get all messages
- Can't distribute load

Kafka:
- Consumer groups for load distribution
- Only one consumer in group processes each message
```

**Impact:** Worked around with Celery:
- Redis Pub/Sub → Single subscriber → Celery task queue → Worker pool
- Celery provides load distribution

**4. No Backpressure:**
```
Redis Pub/Sub:
- If consumer is slow, messages buffer in memory
- Can cause Redis OOM

Kafka:
- Consumer pulls at own pace
- Broker doesn't care about consumer speed
```

**Impact:** Monitored Redis memory, acceptable for our throughput

**When Kafka Would Be Better:**

**1. Event Sourcing:**
```
Need to replay events from any point in time
Example: Reconstruct portfolio state at 2 PM yesterday
```

**2. High Throughput:**
```
Kafka: Millions of messages/second
Redis Pub/Sub: Thousands of messages/second

Our load: 1000 ticks/sec → Redis is sufficient
```

**3. Multiple Consumer Groups:**
```
Team A: Real-time analytics
Team B: ML model training
Team C: Audit logging

All need full stream, consume at different rates
Kafka: Consumer groups perfect for this
```

**4. Compliance/Audit:**
```
Financial regulations: Store all market data for 7 years
Kafka: Built-in retention policies
```

**5. Complex Stream Processing:**
```
Kafka Streams: Stateful operations, windowing, joins
Redis Pub/Sub: Simple pub/sub only
```

**Our Decision Matrix:**

| Requirement | Redis Pub/Sub | Kafka | Winner |
|-------------|---------------|-------|--------|
| Latency (<5ms) | ✅ <1ms | ❌ 5-10ms | Redis |
| Persistence | ❌ None | ✅ Durable | Kafka |
| Ops complexity | ✅ Simple | ❌ Complex | Redis |
| Throughput (1K msg/s) | ✅ Enough | ✅ Overkill | Redis |
| Replay capability | ❌ No | ✅ Yes | Kafka |
| Development time | ✅ 1 day | ❌ 5 days | Redis |

**Result:** 4-2 for Redis Pub/Sub

**Migration Path to Kafka (If Needed):**

**Phase 1: Keep Redis Pub/Sub for hot path**
```
Feed → Redis Pub/Sub → Workers (real-time)
     ↓
     └→ Kafka (async, durability)
```

**Phase 2: Dual write**
```
Feed → Redis Pub/Sub + Kafka → Workers
```

**Phase 3: Full Kafka**
```
Feed → Kafka → Workers
```

**Cost Comparison:**

```
Redis Pub/Sub: $200/month (single ElastiCache instance)
Kafka: $1,200/month (3 MSK brokers + Zookeeper)

6x more expensive
```

**Conclusion:**
For an MVP trading platform with:
- 1000 ticks/second
- <5ms latency requirement
- No compliance/audit needs
- Small team (2-3 developers)

**Redis Pub/Sub was the right choice.**

For a production fintech platform with:
- Millions of messages/second
- Audit trail requirements
- Multiple teams consuming data
- Complex stream processing

**Kafka would be essential.**

**Current Status:**
- Redis Pub/Sub works perfectly for our scale
- If we hit 10K+ ticks/second or need audit trail, we'd migrate to Kafka
- Would take 2 weeks to migrate (already designed for event-driven architecture)"

---

### **Q25: Explain your caching strategy. Why multi-level caching?**

**Answer:**
"Our caching strategy is based on the principle of **'cache where you need it'** with different levels optimized for different access patterns.

**The 3 Levels:**

**Level 1: Application Cache (In-Process)**
```
Not implemented in our project, but would add:
- Python dict/LRU cache in each service
- Latency: <1ms
- Scope: Single process
- Size: 100-500 MB per process
```

**Level 2: Distributed Cache (Redis - What We Built)**
```
- Latest market data
- TTL: 5 minutes
- Latency: 1-2ms
- Scope: All services
- Size: 2-4 GB
```

**Level 3: Database (MongoDB)**
```
- Historical data
- Persistent
- Latency: 10-50ms
- Scope: All services
- Size: Unlimited
```

**Why Multi-Level?**

**1. Latency Optimization:**
```
Request flow:
1. Check L1 (in-process): 0.1ms → Found? Return
2. Check L2 (Redis): 2ms → Found? Return + populate L1
3. Check L3 (MongoDB): 30ms → Found? Return + populate L2 & L1

Best case: 0.1ms (L1 hit)
Worst case: 32ms (L3 hit + populate caches)
```

**2. Reduce Load on Lower Layers:**
```
Without L1 & L2:
All requests hit MongoDB → 10,000 req/sec → DB overwhelmed

With L1 & L2:
L1 hit rate: 60% → 6,000 req/sec handled
L2 hit rate: 35% → 3,500 req/sec handled
L3 hit rate: 5% → 500 req/sec to MongoDB

10,000 req/sec → 500 req/sec to DB (95% reduction)
```

**3. Fault Tolerance:**
```
MongoDB down:
- L1 & L2 still serve cached data
- Graceful degradation (slightly stale data)
- System stays up

Single-level cache:
- Cache down → All requests fail
- No fallback
```

**Our Redis Caching Details:**

**Cache Keys Structure:**
```
latest:underlying:{product}        # Latest price for NIFTY
latest:option:{symbol}             # Latest quote for specific option
latest:chain:{product}:{expiry}    # Latest option chain
latest:pcr:{product}:{expiry}      # PCR values
ohlc:{product}:{window}m           # OHLC windows
volatility_surface:{product}       # IV surface
processed:{product}:{tick_id}      # Idempotency tracking
```

**TTL Strategy:**
```
Hot data (latest prices): 5 min
- Balance: Freshness vs DB load
- Market data updates every 1-5 seconds
- 5 min stale is acceptable

OHLC windows: Window duration
- 5min OHLC: 5min TTL
- Expires when window ends (natural lifecycle)

Idempotency keys: 1 hour
- Only need during retry window
- Longer TTL = wasted memory
```

**Cache Population Strategies:**

**1. Cache-Aside (Lazy Loading) - What We Use:**
```
def get_option_chain(product, expiry):
    # Try cache
    cached = redis.get(f"latest:chain:{product}:{expiry}")
    if cached:
        return json.loads(cached)  # Cache hit
    
    # Cache miss - query DB
    data = db.option_chains.find_one(...)
    
    # Populate cache
    redis.setex(f"latest:chain:{product}:{expiry}", 300, json.dumps(data))
    
    return data
```

**Pros:**
- Only cache what's requested
- No wasted memory
- Simple logic

**Cons:**
- First request always slow (cache miss)
- Cache stampede risk

**2. Write-Through (Could Add):**
```
def store_option_chain(chain_data):
    # Write to DB
    db.option_chains.insert_one(chain_data)
    
    # Immediately update cache
    key = f"latest:chain:{chain_data['product']}:{chain_data['expiry']}"
    redis.setex(key, 300, json.dumps(chain_data))
```

**Pros:**
- Cache always warm
- No cache miss
- Consistent

**Cons:**
- Caches unused data
- Write latency increases

**3. Write-Behind (Not Used - Too Complex):**
```
def store_option_chain(chain_data):
    # Write to cache immediately
    redis.setex(key, 300, json.dumps(chain_data))
    
    # Async write to DB (queue)
    async_write_to_db.delay(chain_data)
```

**Pros:**
- Fastest writes
- Decoupled

**Cons:**
- Data loss risk if cache fails before DB write
- Complex consistency

**Cache Invalidation Strategies:**

**1. TTL-Based (Primary) - What We Use:**
```python
redis.setex(key, 300, value)  # Auto-expires after 5 min
```
**Pros:** Simple, automatic, no manual logic
**Cons:** Stale data up to TTL

**2. Event-Driven (Secondary):**
```python
def process_option_chain(data):
    # Store in DB
    db.option_chains.insert_one(data)
    
    # Invalidate by overwriting with fresh data
    key = f"latest:chain:{data['product']}:{data['expiry']}"
    redis.setex(key, 300, json.dumps(data))
```
**Pros:** Always fresh
**Cons:** More complex

**3. Pattern-Based (Emergency):**
```python
def invalidate_all_nifty_caches():
    pattern = "latest:*:NIFTY:*"
    keys = redis.keys(pattern)
    if keys:
        redis.delete(*keys)
```
**Pros:** Bulk invalidation
**Cons:** Expensive (O(N) scan)

**Cache Metrics We Track:**

```python
@app.route('/metrics')
def cache_metrics():
    return {
        'redis_memory_usage': redis.info('memory')['used_memory_human'],
        'redis_keys': redis.dbsize(),
        'cache_hit_rate': calculate_hit_rate(),
        'avg_ttl': calculate_avg_ttl(),
        'hot_keys': get_most_accessed_keys()
    }
```

**Common Cache Patterns We Implemented:**

**1. Cache Stampede Prevention:**
```python
# Problem: 1000 requests hit expired cache simultaneously
# Solution: Lock-based approach (if needed)
lock = redis.lock(f"lock:{key}", timeout=10)
if lock.acquire(blocking=False):
    try:
        data = fetch_from_db()
        redis.setex(key, 300, data)
    finally:
        lock.release()
else:
    # Wait for other request to populate
    time.sleep(0.1)
    cached = redis.get(key)
```

**2. Probabilistic Early Expiration:**
```python
# Refresh cache before expiry to avoid stampede
ttl = redis.ttl(key)
if ttl < 30 and random.random() < 0.1:  # 10% of requests when TTL <30s
    refresh_cache(key)
```

**Why Not Single-Level (Just Redis)?**

**Option A: Only Redis (No MongoDB)**
```
Pros: Fast, simple
Cons: 
- No durability (data loss on restart)
- Limited by Redis memory
- No complex queries (time-range, aggregations)
```

**Option B: Only MongoDB (No Redis)**
```
Pros: Simple, durable
Cons:
- Slow (30-50ms vs 2ms)
- MongoDB overwhelmed at scale
- Higher costs (more DB instances)
```

**Option C: Multi-level (Our Choice)**
```
Pros:
- Best of both worlds
- Fault tolerant
- Scalable
- Fast

Cons:
- More complex
- Cache invalidation challenges
- Stale data possible
```

**Cost Analysis:**

```
Single MongoDB (no cache):
- Need M50 instance: $1,000/month
- Can handle 1,000 req/sec

Redis + Smaller MongoDB:
- Redis: $200/month
- MongoDB M30: $500/month
- Total: $700/month
- Can handle 10,000 req/sec

30% cost savings + 10x performance improvement
```

**Trade-offs:**

**Consistency:**
```
Multi-level cache: Eventual consistency
- L1, L2 might have stale data
- MongoDB always has latest

Strong consistency: Direct DB queries
- Always fresh
- But slower
```

**For trading data:** Eventual consistency acceptable (5 min stale OK)

**Complexity:**
```
No cache: Simple code, slow
Multi-level: Complex, fast, more bugs potential
```

**Memory:**
```
Cache uses RAM: Expensive but fast
DB uses disk: Cheap but slow
```

**Conclusion:**
Multi-level caching is essential for:
- High-performance systems
- Read-heavy workloads
- Expensive computations

Trade-off: Complexity for performance

Our 3-level strategy:
- L1 (not implemented): Would add for 10x scale
- L2 (Redis): Implemented, 95% hit rate
- L3 (MongoDB): Fallback + historical data

This gives us <5ms response times while keeping MongoDB load low."

---

### **Q26: How do you ensure data consistency in your distributed system?**

**Answer:**
"Great question. In distributed systems, you can't have strong consistency without sacrificing availability or partition tolerance (CAP theorem). Our system prioritizes **Availability** and **Partition Tolerance**, accepting **Eventual Consistency**.

**CAP Theorem Trade-off:**

```
CAP Theorem: Can only have 2 of 3:
- Consistency: All nodes see same data at same time
- Availability: Every request gets a response
- Partition Tolerance: System works despite network failures

Our choice: AP (Availability + Partition Tolerance)
- Trading platform must stay up (Availability)
- Network issues shouldn't crash system (Partition Tolerance)
- Accept eventual consistency (data sync within seconds)
```

**Consistency Challenges in Our System:**

**1. Cache Invalidation:**
```
Problem:
Worker updates MongoDB → MongoDB has new data
Redis cache still has old data → Clients see stale data

Timeline:
10:00:00 - Worker calculates PCR = 1.05, stores in MongoDB
10:00:00 - Redis cache has PCR = 1.03 (from 5 min ago)
10:00:01 - Client requests PCR → Gets 1.03 from cache (STALE)
10:05:00 - Redis cache expires → Next request gets 1.05 (FRESH)

Stale window: 0-5 minutes
```

**Solution: Event-Driven Cache Update**
```python
def process_option_chain(data):
    # Calculate PCR
    pcr = calculate_pcr(data)
    
    # Store in MongoDB
    db.option_chains.insert_one({'pcr': pcr, ...})
    
    # Immediately update cache (invalidate by overwriting)
    redis.setex(f"latest:pcr:{product}:{expiry}", 300, json.dumps({'pcr': pcr}))
    
    # Publish to WebSocket
    redis.publish('enriched:option_chain', json.dumps({'pcr': pcr}))

Stale window: 0-1 seconds (publish latency)
```

**2. Multiple Workers Processing Same Data:**
```
Problem:
tick_id=123 published to Redis Pub/Sub
Worker 1 receives it → Processes
Worker 2 receives it → Processes (DUPLICATE)

MongoDB has 2 entries for tick_id=123
Analytics show double-counted data
```

**Solution: Idempotency**
```python
def process_tick(tick_data):
    tick_id = tick_data['tick_id']
    
    # Idempotency check
    if redis.exists(f"processed:tick:{tick_id}"):
        return  # Already processed
    
    # Process
    db.ticks.insert_one(tick_data)
    
    # Mark as processed
    redis.setex(f"processed:tick:{tick_id}", 3600, '1')

Result: At-most-once processing (no duplicates)
```

**3. Celery Task Retries:**
```
Problem:
Task processes tick → Stores in MongoDB → Worker crashes before ACK
Celery retries task → Processes again (DUPLICATE)
```

**Solution: Idempotency + Late ACK**
```python
celery_app.conf.update(
    task_acks_late=True,  # ACK after success
)

@celery_app.task
def process_tick(data):
    # Idempotency check first
    if already_processed(data):
        return
    
    # Process
    store_in_db(data)
    
    # Only ACKs if successful

Result: At-least-once delivery + Idempotency = Exactly-once semantics
```

**4. Concurrent Updates:**
```
Problem:
Worker 1: Calculate PCR for NIFTY → 1.05
Worker 2: Calculate PCR for NIFTY → 1.03 (using old data)

Both update MongoDB/Redis simultaneously
Which value wins? Undefined!
```

**Solution: Timestamp-Based Last-Write-Wins**
```python
def update_pcr(product, expiry, pcr, timestamp):
    # Only update if newer
    existing = db.option_chains.find_one({
        'product': product,
        'expiry': expiry
    })
    
    if existing and existing['timestamp'] > timestamp:
        return  # Existing data is newer, skip
    
    # Update with newer data
    db.option_chains.update_one(
        {'product': product, 'expiry': expiry},
        {'$set': {'pcr': pcr, 'timestamp': timestamp}},
        upsert=True
    )

Result: Newer data always wins
```

**5. Read-Your-Writes Consistency:**
```
Problem:
Client writes data → Stored in MongoDB
Client immediately reads → Reads from Redis cache (old data)

Timeline:
10:00:00 - Client: "Update my portfolio"
10:00:01 - API Gateway: Updates MongoDB
10:00:02 - Client: "Show my portfolio"
10:00:03 - API Gateway: Reads from Redis cache (OLD portfolio)

Client sees old data after their own write!
```

**Solution: Write-Through Cache**
```python
def update_portfolio(user_id, data):
    # Update MongoDB
    db.portfolios.update_one({'user_id': user_id}, {'$set': data})
    
    # Immediately invalidate cache
    redis.delete(f"portfolio:{user_id}")
    
    # Or update cache directly (write-through)
    redis.setex(f"portfolio:{user_id}", 300, json.dumps(data))

Result: Read-your-writes consistency guaranteed
```

**6. MongoDB Replica Lag:**
```
Problem:
Write to MongoDB primary → Replicated to secondaries (100ms lag)
Read from secondary → Old data

Timeline:
10:00:00 - Write to primary: PCR = 1.05
10:00:00.100 - Read from secondary: PCR = 1.03 (not replicated yet)
```

**Solution: Read from Primary for Critical Data**
```python
# MongoDB read preference
mongo_client = MongoClient(
    MONGO_URL,
    readPreference='primary'  # Always read from primary
)

# Or use read concern
db.option_chains.find_one(
    {'product': 'NIFTY'},
    read_concern=ReadConcern('majority')  # Wait for majority replication
)
```

**Consistency Levels We Offer:**

**1. Strong Consistency (Direct DB Read):**
```python
@app.route('/api/data/chain/<product>')
def get_chain_consistent(product):
    # Skip cache, read directly from MongoDB primary
    data = db.option_chains.find_one({'product': product})
    return jsonify(data)

Latency: 30-50ms
Use case: Critical operations (order placement)
```

**2. Eventual Consistency (Cached):**
```python
@app.route('/api/data/chain/<product>')
def get_chain_fast(product):
    # Try cache first
    cached = redis.get(f"latest:chain:{product}")
    if cached:
        return jsonify(json.loads(cached))
    
    # Fallback to DB
    data = db.option_chains.find_one({'product': product})
    redis.setex(f"latest:chain:{product}", 300, json.dumps(data))
    return jsonify(data)

Latency: 2-5ms (cache hit)
Use case: Real-time dashboards (5sec stale OK)
```

**3. Session Consistency (Read-Your-Writes):**
```python
@app.route('/api/portfolio/update', methods=['POST'])
def update_portfolio():
    # Write
    db.portfolios.update_one(...)
    
    # Invalidate cache
    redis.delete(f"portfolio:{user_id}")
    
    # Force next read from DB
    request.session['cache_bypass'] = True

@app.route('/api/portfolio')
def get_portfolio():
    if request.session.get('cache_bypass'):
        # Read from DB (consistent with write)
        return db.portfolios.find_one(...)
    else:
        # Read from cache

Use case: User's own data
```

**Monitoring Consistency:**

```python
@app.route('/metrics/consistency')
def consistency_metrics():
    # Measure cache vs DB divergence
    sample_keys = get_random_cache_keys(100)
    
    divergent = 0
    for key in sample_keys:
        cached = redis.get(key)
        db_value = db.find_one(...)
        
        if cached != db_value:
            divergent += 1
    
    consistency_rate = 1 - (divergent / 100)
    
    return {
        'consistency_rate': consistency_rate,
        'divergent_keys': divergent,
        'avg_lag_seconds': calculate_avg_lag()
    }

Alert if consistency_rate < 0.95 (95%)
```

**Trade-offs:**

```
Strong Consistency:
Pros: Always correct data
Cons: Slow (30-50ms), lower availability

Eventual Consistency:
Pros: Fast (<5ms), highly available
Cons: Possibly stale (seconds)

Our choice: Eventual consistency
Why: Trading data freshness (5sec) acceptable, speed critical
```

**For Critical Operations (Would Add):**

```python
# Order placement - needs strong consistency
@app.route('/api/orders/place', methods=['POST'])
def place_order():
    # Use MongoDB transactions (ACID)
    with mongo_client.start_session() as session:
        with session.start_transaction():
            # Check balance
            balance = db.accounts.find_one({'user_id': user_id}, session=session)
            
            if balance < order_cost:
                session.abort_transaction()
                return {'error': 'Insufficient funds'}, 400
            
            # Deduct balance
            db.accounts.update_one(
                {'user_id': user_id'},
                {'$inc': {'balance': -order_cost}},
                session=session
            )
            
            # Create order
            db.orders.insert_one(order_data, session=session)
            
            # Commit atomically
            session.commit_transaction()

Strong consistency: Both balance update and order creation succeed or fail together
```

**Summary:**

```
Our Consistency Model:
- Market data: Eventual consistency (seconds)
- User reads: Session consistency (read-your-writes)
- Transactions: Would use strong consistency (not implemented)

Techniques Used:
1. Idempotency (prevent duplicates)
2. Late ACK (prevent data loss)
3. Event-driven invalidation (reduce staleness)
4. Timestamp-based conflict resolution (last-write-wins)
5. Write-through cache (read-your-writes)

Acceptable because:
- Market data updates every 1-5 seconds
- 5-second staleness acceptable for trading analytics
- Critical operations (order placement) would use transactions
```

This is a classic example of choosing **eventual consistency** for **performance and availability** in a non-critical domain (market data analytics, not order execution)."

---

Let me continue with more technical discussion questions. Would you like me to proceed with:
- Performance & Optimization questions
- Scalability discussions
- Technology trade-off questions
- Production issues & debugging
- Or something specific?
