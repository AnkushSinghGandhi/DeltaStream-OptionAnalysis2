### **7. TASK IDEMPOTENCY**

**What it is:**
Ensuring a task can be executed multiple times without changing the result beyond the first execution.

**Why it matters:**
- Network issues can cause duplicate messages
- Retries can process same task twice
- Worker crashes can lead to re-processing

**In your code:**
```python
def process_underlying_tick(tick_data):
    tick_id = tick_data['tick_id']
    product = tick_data['product']
    
    # Check if already processed
    idempotency_key = f"processed:underlying:{product}:{tick_id}"
    if redis_client.exists(idempotency_key):
        return  # Already processed, skip
    
    # Process the tick
    store_in_mongodb(tick_data)
    update_cache(tick_data)
    
    # Mark as processed (TTL 1 hour)
    redis_client.setex(idempotency_key, 3600, '1')
```

**Without idempotency:**
- Same tick processed twice → Duplicate DB entries
- Analytics calculated multiple times → Incorrect metrics

---
