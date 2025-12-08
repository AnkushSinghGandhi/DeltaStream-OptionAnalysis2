# Quick Start Guide

Get Option ARO running in 5 minutes!

## Prerequisites

- Docker & Docker Compose installed
- 4GB+ RAM available
- Ports 6379, 8000-8005, 27017 free

## Step 1: Start Services (1 minute)

```bash
# Clone repository
git clone <repo-url>
cd option-aro-clone

# Start all services
./scripts/start-local.sh

# Or using docker-compose
docker-compose up -d
```

Wait ~30 seconds for services to initialize.

## Step 2: Verify (30 seconds)

```bash
# Check health
curl http://localhost:8000/health

# Get products
curl http://localhost:8000/api/data/products
```

## Step 3: See Real-Time Data (30 seconds)

**Option A: Browser**
```bash
open examples/subscribe-example.html
```

Click "Subscribe to NIFTY" and watch live updates!

**Option B: Command Line**
```bash
cd examples
node subscribe-example.js
```

## Step 4: Explore API (2 minutes)

```bash
# Run all examples
./examples/curl-examples.sh

# Or try individual endpoints
curl "http://localhost:8000/api/data/underlying/NIFTY?limit=5"
curl "http://localhost:8000/api/analytics/pcr/NIFTY"
curl "http://localhost:8000/api/analytics/volatility-surface/NIFTY"
```

## What's Running?

- **Feed Generator**: Creating realistic market data
- **Worker**: Processing and enriching data
- **API Gateway**: REST API at http://localhost:8000
- **Socket Gateway**: WebSocket at http://localhost:8002
- **MongoDB**: Storing all data
- **Redis**: Caching & message broker

## View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f feed-generator
docker-compose logs -f worker-enricher
```

## Common Commands

```bash
# Stop services
./scripts/stop-local.sh

# Restart service
docker-compose restart worker-enricher

# Scale workers
docker-compose up -d --scale worker-enricher=5

# View MongoDB data
docker-compose exec mongodb mongosh option_aro
```

## Next Steps

- Read [README.md](README.md) for full documentation
- See [VERIFICATION.md](VERIFICATION.md) for comprehensive testing
- Check [API Documentation](http://localhost:8000/api/docs)
- Import [Postman Collection](examples/postman-collection.json)

## Troubleshooting

### Services not starting?
```bash
docker-compose logs <service-name>
```

### No data flowing?
```bash
docker-compose restart worker-enricher
docker-compose logs -f feed-generator
```

### Port already in use?
Edit `docker-compose.yml` to change port mappings.

## Clean Up

```bash
# Stop and remove everything
docker-compose down -v
```

---

**That's it! You now have a fully functional option trading analytics platform running locally.** 🚀
