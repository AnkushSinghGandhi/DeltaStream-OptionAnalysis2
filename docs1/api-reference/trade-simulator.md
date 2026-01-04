# Trade Simulator API

> **Paper trading with realistic order book matching and risk management**

**Base URL**: `http://localhost:8000/api/trade`  
**Port**: 8007 (accessed via API Gateway)

---

## 🔐 Authentication

All endpoints require JWT authentication:

```http
Authorization: Bearer <token>
```

---

## 📚 Endpoints Overview

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **Orders** | `/order` | POST | Place new order |
| | `/orders` | GET | Get order history |
| | `/order/{id}` | DELETE | Cancel order |
| **Portfolio** | `/portfolio` | GET | Portfolio summary |
| | `/positions` | GET | Open positions |
| | `/pnl` | GET | P&L summary |
| | `/trades` | GET | Trade history |
| | `/performance` | GET | Performance metrics |
| **Risk** | `/risk` | GET | Risk metrics |
| **Market** | `/orderbook/{symbol}` | GET | Order book depth |

---

## 📤 Order Management

### 1. Place Order

**Endpoint**: `POST /api/trade/order`

**Request Body**:
```json
{
  "symbol": "NIFTY25JAN21500CE",
  "product": "NIFTY",
  "strike": 21500,
  "expiry": "2025-01-25",
  "option_type": "CE",
  "order_type": "LIMIT",
  "side": "BUY",
  "quantity": 50,
  "price": 125.50
}
```

**Fields**:
- `symbol`: Option symbol (required)
- `product`: NIFTY, BANKNIFTY, FINNIFTY
- `order_type`: MARKET or LIMIT
- `side`: BUY or SELL
- `quantity`: Number of contracts
- `price`: Limit price (required for LIMIT orders)

**Response** (201 Created):
```json
{
  "order_id": "ORD_20250103_A1B2C3D4",
  "status": "FILLED",
  "filled_quantity": 50,
  "avg_fill_price": 125.30,
  "message": "Order filled"
}
```

**Statuses**:
- `PENDING`: Limit order waiting for price
- `FILLED`: Order completely filled
- `PARTIALLY_FILLED`: Partial execution
- `REJECTED`: Failed risk checks
- `CANCELLED`: User cancelled

**Errors**:
```json
{
  "error": "Insufficient margin. Required: 62750.00, Available: 50000.00",
  "type": "risk_limit"
}
```

**Risk Rejection Reasons**:
- Insufficient margin
- Position limit exceeded (max 10)
- Order value > Rs. 5 lakh
- Daily loss > Rs. 50k
- Concentration > 30%

**Example**:
```bash
# Market buy
curl -X POST http://localhost:8000/api/trade/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY25JAN21500CE",
    "order_type": "MARKET",
    "side": "BUY",
    "quantity": 50
  }'

# Limit sell
curl -X POST http://localhost:8000/api/trade/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY25JAN21500CE",
    "order_type": "LIMIT",
    "side": "SELL",
    "quantity": 50,
    "price": 130.00
  }'
```

---

### 2. Get Orders

**Endpoint**: `GET /api/trade/orders?status=FILLED&limit=20`

**Query Parameters**:
- `status`: Filter by status (optional)
- `limit`: Number of orders (default: 50)

**Response**:
```json
{
  "orders": [
    {
      "order_id": "ORD_20250103_A1B2C3D4",
      "symbol": "NIFTY25JAN21500CE",
      "order_type": "LIMIT",
      "side": "BUY",
      "quantity": 50,
      "price": 125.50,
      "status": "FILLED",
      "filled_quantity": 50,
      "avg_fill_price": 125.30,
      "placed_at": "2025-01-03T10:30:00Z",
      "filled_at": "2025-01-03T10:30:02Z"
    }
  ]
}
```

---

### 3. Cancel Order

**Endpoint**: `DELETE /api/trade/order/{order_id}`

**Response**:
```json
{
  "message": "Order cancelled",
  "order_id": "ORD_20250103_A1B2C3D4"
}
```

**Errors**:
- `400`: Cannot cancel (already filled/cancelled)
- `404`: Order not found

---

## 💼 Portfolio Management

### 4. Get Portfolio

**Endpoint**: `GET /api/trade/portfolio`

**Response**:
```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "cash_balance": 950000.00,
  "margin_used": 150000.00,
  "margin_available": 800000.00,
  "total_pnl": 25000.00,
  "realized_pnl": 15000.00,
  "unrealized_pnl": 10000.00,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-03T10:30:00Z"
}
```

---

### 5. Get Positions

**Endpoint**: `GET /api/trade/positions`

**Response**:
```json
{
  "positions": [
    {
      "symbol": "NIFTY25JAN21500CE",
      "product": "NIFTY",
      "strike": 21500,
      "expiry": "2025-01-25",
      "option_type": "CE",
      "quantity": 50,
      "avg_entry_price": 125.30,
      "current_price": 130.50,
      "unrealized_pnl": 260.00,
      "margin_required": 62650.00,
      "opened_at": "2025-01-03T10:30:00Z"
    }
  ],
  "count": 1
}
```

**P&L Calculation**:
```python
unrealized_pnl = (current_price - entry_price) * quantity
# For short positions (negative qty), sign is reversed
```

---

### 6. Get P&L Summary

**Endpoint**: `GET /api/trade/pnl?period=today`

**Query Parameters**:
- `period`: today, week, month, year, all (default: all)

**Response**:
```json
{
  "period": "today",
  "realized_pnl": 5000.00,
  "unrealized_pnl": 10000.00,
  "total_pnl": 15000.00,
  "returns_pct": 1.5,
  "initial_capital": 1000000.00,
  "current_value": 1015000.00
}
```

---

### 7. Get Trade History

**Endpoint**: `GET /api/trade/trades?limit=50`

**Response**:
```json
{
  "trades": [
    {
      "trade_id": "TRD_20250103_X1Y2Z3W4",
      "order_id": "ORD_20250103_A1B2C3D4",
      "symbol": "NIFTY25JAN21500CE",
      "side": "BUY",
      "quantity": 50,
      "price": 125.30,
      "value": 6265.00,
      "commission": 20.00,
      "net_value": 6285.00,
      "executed_at": "2025-01-03T10:30:02Z"
    }
  ],
  "count": 1
}
```

---

### 8. Get Performance Metrics

**Endpoint**: `GET /api/trade/performance`

**Response**:
```json
{
  "total_trades": 10,
  "closed_trades": 5,
  "win_rate": 60.0,
  "avg_profit": 3000.00,
  "avg_loss": 1500.00,
  "profit_factor": 2.0,
  "total_profit": 15000.00,
  "total_loss": 7500.00
}
```

**Metrics Explained**:
- `win_rate`: % of profitable trades
- `avg_profit`: Average profit per winning trade
- `avg_loss`: Average loss per losing trade
- `profit_factor`: Total profit / Total loss

---

## 🛡️ Risk Management

### 9. Get Risk Metrics

**Endpoint**: `GET /api/trade/risk`

**Response**:
```json
{
  "margin_used": 150000.00,
  "margin_available": 850000.00,
  "margin_utilization": 0.15,
  "open_positions": 3,
  "max_positions": 10,
  "total_pnl": 25000.00,
  "daily_loss_limit": -50000.00,
  "exposure_by_product": {
    "NIFTY": 120000.00,
    "BANKNIFTY": 30000.00
  },
  "max_concentration": 0.12,
  "concentration_limit": 0.30
}
```

**Risk Limits** (Default):
```python
{
    'max_open_positions': 10,
    'max_order_value': 500000,  # Rs. 5L per order
    'max_portfolio_value': 2000000,  # Rs. 20L total
    'max_loss_per_day': -50000,  # Stop at -50k
    'min_cash_balance': 100000,  # Keep Rs. 1L
    'max_position_concentration': 0.30,  # 30% max
    'margin_multiplier_buy': 1.0,  # 100% for buying
    'margin_multiplier_sell': 5.0,  # 500% for selling (SPAN)
}
```

---

## 📊 Market Data

### 10. Get Order Book Depth

**Endpoint**: `GET /api/trade/orderbook/{symbol}`

**Response**:
```json
{
  "symbol": "NIFTY25JAN21500CE",
  "mid_price": 125.50,
  "last_trade": 125.30,
  "spread": 0.50,
  "bids": [
    [125.25, 200],
    [125.00, 150],
    [124.75, 100]
  ],
  "asks": [
    [125.75, 250],
    [126.00, 180],
    [126.25, 120]
  ]
}
```

**Format**: `[price, quantity]`

---

## 🔄 Order Execution Flow

### Market Order
```
1. Place market buy order
2. RMS checks (margin, limits)
3. Match against best asks
4. Fill immediately
5. Generate trades
6. Update position
7. Update portfolio
```

### Limit Order
```
1. Place limit buy @ 125.00
2. RMS checks
3. Check if best ask <= 125.00
   - Yes: Fill immediately
   - No: Mark as PENDING
4. Order sits in pending state
5. When market moves, re-check
6. Fill when condition met
```

### Realistic Matching
- **Bid/Ask Spread**: 0.5-2% of mid price
- **Market Depth**: 5 levels each side
- **Slippage**: Large orders walk the book
- **Partial Fills**: Supported

---

## 💡 Common Workflows

### 1. Buy Option
```bash
# Get portfolio
curl http://localhost:8000/api/trade/portfolio \
  -H "Authorization: Bearer $TOKEN"

# Check risk
curl http://localhost:8000/api/trade/risk \
  -H "Authorization: Bearer $TOKEN"

# Place order
curl -X POST http://localhost:8000/api/trade/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @order.json

# Check position
curl http://localhost:8000/api/trade/positions \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Close Position
```bash
# Sell existing position
curl -X POST http://localhost:8000/api/trade/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY25JAN21500CE",
    "order_type": "MARKET",
    "side": "SELL",
    "quantity": 50
  }'

# Check P&L
curl http://localhost:8000/api/trade/pnl?period=today \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🧪 Testing

See [examples/trade-simulator-examples.sh](../../examples/trade-simulator-examples.sh) for complete test suite.

---

## 📚 Related Docs

- [Tutorial Chapter 13](../tutorials/complete-guide/chapter13.md) - Build this service
- [RMS Documentation](../architecture/risk-management.md) - Risk management details
- [Order Book Algorithm](../architecture/order-matching.md) - Matching engine
