### **6. DEAD LETTER QUEUE (DLQ)**

**What it is:**
A special queue where messages that failed after all retry attempts are stored for later inspection/manual handling.

**In your code:**
```python
def on_failure(self, exc, task_id, args, kwargs, einfo):
    # After max retries exhausted, send to DLQ
    dlq_message = {
        'task_id': task_id,
        'task_name': self.name,
        'error': str(exc),
        'args': args,
        'timestamp': datetime.now().isoformat()
    }
    redis_client.lpush('dlq:enrichment', json.dumps(dlq_message))
```

**Why DLQ is critical:**
- **No data loss**: Failed messages aren't discarded
- **Debugging**: Inspect what went wrong
- **Replay capability**: Can manually re-process later
- **Alerting**: Monitor DLQ size to detect issues

**Viewing DLQ:**
```bash
redis-cli LRANGE dlq:enrichment 0 -1
```

---
