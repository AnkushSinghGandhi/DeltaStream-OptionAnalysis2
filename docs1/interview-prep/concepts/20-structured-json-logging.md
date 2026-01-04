### **20. STRUCTURED JSON LOGGING**

**What it is:**
Logging in JSON format with structured fields rather than plain text.

**Traditional logging:**
```
ERROR - Failed to process tick for NIFTY at 2025-01-15 10:30:00
```

**Structured JSON logging:**
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "error",
  "service": "worker-enricher",
  "event": "tick_processing_failed",
  "product": "NIFTY",
  "tick_id": 12345,
  "error": "MongoDB connection timeout",
  "trace_id": "abc123"
}
```

**In your code:**
```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

logger.error(
    "tick_processing_failed",
    product="NIFTY",
    tick_id=12345,
    error=str(e)
)
```

**Benefits:**
- **Searchable**: Query logs by any field (show me all NIFTY errors)
- **Aggregatable**: Count errors by product, service, etc.
- **Machine-readable**: Easy to parse by log aggregators (ELK, Splunk)
- **Contextual**: Include request ID, user ID, trace ID

---
