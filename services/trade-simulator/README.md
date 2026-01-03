# Trade Simulator Service

**Production-grade paper trading with realistic order execution**

## Features

### Order Management System (OMS)
- ✅ Market & Limit orders
- ✅ Order lifecycle tracking (PENDING → FILLED/REJECTED)
- ✅ Partial fills support
- ✅ Order cancellation
- ✅ Trade history

### Risk Management System (RMS)
- ✅ Pre-trade margin checks
- ✅ Position limits (max 10)
- ✅ Order value caps (Rs. 5L/order)
- ✅ Daily loss limits (-50k stop)
- ✅ Concentration limits (30% per product)
- ✅ SPAN margin calculation

### Order Book Matching
- ✅ Realistic bid/ask spreads (0.5-2%)
- ✅ 5 levels of market depth
- ✅ Price-time priority matching
- ✅ Slippage simulation
- ✅ Partial fills

### Portfolio Management
- ✅ Real-time P&L tracking
- ✅ Position management
- ✅ Performance metrics (win rate, profit factor)
- ✅ Trade history
- ✅ Margin utilization

## Quick Start

```bash
# Build and start
docker-compose up -d trade-simulator

# Check health
curl http://localhost:8007/health

# Get JWT token first
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r '.token')

# Place market order
curl -X POST http://localhost:8000/api/trade/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY25JAN21500CE",
    "order_type": "MARKET",
    "side": "BUY",
    "quantity": 50
  }'

# Check portfolio
curl http://localhost:8000/api/trade/portfolio \
  -H "Authorization: Bearer $TOKEN"
```

## Architecture

```
Trade Simulator (Port 8007)
├── Order Book Manager
│   └── Maintains bid/ask depth for each symbol
├── Risk Management System (RMS)
│   ├── Pre-trade checks
│   ├── Margin calculation
│   └── Limit enforcement
├── Order Management System (OMS)
│   ├── Order placement
│   ├── Execution engine
│   └── Trade generation
└── Portfolio Manager
    ├── Position tracking
    ├── P&L calculation
    └── Performance metrics
```

## Database Schema

### Collections

**portfolios**: User cash balance, margin, P&L  
**orders**: Order lifecycle and status  
**trades**: Execution records  
**positions**: Open positions with entry prices

## API Endpoints

See [API Documentation](../../docs/api-reference/trade-simulator.md)

## Configuration

Environment variables:
```bash
MONGO_URI=mongodb://mongodb:27017/deltastream
REDIS_URL=redis://redis:6379/0
JWT_SECRET=your-secret-key
PORT=8007
```

## Risk Limits (Configurable)

```python
max_open_positions = 10
max_order_value = 500000  # Rs. 5L
max_portfolio_value = 2000000  # Rs. 20L  
max_loss_per_day = -50000  # -Rs. 50k
max_position_concentration = 0.30  # 30%
```

## Testing

```bash
# Run tests
pytest tests/test_trade_simulator.py -v

# Test order placement
python test_orders.py

# Test risk checks
python test_rms.py
```

## Integration

Works with:
- **Auth Service**: JWT verification
- **Storage Service**: Option price data
- **Socket Gateway**: Real-time position updates
- **Analytics Service**: Strategy suggestions

## Files

```
trade-simulator/
├── app.py              # Main Flask service
├── order_book.py       # Order book & matching
├── rms.py              # Risk management
├── oms.py              # Order management
├── portfolio.py        # Portfolio tracking
├── requirements.txt    # Dependencies
├── Dockerfile          # Container
└── README.md           # This file
```

## Production Considerations

### Performance
- Order book cached in Redis
- Position updates asynchronous
- Batch trade generation

### Scalability
- Horizontal scaling supported
- Stateless design (DB/Redis state)
- Load balancer friendly

### Monitoring
- Prometheus metrics endpoint
- Structured JSON logging
- Health check endpoint

## Example Workflows

### Complete Trade Flow
```bash
# 1. Register & Login
# 2. Check risk metrics
curl http://localhost:8000/api/trade/risk -H "Authorization: Bearer $TOKEN"

# 3. Buy option
curl -X POST http://localhost:8000/api/trade/order \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"symbol":"NIFTY25JAN21500CE","order_type":"MARKET","side":"BUY","quantity":50}'

# 4. Monitor position
curl http://localhost:8000/api/trade/positions -H "Authorization: Bearer $TOKEN"

# 5. Close position
curl -X POST http://localhost:8000/api/trade/order \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"symbol":"NIFTY25JAN21500CE","order_type":"MARKET","side":"SELL","quantity":50}'

# 6. Check P&L
curl http://localhost:8000/api/trade/pnl -H "Authorization: Bearer $TOKEN"
```

## License

Part of DeltaStream Options Trading Platform
