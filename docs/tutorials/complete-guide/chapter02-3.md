## 2.8 Building the Global Datafeeds Provider (Production Option)

The synthetic provider is great for development, but for production you'll want real market data. Let's build the **Global Datafeeds provider** step-by-step.

**Note:** This section is optional - skip to Part 2 Complete if using synthetic data for now.

---

### Step 2.14: Create Base Structure and Configuration

**Action:** Create `providers/gdf_provider.py` and add imports and configuration:

```python
"""
Global Datafeeds Provider

Real market data from Global Datafeeds API.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import structlog
import redis
import gfdlws as gw

# Configuration from environment
GDF_ENDPOINT = os.getenv('GDF_ENDPOINT', 'ws://nimblewebstream.lisuns.com:4575')
GDF_API_KEY = os.getenv('GDF_API_KEY', '')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Market symbols to track
SYMBOLS = os.getenv('GDF_SYMBOLS', os.getenv('SYMBOLS', 'NIFTY,BANKNIFTY')).split(',')
EXCHANGE = os.getenv('EXCHANGE', 'NFO')  # NFO for derivatives

# Polling interval (seconds)
POLL_INTERVAL = int(os.getenv('GDF_POLL_INTERVAL', os.getenv('POLL_INTERVAL', '5')))

# Logger
logger = structlog.get_logger()
```

**Why two env vars for SYMBOLS?**
- `GDF_SYMBOLS` is provider-specific
- Falls back to generic `SYMBOLS` for compatibility
- Allows different symbols for different providers

**Verify:** File should import `gfdlws` - this is the official Global Datafeeds Python SDK.

---

### Step 2.15: Add the Provider Class and Initialization

**Action:** Add the class definition and `__init__` method:

```python
class GlobalDatafeedsProvider:
    """Real-time market data feed using Global Datafeeds API"""
    
    def __init__(self):
        self.logger = logger.bind(provider='globaldatafeeds')
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.connection = None
        self.running = True
        self.current_prices = {}  # Track current spot prices
        
        # Validate configuration
        if not GDF_API_KEY:
            raise ValueError("GDF_API_KEY environment variable must be set")
```

**Why validate API key?**
- Fail fast: Error at startup rather than during data fetch
- Clear error message for users
- Prevents wasted API calls

---

### Step 2.16: Add Connection Method

**Action:** Add the `connect()` method:

```python
def connect(self):
    """Establish connection to Global Datafeeds"""
    try:
        self.logger.info("connecting_to_gdf", endpoint=GDF_ENDPOINT)
        self.connection = gw.ws.connect(GDF_ENDPOINT, GDF_API_KEY)
        self.logger.info("gdf_connected")
        return True
    except Exception as e:
        self.logger.error("connection_failed", error=str(e))
        return False
```

**Non-trivial concept - WebSocket Connection:**
- `gw.ws.connect()` establishes **persistent** connection
- Unlike HTTP (request→response), WebSocket stays open
- Connection is reused for all API calls
- More efficient than reconnecting each time

**Why separate `connect()` method?**
- Allows reconnection after network failures
- Can be called from error handler
- Testable in isolation

---

### Step 2.17: Add Data Fetching Methods

**Action:** Add methods to fetch option chains and underlying quotes:

```python
def fetch_option_chain(self, underlying: str):
    """Fetch complete option chain for underlying"""
    try:
        response = gw.lastquoteoptiongreekschain.get(
            self.connection,
            EXCHANGE,
            underlying
        )
        
        data = json.loads(response)
        
        if data.get('Result'):
            self.logger.info(
                "option_chain_fetched",
                underlying=underlying,
                options_count=len(data['Result'])
            )
            return data['Result']
        return []
            
    except Exception as e:
        self.logger.error("option_chain_fetch_error", underlying=underlying, error=str(e))
        return []

def fetch_underlying_quote(self, symbols: List[str]):
    """Fetch underlying index quotes (NIFTY-I, BANKNIFTY-I)"""
    try:
        # Format: [{"Value":"NIFTY-I"}, {"Value":"BANKNIFTY-I"}]
        instruments = json.dumps([{"Value": f"{symbol}-I"} for symbol in symbols])
        
        response = gw.lastquotearray.get(
            self.connection,
            EXCHANGE,
            instruments,
            'false'  # Full quote, not just LTP
        )
        
        data = json.loads(response)
        
        if data.get('Result'):
            return data['Result']
        return []
            
    except Exception as e:
        self.logger.error("underlying_fetch_error", error=str(e))
        return []
```

**What `lastquoteoptiongreekschain.get()` returns:**
```json
{
  "Result": [
    {
      "InstrumentIdentifier": "OPTIDX_NIFTY_25JAN2024_CE_21500",
      "LastTradePrice": 125.50,
      "OpenInterest": 2500000,
      "IV": 18.5,
      "Delta": 0.55
    }
    // ... 200+ more options
  ]
}
```

**Why the `-I` suffix?**
- Global Datafeeds format: `NIFTY-I` means "NIFTY Index"
- Different from `NIFTY` futures or `NIFTY` options
- Required by the API

---

### Step 2.18: Add Data Transformation Methods

**Action:** Add methods to convert Global Datafeeds format to DeltaStream format:

```python
def transform_option_data(self, option: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Global Datafeeds option data to DeltaStream format"""
    instrument_id = option.get('InstrumentIdentifier', '')
    
    return {
        'instrument': instrument_id,
        'price': float(option.get('LastTradePrice', 0)),
        'timestamp': datetime.now().isoformat(),
        'volume': int(option.get('LastTradeQuantity', 0)),
        'oi': int(option.get('OpenInterest', 0)),
        'bid_qty': int(option.get('TotalBuyQuantity', 0)),
        'ask_qty': int(option.get('TotalSellQuantity', 0)),
        'bid': float(option.get('BestBuyPrice', 0)),
        'ask': float(option.get('BestSellPrice', 0)),
        # Greeks
        'iv': float(option.get('IV', 0)),
        'delta': float(option.get('Delta', 0)),
        'gamma': float(option.get('Gamma', 0)),
        'theta': float(option.get('Theta', 0)),
        'vega': float(option.get('Vega', 0)),
        # Additional info
        'exchange': option.get('Exchange', EXCHANGE),
        'last_trade_time': option.get('LastTradeTime'),
    }

def transform_underlying_data(self, quote: Dict[str, Any]) -> Dict[str, Any]:
    """Transform underlying quote to DeltaStream format"""
    instrument_id = quote.get('InstrumentIdentifier', '')
    symbol = instrument_id.replace('-I', '') if '-I' in instrument_id else instrument_id
    
    return {
        'product': symbol,
        'price': float(quote.get('LastTradePrice', 0)),
        'timestamp': datetime.now().isoformat(),
        'tick_id': int(datetime.now().timestamp() * 1000),
        'volume': int(quote.get('LastTradeQuantity', 0)),
        'open': float(quote.get('Open', 0)),
        'high': float(quote.get('High', 0)),
        'low': float(quote.get('Low', 0)),
        'close': float(quote.get('Close', 0)),
        'change': float(quote.get('PercentChange', 0)),
    }
```

**Why transformation?**

Global Datafeeds uses different field names than our system:

**Before (GDF):**
```python
{"InstrumentIdentifier": "...", "TotalBuyQuantity": 500000}
```

**After (DeltaStream):**
```python
{"instrument": "...", "bid_qty": 500000}
```

**Benefits:**
- Worker Enricher doesn't need to know about GDF
- Can switch providers without changing downstream code
- Consistent naming across system

---

### Step 2.19: Add Publishing Methods

**Action:** Add methods to publish data to Redis:

```python
def publish_to_redis(self, channel: str, data: Dict[str, Any]):
    """Publish data to Redis channel"""
    try:
        self.redis_client.publish(channel, json.dumps(data))
        self.logger.debug("data_published", channel=channel)
    except Exception as e:
        self.logger.error("redis_publish_error", channel=channel, error=str(e))

def publish_option_chain(self, underlying: str, options: List[Dict]):
    """Publish complete option chain (matches synthetic feed format)"""
    try:
        transformed_options = [self.transform_option_data(opt) for opt in options]
        
        chain_data = {
            'type': 'OPTION_CHAIN',
            'product': underlying,
            'timestamp': datetime.now().isoformat(),
            'expiry': transformed_options[0]['last_trade_time'] if transformed_options else None,
            'spot_price': self.current_prices.get(underlying, 0),
            'strikes': list(set([opt['instrument'].split('_')[-2] for opt in transformed_options if '_' in opt['instrument']])),
            'calls': [opt for opt in transformed_options if 'CE' in opt['instrument']],
            'puts': [opt for opt in transformed_options if 'PE' in opt['instrument']],
        }
        
        # Publish to same channel as synthetic feed
        self.publish_to_redis('market:option_chain', chain_data)
        
        self.logger.info("option_chain_published", underlying=underlying, options_count=len(options))
    except Exception as e:
        self.logger.error("chain_publish_error", underlying=underlying, error=str(e))

def publish_underlying_quotes(self, quotes: List[Dict]):
    """Publish underlying index quotes (matches synthetic feed format)"""
    for quote in quotes:
        try:
            transformed = self.transform_underlying_data(quote)
            
            # Match synthetic feed format exactly
            underlying_tick = {
                'type': 'UNDERLYING',
                'product': transformed['product'],
                'price': transformed['price'],
                'timestamp': transformed['timestamp'],
                'tick_id': transformed['tick_id'],
                # Additional real market data
                'volume': transformed.get('volume', 0),
                'open': transformed.get('open', 0),
                'high': transformed.get('high', 0),
                'low': transformed.get('low', 0),
                'close': transformed.get('close', 0),
                'change': transformed.get('change', 0),
            }
            
            # Store current price for chain generation
            self.current_prices[transformed['product']] = transformed['price']
            
            # Publish to same channel as synthetic feed
            self.publish_to_redis('market:underlying', underlying_tick)
            
            self.logger.info("underlying_published", product=transformed['product'], price=transformed['price'])
        except Exception as e:
            self.logger.error("underlying_publish_error", error=str(e))
```

**Key insight - Channel compatibility:**

Both providers publish to the same channels:
- `market:underlying` ✓
- `market:option_chain` ✓

This means Worker Enricher doesn't know/care which provider is running. Perfect drop-in replacement!

---

### Step 2.20: Add Main Loop with Error Handling

**Action:** Add the `run()` method to complete the provider:

```python
def run(self):
    """Main loop - fetch and publish market data"""
    self.logger.info("starting_gdf_provider", symbols=SYMBOLS)
    
    # Connect to Global Datafeeds
    if not self.connect():
        self.logger.error("initial_connection_failed")
        return
    
    while self.running:
        try:
            # 1. Fetch and publish underlying quotes
            underlying_quotes = self.fetch_underlying_quote(SYMBOLS)
            if underlying_quotes:
                self.publish_underlying_quotes(underlying_quotes)
            
            # 2. Fetch and publish option chains for each symbol
            for symbol in SYMBOLS:
                option_chain = self.fetch_option_chain(symbol)
                if option_chain:
                    self.publish_option_chain(symbol, option_chain)
            
            # Wait before next fetch
            self.logger.debug("waiting", seconds=POLL_INTERVAL)
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            self.logger.info("shutdown_requested")
            self.running = False
            break
        except Exception as e:
            self.logger.error("loop_error", error=str(e))
            # Try to reconnect
            self.logger.info("attempting_reconnection")
            time.sleep(5)
            self.connect()
```

**Non-trivial concept - Resilience:**

What can go wrong?
1. Network timeout → catch exception, wait, reconnect
2. API error → log it, continue loop
3. Invalid data → transformation fails, log it, skip that item

**Why not crash?**
- Temporary failures are normal in production
- Network glitches happen
- API maintenance occurs
- Auto-recovery keeps system running

**Verify:** Complete `providers/gdf_provider.py` file should now have ~300 lines.

---

### Step 2.21: Test the Global Datafeeds Provider

**Action:** Configure and test the real data provider:

```bash
# Set provider to Global Datafeeds
export FEED_PROVIDER=globaldatafeeds
export GDF_API_KEY=your_actual_api_key

# Run feed generator
python app.py
```

**Expected output (during market hours 9:15 AM - 3:30 PM IST):**
```json
{"event": "feed_generator_starting", "provider": "globaldatafeeds"}
{"event": "connecting_to_gdf", "endpoint": "ws://nimblewebstream.lisuns.com:4575"}
{"event": "gdf_connected"}
{"event": "option_chain_fetched", "underlying": "NIFTY", "options_count": 248}
{"event": "underlying_published", "product": "NIFTY", "price": 21543.50}
```

**Common issues:**

1. **"GDF_API_KEY must be set"**
   - Solution: Add your API key to `.env` file

2. **"No data received"**
   - Solution: Check if market hours (9:15 AM - 3:30 PM IST, Mon-Fri)
   - NSE closed on weekends/holidays

3. **Connection timeout**
   - Solution: Verify network connectivity and API key validity

**To get Global Datafeeds API key:**
1. Visit https://globaldatafeeds.in/
2. Sign up and subscribe to NSE data plan
3. Copy API key from dashboard

---

---

**Navigation:**
← [Previous: Chapter 2-2](chapter02-2.md) | [Next: Chapter 2-4](chapter02-4.md) →

---
