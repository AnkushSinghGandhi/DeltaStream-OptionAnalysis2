# WebSocket API

> **Real-time data streaming via Socket.IO**

**URL**: `ws://localhost:8002`  
**Protocol**: Socket.IO

## Connection

```javascript
const io = require('socket.io-client');
const socket = io('http://localhost:8002');

socket.on('connect', () => {
  console.log('Connected:', socket.id);
});
```

## Events (Client → Server)

### subscribe
Subscribe to data streams

**Payload**:
```json
{
  "type": "product",  // or "chain"
  "symbol": "NIFTY"
}
```

### unsubscribe
Unsubscribe from stream

**Payload**:
```json
{
  "type": "product",
  "symbol": "NIFTY"
}
```

### get_products
Request products list

## Events (Server → Client)

### connected
Connection confirmation

**Payload**:
```json
{
  "message": "Connected to Socket Gateway",
  "client_id": "abc123"
}
```

### underlying_update
Real-time price updates

**Payload**:
```json
{
  "product": "NIFTY",
  "price": 21543.25,
  "timestamp": "2025-01-03T10:30:00Z"
}
```

### chain_summary
Option chain summary

**Payload**:
```json
{
  "product": "NIFTY",
  "expiry": "2025-01-25",
  "spot_price": 21543.25,
  "pcr_oi": 1.15,
  "max_pain_strike": 21500
}
```

### chain_update
Full chain with all strikes

## Rooms

- `general` - Auto-joined, system messages
- `product:{symbol}` - Underlying price updates
- `chain:{symbol}` - Option chain updates

## Related
- [Examples](../../examples/) - WebSocket client examples
- [Tutorial Chapter 6](../tutorials/complete-guide/chapter06.md)
