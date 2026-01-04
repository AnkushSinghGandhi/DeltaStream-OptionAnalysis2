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
mongo_client = MongoClient('mongodb://localhost:27017')
db = mongo_client['deltastream']

@app.route('/api/ticks/<product>')
def get_ticks(product):
    ticks = list(db.underlying_ticks.find({'product': product}))
    return jsonify(ticks)
```

```python
# In Analytics Service
from pymongo import MongoClient
mongo_client = MongoClient('mongodb://localhost:27017')
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


---

**Navigation:**
← [Previous: Chapter 3-3](chapter03-3.md) | [Next: Chapter 4-2](chapter04-2.md) →

---
