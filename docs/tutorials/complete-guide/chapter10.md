# Part 10: Logging Service & Centralized Logging

Centralized logging is essential for production microservices. Instead of SSH-ing into 13 different containers, aggregate all logs in one place with queryable, searchable access.

---

## 10.1 Understanding Centralized Logging

**Problem with Distributed Logs:**

```
Service A → /var/log/service-a.log (Container A)
Service B → /var/log/service-b.log (Container B) 
Service C → /var/log/service-c.log (Container C)
...
Service M → /var/log/service-m.log (Container M)
```

**Issues:**
- ❌ Must SSH into each container
- ❌ Logs lost when container restarts
- ❌ Can't correlate events across services (e.g., "trace a user request")
- ❌ No unified search ("find all errors in last hour")
- ❌ Manual aggregation is painful

**Solution: Centralized Logging Service**

```
┌──────────┐
│ Service A│──┐
└──────────┘  │
┌──────────┐  │    ┌─────────────────┐
│ Service B│──┼───▶│ Logging Service │
└──────────┘  │    └─────────────────┘
┌──────────┐  │            │
│ Service C│──┘            ▼
└──────────┘        ┌──────────────┐
                    │ File Storage │
                    │ + Redis Pub  │
                    └──────────────┘
```

**Benefits:**
- ✅ Single API to query all logs
- ✅ Persistent storage (survives restarts)
- ✅ Real-time streaming via Redis
- ✅ Correlate events across services
- ✅ Foundation for ELK/Loki integration

---

## 10.2 Project Setup

### Step 10.1: Create Directory Structure

**Action:** Create the logging service directory:

```bash
mkdir -p services/logging-service
cd services/logging-service
```

### Step 10.2: Create Requirements File

**Action:** Create `requirements.txt`:

```txt
flask==3.0.0
flask-cors==4.0.0
redis==5.0.1
```

**Why these dependencies?**
- `flask`: REST API for log ingestion and querying
- `flask-cors`: Allow frontend to query logs
- `redis`: Real-time log streaming (pub/sub)

---

## 10.3 Building the Service

### Step 10.3: Create Base Application Setup

**Action:** Create `app.py` and add imports + configuration:

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
```

**Breaking Down the Configuration:**

**Path Library:**
```python
from pathlib import Path
```
- Modern Python way to handle file paths
- Cross-platform (works on Windows/Linux/Mac)
- Object-oriented interface

**Environment Variables:**
```python
LOG_DIR = os.getenv('LOG_DIR', '/app/logs')
```
- `os.getenv('KEY', 'default')` → Gets env var or returns default
- Production: `/app/logs` (inside container)
- Development: can override with `export LOG_DIR=/tmp/logs`

**Creating Directory:**
```python
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
```
- `parents=True` → Creates parent directories if needed (like `mkdir -p`)
- `exist_ok=True` → No error if directory already exists
- Without these flags, would error if path doesn't exist

---

### Step 10.4: Add Health Check Endpoint

**Action:** Add health check:

```python
@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200
```

**Why health check?**
- Kubernetes liveness probe
- Docker healthcheck
- Load balancer monitoring

---

### Step 10.5: Implement Log Ingestion Endpoint

**Action:** Add the log ingestion API:

```python
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
            f.write(json.dumps(log_entry) + '\\n')
        
        # Publish to Redis for real-time monitoring
        redis_client.publish('logs:all', json.dumps(log_entry))
        
        return jsonify({'status': 'logged'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Breaking Down the Logic:**

**Get JSON Body:**
```python
log_entry = request.get_json()
```
- Flask parses JSON from request body
- Returns Python dict
- Example: `{'service': 'feed-generator', 'level': 'info', 'message': '...'}`

**Add Timestamp if Missing:**
```python
if 'timestamp' not in log_entry:
    log_entry['timestamp'] = datetime.now().isoformat()
```
- Some services may not include timestamp
- `.isoformat()` → "2024-01-25T10:30:45.123456"
- Standardized format for sorting/parsing

**Get Service Name:**
```python
service = log_entry.get('service', 'unknown')
```
- `.get(key, default)` → Safe dictionary access
- If 'service' key doesn't exist, returns 'unknown'
- Better than `log_entry['service']` which raises KeyError

**Path Construction:**
```python
log_file = Path(LOG_DIR) / f"{service}.log"
```
- `/` operator = path joining (clean, OS-agnostic)
- Equivalent to: `os.path.join(LOG_DIR, f"{service}.log")`
- Example result: `/app/logs/feed-generator.log`

**Write to File (Append Mode):**
```python
with open(log_file, 'a') as f:
    f.write(json.dumps(log_entry) + '\\n')
```
- `'a'` = append mode (doesn't overwrite existing)
- `json.dumps()` → Convert dict to JSON string
- `+ '\\n'` → Each log entry on new line (newline-delimited JSON)
- `with` statement → Auto-closes file even if error occurs

**Publish to Redis:**
```python
redis_client.publish('logs:all', json.dumps(log_entry))
```
- Publishes to channel `logs:all`
- Any subscriber gets log instantly (real-time monitoring)
- Non-blocking (fire-and-forget)

**Example Usage:**
```bash
curl -X POST http://localhost:8005/logs \\
  -H "Content-Type: application/json" \\
  -d '{
    "service": "feed-generator",
    "level": "error",
    "message": "Connection failed"
  }'
```

**Result:**
- File created: `/app/logs/feed-generator.log`
- Contents: `{"service":"feed-generator","level":"error","message":"Connection failed","timestamp":"2024-01-25T10:30:45.123456"}`
- Redis channel `logs:all` receives same message

---

### Step 10.6: Implement Log Query Endpoint

**Action:** Add the log retrieval API:

```python
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
```

**Breaking Down the Query Logic:**

**URL Parameter:**
```python
@app.route('/logs/<service>', methods=['GET'])
def get_logs(service):
```
- `<service>` → URL variable
- Example: `GET /logs/feed-generator` → service = "feed-generator"

**Query Parameter:**
```python
limit = int(request.args.get('limit', 100))
```
- `request.args` → Query string parameters
- Example: `?limit=50` → limit = 50
- Default: 100

**Check File Existence:**
```python
if not log_file.exists():
    return jsonify({'logs': []}), 200
```
- Doesn't error if service never logged
- Returns empty array (graceful degradation)

**Read All Lines:**
```python
with open(log_file, 'r') as f:
    lines = f.readlines()
```
- `readlines()` → Returns list of strings
- Each element = one line (including `\\n`)

**Get Last N Lines:**
```python
recent_lines = lines[-limit:]
```
- Python slice: `[-N:]` → Last N elements
- Example: `lines[-3:]` → Last 3 lines
- If file has 1000 lines and limit=100 → lines 900-1000

**Parse JSON Lines:**
```python
logs = [json.loads(line.strip()) for line in recent_lines if line.strip()]
```

**Step-by-step:**
1. `for line in recent_lines` → Loop through lines
2. `if line.strip()` → Skip empty lines
3. `line.strip()` → Remove `\\n` and whitespace
4. `json.loads()` → Parse JSON string to dict
5. `[...]` → List comprehension creates list

**Example:**
```python
recent_lines = [
  '{"service":"feed","level":"info"}\\n',
  '\\n',  # Empty line
  '{"service":"feed","level":"error"}\\n'
]

# After filtering and parsing:
logs = [
  {"service":"feed","level":"info"},
  {"service":"feed","level":"error"}
]
```

**Example API Call:**
```bash
curl http://localhost:8005/logs/feed-generator?limit=50
```

**Response:**
```json
{
  "service": "feed-generator",
  "count": 50,
  "logs": [
    {"timestamp": "...", "level": "info", "message": "..."},
    {"timestamp": "...", "level": "error", "message": "..."}
  ]
}
```

---

### Step 10.7: Add Flask Runner

**Action:** Add the main entry point:

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
```

**Why `host='0.0.0.0'`?**
- Binds to all network interfaces
- Container can accept external requests
- Without this, only accessible from inside container

---

## 10.4 Dockerization

### Step 10.8: Create Dockerfile

**Action:** Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Create log directory
RUN mkdir -p /app/logs

# Volume for persistent logs
VOLUME /app/logs

CMD ["python", "app.py"]
```

**Breaking Down Docker Syntax:**

**Volume Declaration:**
```dockerfile
VOLUME /app/logs
```
- Marks `/app/logs` as a volume
- Logs persist even if container restarts
- Can mount to host directory: `-v ./logs:/app/logs`

---

### Step 10.9: Test the Service

**Action:** Run locally and test:

```bash
# Start service
export REDIS_URL=redis://localhost:6379/0
export LOG_DIR=./test_logs
python app.py
```

**Send a log:**
```bash
curl -X POST http://localhost:8005/logs \\
  -H "Content-Type: application/json" \\
  -d '{
    "service": "test-service",
    "level": "info",
    "message": "Hello logging!"
  }'
```

**Query logs:**
```bash
curl http://localhost:8005/logs/test-service
```

**Expected:**
```json
{
  "service": "test-service",
  "count": 1,
  "logs": [
    {
      "service": "test-service",
      "level": "info",
      "message": "Hello logging!",
      "timestamp": "2024-01-25T10:30:45.123456"
    }
  ]
}
```

---

## 10.5 Integration Patterns

### How Services Send Logs

**Option 1: Direct HTTP POST** (Simple)
```python
import requests

requests.post('http://logging-service:8005/logs', json={
    'service': 'my-service',
    'level': 'error',
    'message': 'Something went wrong'
})
```

**Option 2: Custom Logging Handler** (Recommended)
```python
import logging
import requests

class HTTPLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            'service': 'my-service',
            'level': record.levelname,
            'message': record.getMessage()
        }
        requests.post('http://logging-service:8005/logs', json=log_entry)

logger = logging.getLogger()
logger.addHandler(HTTPLogHandler())
logger.error("This goes to logging service")
```

---

## Summary

You've built a **Centralized Logging Service** that:

✅ Ingests logs via POST /logs
✅ Stores logs persistently (file-based)
✅ Queries logs via GET /logs/<service>
✅ Streams logs real-time  via Redis pub/sub
✅ Supports filtering (limit parameter)
✅ Gracefully handles missing data

**Key Learnings:**
- Path library for cross-platform file handling
- List slicing for "last N items"
- Append mode file writing
- Newline-delimited JSON format
- Redis pub/sub for real-time streaming
- Custom logging handlers

**Next Steps:**
- Chapter 11: Kubernetes deployment
- Chapter 12: Connect to ELK/Loki for advanced querying

---
