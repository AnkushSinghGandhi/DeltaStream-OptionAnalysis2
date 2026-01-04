# Part 8: Testing & Deployment

Now that all services are built, let's integrate them with Docker Compose and test the complete system end-to-end.

---

## 8.1 Understanding Docker Compose

**What is Docker Compose?**
- Tool for orchestrating multi-container applications
- Define all services in one YAML file
- Start/stop entire stack with one command
- Manages networking, volumes, dependencies

**Why Docker Compose for DeltaStream?**
- 13 services (2 infrastructure + 7 microservices + ...)
- Complex networking (services must talk to each other)
- Dependency management (worker needs MongoDB ready)
- Reproducible environments (dev = staging = prod... mostly)

---

## 8.2 Creating Docker Compose Configuration

### Step 8.1: Create Base File Structure

**Action:** Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  # Infrastructure services will go here
  
volumes:
  # Data persistence volumes
  
networks:
  #Custom network
```

**Breaking Down Version:**
```yaml
version: '3.8'
```
- Compose file format version
- `3.8` = Modern features (healthchecks, depends_on conditions)
- Compatible with Docker Engine 19.03+

---

### Step 8.2: Add Infrastructure Services

**Action:** Add Redis and MongoDB to the `services` section:

```yaml
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
```

**Breaking Down Redis Configuration:**

**Image:**
```yaml
image: redis/redis-stack:latest
```
- Official Redis with RedisInsight built-in
- `latest` = Most recent version (not recommended for prod)
- Alternative: Pin version like `redis/redis-stack:7.2.0`

**Ports:**
```yaml
ports:
  - "6379:6379"
```
- Format: `"HOST_PORT:CONTAINER_PORT"`
- Maps port 6379 on your machine → port 6379 in container
- Allows `redis-cli -p 6379` from host

**Command Override:**
```yaml
command: redis-server --appendonly yes
```
- Overrides default Dockerfile CMD
- `--appendonly yes` → Enables AOF (Append-Only File)
- Data persists through restarts (crash recovery)

**Volumes:**
```yaml
volumes:
  - redis_data:/data
```
- Named volume (defined at bottom of file)
- `/data` → Where Redis stores files
- Persists even if container destroyed

**Healthcheck:**
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 5s
  timeout: 3s
  retries: 5
```
- `test`: Command to run (exit 0 = healthy)
- `interval`: Run every 5 seconds
- `timeout`: Max 3 seconds to respond
- `retries`: After 5 failures, mark unhealthy

**Why healthchecks matter:**
- Other services wait for Redis to be ready
- `depends_on: condition: service_healthy` = smart waiting

**Breaking Down MongoDB Configuration:**

**Environment Variables:**
```yaml
environment:
  MONGO_INITDB_DATABASE: deltastream
```
- Creates `deltastream` database on first run
- Without this, would need manual `use deltastream`

**MongoDB Healthcheck:**
```yaml
test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/deltastream --quiet
```
- `echo '...'` → Sends MongoDB command
- `| mongosh` → Pipe to MongoDB shell
- `--quiet` → Suppress extra output
- Returns `1` (true in Mongo) = healthy

---

### Step 8.3: Add Feed Generator Service

**Action:** Add the feed generator:

```yaml
  feed-generator:
    build:
      context: ./services/feed-generator
    container_name: deltastream-feed
    environment:
      - REDIS_URL=redis://redis:6379/0
      - FEED_PROVIDER=synthetic
      - FEED_INTERVAL=1
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped
```

**Breaking Down Service Build:**

**Build Context:**
```yaml
build:
  context: ./services/feed-generator
```
- Builds image from local Dockerfile
- `context`: Directory containing Dockerfile
- Alternative: `image: myregistry/feed-generator:v1` for pre-built images

**Environment Variables:**
```yaml
environment:
  - REDIS_URL=redis://redis:6379/0
```
- `redis://` → Redis protocol
- `redis` → Hostname (service name in Compose becomes DNS)
- `6379` → Port
- `/0` → Database 0

**Why `redis` not `localhost`?**
- Each container has own `localhost`
- Docker Compose creates internal DNS
- Service names resolve to container IPs

**Smart Dependencies:**
```yaml
depends_on:
  redis:
    condition: service_healthy
```
- Wait for Redis healthcheck to pass
- Old syntax: `depends_on: [redis]` (doesn't wait for ready)
- New: Actually waits for service to be functional

**Restart Policy:**
```yaml
restart: unless-stopped
```
- `unless-stopped`: Restart on crash, but not if manually stopped
- Alternatives:
  - `no`: Never restart
  - `always`: Even if stopped manually
  - `on-failure`: Only on non-zero exit

---

### Step 8.4: Add Worker Enricher Service

**Action:** Add the Celery worker:

```yaml
  worker-enricher:
    build:
      context: ./services/worker-enricher
    container_name: deltastream-worker
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      redis:
        condition: service_healthy
      mongodb:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped
```

**Breaking Down Celery Configuration:**

**Multiple Redis Databases:**
```yaml
- CELERY_BROKER_URL=redis://redis:6379/1
- CELERY_RESULT_BACKEND=redis://redis:6379/2
```
- Redis has 16 databases (0-15)
- `/0` → Market data pub/sub
- `/1` → Celery task queue
- `/2` → Celery results
- Logical separation, same Redis instance

**MongoDB URL:**
```yaml
- MONGO_URL=mongodb://mongodb:27017/deltastream
```
- `mongodb://` → MongoDB protocol
- `mongodb` → Service name
- `/deltastream` → Database name

**Multiple Dependencies:**
```yaml
depends_on:
  redis:
    condition: service_healthy
  mongodb:
    condition: service_healthy
```
- Wait for both Redis AND MongoDB
- Both must pass healthchecks

---

### Step 8.5: Add API Services (Storage, Auth, Gateway)

**Action:** Add storage, auth, and API gateway:

```yaml
  storage:
    build:
      context: ./services/storage
    container_name: deltastream-storage
    ports:
      - "8003:8003"
    environment:
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - PORT=8003
    depends_on:
      mongodb:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped

  auth:
    build:
      context: ./services/auth
    container_name: deltastream-auth
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - JWT_SECRET=${JWT_SECRET}
      - PORT=8001
    depends_on:
      mongodb:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped

  api-gateway:
    build:
      context: ./services/api-gateway
    container_name: deltastream-api-gateway
    ports:
      - "8000:8000"
    environment:
      - AUTH_SERVICE_URL=http://auth:8001
      - STORAGE_SERVICE_URL=http://storage:8003
      - ANALYTICS_SERVICE_URL=http://analytics:8004
      - PORT=8000
    depends_on:
      - auth
      - storage
    networks:
      - deltastream-network
    restart: unless-stopped
```

**Breaking Down Port Mapping:**

**Why expose ports?**
```yaml
ports:
  - "8000:8000"  # API Gateway - needs external access
```
- API Gateway: External (frontend calls it)
- Storage/Auth: Internal only (no port mapping = can't access from host)

**Environment Variable Substitution:**
```yaml
- JWT_SECRET=${JWT_SECRET}
```
- Reads from `.env` file or shell environment
- Create `.env` in same directory as `docker-compose.yml`:
```bash
JWT_SECRET=your_super_secret_key_here_change_me
```

---

### Step 8.6: Add Socket Gateway and Analytics

**Action:** Add final services:

```yaml
  socket-gateway:
    build:
      context: ./services/socket-gateway
    container_name: deltastream-socket
    ports:
      - "8002:8002"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - PORT=8002
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped

  analytics:
    build:
      context: ./services/analytics
    container_name: deltastream-analytics
    ports:
      - "8004:8004"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - PORT=8004
    depends_on:
      redis:
        condition: service_healthy
      mongodb:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped
```

---

### Step 8.7: Define Volumes and Networks

**Action:** Add volumes and network at bottom of file:

```yaml
volumes:
  redis_data:
  mongo_data:

networks:
  deltastream-network:
    driver: bridge
```

**Breaking Down Volumes:**

**Named Volumes:**
```yaml
volumes:
  redis_data:
  mongo_data:
```
- Simple syntax = Docker manages location
- Alternative: Bind mounts (`./data:/data`)
- Named volumes persist through `docker-compose down`

**Where are they stored?**
```bash
docker volume inspect deltastream_redis_data
# "Mountpoint": "/var/lib/docker/volumes/deltastream_redis_data/_data"
```

**Network:**
```yaml
networks:
  deltastream-network:
    driver: bridge
```
- `bridge`: Default network driver
- All services on same network can talk
- Isolated from other Docker networks

---

## 8.3 Testing the Complete System

### Step 8.8: Start Infrastructure

**Action:** Start just Redis and MongoDB first:

```bash
docker-compose up -d redis mongodb
```

**Breaking Down Docker Compose Commands:**

**`-d` flag:**
- Detached mode (background)
- Without: Logs block terminal

**Specific services:**
- `redis mongodb` → Only these two
- Without: Starts all services

**Check status:**
```bash
docker-compose ps
```

**Expected output:**
```
NAME                  STATUS               PORTS
deltastream-redis     Up (healthy)         6379
deltastream-mongodb   Up (healthy)         27017
```

**If unhealthy:**
```bash
# View logs
docker-compose logs redis
docker-compose logs mongodb

# Common issues:
# - Port already in use
# - Insufficient resources
```

---

### Step 8.9: Start Core Services

**Action:** Start feed and worker:

```bash
docker-compose up -d feed-generator worker-enricher

# Watch logs (follow mode)
docker-compose logs -f feed-generator worker-enricher
```

**Breaking Down Log Commands:**

**`-f` flag:**
- Follow mode (like `tail -f`)
- Streams new log lines
- Ctrl+C to stop (doesn't stop containers)

**Multiple services:**
- Shows interleaved logs
- Color-coded by service

**Expected logs:**
```
feed-generator  | {"event": "feed_starting", "provider": "synthetic"}
worker-enricher | [INFO] Celery worker ready
feed-generator  | {"event": "tick_published", "product": "NIFTY"}
worker-enricher | [INFO] Task received: process_option_chain
```

---

### Step 8.10: Verify Data Flow

**Action:** Check MongoDB for data:

```bash
# Connect to MongoDB shell
docker exec -it deltastream-mongodb mongosh deltastream

# Count documents
db.underlying_ticks.countDocuments()
db.option_chains.countDocuments()

# View latest chain
db.option_chains.find().limit(1).sort({timestamp: -1}).pretty()
```

**Breaking Down Docker Exec:**

**Command syntax:**
```bash
docker exec -it deltastream-mongodb mongosh deltastream
```
- `exec`: Run command in running container
- `-it`: Interactive terminal
- `deltastream-mongodb`: Container name  
- `mongosh deltastream`: Command to run (MongoDB shell + database)

**Expected output:**
```json
{
  "_id": ObjectId("..."),
  "product": "NIFTY",
  "expiry": "2024-01-25",
  "spot_price": 21543.5,
  "pcr_oi": 1.25,
  "max_pain_strike": 21500,
  "calls": [...],
  "puts": [...]
}
```

---

### Step 8.11: Start All Services

**Action:** Start the complete stack:

```bash
# Start everything
docker-compose up -d

# Check all services
docker-compose ps
```

---

### Step 8.12: Test API Endpoints

**Action:** Test the API Gateway:

```bash
# Health check
curl http://localhost:8000/health

# Get products
curl http://localhost:8000/api/data/products

# Get underlying data
curl http://localhost:8000/api/data/underlying/NIFTY

# Get option chain
curl http://localhost:8000/api/data/option-chain/NIFTY/2024-01-25
```

**Expected responses:**
```json
// /health
{"status": "healthy", "timestamp": "2024-01-25T10:30:00Z"}

// /api/data/products
{"products": ["NIFTY", "BANKNIFTY", "FINNIFTY", ...]}

// /api/data/underlying/NIFTY
{
  "product": "NIFTY",
  "price": 21543.5,
  "change": 0.25,
  "timestamp": "..."
}
```

---

### Step 8.13: Test WebSocket Connection

**Action:** Create `test_socket.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Test</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
    <h1>DeltaStream WebSocket Test</h1>
    <div id="status">Connecting...</div>
    <div id="data"></div>

    <script>
        const socket = io('http://localhost:8002');
        
        socket.on('connected', (data) => {
            document.getElementById('status').innerText = 'Connected!';
            console.log('Connected:', data);
        });
        
        socket.on('underlying_update', (data) => {
            console.log('Update:', data);
            document.getElementById('data').innerHTML = `
                <strong>${data.product}</strong>: ₹${data.price}
            `;
        });

        // Subscribe to NIFTY updates
        socket.emit('subscribe', {
            type: 'product',
            symbol: 'NIFTY'
        });
    </script>
</body>
</html>
```

**Open in browser →** See real-time updates!

---

## 8.4 Performance Testing

### Step 8.14: Load Test WebSocket

**Action:** Create `test_load.py`:

```python
import asyncio
import socketio

async def test_concurrent_connections(num_clients=100):
    """Test 100 concurrent WebSocket connections."""
    clients = []
    
    for i in range(num_clients):
        sio = socketio.AsyncClient()
        await sio.connect('http://localhost:8002')
        await sio.emit('subscribe', {
            'type': 'product',
            'symbol': 'NIFTY'
        })
        clients.append(sio)
        print(f"Connected client {i+1}/{num_clients}")
    
    print(f"\n✅ All {num_clients} clients connected!")
    
    # Keep alive for 60 seconds
    print("Monitoring for 60 seconds...")
    await asyncio.sleep(60)
    
    # Disconnect all
    print("Disconnecting clients...")
    for sio in clients:
        await sio.disconnect()
    
    print("Test complete!")

# Run
asyncio.run(test_concurrent_connections(100))
```

**Run test:**
```bash
pip install python-socketio aiohttp
python test_load.py
```

**Breaking Down Async Testing:**

**AsyncClient:**
```python
sio = socketio.AsyncClient()
```
- Non-blocking Socket.IO client
- Can create 100 without threading

**Async Operations:**
```python
await sio.connect('http://localhost:8002')
```
- `await` = Don't block, switch to other tasks
- Allows 100 concurrent connections efficiently

---

## Summary

You've successfully **deployed and tested** the complete DeltaStream platform!

✅ **Docker Compose** - Orchestrated 9 services
✅ **Healthchecks** - Smart dependency management
✅ **Networking** - Internal DNS resolution
✅ **Volume Persistence** - Data survives restarts
✅ **End-to-End Testing** - Verified data flow
✅ **WebSocket Testing** - Real-time updates working
✅ **Load Testing** - 100 concurrent connections

**Key Learnings:**
- Docker Compose YAML syntax
- Healthcheck configuration
- Service dependency management
- Volume vs bind mount
- Bridge networking
- Interactive container access (`docker exec`)
- Async WebSocket testing

**Production Deployment:**
- **Kubernetes** (Chapter 11) for production orchestration
- **Prometheus + Grafana** (Chapter 12) for monitoring
- **CI/CD Pipeline** for automated deployments

**Congratulations! 🎉** You've built a production-grade microservices platform from scratch!

---
