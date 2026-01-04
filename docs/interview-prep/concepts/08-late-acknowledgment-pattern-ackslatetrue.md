### **8. LATE ACKNOWLEDGMENT PATTERN (acks_late=True)**

**What it is:**
Task is acknowledged to broker only AFTER successful completion, not when worker receives it.

**Two modes:**
```
Early Ack (default):
Worker receives task → Send ACK → Process task → Done
Problem: If worker crashes during processing, task is lost

Late Ack (acks_late=True):
Worker receives task → Process task → Send ACK → Done
Benefit: If worker crashes, task is NOT acked, so broker re-queues it
```

**In your code:**
```python
celery_app.conf.update(
    task_acks_late=True,  # Don't ack until task completes
)
```

**Why it matters:**
- Prevents message loss on worker crash
- Ensures at-least-once delivery
- Combined with idempotency = exactly-once processing

---
