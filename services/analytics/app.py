#!/usr/bin/env python3
"""
Analytics Service

Provides aggregation and analysis endpoints:
- PCR trends
- Volatility surface
- Max pain analysis
- OI build-up analysis
- Historical metrics
"""

import os
import json
import redis
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
import structlog

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
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/deltastream')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'analytics')
PORT = int(os.getenv('PORT', '8004'))

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Database clients
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['deltastream']


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200


@app.route('/pcr/<product>', methods=['GET'])
def get_pcr_analysis(product):
    """
    Get PCR (Put-Call Ratio) analysis.
    
    Query params:
    - expiry: Specific expiry (optional)
    - history: Include historical data (true/false)
    """
    try:
        expiry = request.args.get('expiry')
        include_history = request.args.get('history', 'false').lower() == 'true'
        
        result = {'product': product}
        
        # Get latest PCR from cache
        if expiry:
            cache_key = f"latest:pcr:{product}:{expiry}"
            cached = redis_client.get(cache_key)
            if cached:
                result['latest'] = json.loads(cached)
        else:
            # Get latest for all expiries
            pattern = f"latest:pcr:{product}:*"
            keys = redis_client.keys(pattern)
            latest_data = []
            for key in keys:
                cached = redis_client.get(key)
                if cached:
                    data = json.loads(cached)
                    expiry_date = key.split(':')[-1]
                    data['expiry'] = expiry_date
                    latest_data.append(data)
            result['latest'] = latest_data
        
        # Get historical PCR if requested
        if include_history:
            query = {'product': product}
            if expiry:
                query['expiry'] = expiry
            
            chains = list(db.option_chains.find(
                query,
                {'_id': 0, 'product': 1, 'expiry': 1, 'pcr_oi': 1, 
                 'pcr_volume': 1, 'timestamp': 1}
            ).sort('timestamp', DESCENDING).limit(100))
            
            for chain in chains:
                if 'timestamp' in chain:
                    chain['timestamp'] = chain['timestamp'].isoformat()
            
            result['history'] = chains
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error("pcr_analysis_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/volatility-surface/<product>', methods=['GET'])
def get_volatility_surface(product):
    """
    Get volatility surface (IV across strikes and expiries).
    """
    try:
        # Try cache first
        cache_key = f"volatility_surface:{product}"
        cached = redis_client.get(cache_key)
        if cached:
            return jsonify(json.loads(cached)), 200
        
        # Calculate from recent data
        recent_time = datetime.now() - timedelta(minutes=5)
        quotes = list(db.option_quotes.find({
            'product': product,
            'timestamp': {'$gte': recent_time}
        }))
        
        if not quotes:
            return jsonify({
                'product': product,
                'error': 'No recent data available'
            }), 404
        
        # Group by expiry
        expiry_groups = {}
        for quote in quotes:
            expiry = quote['expiry']
            if expiry not in expiry_groups:
                expiry_groups[expiry] = []
            expiry_groups[expiry].append(quote)
        
        # Build surface
        surface = {
            'product': product,
            'expiries': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for expiry, expiry_quotes in expiry_groups.items():
            expiry_quotes.sort(key=lambda x: x['strike'])
            
            strikes = [q['strike'] for q in expiry_quotes]
            call_ivs = [q['iv'] for q in expiry_quotes if q['option_type'] == 'CALL']
            put_ivs = [q['iv'] for q in expiry_quotes if q['option_type'] == 'PUT']
            
            avg_iv = sum([q['iv'] for q in expiry_quotes]) / len(expiry_quotes)
            
            surface['expiries'].append({
                'expiry': expiry,
                'strikes': list(set(strikes)),
                'call_ivs': call_ivs,
                'put_ivs': put_ivs,
                'avg_iv': round(avg_iv, 4),
                'num_quotes': len(expiry_quotes)
            })
        
        return jsonify(surface), 200
        
    except Exception as e:
        logger.error("volatility_surface_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/max-pain/<product>', methods=['GET'])
def get_max_pain_analysis(product):
    """
    Get max pain analysis.
    
    Query params:
    - expiry: Specific expiry (required)
    """
    try:
        expiry = request.args.get('expiry')
        if not expiry:
            return jsonify({'error': 'Expiry parameter required'}), 400
        
        # Get latest chain
        chain = db.option_chains.find_one(
            {'product': product, 'expiry': expiry},
            sort=[('timestamp', DESCENDING)]
        )
        
        if not chain:
            return jsonify({
                'product': product,
                'expiry': expiry,
                'error': 'No data available'
            }), 404
        
        result = {
            'product': product,
            'expiry': expiry,
            'max_pain_strike': chain['max_pain_strike'],
            'spot_price': chain['spot_price'],
            'distance_from_spot': chain['max_pain_strike'] - chain['spot_price'],
            'distance_pct': round(
                ((chain['max_pain_strike'] - chain['spot_price']) / chain['spot_price']) * 100,
                2
            ),
            'total_call_oi': chain['total_call_oi'],
            'total_put_oi': chain['total_put_oi'],
            'timestamp': chain['timestamp'].isoformat()
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error("max_pain_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/oi-buildup/<product>', methods=['GET'])
def get_oi_buildup(product):
    """
    Get open interest build-up analysis.
    
    Query params:
    - expiry: Specific expiry (required)
    """
    try:
        expiry = request.args.get('expiry')
        if not expiry:
            return jsonify({'error': 'Expiry parameter required'}), 400
        
        # Get latest chain
        chain = db.option_chains.find_one(
            {'product': product, 'expiry': expiry},
            sort=[('timestamp', DESCENDING)]
        )
        
        if not chain:
            return jsonify({
                'product': product,
                'expiry': expiry,
                'error': 'No data available'
            }), 404
        
        spot = chain['spot_price']
        calls = chain['calls']
        puts = chain['puts']
        
        # Analyze build-up by strike zones
        analysis = {
            'product': product,
            'expiry': expiry,
            'spot_price': spot,
            'call_buildup': {
                'itm': sum(c['open_interest'] for c in calls if c['strike'] < spot),
                'atm': sum(c['open_interest'] for c in calls if abs(c['strike'] - spot) < spot * 0.01),
                'otm': sum(c['open_interest'] for c in calls if c['strike'] > spot)
            },
            'put_buildup': {
                'itm': sum(p['open_interest'] for p in puts if p['strike'] > spot),
                'atm': sum(p['open_interest'] for p in puts if abs(p['strike'] - spot) < spot * 0.01),
                'otm': sum(p['open_interest'] for p in puts if p['strike'] < spot)
            },
            'timestamp': chain['timestamp'].isoformat()
        }
        
        # Calculate interpretation
        if analysis['call_buildup']['otm'] > analysis['put_buildup']['otm']:
            analysis['interpretation'] = 'Bullish - High OTM call writing'
        elif analysis['put_buildup']['otm'] > analysis['call_buildup']['otm']:
            analysis['interpretation'] = 'Bearish - High OTM put writing'
        else:
            analysis['interpretation'] = 'Neutral - Balanced OI'
        
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error("oi_buildup_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/ohlc/<product>', methods=['GET'])
def get_ohlc(product):
    """
    Get OHLC data.
    
    Query params:
    - window: Time window in minutes (1, 5, 15)
    """
    try:
        window = request.args.get('window', '5')
        
        cache_key = f"ohlc:{product}:{window}m"
        cached = redis_client.get(cache_key)
        
        if cached:
            return jsonify(json.loads(cached)), 200
        else:
            return jsonify({
                'product': product,
                'window': f"{window}m",
                'error': 'No OHLC data available'
            }), 404
        
    except Exception as e:
        logger.error("ohlc_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("analytics_service_starting", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False)
