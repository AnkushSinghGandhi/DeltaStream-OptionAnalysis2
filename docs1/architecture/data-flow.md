# Data Flow Through DeltaStream

> **Complete journey of data from generation to client**

## 📊 Overview

Data flows through DeltaStream in three primary pipelines:
1. **Real-time Data Pipeline**: Live market data streaming
2. **API Request Pipeline**: On-demand data retrieval
3. **AI Analytics Pipeline**: LLM-powered insights

---

## 🔄 Pipeline 1: Real-time Data Flow

### Step-by-Step Journey

```
┌──────────────────┐
│  1. GENERATION   │
│  Feed Generator  │
└────────┬─────────┘
         │ Publishes to Redis
         ▼
┌────────────────────────────┐
│ Redis Pub/Sub Channel      │
│ - market:underlying        │
│ - market:option_quote      │
│ - market:option_chain      │
└────────┬───────────────────┘
         │ Multiple subscribers
         ▼
┌─────────────────────┐
│  2. SUBSCRIPTION    │
│  Worker Subscriber  │
│  (Single process)   │
└────────┬────────────┘
         │ Dispatches to queue
         ▼
┌──────────────────────┐
│ Celery Task Queue    │
│ (Redis as broker)    │
└────────┬─────────────┘
         │ Workers pick tasks
         ▼
┌───────────────────────────────┐
│  3. PROCESSING                │
│  Celery Workers (4-8 process) │
│  - Calculate PCR              │
│  - Calculate max pain         │
│  - Compute OHLC               │
└────────┬──────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌───────────┐
│MongoDB│  │Redis Cache│
│ Store │  │  Update   │
└───┬───┘  └─────┬─────┘
    │            │
    └──────┬─────┘
           ▼
┌──────────────────────────┐
│ 4. ENRICHED PUBLISHING   │
│ Redis Pub/Sub            │
│ - enriched:option_chain  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────┐
│ 5. BROADCASTING      │
│ Socket Gateway       │
│ (Flask-SocketIO)     │
└──────────┬───────────┘
           │ WebSocket push
           ▼
┌──────────────────────┐
│ 6. CLIENT DISPLAY    │
│ Browser/Mobile App   │
└──────────────────────┘
```

### Timing & Latency

| Stage | Latency | Notes |
|-------|---------|-------|
| Feed generates | 0ms | Baseline |
| Redis pub/sub | +1-2ms | In-memory |
| Worker dispatch | +5ms | Queue overhead |
| Processing | +50-200ms | CPU-bound (PCR, max pain) |
| MongoDB insert | +10-30ms | Network + disk |
| Redis cache update | +1ms | In-memory |
| Publish enriched | +1ms | In-memory |
| Socket broadcast | +2-5ms | Network |
| **Total** | **70-250ms** | Generation → Client |

**Optimization opportunities:**
- Pre-compute common calculations
- Use Redis Streams for exactly-once delivery
- Connection pooling
- In-memory caching of recent data

---

## 📡 Pipeline 2: API Request Flow

### REST APi Request Path

```
┌─────────────┐
│   1. CLIENT │
│   Request   │
└──────┬──────┘
       │ HTTP GET /api/data/chain/NIFTY/2025-01-25
       ▼
┌──────────────────────┐
│  2. API GATEWAY      │
│  - Extract JWT       │
│  - Verify auth       │
│  - Route request     │
└──────┬───────────────┘
       │ Authenticated
       ▼
┌──────────────────────┐
│ 3 STORAGE SERVICE   │
│ - Parse params       │
│ - Check cache        │
└──────┬───────────────┘
       │
   ┌───▼───┐ Cache hit?
   │ Redis │─────────────────┐
   └───┬───┘                 │
       │ Miss                │ Hit
       ▼                     │
┌──────────────┐            │
│  4. MongoDB  │            │
│  - Query     │            │
│  - Fetch data│            │
└──────┬───────┘            │
       │                    │
       ▼                    │
┌──────────────┐            │
│ 5. UPDATE    │            │
│ Redis Cache  │            │
└──────┬───────┘            │
       │                    │
       └────────┬───────────┘
                ▼
       ┌────────────────┐
       │ 6. SERIALIZE   │
       │ JSON response  │
       └────────┬───────┘
                ▼
       ┌────────────────┐
       │ 7. RETURN      │
       │  to client     │
       └────────────────┘
```

### Cache Strategy (Cache-Aside)

**Fast Path (Cache Hit):**
```
Client → API Gateway → Storage → Redis → Response
Total: ~5-10ms
```

**Slow Path (Cache Miss):**
```
Client → API Gateway → Storage → Redis (miss)
  → MongoDB → Store in Redis → Response
Total: ~30-60ms
```

**Cache TTL Strategy:**
```python
# Latest data: 5-minute TTL
latest:underlying:{product}       # 300s
latest:chain:{product}:{expiry}   # 300s

# OHLC windows: Duration = TTL
ohlc:{product}:5m                 # 300s
ohlc:{product}:30m                # 1800s

# Idempotency tracking: 1-hour TTL
processed:{resource}:{id}         # 3600s
```

---

## 🤖 Pipeline 3: AI Analytics Flow

### RAG (Retrieval-Augmented Generation) Flow

```
┌────────────────┐
│ 1. USER QUERY  │
│ "How does PCR  │
│  calculation   │
│  work?"        │
└───────┬────────┘
        │
        ▼
┌────────────────────────┐
│ 2. VECTOR EMBEDDING    │
│ sentence-transformers  │
│ Convert query → vector │
└───────┬────────────────┘
        │
        ▼
┌──────────────────────────┐
│ 3. VECTOR SEARCH         │
│ Redis (vector similarity)│
│ Find top-k similar docs  │
└───────┬──────────────────┘
        │ Retrieved: README.md section on PCR
        ▼
┌─────────────────────────────┐
│ 4. CONTEXT ASSEMBLY         │
│ Combine: query + documents  │
└───────┬─────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│ 5. LLM GENERATION            │
│ HuggingFace FLAN-T5          │
│ Generate answer from context │
└───────┬──────────────────────┘
        │
        ▼
┌────────────────────────┐
│ 6. RESPONSE TO USER    │
│ "PCR is calculated..."  │
└────────────────────────┘
```

### Market Pulse Generation

```
┌─────────────────────┐
│ 1. FETCH ANALYTICS  │
│ GET /analytics/pcr  │
└──────────┬──────────┘
           │ {pcr: 1.15, max_pain: 21500, ...}
           ▼
┌──────────────────────────┐
│ 2. TEMPLATE PROMPT       │
│ "Summarize market with   │
│  PCR=1.15, max_pain=..."│
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 3. LLM INFERENCE         │
│ HuggingFace API call     │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 4. POST-PROCESS          │
│ Format, validate         │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 5. CACHE RESULT          │
│ Redis (1hr TTL)          │
└──────────┬───────────────┘
           │
           ▼
┌────────────────────────────┐
│ 6. RETURN TO CLIENT        │
│ "Markets show bearish..."  │
└────────────────────────────┘
```

---

## 🔄 Event-Driven Architecture

### Pub/Sub Channels

| Channel | Publisher | Subscriber(s) | Data |
|---------|-----------|---------------|------|
| `market:underlying` | Feed Generator | Worker | Raw underlying ticks |
| `market:option_quote` | Feed Generator | Worker | Individual option quotes |
| `market:option_chain` | Feed Generator | Worker | Complete option chains |
| `enriched:underlying` | Worker | Socket Gateway | Processed underlying |
| `enriched:option_chain` | Worker | Socket Gateway | Enriched chain + analytics |
| `logs:all` | All services | Logging Service | Structured logs |

### Benefits of Event-Driven

1. **Loose Coupling**: Services don't know about each other
2. **Scalability**: Add subscribers without changing publishers
3. **Resilience**: If subscriber down, messages buffered
4. **Flexibility**: Easy to add new data consumers

---

## 📈 Data Volume & Throughput

### Expected Load (Market Hours: 9:15 AM - 3:30 PM IST)

| Data Type | Frequency | Volume/Day |
|-----------|-----------|------------|
| Underlying ticks | Every 1s | ~23,000 ticks |
| Option quotes | Every 5s | ~4,600/quote |
| Option chains | Every 30s | ~768 chains |
| Enriched events | Every 30s | ~768 events |
| WebSocket messages | Continuous | ~200,000 |

### Scaling Thresholds

| Component | Current | Scale Up When | Max Capacity |
|-----------|---------|---------------|--------------|
| Workers | 4 | Queue > 100 | 20 workers |
| Socket Gateway | 2 | Connections > 500 | 15 instances |
| API Gateway | 3 | RPS > 100 | 10 instances |
| MongoDB | 1 | Writes > 1000/s | Sharding |
| Redis | 1 | Memory > 80% | 16GB → 32GB |

---

## 🎯 Data Consistency

### Eventual Consistency Model

```
Feed → Worker (Process) → MongoDB (Persist)
                        → Redis (Cache)
                        → Publish (WebSocket)
```

**Timeline:**
- t=0: Feed publishes
- t=50ms: Worker processes
- t=60ms: MongoDB persisted
- t=61ms: Redis updated
- t=70ms: Clients receive

**Implications:**
- API might return old data for 60-70ms
- Acceptable for trading analytics (not order execution)
- Cache invalidation handles staleness

---

## 📚 Related Docs

- [System Design](system-design.md)
- [Microservices](microservices.md)
