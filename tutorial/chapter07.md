## Part 7: Analytics Service & Complete System Integration

### 7.1 Analytics Service Implementation

The Analytics Service provides advanced calculations and aggregations.

`services/analytics/app.py`:

```python
#!/usr/bin/env python3
"""
Analytics Service

Provides advanced market analytics:
- Historical PCR trends
- Volatility surface
- Greeks aggregation
- Support/Resistance levels
"""

import os
import redis
import structlog
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timedelta
import json

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/deltastream')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'analytics')
PORT = int(os.getenv('PORT', '8004'))

app = Flask(__name__)
CORS(app)

mongo_client = MongoClient(MONGO_URL)
db = mongo_client['deltastream']
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


@app.route('/pcr/<product>', methods=['GET'])
def get_pcr_trend(product):
    """Get PCR trend over time."""
    try:
        expiry = request.args.get('expiry')
        hours = int(request.args.get('hours', 24))
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        query = {
            'product': product,
            'timestamp': {'$gte': start_time}
        }
        if expiry:
            query['expiry'] = expiry
        
        chains = list(db.option_chains.find(
            query,
            {'_id': 0, 'timestamp': 1, 'pcr_oi': 1, 'pcr_volume': 1, 'expiry': 1}
        ).sort('timestamp', DESCENDING).limit(100))
        
        for chain in chains:
            if 'timestamp' in chain:
                chain['timestamp'] = chain['timestamp'].isoformat()
        
        return jsonify({
            'product': product,
            'data_points': len(chains),
            'pcr_trend': chains
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/volatility-surface/<product>', methods=['GET'])
def get_volatility_surface(product):
    """Get cached volatility surface."""
    try:
        cached = redis_client.get(f"volatility_surface:{product}")
        if not cached:
            return jsonify({'error': 'No data available'}), 404
        
        return jsonify(json.loads(cached)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
```

---

