# System Design - DeltaStream

> **High-level architecture and design decisions**

## 📐 Architecture Overview

DeltaStream follows a **microservices architecture** with **event-driven communication** for real-time options trading analytics.

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│              (Web Dashboard, Mobile App, APIs)               │
└──────────────────┬────────────────────┬─────────────────────┘
                   │                    │
          ┌────────▼─────────┐   ┌─────▼──────────┐
          │   API Gateway    │   │ Socket Gateway │
          │   (Port 8000)    │   │  (Port 8002)   │
          └────────┬─────────┘   └─────┬──────────┘
                   │                   │
        ┌──────────┴──────────┬────────┴────────┐
        │                     │                  │
    ┌───▼────┐        ┌───────▼──────┐   ┌──────▼─────┐
    │  Auth  │        │   Storage    │   │ Analytics  │
    │ (8001) │        │    (8003)    │   │   (8004)   │
    └────────┘        └───────┬──────┘   └──────┬─────┘
                              │                  │
                    ┌─────────▼──────────────────▼─────────┐
                    │         MongoDB (Persistence)         │
                    └───────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Event Processing Layer                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌────────────┐│
│  │     Feed     │─────▶│ Redis Pub/Sub│─────▶│   Worker   ││
│  │  Generator   │      │  (Channels)  │      │  Enricher  ││
│  └──────────────┘      └──────────────┘      │  (Celery)  ││
│                               ▲               └─────┬──────┘│
│                               │                     │        │
│                               └─────────────────────┘        │
│                         (Publishes enriched data)            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
├─────────────────────────────────────────────────────────────┤
│  Redis: Cache + Pub/Sub + Celery Broker + Vector Store      │
│  MongoDB: Persistent storage for all market data            │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Design Principles

### 1. **Separation of Concerns**
Each service has a single, well-defined responsibility:
- **Feed Generator**: Data ingestion
- **Worker**: Data processing
- **Storage**: Data persistence
- **API Gateway**: Request routing
- **Auth**: Authentication

### 2. **Event-Driven Architecture**
- Services communicate via events (Redis Pub/Sub)
- Loose coupling between services
- Asynchronous processing

### 3. **Horizontal Scalability**
- All services are stateless (except storage)
- Can scale services independently
- Load balancing via Kubernetes

### 4. **Fault Tolerance**
- Retry logic with exponential backoff
- Dead letter queues for failed messages
- Health checks on all services
- Graceful degradation

### 5. **Observability**
- Structured JSON logging
- Prometheus metrics on all services
- Distributed tracing capability

## 📊 Data Flow

### Real-time Data Pipeline

```
1. Feed Generator → Redis Pub/Sub (market:underlying)
       ↓
2. Worker subscribes → Processes data
       ↓
3. Stores in MongoDB
       ↓
4. Updates Redis cache
       ↓
5. Publishes to enriched channel → Redis Pub/Sub
       ↓
6. Socket Gateway broadcasts → WebSocket clients
```

### API Request Flow

```
1. Client → API Gateway (HTTP)
       ↓
2. Gateway authenticates → Auth Service
       ↓
3. Gateway routes → Storage/Analytics Service
       ↓
4. Service checks cache → Redis (fast path)
       ↓
5. Cache miss → Query MongoDB (slow path)
       ↓
6. Update cache → Return response
```

## 🔧 Technology Stack

### Backend Services
- **Language**: Python 3.10+
- **Framework**: Flask (REST), Flask-SocketIO (WebSocket)
- **Task Queue**: Celery

### Data Layer
- **Cache**: Redis (in-memory)
- **Database**: MongoDB (document store)
- **Broker**: Redis (Celery tasks + Pub/Sub)

### Infrastructure
- **Containers**: Docker
- **Orchestration**: Kubernetes
- **Process Management**: Supervisor (Worker Enricher)

### Observability
- **Logging**: structlog (JSON)
- **Metrics**: Prometheus
- **Visualization**: Grafana
- **Log Aggregation**: Loki

### AI/ML
- **Framework**: LangChain
- **Models**: HuggingFace (FLAN-T5, MiniLM)
- **Vector Store**: Redis

## 🚀 Deployment Architecture

### Development (Docker Compose)
```
All services run locally in containers
- Single Docker network
- Shared volumes for data
- Port mapping to localhost
```

### Production (Kubernetes)
```
Multiple pods per service
- LoadBalancer for ingress
- HPA for auto-scaling
- Persistent volumes for data
- ConfigMaps for configuration
- Secrets for credentials
```

## 🎨 Design Patterns

1. **API Gateway Pattern**: Single entry point for all clients
2. **Repository Pattern**: Data access abstraction (Storage Service)
3. **Pub/Sub Pattern**: Event-driven communication
4. **Cache-Aside Pattern**: Application-managed caching
5. **Circuit Breaker**: (Future) Fault tolerance
6. **CQRS**: Separate read/write paths (implicit)

## 📈 Scalability Considerations

### Horizontal Scaling
- **API Gateway**: 3-10 instances (based on traffic)
- **Worker Enricher**: 2-20 instances (based on data volume)
- **Socket Gateway**: 5-15 instances (based on WebSocket connections)

### Vertical Scaling
- **MongoDB**: Increased RAM for working set
- **Redis**: Increased memory for cache size

### Bottlenecks
- **MongoDB writes**: Use sharding for high volume
- **Redis memory**: Implement eviction policies
- **Worker queue**: Monitor queue length, scale workers

## 🔐 Security

- JWT-based stateless authentication
- bcrypt password hashing
- CORS configuration
- Rate limiting (API Gateway)
- Secret management (Kubernetes Secrets)

## 📚 Related Docs

- [Microservices Details](microservices.md)
- [Data Flow Deep Dive](data-flow.md)
- [Tech Stack Details](tech-stack.md)
