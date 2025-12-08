# Storage Service

## Overview

MongoDB wrapper service providing REST API for querying option market data.

## Endpoints

### GET /health
Health check.

### GET /underlying/{product}
Get underlying price ticks.

**Query Params:**
- `start`: Start timestamp (ISO format)
- `end`: End timestamp (ISO format)
- `limit`: Max results (default: 100)

**Example:**
```bash
curl "http://localhost:8003/underlying/NIFTY?limit=10"
```

### GET /option/quote/{symbol}
Get option quotes for a symbol.

### GET /option/chain/{product}
Get option chains.

**Query Params:**
- `expiry`: Filter by expiry date
- `limit`: Max results (default: 10)

### GET /products
List all products.

### GET /expiries/{product}
Get expiry dates for a product.
