# Technology Stack

> **Complete inventory of technologies and frameworks**

## 🐍 Backend / Core

### Programming Language
- **Python 3.10+**
  - Type hints for code clarity
  - Async/await support (future)
  - Rich standard library

### Web Frameworks
- **Flask 2.3+**
  - Lightweight WSGI framework
  - RESTful API development
  - Easy to extend with blueprints

- **Flask-SocketIO 5.3+**
  - WebSocket support
  - Room-based broadcasting
  - Redis message queue integration

### Task Queue
- **Celery 5.3+**
  - Distributed task processing
  - Retry logic & DLQ
  - Multiple worker processes
  - Beat scheduler for periodic tasks

--- ##  💾 Data Layer

### Database
- **MongoDB 6.0+**
  - Document-oriented storage
  - Flexible schema
  - Compound indexes
  - Aggregation pipeline

**Why MongoDB:**
- Semi-structured option chain data
- Fast writes for market data
- Easy horizontal scaling
- Rich query language

### Cache / Message Broker
- **Redis 7.0+**
  - In-memory data store
  - Pub/Sub messaging
  - Celery broker & result backend
  - Vector store (Redis Stack)
  - Sorted sets for time-series

**Redis Usage:**
- Cache: Latest prices, chains
- Pub/Sub: Event streaming
- Queue: Celerybroker
- Vectors: RAG embeddings

---

## 🔌 APIs & Communication

### REST API
- **Flask-RESTX** / **plain Flask**
  - Swagger/OpenAPI documentation
  - Request validation
  - Response serialization

### WebSocket
- **Flask-SocketIO**
  - Real-time bidirectional communication
  - Socket.IO protocol
  - Fallback to long-polling

### Messaging
- **Redis Pub/Sub**
  - Event-driven architecture
  - Pattern-based subscriptions
  - Fire-and-forget messaging

---

## 🤖 AI / Machine Learning

### LLM Framework
- **LangChain 0.1+**
  - LLM abstraction layer
  - RAG implementation
  - Prompt templates
  - Chain composition

### Models
- **HuggingFace Transformers**
  - FLAN-T5-Large (text generation)
  - all-MiniLM-L6-v2 (embeddings)
  - Inference via HuggingFace API

### Vector Operations
- **sentence-transformers**
  - Semantic embeddings
  - Cosine similarity

**Why these models:**
- Open-source & free
- Good quality for analytics summaries
- API-based (no GPU needed locally)

---

## 🐳 DevOps / Infrastructure

### Containerization
- **Docker 24+**
  - Application containers
  - Multi-stage builds
  - Layer caching

- **Docker Compose 2.2+**
  - Local orchestration
  - Service dependencies
  - Volume mapping

### Orchestration
- **Kubernetes 1.28+**
  - Production deployment
  - Auto-scaling (HPA)
  - Rolling updates
  - Service discovery

### Process Management
- **Supervisor 4.2+**
  - Multi-process management
  - Auto-restart on crash
  - Worker Enricher (subscriber + Celery workers)

---

## 📊 Observability

### Logging
- **structlog 23.1+**
  - Structured JSON logging
  - Contextual loggers
  - Processors pipeline

### Metrics
- **Prometheus Client**
  - Counter, Gauge, Histogram
  - /metrics endpoint
  - Time-series data

### Visualization
- **Grafana**
  - Dashboards for metrics
  - Prometheus data source
  - Alerting rules

### Log Aggregation
- **Loki** (recommended)
  - Grafana Labs log aggregation
  - Label-based querying
  - Cost-effective

- **ELK Stack** (alternative)
  - Elasticsearch + Logstash + Kibana
  - Powerful search
  - Resource-intensive

---

## 🔐 Security

### Authentication
- **PyJWT 2.8+**
  - JSON Web Tokens
  - HS256 algorithm
  - Token expiration

### Password Hashing
- **bcrypt 4.1+**
  - Salted password hashing
  - Configurable work factor
  - Brute-force resistant

### CORS
- **Flask-CORS 4.0+**
  - Cross-origin resource sharing
  - Configurable origins

---

## 🧪 Testing

### Unit Testing
- **pytest 7.4+**
  - Test discovery
  - Fixtures
  - Parametrize

### Mocking
- **unittest.mock** (stdlib)
  - Mock external dependencies
  - Patch functions

### Integration Testing
- **pytest-flask**
  - Flask app testing
  - Context handling

###Load Testing
- **Locust** (optional)
  - Performance testing
  - WebSocket support

---

## 📦 Key Python Libraries

### Core Dependencies
```python
# Web
Flask==2.3.0
Flask-SocketIO==5.3.0
Flask-CORS==4.0.0

# Data
pymongo==4.6.0
redis==5.0.1

# Task Queue
celery==5.3.4

# Auth
PyJWT==2.8.0
bcrypt==4.1.2

# AI/ML
langchain==0.1.0
transformers==4.36.0
sentence-transformers==2.2.2
huggingface-hub==0.20.0

# Logging
structlog==23.1.0

# HTTP
requests==2.31.0

# Utilities
python-dotenv==1.0.0
feedparser==6.0.10  # For news RSS
```

---

## 🎨 Frontend (Optional - Not in Tutorial)

### Framework
- **React 18+**
  - Component-based UI
  - Hooks (useState, useEffect)
  - Context API

### State Management
- **Redux Toolkit** or **Zustand**
  - Global state
  - WebSocket data management

### WebSocket Client
- **Socket.IO Client**
  - Real-time updates
  - Automatic reconnection

### Charts
- **Recharts** or **Chart.js**
  - Option chain visualization
  - PCR trends
  - Volatility surface

---

## 📚 Development Tools

### Code Quality
- **Black** - Code formatting
- **Flake8** - Linting
- **mypy** - Type checking

### API Documentation
- **OpenAPI** / **Swagger**
  - Auto-generated docs
  - Interactive API explorer

### Version Control
- **Git**
  - Branch strategy: main & feature branches
  - Commit conventions

---

## 🌐 External Services

### LLM API
- **HuggingFace Inference API**
  - Serverless LLM inference
  - Free tier available
  - text-generation endpoint

### News Data (Optional)
- **Yahoo Finance RSS**
  - Free news feeds
  - Market sentiment data

---

## 🔄 Versioning Strategy

| Component | Version | Update Policy |
|-----------|---------|---------------|
| Python | 3.10+ | Minor updates OK |
| Flask | 2.3+ | Patch updates only |
| MongoDB | 6.0+ | Major version stable |
| Redis | 7.0+ | Patch updates safe |
| Kubernetes | 1.28+ | Follow cluster version |

---

## 📈 Performance Characteristics

| Technology | Latency | Throughput | Notes |
|------------|---------|------------|-------|
| Redis GET | <1ms | 100k+ ops/s | In-memory |
| MongoDB Query | 10-50ms | 10k ops/s | With index |
| Celery Task | 50-200ms | 1k tasks/s | CPU-bound |
| WebSocket Message | 2-10ms | 50k msgs/s | Network-bound |
| LLM API Call | 1-5s | 10 req/min | External API |

---

## 🎯 Technology Choices - Rationale

**Why Flask over FastAPI?**
- Mature ecosystem
- Extensive SocketIO support
- Team familiarity

**Why MongoDB over PostgreSQL?**
- Flexible schema for option chains
- Fast writes for market data
- Easier horizontal scaling

**Why Celery over RQ?**
- More features (retry, DLQ, beat)
- Production-tested at scale
- Better monitoring tools

**Why HuggingFace over OpenAI?**
- Cost (free tier)
- Privacy (data not used for training)
- Open-source models

---

## 📚 Related Docs

- [System Design](system-design.md)
- [Setup Guide](../development/setup.md)
