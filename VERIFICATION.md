# Verification Guide

This document provides step-by-step instructions to verify that the DeltaStream system is working correctly.

## Prerequisites

- Docker and Docker Compose installed
- `curl` and `jq` for API testing
- Node.js (optional, for WebSocket client)
- Browser (for HTML client)

## Step 1: Start All Services

```bash
# Start services
./scripts/start-local.sh

# Or using docker-compose
docker-compose up -d

# Wait 30 seconds for services to initialize
sleep 30
```

**Expected Output:**
```
Services started!
Service URLs:
  API Gateway:    http://localhost:8000
  ...
```

## Step 2: Verify Service Health

```bash
# Check all service health endpoints
for port in 8000 8001 8002 8003 8004 8005; do
  echo "Checking port $port..."
  curl -s http://localhost:$port/health | jq .
done
```

**Expected Output for each:**
```json
{
  "status": "healthy",
  "service": "api-gateway"
}
```

## Step 3: Verify Feed Generation

```bash
# Check feed generator logs
docker-compose logs -f feed-generator --tail=20
```

**Expected Output:**
```json
{"timestamp":"2025-01-15T10:30:00Z","event":"feed_generator_started","products":[...]}
{"timestamp":"2025-01-15T10:30:01Z","event":"published_option_chain","product":"NIFTY"}
```

**Press Ctrl+C to stop following logs**

## Step 4: Verify Worker Processing

```bash
# Check worker logs
docker-compose logs worker-enricher --tail=50 | grep "processed"
```

**Expected Output:**
```json
{"event":"processed_underlying_tick","product":"NIFTY","price":21543.25}
{"event":"processed_option_chain","product":"NIFTY","pcr":1.0234}
```

## Step 5: Verify Data in MongoDB

```bash
# Check MongoDB collections
docker-compose exec mongodb mongosh deltastream --eval "
  db.underlying_ticks.countDocuments();
  db.option_quotes.countDocuments();
  db.option_chains.countDocuments();
"
```

**Expected Output:**
```
150   # underlying_ticks (should be > 0)
200   # option_quotes (should be > 0)
15    # option_chains (should be > 0)
```

Numbers will vary based on how long the system has been running.

## Step 6: Verify Redis Cache

```bash
# Check Redis keys
docker-compose exec redis redis-cli KEYS "latest:*" | head -20
```

**Expected Output:**
```
latest:underlying:NIFTY
latest:underlying:BANKNIFTY
latest:chain:NIFTY:2025-01-25
latest:pcr:NIFTY:2025-01-25
...
```

## Step 7: Test REST API

### Get Products
```bash
curl -s http://localhost:8000/api/data/products | jq .
```

**Expected Output:**
```json
{
  "products": ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "AAPL", "TSLA", "SPY", "QQQ"]
}
```

### Get Underlying Ticks
```bash
curl -s "http://localhost:8000/api/data/underlying/NIFTY?limit=5" | jq '.ticks[0]'
```

**Expected Output:**
```json
{
  "product": "NIFTY",
  "price": 21543.25,
  "timestamp": "2025-01-15T10:30:45.123456",
  "tick_id": 12345
}
```

### Get Option Chain
```bash
curl -s "http://localhost:8000/api/data/chain/NIFTY?limit=1" | jq '.chains[0] | {product, expiry, pcr_oi, atm_straddle_price}'
```

**Expected Output:**
```json
{
  "product": "NIFTY",
  "expiry": "2025-01-25",
  "pcr_oi": 1.0234,
  "atm_straddle_price": 253.25
}
```

### Get PCR Analysis
```bash
curl -s http://localhost:8000/api/analytics/pcr/NIFTY | jq '.latest[0]'
```

**Expected Output:**
```json
{
  "pcr_oi": 1.0234,
  "pcr_volume": 0.9876,
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

## Step 8: Test WebSocket Connection (Browser)

```bash
# Open HTML client in browser
open examples/subscribe-example.html
# Or on Linux: xdg-open examples/subscribe-example.html
```

**Expected Behavior:**
1. Status shows "Connected"
2. Click "Subscribe to NIFTY" button
3. Price updates appear in real-time
4. Chain summary updates every few seconds
5. Event log shows incoming messages

**Expected Log Entries:**
```
[10:30:45] Connected to Socket Gateway
[10:30:45] Subscribed to NIFTY
[10:30:46] NIFTY: 21543.25
[10:30:50] Chain update: NIFTY PCR=1.0234
```

## Step 9: Test WebSocket Connection (Node.js)

```bash
# Run Node.js client
cd examples
node subscribe-example.js
```

**Expected Output:**
```
Connecting to http://localhost:8002...
Connected to Socket Gateway
Client ID: abc123xyz
Subscribed: product:NIFTY
Available products: ["NIFTY", "BANKNIFTY", ...]
[2025-01-15T10:30:46] NIFTY Price: 21543.25
[Chain Summary] NIFTY (2025-01-25)
  Spot: 21543.25
  PCR (OI): 1.0234
  ATM Straddle: 253.25
```

**Press Ctrl+C to stop**

## Step 10: Test Authentication

### Register User
```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}' \
  | jq .
```

**Expected Output:**
```json
{
  "message": "User registered successfully",
  "token": "eyJ...",
  "user": {
    "id": "abc123",
    "email": "test@example.com",
    "name": "Test User"
  }
}
```

### Login
```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' \
  | jq .
```

**Expected Output:**
```json
{
  "message": "Login successful",
  "token": "eyJ...",
  "user": {...}
}
```

## Step 11: Run Complete API Examples

```bash
# Run all API examples
./examples/curl-examples.sh
```

**Expected Output:**
Series of successful API responses for all endpoints.

## Step 12: Monitor System

### View All Logs
```bash
docker-compose logs -f
```

### View Specific Service Logs
```bash
docker-compose logs -f feed-generator
docker-compose logs -f worker-enricher
docker-compose logs -f socket-gateway
```

### Check Resource Usage
```bash
docker stats
```

**Expected Output:**
All containers running with reasonable CPU (<50%) and memory usage.

## Success Criteria

✅ All health endpoints return `{"status": "healthy"}`
✅ Feed generator is publishing ticks (check logs)
✅ Worker is processing data (check logs)
✅ MongoDB has data (underlying_ticks, option_quotes, option_chains)
✅ Redis has cached data (latest:* keys)
✅ REST API returns valid data for all endpoints
✅ WebSocket client receives real-time updates
✅ Authentication works (register & login)

## Troubleshooting

### Services Not Starting
```bash
# Check logs
docker-compose logs <service-name>

# Restart service
docker-compose restart <service-name>
```

### No Data Flowing
```bash
# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Check MongoDB connectivity
docker-compose exec mongodb mongosh deltastream --eval "db.serverStatus()"

# Restart worker
docker-compose restart worker-enricher
```

### WebSocket Not Connecting
```bash
# Check socket gateway logs
docker-compose logs socket-gateway

# Test health endpoint
curl http://localhost:8002/health
```

## Cleanup

```bash
# Stop all services
./scripts/stop-local.sh

# Or with docker-compose
docker-compose down

# Remove volumes (deletes all data)
docker-compose down -v
```

## Performance Validation

### Expected Performance
- Feed generation: ~100-200 ticks/second
- Worker processing: <100ms per task
- WebSocket latency: <50ms
- API response time: <200ms
- MongoDB writes: ~100-200/second

### Load Testing
```bash
# Install Apache Bench
apt-get install apache2-utils

# Test API endpoint
ab -n 1000 -c 10 http://localhost:8000/api/data/products
```

**Expected:** >100 requests/second with <500ms average response time.

---

## Summary

If all steps pass, you have successfully verified:

1. ✅ Infrastructure (Redis, MongoDB)
2. ✅ Data Generation (Feed Generator)
3. ✅ Data Processing (Worker Enricher)
4. ✅ Data Storage (MongoDB, Redis)
5. ✅ REST API (API Gateway)
6. ✅ Real-time Streaming (Socket Gateway)
7. ✅ Authentication (Auth Service)
8. ✅ Analytics (Analytics Service)

**The DeltaStream system is fully operational! 🎉**
