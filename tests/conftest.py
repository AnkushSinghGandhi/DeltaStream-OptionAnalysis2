"""Pytest configuration and fixtures."""

import pytest
import redis
from pymongo import MongoClient
import time


@pytest.fixture(scope="session")
def redis_client():
    """Create Redis client for tests."""
    client = redis.from_url('redis://localhost:6379/0', decode_responses=True)
    yield client
    client.close()


@pytest.fixture(scope="session")
def mongo_client():
    """Create MongoDB client for tests."""
    client = MongoClient('mongodb://localhost:27017/deltastream_test')
    yield client
    # Cleanup
    client.drop_database('deltastream_test')
    client.close()


@pytest.fixture(scope="session")
def db(mongo_client):
    """Get test database."""
    return mongo_client['deltastream_test']


@pytest.fixture(autouse=True)
def cleanup_redis(redis_client):
    """Clean up Redis after each test."""
    yield
    # Clean test keys
    for key in redis_client.scan_iter("test:*"):
        redis_client.delete(key)
