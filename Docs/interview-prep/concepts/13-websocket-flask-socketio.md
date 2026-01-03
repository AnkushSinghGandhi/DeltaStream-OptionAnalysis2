### **13. WEBSOCKET (Flask-SocketIO)**

**What it is:**
Full-duplex communication protocol allowing bi-directional real-time data between client and server over a single TCP connection.

**HTTP vs WebSocket:**
```
HTTP (Request-Response):
Client → Request → Server
Client ← Response ← Server
(Need new request for updates)

WebSocket (Persistent Connection):
Client ←→ Server
(Server can push updates anytime)
```

**In your code:**
```python
# Server pushes data to client
socketio.emit('underlying_update', data, room='product:NIFTY')

# Client receives instantly (no polling needed)
socket.on('underlying_update', (data) => {
    console.log('Live price:', data.price);
});
```

**Why WebSocket for trading:**
- Real-time price updates (no polling)
- Low latency (<100ms)
- Efficient (single connection vs repeated HTTP requests)

---
