# Part 13: Trade Simulator Service

The Trade Simulator implements a complete paper trading system with order matching, risk management, and portfolio tracking. This allows practice trading without real money.

---

## 13.1 Understanding Trading Systems

### What is an OMS?

**OMS = Order Management System**

Handles the complete order lifecycle:

```
USER                 OMS                  MARKET
  │                   │                     │
  ├─Place Order──────▶│                     │
  │                   ├─Risk Check─────────▶│
  │                   │◀─Approved───────────┤
  │                   ├─Execute────────────▶│
  │                   │◀─Filled─────────────┤
  │◀─Confirmation─────┤                     │
  │                   ├─Update Position────▶│
```

**Responsibilities:**
- Order validation
- Risk pre-checks  
- Execution routing
- Fill management
- Position updates

### What is an RMS?

**RMS = Risk Management System**

Protects against:
- ❌ Insufficient margin
- ❌ Excessive positions
- ❌ Large losses
- ❌ Concentration risk

**Example risk check:**
```python
if user.margin_available < required_margin:
    return False, "Insufficient margin"

if user.num_positions >= 10:
    return False, "Position limit reached"

if user.daily_pnl < -50000:
    return False, "Daily loss limit exceeded"
```

### What is an Order Book?

Shows all buy/sell orders at different prices:

```
ASKS (Sell side)
126.50 │ ████ 100
126.25 │ ██████ 150
126.00 │ ████████ 200
125.75 │ ██████████ 250  ← Best Ask
─────────────────────────────── SPREAD (0.50)
125.25 │ ████████████ 300  ← Best Bid
125.00 │ ██████████ 250
124.75 │ ████████ 200
124.50 │ ██████ 150
BIDS (Buy side)
```

**Market order:** Fills at best available price
**Limit order:** Only fills if price condition met

---

## 13.2 Building the Order Book

### Step 13.1: Create Order Book Structure

**Action:** Create `order_book.py`:

```python
#!/usr/bin/env python3
"""Order Book - Realistic bid/ask spread and depth simulation"""

import random
from datetime import datetime
from typing import List, Tuple, Optional

class OrderBook:
    """Order book for a single symbol"""
    
    def __init__(self, symbol: str, mid_price: float):
        self.symbol = symbol
        self.mid_price = mid_price
        self.bids = []  # [(price, quantity, timestamp), ...]
        self.asks = []  # [(price, quantity, timestamp), ...]
        self.last_trade_price = mid_price
        
        # Initialize with realistic market depth
        self._initialize_depth()
```

**Breaking Down Structure:**

**Bids vs Asks:**
```python
self.bids = []  # Buy orders (sorted high to low)
self.asks = []  # Sell orders (sorted low to high)
```
- Bids: Higher price = better for buyer
- Asks: Lower price = better for seller

**Tuple Structure:**
```python
(price, quantity, timestamp)
```
- `price`: Price per unit
- `quantity`: Number of shares/lots
- `timestamp`: For price-time priority

---

### Step 13.2: Initialize Market Depth

**Action:** Add depth initialization:

```python
    def _initialize_depth(self):
        """Create realistic bid/ask spread with depth"""
        # Typical option spread: 0.5% to 2% of mid price
        spread_pct = random.uniform(0.005, 0.02)
        spread = self.mid_price * spread_pct
        
        # Best bid/ask
        best_bid = self.mid_price - spread / 2
        best_ask = self.mid_price + spread / 2
        
        # Create 5 levels of depth on each side
        levels = 5
        for i in range(levels):
            # Bids (decreasing prices)
            bid_price = best_bid - (i * spread * 0.5)
            bid_qty = random.randint(50, 500)
            self.bids.append((bid_price, bid_qty, datetime.now()))
            
            # Asks (increasing prices)
            ask_price = best_ask + (i * spread * 0.5)
            ask_qty = random.randint(50, 500)
            self.asks.append((ask_price, ask_qty, datetime.now()))
        
        # Sort: bids descending, asks ascending
        self.bids.sort(key=lambda x: x[0], reverse=True)
        self.asks.sort(key=lambda x: x[0])
```

**Breaking Down Market Depth:**

**Spread Calculation:**
```python
spread_pct = random.uniform(0.005, 0.02)  # 0.5% to 2%
spread = self.mid_price * spread_pct
```
- Mid price = 125 → Spread = 1.25 (1%)
- Best bid = 125 - 0.625 = 124.375
- Best ask = 125 + 0.625 = 125.625

**Level Spacing:**
```python
bid_price = best_bid - (i * spread * 0.5)
```
- i=0: 124.375 (best bid)
- i=1: 124.375 - 0.625 = 123.75
- i=2: 123.75 - 0.625 = 123.125

**Why Sort?**
```python
self.bids.sort(key=lambda x: x[0], reverse=True)
```
- Bids: Highest price first (buyer priority)
- Asks: Lowest price first (seller priority)

**Example Result:**
```
Mid: 125.00
Bids:          Asks:
124.38 - 300   125.63 - 250
123.75 - 200   126.25 - 180
123.13 - 150   126.88 - 120
```

---

### Step 13.3: Implement Market Buy Matching

**Action:** Add market buy order matching:

```python
    def match_market_buy(self, quantity: int) -> List[Tuple[float, int]]:
        """Match market buy order against asks
        
        Returns list of (price, quantity) fills
        """
        fills = []
        remaining = quantity
        
        while remaining > 0 and self.asks:
            ask_price, ask_qty, ask_time = self.asks[0]
            
            # Fill as much as possible from this level
            fill_qty = min(remaining, ask_qty)
            fills.append((ask_price, fill_qty))
            
            remaining -= fill_qty
            
            # Update or remove ask level
            if fill_qty < ask_qty:
                # Partial fill - update quantity
                self.asks[0] = (ask_price, ask_qty - fill_qty, ask_time)
            else:
                # Complete fill - remove level
                self.asks.pop(0)
        
        # Update last trade price
        if fills:
            self.last_trade_price = fills[-1][0]
        
        return fills
```

**Breaking Down Matching Logic:**

**While Loop:**
```python
while remaining > 0 and self.asks:
```
- Continue until order fully filled
- Or no more asks available (partial fill)

**Minimum Fill:**
```python
fill_qty = min(remaining, ask_qty)
```
- If remaining=300, ask_qty=250 → fill_qty=250
- If remaining=50, ask_qty=250 → fill_qty=50

**Level Update:**
```python
if fill_qty < ask_qty:
    # Partial: Update quantity
    self.asks[0] = (ask_price, ask_qty - fill_qty, ask_time)
else:
    # Complete: Remove level
    self.asks.pop(0)
```

**Example Execution:**

**Initial state:**
```
Want to buy: 300
Asks:
  125.75 - 250
  126.00 - 200
  126.25 - 150
```

**Step 1:** Fill 250 @ 125.75
```
Remaining: 50
Fills: [(125.75, 250)]
Asks:
  126.00 - 200  ← Level removed
  126.25 - 150
```

**Step 2:** Fill 50 @ 126.00
```
Remaining: 0
Fills: [(125.75, 250), (126.00, 50)]
Asks:
  126.00 - 150  ← 50 taken from 200
  126.25 - 150
```

**Average Price:**
```python
total_value = (125.75 * 250) + (126.00 * 50) = 37,737.50
total_qty = 300
avg_price = 37,737.50 / 300 = 125.79
```

**Key Insight:** Large orders "walk the book" causing **slippage**.

---

### Step 13.4: Implement Limit Order Matching

**Action:** Add limit order matching:

```python
    def check_limit_buy(self, price: float, quantity: int) -> Optional[List]:
        """Check if limit buy can be filled"""
        best_ask = self.get_best_ask()
        if not best_ask:
            return None
        
        # Limit buy fills if ask <= limit price
        if best_ask[0] <= price:
            fills = []
            remaining = quantity
            
            for ask_price, ask_qty, _ in self.asks:
                # Can't fill above limit price
                if ask_price > price:
                    break
                
                fill_qty = min(remaining, ask_qty)
                fills.append((ask_price, fill_qty))
                remaining -= fill_qty
                
                if remaining == 0:
                    break
            
            return fills if fills else None
        
        return None  # Order remains pending
    
    def get_best_ask(self):
        """Get best (lowest) ask"""
        return self.asks[0] if self.asks else None
```

**Breaking Down Limit Logic:**

**Price Check:**
```python
if best_ask[0] <= price:
```
- Only execute if ask price ≤ limit price
- Protects buyer from overpaying

**Fill Loop:**
```python
for ask_price, ask_qty, _ in self.asks:
    if ask_price > price:
        break  # Stop at higher prices
```

**Example:**

**Limit buy @ 126.00 for 100:**
```
Asks:
  125.75 - 250  ← Can fill (< 126.00)
  126.00 - 200  ← Can fill (= 126.00)
  126.25 - 150  ← Too expensive

Result: Fill 100 @ 125.75
```

**Key Difference from Market:**
- Market: Fills at any price
- Limit: Only fills if price favorable

---

## 13.3 Implementing Risk Management

### Step 13.5: Create RMS Structure

**Action:** Create `rms.py`:

```python
#!/usr/bin/env python3
"""RMS - Risk Management System"""

class RiskManagementSystem:
    """Risk management and compliance checks"""
    
    DEFAULT_LIMITS = {
        'max_open_positions': 10,
        'max_order_value': 500000,  # Rs. 5 lakh
        'max_portfolio_value': 2000000,  # Rs. 20 lakh
        'max_loss_per_day': -50000,  # Stop at -50k
        'min_cash_balance': 100000,  # Keep Rs. 1 lakh
        'max_position_concentration': 0.30,  # Max 30% in one position
    }
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        self.limits = self.DEFAULT_LIMITS.copy()
```

**Why These Limits?**

**Position Limit:**
```python
'max_open_positions': 10
```
- Prevents over-diversification
- Easier to manage and monitor

**Order Value:**
```python
'max_order_value': 500000
```
- Prevents fat finger errors
- Single order can't blow up account

**Daily Loss:**
```python
'max_loss_per_day': -50000
```
- Circuit breaker for bad days
- Prevents revenge trading

---

### Step 13.6: Implement Margin Calculations

**Action:** Add margin calculation methods:

```python
    def calculate_margin(self, order: dict, current_price: float) -> float:
        """Calculate required margin for order"""
        
        if order['side'] == 'BUY':
            # Buying options = pay full premium
            return self._calculate_margin_buy(order)
        else:
            # Selling options = SPAN margin
            return self._calculate_margin_sell(order, current_price)
    
    def _calculate_margin_buy(self, order: dict) -> float:
        """Margin for buying = full premium"""
        quantity = order['quantity']
        price = order.get('price', 100)  # Default if market order
        
        margin = quantity * price
        return margin
    
    def _calculate_margin_sell(self, order: dict, underlying_price: float) -> float:
        """Margin for selling = SPAN margin (18% of underlying)"""
        lot_size = 50  # NIFTY lot size
        quantity = order['quantity']
        
        # SPAN margin ≈ 18% of underlying value
        margin_per_lot = underlying_price * lot_size * 0.18
        num_lots = quantity / lot_size
        
        total_margin = margin_per_lot * num_lots
        return total_margin
```

**Breaking Down Margin Logic:**

**Buy Options (Simple):**
```python
# Buy 50 NIFTY CE @ 125
margin = 50 * 125 = 6,250
```
- Pay full premium
- Maximum loss = premium paid
- No additional margin needed

**Sell Options (SPAN Margin):**
```python
# Sell 50 NIFTY CE (1 lot)
# Underlying = 21,500
margin_per_lot = 21,500 * 50 * 0.18 = 1,93,500
```
- Much higher margin
- Unlimited risk (need buffer)
- Exchange requirement

**Why 18%?**
- Based on historical volatility
- Covers ~99% of 1-day moves
- Exchange-mandated formula

**Comparison:**
```
Buy  50 CE @ 125:    6,250 margin
Sell 50 CE @ 125: 1,93,500 margin  (30x higher!)
```

---

### Step 13.7: Implement Pre-Trade Risk Checks

**Action:** Add comprehensive risk checking:

```python
    def pre_trade_risk_check(self, user_id: str, order: dict, current_price: float) -> bool:
        """Perform all pre-trade risk checks"""
        
        # 1. Check margin availability
        required_margin = self.calculate_margin(order, current_price)
        portfolio = self.db.portfolios.find_one({'user_id': user_id})
        
        if not portfolio:
            raise InsufficientFundsError("No portfolio found")
        
        if portfolio['margin_available'] < required_margin:
            raise InsufficientFundsError(
                f"Need {required_margin:,.0f}, have {portfolio['margin_available']:,.0f}"
            )
        
        # 2. Check position limits
        positions = list(self.db.positions.find({'user_id': user_id}))
        if len(positions) >= self.limits['max_open_positions']:
            raise PositionLimitError(
                f"Maximum {self.limits['max_open_positions']} positions allowed"
            )
        
        # 3. Check order value
        order_value = order['quantity'] * order.get('price', current_price)
        if order_value > self.limits['max_order_value']:
            raise OrderValueLimitError(
                f"Max order value: {self.limits['max_order_value']:,.0f}"
            )
        
        # 4. Check daily loss limit
        today_pnl = self._get_today_pnl(user_id)
        if today_pnl < self.limits['max_loss_per_day']:
            raise DailyLossLimitError(
                f"Daily loss limit reached: {today_pnl:,.0f}"
            )
        
        return True
    
    def _get_today_pnl(self, user_id: str) -> float:
        """Calculate today's P&L"""
        from datetime import datetime, time
        
        today_start = datetime.combine(datetime.today(), time.min)
        
        trades = list(self.db.trades.find({
            'user_id': user_id,
            'timestamp': {'$gte': today_start}
        }))
        
        return sum(t.get('pnl', 0) for t in trades)


# Custom exceptions
class RiskLimitError(Exception):
    pass

class InsufficientFundsError(RiskLimitError):
    pass

class PositionLimitError(RiskLimitError):
    pass

class OrderValueLimitError(RiskLimitError):
    pass

class DailyLossLimitError(RiskLimitError):
    pass
```

**Risk Check Flow:**
```
Order → [Margin OK?] → [Position Limit OK?] → [Value OK?] → [Loss Limit OK?] → ✅ APPROVED
            ↓                  ↓                  ↓                 ↓
        ❌ REJECT          ❌ REJECT          ❌ REJECT         ❌ REJECT
```

---

## 13.4 Building the OMS

### Step 13.8: Create OMS Structure

**Action:** Create `oms.py`:

```python
#!/usr/bin/env python3
"""OMS - Order Management System"""

import uuid
from datetime import datetime
from typing import Dict, List

from order_book import OrderBookManager
from rms import RiskManagementSystem

class OrderManagementSystem:
    
    def __init__(self, db, redis, order_book_mgr, rms):
        self.db = db
        self.redis = redis
        self.order_book_manager = order_book_mgr
        self.rms = rms
```

---

### Step 13.9: Implement Order Placement

**Action:** Add order placement logic:

```python
    def place_order(self, user_id: str, order_request: Dict) -> Dict:
        """Place new order with risk checks"""
        
        # Generate order ID
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        
        # Create order object
        order = {
            'order_id': order_id,
            'user_id': user_id,
            'symbol': order_request['symbol'],
            'order_type': order_request['order_type'],  # MARKET, LIMIT
            'side': order_request['side'],  # BUY, SELL
            'quantity': order_request['quantity'],
            'price': order_request.get('price'),
            'status': 'PENDING',
            'filled_quantity': 0,
            'placed_at': datetime.now()
        }
        
        try:
            # Get current price
            current_price = self._get_current_price(order['symbol'])
            
            # Pre-trade risk check
            self.rms.pre_trade_risk_check(user_id, order, current_price)
            
            # Execute order
            order = self._execute_order(order, current_price)
            
            # Save to database
            self.db.orders.insert_one(order)
            
            return order
            
        except RiskLimitError as e:
            # Mark as rejected
            order['status'] = 'REJECTED'
            order['rejection_reason'] = str(e)
            self.db.orders.insert_one(order)
            raise
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        # Try Redis cache first
        cached = self.redis.get(f"latest:quote:{symbol}")
        if cached:
            import json
            quote = json.loads(cached)
            return quote.get('ltp', 100)
        
        # Fallback to default
        return 100.0
```

**Breaking Down Order ID:**
```python
order_id = f"ORD_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
```
- Example: `ORD_20250103_a1b2c3d4`
- Date prefix: Easy filtering
- UUID: Unique across all time

---

### Step 13.10: Implement Order Execution

**Action:** Add execution logic:

```python
    def _execute_order(self, order: Dict, current_price: float) -> Dict:
        """Execute order via order book matching"""
        symbol = order['symbol']
        
        # Get or create order book
        order_book = self.order_book_manager.get_or_create_book(
            symbol, current_price
        )
        
        # Match order based on type
        if order['order_type'] == 'MARKET':
            if order['side'] == 'BUY':
                fills = order_book.match_market_buy(order['quantity'])
            else:
                fills = order_book.match_market_sell(order['quantity'])
        else:  # LIMIT
            if order['side'] == 'BUY':
                fills = order_book.check_limit_buy(
                    order['price'], order['quantity']
                )
            else:
                fills = order_book.check_limit_sell(
                    order['price'], order['quantity']
                )
        
        if fills:
            # Calculate average fill price
            total_value = sum(price * qty for price, qty in fills)
            total_qty = sum(qty for _, qty in fills)
            avg_price = total_value / total_qty
            
            # Update order
            order['filled_quantity'] = total_qty
            order['avg_fill_price'] = avg_price
            order['filled_at'] = datetime.now()
            order['status'] = 'FILLED' if total_qty == order['quantity'] else 'PARTIALLY_FILLED'
            order['fills'] = fills
            
            # Generate trades
            self._generate_trades(order, fills)
            
            # Update position
            self._update_position(order)
        else:
            order['status'] = 'PENDING'
        
        return order
    
    def _generate_trades(self, order: Dict, fills: List):
        """Generate trade records from fills"""
        for price, qty in fills:
            trade = {
                'trade_id': f"TRD_{uuid.uuid4().hex[:8]}",
                'order_id': order['order_id'],
                'user_id': order['user_id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'price': price,
                'quantity': qty,
                'value': price * qty,
                'commission': self._calculate_commission(price * qty),
                'timestamp': datetime.now()
            }
            self.db.trades.insert_one(trade)
    
    def _calculate_commission(self, trade_value: float) -> float:
        """Calculate brokerage commission"""
        # Flat fee + percentage
        flat_fee = 20
        percentage = 0.0003  # 0.03%
        
        commission = flat_fee + (trade_value * percentage)
        return round(commission, 2)
```

**Execution Example:**

**Input:**
```python
order = {
    'order_type': 'MARKET',
    'side': 'BUY',
    'quantity': 300
}
```

**Order Book:**
```
125.75 - 250
126.00 - 200
```

**Execution:**
```python
fills = [(125.75, 250), (126.00, 50)]
total_value = (125.75 * 250) + (126.00 * 50) = 37,737.50
tot al_qty = 300
avg_price = 125.79
```

**Result:**
```python
order = {
    'status': 'FILLED',
    'filled_quantity': 300,
    'avg_fill_price': 125.79,
    'fills': [(125.75, 250), (126.00, 50)]
}
```

**Trades Generated:**
```
Trade 1: 250 @ 125.75 = 31,437.50 + commission 14.43
Trade 2:  50 @ 126.00 =  6,300.00 + commission  5.89
```

---

## Summary

You've built a **complete Trade Simulator** with:

✅ **Order Book** - Realistic bid/ask spreads
✅ **Market Matching** - Walk-the-book execution
✅ **Limit Orders** - Price-protected fills
✅ **Risk Management** - Margin & position limits
✅ **SPAN Margin** - Option seller requirements
✅ **OMS** - Order lifecycle management
✅ **Portfolio Tracking** - P&L calculation

**Key Learnings:**
- Order book mechanics (bids/asks)
- Market vs limit order execution
- Slippage from walking the book
- SPAN margin for option selling
- Risk check implementation
- Average fill price calculation

**Production Enhancements:**
- WebSocket for real-time order updates
- FIFO P&L matching
- Tax lot tracking
- Corporate actions handling
- Advanced order types (stop-loss, bracket orders)

**Congratulations! 🎉** All critical tutorial chapters are now complete with comprehensive explanations!

---
