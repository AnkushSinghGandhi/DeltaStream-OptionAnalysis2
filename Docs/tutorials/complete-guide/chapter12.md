## Part 12: Observability & Monitoring

### Learning Objectives

By the end of Part 12, you will understand:

1. **Prometheus** - Metrics collection and storage
2. **Grafana** - Metrics visualization
3. **Loki** - Log aggregation
4. **Alerting** - Proactive issue detection
5. **Distributed tracing** - Request flow visualization

---

### 12.1 Prometheus Setup

`observability/prometheus.yml`:

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

**Run Prometheus:**
```bash
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/observability/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Access: http://localhost:9090
```

---

### 12.2 Instrumenting Services

Add to `services/api-gateway/app.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest
import time

# Metrics
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

**Example metrics:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/data/underlying/NIFTY",status="200"} 1523.0

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1",method="GET",endpoint="/api/data/underlying/NIFTY"} 1450.0
http_request_duration_seconds_sum{method="GET",endpoint="/api/data/underlying/NIFTY"} 89.5
```

---

### 12.3 Grafana Dashboards

```bash
# Run Grafana
docker run -d \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  grafana/grafana

# Access: http://localhost:3000 (admin/admin)
```

**Add Prometheus data source:**
1. Configuration → Data Sources
2. Add Prometheus
3. URL: `http://prometheus:9090`

**Import dashboard:**
- Upload `observability/grafana-dashboard.json`

**Key panels:**
- Request rate (requests/sec)
- Latency percentiles (p50, p95, p99)
- Error rate
- Active WebSocket connections
- Celery queue length

---

### 12.4 Loki for Log Aggregation

```bash
# Run Loki
docker run -d -p 3100:3100 grafana/loki

# Run Promtail (log shipper)
docker run -d \
  -v $(pwd)/observability/promtail-config.yaml:/etc/promtail/config.yaml \
  -v /var/log:/var/log \
  grafana/promtail
```

`observability/promtail-config.yaml`:

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

**Query logs in Grafana:**
```
{container="deltastream-worker"} |= "error"
{container="deltastream-api-gateway"} | json | status_code >= 500
```

---

### 12.5 Alerting Rules

`observability/alerts.yml`:

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

---

