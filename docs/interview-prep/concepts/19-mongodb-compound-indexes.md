### **19. MONGODB COMPOUND INDEXES**

**What it is:**
Index on multiple fields to optimize queries filtering/sorting by those fields.

**In your code:**
```python
# Compound index on (product + timestamp)
db.underlying_ticks.create_index([
    ('product', ASCENDING),
    ('timestamp', DESCENDING)
])
```

**Query optimization:**
```python
# This query uses the compound index efficiently
db.underlying_ticks.find({
    'product': 'NIFTY',
    'timestamp': {'$gte': start_time}
}).sort('timestamp', -1)

# Without index: Full collection scan (slow)
# With index: Index seek (fast)
```

**Your 3 indexed collections:**
1. `underlying_ticks`: (product, timestamp)
2. `option_quotes`: (product, timestamp) and (symbol, timestamp)
3. `option_chains`: (product, expiry, timestamp)

**Why compound over single:**
- Single index on `product`: Can filter by product, but sort is slow
- Compound index on `(product, timestamp)`: Fast filter + fast sort

---
