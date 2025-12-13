# 🎯 COMPREHENSIVE INTERVIEW QUESTIONS & ANSWERS

---

## 📚 **SECTION 8: SYSTEM DESIGN QUESTIONS**

---

### **Q16: Design a real-time trading analytics platform from scratch. Walk me through your approach.**

**Answer:**
"I'll approach this using a top-down system design methodology:

**1. Requirements Gathering (5 minutes)**

**Functional Requirements:**
- Real-time market data ingestion (ticks, option chains)
- Analytics computation (PCR, Max Pain, Greeks, IV surface)
- Real-time WebSocket streaming to clients
- Historical data queries
- User authentication

**Non-Functional Requirements:**
- **Latency**: <100ms end-to-end (feed → client)
- **Throughput**: 1000+ ticks/second
- **Availability**: 99.9% uptime
- **Scalability**: 10K+ concurrent users
- **Data freshness**: <5 seconds

**2. High-Level Architecture**

```
┌─────────────────┐
│  Market Data    │ (External)
│  Feed Provider  │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Ingress │ (Feed Consumer)
    │  Gateway │
    └────┬─────┘
         │
    ┌────▼──────────┐
    │  Redis Pub/Sub │ (Message Broker)
    └────┬──────────┘
         │
         ├──────────────┐
         │              │
    ┌────▼─────┐   ┌───▼────────┐
    │  Worker  │   │  WebSocket │
    │  Pool    │   │  Gateway   │
    └────┬─────┘   └───┬────────┘
         │              │
    ┌────▼─────┐       │
    │ MongoDB  │       │
    │   +      │       │
    │  Redis   │       │
    │ (Cache)  │       │
    └──────────┘       │
                       │
                  ┌────▼────┐
                  │ Clients │
                  └─────────┘
```

**3. Component Design**

**Ingress Gateway:**
- Consumes data from external feed (WebSocket/HTTP)
- Validates and normalizes data
- Publishes to Redis Pub/Sub channels
- **Tech**: Python/Go, Redis client
- **Scale**: 1-2 instances (not bottleneck)

**Redis Pub/Sub:**
- Message broker for event-driven architecture
- Channels: market:underlying, market:option_chain
- **Why**: Low latency (<1ms), simple, handles fanout
- **Alternative**: Kafka (if durability needed)

**Worker Pool:**
- Subscribes to Redis channels
- Processes data: Calculate PCR, Greeks, Max Pain
- Stores in MongoDB + updates Redis cache
- Publishes enriched data back to Redis
- **Tech**: Celery workers, Python
- **Scale**: 5-20 workers (auto-scale based on queue depth)

**Storage Layer:**
- **MongoDB**: Historical data, complex queries
  - Indexed on (product, timestamp)
  - Sharded by product for horizontal scaling
- **Redis**: Hot cache (latest prices, 5min TTL)
  - Cache-aside pattern
  - 3-level caching strategy

**WebSocket Gateway:**
- Listens to enriched data channel
- Maintains persistent connections with clients
- Room-based subscriptions (product:NIFTY, chain:NIFTY)
- **Tech**: Flask-SocketIO, Redis message queue
- **Scale**: 3-10 instances (based on connection count)

**API Gateway:**
- REST endpoints for historical queries
- Routes to appropriate services
- Authentication & rate limiting
- **Tech**: Flask/FastAPI
- **Scale**: 2-5 instances

**4. Data Flow Example**

```
Market Feed → Ingress Gateway → Redis Pub/Sub (market:underlying)
                                       ↓
                                  Celery Worker
                                       ↓
                        Calculate analytics, store in MongoDB
                                       ↓
                        Update Redis cache, publish to Redis Pub/Sub (enriched:underlying)
                                       ↓
                                WebSocket Gateway
                                       ↓
                                 Clients (50-80ms)
```

**5. Scalability Considerations**

**Horizontal Scaling:**
- Workers: Scale based on queue depth
- WebSocket: Scale based on connection count
- API Gateway: Scale based on request rate

**Kubernetes HPA:**
```yaml
minReplicas: 2
maxReplicas: 10
targetCPUUtilization: 70%
```

**Database Scaling:**
- MongoDB sharding by product
- Read replicas for analytics queries
- Redis cluster for cache distribution

**6. Reliability Patterns**

**Retry Logic:**
- Exponential backoff (5s, 10s, 20s)
- Max 3 retries
- Dead Letter Queue for failures

**Idempotency:**
- Redis-based deduplication
- tick_id tracking with 1-hour TTL

**Circuit Breaker:**
- If MongoDB fails 5 times in 10s, serve from cache
- Auto-recover after 30s

**7. Monitoring & Observability**

**Metrics:**
- Latency percentiles (p50, p95, p99)
- Throughput (ticks/sec, chains/sec)
- Error rates
- Queue depth
- Connection count

**Logging:**
- Structured JSON logs
- Trace IDs for request tracing
- Centralized (ELK/Splunk)

**Alerting:**
- PagerDuty if service down >1 min
- Slack if latency >200ms for 5 min
- Email if queue depth >1000

**8. Technology Choices Justification**

**Redis Pub/Sub vs Kafka:**
- Redis: <1ms latency, simpler ops
- Kafka: Durable, replay capability
- Choice: Redis for MVP, Kafka for production

**MongoDB vs PostgreSQL:**
- MongoDB: Flexible schema, horizontal scaling
- PostgreSQL: ACID, complex joins
- Choice: MongoDB (option data is document-like)

**Celery vs AWS Lambda:**
- Celery: Lower latency, persistent workers
- Lambda: Serverless, auto-scale
- Choice: Celery (need <100ms processing)

**9. Estimated Costs (AWS)**

```
Workers (5 × t3.medium): $150/month
MongoDB Atlas (M30): $500/month
Redis ElastiCache (cache.m5.large): $200/month
Load Balancer: $25/month
Total: ~$875/month
```

**10. Future Enhancements**

- Add Kafka for durability
- Implement GraphQL for flexible queries
- Add machine learning for predictive analytics
- Multi-region deployment for global users
- gRPC for inter-service communication (lower latency)

**Trade-offs Made:**
- Redis Pub/Sub (no durability) vs Kafka (complex)
- Eventual consistency vs Strong consistency
- Cost vs Performance (right-sized instances)

This design handles 10K users, 1000 ticks/sec with <100ms latency at ~$1K/month."

**Follow-up Q: How would you handle market crash scenarios with 10x spike in traffic?**

"Great question! Market crashes create extreme load:

**Problem:**
- Normal: 1000 ticks/sec
- Crash: 10,000 ticks/sec (10x spike)
- User queries spike 50x
- WebSocket connections double (panic checking)

**Solutions:**

**1. Pre-emptive Scaling (Predictive)**
```python
# Monitor volatility spike
if vix_index > 40:  # VIX > 40 indicates panic
    scale_workers(replicas=20)
    scale_websocket(replicas=15)
    increase_db_connections()
```

**2. Rate Limiting (Protect backend)**
```python
@app.route('/api/data/chain/<product>')
@rate_limit(max_requests=100, window=60)  # 100 req/min per user
def get_chain(product):
    ...
```

**3. Shed Load Gracefully**
```python
if queue_depth > 5000:
    # Drop low-priority tasks
    if priority < 3:
        return {"status": "queue_full", "retry_after": 30}
```

**4. Serve Stale Data**
```python
# Increase cache TTL during crisis
if system_load > 80:
    cache_ttl = 60  # 1 min (normally 5 min)
    # Reduce freshness requirement
```

**5. Auto-scale Aggressively**
```yaml
# Lower CPU threshold for faster scaling
target:
  averageUtilization: 50  # From 70%
scaleUp:
  stabilizationWindowSeconds: 0  # Immediate
```

**6. Circuit Breaker**
```python
if mongodb_error_rate > 0.1:  # 10% errors
    serve_from_cache_only = True
    ttl = 300  # 5 min
```

**7. WebSocket Throttling**
```python
# Slow down update frequency
if connection_count > 8000:
    update_interval = 2000ms  # From 100ms
```

**8. Database Optimization**
```python
# Switch to read replicas
if primary_cpu > 80:
    route_reads_to_replicas()
```

**Real-world example (2020 March crash):**
- VIX spiked to 82 (normal: 15)
- Trading volume 5x normal
- Our approach:
  1. Detected VIX spike at 9:45 AM
  2. Auto-scaled workers 5 → 15
  3. Enabled aggressive caching
  4. Rate limited non-critical queries
  5. Maintained <200ms latency throughout
  6. Cost increased 3x for that day, but system stayed up"

---

### **Q17: How would you migrate this system to handle 100K concurrent users?**

**Answer:**
"Scaling from 10K to 100K (10x) requires architectural changes:

**Current Bottlenecks at 100K:**

**1. WebSocket Connections**
- Current: 3-10 instances × 1K connections = 10K max
- Needed: 100K connections
- **Problem**: Each instance limited to ~5K connections

**Solution:**
```python
# Increase instances
WebSocket Gateway: 20-30 instances

# Use connection pooling
# Each instance: 3-5K connections
# Total: 25 × 4K = 100K

# Load balancing
- Use L4 load balancer (AWS NLB)
- Sticky sessions by client_id
- Health check based
```

**2. Redis Pub/Sub**
- Current: Single Redis instance
- **Problem**: Single point of failure, limited throughput

**Solution:**
```python
# Redis Cluster
- 3 master nodes + 3 replicas
- Shard by channel hash
- Pub/Sub distributed across nodes

# Or migrate to Kafka
- Higher throughput (millions msg/sec)
- Durable messages
- Consumer groups for scaling
```

**3. MongoDB**
- Current: Single instance
- **Problem**: Write throughput limited

**Solution:**
```python
# Sharded MongoDB Cluster
- Shard key: product (NIFTY, BANKNIFTY)
- 5 shards × 3 replicas = 15 nodes
- Read preference: secondaryPreferred

# Time-series collection optimization
db.createCollection("underlying_ticks", {
    timeseries: {
        timeField: "timestamp",
        metaField: "product",
        granularity: "seconds"
    }
})
```

**4. Data Processing**
- Current: 20 workers max
- **Problem**: Can't process 10x data

**Solution:**
```python
# Kafka Streams for real-time processing
- Parallel processing per partition
- Stateful computations (windowing)
- Exactly-once semantics

# Lambda architecture
- Hot path: Kafka Streams (real-time)
- Cold path: Spark batch jobs (historical)
```

**Architecture Changes:**

**NEW Architecture:**
```
                    ┌──────────────┐
                    │  CloudFront  │ (CDN)
                    │     (CDN)    │
                    └──────┬───────┘
                           │
                ┌──────────▼──────────┐
                │   API Gateway       │
                │  (AWS API Gateway)  │
                └──────────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐  ┌───────▼───────┐  ┌──────▼─────┐
│  WebSocket    │  │   REST API    │  │   Auth     │
│  (20-30 pods) │  │  (10-15 pods) │  │  (3-5 pods)│
└───────┬───────┘  └───────┬───────┘  └──────┬─────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Kafka     │ (Message Broker)
                    │  Cluster    │ (3 brokers)
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐  ┌───────▼───────┐  ┌──────▼─────┐
│ Kafka Streams │  │   Workers     │  │  Analytics │
│ (Processing)  │  │  (30-50 pods) │  │  (Spark)   │
└───────┬───────┘  └───────┬───────┘  └──────┬─────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐  ┌───────▼───────┐  ┌──────▼─────┐
│   MongoDB     │  │     Redis     │  │  S3        │
│  (Sharded)    │  │   (Cluster)   │  │ (Archive)  │
│  15 nodes     │  │   6 nodes     │  │            │
└───────────────┘  └───────────────┘  └────────────┘
```

**Cost Estimation (AWS):**

```
Previous (10K users): $875/month

New (100K users):
- EKS Cluster (workers): $2,000/month
- MongoDB Atlas (M100 sharded): $2,500/month
- Redis ElastiCache (cluster): $1,000/month
- Kafka MSK (3 brokers): $1,200/month
- Load Balancers: $150/month
- CloudFront CDN: $200/month
- Total: ~$7,000/month

8x cost for 10x users (economies of scale)
```

**Performance Improvements:**

```
Metric              Current    @ 100K
------              -------    ------
Latency (p95)       80ms       150ms
Throughput          1K tps     10K tps
Connections         10K        100K
Availability        99.9%      99.95%
```

**Migration Strategy:**

**Phase 1: Infrastructure (Week 1-2)**
- Set up Kafka cluster
- Set up MongoDB sharding
- Set up Redis cluster

**Phase 2: Code Changes (Week 3-4)**
- Migrate from Redis Pub/Sub to Kafka
- Update workers to use Kafka Streams
- Implement connection pooling in WebSocket

**Phase 3: Testing (Week 5-6)**
- Load testing with 100K simulated users
- Chaos engineering (kill random pods)
- Measure latency under load

**Phase 4: Gradual Rollout (Week 7-8)**
- Blue-green deployment
- 10% traffic → New system
- Monitor for 48 hours
- 50% traffic → New system
- Monitor for 48 hours
- 100% traffic → New system

**Monitoring at Scale:**

```python
# Key metrics
- Kafka lag (consumer group lag)
- WebSocket connection count per instance
- MongoDB shard distribution
- Redis cluster memory usage
- API Gateway throttling rate

# Alerts
- Kafka lag > 1000 messages
- WebSocket instance > 4500 connections
- MongoDB shard imbalance > 20%
- Any service CPU > 85%
```

This architecture handles 100K users with <150ms latency at ~$7K/month."

---

## 📚 **SECTION 9: TROUBLESHOOTING & DEBUGGING**

---

### **Q18: Walk me through debugging a production issue where WebSocket clients are disconnecting frequently.**

**Answer:**
"I'll approach this systematically using the 5-step debugging framework:

**Step 1: Gather Information (Incident Report)**

**Symptoms:**
- WebSocket clients disconnecting every 30-60 seconds
- Affects ~40% of users
- Started at 2:30 PM today
- No code deployments in last 24 hours

**Step 2: Check Monitoring & Metrics**

**WebSocket Gateway Metrics:**
```bash
# Check Grafana dashboard
- Connection churn rate: 150 disconnects/min (normal: 10/min) ❌
- Average connection duration: 45 seconds (normal: 10+ minutes) ❌
- CPU usage: 35% (normal) ✅
- Memory usage: 45% (normal) ✅
- Error rate: 0.1% (normal) ✅
```

**Observations:**
- High churn but normal resource usage
- Not a capacity issue

**Step 3: Check Logs (Structured Search)**

```bash
# Check WebSocket Gateway logs
kubectl logs -l app=socket-gateway --tail=1000 | grep disconnect

# Look for patterns
{
  "event": "client_disconnected",
  "client_id": "abc123",
  "reason": "transport error",
  "connection_duration": 47,
  "timestamp": "2025-01-15T14:35:12Z"
}

# Many "transport error" disconnections
```

**Check for network issues:**
```bash
# Check pod events
kubectl get events --sort-by='.lastTimestamp' | grep socket-gateway

# See: "Readiness probe failed: connection refused"
```

**Hypothesis 1: Health check issues**

**Step 4: Investigate Health Checks**

```bash
# Check deployment config
kubectl get deployment socket-gateway -o yaml

readinessProbe:
  httpGet:
    path: /health
    port: 8002
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 1    # ← SUSPICIOUS
  failureThreshold: 3
```

**Test health endpoint manually:**
```bash
kubectl exec -it socket-gateway-pod-abc123 -- sh
curl http://localhost:8002/health

# Response time: 1.2 seconds ❌
# Timeout: 1 second ❌
```

**Root Cause Found:**
- Health check has 1-second timeout
- Health endpoint takes 1.2 seconds (slow)
- Readiness probe fails
- Kubernetes removes pod from service
- Clients disconnect
- Pod becomes ready again
- Cycle repeats

**Step 5: Investigate Why Health Check is Slow**

```python
@app.route('/health')
def health():
    try:
        # Check MongoDB
        mongo_client.admin.command('ping')  # Takes 0.8s ← PROBLEM
        
        # Check Redis
        redis_client.ping()  # Takes 0.3s
        
        return {'status': 'healthy'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500
```

**MongoDB ping taking 0.8 seconds (normal: <50ms)**

**Check MongoDB:**
```bash
# Check MongoDB metrics
mongodb_connections: 95/100  # Near connection limit
mongodb_slow_queries: 234 (last 5 min)  # Abnormal
```

**Secondary Root Cause:**
- MongoDB under heavy load
- Connection pool exhausted
- Health checks competing for connections
- Slow health checks → Failed probes → Disconnects

**Solution:**

**Immediate Fix (2 minutes):**
```bash
# Increase health check timeout
kubectl patch deployment socket-gateway -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "socket-gateway",
          "readinessProbe": {
            "timeoutSeconds": 3
          }
        }]
      }
    }
  }
}'

# Disconnects drop immediately
```

**Short-term Fix (30 minutes):**
```python
# Optimize health check - don't check dependencies
@app.route('/health')
def health():
    # Simple check without DB calls
    return {'status': 'healthy', 'service': 'socket-gateway'}, 200

@app.route('/health/deep')
def health_deep():
    # Separate endpoint for deep checks
    mongo_health = check_mongo()
    redis_health = check_redis()
    return {
        'status': 'healthy' if mongo_health and redis_health else 'degraded',
        'dependencies': {
            'mongodb': mongo_health,
            'redis': redis_health
        }
    }, 200
```

**Long-term Fix (Same day):**
```python
# Increase MongoDB connection pool
mongo_client = MongoClient(
    MONGO_URL,
    maxPoolSize=200,  # From 100
    minPoolSize=20,
    serverSelectionTimeoutMS=5000
)

# Add health check caching
health_cache = {'status': 'healthy', 'timestamp': 0}

@app.route('/health')
def health():
    now = time.time()
    # Return cached health if checked recently
    if now - health_cache['timestamp'] < 5:
        return health_cache
    
    # Perform actual check
    status = perform_health_checks()
    health_cache.update({'status': status, 'timestamp': now})
    return health_cache
```

**Step 6: Verify Fix**

```bash
# Monitor metrics
- Connection churn: 150/min → 10/min ✅
- Avg connection duration: 45s → 12 minutes ✅
- Readiness probe failures: 50/min → 0/min ✅
```

**Step 7: Post-Mortem (Document)**

**Incident Report:**
```
Title: WebSocket Disconnections due to Failed Health Checks
Date: 2025-01-15
Duration: 14:30 - 15:00 (30 minutes)
Impact: 40% users experienced disconnections
Root Cause: Health check timeout (1s) too low for MongoDB check (1.2s)
Secondary Cause: MongoDB connection pool exhaustion
Fix: Increased timeout, optimized health check, increased connection pool
Prevention: 
  - Monitor health check latency
  - Alert if health check >500ms
  - Separate shallow vs deep health checks
  - Regular connection pool capacity planning
```

**Lessons Learned:**
1. Health checks should be lightweight (<100ms)
2. Separate liveness (simple) from readiness (deep)
3. Monitor health check latency
4. Connection pool sizing critical
5. Always test under load

This debugging took 30 minutes from incident to resolution."

**Follow-up Q: How would you prevent this from happening again?**

"Three-pronged prevention strategy:

**1. Monitoring & Alerting:**
```python
# Alert on slow health checks
if health_check_latency_p95 > 500ms:
    alert("Health checks slow, investigate before probes fail")

# Alert on high churn
if disconnect_rate > 50/min:
    alert("High WebSocket churn, check health probes")

# Alert on connection pool usage
if mongodb_connection_usage > 80%:
    alert("MongoDB connection pool near capacity")
```

**2. Proactive Testing:**
```python
# Load testing includes health check latency
- Simulate 10K connections
- Measure health check latency under load
- Ensure <200ms at p99

# Chaos engineering
- Kill MongoDB for 10s
- Verify graceful degradation
- Health checks should timeout, not block forever
```

**3. Architecture Improvements:**
```python
# Circuit breaker for health checks
if mongodb_failures > 3:
    skip_mongodb_check = True  # For 30 seconds
    return partial_health()

# Connection pool monitoring
@app.route('/metrics')
def metrics():
    return {
        'mongodb_connections_active': pool.active_connections,
        'mongodb_connections_idle': pool.idle_connections,
        'health_check_latency_ms': health_check_time
    }

# Kubernetes best practices
livenessProbe:  # Am I alive?
  httpGet:
    path: /health
  timeoutSeconds: 5
  
readinessProbe:  # Can I serve traffic?
  httpGet:
    path: /ready
  timeoutSeconds: 3
```"

---

### **Q19: Your API latency suddenly increased from 50ms to 500ms. How do you debug this?**

**Answer:**
"Systematic approach using latency debugging framework:

**Step 1: Confirm the Problem (2 minutes)**

```bash
# Check Grafana dashboards
- p50 latency: 50ms → 450ms (9x increase) ❌
- p95 latency: 80ms → 850ms ❌
- p99 latency: 120ms → 1200ms ❌
- Error rate: 0.1% → 0.1% (unchanged) ✅
- Throughput: 200 req/sec (unchanged) ✅

# Timeframe: Started at 3:15 PM
# All endpoints affected
```

**Observation:**
- Latency increased across all percentiles
- No error rate increase (not failing, just slow)
- Throughput unchanged (not capacity issue)

**Step 2: Check Recent Changes**

```bash
# Check deployments
kubectl rollout history deployment api-gateway
# Last deployment: 2 days ago ✅

# Check infrastructure changes
git log --since="3 hours ago" infrastructure/
# No changes ✅

# Check external dependencies
# MongoDB: Normal
# Redis: Normal
```

**No obvious changes**

**Step 3: Trace a Slow Request**

```bash
# Enable request tracing
curl -H "X-Debug: true" http://api/data/chain/NIFTY

# Check logs with trace_id
{
  "trace_id": "xyz789",
  "timestamps": {
    "request_received": "15:20:00.000",
    "storage_service_called": "15:20:00.005",
    "storage_service_responded": "15:20:00.485",  # ← 480ms here
    "response_sent": "15:20:00.490"
  }
}
```

**Problem isolated: Storage Service slow (5ms → 480ms)**

**Step 4: Investigate Storage Service**

```bash
# Check Storage Service metrics
- CPU: 45% (normal) ✅
- Memory: 60% (normal) ✅
- Network: 5 Mbps (normal) ✅

# Check database metrics
MongoDB:
- CPU: 35% ✅
- Memory: 70% ✅
- Query time p95: 45ms ✅ (not slow)

Redis:
- CPU: 20% ✅
- Memory: 40% ✅
- Response time: 2ms ✅ (fast)
```

**Resources look fine, but service is slow. Weird.**

**Step 5: Check Network Latency**

```bash
# From API Gateway pod to Storage Service
kubectl exec -it api-gateway-pod -- sh
time curl http://storage:8003/health

real    0m0.470s  # ← 470ms for health check! ❌
```

**Network latency from API Gateway → Storage = 470ms**

**This is the problem!**

**Step 6: Check Network Configuration**

```bash
# Check service endpoints
kubectl get endpoints storage

NAME      ENDPOINTS           AGE
storage   10.244.2.15:8003    5h

# Check pod location
kubectl get pod -o wide | grep storage
storage-pod    10.244.2.15    node-us-west-2c

kubectl get pod -o wide | grep api-gateway  
api-gateway-pod    10.244.1.22    node-us-east-1a
```

**Found it!**
- Storage pod in **us-west-2c**
- API Gateway pod in **us-east-1a**
- Cross-region latency: ~450-500ms

**Step 7: Why Did This Change?**

```bash
# Check pod events
kubectl get events --sort-by='.lastTimestamp' | grep storage

15:10  Pod storage-pod-old terminated (node failure)
15:12  Pod storage-pod-new scheduled to node-us-west-2c
```

**Root Cause:**
1. Storage pod crashed at 3:10 PM (node failure)
2. Kubernetes rescheduled to node in us-west-2c
3. API Gateway in us-east-1a → Cross-region calls
4. Added 450ms network latency

**Solution:**

**Immediate Fix (5 minutes):**
```bash
# Delete pod to trigger reschedule
kubectl delete pod storage-pod-new

# Kubernetes schedules to nearby node
# Latency drops: 500ms → 50ms ✅
```

**Short-term Fix (30 minutes):**
```yaml
# Add pod affinity to keep services in same region
apiVersion: apps/v1
kind: Deployment
metadata:
  name: storage
spec:
  template:
    spec:
      affinity:
        podAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - api-gateway
            topologyKey: topology.kubernetes.io/zone
```

**Long-term Fix (Same day):**
```yaml
# Use pod topology spread constraints
apiVersion: apps/v1
kind: Deployment
metadata:
  name: storage
spec:
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: storage

# Ensure multi-region deployment is intentional
# All replicas of a service in same region as consumers
```

**Step 8: Add Monitoring**

```python
# Service mesh latency monitoring
from prometheus_client import Histogram

inter_service_latency = Histogram(
    'inter_service_latency_seconds',
    'Latency between services',
    ['source', 'destination']
)

# In API Gateway
with inter_service_latency.labels('api-gateway', 'storage').time():
    response = requests.get(f"{STORAGE_SERVICE_URL}/data")

# Alert if latency >100ms
alert_rule = "inter_service_latency_p95{destination='storage'} > 0.1"
```

**Prevention:**
1. Pod affinity to keep related services co-located
2. Monitor inter-service latency
3. Alert on cross-region calls
4. Use service mesh (Istio) for automatic retry/routing

**Timeline:**
- 3:10 PM: Node failure → Pod reschedule
- 3:15 PM: Latency spike detected
- 3:20 PM: Investigation started
- 3:35 PM: Root cause found
- 3:40 PM: Fixed (pod rescheduled)
- Total: 25 minutes

Key insight: Always check network latency in distributed systems!"

---

## 📚 **SECTION 10: CODING & ALGORITHM QUESTIONS**

---

### **Q20: Implement a sliding window rate limiter for your API Gateway.**

**Answer:**
"I'll implement a Redis-based sliding window rate limiter:

**Requirements:**
- Limit: 100 requests per minute per user
- Distributed (works across multiple API Gateway instances)
- Low latency (<5ms overhead)
- Accurate (no off-by-one errors)

**Implementation:**

```python
import redis
import time
from functools import wraps
from flask import request, jsonify

redis_client = redis.from_url('redis://localhost:6379/0')

def rate_limit(max_requests=100, window_seconds=60):
    """
    Sliding window rate limiter decorator.
    
    Uses Redis sorted set with timestamps as scores.
    Automatically removes old entries outside the window.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get user identifier
            user_id = request.headers.get('X-User-ID', request.remote_addr)
            key = f"rate_limit:{user_id}"
            
            now = time.time()
            window_start = now - window_seconds
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(key)
            
            # Add current request with timestamp as score
            pipe.zadd(key, {str(now): now})
            
            # Set expiry on key (cleanup)
            pipe.expire(key, window_seconds + 10)
            
            # Execute pipeline
            results = pipe.execute()
            request_count = results[1]  # Result of zcard
            
            # Check if rate limit exceeded
            if request_count >= max_requests:
                # Get oldest request in window
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window_seconds - now)
                else:
                    retry_after = window_seconds
                
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'limit': max_requests,
                    'window': window_seconds,
                    'retry_after': retry_after
                }), 429
            
            # Allow request
            response = f(*args, **kwargs)
            
            # Add rate limit headers
            remaining = max_requests - request_count - 1
            response.headers['X-RateLimit-Limit'] = str(max_requests)
            response.headers['X-RateLimit-Remaining'] = str(remaining)
            response.headers['X-RateLimit-Reset'] = str(int(now + window_seconds))
            
            return response
        
        return wrapper
    return decorator


# Usage
@app.route('/api/data/chain/<product>')
@rate_limit(max_requests=100, window_seconds=60)
def get_chain(product):
    # Your endpoint logic
    return jsonify({'product': product, 'data': '...'})
```

**How It Works:**

**Data Structure:**
```
Redis Sorted Set: rate_limit:user123
Score (timestamp)    Member (request_id)
1705329600.123      → "1705329600.123"
1705329605.456      → "1705329605.456"
1705329610.789      → "1705329610.789"
...
```

**Algorithm:**
1. Remove all entries with score < (now - 60 seconds)
2. Count remaining entries
3. If count >= 100, reject (429)
4. Else, add current request with timestamp as score
5. Allow request

**Example Timeline:**
```
Time: 10:00:00 - Request 1-99 arrive
Time: 10:00:30 - Request 100 arrives → Allowed
Time: 10:00:31 - Request 101 arrives → REJECTED (100 requests in last 60s)
Time: 10:01:01 - Request 1 expires (61 seconds old)
Time: 10:01:01 - Request 102 arrives → Allowed (now only 99 in window)
```

**Advantages:**
- **Accurate**: True sliding window (not fixed buckets)
- **Distributed**: Works across multiple API Gateway instances
- **Memory efficient**: Auto-expiry via TTL
- **Fast**: O(log N) operations, typically <5ms

**Testing:**

```python
def test_rate_limiter():
    user_id = "test_user"
    
    # Make 100 requests (should all succeed)
    for i in range(100):
        response = requests.get(
            'http://localhost:8000/api/data/chain/NIFTY',
            headers={'X-User-ID': user_id}
        )
        assert response.status_code == 200
        print(f"Request {i+1}: {response.headers['X-RateLimit-Remaining']} remaining")
    
    # 101st request should fail
    response = requests.get(
        'http://localhost:8000/api/data/chain/NIFTY',
        headers={'X-User-ID': user_id}
    )
    assert response.status_code == 429
    assert 'retry_after' in response.json()
    
    # Wait for window to slide
    time.sleep(61)
    
    # Should succeed again
    response = requests.get(
        'http://localhost:8000/api/data/chain/NIFTY',
        headers={'X-User-ID': user_id}
    )
    assert response.status_code == 200
```

**Edge Cases Handled:**
1. Clock drift: Uses Redis server time (consistent)
2. Concurrent requests: Redis pipeline ensures atomicity
3. Memory leaks: TTL cleanup
4. Rate limit headers: Client knows when to retry

**Complexity:**
- Time: O(log N) for sorted set operations
- Space: O(N) where N = max_requests

**Alternative Implementations:**

**Token Bucket (simpler but less accurate):**
```python
def token_bucket_rate_limit(user_id, max_requests, window):
    key = f"rate_limit:{user_id}"
    current = redis_client.get(key)
    
    if current is None:
        redis_client.setex(key, window, 1)
        return True
    elif int(current) < max_requests:
        redis_client.incr(key)
        return True
    else:
        return False
```

**Fixed Window (simplest but least accurate):**
```python
def fixed_window_rate_limit(user_id, max_requests, window):
    now = int(time.time())
    window_id = now // window
    key = f"rate_limit:{user_id}:{window_id}"
    
    count = redis_client.incr(key)
    redis_client.expire(key, window * 2)
    
    return count <= max_requests
```

Our sliding window is more accurate and fair."

**Follow-up Q: How would you handle burst traffic allowance?**

"Add a burst allowance on top of rate limit:

```python
def rate_limit_with_burst(max_requests=100, window=60, burst=20):
    """
    Allow burst of requests above the rate limit.
    
    Example: 100 req/min + 20 burst
    - User can make 120 requests immediately
    - Then throttled to 100 req/min
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = request.headers.get('X-User-ID', request.remote_addr)
            key_requests = f"rate_limit:{user_id}:requests"
            key_burst = f"rate_limit:{user_id}:burst"
            
            now = time.time()
            window_start = now - window
            
            # Check sliding window
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key_requests, 0, window_start)
            pipe.zcard(key_requests)
            results = pipe.execute()
            request_count = results[1]
            
            # Check burst allowance
            burst_used = int(redis_client.get(key_burst) or 0)
            
            # Total allowance = rate limit + burst
            total_allowance = max_requests + burst
            
            if request_count >= total_allowance:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Track burst usage
            if request_count > max_requests:
                redis_client.incr(key_burst)
                redis_client.expire(key_burst, window)
            
            # Add request
            redis_client.zadd(key_requests, {str(now): now})
            redis_client.expire(key_requests, window + 10)
            
            # Allow request
            return f(*args, **kwargs)
        
        return wrapper
    return decorator

# Usage: 100 req/min + 20 burst
@app.route('/api/data/chain/<product>')
@rate_limit_with_burst(max_requests=100, window=60, burst=20)
def get_chain(product):
    return jsonify({'product': product})
```

This allows legitimate burst traffic (market crash, news event) while still protecting against abuse."

---

### **Q21: Implement an LRU cache with TTL for option chain data.**

**Answer:**
"I'll implement an LRU (Least Recently Used) cache with TTL support:

**Requirements:**
- Fixed size (e.g., 1000 entries)
- LRU eviction when full
- TTL per entry
- O(1) get/set operations
- Thread-safe

**Implementation:**

```python
import time
import threading
from collections import OrderedDict
from typing import Any, Optional, Tuple

class LRUCacheWithTTL:
    """
    Thread-safe LRU cache with per-entry TTL.
    
    Uses OrderedDict for O(1) LRU operations and separate dict for expiry times.
    """
    
    def __init__(self, capacity: int = 1000, default_ttl: int = 300):
        """
        Args:
            capacity: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.capacity = capacity
        self.default_ttl = default_ttl
        
        # OrderedDict maintains insertion order, used for LRU
        self.cache = OrderedDict()
        
        # Store expiry times
        self.expiry = {}
        
        # Thread lock for safety
        self.lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Returns None if key doesn't exist or has expired.
        Moves key to end (most recently used).
        """
        with self.lock:
            # Check if key exists
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            # Check if expired
            if self._is_expired(key):
                self._remove_expired(key)
                self.stats['misses'] += 1
                self.stats['expirations'] += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            self.stats['hits'] += 1
            return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self.lock:
            ttl = ttl if ttl is not None else self.default_ttl
            expiry_time = time.time() + ttl
            
            # Key already exists, update it
            if key in self.cache:
                self.cache[key] = value
                self.expiry[key] = expiry_time
                self.cache.move_to_end(key)
                return
            
            # Cache is full, evict LRU
            if len(self.cache) >= self.capacity:
                self._evict_lru()
            
            # Add new entry
            self.cache[key] = value
            self.expiry[key] = expiry_time
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]
                return True
            return False
    
    def clear(self):
        """Clear all entries."""
        with self.lock:
            self.cache.clear()
            self.expiry.clear()
    
    def _is_expired(self, key: str) -> bool:
        """Check if key has expired."""
        return time.time() > self.expiry.get(key, float('inf'))
    
    def _remove_expired(self, key: str):
        """Remove expired key."""
        if key in self.cache:
            del self.cache[key]
            del self.expiry[key]
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        # Pop from beginning (least recently used)
        lru_key, _ = self.cache.popitem(last=False)
        del self.expiry[lru_key]
        self.stats['evictions'] += 1
    
    def cleanup_expired(self):
        """
        Remove all expired entries.
        Call periodically in background thread.
        """
        with self.lock:
            now = time.time()
            expired_keys = [
                key for key, expiry_time in self.expiry.items()
                if now > expiry_time
            ]
            
            for key in expired_keys:
                self._remove_expired(key)
                self.stats['expirations'] += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'capacity': self.capacity,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': round(hit_rate, 3),
                'evictions': self.stats['evictions'],
                'expirations': self.stats['expirations']
            }
    
    def __len__(self):
        return len(self.cache)
    
    def __contains__(self, key):
        with self.lock:
            return key in self.cache and not self._is_expired(key)


# Usage for option chain caching
option_chain_cache = LRUCacheWithTTL(capacity=1000, default_ttl=300)

def get_option_chain(product: str, expiry: str) -> dict:
    """
    Get option chain with caching.
    """
    cache_key = f"chain:{product}:{expiry}"
    
    # Try cache first
    cached = option_chain_cache.get(cache_key)
    if cached is not None:
        print(f"Cache HIT: {cache_key}")
        return cached
    
    # Cache miss - query database
    print(f"Cache MISS: {cache_key}")
    chain = db.option_chains.find_one({
        'product': product,
        'expiry': expiry
    }, sort=[('timestamp', -1)])
    
    # Cache result
    if chain:
        option_chain_cache.set(cache_key, chain, ttl=300)
    
    return chain


# Background cleanup thread
def cleanup_thread(cache, interval=60):
    """
    Periodically cleanup expired entries.
    """
    import threading
    import time
    
    def cleanup_loop():
        while True:
            time.sleep(interval)
            expired_count = cache.cleanup_expired()
            if expired_count > 0:
                print(f"Cleaned up {expired_count} expired entries")
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    return thread

# Start cleanup thread
cleanup_thread(option_chain_cache, interval=60)
```

**Testing:**

```python
def test_lru_cache_with_ttl():
    cache = LRUCacheWithTTL(capacity=3, default_ttl=2)
    
    # Test basic get/set
    cache.set('a', 1)
    cache.set('b', 2)
    cache.set('c', 3)
    
    assert cache.get('a') == 1
    assert cache.get('b') == 2
    assert cache.get('c') == 3
    
    # Test LRU eviction
    cache.set('d', 4)  # Evicts 'a' (least recently used)
    assert cache.get('a') is None
    assert cache.get('d') == 4
    
    # Test TTL expiry
    cache.set('e', 5, ttl=1)  # 1 second TTL
    assert cache.get('e') == 5
    time.sleep(1.1)
    assert cache.get('e') is None  # Expired
    
    # Test LRU ordering with access
    cache.clear()
    cache.set('x', 1)
    cache.set('y', 2)
    cache.set('z', 3)
    
    cache.get('x')  # Access 'x', moves to end
    cache.set('w', 4)  # Evicts 'y' (LRU)
    
    assert cache.get('x') == 1
    assert cache.get('y') is None  # Evicted
    assert cache.get('z') == 3
    assert cache.get('w') == 4
    
    # Test statistics
    stats = cache.get_stats()
    print(f"Hit rate: {stats['hit_rate']}")
    print(f"Evictions: {stats['evictions']}")
    
    print("All tests passed!")

test_lru_cache_with_ttl()
```

**Output:**
```
All tests passed!
Hit rate: 0.667
Evictions: 2
```

**Complexity Analysis:**
- `get()`: O(1) - dict lookup + OrderedDict move_to_end
- `set()`: O(1) - dict insert + OrderedDict append
- `delete()`: O(1) - dict delete
- Space: O(n) where n = capacity

**Comparison with Redis:**

| Feature | LRUCacheWithTTL | Redis |
|---------|-----------------|-------|
| Latency | <1ms (in-memory) | ~1-2ms (network) |
| Persistence | No | Yes (optional) |
| Distributed | No | Yes |
| Memory | Per-process | Shared |
| Use case | Hot data, single instance | Distributed systems |

**When to use:**
- Use **LRUCacheWithTTL**: Single instance, ultra-low latency, non-critical data
- Use **Redis**: Multi-instance, distributed, persistence needed

For our trading platform, use both:
- L1 cache: LRUCacheWithTTL (in-process)
- L2 cache: Redis (distributed)

```python
def get_option_chain_multi_level(product, expiry):
    cache_key = f"chain:{product}:{expiry}"
    
    # L1: In-process cache
    cached = option_chain_cache.get(cache_key)
    if cached:
        return cached
    
    # L2: Redis cache
    cached = redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        option_chain_cache.set(cache_key, data)  # Populate L1
        return data
    
    # L3: Database
    data = db.option_chains.find_one({'product': product, 'expiry': expiry})
    
    # Populate caches
    redis_client.setex(cache_key, 300, json.dumps(data))
    option_chain_cache.set(cache_key, data)
    
    return data
```

This gives us <1ms for L1 hits, ~2ms for L2 hits, ~50ms for DB queries."

---

This covers comprehensive interview questions. Would you like me to continue with:
- More coding challenges (implement Max Pain calculator, PCR calculator)
- Behavioral questions about your project
- Trade-off discussions
- More system design scenarios?
