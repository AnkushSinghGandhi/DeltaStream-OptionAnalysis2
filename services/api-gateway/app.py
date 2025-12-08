#!/usr/bin/env python3
"""
API Gateway Service

Central REST API gateway that:
- Routes requests to appropriate services
- Provides unified API interface
- Handles authentication
- Serves OpenAPI documentation
"""

import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
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
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth:8001')
STORAGE_SERVICE_URL = os.getenv('STORAGE_SERVICE_URL', 'http://storage:8003')
ANALYTICS_SERVICE_URL = os.getenv('ANALYTICS_SERVICE_URL', 'http://analytics:8004')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'api-gateway')
PORT = int(os.getenv('PORT', '8000'))

# Initialize Flask
app = Flask(__name__)
CORS(app)


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200


@app.route('/api/docs', methods=['GET'])
def api_docs():
    """OpenAPI documentation."""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Option ARO API",
            "version": "1.0.0",
            "description": "REST API for Option ARO clone - real-time option market data and analytics"
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Local development"}
        ],
        "paths": {
            "/api/auth/register": {
                "post": {
                    "summary": "Register new user",
                    "tags": ["Authentication"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string"},
                                        "password": {"type": "string"},
                                        "name": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/auth/login": {
                "post": {
                    "summary": "Login user",
                    "tags": ["Authentication"]
                }
            },
            "/api/data/underlying/{product}": {
                "get": {
                    "summary": "Get underlying price ticks",
                    "tags": ["Data"],
                    "parameters": [
                        {"name": "product", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}}
                    ]
                }
            },
            "/api/data/chain/{product}": {
                "get": {
                    "summary": "Get option chains",
                    "tags": ["Data"]
                }
            },
            "/api/analytics/pcr/{product}": {
                "get": {
                    "summary": "Get PCR analysis",
                    "tags": ["Analytics"]
                }
            },
            "/api/analytics/volatility-surface/{product}": {
                "get": {
                    "summary": "Get volatility surface",
                    "tags": ["Analytics"]
                }
            }
        }
    }
    return jsonify(openapi_spec), 200


# Auth endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Proxy to auth service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/register",
            json=request.get_json(),
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("register_error", error=str(e))
        return jsonify({'error': 'Auth service unavailable'}), 503


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Proxy to auth service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/login",
            json=request.get_json(),
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("login_error", error=str(e))
        return jsonify({'error': 'Auth service unavailable'}), 503


@app.route('/api/auth/verify', methods=['POST'])
def verify():
    """Proxy to auth service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/verify",
            headers={'Authorization': request.headers.get('Authorization', '')},
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("verify_error", error=str(e))
        return jsonify({'error': 'Auth service unavailable'}), 503


# Data endpoints
@app.route('/api/data/products', methods=['GET'])
def get_products():
    """Get available products."""
    try:
        response = requests.get(f"{STORAGE_SERVICE_URL}/products", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("get_products_error", error=str(e))
        return jsonify({'error': 'Storage service unavailable'}), 503


@app.route('/api/data/underlying/<product>', methods=['GET'])
def get_underlying(product):
    """Get underlying ticks."""
    try:
        params = request.args.to_dict()
        response = requests.get(
            f"{STORAGE_SERVICE_URL}/underlying/{product}",
            params=params,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("get_underlying_error", error=str(e))
        return jsonify({'error': 'Storage service unavailable'}), 503


@app.route('/api/data/chain/<product>', methods=['GET'])
def get_chain(product):
    """Get option chains."""
    try:
        params = request.args.to_dict()
        response = requests.get(
            f"{STORAGE_SERVICE_URL}/option/chain/{product}",
            params=params,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("get_chain_error", error=str(e))
        return jsonify({'error': 'Storage service unavailable'}), 503


@app.route('/api/data/expiries/<product>', methods=['GET'])
def get_expiries(product):
    """Get expiry dates."""
    try:
        response = requests.get(
            f"{STORAGE_SERVICE_URL}/expiries/{product}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("get_expiries_error", error=str(e))
        return jsonify({'error': 'Storage service unavailable'}), 503


# Analytics endpoints
@app.route('/api/analytics/pcr/<product>', methods=['GET'])
def get_pcr(product):
    """Get PCR analysis."""
    try:
        response = requests.get(
            f"{ANALYTICS_SERVICE_URL}/pcr/{product}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("get_pcr_error", error=str(e))
        return jsonify({'error': 'Analytics service unavailable'}), 503


@app.route('/api/analytics/volatility-surface/<product>', methods=['GET'])
def get_volatility_surface(product):
    """Get volatility surface."""
    try:
        response = requests.get(
            f"{ANALYTICS_SERVICE_URL}/volatility-surface/{product}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("get_volatility_surface_error", error=str(e))
        return jsonify({'error': 'Analytics service unavailable'}), 503


@app.route('/api/analytics/max-pain/<product>', methods=['GET'])
def get_max_pain(product):
    """Get max pain analysis."""
    try:
        response = requests.get(
            f"{ANALYTICS_SERVICE_URL}/max-pain/{product}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error("get_max_pain_error", error=str(e))
        return jsonify({'error': 'Analytics service unavailable'}), 503


if __name__ == '__main__':
    logger.info("api_gateway_starting", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False)
