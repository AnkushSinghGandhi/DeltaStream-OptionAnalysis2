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

### 2.2 Feed Generator Architecture: Provider Pattern

Our feed generator supports **two data sources** through a clean provider pattern:

1. **Synthetic Provider** (Demo/Testing)
   - Generates simulated market data
   - Uses simplified Black-Scholes for option pricing
   - Available 24/7 (no market hours restriction)
   - Perfect for development and testing

2. **Global Datafeeds Provider** (Production)
   - Connects to real NSE/BSE market data via WebSocket
   - Provides actual option chains with real Greeks
   - Available during market hours (9:15 AM - 3:30 PM IST)
   - Requires API subscription

**Switching between providers:**
```bash
# Use synthetic feed (default)
FEED_PROVIDER=synthetic

# Use real market data
FEED_PROVIDER=globaldatafeeds
GDF_API_KEY=your_api_key
```

**Architecture:**
```
app.py (Entry Point)
  ↓
Provider Factory (reads FEED_PROVIDER env var)
  ↓
┌──────────────────────┬────────────────────────────┐
│ SyntheticFeedProvider│ GlobalDatafeedsProvider   │
├──────────────────────┼────────────────────────────┤
│ - Simulated data     │ - Real market data (gfdlws)│
│ - Always available   │ - Market hours only        │
│ - Free               │ - Requires API key         │
└──────────────────────┴────────────────────────────┘
  ↓
Redis Pub/Sub (market:underlying, market:option_chain)
  ↓
Worker Enricher Service
```

Both providers publish to the **same Redis channels**, making them **drop-in replacements** for each other.

---


---

**Navigation:**
← [Previous: Chapter 1-3](chapter01-3.md) | [Next: Chapter 2-2](chapter02-2.md) →

---
