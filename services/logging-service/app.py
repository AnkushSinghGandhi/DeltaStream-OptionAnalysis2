#!/usr/bin/env python3
"""
Logging Service

Consumes structured logs from all services and:
- Persists logs to files
- Provides query API
- Demonstrates log forwarding to ELK/Loki
"""

import os
import json
import redis
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import structlog
from pathlib import Path

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
SERVICE_NAME = os.getenv('SERVICE_NAME', 'logging-service')
PORT = int(os.getenv('PORT', '8005'))
LOG_DIR = os.getenv('LOG_DIR', '/app/logs')

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Create log directory
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200


@app.route('/logs', methods=['POST'])
def ingest_log():
    """
    Ingest a log entry.
    
    Body: JSON log entry
    """
    try:
        log_entry = request.get_json()
        
        # Add timestamp if not present
        if 'timestamp' not in log_entry:
            log_entry['timestamp'] = datetime.now().isoformat()
        
        # Write to file
        service = log_entry.get('service', 'unknown')
        log_file = Path(LOG_DIR) / f"{service}.log"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Publish to Redis for real-time monitoring
        redis_client.publish('logs:all', json.dumps(log_entry))
        
        return jsonify({'status': 'logged'}), 201
        
    except Exception as e:
        logger.error("log_ingestion_error", error=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/logs/<service>', methods=['GET'])
def get_logs(service):
    """
    Get logs for a service.
    
    Query params:
    - limit: Max number of lines (default: 100)
    """
    try:
        limit = int(request.args.get('limit', 100))
        log_file = Path(LOG_DIR) / f"{service}.log"
        
        if not log_file.exists():
            return jsonify({'logs': []}), 200
        
        # Read last N lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-limit:]
        
        logs = [json.loads(line.strip()) for line in recent_lines if line.strip()]
        
        return jsonify({
            'service': service,
            'count': len(logs),
            'logs': logs
        }), 200
        
    except Exception as e:
        logger.error("get_logs_error", error=str(e))
        return jsonify({'error': str(e)}), 500


def consume_logs():
    """
    Consume logs from Redis pub/sub (for demonstration).
    In production, use Filebeat/Promtail to forward to ELK/Loki.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe('logs:all')
    
    logger.info("log_consumer_started")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                log_entry = json.loads(message['data'])
                # Here you could forward to external log aggregator
                # For now, just print
                print(json.dumps(log_entry))
            except Exception as e:
                logger.error("log_processing_error", error=str(e))


if __name__ == '__main__':
    logger.info("logging_service_starting", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False)
