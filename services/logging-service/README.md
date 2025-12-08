# Logging Service

## Overview

Centralized logging service that:
- Ingests structured JSON logs
- Persists logs to files
- Provides query API
- Demonstrates log forwarding patterns

## Endpoints

### POST /logs
Ingest a log entry.

**Body:**
```json
{
  "service": "api-gateway",
  "level": "info",
  "message": "Request processed",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### GET /logs/{service}
Retrieve logs for a service.

**Query Params:**
- `limit`: Max number of entries (default: 100)

**Example:**
```bash
curl "http://localhost:8005/logs/api-gateway?limit=50"
```

## Log Forwarding

### To Loki (Grafana)

**Using Promtail:**

1. Install Promtail
2. Configure `promtail-config.yaml`:
```yaml
server:
  http_listen_port: 9080

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: option-aro
    static_configs:
      - targets:
          - localhost
        labels:
          job: option-aro
          __path__: /app/logs/*.log
```

3. Run Promtail:
```bash
promtail -config.file=promtail-config.yaml
```

### To Elasticsearch

**Using Filebeat:**

1. Install Filebeat
2. Configure `filebeat.yml`:
```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /app/logs/*.log
    json.keys_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

3. Run Filebeat:
```bash
filebeat -e -c filebeat.yml
```

## Production Usage

Instead of pushing logs to this service via API,
use log shippers (Promtail/Filebeat) to tail log files
and forward to centralized log stores.

All services already emit structured JSON logs to stdout,
which can be collected by Docker/Kubernetes log drivers.
