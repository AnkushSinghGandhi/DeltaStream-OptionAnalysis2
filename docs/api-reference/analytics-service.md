# Analytics Service API

> **Advanced market analytics and calculations**

**Base URL**: `http://localhost:8000/api/analytics`  
**Port**: 8004

## Endpoints

### GET /analytics/pcr/:product
Get PCR (Put-Call Ratio) trends

**Response**:
```json
{
  "product": "NIFTY",
  "pcr_trend": [
    {
      "timestamp": "2025-01-03T10:30:00Z",
      "pcr_oi": 1.15,
      "pcr_volume": 0.98
    }
  ]
}
```

### GET /analytics/volatility-surface/:product
Get implied volatility surface

**Response**:
```json
{
  "product": "NIFTY",
  "expiries": [
    {
      "expiry": "2025-01-25",
      "strikes": [
        {"strike": 21500, "iv": 0.25},
        {"strike": 21600, "iv": 0.23}
      ]
    }
  ]
}
```

## Related
- [Tutorial Chapter 7](../tutorials/complete-guide/chapter07.md)
