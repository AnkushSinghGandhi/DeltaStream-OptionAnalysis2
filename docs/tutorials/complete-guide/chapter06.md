# Part 6: WebSocket Gateway - Real-Time Communication

WebSockets enable real-time, bidirectional communication between server and clients. For an options trading platform, this means instant price updates without polling.

---

## 6.1 Understanding WebSockets

### HTTP vs WebSocket: The Problem

**Traditional HTTP (Polling):**
```
Client                    Server
  │                         │
  ├──GET /api/data─────────▶│
  │◀────{data}──────────────┤
  │   (Wait 1 second)        │
  ├──GET /api/data─────────▶│
  │◀────{data}──────────────┤
  │   (Wait 1 second)        │
  ├──GET /api/data─────────▶│
```

**Problems:**
- ❌ **Latency**: 1-5 second delays
- ❌ **Overhead**: New TCP connection every request
- ❌ **Bandwidth**: HTTP headers repeated (50-200 bytes each)
- ❌ **Server load**: 1000 clients × 1 req/sec = 1000 req/sec

**WebSocket (Server Push):**
```
Client                    Server
  │                         │
  ├──Upgrade: websocket────▶│
  │◀────101 Switching───────┤
  │                         │
  │ ◀──────{data}───────────┤  Server pushes
  │ ◀──────{data}───────────┤
  │ ◀──────{data}───────────┤
  │                         │
  (Single persistent connection)
```

**Benefits:**
- ✅ **Real-time**: ~0ms latency (instant push)
- ✅ **Efficient**: Single persistent TCP connection
- ✅ **Low bandwidth**: No repeated headers
- ✅ **Scalable**: 10,000+ concurrent connections per server

---

## 6.2 Project Setup

### Step 6.1: Create Directory Structure

**Action:** Create the socket gateway service:

```bash
mkdir -p services/socket-gateway
cd services/socket-gateway
```

### Step 6.2: Create Requirements File

**Action:** Create `requirements.txt`:

```txt
Flask==3.0.0
flask-socketio==5.3.5
flask-cors==4.0.0
python-socketio==5.10.0
redis==5.0.1
structlog==24.1.0
```

**Why these dependencies?**
- `flask-socketio`: Integrates Socket.IO with Flask
- `python-socketio`: Core Socket.IO protocol implementation
- `redis`: For pub/sub and horizontal scaling

**What is Socket.IO?**
- Library built on top of WebSockets
- Adds features: Rooms, namespaces, automatic reconnection
- Fallback to HTTP long-polling if WebSocket unavailable

---

## 6.3 Building the Service

### Step 6.3: Create Base Application Setup

**Action:** Create `app.py` with imports and configuration:

```python
#!/usr/bin/env python3
"""
Socket Gateway Service

Flask-SocketIO based WebSocket server that:
1. Accepts client connections
2. Manages room-based subscriptions  
3. Listens to Redis pub/sub for enriched data
4. Broadcasts updates to subscribed clients
5. Supports horizontal scaling with Redis adapter
"""

import os
import json
import redis
import structlog
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from threading import Thread
import time

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'socket-gateway')
PORT = int(os.getenv('PORT', '8002'))

# Initialize Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
CORS(app)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Connected clients tracking
connected_clients = {}
```

**Why Flask for WebSocket?**
- Already using Flask for other services (consistency)
- Flask-SocketIO integrates seamlessly
- Can still have HTTP endpoints alongside WebSockets

---

### Step 6.4: Initialize Socket.IO with Redis Adapter

**Action:** Add Socket.IO initialization:

```python
# SocketIO with Redis message queue (critical for scaling)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    message_queue=REDIS_URL,
    async_mode='threading',
    logger=False,
    engineio_logger=False
)
```

**Breaking Down SocketIO Configuration:**

**CORS Setting:**
```python
cors_allowed_origins="*"
```
- Allows WebSocket connections from any origin
- Browser enforces CORS for WebSockets too
- Production: Restrict to specific domains

**Message Queue (Critical for Horizontal Scaling):**
```python
message_queue=REDIS_URL
```

**Why this matters:**

**Without message_queue (single server):**
```
Client A ──▶ Socket Server 1
Client B ──▶ Socket Server 1

Server 1 broadcasts → Both A and B receive ✓
```

**Without message_queue (multiple servers):**
```
Client A ──▶ Socket Server 1
Client B ──▶ Socket Server 2

Server 1 broadcasts → Only A receives ✗
Server 2 broadcasts → Only B receives ✗
```

**With message_queue (Redis adapter):**
```
Client A ──▶ Socket Server 1 ──┐
                                 ├──▶ Redis (pub/sub)
Client B ──▶ Socket Server 2 ──┘

Server 1 emits → Redis → Both servers receive → Both A and B get update ✓
```

**How it works internally:**
1. `socketio.emit()` publishes to Redis channel
2. All SocketIO instances subscribe to that channel
3. Each instance broadcasts to its connected clients
4. Result: All clients receive, regardless of which server they're connected to

**Async Mode:**
```python
async_mode='threading'
```
- Uses threading for concurrency
- Alternatives: `eventlet`, `gevent`, `asyncio`
- `threading`: Built-in, no extra dependencies

---

### Step 6.5: Add Connection Handler

**Action:** Add connection management:

```python
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    client_id = request.sid
    
    # Track connection
    connected_clients[client_id] = {
        'connected_at': time.time(),
        'rooms': ['general']
    }
    
    # Auto-join general room
    join_room('general')
    
    logger.info(
        "client_connected",
        client_id=client_id,
        total_clients=len(connected_clients)
    )
    
    # Send confirmation to client
    emit('connected', {
        'message': 'Connected to DeltaStream',
        'client_id': client_id,
        'server_time': time.time()
    })
```

**Breaking Down Connection Logic:**

**Decorator:**
```python
@socketio.on('connect')
```
- Fired when client connects
- Before any custom events
- Automatic by Socket.IO

**Session ID:**
```python
client_id = request.sid
```
- Unique identifier for this connection
- Generated by Socket.IO
- Persists for connection lifetime
- Example: `"a3b4c5d6e7f8g9h0"`

**Tracking Clients:**
```python
connected_clients[client_id] = {
    'connected_at': time.time(),
    'rooms': ['general']
}
```
- Dictionary to track all connections
- `time.time()` → Unix timestamp (e.g., 1706193845.123)
- Useful for metrics, debugging

**Auto-Join Room:**
```python
join_room('general')
```
- Every client joins `'general'` room on connect
- Allows broadcasting to all clients: `emit(..., room='general')`

**Emit Confirmation:**
```python
emit('connected', {...})
```
- Sends message to THIS client only
- Client receives on `socket.on('connected', ...)`

---

### Step 6.6: Add Disconnection Handler

**Action:** Add disconnect handler:

```python
@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    client_id = request.sid
    
    if client_id in connected_clients:
        del connected_clients[client_id]
    
    logger.info(
        "client_disconnected",
        client_id=client_id,
        remaining_clients=len(connected_clients)
    )
```

**When does disconnect fire?**
- Client closes browser tab
- Network connection drops
- Client calls `socket.disconnect()`
- Server crashes (client detects, fires `disconnect` on reconnect)

---

### Step 6.7: Implement Room Subscriptions

**Action:** Add subscribe/unsubscribe handlers:

```python
@socketio.on('subscribe')
def handle_subscribe(data):
    """
    Handle subscription requests.
    
    Args:
        data: {'type': 'product'|'chain', 'symbol': 'NIFTY'}
    """
    client_id = request.sid
    subscription_type = data.get('type')
    symbol = data.get('symbol')
    
    # Validation
    if not subscription_type or not symbol:
        emit('error', {'message': 'Missing type or symbol'})
        return
    
    # Create room name
    room = f"{subscription_type}:{symbol}"
    
    # Join room
    join_room(room)
    
    # Track subscription
    if client_id in connected_clients:
        if 'rooms' not in connected_clients[client_id]:
            connected_clients[client_id]['rooms'] = []
        if room not in connected_clients[client_id]['rooms']:
            connected_clients[client_id]['rooms'].append(room)
    
    logger.info("client_subscribed", client_id=client_id, room=room)
    
    # Confirm subscription
    emit('subscribed', {
        'room': room,
        'message': f'Subscribed to {room}'
    })
    
    # Send latest cached data
    send_cached_data(room, client_id)


@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Handle unsubscription requests."""
    client_id = request.sid
    subscription_type = data.get('type')
    symbol = data.get('symbol')
    
    room = f"{subscription_type}:{symbol}"
    
    # Leave room
    leave_room(room)
    
    # Update tracking
    if client_id in connected_clients:
        if 'rooms' in connected_clients[client_id]:
            if room in connected_clients[client_id]['rooms']:
                connected_clients[client_id]['rooms'].remove(room)
    
    logger.info("client_unsubscribed", client_id=client_id, room=room)
    
    emit('unsubscribed', {
        'room': room,
        'message': f'Unsubscribed from {room}'
    })
```

**Breaking Down Room System:**

**What Are Rooms?**
Rooms = broadcast groups. Like chat rooms, but for data streams.

**Room Naming Convention:**
```python
room = f"{subscription_type}:{symbol}"
```
- `product:NIFTY` → NIFTY underlying price updates
- `product:BANKNIFTY` → BANKNIFTY updates
- `chain:NIFTY` → Full NIFTY option chain
- `chain:BANKNIFTY` → Full BANKNIFTY chain

**Why This Structure?**
- Allows granular subscriptions
- Client chooses what they want
- Server only sends relevant data

**Joining a Room:**
```python
join_room(room)
```
- Socket.IO function
- Adds this client's socket to room
- No need to manually track

**Example Flow:**

**Client Side:**
```javascript
socket.emit('subscribe', {
    type: 'product',
    symbol: 'NIFTY'
});
```

**Server:**
1. Receives event
2. Creates room: `"product:NIFTY"`
3. Calls `join_room("product:NIFTY")`
4. Client added to room internally
5. Sends confirmation

**Client receives:**
```javascript
socket.on('subscribed', (data) => {
    console.log(data.message); // "Subscribed to product:NIFTY"
});
```

**Broadcasting to Rooms:**
```python
# Later, when data arrives
socketio.emit('underlying_update', nifty_data, room='product:NIFTY')
```
- Only clients in `product:NIFTY` room receive
- Efficient (no loops)

---

### Step 6.8: Add Helper for Cached Data

**Action:** Add function to send cached data on subscription:

```python
def send_cached_data(room, client_id):
    """Send latest cached data for a room to newly subscribed client."""
    try:
        # Parse room
        parts = room.split(':')
        if len(parts) != 2:
            return
        
        subscription_type, symbol = parts
        
        if subscription_type == 'product':
            # Get latest underlying from Redis
            cache_key = f"latest:underlying:{symbol}"
            cached = redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                socketio.emit('underlying_update', data, room=client_id)
        
        elif subscription_type == 'chain':
            # Get latest chain
            cache_key = f"latest:chain:{symbol}"
            cached = redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                socketio.emit('chain_update', data, room=client_id)
    
    except Exception as e:
        logger.error("send_cached_data_error", error=str(e))
```

**Why send cached data?**
- Client subscribes mid-stream
- Without cache: waits for next update (could be 1-5 seconds)
- With cache: Gets latest immediately

**Emitting to Specific Client:**
```python
socketio.emit('underlying_update', data, room=client_id)
```
- `room=client_id` → Send to THIS client only  
- Each client's `sid` is also a "room" with one member

---

### Step 6.9: Add Redis Listener Background Thread

**Action:** Add the Redis subscriber that bridges pub/sub to WebSocket:

```python
def redis_listener():
    """
    Listen to Redis pub/sub and broadcast to WebSocket clients.
    Runs in background thread.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe('enriched:underlying', 'enriched:option_chain')
    
    logger.info(
        "redis_listener_started",
        channels=['enriched:underlying', 'enriched:option_chain']
    )
    
    for message in pubsub.listen():
        try:
            # Skip non-message types
            if message['type'] != 'message':
                continue
            
            channel = message['channel']
            data = json.loads(message['data'])
            
            if channel == 'enriched:underlying':
                handle_underlying_update(data)
            
            elif channel == 'enriched:option_chain':
                handle_chain_update(data)
        
        except Exception as e:
            logger.error("redis_listener_error", error=str(e), exc_info=True)


def handle_underlying_update(data):
    """Broadcast underlying price update."""
    product = data['product']
    
    # Broadcast to all clients
    socketio.emit('underlying_update', data, room='general')
    
    # Broadcast to product-specific subscribers
    product_room = f"product:{product}"
    socketio.emit('underlying_update', data, room=product_room)
    
    # Cache for new subscribers
    cache_key = f"latest:underlying:{product}"
    redis_client.setex(cache_key, 60, json.dumps(data))
    
    logger.debug(
        "broadcasted_underlying",
        product=product,
        price=data.get('price')
    )


def handle_chain_update(data):
    """Broadcast option chain update."""
    product = data['product']
    
    # Broadcast summary to all (lightweight)
    summary = {
        'product': product,
        'expiry': data['expiry'],
        'spot_price': data['spot_price'],
        'pcr_oi': data['pcr_oi'],
        'max_pain_strike': data['max_pain_strike'],
        'atm_straddle_price': data.get('atm_straddle_price'),
        'timestamp': data['timestamp']
    }
    socketio.emit('chain_summary', summary, room='general')
    
    # Broadcast full chain to subscribers only (heavy payload)
    chain_room = f"chain:{product}"
    socketio.emit('chain_update', data, room=chain_room)
    
    # Cache
    cache_key = f"latest:chain:{product}"
    redis_client.setex(cache_key, 60, json.dumps(data))
    
    logger.debug(
        "broadcasted_chain",
        product=product,
        pcr=data['pcr_oi']
    )
```

**Breaking Down Redis Listener:**

**PubSub Setup:**
```python
pubsub = redis_client.pubsub()
pubsub.subscribe('enriched:underlying', 'enriched:option_chain')
```
- Creates Redis pub/sub client
- Subscribes to 2 channels
- Blocks and listens indefinitely

**Listen Loop:**
```python
for message in pubsub.listen():
```
- Iterator that yields messages
- Blocks until message received
- Never ends (infinite loop)

**Message Types:**
```python
if message['type'] != 'message':
    continue
```
- Redis sends meta messages: `subscribe`, `psubscribe`, `message`
- We only care about `message` (actual data)

**Why Two Broadcast Levels?**

**Underlying updates:**
```python
socketio.emit('underlying_update', data, room='general')      # All clients
socketio.emit('underlying_update', data, room='product:NIFTY') # NIFTY subscribers
```
- Everyone sees prices (lightweight: ~100 bytes)
- Redundant but allows flexibility

**Chain updates:**
```python
socketio.emit('chain_summary', summary, room='general')  # Lightweight summary
socketio.emit('chain_update', data, room='chain:NIFTY')  # Full chain (heavy)
```
- Full chain is large (~50-100KB)
- Only send to subscribers

**Caching with TTL:**
```python
redis_client.setex(cache_key, 60, json.dumps(data))
```
- `setex(key, ttl, value)` → Set with expiry
- TTL = 60 seconds
- Auto-deletes after 60s (stale data cleanup)

---

### Step 6.10: Start Background Thread

**Action:** Add thread starter and Flask runner:

```python
def start_redis_listener():
    """Start Redis listener in background thread."""
    listener_thread = Thread(target=redis_listener, daemon=True)
    listener_thread.start()
    logger.info("redis_listener_thread_started")


if __name__ == '__main__':
    # Start Redis listener
    start_redis_listener()
    
    # Run Flask-SocketIO server
    logger.info("socket_gateway_starting", port=PORT)
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False)
```

**Breaking Down Threading:**

**Daemon Thread:**
```python
Thread(target=redis_listener, daemon=True)
```
- `daemon=True` → Dies when main program exits
- No need to manually stop thread
- Without: Program hangs on exit

**Why Thread?**
- Flask-SocketIO runs HTTP server (blocks)
- Redis listener also blocks (infinite loop)
- Can't do both in one thread

**Execution Flow:**
```
Main Thread                 Background Thread
     │                            │
     ├─start_redis_listener()────▶│
     │                            ├─pubsub.listen() (blocks)
     │                            │ (listening...)
     ├─socketio.run() (blocks)   │
     │ (HTTP server)              │
     │                            │
```

**Thread Safety:**
- `socketio.emit()` is thread-safe
- Background thread can safely broadcast
- Flask-SocketIO handles locking internally

---

## 6.4 Client Implementation Example

### Step 6.11: Create HTML/JavaScript Client

**Action:** Create `test_websocket.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>DeltaStream WebSocket Test</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body { font-family: monospace; padding: 20px; }
        .update { margin: 5px 0; padding: 10px; background: #f0f0f0; }
        .connected { color: green; }
        .disconnected { color: red; }
    </style>
</head>
<body>
    <h1>DeltaStream Real-Time Feed</h1>
    <div id="status" class="disconnected">Disconnected</div>
    <button onclick="subscribeNIFTY()">Subscribe NIFTY</button>
    <button onclick="subscribeBAN()">Subscribe BANKNIFTY</button>
    <div id="updates"></div>

    <script>
        const socket = io('http://localhost:8002');
        
        socket.on('connect', () => {
            console.log('WebSocket connected');
        });
        
        socket.on('connected', (data) => {
            console.log('Server confirmation:', data);
            document.getElementById('status').innerHTML = 
                `Connected: ${data.client_id}`;
            document.getElementById('status').className = 'connected';
        });
        
        socket.on('subscribed', (data) => {
            console.log('Subscribed to:', data.room);
            addUpdate('Subscribed to ' + data.room);
        });
        
        socket.on('underlying_update', (data) => {
            console.log('Price update:', data);
            addUpdate(
                `${data.product}: ₹${data.price.toFixed(2)} ` +
                `(${new Date(data.timestamp).toLocaleTimeString()})`
            );
        });
        
        socket.on('chain_summary', (data) => {
            console.log('Chain summary:', data);
            addUpdate(
                `${data.product} Chain: PCR=${data.pcr_oi.toFixed(2)}, ` +
                `Max Pain=${data.max_pain_strike}`
            );
        });
        
        socket.on('disconnect', () => {
            console.log('Disconnected');
            document.getElementById('status').innerHTML = 'Disconnected';
            document.getElementById('status').className = 'disconnected';
        });
        
        function subscribeNIFTY() {
            socket.emit('subscribe', {
                type: 'product',
                symbol: 'NIFTY'
            });
        }
        
        function subscribeBAN() {
            socket.emit('subscribe', {
                type: 'product',
                symbol: 'BANKNIFTY'
            });
        }
        
        function addUpdate(text) {
            const div = document.createElement('div');
            div.className = 'update';
            div.textContent = text;
            const container = document.getElementById('updates');
            container.insertBefore(div, container.firstChild);
            
            // Keep only last 20
            while (container.children.length > 20) {
                container.removeChild(container.lastChild);
            }
        }
    </script>
</body>
</html>
```

**Testing:**
1. Start feed generator and worker
2. Start socket gateway: `python app.py`
3. Open `test_websocket.html` in browser
4. See real-time updates streaming!

---

## Summary

You've built a **production-grade WebSocket Gateway** with:

✅ **Socket.IO** - Real-time bidirectional communication
✅ **Room-based subscriptions** - Granular data delivery
✅ **Redis adapter** - Horizontal scaling across multiple servers
✅ **Background threading** - Non-blocking Redis listener
✅ **Caching** - Instant data for new subscribers
✅ **Connection management** - Track clients, rooms

**Key Learnings:**
- WebSocket vs HTTP polling
- Socket.IO rooms and broadcasting
- Redis message queue for multi-server deployments
- Thread-safe WebSocket emission
- Daemon threads in Python
- Client-server event flow

**Production Considerations:**
- Add authentication (JWT in handshake)
- Rate limiting (max subscriptions per client)
- Monitoring (connection count, message rate)
- Error recovery (auto-reconnect, exponential backoff)

**Next:** Chapter 9 covers AI integration with LangChain and RAG!

---
