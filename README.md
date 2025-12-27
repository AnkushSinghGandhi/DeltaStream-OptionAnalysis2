# deltastream - Option Analysis

A production-grade, microservices-based option trading analytics platform with real-time data processing, WebSocket streaming, and comprehensive market analysis.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Features

- **Real-Time Market Data**: Live option quotes, underlying prices, and option chains
- **Advanced Analytics**: PCR, Implied Volatility Surface, Max Pain, OI Build-up
- **WebSocket Streaming**: Real-time updates via Socket.IO with room-based subscriptions
- **Microservices Architecture**: Scalable, independent services
- **Production Ready**: Docker, Kubernetes manifests, CI/CD, monitoring
- **Comprehensive API**: RESTful APIs with OpenAPI documentation
- **Data Processing Pipeline**: Celery workers with retry logic and DLQ
- **Caching Layer**: Redis cache-aside pattern with TTL and invalidation

## 📋 Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Services](#services)
- [Data Flow](#data-flow)
- [API Documentation](#api-documentation)
- [WebSocket API](#websocket-api)
- [Deployment](#deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🏗️ Architecture

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
         │                                                 │
         │                                                 ▼
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

### Microservices

1. **Feed Generator**: Generates realistic synthetic option market data
2. **Worker Enricher**: Processes and enriches raw data (Celery workers)
3. **Socket Gateway**: WebSocket server for real-time streaming
4. **API Gateway**: Central REST API routing and authentication
5. **Storage Service**: MongoDB data access layer
6. **Auth Service**: JWT-based authentication
7. **Analytics Service**: Aggregation and analysis endpoints
8. **Logging Service**: Centralized logging and log forwarding

## ⚡ Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM
- Ports available: 6379, 8000-8005, 27017

### Start All Services

```bash
# Clone repository
git clone <repo-url>
cd deltastream-option-analysis

# Start services
./scripts/start-local.sh

# Or using docker-compose directly
docker-compose up -d

# View logs
docker-compose logs -f
```

### Verify Services

```bash
# Check health
curl http://localhost:8000/health

# Get products
curl http://localhost:8000/api/data/products

# Run API examples
./examples/curl-examples.sh
```

### Test WebSocket Connection

**Browser:**
```bash
# Open in browser
open examples/subscribe-example.html
```

**Node.js:**
```bash
# Install socket.io-client
npm install -g socket.io-client

# Run example
node examples/subscribe-example.js
```

## 📦 Services

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | REST API entry point |
| Auth | 8001 | Authentication |
| Socket Gateway | 8002 | WebSocket server |
| Storage | 8003 | Data access |
| Analytics | 8004 | Analysis endpoints |
| Logging | 8005 | Log ingestion |
| Redis | 6379 | Cache & message broker |
| MongoDB | 27017 | Database |

### Service Details

Each service has its own README with detailed documentation:
- [Feed Generator](services/feed-generator/README.md)
- [Worker Enricher](services/worker-enricher/README.md)
- [Socket Gateway](services/socket-gateway/README.md)
- [API Gateway](services/api-gateway/README.md)
- [Storage Service](services/storage/README.md)
- [Auth Service](services/auth/README.md)
- [Analytics Service](services/analytics/README.md)
- [Logging Service](services/logging-service/README.md)

## 🔄 Data Flow

### Market Data Pipeline

```
1. Feed Generator
   ↓ publishes to Redis pub/sub (market:underlying, market:option_chain)
2. Worker Enricher (Subscriber)
   ↓ dispatches Celery tasks
3. Celery Workers
   ↓ process, calculate metrics
4. MongoDB (persistence) + Redis (cache)
   ↓ publishes enriched data
5. Socket Gateway
   ↓ broadcasts to WebSocket clients
6. Clients (receive real-time updates)
```

### Example: Option Chain Flow

1. **Feed Generator** creates option chain with 21 strikes (calls + puts)
2. **Worker** receives chain, calculates:
   - PCR (Put-Call Ratio)
   - Max Pain strike
   - ATM Straddle price
   - OI build-up analysis
3. **Storage** persists enriched chain to MongoDB
4. **Cache** updates Redis with latest values (5min TTL)
5. **Socket** broadcasts to subscribed clients
6. **API** serves historical data on demand

## 📖 API Documentation

### Base URL
```
http://localhost:8000
```

### OpenAPI Specification
```bash
curl http://localhost:8000/api/docs
```

### Authentication Endpoints

#### Register User
```bash
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}

Response: {token, user}
```

#### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response: {token, user}
```

### Data Endpoints

#### Get Products
```bash
GET /api/data/products

Response: {products: ["NIFTY", "BANKNIFTY", ...]}
```

#### Get Underlying Ticks
```bash
GET /api/data/underlying/NIFTY?limit=10

Response: {product, count, ticks: [...]}
```

#### Get Option Chain
```bash
GET /api/data/chain/NIFTY?expiry=2025-01-25&limit=1

Response: {product, count, chains: [...]}
```

### Analytics Endpoints

#### PCR Analysis
```bash
GET /api/analytics/pcr/NIFTY?history=true

Response: {product, latest: {...}, history: [...]}
```

#### Volatility Surface
```bash
GET /api/analytics/volatility-surface/NIFTY

Response: {product, expiries: [{expiry, strikes, ivs, ...}]}
```

#### Max Pain
```bash
GET /api/analytics/max-pain/NIFTY?expiry=2025-01-25

Response: {product, max_pain_strike, distance_from_spot, ...}
```

## 🔌 WebSocket API

### Connection
```javascript
const socket = io('http://localhost:8002');
```

### Events

#### Client → Server

**Subscribe to Product**
```javascript
socket.emit('subscribe', {type: 'product', symbol: 'NIFTY'});
```

**Subscribe to Chain**
```javascript
socket.emit('subscribe', {type: 'chain', symbol: 'NIFTY'});
```

**Get Products**
```javascript
socket.emit('get_products');
```

#### Server → Client

**Underlying Update**
```javascript
socket.on('underlying_update', (data) => {
  // {product, price, timestamp}
});
```

**Chain Summary**
```javascript
socket.on('chain_summary', (data) => {
  // {product, expiry, spot_price, pcr_oi, atm_straddle_price}
});
```

**Full Chain Update**
```javascript
socket.on('chain_update', (data) => {
  // {product, expiry, calls: [...], puts: [...], ...}
});
```

### Rooms

- `general`: Auto-joined, receives all updates
- `product:NIFTY`: Product-specific underlying updates
- `chain:NIFTY`: Product-specific chain updates

## 🚢 Deployment

### Docker Compose (Local/Dev)

```bash
# Start
docker-compose up -d

# Scale workers
docker-compose up -d --scale worker-enricher=3

# Stop
docker-compose down
```

### Kubernetes (Production)

```bash
# Apply manifests
kubectl apply -f k8s/

# Scale deployment
kubectl scale deployment worker-enricher --replicas=5

# Check status
kubectl get pods
```

### Environment Variables

Create `.env` file or set environment variables:

```bash
# Redis
REDIS_URL=redis://redis:6379/0

# MongoDB
MONGO_URL=mongodb://mongodb:27017/deltastream

# JWT Secret (change in production!)
JWT_SECRET=your-secret-key-change-in-production

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

## 📊 Monitoring & Observability

### Structured Logging

All services emit structured JSON logs:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "worker-enricher",
  "level": "info",
  "event": "processed_option_chain",
  "product": "NIFTY",
  "pcr": 1.0234
}
```

### Log Forwarding

**To Loki (Grafana):**
```bash
# See observability/promtail-config.yaml
promtail -config.file=observability/promtail-config.yaml
```

**To Elasticsearch:**
```bash
# See observability/filebeat.yml
filebeat -e -c observability/filebeat.yml
```

### Metrics

Each service exposes `/health` and `/metrics` endpoints:

```bash
curl http://localhost:8002/metrics
```

### Prometheus

```bash
# Add to prometheus.yml
scrape_configs:
  - job_name: 'deltastream'
    static_configs:
      - targets:
        - 'api-gateway:8000'
        - 'socket-gateway:8002'
        - 'analytics:8004'
```

## 🛠️ Development

### Project Structure

```
deltastream-option-analysis/
├── services/           # Microservices
│   ├── api-gateway/
│   ├── auth/
│   ├── feed-generator/
│   ├── worker-enricher/
│   ├── socket-gateway/
│   ├── storage/
│   ├── analytics/
│   └── logging-service/
├── scripts/            # Utility scripts
├── examples/           # Client examples
├── tests/              # Tests
├── k8s/                # Kubernetes manifests
├── observability/      # Monitoring configs
├── docker-compose.yml
├── Makefile
└── README.md
```

### Local Development

```bash
# Install dependencies for a service
cd services/api-gateway
pip install -r requirements.txt

# Run service locally
export REDIS_URL=redis://localhost:6379/0
python app.py

# Run tests
pytest tests/
```

### Make Commands

```bash
make help           # Show available commands
make build          # Build Docker images
make up             # Start services
make down           # Stop services
make logs           # View logs
make test           # Run tests
make lint           # Run linters
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific service tests
pytest tests/test_worker.py -v

# With coverage
pytest tests/ --cov=services --cov-report=html
```

### Integration Tests

```bash
# Start services
docker-compose up -d

# Run integration tests
pytest tests/integration/ -v
```

### Manual Testing

```bash
# Test feed generation
docker-compose logs -f feed-generator

# Test WebSocket connection
node examples/subscribe-example.js

# Test REST API
./examples/curl-examples.sh
```

## 🔧 Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs <service-name>

# Check health
curl http://localhost:8000/health

# Restart service
docker-compose restart <service-name>
```

### No Data Flowing

```bash
# Check Redis pub/sub
redis-cli SUBSCRIBE market:underlying

# Check MongoDB
mongosh deltastream --eval "db.underlying_ticks.countDocuments()"

# Check worker status
docker-compose logs worker-enricher
```

### WebSocket Not Connecting

```bash
# Check socket gateway logs
docker-compose logs socket-gateway

# Check Redis connection
redis-cli ping

# Test with curl
curl http://localhost:8002/health
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Reduce worker concurrency
# Edit docker-compose.yml: CELERY_WORKER_CONCURRENCY=2

# Scale down
docker-compose up -d --scale worker-enricher=1
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Flask & Flask-SocketIO for web framework
- Celery for distributed task processing
- Redis for caching and message broker
- MongoDB for data persistence
- Socket.IO for real-time communication

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- See service-specific READMEs

---

**Built with ❤️ for option traders and developers**
