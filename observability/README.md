# Observability

Monitoring and logging configurations for DeltaStream.

## Components

### Prometheus
Metrics collection and alerting.

```bash
# Run Prometheus
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Access at http://localhost:9090
```

### Grafana
Metrics visualization.

```bash
# Run Grafana
docker run -d \
  -p 3000:3000 \
  grafana/grafana

# Import grafana-dashboard.json
# Access at http://localhost:3000 (admin/admin)
```

### Loki + Promtail
Log aggregation.

```bash
# Run Loki
docker run -d -p 3100:3100 grafana/loki

# Run Promtail
docker run -d \
  -v $(pwd)/promtail-config.yaml:/etc/promtail/config.yaml \
  -v /var/log:/var/log \
  grafana/promtail
```

### Elasticsearch + Filebeat
Alternative log aggregation.

```bash
# Run Elasticsearch
docker run -d \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  elasticsearch:8.10.0

# Run Filebeat
docker run -d \
  -v $(pwd)/filebeat.yml:/usr/share/filebeat/filebeat.yml \
  -v /var/lib/docker/containers:/var/lib/docker/containers:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  elastic/filebeat:8.10.0
```

## Metrics

### Application Metrics
- Request rate and latency
- WebSocket connections
- Celery task throughput
- Feed generation rate

### Infrastructure Metrics
- CPU and memory usage
- Redis memory and connections
- MongoDB operations
- Network I/O

## Logs

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

## Alerts

Create alerts in Prometheus:

```yaml
groups:
  - name: option-aro
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: WorkerQueueBacklog
        expr: celery_queue_length > 1000
        for: 10m
        annotations:
          summary: "Celery queue backlog"
```

## Production Setup

1. Deploy Prometheus with persistent storage
2. Configure Grafana dashboards
3. Set up Loki/ELK stack
4. Configure alerts and notifications
5. Enable distributed tracing (Jaeger)
