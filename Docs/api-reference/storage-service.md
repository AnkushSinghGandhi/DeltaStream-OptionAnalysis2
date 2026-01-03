# Storage Service API

> **MongoDB data access layer for market data**

**Base URL**: `http://localhost:8000/api/data`  
**Port**: 8003

## Endpoints

### GET /data/products
List available products (NIFTY, BANKNIFTY, etc.)

**Response**:
```json
{
  "products": ["NIFTY", "BANKNIFTY", "FINNIFTY"]
}
```

### GET /data/underlying/:product
Get latest underlying price

**Parameters**:
- `product` (path): Product symbol (e.g., NIFTY)
- `limit` (query): Number of records (default: 10)

**Response**:
```json
{
  "data": [
    {
      "product": "NIFTY",
      "price": 21543.25,
      "timestamp": "2025-01-03T10:30:00Z"
    }
  ]
}
```

### GET /data/chain/:product/:expiry
Get option chain

**Parameters**:
- `product` (path): Product symbol
- `expiry` (path): Expiry date (YYYY-MM-DD)
- `limit` (query): Number of chains

**Response**:
```json
{
  "chains": [
    {
      "product": "NIFTY",
      "expiry": "2025-01-25",
      "spot_price": 21543.25,
      "pcr_oi": 1.15,
      "strikes": [...]
    }
  ]
}
```

### GET /data/expiries/:product
Get available expiry dates

**Response**:
```json
{
  "expiries": ["2025-01-25", "2025-02-01", "2025-02-08"]
}
```

## Related
- [Tutorial Chapter 4](../tutorials/complete-guide/chapter04.md)
