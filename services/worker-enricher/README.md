# Worker Enricher Service

## Overview

The Worker Enricher is a Celery-based processing service that consumes raw market data, performs calculations and enrichments, and produces analysis-ready data.

## Architecture

This service runs two processes via supervisord:

1. **Subscriber**: Listens to Redis pub/sub channels and dispatches Celery tasks
2. **Celery Worker**: Processes tasks with configurable concurrency

## Enrichment Pipeline

```
Raw Feed → Redis Pub/Sub → Subscriber → Celery Task Queue → Worker → MongoDB + Redis Cache → Enriched Pub/Sub
```

## Features

### Data Processing
- **Underlying Ticks**: Store, cache, calculate OHLC windows
- **Option Quotes**: Store, cache, build IV surface data
- **Option Chains**: Calculate PCR, max pain, straddle, build-up analysis

### Calculations

#### PCR (Put-Call Ratio)
```python
PCR (OI) = Total Put Open Interest / Total Call Open Interest
PCR (Volume) = Total Put Volume / Total Call Volume
```

Interpretation:
- PCR > 1: More puts than calls (bearish sentiment)
- PCR < 1: More calls than puts (bullish sentiment)
- PCR ≈ 0.7-1.0: Typical range

#### ATM Straddle Price
```python
Straddle Price = ATM Call Price + ATM Put Price
```

Indicates expected volatility. Higher straddle = higher expected move.

#### Max Pain
Strike price where total option value is minimized (maximum pain for option buyers).

```python
For each strike:
  Total Value = Sum(Call OI * max(0, strike - call_strike)) + 
                Sum(Put OI * max(0, put_strike - strike))
Max Pain = Strike with minimum Total Value
```

#### OHLC Windows
Calculates Open, High, Low, Close for 1-minute, 5-minute, and 15-minute windows.

#### Volatility Surface
Grid of Implied Volatility across strikes and expiries. Useful for:
- Identifying volatility skew
- Detecting arbitrage opportunities
- Risk management

### Reliability Features

#### Idempotency
Each task checks if it's already been processed using Redis keys:
```python
key = f"processed:underlying:{product}:{tick_id}"
if redis.exists(key):
    return  # Already processed
```

#### Retry Logic
- Automatic retry on failure (max 3 retries)
- Exponential backoff (5 seconds base delay)
- Task-level error handling

#### Dead Letter Queue (DLQ)
Failed messages after max retries are sent to `dlq:enrichment` Redis list for inspection.

```bash
# View DLQ messages
redis-cli LRANGE dlq:enrichment 0 -1
```

#### Task Acknowledgment
- `task_acks_late=True`: Task ack sent only after completion
- Ensures no message loss on worker crash

## Environment Variables

- `REDIS_URL`: Redis connection for pub/sub and caching
- `MONGO_URL`: MongoDB connection for persistence
- `CELERY_BROKER_URL`: Celery message broker (Redis)
- `CELERY_RESULT_BACKEND`: Celery result storage (Redis)
- `SERVICE_NAME`: Service identifier

## Data Flow

### Underlying Tick Processing
1. Subscriber receives tick from `market:underlying`
2. Dispatches `process_underlying_tick` task
3. Worker:
   - Checks idempotency
   - Stores in MongoDB `underlying_ticks` collection
   - Updates Redis cache `latest:underlying:{product}`
   - Triggers OHLC calculation tasks
   - Publishes to `enriched:underlying`

### Option Chain Processing
1. Subscriber receives chain from `market:option_chain`
2. Dispatches `process_option_chain` task
3. Worker:
   - Calculates PCR, max pain, straddle
   - Analyzes OI build-up
   - Stores in MongoDB `option_chains` collection
   - Updates Redis caches
   - Publishes to `enriched:option_chain`
   - Triggers volatility surface calculation

## MongoDB Collections

### underlying_ticks
```javascript
{
  product: "NIFTY",
  price: 21543.25,
  timestamp: ISODate("2025-01-15T10:30:00Z"),
  tick_id: 12345,
  processed_at: ISODate("2025-01-15T10:30:01Z")
}
```

### option_quotes
```javascript
{
  symbol: "NIFTY20250125C21500",
  product: "NIFTY",
  strike: 21500,
  expiry: "2025-01-25",
  option_type: "CALL",
  bid: 125.50,
  ask: 127.80,
  last: 126.50,
  volume: 5432,
  open_interest: 45678,
  delta: 0.5234,
  gamma: 0.0012,
  vega: 8.45,
  theta: -2.34,
  iv: 0.2145,
  timestamp: ISODate("2025-01-15T10:30:00Z"),
  processed_at: ISODate("2025-01-15T10:30:01Z")
}
```

### option_chains
```javascript
{
  product: "NIFTY",
  expiry: "2025-01-25",
  spot_price: 21543.25,
  pcr_oi: 1.0234,
  pcr_volume: 0.9876,
  atm_strike: 21550,
  atm_straddle_price: 253.25,
  max_pain_strike: 21500,
  total_call_oi: 5000000,
  total_put_oi: 5117000,
  call_buildup_otm: 3000000,
  put_buildup_otm: 2800000,
  calls: [...],
  puts: [...],
  timestamp: ISODate("2025-01-15T10:30:00Z"),
  processed_at: ISODate("2025-01-15T10:30:01Z")
}
```

## Redis Cache Keys

### Latest Data (TTL: 5 minutes)
- `latest:underlying:{product}`: Latest underlying price
- `latest:option:{symbol}`: Latest option quote
- `latest:chain:{product}:{expiry}`: Latest enriched chain
- `latest:pcr:{product}:{expiry}`: Latest PCR values

### Computed Data
- `ohlc:{product}:{window}m`: OHLC for time window
- `volatility_surface:{product}`: IV surface grid
- `iv_surface:{product}`: Sorted set of IV data points

### Operational
- `processed:underlying:{product}:{tick_id}`: Idempotency tracking (TTL: 1 hour)
- `dlq:enrichment`: Dead letter queue (list)

## Performance

### Throughput
- Processes 100-200 messages/second with 4 workers
- Average task completion: 50-100ms
- MongoDB writes: batched where possible

### Scaling

Horizontal scaling:
```bash
# Run multiple worker containers
docker-compose up --scale worker-enricher=5
```

Celery will automatically distribute tasks across workers.

### Monitoring

#### Celery Flower (optional)
```bash
pip install flower
celery -A app flower --port=5555
```

Access at http://localhost:5555 for real-time task monitoring.

#### Task Stats
```python
# In Python shell
from app import celery_app
stats = celery_app.control.inspect().stats()
print(stats)
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run subscriber only
python app.py subscribe

# Run celery worker only
celery -A app worker --loglevel=info

# Run both with supervisord
supervisord -c supervisord.conf
```

## Troubleshooting

### Tasks not processing
1. Check Redis connection: `redis-cli ping`
2. Check Celery worker logs: `docker-compose logs worker-enricher`
3. Inspect task queue: `redis-cli -n 1 KEYS celery*`

### High task latency
1. Increase worker concurrency: `--concurrency=8`
2. Check MongoDB indexes
3. Monitor Redis memory usage

### Messages in DLQ
```bash
# View DLQ
redis-cli LRANGE dlq:enrichment 0 -1

# Replay a message (custom script needed)
python replay_dlq.py
```

## Future Enhancements

- [ ] Add Prometheus metrics endpoint
- [ ] Implement circuit breaker for MongoDB
- [ ] Add more sophisticated IV calculation (actual Black-Scholes)
- [ ] Implement order book analysis
- [ ] Add correlation analysis between products
- [ ] Real-time Greeks calculation for portfolios
