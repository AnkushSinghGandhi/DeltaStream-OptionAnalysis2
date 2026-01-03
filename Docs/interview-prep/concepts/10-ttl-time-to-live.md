### **10. TTL (TIME TO LIVE)**

**What it is:**
Automatic expiration of cached data after specified time.

**In your code:**
```python
# Cache with 5-minute TTL
redis_client.setex(f"latest:underlying:{product}", 300, json.dumps(data))
                                                    ^^^
                                                  300 seconds = 5 min
```

**Why TTL:**
- **Memory management**: Old data auto-deleted
- **Freshness**: Forces re-fetch of stale data
- **No manual invalidation**: Redis handles cleanup

**TTL strategy in your project:**
```
Hot data (latest prices): 5 min TTL
OHLC windows: Window duration TTL (5min window = 5min TTL)
Idempotency keys: 1 hour TTL
```

---
