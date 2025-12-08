"""Integration tests for the full pipeline."""

import pytest
import json
import time
import redis
from pymongo import MongoClient


@pytest.mark.integration
class TestDataPipeline:
    """Test the complete data pipeline."""
    
    def test_feed_to_storage(self, redis_client, mongo_client):
        """Test data flows from feed to storage."""
        # This is a placeholder for integration test
        # In real test, we'd:
        # 1. Publish mock data to Redis
        # 2. Wait for worker to process
        # 3. Verify data in MongoDB
        # 4. Verify cache in Redis
        
        # For now, just verify connections
        assert redis_client.ping()
        assert mongo_client.server_info()
    
    def test_api_endpoints(self):
        """Test API endpoints are responding."""
        import requests
        
        # Test health endpoints
        services = [
            ('http://localhost:8000/health', 'api-gateway'),
            ('http://localhost:8001/health', 'auth'),
            ('http://localhost:8002/health', 'socket-gateway'),
            ('http://localhost:8003/health', 'storage'),
            ('http://localhost:8004/health', 'analytics'),
        ]
        
        for url, service in services:
            try:
                response = requests.get(url, timeout=5)
                assert response.status_code == 200
                data = response.json()
                assert data['status'] == 'healthy'
            except requests.exceptions.ConnectionError:
                pytest.skip(f"{service} not running")
