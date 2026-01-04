**Why cache latest price?**
- API request: "What's latest NIFTY price?"
- Without cache: Query MongoDB (10-50ms)
- With cache: Read Redis (sub-millisecond)

**TTL (5 minutes):**
- If no new ticks for 5 min → cache expires
- Next request hits MongoDB → refreshes cache
- Prevents stale data during market close

**Async OHLC calculation:**

```python
for window_minutes in [1, 5, 15]:
    calculate_ohlc_window.delay(product, window_minutes)
```

**Why `.delay()`?**
- OHLC calculation is slow (query MongoDB for all ticks in window)
- Don't block tick processing
- Dispatch as separate tasks → processed by available workers

**Publishing enriched event:**

```python
redis_client.publish('enriched:underlying', json.dumps(enriched))
```

- **Why publish again?** Socket Gateway subscribes to `enriched:*` channels
- Contains `processed_at` (not in raw tick)
- Decouples workers from Socket Gateway

---

#### Step 3.8: Add Option Chain Processing Task

**Action:** Add the core analytics task for processing option chains. This is the **most complex** task - it calculates PCR and max pain.

Add to `app.py`:

```python
@celery_app.task(base=EnrichmentTask, bind=True)
def process_option_chain(self, chain_data: Dict[str, Any]):
    """
    Process complete option chain.
    
    - Store chain in MongoDB
    - Calculate PCR (Put-Call Ratio)
    - Calculate max pain
    - Identify ATM straddle
    - Calculate total call/put open interest build-up
    - Publish enriched chain
    
    Args:
        chain_data: Option chain dictionary
    """
    try:
        product = chain_data['product']
        expiry = chain_data['expiry']
        spot_price = chain_data['spot_price']
        calls = chain_data['calls']
        puts = chain_data['puts']
        
        # Calculate PCR (Put-Call Ratio)
        total_call_oi = sum(c['open_interest'] for c in calls)
        total_put_oi = sum(p['open_interest'] for p in puts)
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        total_call_volume = sum(c['volume'] for c in calls)
        total_put_volume = sum(p['volume'] for p in puts)
        pcr_volume = total_put_volume / total_call_volume if total_call_volume > 0 else 0
```

**PCR Calculation Explained:**

**PCR_OI (Open Interest based):**
```python
pcr = total_put_oi / total_call_oi
```

Example:
```
Calls:
- Strike 21000: OI = 50,000
- Strike 21050: OI = 40,000
- Strike 21100: OI = 30,000
Total Call OI = 120,000

Puts:
- Strike 21000: OI = 20,000
- Strike 21050: OI = 30,000
- Strike 21100: OI = 40,000
Total Put OI = 90,000

PCR = 90,000 / 120,000 = 0.75
```

**Interpretation:**
- PCR < 0.8: **Bullish** (more calls → expect upside)
- PCR > 1.2: **Bearish** (more puts → expect downside)
- PCR ≈ 1.0: **Neutral**

**Why OI vs Volume?**

- **Open Interest**: Outstanding contracts (reflects positioning)
  - High call OI at 22,000: Many believe NIFTY won't cross 22,000
  - High put OI at 21,000: Many believe NIFTY won't fall below 21,000

- **Volume**: Today's trades (reflects short-term activity)
  - High call volume: Lots of call buying/selling today
  - Less reliable for sentiment (could be day traders)

**We calculate both** but PCR_OI is more reliable.

```python
        # Find ATM strike
        strikes = sorted(chain_data['strikes'])
        atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
        
        # Get ATM straddle
        atm_call = next((c for c in calls if c['strike'] == atm_strike), None)
        atm_put = next((p for p in puts if p['strike'] == atm_strike), None)
        
        atm_straddle_price = 0
        if atm_call and atm_put:
            atm_straddle_price = atm_call['last'] + atm_put['last']
```

**ATM Strike Selection:**

```python
atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
```

**How it works:**

Example: spot_price = 21,537, strikes = [21,000, 21,050, ..., 21,500, 21,550, ...]

```
abs(21,000 - 21,537) = 537
abs(21,050 - 21,537) = 487
abs(21,500 - 21,537) = 37
abs(21,550 - 21,537) = 13  ← Minimum!
```

ATM strike = 21,550 (closest to spot)

**ATM Straddle Price:**

```python
atm_straddle_price = atm_call['last'] + atm_put['last']
```

**What is a straddle?**
- Buy **both** ATM call and ATM put
- Profits if price moves **either direction** (big volatility)

Example:
- ATM call (21,550) = ₹200
- ATM put (21,550) = ₹180
- Straddle cost = ₹380

**Breakeven:**
- Upside: 21,550 + 380 = 21,930 (profit if NIFTY > 21,930)
- Downside: 21,550 - 380 = 21,170 (profit if NIFTY < 21,170)

**Why track straddle price?**
- **Implied volatility indicator**: Expensive straddle = high expected volatility
- **Market sentiment**: Cheap straddle = low volatility expected (calm market)

```python
        # Calculate max pain (strike with maximum total writer profit)
        max_pain_strike = calculate_max_pain(calls, puts, strikes)
```

**Max Pain Algorithm** (already explained in Part 1, but here's the implementation):

```python
def calculate_max_pain(calls: List[Dict], puts: List[Dict], strikes: List[float]) -> float:
    """
    Calculate max pain strike (strike where option writers have maximum profit).
    
    Max pain is the strike price where the total value of outstanding options
    (both calls and puts) is minimized.
    """
    max_pain = strikes[0]
    min_total_value = float('inf')
    
    for strike in strikes:
        # Calculate total value for this strike
        call_value = sum(
            c['open_interest'] * max(0, strike - c['strike'])
            for c in calls
        )
        put_value = sum(
            p['open_interest'] * max(0, p['strike'] - strike)
            for p in puts
        )
        total_value = call_value + put_value
        
        if total_value < min_total_value:
            min_total_value = total_value
            max_pain = strike
    
    return max_pain
```

**Detailed walkthrough:**

Assuming spot = 21,500, strikes = [21,000, 21,500, 22,000]

**Test strike = 21,500 (ATM):**

Calls:
```
Strike 21,000 (ITM): OI = 50k, Intrinsic = max(0, 21500-21000) = 500
                     Value = 50k * 500 = 25,000,000
Strike 21,500 (ATM): OI = 40k, Intrinsic = max(0, 21500-21500) = 0
                     Value = 0
Strike 22,000 (OTM): OI = 30k, Intrinsic = max(0, 21500-22000) = 0
                     Value = 0
Total Call Value = 25,000,000
```

Puts:
```
Strike 21,000 (OTM): OI = 20k, Intrinsic = max(0, 21000-21500) = 0
                     Value = 0
Strike 21,500 (ATM): OI = 30k, Intrinsic = max(0, 21500-21500) = 0
                     Value = 0
Strike 22,000 (ITM): OI = 40k, Intrinsic = max(0, 22000-21500) = 500
                     Value = 40k * 500 = 20,000,000
Total Put Value = 20,000,000
```

**Total = 25M + 20M = 45M** (option buyers' total profit)

**Test strike = 22,000 (above spot):**

Calls:
```
Strike 21,000: OI = 50k, Intrinsic = max(0, 22000-21000) = 1000
               Value = 50,000,000
Strike 21,500: OI = 40k, Intrinsic = max(0, 22000-21500) = 500
               Value = 20,000,000
Strike 22,000: OI = 30k, Intrinsic = 0
               Value = 0
Total = 70,000,000
```

Puts:
```
All OTM, Total = 0
```

**Total = 70M** (higher than 45M → worse for option writers)

**Algorithm finds minimum** → Max pain = strike with **lowest total value** (best for option writers).

```python
        # Build-up analysis (OI changes - simplified for demo)
        call_buildup = sum(c['open_interest'] for c in calls if c['strike'] > spot_price)
        put_buildup = sum(p['open_interest'] for p in puts if p['strike'] < spot_price)
```

**OI Build-up Analysis:**

```python
call_buildup = sum(c['open_interest'] for c in calls if c['strike'] > spot_price)
```

**What is this measuring?**

- **OTM call OI**: Positions expecting upside
- If call_buildup is high:
  - Many sold OTM calls (resistance)
  - OR many bought OTM calls (bullish bets)

**Interpretation** (requires change from previous snapshot, not implemented in demo):
- **Increasing call OI**: New positions opened (need to check call price to determine buy/sell)
- **Decreasing call OI**: Positions closed (profit-taking or stop-loss)

**Production enhancement:**
```python
# Store previous OI
previous_chain = db.option_chains.find_one({
    'product': product,
    'expiry': expiry
}, sort=[('timestamp', DESCENDING)])

if previous_chain:
    for call in calls:
        prev_call = next((c for c in previous_chain['calls'] if c['strike'] == call['strike']), None)
        if prev_call:
            call['oi_change'] = call['open_interest'] - prev_call['open_interest']
```

---

**Storing enriched chain:**

```python
        # Create enriched chain
        enriched_chain = {
            'product': product,
            'expiry': expiry,
            'spot_price': spot_price,
            'pcr_oi': round(pcr, 4),
            'pcr_volume': round(pcr_volume, 4),
            'atm_strike': atm_strike,
            'atm_straddle_price': round(atm_straddle_price, 2),
            'max_pain_strike': max_pain_strike,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'call_buildup_otm': call_buildup,
            'put_buildup_otm': put_buildup,
            'calls': calls,
            'puts': puts,
            'timestamp': chain_data['timestamp'],
            'processed_at': datetime.now().isoformat()
        }
        
        # Store in MongoDB
        db = get_mongo_client()['deltastream']
        db.option_chains.insert_one({
            **enriched_chain,
            'timestamp': datetime.fromisoformat(chain_data['timestamp'])
        })
```

**Schema in MongoDB:**

```json
{
  "_id": ObjectId("..."),
  "product": "NIFTY",
  "expiry": "2025-01-25",
  "spot_price": 21537.45,
  "pcr_oi": 1.0234,
  "pcr_volume": 0.9876,
  "atm_strike": 21550,
  "atm_straddle_price": 380.50,
  "max_pain_strike": 21500,
  "total_call_oi": 1200000,
  "total_put_oi": 1228080,
  "calls": [ { "strike": 21000, "last": 550, "delta": 0.55, "oi": 25000 }, /* ... more strikes ... */ ],
  "puts": [ { "strike": 21000, "last": 20, "delta": -0.45, "oi": 30000 }, /* ... more strikes ... */ ],
  "timestamp": ISODate("2025-01-03T12:30:00Z"),
  "processed_at": "2025-01-03T12:30:00.250Z"
}
```

**Why store full chain?**
- **Historical analysis**: Backtest strategies
- **Reproducibility**: Re-calculate metrics if algo changes
- **Debugging**: Verify calculations

**Trade-off**: Storage (50KB/chain * 100/day = 5MB/day = 1.8GB/year)

```python
        # Update Redis cache
        redis_client = get_redis_client()
        redis_client.setex(
            f"latest:chain:{product}:{expiry}",
            300,
            json.dumps(enriched_chain)
        )
        
        # Cache PCR for analytics
        redis_client.setex(
            f"latest:pcr:{product}:{expiry}",
            300,
            json.dumps({
                'pcr_oi': round(pcr, 4),
                'pcr_volume': round(pcr_volume, 4),
                'timestamp': chain_data['timestamp']
            })
        )
        
        # Publish enriched chain
        redis_client.publish('enriched:option_chain', json.dumps(enriched_chain))
        
        logger.info(
            "processed_option_chain",
            product=product,
            expiry=expiry,
            pcr=round(pcr, 4),
            atm_straddle=round(atm_straddle_price, 2),
            max_pain=max_pain_strike
        )
        
    except Exception as e:
        logger.error("option_chain_processing_error", error=str(e), exc_info=True)
        raise
```

**Multiple cache keys:**

1. **Full chain**: `latest:chain:NIFTY:2025-01-25`
   - Contains all data (50KB)
   - Used by: "Get latest chain" API

2. **PCR only**: `latest:pcr:NIFTY:2025-01-25`
   - Contains just PCR (100 bytes)
   - Used by: "Get PCR" API, analytics dashboard

**Why separate?**
- Don't transfer 50KB when you only need PCR
- Reduces bandwidth, especially for mobile clients

---

### Part 3 Complete (Stopping Point)

This is a natural stopping point for Part 3. We've covered:

✅ Celery task queue fundamentals
✅ Idempotency patterns
✅ Retry logic and dead-letter queues
✅ Lazy client initialization (singleton pattern)
✅ Processing underlying ticks
✅ PCR calculation with detailed explanation
✅ Max Pain algorithm implementation
✅ MongoDB persistence
✅ Redis caching with TTL

### What's Next: Part 3 Continuation

The tutorial will continue with:

4. **OHLC Window Calculation** (aggregating ticks into candlesticks)
5. **Volatility Surface Generation** (3D IV surface across strikes and expiries)
6. **Pub/Sub Subscriber** (consuming Redis channels, dispatching Celery tasks)
7. **Supervisor Configuration** (running subscriber + workers together)
8. **Docker Setup** (Dockerfile, Docker Compose integration)
9. **Testing** (unit tests for PCR/max pain, integration tests)

**Ready to continue?** Let me know when you want the rest of Part 3!

#### Step 3.9: Add OHLC Window Calculation Task

**Action:** Add the task for calculating OHLC (Open, High, Low, Close) windows:

```python
@celery_app.task(base=EnrichmentTask, bind=True)
def calculate_ohlc_window(self, product: str, window_minutes: int):
    """
    Calculate OHLC (Open, High, Low, Close) for a time window.
    
    Args:
        product: Product symbol
        window_minutes: Time window in minutes
    """
    try:
        db = get_mongo_client()['deltastream']
        redis_client = get_redis_client()
        
        # Get ticks from last N minutes
        start_time = datetime.now() - timedelta(minutes=window_minutes)
        ticks = list(db.underlying_ticks.find({
            'product': product,
            'timestamp': {'$gte': start_time}
        }).sort('timestamp', ASCENDING))
        
        if not ticks:
            return
        
        # Calculate OHLC
        prices = [t['price'] for t in ticks]
        ohlc = {
            'product': product,
            'window_minutes': window_minutes,
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'start_time': ticks[0]['timestamp'].isoformat(),
            'end_time': ticks[-1]['timestamp'].isoformat(),
            'num_ticks': len(ticks)
        }
        
        # Cache in Redis
        redis_client.setex(
            f"ohlc:{product}:{window_minutes}m",
            window_minutes * 60,
            json.dumps(ohlc)
        )
        
        logger.info(
            "calculated_ohlc",
            product=product,
            window=f"{window_minutes}m",
            ohlc=ohlc
        )
        
    except Exception as e:
        logger.error("ohlc_calculation_error", error=str(e), exc_info=True)
        raise
```

**What is OHLC?**

OHLC = **Open, High, Low, Close** - the four key prices for a time period.

Example: 1-minute candle for NIFTY (12:30:00 to 12:31:00)
```
Ticks in window:
12:30:05 → 21,500
12:30:15 → 21,505
12:30:30 → 21,510 ← High
12:30:45 → 21,502
12:31:00 → 21,507

OHLC:
Open  = 21,500 (first tick)
High  = 21,510 (max price)
Low   = 21,500 (min price)
Close = 21,507 (last tick)
```

**MongoDB query:**

```python
start_time = datetime.now() - timedelta(minutes=window_minutes)
ticks = list(db.underlying_ticks.find({
    'product': product,
    'timestamp': {'$gte': start_time}
}).sort('timestamp', ASCENDING))
```

**Query breakdown:**

```python
{'timestamp': {'$gte': start_time}}
```
- `$gte`: Greater than or equal to (MongoDB operator)
- Gets all ticks from `start_time` to now

**Why sort by timestamp ASCENDING?**

```python
prices = [t['price'] for t in ticks]
ohlc['open'] = prices[0]   # First tick (earliest)
ohlc['close'] = prices[-1]  # Last tick (latest)
```

- Need chronological order for open/close
- Open = first tick, Close = last tick

**OHLC calculation:**

```python
prices = [t['price'] for t in ticks]
ohlc = {
    'open': prices[0],
    'high': max(prices),
    'low': min(prices),
    'close': prices[-1]
}
```

**Simple list operations:**
- `max(prices)`: Maximum value in list (high)
- `min(prices)`: Minimum value in list (low)
- `prices[0]`: First element (open)
- `prices[-1]`: Last element (close)

**Caching with TTL:**

```python
redis_client.setex(
    f"ohlc:{product}:{window_minutes}m",
    window_minutes * 60,  # TTL in seconds
    json.dumps(ohlc)
)
```

**Why TTL = window_minutes * 60?**

Example: 5-minute window
- TTL = 5 * 60 = 300 seconds
- After 5 minutes, cache expires
- Next request recalculates with fresh data

**Benefit**: OHLC is always fresh (max lag = window size).

---

#### Step 3.10: Add Volatility Surface Generation Task

**Action:** Add the task for generating implied volatility surfaces:

```python
@celery_app.task(base=EnrichmentTask, bind=True)
def calculate_volatility_surface(self, product: str):
    """
    Calculate implied volatility surface for a product.
    
    Creates a grid of IV values across strikes and expiries.
    
    Args:
        product: Product symbol
    """
    try:
        redis_client = get_redis_client()
        db = get_mongo_client()['deltastream']
        
        # Get recent option quotes
        recent_time = datetime.now() - timedelta(minutes=5)
        quotes = list(db.option_quotes.find({
            'product': product,
            'timestamp': {'$gte': recent_time}
        }))
        
        if not quotes:
            return
        
        # Group by expiry
        expiry_groups = {}
        for quote in quotes:
            expiry = quote['expiry']
            if expiry not in expiry_groups:
                expiry_groups[expiry] = []
            expiry_groups[expiry].append(quote)
        
        # Build surface
        surface = {
            'product': product,
            'expiries': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for expiry, expiry_quotes in expiry_groups.items():
            # Sort by strike
            expiry_quotes.sort(key=lambda x: x['strike'])
            
            strikes = [q['strike'] for q in expiry_quotes]
            ivs = [q['iv'] for q in expiry_quotes]
            
            surface['expiries'].append({
                'expiry': expiry,
                'strikes': strikes,
                'ivs': ivs,
                'avg_iv': sum(ivs) / len(ivs) if ivs else 0
            })
        
        # Cache surface
        redis_client.setex(
            f"volatility_surface:{product}",
            300,
            json.dumps(surface)
        )
        
        logger.info(
            "calculated_volatility_surface",
            product=product,
            num_expiries=len(surface['expiries'])
        )
        
    except Exception as e:
        logger.error("volatility_surface_error", error=str(e), exc_info=True)
        raise
```

**What is a Volatility Surface?**

A **3D surface** showing implied volatility (IV) across:
- **X-axis**: Strike prices
- **Y-axis**: Time to expiry
- **Z-axis**: Implied volatility

**Example data:**

```
Expiry: 2025-01-25 (7 days)
Strike  →  21000   21500   22000
IV      →  18%     20%     22%

Expiry: 2025-02-25 (37 days)
Strike  →  21000   21500   22000
IV      →  16%     18%     20%

Expiry: 2025-03-25 (67 days)
Strike  →  21000   21500   22000
IV      →  15%     17%     19%
```

**Observations:**
1. **ATM (21,500) has higher IV** than ITM/OTM (volatility smile)
2. **Longer expiry has lower IV** (more time = more certainty)

**Why track IV surface?**

- **Arbitrage opportunities**: If one strike's IV is abnormally high/low
- **Volatility skew**: Market fear (puts more expensive → high IV on downside)
- **Calendar spreads**: Exploit IV differences across expiries

**Grouping quotes by expiry:**

```python
expiry_groups = {}
for quote in quotes:
    expiry = quote['expiry']
    if expiry not in expiry_groups:
        expiry_groups[expiry] = []
    expiry_groups[expiry].append(quote)
```

**Result:**
```python
{
    '2025-01-25': [quote1, quote2, quote3, ...],
    '2025-02-25': [quote4, quote5, quote6, ...],
    '2025-03-25': [quote7, quote8, quote9, ...]
}
```

**Building surface:**

```python
for expiry, expiry_quotes in expiry_groups.items():
    expiry_quotes.sort(key=lambda x: x['strike'])
    
    strikes = [q['strike'] for q in expiry_quotes]
    ivs = [q['iv'] for q in expiry_quotes]
    
    surface['expiries'].append({
        'expiry': expiry,
        'strikes': strikes,
        'ivs': ivs,
        'avg_iv': sum(ivs) / len(ivs)
    })
```

**Why sort by strike?**
- Visualization needs strikes in order (21,000, 21,500, 22,000, ...)
- Allows plotting IV curve

**Average IV calculation:**
```python
avg_iv = sum(ivs) / len(ivs)
```

Example: ivs = [0.18, 0.20, 0.22]
```
avg_iv = (0.18 + 0.20 + 0.22) / 3 = 0.20 (20%)
```

---

**Navigation:**
← [Previous: Chapter 3-1](chapter03-1.md) | [Next: Chapter 3-3](chapter03-3.md) →

---
