# Socket Gateway Service

## Overview

The Socket Gateway provides real-time WebSocket connections for clients to receive live market data updates. It uses Flask-SocketIO with Redis as a message queue adapter, enabling horizontal scaling across multiple instances.

## Features

- **Room-Based Subscriptions**: Clients can subscribe to specific products or chains
- **Multi-Instance Support**: Redis message_queue enables load balancing
- **Automatic Reconnection**: Socket.IO handles reconnection logic
- **Structured Events**: Clean event-based architecture
- **Cached Data**: Sends latest cached data on subscription

## Architecture

```
Clients (WebSocket)
     ↓
 Socket Gateway (multiple instances)
     ↓
 Redis Pub/Sub (enriched channels)
     ↑
 Worker Enricher
```

## Room Structure

### General Room
- **Room Name**: `general`
- **Auto-join**: All clients automatically join on connection
- **Content**: Summary updates for all products

### Product Rooms
- **Room Name**: `product:{SYMBOL}` (e.g., `product:NIFTY`)
- **Content**: Real-time underlying price updates for specific product

### Chain Rooms
- **Room Name**: `chain:{SYMBOL}` (e.g., `chain:NIFTY`)
- **Content**: Complete option chain updates for specific product

## Client Events

### Outgoing (Server → Client)

#### `connected`
```json
{
  "message": "Connected to DeltaStream socket gateway",
  "client_id": "abc123",
  "rooms": ["general"]
}
```

#### `underlying_update`
```json
{
  "type": "UNDERLYING_ENRICHED",
  "product": "NIFTY",
  "price": 21543.25,
  "timestamp": "2025-01-15T10:30:45.123456",
  "processed_at": "2025-01-15T10:30:46.234567"
}
```

#### `chain_summary`
Broadcast to `general` room (lightweight summary):
```json
{
  "product": "NIFTY",
  "expiry": "2025-01-25",
  "spot_price": 21543.25,
  "pcr_oi": 1.0234,
  "pcr_volume": 0.9876,
  "atm_straddle_price": 253.25,
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

#### `chain_update`
Broadcast to `chain:{SYMBOL}` room (full chain):
```json
{
  "product": "NIFTY",
  "expiry": "2025-01-25",
  "spot_price": 21543.25,
  "pcr_oi": 1.0234,
  "pcr_volume": 0.9876,
  "atm_strike": 21550,
  "atm_straddle_price": 253.25,
  "max_pain_strike": 21500,
  "total_call_oi": 5000000,
  "total_put_oi": 5117000,
  "calls": [...],
  "puts": [...],
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

#### `products`
```json
{
  "products": ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "AAPL", "TSLA", "SPY", "QQQ"]
}
```

#### `subscribed`
```json
{
  "room": "product:NIFTY",
  "message": "Subscribed to product:NIFTY"
}
```

#### `unsubscribed`
```json
{
  "room": "product:NIFTY",
  "message": "Unsubscribed from product:NIFTY"
}
```

#### `error`
```json
{
  "message": "Invalid subscription request"
}
```

### Incoming (Client → Server)

#### `subscribe`
Subscribe to product or chain updates:
```json
{
  "type": "product",  // or "chain"
  "symbol": "NIFTY"
}
```

#### `unsubscribe`
Unsubscribe from updates:
```json
{
  "type": "product",
  "symbol": "NIFTY"
}
```

#### `get_products`
Request list of available products (no payload required).

## Client Examples

### JavaScript (Browser)
```javascript
// Connect
const socket = io('http://localhost:8002');

// Handle connection
socket.on('connected', (data) => {
  console.log('Connected:', data);
  
  // Subscribe to NIFTY updates
  socket.emit('subscribe', {type: 'product', symbol: 'NIFTY'});
  socket.emit('subscribe', {type: 'chain', symbol: 'NIFTY'});
});

// Listen to underlying updates
socket.on('underlying_update', (data) => {
  console.log('Price update:', data.product, data.price);
});

// Listen to chain summaries
socket.on('chain_summary', (data) => {
  console.log('Chain summary:', data.product, 'PCR:', data.pcr_oi);
});

// Listen to full chain updates (only if subscribed to chain room)
socket.on('chain_update', (data) => {
  console.log('Full chain:', data.product, data.calls.length, 'strikes');
});

// Get products list
socket.emit('get_products');
socket.on('products', (data) => {
  console.log('Available products:', data.products);
});
```

### Python (Client)
```python
import socketio

sio = socketio.Client()

@sio.on('connected')
def on_connected(data):
    print('Connected:', data)
    sio.emit('subscribe', {'type': 'product', 'symbol': 'NIFTY'})

@sio.on('underlying_update')
def on_underlying(data):
    print(f"Price update: {data['product']} = {data['price']}")

@sio.on('chain_summary')
def on_chain_summary(data):
    print(f"PCR: {data['pcr_oi']}")

sio.connect('http://localhost:8002')
sio.wait()
```

### Node.js (Client)
```javascript
const io = require('socket.io-client');
const socket = io('http://localhost:8002');

socket.on('connected', (data) => {
  console.log('Connected:', data);
  socket.emit('subscribe', {type: 'product', symbol: 'NIFTY'});
});

socket.on('underlying_update', (data) => {
  console.log(`${data.product}: ${data.price}`);
});
```

## Horizontal Scaling

### Why Redis Message Queue?

When running multiple Socket Gateway instances behind a load balancer:
- Without Redis: Events only reach clients connected to the emitting instance
- With Redis: Events are broadcasted across all instances

### Configuration
```python
socketio = SocketIO(
    app,
    message_queue=redis_url  # Enable multi-instance support
)
```

### Running Multiple Instances
```bash
# Using docker-compose
docker-compose up --scale socket-gateway=3

# With Kubernetes
kubectl scale deployment socket-gateway --replicas=5
```

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "socket-gateway",
  "clients": 42
}
```

### GET /metrics
Metrics for monitoring.

**Response:**
```json
{
  "total_clients": 42,
  "rooms": {
    "general": 42,
    "product:NIFTY": 25,
    "product:BANKNIFTY": 18,
    "chain:NIFTY": 12
  }
}
```

## Environment Variables

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `SERVICE_NAME`: Service identifier (default: `socket-gateway`)
- `PORT`: Server port (default: `8002`)
- `SECRET_KEY`: Flask secret key (default: `dev-secret-key`)

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export REDIS_URL=redis://localhost:6379/0
export PORT=8002

# Run server
python app.py
```

## Testing

### Using wscat (WebSocket CLI)
```bash
npm install -g wscat
wscat -c ws://localhost:8002/socket.io/?EIO=4&transport=websocket
```

### Using curl (HTTP endpoints)
```bash
# Health check
curl http://localhost:8002/health

# Metrics
curl http://localhost:8002/metrics
```

## Performance

### Capacity
- Single instance: ~1000 concurrent connections
- With load balancer: Linear scaling (3 instances = ~3000 connections)
- Message throughput: ~10k messages/second per instance

### Optimization
- Use `gevent` for async I/O (included in requirements)
- Enable Redis connection pooling
- Consider using `msgpack` for binary serialization (smaller payloads)

## Monitoring

### Key Metrics
- `total_clients`: Number of connected clients
- `rooms`: Distribution of clients across rooms
- Message latency: Time from Redis pub/sub to client receive

### Logging
Structured JSON logs include:
- Client connections/disconnections
- Subscription events
- Broadcast events (debug level)
- Errors

## Security Considerations

### Production Checklist
- [ ] Enable HTTPS/WSS
- [ ] Implement authentication (JWT tokens)
- [ ] Rate limiting per client
- [ ] Validate subscription requests
- [ ] Set CORS origins properly
- [ ] Use proper SECRET_KEY

### Authentication (Future)
```python
@socketio.on('connect')
def handle_connect(auth):
    token = auth.get('token')
    if not verify_jwt(token):
        return False  # Reject connection
```

## Troubleshooting

### Clients not receiving updates
1. Check Redis connection: `redis-cli ping`
2. Verify client subscribed to correct room
3. Check enriched data is being published: `redis-cli SUBSCRIBE enriched:underlying`

### High latency
1. Check Redis latency: `redis-cli --latency`
2. Monitor network bandwidth
3. Reduce message payload size (send summaries instead of full chains)

### Connection drops
1. Check firewall/proxy settings
2. Increase Socket.IO ping timeout: `socketio = SocketIO(app, ping_timeout=60)`
3. Enable client-side reconnection logic

## Future Enhancements

- [ ] Add JWT authentication
- [ ] Implement rate limiting
- [ ] Add message compression
- [ ] Support for historical data streaming
- [ ] Add admin room for monitoring
- [ ] Implement private rooms for portfolios
