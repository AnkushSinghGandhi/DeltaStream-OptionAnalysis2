# Feed Generator Service

## Overview

The Feed Generator service simulates a realistic market data feed for option trading. It generates synthetic but realistic market data including:

- **Products**: Multiple underlying symbols (NIFTY, BANKNIFTY, AAPL, TSLA, etc.)
- **Expiry Dates**: Weekly and monthly option expiries
- **Strike Prices**: Complete strike ladder around current spot price
- **Option Quotes**: Bid/ask spreads, last price, volume, open interest
- **Greeks**: Delta, Gamma, Vega, Theta
- **Implied Volatility**: Realistic IV values (15-35%)
- **Option Chains**: Complete call/put chains for each expiry

## Data Flow

The service publishes data to Redis pub/sub channels:

1. `market:underlying` - Underlying price ticks (every tick)
2. `market:option_chain` - Complete option chains (every 5 ticks)
3. `market:option_quote` - Individual option quotes (random sampling)

## Environment Variables

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `FEED_INTERVAL`: Seconds between ticks (default: `1`)
- `SERVICE_NAME`: Service identifier (default: `feed-generator`)

## Data Models

### Underlying Tick
```json
{
  "type": "UNDERLYING",
  "product": "NIFTY",
  "price": 21543.25,
  "timestamp": "2025-01-15T10:30:45.123456",
  "tick_id": 12345
}
```

### Option Quote
```json
{
  "symbol": "NIFTY20250125C21500",
  "product": "NIFTY",
  "strike": 21500,
  "expiry": "2025-01-25",
  "option_type": "CALL",
  "bid": 125.50,
  "ask": 127.80,
  "last": 126.50,
  "volume": 5432,
  "open_interest": 45678,
  "delta": 0.5234,
  "gamma": 0.0012,
  "vega": 8.45,
  "theta": -2.34,
  "iv": 0.2145,
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

### Option Chain
```json
{
  "product": "NIFTY",
  "expiry": "2025-01-25",
  "spot_price": 21543.25,
  "strikes": [21000, 21050, 21100, ...],
  "calls": [...],
  "puts": [...],
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

## Price Generation Algorithm

The service uses a simplified **Geometric Brownian Motion** model for underlying price updates:

```
S(t+1) = S(t) * (1 + N(0, σ))
```

Where:
- `S(t)` is the price at time t
- `N(0, σ)` is a normal random variable with mean 0 and standard deviation σ
- σ varies by product type (indices have lower volatility than stocks)

## Option Pricing

Options are priced using a simplified Black-Scholes approximation:

```
Option Price = Intrinsic Value + Time Value

Intrinsic Value (Call) = max(0, Spot - Strike)
Intrinsic Value (Put) = max(0, Strike - Spot)

Time Value = Spot * IV * sqrt(TTE) * adjustment_factor
```

This is intentionally simplified for demo purposes. Production systems should use proper options pricing libraries.

## Greeks Calculation

Greeks are approximated using simplified formulas:

- **Delta**: ATM options ≈ 0.5, ITM ≈ 0.8, OTM ≈ 0.2
- **Gamma**: Highest for ATM options
- **Vega**: Proportional to `Spot * sqrt(TTE)`
- **Theta**: `-OptionPrice / (TTE * 365)`

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export REDIS_URL=redis://localhost:6379/0
export FEED_INTERVAL=1

# Run the service
python app.py
```

## Monitoring

The service emits structured JSON logs including:
- Feed startup confirmation
- Option chain publications
- Status updates every 10 ticks
- Current prices for all products

## Performance Considerations

- Generates ~100-200 messages per second (8 products, multiple quotes per product)
- Redis pub/sub can handle this easily (tested up to 10k msg/sec)
- To reduce load, adjust `FEED_INTERVAL` or reduce number of products

## Future Enhancements

- Add order book depth (bid/ask levels)
- Implement corporate actions (dividends, splits)
- Add futures data
- Support for different market hours
- Historical data replay mode
