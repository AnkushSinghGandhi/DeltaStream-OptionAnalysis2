## Part 4: Building the Storage & Auth Services

### Learning Objectives

By the end of Part 4, you will understand:

1. **Repository Pattern** - Abstracting database access behind clean APIs
2. **MongoDB indexes** - Compound indexes for time-series queries
3. **REST API design** - Query parameters, pagination, filtering
4. **JWT authentication** - Stateless token-based auth
5. **Password hashing** - bcrypt for secure password storage
6. **Token verification** - Validating JWT tokens
7. **Error handling** - Standardized error responses

---

### 4.1 Understanding the Repository Pattern

Before building the Storage service, let's understand **why we need it**.

#### The Anti-Pattern: Direct Database Access

Imagine if every service directly accessed MongoDB:

```python
# In API Gateway
from pymongo import MongoClient
mongo_client = MongoClient('mongodb://...')
db = mongo_client['deltastream']

@app.route('/api/ticks/<product>')
def get_ticks(product):
    ticks = list(db.underlying_ticks.find({'product': product}))
    return jsonify(ticks)
```

```python
# In Analytics Service
from pymongo import MongoClient
mongo_client = MongoClient('mongodb://...')
db = mongo_client['deltastream']

def calculate_stats(product):
    ticks = list(db.underlying_ticks.find({'product': product}))
    # ... calculations
```

**Problems with this approach:**

1. **Duplication**: Same query logic in multiple services
2. **Coupling**: All services depend on MongoDB schema
3. **No abstraction**: Schema change breaks all services
4. **Security**: Database credentials in every service
5. **Inconsistency**: Different services handle datetimes differently
6. **Testing**: Can't easily mock database

---

#### The Solution: Repository Pattern

Create a **single service** that owns MongoDB access:

```
┌────────────────┐     HTTP      ┌────────────────┐     MongoDB     ┌──────────┐
│  API Gateway   │────────────▶│ Storage Service│────────────────▶│ MongoDB  │
└────────────────┘              └────────────────┘                  └──────────┘
                                        ▲
┌────────────────┐              │
│   Analytics    │──────────────┘
└────────────────┘
```

**Benefits:**

1. **Single source of truth**: All database logic in one place
2. **Abstraction**: Services use HTTP API, not MongoDB queries
3. **Consistency**: Datetime handling centralized
4. **Security**: Only Storage service has DB credentials
5. **Testing**: Mock HTTP responses instead of database
6. **Schema evolution**: Update Storage service, other services unchanged

**This is the Repository Pattern**, also known as **Data Access Layer** or **DAO (Data Access Object)** pattern.

---

### 4.2 Building the Storage Service

#### Project Structure

```
services/storage/
├── app.py                  # Main Flask application
├── requirements.txt        # Dependencies
├── Dockerfile             # Container image
└── README.md              # Documentation
```

---

#### Part 4.2.1: Dependencies

`requirements.txt`:
```txt
Flask==3.0.0
flask-cors==4.0.0
pymongo==4.6.1
structlog==23.2.0
```

**Why these?**

- `Flask`: Lightweight web framework for REST API
- `flask-cors`: Handle CORS (Cross-Origin Resource Sharing) for browser clients
- `pymongo`: MongoDB driver
- `structlog`: Structured logging

---

#### Part 4.2.2: Storage Service Implementation

```python
#!/usr/bin/env python3
"""
Storage Service

MongoDB wrapper service providing REST API for data storage and retrieval.
Abstracts database operations and provides a clean interface for other services.
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING
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
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/deltastream')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'storage')
PORT = int(os.getenv('PORT', '8003'))

# Initialize Flask
app = Flask(__name__)
CORS(app)
app.config['JSON_SORT_KEYS'] = False
```

**Flask initialization:**

```python
app = Flask(__name__)
CORS(app)
```

**What is CORS?**

**Problem**: Browser security prevents JavaScript from making requests to different domains.

Example:
- Frontend runs on: `http://localhost:3000`
- API runs on: `http://localhost:8003`
- Browser blocks request (different ports = different origins)

**Solution**: `flask-cors` adds HTTP headers telling browser requests are allowed:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
```

```python
app.config['JSON_SORT_KEYS'] = False
```

**What does this do?**

By default, Flask sorts JSON keys alphabetically. This changes:
```json
{"timestamp": "...", "product": "NIFTY", "price": 21500}
```

To:
```json
{"price": 21500, "product": "NIFTY", "timestamp": "..."}
```

We disable this to preserve original key order (cleaner, more predictable responses).

---

#### Part 4.2.3: MongoDB Connection and Indexes

```python
# MongoDB client
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['deltastream']

# Create indexes
db.underlying_ticks.create_index([('product', ASCENDING), ('timestamp', DESCENDING)])
db.underlying_ticks.create_index([('timestamp', DESCENDING)])
db.option_quotes.create_index([('symbol', ASCENDING), ('timestamp', DESCENDING)])
db.option_quotes.create_index([('product', ASCENDING), ('timestamp', DESCENDING)])
db.option_chains.create_index([('product', ASCENDING), ('expiry', ASCENDING), ('timestamp', DESCENDING)])
```

**Index creation on startup:**

```python
db.underlying_ticks.create_index([('product', ASCENDING), ('timestamp', DESCENDING)])
```

**Why create indexes in application code?**

**Alternative**: Create indexes manually via MongoDB shell.

**Problems:**
- Must remember to create indexes in production
- New developers forget to create indexes locally
- Indexes not version controlled

**Application approach:**
- Indexes automatically created on every startup
- `create_index()` is idempotent (safe to run multiple times)
- Indexes are documented in code

**Compound index explanation:**

```python
[('product', ASCENDING), ('timestamp', DESCENDING)]
```

This creates an index where:
- **First** sorted by `product` (A→Z)
- **Then** sorted by `timestamp` (newest→oldest)

**Example index structure:**

```
NIFTY, 2025-01-03T18:00:00
NIFTY, 2025-01-03T17:59:59
NIFTY, 2025-01-03T17:59:58
⋮
BANKNIFTY, 2025-01-03T18:00:00
BANKNIFTY, 2025-01-03T17:59:59
```

**Query optimization:**

```python
db.underlying_ticks.find({'product': 'NIFTY'}).sort('timestamp', DESCENDING)
```

- Index matches query exactly → **O(log N) + k** where k = results
- Without index → **O(N)** full collection scan

---

#### Part 4.2.4: Health Check Endpoint

```python
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    try:
        # Ping MongoDB
        mongo_client.admin.command('ping')
        return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

**Why health checks?**

In production (Kubernetes, Docker Swarm):
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

- Container platform hits `/health` every 30s
- If response != 200 → container marked unhealthy
- After 3 failures → container restarted

**MongoDB ping:**

``` python
mongo_client.admin.command('ping')
```

- Verifies MongoDB connection is alive
- Returns immediately (no data transfer)
- Throws exception if MongoDB is down

---

#### Part 4.2.5: Get Underlying Ticks Endpoint

```python
@app.route('/underlying/<product>', methods=['GET'])
def get_underlying_ticks(product):
    """
    Get underlying price ticks for a product.
    
    Query params:
    - start: Start timestamp (ISO format)
    - end: End timestamp (ISO format)
    - limit: Max number of results (default: 100)
    """
    try:
        # Parse query params
        start = request.args.get('start')
        end = request.args.get('end')
        limit = int(request.args.get('limit', 100))
        
        # Build query
        query = {'product': product}
        if start or end:
            query['timestamp'] = {}
            if start:
                query['timestamp']['$gte'] = datetime.fromisoformat(start)
            if end:
                query['timestamp']['$lte'] = datetime.fromisoformat(end)
        
        # Execute query
        ticks = list(db.underlying_ticks.find(
            query,
            {'_id': 0}
        ).sort('timestamp', DESCENDING).limit(limit))
        
        # Convert datetime to ISO string
        for tick in ticks:
            if 'timestamp' in tick:
                tick['timestamp'] = tick['timestamp'].isoformat()
            if 'processed_at' in tick:
                tick['processed_at'] = tick['processed_at'].isoformat()
        
        return jsonify({
            'product': product,
            'count': len(ticks),
            'ticks': ticks
        }), 200
        
    except Exception as e:
        logger.error("get_underlying_ticks_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500
```

**Query parameter parsing:**

```python
start = request.args.get('start')
end = request.args.get('end')
limit = int(request.args.get('limit', 100))
```

**Example request:**
```
GET /underlying/NIFTY?start=2025-01-03T10:00:00&end=2025-01-03T12:00:00&limit=50
```

**Parsed values:**
```python
product = 'NIFTY'  # From URL path
start = '2025-01-03T10:00:00'
end = '2025-01-03T12:00:00'
limit = 50
```

**Dynamic query building:**

```python
query = {'product': product}
if start or end:
    query['timestamp'] = {}
    if start:
        query['timestamp']['$gte'] = datetime.fromisoformat(start)
    if end:
        query['timestamp']['$lte'] = datetime.fromisoformat(end)
```

**Why dynamic?**

Different requests need different queries:

Request: `GET /underlying/NIFTY`
```python
query = {'product': 'NIFTY'}
```

Request: `GET /underlying/NIFTY?start=2025-01-03T10:00:00`
```python
query = {
    'product': 'NIFTY',
    'timestamp': {'$gte': datetime(2025, 1, 3, 10, 0, 0)}
}
```

Request: `GET /underlying/NIFTY?start=2025-01-03T10:00:00&end=2025-01-03T12:00:00`
```python
query = {
    'product': 'NIFTY',
    'timestamp': {
        '$gte': datetime(2025, 1, 3, 10, 0, 0),
        '$lte': datetime(2025, 1, 3, 12, 0, 0)
    }
}
```

**Datetime conversion:**

```python
for tick in ticks:
    if 'timestamp' in tick:
        tick['timestamp'] = tick['timestamp'].isoformat()
```

**Why?**

MongoDB stores: `ISODate("2025-01-03T12:30:00Z")`
Python gets: `datetime(2025, 1, 3, 12, 30, 0)`
JSON needs: `"2025-01-03T12:30:00"`

`datetime.isoformat()` → converts to string.

**Without conversion:**
```python
return jsonify(tick)
# Error: Object of type datetime is not JSON serializable
```

---

#### Part 4.2.6: Get Option Chains Endpoint

```python
@app.route('/option/chain/<product>', methods=['GET'])
def get_option_chain(product):
    """
    Get option chains for a product.
    
    Query params:
    - expiry: Filter by expiry date (YYYY-MM-DD)
    - limit: Max results (default: 10)
    """
    try:
        expiry = request.args.get('expiry')
        limit = int(request.args.get('limit', 10))
        
        query = {'product': product}
        if expiry:
            query['expiry'] = expiry
        
        chains = list(db.option_chains.find(
            query,
            {'_id': 0}
        ).sort('timestamp', DESCENDING).limit(limit))
        
        for chain in chains:
            if 'timestamp' in chain:
                chain['timestamp'] = chain['timestamp'].isoformat()
            if 'processed_at' in chain:
                chain['processed_at'] = chain['processed_at'].isoformat()
        
        return jsonify({
            'product': product,
            'count': len(chains),
            'chains': chains
        }), 200
        
    except Exception as e:
        logger.error("get_option_chain_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500
```

**Field projection:**

```python
db.option_chains.find(query, {'_id': 0})
```

**What is `{'_id': 0}`?**

By default, MongoDB returns:
```json
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "product": "NIFTY",
  "expiry": "2025-01-25",
  ...
}
```

With `{'_id': 0}`:
```json
{
  "product": "NIFTY",
  "expiry": "2025-01-25",
  ...
}
```

**Why exclude `_id`?**
- Not useful for API consumers
- `ObjectId` isn't JSON-serializable (needs string conversion)
- Reduces payload size

---

#### Part 4.2.7: Get Products and Expiries

```python
@app.route('/products', methods=['GET'])
def get_products():
    """Get list of available products."""
    try:
        products = db.underlying_ticks.distinct('product')
        return jsonify({'products': products}), 200
    except Exception as e:
        logger.error("get_products_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/option/expiries/<product>', methods=['GET'])
def get_expiries(product):
    """Get available expiries for a product."""
    try:
        expiries = db.option_chains.distinct('expiry', {'product': product})
        expiries = sorted(expiries)
        return jsonify({'product': product, 'expiries': expiries}), 200
    except Exception as e:
        logger.error("get_expiries_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500
```

**MongoDB `distinct()` operation:**

```python
products = db.underlying_ticks.distinct('product')
```

**Example output:**
```python
['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX']
```

**Why `distinct()` instead of aggregation?**

Alternative (aggregation):
```python
products = db.underlying_ticks.aggregate([
    {'$group': {'_id': '$product'}},
    {'$project': {'_id': 0, 'product': '$_id'}}
])
```

**Comparison:**
- `distinct()`: Simple, fast, one line
- Aggregation: Powerful but overkill for simple use case

Use `distinct()` for simple unique value queries.

---

### 4.3 Building the Auth Service

Now let's build JWT-based authentication.

#### Part 4.3.1: Understanding JWT Authentication

**What is JWT?**

JWT = **JSON Web Token** - a compact, URL-safe way to represent claims between two parties.

**JWT Structure:**

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNzA0MjkwNDAwfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

Three parts separated by `.`:

1. **Header** (red): `{"alg": "HS256", "typ": "JWT"}`
2. **Payload** (purple): `{"user_id": "123", "email": "user@example.com", "exp": 1704290400}`
3. **Signature** (blue): HMACSHA256(base64(header) + "." + base64(payload), secret)

**How it works:**

1. **Login**: User sends email/password → Server verifies → Returns JWT
2. **Authenticated request**: Client sends JWT in `Authorization` header
3. **Verification**: Server decodes JWT, verifies signature → Extracts user_id

**Why JWT is powerful:**

**Stateless**: Server doesn't store sessions. JWT contains all info needed.

Traditional session:
```
Client                    Server                  Database
  │                         │                         │
  ├──login────────────────▶│                         │
  │                         ├──save session─────────▶│
  │◀──────session_id────────│                         │
  │                         │                         │
  ├──request + session_id──▶│                         │
  │                         ├──lookup session───────▶│
  │                         │◀─────user_id───────────│
  │◀──────response──────────│                         │
```

JWT:
```
Client                    Server
  │                         │
  ├──login────────────────▶│
  │◀──────JWT──────────────│ (server doesn't store anything)
  │                         │
  ├──request + JWT────────▶│ (server verifies signature, extracts user_id)
  │◀──────response──────────│
```

**Benefits:**
- No database lookup on every request (faster)
- Scales infinitely (no session storage)
- Works across multiple servers (stateless)

**Trade-offs:**
- Can't instantly revoke tokens (must wait for expiry)
- Token size larger than session ID (100+ bytes vs 16 bytes)

---

#### Part 4.3.2: Auth Service Implementation

```python
#!/usr/bin/env python3
"""
Auth Service

JWT-based authentication service.
Provides user registration, login, and token verification.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import structlog

# Configuration
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/deltastream')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
SERVICE_NAME = os.getenv('SERVICE_NAME', 'auth')
PORT = int(os.getenv('PORT', '8001'))

# Initialize Flask
app = Flask(__name__)
CORS(app)

# MongoDB
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['deltastream']
users_collection = db['users']

# Create unique index on email
users_collection.create_index('email', unique=True)
```

**Unique index on email:**

```python
users_collection.create_index('email', unique=True)
```

**Why unique index?**

- Prevents duplicate email registrations
- MongoDB enforces uniqueness (can't have two users with same email)
- Insert attempt with duplicate email → `DuplicateKeyError`

**Example:**
```python
users_collection.insert_one({'email': 'user@example.com', ...})  # Success
users_collection.insert_one({'email': 'user@example.com', ...})  # DuplicateKeyError
```

---

#### Part 4.3.3: User Registration

```python
@app.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Body:
    {
      "email": "user@example.com",
      "password": "password123",
      "name": "John Doe"
    }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        name = data.get('name', '')
        
        # Validation
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if user exists
        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'User already exists'}), 409
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user = {
            'email': email,
            'password_hash': password_hash,
            'name': name,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        result = users_collection.insert_one(user)
        user_id = str(result.inserted_id)
        
        logger.info("user_registered", email=email, user_id=user_id)
        
        # Generate token
        token = generate_token(user_id, email)
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'name': name
            }
        }), 201
        
    except Exception as e:
        logger.error("register_error", error=str(e), exc_info=True)
        return jsonify({'error': 'Registration failed'}), 500
```

**Password hashing with bcrypt:**

```python
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
```

**Why NOT store plain passwords?**

**Bad** (plaintext):
```python
user = {'email': 'user@example.com', 'password': 'password123'}
```

- Database breach → all passwords exposed
- Admins can see passwords
- Violates security best practices

**Good** (hashed):
```python
password_hash = bcrypt.hashpw('password123'.encode(), bcrypt.gensalt())
# Result: b'$2b$12$KIXQQyJZ...(60 characters)'
```

**How bcrypt works:**

1. **Salt generation**: `bcrypt.gensalt()` → random string
2. **Hashing**: Combines password + salt → hash
3. **Result**: `$2b$12$salt$hash` (embedded salt + hash)

**Example:**
```python
password = "password123"
hash1 = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
hash2 = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# hash1 != hash2 (different salts)
# But both verify correctly:
bcrypt.checkpw(password.encode(), hash1)  # True
bcrypt.checkpw(password.encode(), hash2)  # True
```

**Why different hashes for same password?**
- **Salt** is random each time
- Prevents rainbow table attacks (precomputed hash lists)

**Cost factor** (`$2b$12$...`):

- `12` = cost factor (2^12 iterations)
- Higher cost = slower hash (more secure, harder to brute force)
- Default 12 ≈ 250ms per hash (good balance)

---

#### Part 4.3.4: User Login

```python
@app.route('/login', methods=['POST'])
def login():
    """
    Login user.
    
    Body:
    {
      " email": "user@example.com",
      "password": "password123"
    }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user
        user = users_collection.find_one({'email': email})
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate token
        user_id = str(user['_id'])
        token = generate_token(user_id, email)
        
        logger.info("user_logged_in", email=email, user_id=user_id)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'name': user.get('name', '')
            }
        }), 200
        
    except Exception as e:
        logger.error("login_error", error=str(e), exc_info=True)
        return jsonify({'error': 'Login failed'}), 500
```

**Password verification:**

```python
bcrypt.checkpw(password.encode('utf-8'), user['password_hash'])
```

**How it works:**
1. Extract salt from stored hash: `$2b$12$salt$hash` → salt = `salt`
2. Hash provided password with same salt
3. Compare hashes
4. Return `True` if match, `False` otherwise

**Security note:**

```python
if not user:
    return jsonify({'error': 'Invalid credentials'}), 401

if not bcrypt.checkpw(...):
    return jsonify({'error': 'Invalid credentials'}), 401
```

**Why same error message?**

**Bad** (different messages):
```python
if not user:
    return "Email not found"
if not bcrypt.checkpw(...):
    return "Wrong password"
```

**Problem**: Attacker knows which emails exist in system (information leak).

**Good** (same message):
- Attacker can't distinguish between "email doesn't exist" vs "wrong password"
- Prevents user enumeration attacks

---

#### Part 4.3.5: Token Generation

```python
def generate_token(user_id: str, email: str) -> str:
    """Generate JWT token."""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token
```

**JWT payload:**

```python
payload = {
    'user_id': user_id,
    'email': email,
    'exp': datetime.utcnow() + timedelta(hours=24),
    'iat': datetime.utcnow()
}
```

**Standard JWT claims:**

- `exp` (expiration): Token invalid after this time
- `iat` (issued at): When token was created
- `user_id`, `email`: Custom claims (our data)

**Token encoding:**

```python
token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
```

**Returns:** `eyJhbGc...` (long string)

**JWT_SECRET:**
- Symmetric key for signing
- **Must be kept secret** (stored in environment variable)
- Anyone with secret can forge tokens

**Production secret management:**
```bash
# Generate strong secret
openssl rand -hex 32

# Store in environment (not in code!)
export JWT_SECRET=8f7a9b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

---

#### Part 4.3.6: Token Verification

```python
@app.route('/verify', methods=['POST'])
def verify_token():
    """
    Verify JWT token.
    
    Body:
    {
      "token": "eyJhbGc..."
    }
    """
    try:
        data = request.get_json()
        token = data.get('token', '')
        
        if not token:
            return jsonify({'error': 'Token required'}), 400
        
        # Decode and verify
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        return jsonify({
            'valid': True,
            'user_id': payload['user_id'],
            'email': payload['email']
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error("verify_token_error", error=str(e), exc_info=True)
        return jsonify({'error': 'Verification failed'}), 500
```

**JWT verification:**

```python
payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
```

**What happens:**
1. Split token: header | payload | signature
2. Verify signature: `HMAC(header + payload, JWT_SECRET) == signature`
3. If signature invalid → `InvalidTokenError`
4. Check `exp` claim: If past expiry → `ExpiredSignatureError`
5. If valid → return payload

**Exception handling:**

```python
except jwt.ExpiredSignatureError:
    return jsonify({'error': 'Token expired'}), 401
except jwt.InvalidTokenError:
    return jsonify({'error': 'Invalid token'}), 401
```

**Different errors for different cases:**
- `ExpiredSignatureError`: Token was valid but has expired → client should refresh
- `InvalidTokenError`: Token is malformed or signature invalid → client should re-login

---

### 4.4 Docker Setup for Both Services

#### Storage Service Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8003

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8003"]
```

#### Auth Service Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8001

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8001"]
```

**Flask command:**

```dockerfile
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8003"]
```

**Alternative** (direct Python):
```dockerfile
CMD ["python", "app.py"]
```

Then in `app.py`:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8003)
```

**Why `--host=0.0.0.0`?**

- `127.0.0.1`: Only accessible from inside container
- `0.0.0.0`: Accessible from anywhere (required for Docker networking)

---

### 4.5 Docker Compose Integration

```yaml
  storage:
    build:
      context: ./services/storage
      dockerfile: Dockerfile
    container_name: deltastream-storage
    ports:
      - "8003:8003"
    environment:
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - SERVICE_NAME=storage
      - PORT=8003
    depends_on:
      mongodb:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped

  auth:
    build:
      context: ./services/auth
      dockerfile: Dockerfile
    container_name: deltastream-auth
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - JWT_SECRET=${JWT_SECRET}
      - SERVICE_NAME=auth
      - PORT=8001
    depends_on:
      mongodb:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped
```

**JWT_SECRET from environment:**

```yaml
environment:
  - JWT_SECRET=${JWT_SECRET}
```

This reads from `.env` file or shell environment:

`.env`:
```bash  
JWT_SECRET=8f7a9b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

**Security best practice:**
- `.env` in `.gitignore` (never commit secrets!)
- Provide `.env.example` with dummy values

---

### Part 4 Complete: What You've Built

You now have **production-ready Storage and Auth services**:

**Storage Service:**
✅ Repository Pattern implementation
✅ MongoDB wrapper with clean REST API
✅ Compound indexes for performance
✅ Query parameters (start, end, limit)
✅ Datetime serialization
✅ Error handling

**Auth Service:**
✅ JWT-based authentication
✅ bcrypt password hashing
✅ User registration and login
✅ Token generation and verification
✅ Unique email constraint
✅ Security best practices

---

### Key Learnings from Part 4

**1. Repository Pattern decouples data access**
- Single source of truth for database
- Other services use HTTP, not MongoDB
- Schema changes localized to one service

**2. Indexes are critical for query performance**
- Compound indexes support complex queries
- Create indexes on startup (automated, version controlled)
- Index on fields you query and sort by

**3. JWT enables stateless authentication**
- No session storage needed
- Scales infinitely
- Signature verification without database lookup

**4. Password security is non-negotiable**
- Never store plaintext passwords
- bcrypt with salt prevents rainbow tables
- Same error message for "user not found" vs "wrong password"

**5. REST API design patterns**
- Query parameters for filtering
- Field projection (`{'_id': 0}`)
- Datetime serialization for JSON
- Standardized error responses

---

### What's Next: Tutorial Progress

- ✅ Part 1: Architecture & Project Setup (1,349 lines)
- ✅ Part 2: Feed Generator Service (1,450 lines)
- ✅ Part 3: Worker Enricher Service (2,209 lines)
- ✅ Part 4: Storage & Auth Services (1,800+ lines)
- **Total: 6,800+ lines of comprehensive tutorial content**

**Part 5 Preview** will cover:
- **API Gateway**: Request routing, authentication middleware
- **Service proxying**: Forwarding requests to backend services
- **OpenAPI documentation**: Auto-generated API docs
- **Error handling**: Centralized error responses

**Ready to continue?** Let me know when you want Part 5: Building the API Gateway!

---

