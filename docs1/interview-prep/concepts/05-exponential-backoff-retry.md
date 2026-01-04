### **5. EXPONENTIAL BACKOFF RETRY**

**What it is:**
When a task fails, retry it with increasing delays: 5s → 10s → 20s → 40s

**Why exponential:**
- Prevents overwhelming failing service with retries
- Gives time for transient issues to resolve (network hiccup, DB lock)
- Reduces thundering herd problem

**In your code:**
```python
celery_app.conf.update(
    task_autoretry_for=(Exception,),           # Retry on any exception
    task_retry_kwargs={'max_retries': 3, 'countdown': 5},  # Max 3, start at 5s
    task_default_retry_delay=5,
)
```

**Retry timeline:**
```
Attempt 1: Fails → Wait 5s
Attempt 2: Fails → Wait 10s (2^1 * 5s)
Attempt 3: Fails → Wait 20s (2^2 * 5s)
Attempt 4: Fails → Send to DLQ
```

**Better than fixed retry:**
- Fixed: Retry every 5s → Can overwhelm system
- Exponential: Increasing delays → Gives system breathing room

---
