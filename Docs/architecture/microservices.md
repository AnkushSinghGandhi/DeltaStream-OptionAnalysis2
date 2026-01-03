# Microservices Architecture

> **Deep dive into microservices patterns and communication**

## 🏗️ Service Catalog

### 1. Feed Generator Service
**Port**: N/A (background process)
**Purpose**: Generate synthetic market data
**Dependencies**: Redis (pub/sub)

**Responsibilities:**
- Simulate underlying price movements (Geometric Brownian Motion)
- Generate option chains with Black-Scholes pricing
- Publish raw market data to Redis channels

**Scaling**: 1 instance (single data source)

---

### 2. Worker Enricher Service
**Port**: N/A (Celery workers)
**Purpose**: Process and enrich market data
**Dependencies**: Redis (broker + pub/sub), MongoDB

**Responsibilities:**
- Subscribe to raw market data events
- Calculate analytics (PCR, max pain, OHLC)
- Store enriched data in MongoDB
- Update Redis cache
- Publish enriched events

**Scaling**: 2-20 workers (CPU-bound tasks)

**Process Management**: Supervisor
- 1 subscriber process (listen to Redis)
- 4-8 Celery worker processes

---

### 3. API Gateway
**Port**: 8000
**Purpose**: Single entry point for REST APIs
**Dependencies**: Auth, Storage, Analytics services

**Responsibilities:**
- Route requests to backend services
- Authenticate requests (JWT verification)
- Serve OpenAPI documentation
- Rate limiting
- CORS handling

**Scaling**: 3-10 instances (stateless)

**Endpoints:**
- `/api/auth/*` → Auth Service
- `/api/data/*` → Storage Service
- `/api/analytics/*` → Analytics Service
- `/docs` → OpenAPI spec

---

### 4. Socket Gateway
**Port**: 8002
**Purpose**: Real-time WebSocket streaming
**Dependencies**: Redis (pub/sub + message queue)

**Responsibilities:**
- Handle WebSocket connections
- Manage room-based subscriptions
- Broadcast enriched data to clients
- Coordinate across multiple instances (via Redis)

**Scaling**: 5-15 instances (connection-bound)

**Rooms:**
- `general` - Default room
- `product:{symbol}` - Per- product updates
- `chain:{symbol}` - Option chain updates

---

### 5. Storage Service
**Port**: 8003
**Purpose**: Data access layer (MongoDB wrapper)
**Dependencies**: MongoDB

**Responsibilities:**
- Provide REST API for data retrieval
- Manage MongoDB indexes
- Handle datetime serialization
- Implement Repository Pattern

**Scaling**: 2-5 instances (stateless)

**Endpoints:**
- `/data/underlying/:product`
- `/data/options/:symbol`
- `/data/chain/:product/:expiry`
- `/data/products`

---

### 6. Auth Service
**Port**: 8001
**Purpose**: Authentication  & authorization
**Dependencies**: MongoDB (user storage)

**Responsibilities:**
- User registration
- Login (JWT generation)
- Token verification
- Token refresh

**Scaling**: 2-5 instances (stateless)

**Endpoints:**
- `/auth/register`
- `/auth/login`
- `/auth/verify`
- `/auth/refresh`

---

### 7. Analytics Service
**Port**: 8004
**Purpose**: Advanced market analytics
**Dependencies**: MongoDB, Redis

**Responsibilities:**
- PCR trend analysis
- Volatility surface data
- Historical aggregations
- Max pain calculations across expiries

**Scaling**: 2-5 instances (compute-intensive)

**Endpoints:**
- `/analytics/pcr_trends/:product`
- `/analytics/volatility_surface/:product`

---

### 8. AI Analyst Service
**Port**: 8006
**Purpose**: AI-powered market insights
**Dependencies**: Redis (vector store), Analytics service, HuggingFace API

**Responsibilities:**
- Generate market pulse summaries (LLM)
- Sentiment analysis on news
- RAG-based Q&A chatbot

**Scaling**: 1-3 instances (LLM API calls)

**Endpoints:**
- `/ai/market_pulse/:product`
- `/ai/sentiment/:product`
- `/ai/ask` (RAG chatbot)

---

### 9. Logging Service
**Port**: 8005
**Purpose**: Centralized log aggregation
**Dependencies**: Redis (pub/sub for logs)

**Responsibilities:**
- Ingest logs from all services
- Store logs persistently
- Provide log query API
- Forward to ELK/Loki

**Scaling**: 1-2 instances

---

## 🔄 Communication Patterns

### 1. Synchronous (REST API)
```
API Gateway → Auth Service (token verification)
API Gateway → Storage Service (data queries)
AI Analyst → Analytics Service (fetch data)
```

**Pattern**: Request-response
**When to use**: Direct data retrieval, low latency requirements

---

### 2. Asynchronous (Pub/Sub)
```
Feed Generator → Redis → Worker Enricher
Worker Enricher → Redis → Socket Gateway
```

**Pattern**: Fire-and-forget events
**When to use**: Real-time data streaming, decoupled services

---

### 3. Task Queue (Celery)
```
Subscriber → Celery → Worker Processes
```

**Pattern**: Background job processing
**When to use**: CPU-intensive tasks, retry logic needed

---

## 🎯 Service Discovery

### Development (Docker Compose)
```yaml
# Services discover each other via service names
AUTH_SERVICE_URL: "http://auth:8001"
STORAGE_SERVICE_URL: "http://storage:8003"
```

Docker's internal DNS resolves service names to container IPs.

### Production (Kubernetes)
```yaml
# Kubernetes Services provide stable DNS names
AUTH_SERVICE_URL: "http://auth.deltastream.svc.cluster.local:8001"
```

Kubernetes DNS + Service objects provide service discovery.

---

## 📊 Service Dependencies

```
┌─────────────┐
│  API Gateway│
└──────┬──────┘
       │
   ┌───┴─────────────┬──────────┐
   │                 │          │
┌──▼───┐    ┌────────▼──┐   ┌──▼────────┐
│ Auth │    │  Storage  │   │ Analytics │
└──────┘    └─────┬─────┘   └──┬────────┘
                  │            │
             ┌────▼────────────▼────┐
             │      MongoDB         │
             └─────────────────────┘

┌──────────────┐      ┌───────────────┐
│     Feed     │─────▶│ Redis Pub/Sub │
│  Generator   │      └───────┬───────┘
└──────────────┘              │
                       ┌──────▼──────┐
                       │   Worker    │
                       │  Enricher   │
                       └──────┬──────┘
                              │
                    ┌─────────▼──────┬──────────┐
                    │                │          │
               ┌────▼────┐    ┌──────▼───┐  ┌──▼──────┐
               │ MongoDB │    │  Redis   │  │  Redis  │
               │         │    │  Cache   │  │ Pub/Sub │
               └─────────┘    └──────────┘  └────┬────┘
                                                  │
                                           ┌──────▼──────┐
                                           │   Socket    │
                                           │   Gateway   │
                                           └─────────────┘
```

---

## 🔧 Best Practices Implemented

### 1. Stateless Services
All services (except MongoDB/Redis) are stateless:
- Can scale horizontally
- No session storage
- Restart-safe

### 2. Health Checks
Every service exposes `/health`:
```python
@app.route('/health')
def health():
    return {'status': 'healthy', 'service': SERVICE_NAME}
```

### 3. Graceful Shutdown
Services handle SIGTERM for clean shutdown:
- Close database connections
- Finish in-flight requests
- Deregister from load balancer

### 4. Idempotency
All data processing is idempotent:
- Duplicate messages don't cause issues
- Redis keys track processed items
- MongoDB upserts prevent duplicates

### 5. Retry Logic
Celery tasks retry with exponential backoff:
- Network failures: Auto-retry
- DB unavailable: Retry with increasing delay
- Max retries: Send to DLQ

---

## 📚 Related Docs

- [System Design](system-design.md)
- [Data Flow](data-flow.md)
