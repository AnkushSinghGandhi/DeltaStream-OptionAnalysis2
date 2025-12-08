#!/usr/bin/env python3
"""
Socket Gateway Service

Flask-SocketIO based WebSocket server that:
1. Accepts client connections
2. Manages room-based subscriptions (product-specific rooms)
3. Listens to Redis pub/sub for enriched data
4. Broadcasts updates to subscribed clients
5. Supports multiple instances using Redis message_queue adapter

Room structure:
- 'general': Global updates
- 'product:{SYMBOL}': Product-specific updates (e.g., 'product:NIFTY')
- 'chain:{SYMBOL}': Option chain updates
"""

import os
import json
import redis
import structlog
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
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

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Initialize SocketIO with Redis message queue for multi-instance support
redis_url = REDIS_URL
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    message_queue=redis_url,  # Critical for horizontal scaling
    async_mode='threading',
    logger=False,
    engineio_logger=False
)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Connected clients tracking
connected_clients = {}


@app.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'healthy', 'service': SERVICE_NAME, 'clients': len(connected_clients)}, 200


@app.route('/metrics')
def metrics():
    """Metrics endpoint for monitoring."""
    room_counts = {}
    for sid, client_info in connected_clients.items():
        for room in client_info.get('rooms', []):
            room_counts[room] = room_counts.get(room, 0) + 1
    
    return {
        'total_clients': len(connected_clients),
        'rooms': room_counts
    }, 200


@socketio.on('connect')
def handle_connect():
    """
    Handle client connection.
    
    Automatically joins the 'general' room for global updates.
    """
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
        'message': 'Connected to Option ARO socket gateway',
        'client_id': client_id,
        'rooms': ['general']
    })


@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle client disconnection.
    """
    client_id = request.sid
    if client_id in connected_clients:
        del connected_clients[client_id]
    
    logger.info(
        "client_disconnected",
        client_id=client_id,
        remaining_clients=len(connected_clients)
    )


@socketio.on('subscribe')
def handle_subscribe(data):
    """
    Handle subscription requests.
    
    Client can subscribe to:
    - 'product:{SYMBOL}': Product-specific updates
    - 'chain:{SYMBOL}': Option chain updates
    
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
    
    logger.info(
        "client_subscribed",
        client_id=client_id,
        room=room
    )
    
    emit('subscribed', {
        'room': room,
        'message': f'Subscribed to {room}'
    })
    
    # Send latest cached data for this subscription
    send_cached_data(room)


@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """
    Handle unsubscription requests.
    
    Args:
        data: {'type': 'product'|'chain', 'symbol': 'NIFTY'}
    """
    client_id = request.sid
    subscription_type = data.get('type')
    symbol = data.get('symbol')
    
    if not subscription_type or not symbol:
        emit('error', {'message': 'Invalid unsubscription request'})
        return
    
    room = f"{subscription_type}:{symbol}"
    leave_room(room)
    
    # Update client tracking
    if client_id in connected_clients:
        if 'rooms' in connected_clients[client_id]:
            if room in connected_clients[client_id]['rooms']:
                connected_clients[client_id]['rooms'].remove(room)
    
    logger.info(
        "client_unsubscribed",
        client_id=client_id,
        room=room
    )
    
    emit('unsubscribed', {
        'room': room,
        'message': f'Unsubscribed from {room}'
    })


@socketio.on('get_products')
def handle_get_products():
    """
    Return list of available products.
    """
    products = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'AAPL', 'TSLA', 'SPY', 'QQQ']
    emit('products', {'products': products})


def send_cached_data(room):
    """
    Send latest cached data to client upon subscription.
    
    Args:
        room: Room name (e.g., 'product:NIFTY')
    """
    try:
        room_type, symbol = room.split(':', 1)
        
        if room_type == 'product':
            # Send latest underlying price
            cached = redis_client.get(f"latest:underlying:{symbol}")
            if cached:
                data = json.loads(cached)
                socketio.emit('underlying_update', data, room=room)
        
        elif room_type == 'chain':
            # Send latest option chain (find most recent expiry)
            pattern = f"latest:chain:{symbol}:*"
            keys = redis_client.keys(pattern)
            if keys:
                # Get the first one (simplified - could sort by expiry)
                cached = redis_client.get(keys[0])
                if cached:
                    data = json.loads(cached)
                    socketio.emit('chain_update', data, room=room)
    
    except Exception as e:
        logger.error("send_cached_data_error", room=room, error=str(e))


def redis_listener():
    """
    Listen to Redis pub/sub channels and broadcast to WebSocket clients.
    
    Runs in a background thread.
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
                
                # Broadcast to general room (summary only)
                summary = {
                    'product': product,
                    'expiry': data['expiry'],
                    'spot_price': data['spot_price'],
                    'pcr_oi': data['pcr_oi'],
                    'pcr_volume': data['pcr_volume'],
                    'atm_straddle_price': data['atm_straddle_price'],
                    'timestamp': data['timestamp']
                }
                socketio.emit('chain_summary', summary, room='general')
                
                # Broadcast full chain to chain-specific room
                chain_room = f"chain:{product}"
                socketio.emit('chain_update', data, room=chain_room)
                
                logger.debug(
                    "broadcasted_chain",
                    product=product,
                    expiry=data['expiry'],
                    pcr=data['pcr_oi']
                )
        
        except Exception as e:
            logger.error("redis_listener_error", error=str(e), exc_info=True)


if __name__ == '__main__':
    # Start Redis listener in background thread
    listener_thread = Thread(target=redis_listener, daemon=True)
    listener_thread.start()
    
    logger.info(
        "socket_gateway_starting",
        port=PORT,
        service=SERVICE_NAME
    )
    
    # Run SocketIO server
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False)
