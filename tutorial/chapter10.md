## Part 10: Logging Service & Centralized Logging

### Learning Objectives

By the end of Part 10, you will understand:

1. **Centralized logging** - Aggregating logs from all services
2. **Structured logs** - JSON format for machine parsing
3. **Log ingestion** - REST API for log collection
4. **Log querying** - Retrieving logs by service
5. **Log forwarding** - Integration with ELK/Loki
6. **Redis pub/sub for logs** - Real-time log streaming

---

### 10.1 Why Centralized Logging?

**Problem with distributed logs:**

```
Service A logs → /var/log/service-a.log (Container A)
Service B logs → /var/log/service-b.log (Container B)
Service C logs → /var/log/service-c.log (Container C)
```

**Issues:**
- Must SSH into each container to view logs
- Logs lost when container restarts
- Can't correlate events across services
- No unified search

**Solution: Centralized Logging**

```
All Services → Logging Service → Persistent Storage
                    ↓
            Query API + Search
```

---

### 10.2 Building the Logging Service

`services/logging-service/app.py`:

```python
#!/usr/bin/env python3
"""
Logging Service

Centralized log aggregation providing:
- Log ingestion API
- Persistent storage
- Query API
- Real-time log streaming via Redis
"""

import os
import json
import redis
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'logging-service')
PORT = int(os.getenv('PORT', '8005'))
LOG_DIR = os.getenv('LOG_DIR', '/app/logs')

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Create log directory
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200


@app.route('/logs', methods=['POST'])
def ingest_log():
    """
    Ingest a log entry.
    
    Body: JSON log entry
    """
    try:
        log_entry = request.get_json()
        
        # Add timestamp if not present
        if 'timestamp' not in log_entry:
            log_entry['timestamp'] = datetime.now().isoformat()
        
        # Write to file
        service = log_entry.get('service', 'unknown')
        log_file = Path(LOG_DIR) / f"{service}.log"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Publish to Redis for real-time monitoring
        redis_client.publish('logs:all', json.dumps(log_entry))
        
        return jsonify({'status': 'logged'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logs/<service>', methods=['GET'])
def get_logs(service):
    """
    Get logs for a service.
    
    Query params:
    - limit: Max number of lines (default: 100)
    """
    try:
        limit = int(request.args.get('limit', 100))
        log_file = Path(LOG_DIR) / f"{service}.log"
        
        if not log_file.exists():
            return jsonify({'logs': []}), 200
        
        # Read last N lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-limit:]
        
        logs = [json.loads(line.strip()) for line in recent_lines if line.strip()]
        
        return jsonify({
            'service': service,
            'count': len(logs),
            'logs': logs
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
```

**Key features:**
✅ Log ingestion via POST /logs
✅ Persistent file storage
✅ Query API GET /logs/<service>
✅ Real-time streaming via Redis pub/sub

---

