#!/usr/bin/env python3
"""
Auth Service

JWT-based authentication service.
Provides user registration, login, and token verification.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
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
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/option_aro')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
SERVICE_NAME = os.getenv('SERVICE_NAME', 'auth')
PORT = int(os.getenv('PORT', '8001'))

# Initialize Flask
app = Flask(__name__)
CORS(app)

# MongoDB
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['option_aro']
users_collection = db['users']

# Create unique index on email
users_collection.create_index('email', unique=True)


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200


@app.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Body:
    {
      "email": "user@example.com",
      "password": "password123",
      "name": "John Doe"
    }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        name = data.get('name', '')
        
        # Validation
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if user exists
        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'User already exists'}), 409
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user = {
            'email': email,
            'password_hash': password_hash,
            'name': name,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        result = users_collection.insert_one(user)
        user_id = str(result.inserted_id)
        
        logger.info("user_registered", email=email, user_id=user_id)
        
        # Generate token
        token = generate_token(user_id, email)
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'name': name
            }
        }), 201
        
    except Exception as e:
        logger.error("register_error", error=str(e), exc_info=True)
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/login', methods=['POST'])
def login():
    """
    Login user.
    
    Body:
    {
      "email": "user@example.com",
      "password": "password123"
    }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user
        user = users_collection.find_one({'email': email})
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate token
        user_id = str(user['_id'])
        token = generate_token(user_id, email)
        
        logger.info("user_logged_in", email=email, user_id=user_id)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'name': user.get('name', '')
            }
        }), 200
        
    except Exception as e:
        logger.error("login_error", error=str(e), exc_info=True)
        return jsonify({'error': 'Login failed'}), 500


@app.route('/verify', methods=['POST'])
def verify():
    """
    Verify JWT token.
    
    Headers:
      Authorization: Bearer <token>
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid authorization header'}), 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        return jsonify({
            'valid': True,
            'user_id': payload['user_id'],
            'email': payload['email']
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired', 'valid': False}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token', 'valid': False}), 401
    except Exception as e:
        logger.error("verify_error", error=str(e), exc_info=True)
        return jsonify({'error': 'Verification failed', 'valid': False}), 500


@app.route('/refresh', methods=['POST'])
def refresh():
    """
    Refresh JWT token.
    
    Headers:
      Authorization: Bearer <token>
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid authorization header'}), 401
        
        token = auth_header[7:]
        
        # Decode token (allow expired tokens for refresh)
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={'verify_exp': False}
        )
        
        # Generate new token
        new_token = generate_token(payload['user_id'], payload['email'])
        
        return jsonify({
            'token': new_token
        }), 200
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error("refresh_error", error=str(e), exc_info=True)
        return jsonify({'error': 'Refresh failed'}), 500


def generate_token(user_id: str, email: str) -> str:
    """
    Generate JWT token.
    
    Args:
        user_id: User ID
        email: User email
    
    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


if __name__ == '__main__':
    logger.info("auth_service_starting", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False)
