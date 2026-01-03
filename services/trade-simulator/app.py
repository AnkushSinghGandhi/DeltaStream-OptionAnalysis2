#!/usr/bin/env python3
"""
Trade Simulator Service

Production-grade paper trading with:
- Realistic order book matching
- Risk Management System (RMS)
- Order Management System (OMS)
- Portfolio tracking
"""

import os
import structlog
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import redis
import jwt
from functools import wraps

from order_book import OrderBookManager
from rms import RiskManagementSystem, RiskLimitError
from oms import OrderManagementSystem
from portfolio import PortfolioManager

# Configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'trade-simulator')
PORT = int(os.getenv('PORT', '8007'))
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/deltastream')
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Initialize databases
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.deltastream
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Initialize components
order_book_manager = OrderBookManager(redis_client)
rms = RiskManagementSystem(db, redis_client)
oms = OrderManagementSystem(db, redis_client, order_book_manager, rms)
portfolio_manager = PortfolioManager(db, redis_client)

logger.info("trade_simulator_initialized", port=PORT)


# Auth decorator
def require_auth(f):
    """Verify JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            request.user_id = payload['user_id']
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated


# === ORDER ENDPOINTS ===

@app.route('/api/trade/order', methods=['POST'])
@require_auth
def place_order():
    """Place new order"""
    try:
        order_data = request.get_json()
        
        # Validation
        required = ['symbol', 'order_type', 'side', 'quantity']
        if not all(field in order_data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if order_data['order_type'] == 'LIMIT' and 'price' not in order_data:
            return jsonify({'error': 'Price required for limit orders'}), 400
        
        # Place order
        order = oms.place_order(request.user_id, order_data)
        
        return jsonify({
            'order_id': order['order_id'],
            'status': order['status'],
            'filled_quantity': order['filled_quantity'],
            'avg_fill_price': order['avg_fill_price'],
            'message': f"Order {order['status'].lower()}"
        }), 201
        
    except RiskLimitError as e:
        logger.warning("risk_check_failed", user_id=request.user_id, error=str(e))
        return jsonify({'error': str(e), 'type': 'risk_limit'}), 400
    except Exception as e:
        logger.error("order_placement_failed", user_id=request.user_id, error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/trade/orders', methods=['GET'])
@require_auth
def get_orders():
    """Get user orders"""
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        orders = oms.get_orders(request.user_id, status, limit)
        
        return jsonify({'orders': orders})
        
    except Exception as e:
        logger.error("get_orders_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/trade/order/<order_id>', methods=['DELETE'])
@require_auth
def cancel_order(order_id):
    """Cancel pending order"""
    try:
        oms.cancel_order(request.user_id, order_id)
        return jsonify({'message': 'Order cancelled', 'order_id': order_id})
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("cancel_order_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


# === PORTFOLIO ENDPOINTS ===

@app.route('/api/trade/portfolio', methods=['GET'])
@require_auth
def get_portfolio():
    """Get portfolio summary"""
    try:
        portfolio = portfolio_manager.get_portfolio(request.user_id)
        return jsonify(portfolio)
        
    except Exception as e:
        logger.error("get_portfolio_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/trade/positions', methods=['GET'])
@require_auth
def get_positions():
    """Get open positions"""
    try:
        positions = portfolio_manager.get_positions(request.user_id)
        return jsonify({'positions': positions, 'count': len(positions)})
        
    except Exception as e:
        logger.error("get_positions_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/trade/pnl', methods=['GET'])
@require_auth
def get_pnl():
    """Get P&L summary"""
    try:
        period = request.args.get('period', 'all')  # today, week, month, year, all
        pnl = portfolio_manager.get_pnl_summary(request.user_id, period)
        
        return jsonify(pnl)
        
    except Exception as e:
        logger.error("get_pnl_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/trade/trades', methods=['GET'])
@require_auth
def get_trades():
    """Get trade history"""
    try:
        limit = int(request.args.get('limit', 50))
        trades = portfolio_manager.get_trade_history(request.user_id, limit)
        
        return jsonify({'trades': trades, 'count': len(trades)})
        
    except Exception as e:
        logger.error("get_trades_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/trade/performance', methods=['GET'])
@require_auth
def get_performance():
    """Get performance metrics"""
    try:
        metrics = portfolio_manager.get_performance_metrics(request.user_id)
        return jsonify(metrics)
        
    except Exception as e:
        logger.error("get_performance_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


# === RISK MANAGEMENT ENDPOINTS ===

@app.route('/api/trade/risk', methods=['GET'])
@require_auth
def get_risk_metrics():
    """Get current risk metrics"""
    try:
        metrics = rms.get_risk_metrics(request.user_id)
        return jsonify(metrics)
        
    except Exception as e:
        logger.error("get_risk_metrics_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


# === ORDER BOOK ENDPOINTS ===

@app.route('/api/trade/orderbook/<symbol>', methods=['GET'])
def get_order_book(symbol):
    """Get order book depth for symbol"""
    try:
        depth = order_book_manager.get_market_depth(symbol)
        
        if not depth:
            return jsonify({'error': 'Order book not found'}), 404
        
        return jsonify(depth)
        
    except Exception as e:
        logger.error("get_orderbook_failed", error=str(e))
        return jsonify({'error': str(e)}), 500


# === HEALTH CHECK ===

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    try:
        # Check MongoDB
        db.command('ping')
        
        # Check Redis
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'service': SERVICE_NAME,
            'components': {
                'mongodb': 'connected',
                'redis': 'connected',
                'oms': 'initialized',
                'rms': 'initialized',
                'order_book': 'initialized'
            }
        })
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("starting_trade_simulator", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False)
