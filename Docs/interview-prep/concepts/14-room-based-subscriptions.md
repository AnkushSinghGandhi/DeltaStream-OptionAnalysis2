### **14. ROOM-BASED SUBSCRIPTIONS**

**What it is:**
Socket.IO feature allowing clients to join "rooms" and receive targeted broadcasts.

**In your code:**
```python
# Client joins room
@socketio.on('subscribe')
def handle_subscribe(data):
    symbol = data['symbol']
    room = f"product:{symbol}"
    join_room(room)  # Client now in 'product:NIFTY' room

# Server broadcasts to specific room
socketio.emit('underlying_update', data, room='product:NIFTY')
# Only clients in 'product:NIFTY' room receive this
```

**Your room structure:**
```
'general' → All clients (auto-joined)
'product:NIFTY' → Only NIFTY subscribers
'product:BANKNIFTY' → Only BANKNIFTY subscribers
'chain:NIFTY' → NIFTY option chain subscribers
```

**Benefits:**
- **Bandwidth efficiency**: Clients receive only what they subscribed to
- **Scalability**: Don't broadcast everything to everyone
- **Flexibility**: Clients control what data they receive

---
