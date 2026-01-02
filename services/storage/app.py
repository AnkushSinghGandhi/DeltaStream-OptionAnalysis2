#!/usr/bin/env python3
"""
Storage Service

MongoDB wrapper service providing REST API for data storage and retrieval.
Abstracts database operations and provides a clean interface for other services.
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING
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
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/deltastream')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'storage')
PORT = int(os.getenv('PORT', '8003'))

# Initialize Flask
app = Flask(__name__)
CORS(app)
app.config['JSON_SORT_KEYS'] = False

# MongoDB client
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['deltastream']

# Create indexes
db.underlying_ticks.create_index([('product', ASCENDING), ('timestamp', DESCENDING)])
db.underlying_ticks.create_index([('timestamp', DESCENDING)])
db.option_quotes.create_index([('symbol', ASCENDING), ('timestamp', DESCENDING)])
db.option_quotes.create_index([('product', ASCENDING), ('timestamp', DESCENDING)])
db.option_chains.create_index([('product', ASCENDING), ('expiry', ASCENDING), ('timestamp', DESCENDING)])


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    try:
        # Ping MongoDB
        mongo_client.admin.command('ping')
        return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


@app.route('/underlying/<product>', methods=['GET'])
def get_underlying_ticks(product):
    """
    Get underlying price ticks for a product.
    
    Query params:
    - start: Start timestamp (ISO format)
    - end: End timestamp (ISO format)
    - limit: Max number of results (default: 100)
    """
    try:
        # Parse query params
        start = request.args.get('start')
        end = request.args.get('end')
        limit = int(request.args.get('limit', 100))
        
        # Build query
        query = {'product': product}
        if start or end:
            query['timestamp'] = {}
            if start:
                query['timestamp']['$gte'] = datetime.fromisoformat(start)
            if end:
                query['timestamp']['$lte'] = datetime.fromisoformat(end)
        
        # Execute query
        ticks = list(db.underlying_ticks.find(
            query,
            {'_id': 0}
        ).sort('timestamp', DESCENDING).limit(limit))
        
        # Convert datetime to ISO string
        for tick in ticks:
            if 'timestamp' in tick:
                tick['timestamp'] = tick['timestamp'].isoformat()
            if 'processed_at' in tick:
                tick['processed_at'] = tick['processed_at'].isoformat()
        
        return jsonify({
            'product': product,
            'count': len(ticks),
            'ticks': ticks
        }), 200
        
    except Exception as e:
        logger.error("get_underlying_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/option/quote/<symbol>', methods=['GET'])
def get_option_quote(symbol):
    """
    Get option quotes for a symbol.
    
    Query params:
    - limit: Max number of results (default: 100)
    """
    try:
        limit = int(request.args.get('limit', 100))
        
        quotes = list(db.option_quotes.find(
            {'symbol': symbol},
            {'_id': 0}
        ).sort('timestamp', DESCENDING).limit(limit))
        
        for quote in quotes:
            if 'timestamp' in quote:
                quote['timestamp'] = quote['timestamp'].isoformat()
            if 'processed_at' in quote:
                quote['processed_at'] = quote['processed_at'].isoformat()
        
        return jsonify({
            'symbol': symbol,
            'count': len(quotes),
            'quotes': quotes
        }), 200
        
    except Exception as e:
        logger.error("get_option_quote_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/option/chain/<product>', methods=['GET'])
def get_option_chain(product):
    """
    Get option chains for a product.
    
    Query params:
    - expiry: Expiry date (YYYY-MM-DD) - optional
    - limit: Max number of results (default: 10)
    """
    try:
        expiry = request.args.get('expiry')
        limit = int(request.args.get('limit', 10))
        
        query = {'product': product}
        if expiry:
            query['expiry'] = expiry
        
        chains = list(db.option_chains.find(
            query,
            {'_id': 0}
        ).sort('timestamp', DESCENDING).limit(limit))
        
        for chain in chains:
            if 'timestamp' in chain:
                chain['timestamp'] = chain['timestamp'].isoformat()
            if 'processed_at' in chain:
                chain['processed_at'] = chain['processed_at'].isoformat()
        
        return jsonify({
            'product': product,
            'count': len(chains),
            'chains': chains
        }), 200
        
    except Exception as e:
        logger.error("get_option_chain_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/products', methods=['GET'])
def get_products():
    """
    Get list of available products.
    """
    try:
        products = db.underlying_ticks.distinct('product')
        return jsonify({'products': products}), 200
    except Exception as e:
        logger.error("get_products_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/expiries/<product>', methods=['GET'])
def get_expiries(product):
    """
    Get available expiry dates for a product.
    """
    try:
        expiries = db.option_chains.distinct('expiry', {'product': product})
        expiries.sort()
        return jsonify({
            'product': product,
            'expiries': expiries
        }), 200
    except Exception as e:
        logger.error("get_expiries_error", error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("storage_service_starting", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False)
