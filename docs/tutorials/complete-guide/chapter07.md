# Part 7: Analytics Service

The Analytics Service provides advanced market analysis and aggregations over historical data. Unlike the Worker Enricher which calculates metrics in real-time, this service queries MongoDB to provide trends, surfaces, and deep analysis.

---

## 7.1 Understanding Analytics vs Real-time Processing

**Key Difference:**

- **Worker Enricher**: Real-time calculations on incoming data (PCR, Max Pain) → stores in MongoDB
- **Analytics Service**: Aggregates historical data from MongoDB → provides trends and insights

**What Analytics Service Provides:**
- PCR trends over time
- Volatility surface (IV across strikes/expiries)
- Max Pain analysis
- OI build-up interpretation
- OHLC data

---

## 7.2 Project Setup

### Step 7.1: Create Directory Structure

**Action:** Create the analytics service directory:

```bash
mkdir -p services/analytics
cd services/analytics
```

### Step 7.2: Create Requirements File

**Action:** Create `requirements.txt`:

```txt
flask==3.0.0
flask-cors==4.0.0
pymongo==4.6.0
redis==5.0.1
structlog==24.1.0
```

**Why these dependencies?**
- `flask`: REST API framework
- `flask-cors`: Enable cross-origin requests from frontend
- `pymongo`: MongoDB querying and aggregation
- `redis`: Cache access for fast data retrieval
- `structlog`: Consistent logging with Worker Enricher

---

## 7.3 Building the Service

### Step 7.3: Create Base Application

**Action:** Create `app.py` and add imports and configuration:

```python
#!/usr/bin/env python3
"""
Analytics Service

Provides aggregation and analysis endpoints:
- PCR trends
- Volatility surface
- Max Pain analysis
- OI build-up analysis
- Historical metrics
"""

import os
import json
import redis
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
import structlog

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/deltastream')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'analytics')
PORT = int(os.getenv('PORT', '8004'))

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Database clients
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['deltastream']
```

**Why port 8004?**
- 8000: API Gateway
- 8001: Storage Service
- 8002: Auth Service
- 8003: (Reserved)
- **8004: Analytics Service** ✓

---

### Step 7.4: Add Health Check Endpoint

**Action:** Add health check:

```python
@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200
```

**Why health checks?**
- Kubernetes liveness probes
- Load balancer health monitoring
- Docker Compose dependency waiting

---

### Step 7.5: Implement PCR Analysis Endpoint

**Action:** Add PCR trend endpoint:

```python
@app.route('/pcr/<product>', methods=['GET'])
def get_pcr_analysis(product):
    """
    Get PCR (Put-Call Ratio) analysis.
    
    Query params:
    - expiry: Specific expiry (optional)
    - history: Include historical data (true/false)
    """
    try:
        expiry = request.args.get('expiry')
        include_history = request.args.get('history', 'false').lower() == 'true'
        
        result = {'product': product}
        
        # Get latest PCR from cache
        if expiry:
            cache_key = f"latest:pcr:{product}:{expiry}"
            cached = redis_client.get(cache_key)
            if cached:
                result['latest'] = json.loads(cached)
        else:
            # Get latest for all expiries
            pattern = f"latest:pcr:{product}:*"
            keys = redis_client.keys(pattern)
            latest_data = []
            for key in keys:
                cached = redis_client.get(key)
                if cached:
                    data = json.loads(cached)
                    expiry_date = key.split(':')[-1]
                    data['expiry'] = expiry_date
                    latest_data.append(data)
            result['latest'] = latest_data
        
        # Get historical PCR if requested
        if include_history:
            query = {'product': product}
            if expiry:
                query['expiry'] = expiry
            
            chains = list(db.option_chains.find(
                query,
                {'_id': 0, 'product': 1, 'expiry': 1, 'pcr_oi': 1, 
                 'pcr_volume': 1, 'timestamp': 1}
            ).sort('timestamp', DESCENDING).limit(100))
            
            for chain in chains:
                if 'timestamp' in chain:
                    chain['timestamp'] = chain['timestamp'].isoformat()
            
            result['history'] = chains
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error("pcr_analysis_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500
```

**Breaking Down the Syntax:**

**Flask Route Decorator:**
```python
@app.route('/pcr/<product>', methods=['GET'])
def get_pcr_analysis(product):
```
- `<product>` = URL parameter (e.g., `/pcr/NIFTY` → product="NIFTY")
- `methods=['GET']` = Only allow GET requests
- `product` parameter automatically passed to function

**Query Parameters:**
```python
expiry = request.args.get('expiry')
include_history = request.args.get('history', 'false').lower() == 'true'
```
- `request.args.get('expiry')` → Gets `?expiry=2024-01-25` from URL
- `request.args.get('history', 'false')` → Returns 'false' if not provided (default)
- `.lower() == 'true'` → Converts to boolean (handles "True", "TRUE", "true")

**Redis Key Pattern Matching:**
```python
pattern = f"latest:pcr:{product}:*"
keys = redis_client.keys(pattern)
```
- `*` = Wildcard (matches anything)
- Example: `latest:pcr:NIFTY:*` matches:
  - `latest:pcr:NIFTY:2024-01-25`
  - `latest:pcr:NIFTY:2024-02-01`
  - etc.

**String Splitting:**
```python
expiry_date = key.split(':')[-1]
```
- `key = "latest:pcr:NIFTY:2024-01-25"`
- `split(':')` → `['latest', 'pcr', 'NIFTY', '2024-01-25']`
- `[-1]` → Last element = `'2024-01-25'`

**MongoDB Query Syntax:**
```python
db.option_chains.find(
    {'product': product},  # Filter
    {'_id': 0, 'timestamp': 1}  # Projection (which fields to return)
).sort('timestamp', DESCENDING).limit(100)
```
- Filter: `{'product': product}` → WHERE product = ?
- Projection: `{'_id': 0}` = exclude _id, `{'timestamp': 1}` = include timestamp
- `DESCENDING` = newest first
- `limit(100)` = max 100 results

**List Comprehension:**
```python
for chain in chains:
    if 'timestamp' in chain:
        chain['timestamp'] = chain['timestamp'].isoformat()
```
- Loops through each chain
- Checks if 'timestamp' field exists
- Converts datetime object to ISO string (e.g., "2024-01-25T10:30:00")

**Why `.isoformat()`?**
- MongoDB stores datetime as BSON datetime object
- JSON doesn't support datetime
- `.isoformat()` converts to string: `"2024-01-25T10:30:00"`



**Non-trivial concept - Dual Data Source:**

Why query both Redis AND MongoDB?

**Redis (Cache):**
- Latest PCR values (fast access)
- Updated by Worker Enricher in real-time
- Volatile (lost on restart)

**MongoDB (Historical):**
- PCR values over time (complete history)
- Persistent storage
- Enables trend analysis

**Pattern:**
```
Latest data → Redis (fast)
Historical data → MongoDB (complete)
```

**Example API Call:**
```bash
GET /pcr/NIFTY?expiry=2024-01-25&history=true
```

**Response:**
```json
{
  "product": "NIFTY",
  "latest": {"pcr_oi": 1.25, "pcr_volume": 0.89},
  "history": [
    {"timestamp": "2024-01-25T10:00:00", "pcr_oi": 1.25},
    {"timestamp": "2024-01-25T09:55:00", "pcr_oi": 1.22},
    ...
  ]
}
```

---

### Step 7.6: Implement Volatility Surface Endpoint

**Action:** Add volatility surface calculation:

```python
@app.route('/volatility-surface/<product>', methods=['GET'])
def get_volatility_surface(product):
    """
    Get volatility surface (IV across strikes and expiries).
    """
    try:
        # Try cache first
        cache_key = f"volatility_surface:{product}"
        cached = redis_client.get(cache_key)
        if cached:
            return jsonify(json.loads(cached)), 200
        
        # Calculate from recent data
        recent_time = datetime.now() - timedelta(minutes=5)
        quotes = list(db.option_quotes.find({
            'product': product,
            'timestamp': {'$gte': recent_time}
        }))
        
        if not quotes:
            return jsonify({
                'product': product,
                'error': 'No recent data available'
            }), 404
        
        # Group by expiry
        expiry_groups = {}
        for quote in quotes:
            expiry = quote['expiry']
            if expiry not in expiry_groups:
                expiry_groups[expiry] = []
            expiry_groups[expiry].append(quote)
        
        # Build surface
        surface = {
            'product': product,
            'expiries': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for expiry, expiry_quotes in expiry_groups.items():
            expiry_quotes.sort(key=lambda x: x['strike'])
            
            strikes = [q['strike'] for q in expiry_quotes]
            call_ivs = [q['iv'] for q in expiry_quotes if q['option_type'] == 'CALL']
            put_ivs = [q['iv'] for q in expiry_quotes if q['option_type'] == 'PUT']
            
            avg_iv = sum([q['iv'] for q in expiry_quotes]) / len(expiry_quotes)
            
            surface['expiries'].append({
                'expiry': expiry,
                'strikes': list(set(strikes)),
                'call_ivs': call_ivs,
                'put_ivs': put_ivs,
                'avg_iv': round(avg_iv, 4),
                'num_quotes': len(expiry_quotes)
            })
        
        return jsonify(surface), 200
        
    except Exception as e:
        logger.error("volatility_surface_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500
```

**Breaking Down Volatility Surface Logic:**

**Datetime Query:**
```python
recent_time = datetime.now() - timedelta(minutes=5)
quotes = list(db.option_quotes.find({
    'timestamp': {'$gte': recent_time}
}))
```
- `timedelta(minutes=5)` → 5 minutes ago
- `{'$gte': recent_time}` → MongoDB "greater than or equal" operator
- Equivalent SQL: `WHERE timestamp >= NOW() - INTERVAL 5 MINUTE`

**Grouping Data (Dictionary Pattern):**
```python
expiry_groups = {}
for quote in quotes:
    expiry = quote['expiry']
    if expiry not in expiry_groups:
        expiry_groups[expiry] = []
    expiry_groups[expiry].append(quote)
```

**What this does:**
```python
# Before (flat list):
quotes = [
    {expiry: '2024-01-25', strike: 21000, iv: 18.5},
    {expiry: '2024-01-25', strike: 21050, iv: 19.2},
    {expiry: '2024-02-01', strike: 21000, iv: 17.8},
]

# After (grouped by expiry):
expiry_groups = {
    '2024-01-25': [
        {strike: 21000, iv: 18.5},
        {strike: 21050, iv: 19.2}
    ],
    '2024-02-01': [
        {strike: 21000, iv: 17.8}
    ]
}
```

**Lambda Functions for Sorting:**
```python
expiry_quotes.sort(key=lambda x: x['strike'])
```
- `lambda x: x['strike']` → Anonymous function that returns strike value
- Sorts options by strike price (ascending)
- Equivalent to:
```python
def get_strike(x):
    return x['strike']
expiry_quotes.sort(key=get_strike)
```

**List Comprehension with Filter:**
```python
call_ivs = [q['iv'] for q in expiry_quotes if q['option_type'] == 'CALL']
```
- Loop through `expiry_quotes`
- For each `q`, if it's a CALL
- Extract `q['iv']` and add to list
- Result: `[18.5, 19.2, 20.1, ...]`

**Set for Unique Values:**
```python
strikes: list(set(strikes))
```
- `set(strikes)` → Removes duplicates: `{21000, 21050, 21100}`
- `list()` → Converts back to list: `[21000, 21050, 21100]`



**What is a Volatility Surface?**

Imagine a 3D plot:
- **X-axis**: Strike prices (18000, 18500, 19000...)
- **Y-axis**: Expiries (Jan 25, Feb 1, Feb 8...)
- **Z-axis**: Implied Volatility (IV)

The surface shows how IV changes across strikes and time.

**Why is this useful?**
- Identify IV skew (OTM puts usually have higher IV)
- See which expiries are more expensive
- Detect anomalies (unusually high/low IV)

**Example Output:**
```json
{
  "product": "NIFTY",
  "expiries": [
    {
      "expiry": "2024-01-25",
      "strikes": [21000, 21050, 21100, ...],
      "call_ivs": [18.5, 19.2, 20.1, ...],
      "put_ivs": [22.3, 21.5, 20.8, ...],
      "avg_iv": 19.75
    }
  ]
}
```

---

### Step 7.7: Implement Max Pain Analysis Endpoint

**Action:** Add max pain endpoint:

```python
@app.route('/max-pain/<product>', methods=['GET'])
def get_max_pain_analysis(product):
    """
    Get max pain analysis.
    
    Query params:
    - expiry: Specific expiry (required)
    """
    try:
        expiry = request.args.get('expiry')
        if not expiry:
            return jsonify({'error': 'Expiry parameter required'}), 400
        
        # Get latest chain
        chain = db.option_chains.find_one(
            {'product': product, 'expiry': expiry},
            sort=[('timestamp', DESCENDING)]
        )
        
        if not chain:
            return jsonify({
                'product': product,
                'expiry': expiry,
                'error': 'No data available'
            }), 404
        
        result = {
            'product': product,
            'expiry': expiry,
            'max_pain_strike': chain['max_pain_strike'],
            'spot_price': chain['spot_price'],
            'distance_from_spot': chain['max_pain_strike'] - chain['spot_price'],
            'distance_pct': round(
                ((chain['max_pain_strike'] - chain['spot_price']) / chain['spot_price']) * 100,
                2
            ),
            'total_call_oi': chain['total_call_oi'],
            'total_put_oi': chain['total_put_oi'],
            'timestamp': chain['timestamp'].isoformat()
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error("max_pain_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500
```

**Max Pain Interpretation:**

If Max Pain = 21500 and Spot = 21600:
- **Distance**: -100 points
- **Distance %**: -0.47%

**What this means:**
- Options sellers want price to move toward 21500
- If it stays at 21600, they lose money
- Gravitational pull toward Max Pain

---

### Step 7.8: Implement OI Build-up Analysis

**Action:** Add OI build-up interpretation:

```python
@app.route('/oi-buildup/<product>', methods=['GET'])
def get_oi_buildup(product):
    """
    Get open interest build-up analysis.
    
    Query params:
    - expiry: Specific expiry (required)
    """
    try:
        expiry = request.args.get('expiry')
        if not expiry:
            return jsonify({'error': 'Expiry parameter required'}), 400
        
        # Get latest chain
        chain = db.option_chains.find_one(
            {'product': product, 'expiry': expiry},
            sort=[('timestamp', DESCENDING)]
        )
        
        if not chain:
            return jsonify({
                'product': product,
                'expiry': expiry,
                'error': 'No data available'
            }), 404
        
        spot = chain['spot_price']
        calls = chain['calls']
        puts = chain['puts']
        
        # Analyze build-up by strike zones
        analysis = {
            'product': product,
            'expiry': expiry,
            'spot_price': spot,
            'call_buildup': {
                'itm': sum(c['open_interest'] for c in calls if c['strike'] < spot),
                'atm': sum(c['open_interest'] for c in calls if abs(c['strike'] - spot) < spot * 0.01),
                'otm': sum(c['open_interest'] for c in calls if c['strike'] > spot)
            },
            'put_buildup': {
                'itm': sum(p['open_interest'] for p in puts if p['strike'] > spot),
                'atm': sum(p['open_interest'] for p in puts if abs(p['strike'] - spot) < spot * 0.01),
                'otm': sum(p['open_interest'] for p in puts if p['strike'] < spot)
            },
            'timestamp': chain['timestamp'].isoformat()
        }
        
        # Calculate interpretation
        if analysis['call_buildup']['otm'] > analysis['put_buildup']['otm']:
            analysis['interpretation'] = 'Bullish - High OTM call writing'
        elif analysis['put_buildup']['otm'] > analysis['call_buildup']['otm']:
            analysis['interpretation'] = 'Bearish - High OTM put writing'
        else:
            analysis['interpretation'] = 'Neutral - Balanced OI'
        
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error("oi_buildup_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500
```

**Breaking Down OI Build-up Logic:**

**Sum with Generator Expression:**
```python
'itm': sum(c['open_interest'] for c in calls if c['strike'] < spot)
```

**Step-by-step:**
1. Loop through `calls` list
2. For each call `c`, check if `c['strike'] < spot`
3. If true, yield `c['open_interest']`
4. `sum()` adds all yielded values

**Example:**
```python
calls = [
    {'strike': 21000, 'open_interest': 5000},  # ITM (< 21500)
    {'strike': 21200, 'open_interest': 3000},  # ITM
    {'strike': 21600, 'open_interest': 8000},  # OTM (> 21500)
]
spot = 21500

# ITM calculation:
sum(c['open_interest'] for c in calls if c['strike'] < spot)
# = sum([5000, 3000])  # Only 21000 and 21200 match
# = 8000
```

**ATM Range Check:**
```python
abs(c['strike'] - spot) < spot * 0.01
```
- `abs()` = Absolute value (no negative)
- `spot * 0.01` = 1% of spot
- If spot = 21500, ATM range = 215 points
- Strikes 21400-21600 are considered ATM

**Ternary Comparison Chain:**
```python
if analysis['call_buildup']['otm'] > analysis['put_buildup']['otm']:
    analysis['interpretation'] = 'Bullish'
elif analysis['put_buildup']['otm'] > analysis['call_buildup']['otm']:
    analysis['interpretation'] = 'Bearish'
else:
    analysis['interpretation'] = 'Neutral'
```

**Logic:**
- If OTM call OI > OTM put OI → Bullish
- Else if OTM put OI > OTM call OI → Bearish
- Else → Neutral (balanced)



**OI Build-up Logic:**

**For Calls:**
- **ITM** (In The Money): Strike < Spot
- **ATM** (At The Money): Strike ≈ Spot (within 1%)
- **OTM** (Out of The Money): Strike > Spot

**For Puts:** (reversed)
- **ITM**: Strike > Spot
- **ATM**: Strike ≈ Spot
- **OTM**: Strike < Spot

**Interpretation:**
- **High OTM Call Writing** → Bullish (sellers betting price won't go up much)
- **High OTM Put Writing** → Bearish (sellers betting price won't fall much)

---

### Step 7.9: Add OHLC Endpoint

**Action:** Add OHLC data endpoint:

```python
@app.route('/ohlc/<product>', methods=['GET'])
def get_ohlc(product):
    """
    Get OHLC data.
    
    Query params:
    - window: Time window in minutes (1, 5, 15)
    """
    try:
        window = request.args.get('window', '5')
        
        cache_key = f"ohlc:{product}:{window}m"
        cached = redis_client.get(cache_key)
        
        if cached:
            return jsonify(json.loads(cached)), 200
        else:
            return jsonify({
                'product': product,
                'window': f"{window}m",
                'error': 'No OHLC data available'
            }), 404
        
    except Exception as e:
        logger.error("ohlc_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500
```

**OHLC Recap:**
- **O**pen: First price in window
- **H**igh: Highest price in window
- **L**ow: Lowest price in window
- **C**lose: Last price in window

Generated by Worker Enricher, stored in Redis.

---

### Step 7.10: Add Main Entry Point

**Action:** Add the Flask runner:

```python
if __name__ == '__main__':
    logger.info("analytics_service_starting", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False)
```

**Why `debug=False`?**
- Production safety
- No auto-reload (use gunicorn instead)
- No debug console exposure

---

## 7.4 Dockerization

### Step 7.11: Create Dockerfile

**Action:** Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python", "app.py"]
```

### Step 7.12: Test Locally

**Action:** Run the service:

```bash
export REDIS_URL=redis://localhost:6379/0
export MONGO_URL=mongodb://localhost:27017/deltastream
python app.py
```

**Test endpoints:**
```bash
# Health check
curl http://localhost:8004/health

# PCR analysis
curl http://localhost:8004/pcr/NIFTY?expiry=2024-01-25&history=true

# Volatility surface
curl http://localhost:8004/volatility-surface/NIFTY

# Max Pain
curl http://localhost:8004/max-pain/NIFTY?expiry=2024-01-25
```

---

## Summary

You've built an **Analytics Service** that:

✅ Provides 6 endpoint types (PCR, Volatility Surface, Max Pain, OI Build-up, OHLC, Health)
✅ Queries MongoDB for historical data
✅ Uses Redis cache for fast latest values
✅ Returns JSON responses for frontend consumption
✅ Includes structured logging
✅ Follows REST API conventions

**Key Learnings:**
- Dual data source pattern (Redis + MongoDB)
- Aggregation queries with PyMongo
- Volatility surface construction
- OI build-up interpretation logic
- Flask best practices

**Next:** Chapter 8 integrates all services with Docker Compose and tests the complete system!

---
