### **21. PROMETHEUS METRICS**

**What it is:**
Time-series monitoring system that scrapes metrics from services.

**Typical metrics in your services:**
```python
# Counter (always increasing)
requests_total{service="api-gateway", endpoint="/api/data/products"} 1523

# Gauge (can go up/down)
connected_websocket_clients{service="socket-gateway"} 47

# Histogram (distributions)
request_duration_seconds{service="storage"} 0.025
```

**In your code:**
```python
@app.route('/metrics')
def metrics():
    return {
        'total_clients': len(connected_clients),
        'rooms': room_counts,
        'messages_sent': message_counter
    }
```

**Why Prometheus:**
- Real-time monitoring
- Alerting (PagerDuty if CPU > 80%)
- Grafana dashboards
- Trend analysis

---
