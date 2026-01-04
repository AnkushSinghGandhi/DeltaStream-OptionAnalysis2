# Local Development Setup

> **Step-by-step guide to get DeltaStream running locally**

## Prerequisites

### Required Software
- **Docker Desktop** (includes Docker Compose)
  - Mac: https://docs.docker.com/desktop/install/mac-install/
  - Linux: https://docs.docker.com/desktop/install/linux-install/
- **Python 3.10+**
- **Git**

### Recommended Tools
- **VS Code** or **PyCharm**
- **Postman** (API testing)
- **MongoDB Compass** (database GUI)
- **Redis Insight** (Redis GUI)

---

## Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/deltastream.git
cd deltastream
```

---

## Step 2: Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env file
vim .env
```

**Required variables**:
```bash
# HuggingFace API (for AI features)
HUGGINGFACE_API_TOKEN=hf_xxxxxxxxxxxxx

# Optional: Override defaults
MONGO_URI=mongodb://mongo:27017/deltastream
REDIS_URL=redis://redis:6379
```

**Get HuggingFace token**:
1. Sign up at https://huggingface.co/
2. Go to https://huggingface.co/settings/tokens
3. Create new token
4. Copy to `.env`

---

## Step 3: Build Services

```bash
# Build all Docker images
make build

# Or manually
docker-compose build
```

This will:
- Build 10 service images
- Install Python dependencies
- Create containers

**Expected time**: 5-10 minutes (first time)

---

## Step 4: Start Services

```bash
# Start all services in background
make up

# Or manually
docker-compose up -d
```

**Services started**:
- MongoDB (port 27017)
- Redis (port 6379)
- API Gateway (port 8000)
- Auth Service (port 8001)
- Socket Gateway (port 8002)
- Storage Service (port 8003)
- Analytics (port 8004)
- Logging (port 8005)
- AI Analyst (port 8006)
- Feed Generator (background)
- Worker Enricher (background)

---

## Step 5: Verify Installation

```bash
# Check all services are running
docker-compose ps

# Should show all services as "Up"

# Test API
curl http://localhost:8000/health

# Expected: {"status": "healthy"}
```

---

## Step 6: View Logs

```bash
# All services
make logs

# Specific service
make logs-api
make logs-worker

# Follow logs (Ctrl+C to stop)
docker-compose logs -f worker-enricher
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Services Not Starting
```bash
# Check logs
docker-compose logs <service-name>

# Restart specific service
docker-compose restart <service-name>

# Full reset
make down
make clean
make up
```

### MongoDB Connection Issues
```bash
# Verify MongoDB is running
docker-compose ps mongodb

# Access MongoDB shell
make shell-mongo
```

---

## Development Workflow

### 1. Make Code Changes
```bash
# Edit service code
vim services/api-gateway/app.py
```

### 2. Restart Service
```bash
# Rebuild and restart
docker-compose up -d --build api-gateway

# Or use Makefile
make restart
```

### 3. Test Changes
```bash
curl http://localhost:8000/api/data/products
```

---

## IDE Setup

### VS Code
```bash
# Install Python extension
code --install-extension ms-python.python

# Open project
code .
```

**Recommended settings** (`.vscode/settings.json`):
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true
}
```

### PyCharm
1. Open project folder
2. Configure Python interpreter → Docker Compose
3. Enable Docker integration

---

## Next Steps

- [Run Tests](testing.md)
- [Use Makefile Commands](makefile-guide.md)
- [Start Contributing](contributing.md)

---

**You're ready to develop!** 🚀
