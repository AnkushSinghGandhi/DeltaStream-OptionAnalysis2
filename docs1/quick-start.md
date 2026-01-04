# Quick Start Guide

Welcome to DeltaStream! This guide will help you get started quickly.

## Prerequisites

- Docker & Docker Compose
- Git
- 8GB RAM minimum
- Python 3.10+ (for local development)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/deltastream.git
cd deltastream
```

### 2. Start All Services

```bash
# Build and start all services
make build
make up

# Or using docker-compose directly
docker-compose up -d
```

### 3. Verify Services

```bash
# Check all services are running
docker-compose ps

# View logs
make logs
```

### 4. Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| **API Gateway** | http://localhost:8000 | REST API |
| **Dashboard** | http://localhost:3000 | Web UI |
| **Socket Gateway** | http://localhost:8002 | WebSocket |
| **Documentation** | http://localhost:8080 | This site! |

### 5. Test the System

```bash
# Get products
curl http://localhost:8000/api/data/products

# Get option chain
curl http://localhost:8000/api/data/chain/NIFTY

# Check WebSocket
# Open browser console at http://localhost:3000
```

## Next Steps

- **[Complete Tutorial](tutorials/complete-guide/README.md)** - Build from scratch
- **[API Reference](api-reference/README.md)** - API documentation
- **[Architecture](architecture/system-design.md)** - System design details

## Common Issues

### Services Won't Start

```bash
# Check Docker is running
docker --version

# Clean and rebuild
make clean
make build
make up
```

### Port Conflicts

If ports 8000, 8002, 3000 are in use:

```bash
# Stop conflicting services or edit docker-compose.yml
# Change port mappings: "8001:8000" instead of "8000:8000"
```

### MongoDB Connection Failed

```bash
# Ensure MongoDB is healthy
docker-compose logs mongodb

# Restart MongoDB
docker-compose restart mongodb
```

## Development Mode

### Run Individual Service

```bash
cd services/api-gateway
pip install -r requirements.txt
python app.py
```

### Run Tests

```bash
# All tests
make test

# Specific service
cd services/worker-enricher
pytest tests/ -v
```

## Documentation Site

```bash
cd docs-site
python3 serve.py
# Open http://localhost:8080
```

## Getting Help

- **GitHub Issues**: Report bugs
- **Documentation**: You're reading it!
- **Tutorial**: Step-by-step guide

Ready to dive deeper? Start with the [Complete Tutorial](tutorials/complete-guide/README.md)!
