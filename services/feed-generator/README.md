# Unified Feed Generator

Single feed generator service with multiple data source providers.

## Configuration

Set `FEED_PROVIDER` environment variable to choose data source:

### Synthetic Provider (Demo/Testing)
```bash
FEED_PROVIDER=synthetic
```
- Simulated market data
- 24/7 availability
- Free
- Perfect for development

### Global Datafeeds Provider (Production)
```bash
FEED_PROVIDER=globaldatafeeds
GDF_API_KEY=your_api_key
```
- Real NSE/BSE market data
- Market hours only
- Requires API subscription

## Quick Start

### Development (Synthetic)
```bash
docker-compose up feed-generator
# Uses synthetic by default
```

### Production (Real Data)
```bash
# Set in .env or docker-compose.yml
FEED_PROVIDER=globaldatafeeds
GDF_API_KEY=your_key
docker-compose up feed-generator
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FEED_PROVIDER` | Data source: `synthetic` or `globaldatafeeds` | `synthetic` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |

### Synthetic Provider
| Variable | Description | Default |
|----------|-------------|---------|
| `FEED_INTERVAL` | Update interval (seconds) | `1` |

### Global Datafeeds Provider
| Variable | Description | Default |
|----------|-------------|---------|
| `GDF_ENDPOINT` | WebSocket endpoint | `ws://nimblewebstream.lisuns.com:4575` |
| `GDF_API_KEY` | API key | *Required* |
| `SYMBOLS` | Comma-separated symbols | `NIFTY,BANKNIFTY` |
| `POLL_INTERVAL` | Fetch interval (seconds) | `5` |

## Architecture

```
app.py (Entry Point)
  ↓
Provider Factory (based on FEED_PROVIDER)
  ↓
┌─────────────────┬──────────────────────┐
│ Synthetic       │ Global Datafeeds     │
│ Provider        │ Provider             │
├─────────────────┼──────────────────────┤
│ - Simulated     │ - Real market data   │
│ - Always on     │ - Market hours only  │
│ - Free          │ - API subscription   │
└─────────────────┴──────────────────────┘
  ↓
Redis Pub/Sub (market:underlying, market:option_chain)
  ↓
Worker Enricher
```

## Adding New Providers

1. Create `providers/your_provider.py`
2. Implement `BaseFeedProvider` interface
3. Add to `app.py` provider mapping

Example:
```python
# providers/custom_provider.py
from providers.base_provider import BaseFeedProvider

class CustomProvider(BaseFeedProvider):
    def connect(self):
        # Your connection logic
        pass
    
    def run(self):
        # Your data fetching loop
        pass
```

## Switching Providers

No code changes needed - just update environment variable:

```yaml
# docker-compose.yml
services:
  feed-generator:
    environment:
      - FEED_PROVIDER=synthetic  # or globaldatafeeds
```

Restart service:
```bash
docker-compose restart feed-generator
```
