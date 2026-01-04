### **9. REDIS CACHING - CACHE-ASIDE PATTERN**

**What it is:**
Application code is responsible for reading from cache and updating it.

**Flow:**
```
1. Request arrives
2. Check cache (Redis)
   ├─ Cache HIT → Return cached data
   └─ Cache MISS → Query database → Store in cache → Return data
```

**In your code:**
```python
def get_underlying(product):
    # Try cache first
    cache_key = f"latest:underlying:{product}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)  # Cache HIT
    
    # Cache MISS - query database
    data = db.underlying_ticks.find_one({'product': product})
    
    # Update cache with TTL
    redis_client.setex(cache_key, 300, json.dumps(data))  # 5 min TTL
    
    return data
```

**Alternative patterns:**
- **Write-through**: Write to cache + DB simultaneously
- **Write-behind**: Write to cache, async write to DB later

**Why cache-aside:**
- Application controls what/when to cache
- Read-heavy workloads (your use case)
- DB is source of truth

---
