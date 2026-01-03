### **22. OBSERVABILITY STACK**

**What it is:**
Combination of logging, metrics, and tracing to understand system behavior.

**Three pillars:**

**1. Logs (Structured JSON)**
- What happened: "Order processed"
- When: "2025-01-15T10:30:00Z"
- Context: product, user_id, error details

**2. Metrics (Prometheus)**
- How many: Requests per second
- How fast: Latency percentiles (p50, p95, p99)
- How much: CPU, memory, disk usage

**3. Traces (Optional - Jaeger/Zipkin)**
- Request flow across services
- Latency breakdown per service
- Bottleneck identification

**Your observability:**
- Structured logging (structlog)
- Metrics endpoints (/health, /metrics)
- Health checks (MongoDB ping, Redis ping)

---
