### 1.3 Service Breakdown: Understanding Each Component

Now that we've seen the architecture, let's understand each service in detail. For each, we'll cover:
- **What it does** - Core functionality
- **Why it exists** - Architectural rationale
- **What breaks without it** - Dependencies
- **Key patterns** - Design principles

---

## Feed Generator Service

### What It Does

- Generates synthetic option market data (production: connects to real feeds)
- Simulates underlying price movements using geometric Brownian motion
- Publishes data to Redis pub/sub channels

### Why It Exists

**Decoupling:**
```
Feed Generator ──▶ Redis ──▶ Workers
                     │
                     └──▶ Other Consumers
```
- Data source is isolated
- Swap synthetic → real feed without touching downstream
- Testing doesn't require real market connection

**Flexibility:**
- Development: Synthetic data
- Staging: Replay historical data
- Production: Real NSE/BSE feeds

### What Breaks Without It

- ❌ No new data enters system
- ✅ Historical APIs still work (MongoDB has data)

### Key Pattern: Pub/Sub Decoupling

**Why pub/sub over direct calls?**

**Bad (tight coupling):**
```python
# Feed directly calls worker
worker.process_tick(tick_data)
```
Problems:
- Feed must know about worker
- If worker is down, feed fails
- Can only have one consumer

**Good (pub/sub):**
```python
# Feed publishes, doesn't care who listens
redis_client.publish('market:tick', json.dumps(tick_data))
```
Benefits:
- Feed doesn't know consumers
- Multiple subscribers possible
- Fire-and-forget (non-blocking)

---

## Worker Enricher Service (Celery)

### What It Does

- Subscribes to Redis pub/sub for raw market data
- Dispatches Celery tasks for heavy processing
- Performs CPU-intensive calculations:
  - Put-Call Ratio (PCR)
  - Max Pain strike
  - OHLC aggregations
  - Implied volatility surface
- Persists enriched data to MongoDB
- Updates Redis cache with latest values
- Publishes enriched events back to Redis

### Why It Exists

**Horizontal Scaling:**
```bash
# Market hours: Scale up
celery -A tasks worker --concurrency=10

# Off-hours: Scale down  
celery -A tasks worker --concurrency=2
```

**Retry Logic:**
```python
@celery_app.task(bind=True, max_retries=3)
def process_chain(self, data):
    try:
        # Heavy calculation
        result = calculate_max_pain(...)
    except Exception as exc:
        # Exponential backoff: 2^retry seconds
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

**Idempotency:**
```python
# Same data processed twice → same result
# MongoDB: upsert instead of insert
db.chains.replace_one(
    {'product': product, 'expiry': expiry, 'timestamp': timestamp},
    enriched_data,
    upsert=True
)
```

### What Breaks Without It

- ❌ Data enters but never gets processed
- ❌ No PCR, no Max Pain, no analytics
- ❌ WebSocket clients receive raw data only

### Key Pattern: Cache-Aside

**Flow:**
1. Check Redis cache first (fast: <1ms)
2. If miss, compute and store in MongoDB (slow: 50ms)
3. Update cache for next request
4. Set TTL so stale data expires

**Code:**
```python
# Try cache first
cached = redis_client.get(f"latest:chain:{product}")
if cached:
    return json.loads(cached)

# Cache miss - compute
chain = compute_option_chain(product)

# Store in MongoDB (persistence)
db.chains.insert_one(chain)

# Update cache (performance)
redis_client.setex(
    f"latest:chain:{product}",
    300,  # 5 min TTL
    json.dumps(chain)
)

return chain
```

**Why critical for real-time?**
- Without cache: Every API call hits MongoDB (+50ms latency)
- With cache: Most calls hit Redis (<1ms latency)
- 50x faster response times

---

## API Gateway Service

### What It Does

- Single entry point for all REST API requests
- Routes to appropriate backend services:
  - `/api/auth/*` → Auth Service
  - `/api/data/*` → Storage Service
  - `/api/analytics/*` → Analytics Service
- Provides OpenAPI documentation
- Enforces CORS, rate limiting

### Why It Exists

**Unified Interface:**
```
Client                API Gateway           Backend Services
  │                        │                       │
  ├─GET /api/data/NIFTY───▶│                       │
  │                        ├──route to Storage────▶│
  │                        │◀──{data}──────────────┤
  │◀──{data}───────────────┤                       │
```

**Security Boundary:**
- Single place for rate limiting
- CORS configured once
- API keys validated once

**Backend Abstraction:**
```
# Backend URLs can change without affecting clients
OLD: http://storage-v1:8003/data
NEW: http://storage-v2:9000/data

# Gateway config changes, client URL stays same:
# https://api.deltastream.com/api/data
```

### What Breaks Without It

- ❌ Clients must know all internal service URLs (security risk)
- ❌ CORS must be configured on every service
- ❌ No unified API monitoring

### Key Pattern: Backend for Frontend (BFF)

**Concept:**
Different clients need different API shapes:

```python
# Web BFF (verbose responses)
@app.route('/api/data/chain/<product>')
def get_chain_web(product):
    chain = storage.get_chain(product)
    # Return full chain (50KB)
    return jsonify(chain)

# Mobile BFF (compact responses)
@app.route('/api/mobile/chain/<product>')
def get_chain_mobile(product):
    chain = storage.get_chain(product)
    # Return summary only (5KB)
    return jsonify({
        'pcr': chain['pcr'],
        'max_pain': chain['max_pain']
    })
```

DeltaStream uses single gateway, but it's extensible.

---

## Storage Service

### What It Does

- Wraps MongoDB with clean REST API
- Provides data access for:
  - Underlying price ticks
  - Option quotes
  - Option chains
  - Product/expiry lists
- Manages MongoDB indexes
- Handles datetime serialization

### Why It Exists

**Abstraction:**
```
# Other services don't need MongoDB knowledge
response = requests.get('http://storage:8003/data/chains/NIFTY')
chains = response.json()

# vs direct MongoDB (bad):
from pymongo import MongoClient
db = MongoClient('mongodb://...').deltastream
chains = list(db.option_chains.find({'product': 'NIFTY'}))
```

**Security:**
- Only Storage Service has MongoDB credentials
- Other services can't bypass access control

**Consistency:**
```python
# All datetime handling in one place
def serialize_datetime(doc):
    if 'timestamp' in doc:
        doc['timestamp'] = doc['timestamp'].isoformat()
    return doc
```

### What Breaks Without It

- ❌ No historical data retrieval
- ❌ Every service needs MongoDB connection (tight coupling)
- ❌ Duplicate query logic across services

### Key Pattern: Repository Pattern

**Concept:** Never let domain logic touch the database directly.

**Why?**
```
Today:    API Gateway → Storage Service → MongoDB
Tomorrow: API Gateway → Storage Service → PostgreSQL
                                         (only Storage changes!)
```

**Dependency Inversion:**
```
High-level modules (API Gateway) should not depend on 
low-level modules (MongoDB). Both should depend on 
abstractions (Storage Service interface).
```

---

## Auth Service

### What It Does

- User registration with bcrypt password hashing
- Login with JWT token generation
- Token verification for protected routes
- Token refresh for session extension

### Why It Exists

**Single Source of Truth:**
- All auth logic centralized
- JWT secret only exists here
- Easy to upgrade (add OAuth, 2FA, SSO)

**Stateless Authentication:**
```python
# User logs in
token = generate_jwt({
    'user_id': 123,
    'email': 'user@example.com',
    'exp': time.time() + 86400  # 24 hours
}, secret=JWT_SECRET)

# Token sent with every request
# Any service with JWT_SECRET can verify
payload = jwt.decode(token, JWT_SECRET)
# No database call needed!
```

### What Breaks Without It

- ❌ No user accounts
- ❌ No protected routes
- ❌ API is fully public

### Key Pattern: Stateless JWT Authentication

**How it works:**

**Traditional (stateful):**
```
1. Login → Server creates session in database
2. Returns session_id cookie
3. Every request → Lookup session in database
```
Problem: Database hit on every request

**JWT (stateless):**
```
1. Login → Server creates encrypted token
2. Returns token
3. Every request → Decrypt token (no database!)
```

**JWT Structure:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.    ← Header (algorithm)
eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTcwNjE5Mzg0NX0.  ← Payload (user_id, exp)
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c    ← Signature (verify integrity)
```

**Verification:**
```python
# Decode and verify
payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

# Check expiry
if payload['exp'] < time.time():
    raise TokenExpired()

# User authenticated!
user_id = payload['user_id']
```

**Trade-off:**
- ✅ No database load
- ✅ Scales infinitely
- ❌ Can't instantly revoke tokens (must wait for expiry)

**Solution:** Short TTL (24h) + refresh tokens

---

## Socket Gateway Service

### What It Does

- WebSocket server using Flask-SocketIO
- Subscribes to `enriched:*` Redis channels
- Broadcasts real-time updates to connected clients
- Manages WebSocket rooms (product-specific subscriptions)
- Handles client events (subscribe, unsubscribe)

### Why It Exists

**Real-time Communication:**

**HTTP Polling (bad):**
```javascript
// Client polls every second
setInterval(() => {
    fetch('/api/data/NIFTY').then(r => r.json()).then(data => {
        updateUI(data);
    });
}, 1000);
```
- ❌ 1 second latency
- ❌ Wastes bandwidth (repeated headers)
- ❌ Server load (1000 clients = 1000 req/sec)

**WebSocket (good):**
```javascript
const socket = io('http://localhost:8002');
socket.on('price_update', data => {
    updateUI(data);  // Instant!
});
```
- ✅ ~0ms latency (server pushes)
- ✅ Efficient (persistent connection)
- ✅ Scalable (10,000+ connections/server)

### What Breaks Without It

- ❌ Clients must poll (inefficient, laggy)
- ❌ No real-time dashboards
- ❌ Poor UX

### Key Pattern: Pub/Sub + Rooms

**Why Redis pub/sub as middleware?**

**Without Redis (tight coupling):**
```
Worker → Socket Gateway (directly)
```
Problem: Worker needs to know Socket Gateway location

**With Redis (decoupled):**
```
Worker → Redis → Socket Gateway (subscribes)
```
Benefit: Worker doesn't care who's listening

**Rooms for Targeted Broadcasting:**
```python
# Client joins room
join_room(f'product:NIFTY')

# Server broadcasts to room only
socketio.emit('price_update', data, room='product:NIFTY')
```

**Why?**
- Client watching BANKNIFTY doesn't need NIFTY updates
- Saves bandwidth (especially mobile)
- Scalable (10,000 clients × 100 products need targeted delivery)

---

## Analytics Service

### What It Does

- Aggregation queries ("PCR for last 7 days")
- Complex calculations combining multiple sources
- Volatility surface generation
- Max Pain analysis across expiries
- Reads from MongoDB (historical) + Redis (latest)

### Why It Exists

**Separation of Concerns:**
- Storage Service: Simple data access
- Analytics Service: Complex business logic

**Performance:**
```python
# Cache expensive aggregations
@lru_cache(maxsize=100)
def get_volatility_surface(product):
    # Expensive calculation
    ...
```

**Future Growth:**
- ML models
- Backtesting
- Alerts
- Strategy recommendations

### What Breaks Without It

- ❌ Can only get raw data
- ❌ Every client implements analytics (duplicate logic)
- ❌ No caching of expensive calculations

### Key Pattern: CQRS (Command Query Responsibility Segregation)

**Concept:** Separate reads from writes.

**Write Path (Commands):**
```
Feed → Worker → Storage (MongoDB)
```
- Optimized for writes
- Consistency is priority

**Read Path (Queries):**
```
Client → Analytics → MongoDB + Redis
```
- Optimized for reads
- Performance is priority
- Can be eventually consistent

**Benefits:**
- Scale reads independently from writes
- Different optimization strategies
- Different databases if needed (MongoDB for writes, Elasticsearch for reads)

---

## Logging Service

### What It Does

- Centralized log ingestion
- Receives structured JSON logs from all services
- Writes to files (can ship to Loki, Elasticsearch)
- Provides log query APIs

### Why It Exists

**Distributed System Debugging:**
```
Request ID: abc-123

[API Gateway]  2025-01-03T10:00:00Z request_received request_id=abc-123
[Storage]      2025-01-03T10:00:01Z query_started request_id=abc-123
[Storage]      2025-01-03T10:00:02Z query_slow request_id=abc-123 duration=2s
[API Gateway]  2025-01-03T10:00:02Z request_completed request_id=abc-123
```

Can trace request across 3 services!

### What Breaks Without It

- ❌ Each service logs to stdout (can't correlate)
- ❌ Production debugging is impossible

### Key Pattern: Structured Logging

**Unstructured (bad):**
```python
logger.info(f"Processing chain for {product}")
```
Output: `Processing chain for NIFTY`

**Structured (good):**
```python
logger.info("chain_processing_started", product=product, user_id=user_id)
```
Output (JSON):
```json
{
  "timestamp": "2025-01-03T10:00:00Z",
  "level": "info",
  "event": "chain_processing_started",
  "product": "NIFTY",
  "user_id": 123
}
```

**Why better?**
- Query: "Show all `chain_processing_started` events for user 123"
- Aggregate: "Count errors by product"
- Alert: "Trigger if event X happens > 100 times/minute"

---

## Summary: Why Microservices?

**Could we build this as a monolith?**

Yes! One Flask app doing everything.

**So why microservices?**

1. **Independent Scaling:** Scale analytics separately from feed processing
2. **Independent Deployment:** Deploy auth changes without touching feed
3. **Technology Freedom:** Use Python for analytics, Go for feed (performance)
4. **Team Autonomy:** Team A owns feed, Team B owns analytics
5. **Fault Isolation:** If analytics crashes, feed still works

**Trade-offs:**

**Microservices:**
- ✅ Scalable, flexible, fault-tolerant
- ❌ Complex, network overhead, harder to debug

**Monolith:**
- ✅ Simple, fast (no network), easy to debug
- ❌ Hard to scale, tight coupling

**For DeltaStream:** Microservices win because we need real-time scaling and market data is high-volume.

---

**Navigation:**
← [Previous: Chapter 1-1 (System Architecture)](chapter01-1.md) | [Next: Chapter 1-3 (Project Setup)](chapter01-3.md) →

---
