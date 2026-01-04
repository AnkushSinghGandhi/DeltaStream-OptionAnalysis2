# Part 12: Observability & Monitoring

Observability is the ability to understand your system's internal state from external outputs. For a distributed system with 13 microservices, you need metrics, logs, and traces.

---

## 12.1 The Three Pillars of Observability

**1. Metrics** (What happened?)
- Request count, latency, error rate
- CPU/Memory usage
- Queue length

**2. Logs** (Why did it happen?)
- Error messages
- Stack traces  
- Audit trails

**3. Traces** (How did it flow?)
- Request path through services
- Which service was slow?
- Distributed transaction tracking

**Our Stack:**
- **Prometheus** → Metrics collection & storage
- **Grafana** → Visualization dashboards
- **Loki** → Log aggregation (optional, complements Chapter 10's logging service)
- **Alertmanager** → Proactive alerting

---

## 12.2 Setting Up Prometheus

### Step 12.1: Create Prometheus Configuration

**Action:** Create `observability/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
    metrics_path: '/metrics'

  - job_name: 'socket-gateway'
    static_configs:
      - targets: ['socket-gateway:8002']

  - job_name: 'analytics'
    static_configs:
      - targets: ['analytics:8004']

  # Kubernetes auto-discovery
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: [deltastream]
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

**Breaking Down Prometheus Config:**

**Global Settings:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
```
- `scrape_interval`: How often to fetch metrics from targets
- `evaluation_interval`: How often to evaluate alerting rules
- 15s = good balance (not too frequent, not too stale)

**Static Targets:**
```yaml
- job_name: 'api-gateway'
  static_configs:
    - targets: ['api-gateway:8000']
  metrics_path: '/metrics'
```
- `job_name`: Label for grouping metrics
- `targets`: List of endpoints to scrape
- `api-gateway:8000`: DNS name in Docker/Kubernetes
- `metrics_path`: Where to GET metrics (default: /metrics)

**What Prometheus Does:**
```
Every 15s:
  GET http://api-gateway:8000/metrics → Parse metrics → Store in TSDB
```

**Kubernetes Auto-Discovery:**
```yaml
- job_name: 'kubernetes-pods'
  kubernetes_sd_configs:
    - role: pod
```
- `kubernetes_sd_configs`: Discover pods automatically
- `role: pod`: Monitor Kubernetes pods (not services/nodes)
- No need to hardcode pod IPs

**Relabel Config:**
```yaml
relabel_configs:
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
    action: keep
    regex: true
```
- Only scrape pods with annotation `prometheus.io/scrape: "true"`
- Filter out pods without this annotation

**Pod Annotation Example:**
```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
```

---

### Step 12.2: Run Prometheus

**Action:** Start Prometheus with Docker:

```bash
docker run -d \\
  --name prometheus \\
  -p 9090:9090 \\
  -v $(pwd)/observability/prometheus.yml:/etc/prometheus/prometheus.yml \\
  prom/prometheus

# Access: http://localhost:9090
```

**Breaking Down Docker Command:**

**Volume Mount:**
```bash
-v $(pwd)/observability/prometheus.yml:/etc/prometheus/prometheus.yml
```
- `$(pwd)` → Current directory (expands to absolute path)
- `:` separator between host:container paths
- Overwrites default config inside container

**Why `-d`?**
- Detached mode (runs in background)
- Doesn't block terminal

**Verify it works:**
```bash
# Check if Prometheus is up
curl http://localhost:9090/-/healthy

# View targets
curl http://localhost:9090/api/v1/targets
```

---

## 12.3 Instrumenting Services with Metrics

### Step 12.3: Add Prometheus Client to API Gateway

**Action:** Install dependency and add metrics to `services/api-gateway/app.py`:

```bash
# Add to requirements.txt
prometheus-client==0.19.0
```

```python
from prometheus_client import Counter, Histogram, generate_latest
import time

# Define metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_latency = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    latency = time.time() - request.start_time
    
    request_count.labels(
        request.method,
        request.path,
        response.status_code
    ).inc()
    
    request_latency.labels(
        request.method,
        request.path
    ).observe(latency)
    
    return response

@app.route('/metrics')
def metrics():
    return generate_latest()
```

**Breaking Down Prometheus Instrumentation:**

**Counter Metric:**
```python
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
```
- `Counter`: Monotonically increasing value (never decreases)
- First arg: Metric name (must follow naming convention)
- Second arg: Help text (description)
- Third arg: Labels (dimensions for filtering)

**Why Labels?**
- Allows querying: "How many GET /api/data/NIFTY requests returned 200?"
- Multi-dimensional data

**Histogram Metric:**
```python
request_latency = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)
```
- `Histogram`: Tracks distribution of values
- Automatically creates buckets: 0.005s, 0.01s, 0.025s, ... 10s
- Used for percentile calculations (p50, p95, p99)

**Flask Hooks:**
```python
@app.before_request
def before_request():
    request.start_time = time.time()
```
- Runs before every request
- Stores start time on request object

```python
@app.after_request
def after_request(response):
```
- Runs after every request (but before sending response)
- Calculates latency and records metrics

**Recording Metrics:**
```python
request_count.labels(
    request.method,     # "GET"
    request.path,       # "/api/data/NIFTY"
    response.status_code # 200
).inc()
```
- `.labels()` → Specify label values
- `.inc()` → Increment counter by 1

**Recording Histogram:**
```python
request_latency.labels(
    request.method,
    request.path
).observe(latency)
```
- `.observe(value)` → Record a value
- Prometheus automatically puts it in correct bucket

**Metrics Endpoint:**
```python
@app.route('/metrics')
def metrics():
    return generate_latest()
```
- Exposes metrics in Prometheus text format
- Prometheus scrapes this endpoint every 15s

**Example Metrics Output:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/data/NIFTY",status="200"} 1523.0

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1",method="GET",endpoint="/api/data/NIFTY"} 1450.0
http_request_duration_seconds_bucket{le="0.5",method="GET",endpoint="/api/data/NIFTY"} 1520.0
http_request_duration_seconds_sum{method="GET",endpoint="/api/data/NIFTY"} 89.5
http_request_duration_seconds_count{method="GET",endpoint="/api/data/NIFTY"} 1523.0
```

**Reading Histogram:**
- `_bucket{le="0.1"}` = 1450 requests completed in ≤ 0.1s
- `_sum` = Total time spent (89.5s)
- `_count` = Total requests (1523)
- Average latency = sum / count = 89.5 / 1523 = 0.058s

---

## 12.4 Setting Up Grafana

### Step 12.4: Run Grafana

**Action:** Start Grafana with Docker:

```bash
docker run -d \\
  --name grafana \\
  -p 3000:3000 \\
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \\
  grafana/grafana

# Access: http://localhost:3000 (admin/admin)
```

**Environment Variable:**
```bash
-e "GF_SECURITY_ADMIN_PASSWORD=admin"
```
- Sets admin password
- Default would be random (hard to find)

---

### Step 12.5: Connect Prometheus to Grafana

**Action:** Add Prometheus as a data source:

1. Navigate to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL: `http://prometheus:9090` (or `http://localhost:9090` if not in Docker network)
5. Click **Save & Test**

**Why `prometheus:9090`?**
- Docker Compose creates network
- Services can reference each other by name
- Alternative: Use bridge network IP

---

### Step 12.6: Create Dashboard

**Action:** Create panels to visualize metrics:

**Panel 1: Request Rate**
```promql
rate(http_requests_total[5m])
```
- `rate(counter[5m])` → Requests per second (over 5min window)
- Shows request throughput

**Panel 2: Latency Percentiles**
```promql
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```
- `histogram_quantile(0.95, ...)` → 95th percentile latency
- "95% of requests complete in X seconds"

**Panel 3: Error Rate**
```promql
rate(http_requests_total{status=~"5.."}[5m])
```
- `status=~"5.."` → Regex matching 500-599
- Tracks 5xx errors per second

**Panel 4: Active WebSocket Connections**
```promql
websocket_connections_active
```
(Requires instrumenting WebSocket service)

---

## 12.5 Log Aggregation with Loki (Optional)

### Step 12.7: Run Loki and Promtail

**Action:** Deploy Loki stack:

```bash
# Run Loki
docker run -d \\
  --name loki \\
  -p 3100:3100 \\
  grafana/loki

# Run Promtail (log shipper)
docker run -d \\
  --name promtail \\
  -v $(pwd)/observability/promtail-config.yaml:/etc/promtail/config.yaml \\
  -v /var/log:/var/log \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  grafana/promtail
```

**What is Promtail?**
- Log shipper (like Filebeat or Fluentd)
- Reads logs from files/Docker
- Sends to Loki

---

### Step 12.8: Configure Promtail

**Action:** Create `observability/promtail-config.yaml`:

```yaml
server:
  http_listen_port: 9080

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
```

**Docker Socket Mount:**
```bash
-v /var/run/docker.sock:/var/run/docker.sock
```
- Allows Promtail to query Docker API
- Autodiscover containers
- Read container logs

**Query Loki Logs in Grafana:**
```
{container="deltastream-worker"} |= "error"
```
- Filter by container name
- Search for "error" in logs

```
{container="deltastream-api-gateway"} | json | status_code >= 500
```
- Parse JSON logs
- Filter by field value

---

## 12.6 Alerting

### Step 12.9: Create Alert Rules

**Action:** Create `observability/alerts.yml`:

```yaml
groups:
  - name: deltastream_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "{{ $labels.service }} error rate is {{ $value }}"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"

      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 1000
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue backlog"
```

**Breaking Down Alert Syntax:**

**Alert Condition:**
```yaml
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
```
- Evaluates every 15s (from global config)
- If true for `for: 5m` → fires alert

**For Duration:**
```yaml
for: 5m
```
- Alert must be true for 5 continuous minutes
- Prevents flapping (brief spikes don't alert)

**Labels:**
```yaml
labels:
  severity: critical
```
- Used for routing (critical → PagerDuty, warning → Slack)

**Annotations:**
```yaml
annotations:
  description: "{{ $labels.service }} error rate is {{ $value }}"
```
- `{{ $labels.service }}` → Templating (replaced with actual service name)
- `{{ $value }}` → Current metric value

---

## Summary

You've set up **Complete Observability** for DeltaStream:

✅ **Prometheus** - Scraping metrics every 15s
✅ **Grafana** - Visualizing request rate, latency, errors
✅ **Instrumentation** - Added metrics to API Gateway
✅ **Loki** (Optional) - Centralized log aggregation
✅ **Alerting** - Proactive detection of issues

**Key Learnings:**
- Counter vs Histogram metrics
- Flask before/after request hooks
- Prometheus query language (PromQL)
- Histogram percentile calculations
- Alert rule syntax
- Docker volume mounts for config

**Production Checklist:**
- [ ] All services instrumented
- [ ] Dashboards for each service
- [ ] Alerts configured
- [ ] Alert routing (Slack/PagerDuty)
- [ ] Retention policies set

**Next:** Chapter 13 covers Trade Simulator and production considerations!

---
