## Part 6: Building the WebSocket Gateway

### Learning Objectives

By the end of Part 6, you will understand:

1. **WebSocket communication** - Real-time bidirectional data streaming
2. **Flask-SocketIO** - WebSocket server implementation
3. **Room-based subscriptions** - Client-specific data delivery
4. **Redis message queue** - Horizontal scaling for WebSocket servers
5. **Connection management** - Handling connects, disconnects, subscriptions
6. **Pub/sub integration** - Consuming Redis channels, broadcasting to clients

---

### 6.1 Understanding WebSockets

#### HTTP vs WebSocket

**Traditional HTTP (Request-Response):**
```
Client                    Server
  │                         │
  ├──GET /api/data─────────▶│
  │◀────{data}──────────────┤
  │                         │
  ├──GET /api/data─────────▶│  (Polling every 1s)
  │◀────{data}──────────────┤
  │                         │
  ├──GET /api/data─────────▶│
  │◀────{data}──────────────┤
```

**Problems:**
- **Latency**: Client must poll (1-5s delay)
- **Overhead**: New HTTP connection every request
- **Bandwidth**: Headers repeated (50-200 bytes per request)
- **Server load**: 1000 clients × 1 req/sec = 1000 req/sec

**WebSocket (Persistent Connection):**
```
Client                    Server
  │                         │
  ├──WebSocket handshake───▶│
  │◀────Connection open─────┤
  │ ←──────{data}───────────┤  (Server pushes)
  │ ←──────{data}───────────┤
  │ ←──────{data}───────────┤
  │                         │
  (Connection stays open)
```

**Benefits:**
- **Real-time**: Server pushes instantly (0ms delay)
- **Efficient**: Single persistent connection
- **Low bandwidth**: No repeated headers
- **Scalable**: 10,000+ concurrent connections per server

---

### 6.2 Building the Socket Gateway

#### Dependencies

`requirements.txt`:
```txt
Flask==3.0.0
flask-socketio==5.3.5
flask-cors==4.0.0
python-socketio==5.10.0
redis==5.0.1
structlog==23.2.0
```

**New dependencies:**
- `flask-socketio`: WebSocket integration for Flask
- `python-socketio`: SocketIO protocol implementation

---

#### Part 6.2.1: Setup and Configuration

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

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'socket-gateway')
PORT = int(os.getenv('PORT', '8002'))

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# SocketIO with Redis message queue
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    message_queue=REDIS_URL,  # Critical for horizontal scaling
    async_mode='threading',
    logger=False,
    engineio_logger=False
)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Connected clients tracking
connected_clients = {}
```

**Flask-SocketIO initialization:**

```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    message_queue=REDIS_URL,
    async_mode='threading'
)
```

**Key parameters:**

- `cors_allowed_origins="*"`: Allow WebSocket from any origin (browser security)
- `message_queue=REDIS_URL`: **Critical for horizontal scaling**
- `async_mode='threading'`: Use threads (alternative: eventlet, gevent)

**Why `message_queue` is critical:**

**Without message_queue** (single instance):
```
Client A ──▶ Socket Server 1
             (has connection)

Client B ──▶ Socket Server 1
             (has connection)

Redis pub: "NIFTY price update"
Server 1 receives → broadcasts to A and B ✓
```

**With multiple instances (no message_queue):**
```
Client A ──▶ Socket Server 1
Client B ──▶ Socket Server 2

Redis pub: "NIFTY price update"
Server 1 receives → broadcasts to A ✓
Server 2 receives → broadcasts to B ✓

BUT: If only Server 1 subscribes to Redis, B never gets updates! ✗
```

**With `message_queue` (Redis adapter):**
```
Client A ──▶ Socket Server 1 ──┐
                                ├──▶ Redis (message queue)
Client B ──▶ Socket Server 2 ──┘

Redis pub: "NIFTY price update"
→ Redis message queue
→ Both Server 1 and Server 2 receive
→ A and B both get updates ✓
```

**How it works:**
- SocketIO uses Redis pub/sub internally
- `socketio.emit()` publishes to Redis
- All SocketIO instances subscribed to Redis receive
- Each broadcasts to its connected clients

---

#### Part 6.2.2: Connection Management

```python
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    client_id = request.sid
    connected_clients[client_id] = {
        'connected_at': time.time(),
        'rooms': ['general']
    }
    
    join_room('general')
    
    logger.info(
        "client_connected",
        client_id=client_id,
        total_clients=len(connected_clients)
    )
    
    emit('connected', {
        'message': 'Connected to DeltaStream socket gateway',
        'client_id': client_id,
        'rooms': ['general']
    })


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

**Connection lifecycle:**

1. **Client connects**:
   ```javascript
   const socket = io('http://localhost:8002');
   ```

2. **Server receives `connect` event**:
   ```python
   @socketio.on('connect')
   def handle_connect():
       client_id = request.sid  # Unique session ID
   ```

3. **Server auto-joins `general` room**:
   ```python
   join_room('general')
   ```

4. **Server sends confirmation**:
   ```python
   emit('connected', {'message': '...', 'client_id': client_id})
   ```

5. **Client receives**:
   ```javascript
   socket.on('connected', (data) => {
       console.log(data.message);  // "Connected to..."
   });
   ```

**What is `request.sid`?**
- Unique session ID for each connected client
- Generated by SocketIO
- Used to track connections

---

#### Part 6.2.3: Room-Based Subscriptions

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
    
    if not subscription_type or not symbol:
        emit('error', {'message': 'Invalid subscription request'})
        return
    
    room = f"{subscription_type}:{symbol}"
    join_room(room)
    
    # Update client tracking
    if client_id in connected_clients:
        if 'rooms' not in connected_clients[client_id]:
            connected_clients[client_id]['rooms'] = []
        if room not in connected_clients[client_id]['rooms']:
            connected_clients[client_id]['rooms'].append(room)
    
    logger.info("client_subscribed", client_id=client_id, room=room)
    
    emit('subscribed', {
        'room': room,
        'message': f'Subscribed to {room}'
    })
    
    # Send latest cached data
    send_cached_data(room)


@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Handle unsubscription requests."""
    client_id = request.sid
    subscription_type = data.get('type')
    symbol = data.get('symbol')
    
    room = f"{subscription_type}:{symbol}"
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

**Room system explained:**

**What are rooms?**
Rooms = broadcast groups. Clients join rooms to receive specific updates.

**Room structure:**
```
'general'              → All clients (global updates)
'product:NIFTY'        → Clients interested in NIFTY underlying
'product:BANKNIFTY'    → Clients interested in BANKNIFTY
'chain:NIFTY'          → Clients want full option chains for NIFTY
```

**Example flow:**

```javascript
// Client A joins NIFTY room
socket.emit('subscribe', {type: 'product', symbol: 'NIFTY'});

// Client B joins BANKNIFTY room
socket.emit('subscribe', {type: 'product', symbol: 'BANKNIFTY'});

// Server broadcasts NIFTY update
socketio.emit('underlying_update', nifty_data, room='product:NIFTY');
// Only Client A receives ✓

// Server broadcasts BANKNIFTY update
socketio.emit('underlying_update', banknifty_data, room='product:BANKNIFTY');
// Only Client B receives ✓
```

**Why use rooms instead of individual targeting?**

**Alternative** (track subscriptions manually):
```python
subscriptions = {
    'client_123': ['NIFTY', 'BANKNIFTY'],
    'client_456': ['NIFTY']
}

# Broadcast to all NIFTY subscribers
for client_id, symbols in subscriptions.items():
    if 'NIFTY' in symbols:
        socketio.emit('update', data, room=client_id)  # Individual send
```

**Problems:**
- Loop through all clients (slow)
- Complex tracking logic
- Not scalable

**With rooms:**
```python
socketio.emit('underlying_update', data, room='product:NIFTY')
```
- SocketIO handles routing (optimized C code)
- Single broadcast
- Scalable

---

#### Part 6.2.4: Redis Listener Thread

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
            if message['type'] != 'message':
                continue
            
            channel = message['channel']
            data = json.loads(message['data'])
            
            if channel == 'enriched:underlying':
                product = data['product']
                
                # Broadcast to general room
                socketio.emit('underlying_update', data, room='general')
                
                # Broadcast to product-specific room
                product_room = f"product:{product}"
                socketio.emit('underlying_update', data, room=product_room)
                
                logger.debug(
                    "broadcasted_underlying",
                    product=product,
                    price=data.get('price')
                )
            
            elif channel == 'enriched:option_chain':
                product = data['product']
                
                # Broadcast summary to general
                summary = {
                    'product': product,
                    'expiry': data['expiry'],
                    'spot_price': data['spot_price'],
                    'pcr_oi': data['pcr_oi'],
                    'atm_straddle_price': data['atm_straddle_price'],
                    'timestamp': data['timestamp']
                }
                socketio.emit('chain_summary', summary, room='general')
                
                # Broadcast full chain to subscribers
                chain_room = f"chain:{product}"
                socketio.emit('chain_update', data, room=chain_room)
                
                logger.debug(
                    "broadcasted_chain",
                    product=product,
                    pcr=data['pcr_oi']
                )
        
        except Exception as e:
            logger.error("redis_listener_error", error=str(e))
```

**Data flow:**

```
Worker Enricher                Redis                Socket Gateway               Clients
      │                          │                        │                         │
      ├─publish enriched────────▶│                        │                         │
      │                          ├─notify subscribers────▶│                         │
      │                          │                        ├─emit to rooms──────────▶│
      │                          │                        │                         │
```

**Why run in background thread?**

```python
listener_thread = Thread(target=redis_listener, daemon=True)
listener_thread.start()
```

Flask-SocketIO runs HTTP server. Redis listener blocks indefinitely.
- **Main thread**: HTTP/WebSocket server
- **Background thread**: Redis subscriber

**Thread-safe broadcasting:**

```python
socketio.emit('underlying_update', data, room='product:NIFTY')
```

Flask-SocketIO is thread-safe. Background thread can safely call `socketio.emit()`.

---

### 6.3 Client Example (JavaScript)

```html
<!DOCTYPE html>
<html>
<head>
    <title>DeltaStream Client</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
    <h1>DeltaStream Real-Time Data</h1>
    <div id="status"></div>
    <div id="updates"></div>

    <script>
        const socket = io('http://localhost:8002');
        
        socket.on('connected', (data) => {
            console.log('Connected:', data);
            document.getElementById('status').innerHTML = `Connected: ${data.client_id}`;
            
            // Subscribe to NIFTY updates
            socket.emit('subscribe', {type: 'product', symbol: 'NIFTY'});
        });
        
        socket.on('subscribed', (data) => {
            console.log('Subscribed to:', data.room);
        });
        
        socket.on('underlying_update', (data) => {
            console.log('Price update:', data);
            const div = document.getElementById('updates');
            div.innerHTML = `
                <p>
                    ${data.product}: ₹${data.price} 
                    (${new Date(data.timestamp).toLocaleTimeString()})
                </p>
            ` + div.innerHTML;
        });
        
        socket.on('chain_summary', (data) => {
            console.log('Chain summary:', data);
        });
    </script>
</body>
</html>
```

---

