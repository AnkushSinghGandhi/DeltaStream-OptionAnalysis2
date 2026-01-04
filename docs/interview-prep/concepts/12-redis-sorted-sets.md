### **12. REDIS SORTED SETS**

**What it is:**
Redis data structure where each member has a score, automatically sorted by score.

**In your code:**
```python
# Store IV surface data (score = strike price)
redis_client.zadd(
    f"iv_surface:{product}",
    {
        json.dumps({'strike': 21500, 'iv': 0.25, 'expiry': '2025-01-25'}): 21500
    }
)

# Query by strike range
redis_client.zrangebyscore(f"iv_surface:{product}", 21000, 22000)
```

**Use cases:**
- Leaderboards (score = points)
- Time-series (score = timestamp)
- Volatility surfaces (score = strike price)

**Why sorted sets for IV:**
- Efficient range queries (strikes between X and Y)
- Automatically sorted by strike
- O(log N) insert/lookup

---
