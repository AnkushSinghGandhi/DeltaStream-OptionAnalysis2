### **11. MULTI-LEVEL CACHING (3 CACHE LEVELS)**

**What it is:**
Multiple cache layers with different data and TTLs.

**Your 3 levels:**

**Level 1: Latest Data (Real-time, 5min TTL)**
```python
latest:underlying:{product}      # Latest price
latest:option:{symbol}           # Latest quote
latest:chain:{product}:{expiry}  # Latest chain
```

**Level 2: Computed Data (Analytics, varies)**
```python
ohlc:{product}:{window}m         # OHLC windows
volatility_surface:{product}     # IV surface
```

**Level 3: Operational Data (1hr TTL)**
```python
processed:underlying:{product}:{tick_id}  # Idempotency tracking
```

**Why multi-level:**
- Different data has different freshness requirements
- Separate hot path from cold path
- Optimize memory usage

---
