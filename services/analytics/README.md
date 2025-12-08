# Analytics Service

## Overview

Provides aggregation and advanced analytics for option market data.

## Endpoints

### GET /pcr/{product}
PCR (Put-Call Ratio) analysis.

**Query Params:**
- `expiry`: Filter by expiry (optional)
- `history`: Include historical data (true/false)

**Example:**
```bash
curl "http://localhost:8004/pcr/NIFTY?history=true"
```

### GET /volatility-surface/{product}
Implied volatility surface across strikes and expiries.

### GET /max-pain/{product}
Max pain analysis.

**Query Params:**
- `expiry`: Expiry date (required)

### GET /oi-buildup/{product}
Open interest build-up analysis by strike zones.

**Query Params:**
- `expiry`: Expiry date (required)

### GET /ohlc/{product}
OHLC data for underlying.

**Query Params:**
- `window`: Time window - 1, 5, or 15 (default: 5)

## Analytics Explained

### PCR (Put-Call Ratio)
- PCR > 1: Bearish sentiment
- PCR < 1: Bullish sentiment
- Typical range: 0.7-1.0

### Max Pain
Strike where option writers have maximum profit.
Price tends to gravitate toward max pain.

### OI Build-up
Analyzes where open interest is concentrated:
- ITM: In-the-money
- ATM: At-the-money
- OTM: Out-of-the-money
