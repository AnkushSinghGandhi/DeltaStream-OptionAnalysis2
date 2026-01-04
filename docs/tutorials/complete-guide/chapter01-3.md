### 1.6 Project Structure

Let's set up the directory structure:

```
deltastream-option-analysis/
├── services/                   # All microservices
│   ├── feed-generator/         # Data generation service
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── worker-enricher/        # Celery workers
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── supervisord.conf   # Runs subscriber + Celery worker
│   ├── auth/                   # Authentication service
│   ├── api-gateway/            # REST API gateway
│   ├── storage/                # MongoDB wrapper
│   ├── analytics/              # Analytics computations
│   ├── socket-gateway/         # WebSocket server
│   └── logging-service/        # Centralized logging
├── docker-compose.yml          # Orchestrates all services
├── .env.example                # Environment variables template
├── Makefile                    # Development shortcuts
├── README.md                   # Project documentation
└── tests/                      # Integration tests
    ├── conftest.py
    └── test_integration.py
```

**Why this structure?**

1. **Service isolation**: Each service is self-contained (can run independently)
2. **Docker-first**: Each service has its own Dockerfile
3. **Monorepo**: All services in one repository (easier for small teams)
4. **Shared nothing**: No shared code between services (enforces decoupling)

**Alternative: Polyrepo** (one git repo per service)
- **Pro**: True independence, separate CI/CD, different teams
- **Con**: Harder to coordinate changes, more overhead

For DeltaStream, **monorepo** is the right choice (single team, coordinated releases).

---

### 1.7 Setting Up the Development Environment

Now let's set up your development environment step by step.

---

#### Step 1.1: Install Prerequisites

Before starting, ensure you have these tools installed:

**Install Docker Desktop** (includes Docker + Docker Compose):
- Mac: `brew install --cask docker`
- Windows: Download from docker.com
- Linux: `sudo apt-get install docker.io docker-compose`

**Install Python 3.9+** (for local development):
- Mac: `brew install python@3.9`
- Windows: Download from python.org
- Linux: `sudo apt-get install python3.9`

**Install Git**:
- Mac: `brew install git`
- Linux: `sudo apt-get install git`

**Install a code editor** (VS Code recommended)

**Verify installations:**
```bash
docker --version          # Should show Docker version 20+
python3 --version         # Should show Python 3.9+
git --version            # Should show Git version 2+
```

---

#### Step 1.2: Create the Project Directory

**Action:** Create and initialize your project directory:

```bash
# Create project directory
mkdir deltastream-option-analysis
cd deltastream-option-analysis

# Initialize git
git init
```

**Verify:** You should now be in the `deltastream-option-analysis` directory and see the message "Initialized empty Git repository".

---

#### Step 1.3: Create .gitignore File

**Action:** Create a `.gitignore` file to exclude generated files from version control:

```bash
cat <<EOF > .gitignore
__pycache__/
*.pyc
*.pyo
.env
*.log
.pytest_cache/
.DS_Store
logs/
EOF
```

**What's happening:**
- `__pycache__/`, `*.pyc`, `*.pyo`: Python bytecode (auto-generated, shouldn't be versioned)
- `.env`: Environment variables with secrets (NEVER commit to git)
- `*.log`: Log files (generated at runtime)
- `.pytest_cache/`: Test cache (auto-generated)

**Verify:** Run `ls -a` and you should see `.gitignore` in the directory.

---

#### Step 1.4: Create Environment Variables Template

**Action:** Create `.env.example` as a template for required environment variables:

```bash
cat <<EOF > .env.example
# Redis
REDIS_URL=redis://redis:6379/0

# MongoDB
MONGO_URL=mongodb://mongodb:27017/deltastream

# JWT Secret (change in production!)
JWT_SECRET=your-secret-key-change-in-production

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
EOF
```

**Non-trivial concept - Why `.env.example` instead of `.env`?**
- `.env` contains actual secrets (API keys, passwords) → NEVER commit to git
- `.env.example` shows what variables are needed → ALWAYS commit to git
- Team workflow:
  1. New developer clones repository
  2. Runs: `cp .env.example .env`
  3. Fills in their own secret values
  4. Their `.env` stays local (protected by `.gitignore`)

**Verify:** The file `.env.example` should exist. Later you'll copy it to create your actual `.env`.

---

#### Step 1.5: Create the Directory Structure

**Action:** Create all service directories:

```bash
# Create service directories
mkdir -p services/{feed-generator,worker-enricher,auth,api-gateway,storage,analytics,socket-gateway,logging-service}

# Create test directory
mkdir -p tests

# Create other directories
mkdir -p examples scripts k8s observability
```

**Non-trivial concept - Brace expansion:**
The syntax `{a,b,c}` creates multiple directories:
- `mkdir -p services/{feed-generator,worker-enricher}` 
- Expands to: `mkdir -p services/feed-generator services/worker-enricher`

**Verify:** Run `tree -L 2` (or `find . -type d`) to see the directory structure:
```
.
├── services/
│   ├── feed-generator/
│   ├── worker-enricher/
│   ├── auth/
│   ├── api-gateway/
│   ├── storage/
│   ├── analytics/
│   ├── socket-gateway/
│   └── logging-service/
├── tests/
├── examples/
├── scripts/
├── k8s/
└── observability/
```

---

#### Step 1.6: Create the Docker Compose Foundation

**Action:** Create `docker-compose.yml` to orchestrate infrastructure services. We'll add application services in later chapters.

Create the file with this content:

```yaml
version: '3.8'

services:
  # Infrastructure
  redis:
    image: redis/redis-stack:latest
    container_name: deltastream-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - deltastream-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mongodb:
    image: mongo:6
    container_name: deltastream-mongodb
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: deltastream
    volumes:
      - mongo_data:/data/db
    networks:
      - deltastream-network
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/deltastream --quiet
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  redis_data:
  mongo_data:

networks:
  deltastream-network:
    driver: bridge
```

**Line-by-line explanation:**

```yaml
version: '3.8'
```
- Docker Compose file format version
- 3.8 supports health checks, build secrets, other modern features

```yaml
services:
```
- Defines all containers (services) in this application

```yaml
  redis:
    image: redis/redis-stack:latest
```
- `redis`: Service name (used for DNS inside Docker network)
- `image`: Use pre-built Redis image from Docker Hub
- `redis-stack`: Includes Redis + RedisInsight (web UI for debugging)

```yaml
    container_name: deltastream-redis
```
- Container name (shows in `docker ps`)
- Without this, Docker generates random name like `deltastream_redis_1`

```yaml
    ports:
      - "6379:6379"
```
- Port mapping: `host:container`
- Exposes Redis on `localhost:6379` (so you can connect from host machine)

```yaml
    command: redis-server --appendonly yes
```
- Overrides default command
- `--appendonly yes`: Enable AOF (Append-Only File) persistence
- **Why?** Without this, Redis is in-memory only (data lost on restart)
- **AOF vs RDB**: AOF logs every write (safer), RDB snapshots periodically (faster)

```yaml
    volumes:
      - redis_data:/data
```
- Mount Docker volume `redis_data` to container path `/data`
- **Why?** Persist data across container restarts
- Without volume: Container deleted → all data lost

```yaml
    networks:
      - deltastream-network
```
- Attach to custom network `deltastream-network`
- **Why?** Services on same network can resolve each other by name (`redis`, `mongodb`)
- Example: Worker connects to `redis://redis:6379` (not `localhost:6379`)

```yaml
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```
- **Health check**: How Docker knows if container is healthy
- `test`: Run `redis-cli ping` (returns `PONG` if healthy)
- `interval`: Check every 5 seconds
- `timeout`: Fail if command takes \u003e3 seconds
- `retries`: Mark unhealthy after 5 failed checks

**Why health checks matter:**

```yaml
  auth:
    depends_on:
      redis:
        condition: service_healthy
```

- Without health check: Auth starts immediately (Redis might not be ready → auth crashes)
- With health check: Docker waits until Redis is healthy before starting Auth

```yaml
  mongodb:
    environment:
      MONGO_INITDB_DATABASE: deltastream
```
- Creates database `deltastream` on first run
- Without this: MongoDB starts with no databases

```yaml
volumes:
  redis_data:
  mongo_data:
```
- Declares named volumes (Docker manages storage location)
- Alternative: Bind mounts (`./data:/data`) tie to host filesystem

```yaml
networks:
  deltastream-network:
    driver: bridge
```
- Creates custom network with bridge driver (default, suitable for single host)
- Alternative drivers: `host` (container uses host network), `overlay` (multi-host)

---

#### Step 1.7: Verify the Docker Compose Setup

Now let's verify that your Docker Compose infrastructure is working correctly.

**Action:** Start just the infrastructure services (Redis and MongoDB):

```bash
# Start Redis and MongoDB
docker-compose up -d redis mongodb

# Check status
docker-compose ps
```

**Expected output:**
```
NAME                    STATUS              PORTS
deltastream-redis       Up (healthy)        0.0.0.0:6379->6379/tcp
deltastream-mongodb     Up (healthy)        0.0.0.0:27017->27017/tcp
```

**What's happening:**
- `up -d`: Start services in detached mode (background)
- `-d redis mongodb`: Only start these two services (not the whole stack yet)

**Non-trivial concept - Health checks:**
Notice the `(healthy)` status. Docker waited for the health check to pass before marking the service as ready. Without health checks, services might show "Up" but not actually be ready to accept connections.

---

#### Step 1.8: Test Redis Connection

**Action:** Test that Redis is working correctly:

```bash
# Connect to Redis CLI
docker exec -it deltastream-redis redis-cli
```

**Inside the Redis CLI, run these commands:**
```bash
127.0.0.1:6379> PING
PONG

127.0.0.1:6379> SET test "Hello DeltaStream"
OK

127.0.0.1:6379> GET test
"Hello DeltaStream"

127.0.0.1:6379> exit
```

**What's happening:**
- `docker exec -it`: Execute interactive terminal command in running container
- `redis-cli`: Connect to Redis command-line interface
- `PING/PONG`: Health check command
- `SET/GET`: Test write and read operations

**Verify:** You should see exactly the responses shown above. If `PING` returns `PONG`, Redis is working!

---

#### Step 1.9: Test MongoDB Connection

**Action:** Test that MongoDB is working correctly:

```bash
# Connect to MongoDB shell
docker exec -it deltastream-mongodb mongosh deltastream
```

**Inside the Mongo shell, run these commands:**
```bash
test> db.test.insertOne({message: "Hello DeltaStream"})
{ acknowledged: true, insertedId: ObjectId('...') }

test> db.test.find()
[ { _id: ObjectId('...'), message: 'Hello DeltaStream' } ]

test> exit
```

**What's happening:**
- `mongosh deltastream`: Connect to the `deltastream` database
- `insertOne()`: Create a document (like a row in SQL)
- `find()`: Query all documents in the collection

**Verify:** You should see the inserted document returned. If so, MongoDB is working!

---

#### Step 1.10: Create Development Shortcuts with Makefile

**Action:** Create a `Makefile` to simplify common development commands:

```bash
cat <<'EOF' > Makefile
.PHONY: help build up down logs test clean

help:
	@echo "DeltaStream Development Commands"
	@echo "================================="
	@echo "make build    - Build Docker images"
	@echo "make up       - Start all services"
	@echo "make down     - Stop all services"
	@echo "make logs     - Tail logs"
	@echo "make test     - Run tests"
	@echo "make clean    - Remove all containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "API Gateway: http://localhost:8000"
	@echo "Socket Gateway: http://localhost:8002"

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	pytest tests/ -v

clean:
	docker-compose down -v
	docker system prune -f
EOF
```

**Non-trivial concept - Makefile syntax:**
- `.PHONY`: Declares targets that don't create files (e.g., `build` is a command, not a file)
- `@echo`: `@` suppresses echoing the command itself (cleaner output)
- Tabs matter! Each command line MUST start with a tab (not spaces)

**Usage examples:**
```bash
make help   # Show available commands
make up     # Start all services
make logs   # Watch logs in real-time
make down   # Stop all services
make clean  # Full cleanup (removes volumes too)
```

**Verify:** Run `make help` and you should see the command list.

---

### Part 1 Complete: What You've Learned

You now understand:

✅ **Why microservices** for this problem (scalability, fault isolation, independent deployment)

✅ **The architecture** (8 services, their roles, why each exists)

✅ **Data flow** (from feed generation to client display, with latency breakdown)

✅ **Infrastructure** (Redis for pub/sub + cache + queue, MongoDB for persistence)

✅ **Project structure** (monorepo with service isolation)

✅ **Docker Compose orchestration** (networks, volumes, health checks)

✅ **Development environment** (Docker, Makefile, env variables)

---

### What's Next: Part 2 Preview

In **Part 2: Building the Feed Generator**, we'll:

1. Create the Feed Generator service from scratch
2. Understand geometric Brownian motion for price simulation
3. Implement option pricing (simplified Black-Scholes)
4. Build the Redis publisher
5. Add structured logging
6. Containerize with Docker
7. Test the feed generation pipeline

**You'll write every line of code**, with explanations for:
- Why we calculate Greeks this way
- How option pricing works (time value, intrinsic value, moneyness)
- What realistic market data looks like
- How to publish to Redis pub/sub correctly
- How to structure a production Python service

---

### Mindset for Part 2

We're not just copying code. We're **understanding production engineering**:

- Why use `structlog` instead of `print()`?
- Why validate data before publishing?
- Why use environment variables for configuration?
- How to handle errors gracefully?
- How to make code testable?

**Remember**: The goal is not to finish quickly. The goal is to **deeply understand** every decision, so you can build systems like this yourself.

---

**End of Part 1**

---

---



---

**Navigation:**
← [Previous: Chapter 1-2: Service Breakdown](Chapter 1-2: Service Breakdown) | [Next: Chapter 2-1: Option Pricing Fundamentals](Chapter 2-1: Option Pricing Fundamentals) →

---
