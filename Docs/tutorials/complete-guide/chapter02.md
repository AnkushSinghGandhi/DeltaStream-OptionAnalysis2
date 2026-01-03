## Part 2: Building the Feed Generator Service

### Learning Objectives

By the end of Part 2, you will understand:

1. **Option pricing fundamentals** - Intrinsic value, time value, Greeks
2. **Market data simulation** - Geometric Brownian motion for price movements
3. **Data structure design** - How to model option chains, quotes, and ticks
4. **Redis pub/sub patterns** - Publishing market data to channels
5. **Production service structure** - Configuration, logging, error handling
6. **Dockerization** - Creating production-ready container images

---

### 2.1 Understanding Option Pricing (Conceptual Foundation)

Before we write code, you need to understand **how options are priced**. This is critical because our feed generator must create **realistic** data.

#### What is an Option?

An **option** is a contract giving the right (not obligation) to **buy** (call) or **sell** (put) an asset at a **strike price** before **expiry**.

```
Example:
- NIFTY spot price: 21,500
- Buy NIFTY 21,500 Call expiring Jan 25
- Premium paid: ₹150

Scenarios at expiry:
1. NIFTY = 21,700 → Profit = (21,700 - 21,500) - 150 = ₹50
2. NIFTY = 21,300 → Loss = ₹150 (option expires worthless)
```

#### Option Price Components

**Option Price = Intrinsic Value + Time Value**

**1. Intrinsic Value** (easy to calculate):

For **Call**:
```
Intrinsic = max(0, Spot - Strike)

Examples:
- Spot=21,500, Strike=21,000 → Intrinsic = 500 (in-the-money, ITM)
- Spot=21,500, Strike=21,500 → Intrinsic = 0 (at-the-money, ATM)
- Spot=21,500, Strike=22,000 → Intrinsic = 0 (out-of-the-money, OTM)
```

For **Put**:
```
Intrinsic = max(0, Strike - Spot)

Examples:
- Spot=21,500, Strike=22,000 → Intrinsic = 500 (ITM)
- Spot=21,500, Strike=21,500 → Intrinsic = 0 (ATM)
- Spot=21,500, Strike=21,000 → Intrinsic = 0 (OTM)
```

**2. Time Value** (complex to calculate):

Time value depends on:
- **Time to expiry**: More time = more value (anything can happen)
- **Volatility**: Higher volatility = more value (more chance of big move)
- **Moneyness**: ATM options have highest time value

**Why does an OTM option have value?**

Example: NIFTY = 21,500, 22,000 Call, expiry in 30 days, premium = ₹50

- Intrinsic value = 0 (OTM)
- But premium = ₹50 (why?)
- **Time value** = ₹50 (market believes NIFTY could reach 22,000 in 30 days)

**Time value decays** (theta decay):
- 30 days to expiry: Premium = ₹50
- 15 days to expiry: Premium = ₹30 (less time for big move)
- 1 day to expiry: Premium = ₹5 (very unlikely to move 500 points in 1 day)
- Expiry day: Premium = ₹0 (if still OTM)

#### Greeks (Sensitivity Measures)

**Delta**: How much option price changes when spot moves ₹1

```
Call Delta:
- Deep ITM call (Strike 21,000, Spot 22,000): Delta ≈ 0.95 (moves almost 1:1 with spot)
- ATM call (Strike 21,500, Spot 21,500): Delta ≈ 0.50 (moves half as much)
- Deep OTM call (Strike 22,000, Spot 21,000): Delta ≈ 0.05 (barely moves)

Put Delta: Always negative (put gains when spot falls)
- Deep ITM put: Delta ≈ -0.95
- ATM put: Delta ≈ -0.50
- Deep OTM put: Delta ≈ -0.05
```

**Gamma**: How much delta changes when spot moves ₹1

```
- ATM options have highest gamma (delta changes rapidly)
- ITM/OTM options have low gamma (delta stable)
```

**Vega**: How much option price changes when IV increases 1%

```
- ATM options have highest vega
- Longer expiry options have higher vega
```

**Theta**: How much option price decays per day

```
- Always negative for option buyers
- Accelerates near expiry (time decay curve is non-linear)
```

**Why do we need to know this?**

Our feed generator must create data that:
- Respects intrinsic value (call at 21,000 when spot=21,500 must be worth ≥500)
- Has realistic time value (ATM options costlier than OTM)
- Greeks make sense (ATM delta ≈ 0.50, ITM delta \u003e 0.50)

Unrealistic data breaks downstream analytics (e.g., PCR calculation assumes realistic OI distribution).

---

### 2.2 Implementing the Feed Generator: Project Structure

Create the service directory:

```bash
cd services/feed-generator
```

**Files we'll create:**

```
services/feed-generator/
├── app.py                  # Main application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container image
└── README.md              # Service documentation
```

---

### 2.3 Dependencies: `requirements.txt`

```txt
redis==5.0.1
structlog==23.2.0
```

**Why these?**

- `redis`: Python client for Redis (pub/sub, caching)
- `structlog`: Structured logging library (JSON logs for production)

**Why NOT use:**
- `numpy/scipy`: For demo, we use simplified math (pure Python)
- In production: Use `py_vollib` or `QuantLib` for accurate option pricing

---

### 2.4 Building `app.py`: The Feed Generator

Let's build this incrementally, explaining every non-trivial section.

#### Part 2.4.1: Imports and Configuration

```python
#!/usr/bin/env python3
"""
Feed Generator Service

Generates realistic synthetic option market data including:
- Products (underlying symbols)
- Expiry dates
- Strike prices
- Option quotes (call/put, bid/ask, Greeks)
- Option chains
- Underlying price movements

Publishes data to Redis pub/sub for consumption by workers.
"""

import os
import time
import json
import redis
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import structlog
```

**Line-by-line:**

```python
#!/usr/bin/env python3
```
- **Shebang**: Tells OS to use `python3` interpreter
- Allows running as: `./app.py` instead of `python app.py`
- Must have execute permission: `chmod +x app.py`

```python
"""..."""
```
- **Module docstring**: Describes what this service does
- Good practice: Always document the "why" at file level

```python
from typing import List, Dict, Any
```
- **Type hints**: `List[str]` means "list of strings"
- Not enforced at runtime (Python is dynamically typed)
- **Why use?** IDEs autocomplete, catches bugs early, self-documenting

```python
import structlog
```
- **Structured logging**: Outputs JSON instead of plain text
- **Why?** Logs go to centralized system (Loki/Elasticsearch) where JSON is queryable

```python
# Structured logging setup
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()
```

**What does this do?**

Without `structlog`:
```python
print(f"[{datetime.now()}] INFO: Published tick for NIFTY, price=21500")
```
Output:
```
[2025-01-03 18:24:40] INFO: Published tick for NIFTY, price=21500
```

With `structlog`:
```python
logger.info("tick_published", product="NIFTY", price=21500)
```
Output:
```json
{"event": "tick_published", "product": "NIFTY", "price": 21500, "timestamp": "2025-01-03T18:24:40Z"}
```

**Why is JSON better?**

Query in Loki:
```
{service="feed-generator"} | json | price > 21000 | logfmt
```

Can't easily query plain text logs.

```python
# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
FEED_INTERVAL = float(os.getenv('FEED_INTERVAL', '1'))  # seconds
SERVICE_NAME = os.getenv('SERVICE_NAME', 'feed-generator')
```

**Why environment variables?**

**Bad** (hardcoded):
```python
REDIS_URL = 'redis://localhost:6379/0'
```
- Breaks in Docker (Redis is at `redis:6379` not `localhost:6379`)
- Breaks in production (different Redis host)
- Can't test with different config without code changes

**Good** (environment variables):
```python
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
```
- `os.getenv('KEY', 'default')`: Read from environment, use default if not set
- Docker: `docker run -e REDIS_URL=redis://redis:6379/0`
- Local: `export REDIS_URL=redis://localhost:6379/0 && python app.py`

```python
# Market data configuration
PRODUCTS = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'AAPL', 'TSLA', 'SPY', 'QQQ']
BASE_PRICES = {
    'NIFTY': 21500,
    'BANKNIFTY': 45000,
    'FINNIFTY': 19500,
    'SENSEX': 71000,
    'AAPL': 185,
    'TSLA': 245,
    'SPY': 475,
    'QQQ': 395
}
```

**Why constants at module level?**
- Easier to modify (single place to add new products)
- Self-documenting (see all products at a glance)
- Could be moved to config file (JSON/YAML) for production

---

#### Part 2.4.2: The `OptionFeedGenerator` Class

```python
class OptionFeedGenerator:
    """
    Generates realistic option market data feeds.
    
    This class simulates a market data feed by generating:
    - Underlying price ticks with realistic volatility
    - Option chains with multiple strikes and expiries
    - Option quotes with bid/ask spreads and Greeks
    - Time and sales data
    """
    
    def __init__(self):
        """Initialize the feed generator with Redis connection."""
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.current_prices = BASE_PRICES.copy()
        self.logger = logger.bind(service=SERVICE_NAME)
        self.tick_count = 0
```

**Why use a class?**

**Alternative: Functional approach**
```python
redis_client = redis.from_url(REDIS_URL)
current_prices = BASE_PRICES.copy()

def publish_tick(product):
    # use global redis_client, current_prices
    ...
```

**Problems:**
- Global state (hard to test, can't run two generators in same process)
- No encapsulation (any code can modify `current_prices`)

**Class approach:**
```python
class OptionFeedGenerator:
    def __init__(self):
        self.redis_client = ...
        self.current_prices = ...
```

**Benefits:**
- Encapsulation: `current_prices` is instance variable (protected)
- Testability: Can create multiple instances with different configs
- State management: Each instance tracks its own `tick_count`

```python
self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
```

**What is `decode_responses=True`?**

Without it:
```python
redis_client.get('key')  # Returns: b'value' (bytes)
```

With it:
```python
redis_client.get('key')  # Returns: 'value' (string)
```

**Why use it?**
- We're publishing JSON strings, not binary data
- Avoid manual decoding: `value.decode('utf-8')`

```python
self.current_prices = BASE_PRICES.copy()
```

**Why `.copy()`?**

Without copy:
```python
self.current_prices = BASE_PRICES  # Reference to same dict
self.current_prices['NIFTY'] = 22000
print(BASE_PRICES['NIFTY'])  # 22000 (oops! Modified global)
```

With copy:
```python
self.current_prices = BASE_PRICES.copy()  # New dict
self.current_prices['NIFTY'] = 22000
print(BASE_PRICES['NIFTY'])  # 21500 (global unchanged)
```

```python
self.logger = logger.bind(service=SERVICE_NAME)
```

**What is `.bind()`?**

Without bind:
```python
logger.info("event", product="NIFTY")
# Output: {"event": "event", "product": "NIFTY"}
```

With bind:
```python
logger = logger.bind(service="feed-generator")
logger.info("event", product="NIFTY")
# Output: {"event": "event", "product": "NIFTY", "service": "feed-generator"}
```

**Benefit**: `service` field automatically added to every log (helps filter logs by service in Loki).

---

#### Part 2.4.3: Generating Expiry Dates

```python
def generate_expiry_dates(self, product: str) -> List[str]:
    """
    Generate realistic expiry dates for options.
    
    Returns weekly and monthly expiries for the next 3 months.
    
    Args:
        product: The underlying product symbol
        
    Returns:
        List of expiry dates in YYYY-MM-DD format
    """
    expiries = []
    today = datetime.now()
    
    # Weekly expiries for next 8 weeks
    for week in range(8):
        # Thursday expiry (Indian market convention)
        days_ahead = (3 - today.weekday() + 7 * week) % 7 + 7 * week
        if days_ahead == 0:
            days_ahead = 7
        expiry = today + timedelta(days=days_ahead)
        expiries.append(expiry.strftime('%Y-%m-%d'))
    
    return sorted(list(set(expiries)))
```

**Why weekly expiries on Thursday?**

- Indian markets (NSE): Options expire on **Thursday**
- US markets: Options expire on **Friday**
- `weekday()` returns: Monday=0, Tuesday=1, Wednesday=2, **Thursday=3**, Friday=4

**Algorithm breakdown:**

```python
days_ahead = (3 - today.weekday() + 7 * week) % 7 + 7 * week
```

Let's trace for `today = Monday (weekday=0), week=0`:

```
(3 - 0 + 7*0) % 7 + 7*0
= (3 - 0) % 7 + 0
= 3 % 7 + 0
= 3
```

So expiry is **3 days from Monday = Thursday** ✓

For `today = Monday, week=1`:

```
(3 - 0 + 7*1) % 7 + 7*1
= 10 % 7 + 7
= 3 + 7
= 10
```

So expiry is **10 days from Monday = next week Thursday** ✓

**Edge case: What if today IS Thursday?**

```python
if days_ahead == 0:
    days_ahead = 7
```

- If today is Thursday (weekday=3): `days_ahead = (3-3+0)%7 = 0`
- We want **next Thursday**, not today → set to 7

```python
expiries.append(expiry.strftime('%Y-%m-%d'))
...
return sorted(list(set(expiries)))
```

**Why `set()` then `list()`?**

- `set()`: Removes duplicates (weekly and monthly might overlap)
- `sorted()`: Chronological order (earliest first)

---

#### Part 2.4.4: Generating Strike Prices

```python
def generate_strike_prices(self, product: str, spot_price: float) -> List[float]:
    """
    Generate realistic strike prices around the current spot price.
    
    Args:
        product: The underlying product symbol
        spot_price: Current price of the underlying
        
    Returns:
        List of strike prices
    """
    # Determine strike interval based on product
    if product in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
        interval = 50 if product == 'NIFTY' else 100
    elif product == 'SENSEX':
        interval = 100
    else:
        interval = 5  # For stocks
    
    # Generate strikes +/- 20% from spot
    strikes = []
    base_strike = round(spot_price / interval) * interval
    
    for i in range(-10, 11):
        strike = base_strike + (i * interval)
        if strike > 0:
            strikes.append(float(strike))
    
    return sorted(strikes)
```

**Why different intervals for different products?**

Real NSE example:
- **NIFTY** (spot=21,500): Strikes at 21,000 | 21,050 | 21,100 | ... (50-point intervals)
- **BANKNIFTY** (spot=45,000): Strikes at 44,500 | 44,600 | 44,700 | ... (100-point intervals)
- **Stocks** (AAPL spot=$185): Strikes at $180 | $185 | $190 | ... ($5 intervals)

**If we used same interval for all:**
- NIFTY with $5 interval: 21,000 | 21,005 | 21,010 | ... (too granular, 400 strikes!)
- AAPL with 50-point interval: $150 | $200 | $250 | ... (too coarse, only 3 strikes)

```python
base_strike = round(spot_price / interval) * interval
```

**What does this do?**

Example: `spot_price=21,537`, `interval=50`

```
base_strike = round(21537 / 50) * 50
            = round(430.74) * 50
            = 431 * 50
            = 21,550
```

**Snaps to nearest strike** (21,537 → 21,550).

**Why?**
- Strikes are always round numbers (never 21,537.42)
- Ensures ATM strike is closest to spot

```python
for i in range(-10, 11):
    strike = base_strike + (i * interval)
```

**Generates 21 strikes**:
- `i=-10`: base - 10*interval (deep OTM put / deep ITM call)
- `i=0`: base (ATM)
- `i=+10`: base + 10*interval (deep ITM put / deep OTM call)

**Example** (NIFTY, spot=21,500):
```
base = 21,500
strikes = [21,000, 21,050, ..., 21,500, ..., 22,000]
```

Covers **21,000 to 22,000** (±2.3% from spot).

---

#### Part 2.4.5: Option Pricing (Simplified Black-Scholes)

This is the **most complex** part. We're implementing a simplified option pricing model.

```python
def calculate_option_price(self, spot: float, strike: float, 
                          option_type: str, tte: float, volatility: float = 0.20) -> Dict[str, float]:
    """
    Calculate option price using simplified Black-Scholes approximation.
    
    This is a simplified model for demo purposes. In production,
    use a proper options pricing library.
    
    Args:
        spot: Current underlying price
        strike: Option strike price
        option_type: 'CALL' or 'PUT'
        tte: Time to expiry in years
        volatility: Implied volatility (annualized)
        
    Returns:
        Dictionary with option price and Greeks
    """
    import math
    
    # Risk-free rate (simplified)
    r = 0.05
    
    # Intrinsic value
    if option_type == 'CALL':
        intrinsic = max(0, spot - strike)
    else:
        intrinsic = max(0, strike - spot)
```

**Intrinsic value** (explained earlier):
- Call intrinsic = max(0, spot - strike)
- Put intrinsic = max(0, strike - spot)

```python
    # Time value (simplified)
    if tte > 0:
        moneyness = spot / strike
        time_value = spot * volatility * math.sqrt(tte) * 0.4
```

**Let's break this down:**

Real Black-Scholes formula (complex):
```
C = S*N(d1) - K*e^(-rT)*N(d2)
where d1, d2 involve CDF of normal distribution
```

**Our simplification** (good enough for demo):
```python
time_value = spot * volatility * math.sqrt(tte) * 0.4
```

**Why does this formula make sense?**

1. **Proportional to spot**: Higher spot → higher option price
   - NIFTY 21,500 call worth more than when NIFTY was 10,000

2. **Proportional to volatility**: Higher vol → higher time value
   - If NIFTY moves ±2% daily (high vol), options are valuable
   - If NIFTY moves ±0.1% daily (low vol), options are cheap

3. **Square root of time**: Time decay is non-linear
   - 30-day option NOT worth 2x of 15-day option
   - `sqrt(30/365) = 0.287`, `sqrt(15/365) = 0.203`
   - Ratio = 0.287/0.203 = **1.41x** (not 2x)

4. **Constant 0.4**: Tuning factor (in real BS model, this comes from N(d1) calculations)

**Example calculation:**

```
spot = 21,500
strike = 21,500 (ATM)
tte = 30/365 = 0.082 years
volatility = 0.20 (20% annual)

time_value = 21500 * 0.20 * sqrt(0.082) * 0.4
           = 21500 * 0.20 * 0.286 * 0.4
           = ₹492
```

So ATM option with 30 days to expiry ≈ ₹492 (sounds reasonable).

```python
        # Adjust for moneyness
        if option_type == 'CALL':
            if moneyness > 1.0:
                time_value *= (1.2 - 0.2 * (moneyness - 1.0))
            else:
                time_value *= moneyness
```

**What is moneyness?**

```
moneyness = spot / strike

- moneyness > 1.0: ITM call (spot > strike)
- moneyness = 1.0: ATM call (spot = strike)
- moneyness < 1.0: OTM call (spot < strike)
```

**Why adjust time value by moneyness?**

Real phenomenon: **Time value is highest for ATM options**.

Example (NIFTY = 21,500):
- Strike 21,000 (ITM): Premium = 500 intrinsic + 200 time = 700
- Strike 21,500 (ATM): Premium = 0 intrinsic + 450 time = 450
- Strike 22,000 (OTM): Premium = 0 intrinsic + 150 time = 150

**Algorithm**:

For **ITM call** (`moneyness > 1.0`):
```python
time_value *= (1.2 - 0.2 * (moneyness - 1.0))
```

Example: spot=21,500, strike=21,000, moneyness=1.024
```
time_value *= (1.2 - 0.2 * 0.024)
            *= 1.195
```
**Slight increase** (ITM options have less time value than ATM, but still some).

For **OTM call** (`moneyness < 1.0`):
```python
time_value *= moneyness
```

Example: spot=21,500, strike=22,000, moneyness=0.977
```
time_value *= 0.977
```
**Decreases to 97.7%** of base time value.

**Result**: ATM has max time value, ITM/OTM have progressively less.

```python
        else:
            time_value = 0
```

If `tte = 0` (expiry day), **time value = 0** (only intrinsic value remains).

```python
    option_price = intrinsic + time_value
```

**Total option price = intrinsic + time value** (core formula)!

```python
    # Simple Greeks approximation
    delta = 0.5 if abs(spot - strike) < strike * 0.02 else (0.8 if intrinsic > 0 else 0.2)
    if option_type == 'PUT':
        delta = delta - 1
    
    gamma = 0.01 if abs(spot - strike) < strike * 0.02 else 0.005
    vega = spot * math.sqrt(tte) * 0.01 if tte > 0 else 0
    theta = -option_price / (tte * 365) if tte > 0 else 0
```

**Simplified Greeks** (real BS model uses derivatives of pricing equation):

**Delta:**
```python
delta = 0.5 if abs(spot - strike) < strike * 0.02 else (0.8 if intrinsic > 0 else 0.2)
```

- If strike within 2% of spot (ATM): delta = 0.5
- Else if ITM: delta = 0.8
- Else (OTM): delta = 0.2

**Put delta:**
```python
if option_type == 'PUT':
    delta = delta - 1
```

Put delta is always negative (put gains when spot falls).
- Call delta = 0.5 → Put delta = -0.5

**Theta** (time decay per day):
```python
theta = -option_price / (tte * 365)
```

If option is worth ₹365 with 365 days to expiry:
```
theta = -365 / 365 = -1
```

**Loses ₹1/day on average** (linear approximation; real theta decay is non-linear).

```python
    return {
        'price': round(option_price, 2),
        'delta': round(delta, 4),
        'gamma': round(gamma, 4),
        'vega': round(vega, 4),
        'theta': round(theta, 4),
        'iv': volatility
    }
```

**Returns all metrics** needed for a complete option quote.

---

#### Part 2.4.6: Generating Option Quotes

```python
def generate_option_quote(self, product: str, spot_price: float, 
                          strike: float, expiry: str, option_type: str) -> Dict[str, Any]:
    """
    Generate a complete option quote with bid/ask spread.
    """
    # Calculate time to expiry
    expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
    tte = (expiry_date - datetime.now()).days / 365.0
    tte = max(0.001, tte)  # Minimum 1 day
    
    # Calculate option price
    volatility = random.uniform(0.15, 0.35)  # Random IV between 15-35%
    calc = self.calculate_option_price(spot_price, strike, option_type, tte, volatility)
    
    # Add bid/ask spread (0.5-2% of price)
    spread_pct = random.uniform(0.005, 0.02)
    bid_price = calc['price'] * (1 - spread_pct)
    ask_price = calc['price'] * (1 + spread_pct)
    
    # Generate volumes
    volume = random.randint(100, 10000)
    open_interest = random.randint(1000, 100000)
    
    return {
        'symbol': f"{product}{expiry.replace('-', '')}{option_type[0]}{int(strike)}",
        'product': product,
        'strike': strike,
        'expiry': expiry,
        'option_type': option_type,
        'bid': round(bid_price, 2),
        'ask': round(ask_price, 2),
        'last': round(calc['price'], 2),
        'volume': volume,
        'open_interest': open_interest,
        'delta': calc['delta'],
        'gamma': calc['gamma'],
        'vega': calc['vega'],
        'theta': calc['theta'],
        'iv': round(calc['iv'], 4),
        'timestamp': datetime.now().isoformat()
    }
```

**Bid/ask spread simulation:**

Real market:
- **Bid**: Price buyers are willing to pay
- **Ask**: Price sellers are demanding
- **Spread**: ask - bid (market maker's profit)

Example:
- Fair price (mid): ₹100
- Bid: ₹99 (buyer says "I'll pay 99")
- Ask: ₹101 (seller says "I want 101")
- Spread: ₹2 or 2%

```python
spread_pct = random.uniform(0.005, 0.02)  # 0.5% to 2%
bid_price = calc['price'] * (1 - spread_pct)
ask_price = calc['price'] * (1 + spread_pct)
```

**Why random spread?**
- Liquid options (ATM, near expiry): tighter spread (0.5%)
- Illiquid options (far OTM, long expiry): wider spread (2%)

We approximate with random (good enough for demo).

**Symbol format:**
```python
'symbol': f"{product}{expiry.replace('-', '')}{option_type[0]}{int(strike)}"
```

Example:
```
product = "NIFTY"
expiry = "2025-01-25"
option_type = "CALL"
strike = 21500

symbol = "NIFTY20250125C21500"
```

This is **NSE option symbol format** (real options are named this way).

---

#### Part 2.4.7: Generating Complete Option Chains

```python
def generate_option_chain(self, product: str, expiry: str) -> Dict[str, Any]:
    """
    Generate a complete option chain for a product and expiry.
    """
    spot_price = self.current_prices[product]
    strikes = self.generate_strike_prices(product, spot_price)
    
    calls = []
    puts = []
    
    for strike in strikes:
        call = self.generate_option_quote(product, spot_price, strike, expiry, 'CALL')
        put = self.generate_option_quote(product, spot_price, strike, expiry, 'PUT')
        calls.append(call)
        puts.append(put)
    
    return {
        'product': product,
        'expiry': expiry,
        'spot_price': spot_price,
        'strikes': strikes,
        'calls': calls,
        'puts': puts,
        'timestamp': datetime.now().isoformat()
    }
```

**Simple aggregation** of individual quotes into a chain.

For 21 strikes:
- 21 calls
- 21 puts
- Total: 42 options in one chain

---

#### Part 2.4.8: Price Movement (Geometric Brownian Motion)

```python
def update_underlying_price(self, product: str):
    """
    Update the underlying price with realistic random walk.
    
    Uses geometric Brownian motion to simulate realistic price movements.
    """
    current_price = self.current_prices[product]
    
    # Volatility based on product type
    if product in ['NIFTY', 'SENSEX']:
        volatility = 0.0002  # Lower volatility for indices
    elif product in ['BANKNIFTY', 'FINNIFTY']:
        volatility = 0.0003
    else:
        volatility = 0.0005  # Higher for stocks
    
    # Random price change
    change_pct = random.gauss(0, volatility)
    new_price = current_price * (1 + change_pct)
    
    # Ensure price stays within reasonable bounds
    base_price = BASE_PRICES[product]
    if new_price < base_price * 0.95 or new_price > base_price * 1.05:
        new_price = base_price + random.uniform(-base_price * 0.02, base_price * 0.02)
    
    self.current_prices[product] = round(new_price, 2)
```

**What is Geometric Brownian Motion (GBM)?**

Stock prices follow:
```
S(t+1) = S(t) * (1 + μ*dt + σ*sqrt(dt)*Z)

where:
  μ = drift (average return, we use 0 for demo)
  σ = volatility
  Z = random normal (mean=0, std=1)
  dt = time step (1 second in our case)
```

**Simplified version:**
```python
change_pct = random.gauss(0, volatility)
new_price = current_price * (1 + change_pct)
```

`random.gauss(0, volatility)`:
- **Normal distribution** with mean=0, std=volatility
- Returns values like: -0.0003, 0.0001, 0.0005, -0.0002, ...

**Example:**

```
current_price = 21,500
volatility = 0.0002
change_pct = random.gauss(0, 0.0002)  # Returns 0.00015 (example)
new_price = 21,500 * (1 + 0.00015)
          = 21,500 * 1.00015
          = 21,503.225
          ≈ 21,503.23
```

Price **increased by ₹3.23** (~0.015%).

**Next tick:**
```
change_pct = -0.00021 (random, could be negative)
new_price = 21,503.23 * (1 - 0.00021)
          = 21,503.23 * 0.99979
          = 21,498.71
```

Price **decreased by ₹4.52**.

**This creates realistic price movements** (small random walks, like real markets).

**Bounds check:**
```python
if new_price < base_price * 0.95 or new_price > base_price * 1.05:
    new_price = base_price + random.uniform(-base_price * 0.02, base_price * 0.02)
```

**Why?**
- Without bounds: Price could drift to 0 or infinity over time
- With bounds: Price stays within ±5% of base price

**In production:**
- Remove bounds (let price drift naturally)
- Use real market data instead of simulation

---

#### Part 2.4.9: Publishing to Redis

```python
def publish_tick(self, product: str):
    """
    Publish a complete market tick for a product.
    
    Generates and publishes:
    - Underlying price update
    - Option chain for nearest expiry
    - Individual option quotes
    """
    # Update underlying price
    self.update_underlying_price(product)
    spot_price = self.current_prices[product]
    
    # Get expiries
    expiries = self.generate_expiry_dates(product)
    nearest_expiry = expiries[0] if expiries else None
    
    # Publish underlying tick
    underlying_tick = {
        'type': 'UNDERLYING',
        'product': product,
        'price': spot_price,
        'timestamp': datetime.now().isoformat(),
        'tick_id': self.tick_count
    }
    self.redis_client.publish('market:underlying', json.dumps(underlying_tick))
    
    # Every 5 ticks, publish full option chain
    if self.tick_count % 5 == 0 and nearest_expiry:
        option_chain = self.generate_option_chain(product, nearest_expiry)
        self.redis_client.publish('market:option_chain', json.dumps(option_chain))
        
        self.logger.info(
            "published_option_chain",
            product=product,
            expiry=nearest_expiry,
            num_strikes=len(option_chain['strikes']),
            spot_price=spot_price
        )
    
    self.tick_count += 1
```

**Redis publish:**
```python
self.redis_client.publish('market:underlying', json.dumps(underlying_tick))
```

**What happens?**
1. `json.dumps(underlying_tick)`: Convert Python dict to JSON string
2. `publish('market:underlying', ...)`: Send to Redis channel `market:underlying`
3. All subscribers to that channel receive the message

**Why publish every tick, but chain every 5 ticks?**

- **Underlying price**: Changes every second (need high frequency)
- **Option chain**: 42 options * JSON = large payload (~50KB)

Publishing chain every second:
- 50KB * 8 products * 86,400 seconds/day = **34GB/day** of Redis traffic

Publishing chain every 5 seconds:
- 50KB * 8 * 17,280 ticks/day = **6.9GB/day**

**Trade-off**: Slightly stale option data (max 5 seconds old) for 5x less bandwidth.

```python
if self.tick_count % 5 == 0:
```

**Modulo trick**:
- `tick_count=0`: `0 % 5 = 0` → publish chain
- `tick_count=1`: `1 % 5 = 1` → skip
- `tick_count=5`: `5 % 5 = 0` → publish chain
- Every 5th tick publishes chain

---

#### Part 2.4.10: Main Loop

```python
def run(self):
    """
    Main loop: continuously generate and publish market data.
    """
    self.logger.info(
        "feed_generator_started",
        products=PRODUCTS,
        feed_interval=FEED_INTERVAL
    )
    
    try:
        while True:
            # Publish ticks for all products
            for product in PRODUCTS:
                self.publish_tick(product)
            
            if self.tick_count % 10 == 0:
                self.logger.info(
                    "feed_status",
                    tick_count=self.tick_count,
                    current_prices=self.current_prices
                )
            
            time.sleep(FEED_INTERVAL)
            
    except KeyboardInterrupt:
        self.logger.info("feed_generator_stopped")
    except Exception as e:
        self.logger.error("feed_generator_error", error=str(e), exc_info=True)
        raise
```

**Infinite loop pattern:**

```python
while True:
    # Do work
    time.sleep(FEED_INTERVAL)
```

**Why `time.sleep()`?**
- Without sleep: Loop runs millions of times per second (wastes CPU)
- With sleep: Loop runs once per second (controlled rate)

**Graceful shutdown:**
```python
except KeyboardInterrupt:
    self.logger.info("feed_generator_stopped")
```

User presses `Ctrl+C` → `KeyboardInterrupt` exception → log and exit cleanly.

**Error handling:**
```python
except Exception as e:
    self.logger.error("feed_generator_error", error=str(e), exc_info=True)
    raise
```

- Any unexpected error: Log with full traceback (`exc_info=True`)
- `raise`: Re-raise exception (so Docker sees container failed and can restart)

---

#### Part 2.4.11: Entry Point

```python
if __name__ == '__main__':
    generator = OptionFeedGenerator()
    generator.run()
```

**What is `if __name__ == '__main__':`?**

- If you run: `python app.py` → `__name__` is `'__main__'` → code runs
- If you import: `from app import OptionFeedGenerator` → `__name__` is `'app'` → code doesn't run

**Why?**
- Allows using this file as both **executable** (`python app.py`) and **library** (`import app`)

---

### 2.5 Creating the Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Run the feed generator
CMD ["python", "app.py"]
```

**Line-by-line:**

```dockerfile
FROM python:3.9-slim
```
- **Base image**: Start with Python 3.9 (slim = minimal size, no build tools)
- **Why slim?** 150MB instead of 1GB (faster builds, smaller images)

```dockerfile
WORKDIR /app
```
- **Set working directory** inside container to `/app`
- All subsequent commands run from `/app`

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- **Copy dependencies first** (before code)
- **Why?** Docker layer caching:
  - If `requirements.txt` unchanged → reuse cached layer (fast)
  - If `app.py` changes but `requirements.txt` doesn't → don't reinstall packages

**Anti-pattern** (slower):
```dockerfile
COPY . .                      # Copy everything
RUN pip install -r requirements.txt  # Reinstalls even if only app.py changed
```

**Good pattern** (faster):
```dockerfile
COPY requirements.txt .       # Copy deps first
RUN pip install ...           # Install (cached if deps unchanged)
COPY app.py .                 # Copy code (changes frequently)
```

```dockerfile
CMD ["python", "app.py"]
```
- **Default command** when container starts
- Equivalent to running `python app.py` in the container

---

### 2.6 Testing the Feed Generator

**Step 1: Build the image**

```bash
cd services/feed-generator
docker build -t deltastream-feed-generator .
```

**What happens?**
1. Reads `Dockerfile`
2. Pulls `python:3.9-slim` (if not cached)
3. Runs each instruction (COPY, RUN, etc.)
4. Tags final image as `deltastream-feed-generator`

**Step 2: Run locally (without Docker Compose)**

Start Redis first:
```bash
docker run -d --name test-redis -p 6379:6379 redis:latest
```

Run feed generator:
```bash
docker run --rm \
  --name feed-generator \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  deltastream-feed-generator
```

**Why `host.docker.internal`?**

- From container's perspective, `localhost` is the container itself, not your machine
- `host.docker.internal` is Docker's magic DNS name for "host machine"
- Allows container to reach Redis running on host

**Step 3: Subscribe to see messages**

Open another terminal:
```bash
docker exec -it test-redis redis-cli
SUBSCRIBE market:underlying
```

You should see:
```
1) "subscribe"
2) "market:underlying"
3) (integer) 1
1) "message"
2) "market:underlying"
3) "{\"type\":\"UNDERLYING\",\"product\":\"NIFTY\",\"price\":21503.45,...}"
1) "message"
2) "market:underlying"
3) "{\"type\":\"UNDERLYING\",\"product\":\"BANKNIFTY\",\"price\":45021.78,...}"
```

**Success!** Feed generator is publishing market data.

**Step 4: Stop everything**

```bash
docker stop feed-generator test-redis
docker rm test-redis
```

---

### 2.7 Adding to Docker Compose

Update `docker-compose.yml`:

```yaml
  feed-generator:
    build:
      context: ./services/feed-generator
      dockerfile: Dockerfile
    container_name: deltastream-feed-generator
    environment:
      - REDIS_URL=redis://redis:6379/0
      - SERVICE_NAME=feed-generator
      - FEED_INTERVAL=1
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped
```

**New fields explained:**

```yaml
depends_on:
  redis:
    condition: service_healthy
```
- **Wait for Redis** to be healthy before starting feed-generator
- Without this: Feed-generator starts, Redis not ready → crash

```yaml
restart: unless-stopped
```
- **Auto-restart policy**:
  - Container crashes → Docker restarts it
  - You run `docker stop` → Docker doesn't restart (intended stop)

**Start entire stack:**

```bash
docker-compose up -d
```

**View logs:**

```bash
docker-compose logs -f feed-generator
```

You should see:
```json
{"event": "feed_generator_started", "products": ["NIFTY", ...], "timestamp": "..."}
{"event": "published_option_chain", "product": "NIFTY", "expiry": "2025-01-25", ...}
{"event": "feed_status", "tick_count": 10, "current_prices": {...}}
```

---

### Part 2 Complete: What You've Built

You now have a **production-ready Feed Generator** that:

✅ Simulates realistic underlying price movements (Geometric Brownian Motion)

✅ Generates option chains with proper expiry dates (weekly/monthly)

✅ Calculates option prices with simplified Black-Scholes (intrinsic + time value)

✅ Computes Greeks (delta, gamma, vega, theta)

✅ Publishes data to Redis pub/sub (underlying ticks + option chains)

✅ Uses structured logging (JSON output for observability)

✅ Runs in Docker with proper configuration (env vars, healthchecks)

✅ Integrates with Docker Compose (multi-service orchestration)

---

### What's Next: Part 3 Preview

In **Part 3: Building the Worker Enricher**, we'll:

1. Set up Celery task queue
2. Subscribe to Redis pub/sub channels
3. Implement PCR calculation (Put-Call Ratio)
4. Implement Max Pain algorithm
5. Add MongoDB persistence
6. Implement cache-aside pattern with Redis
7. Add retry logic and dead-letter queues
8. Handle idempotency (process each message exactly once)

**You'll learn:**
- How Celery task queues work (broker, workers, results)
- Why idempotency matters in distributed systems
- How to implement retries with exponential backoff
- When to use dead-letter queues
- MongoDB indexes for time-series data
- Cache invalidation strategies

---

**Ready to continue?** Let me know when you want Part 3: Building the Worker Enricher Service.

---

