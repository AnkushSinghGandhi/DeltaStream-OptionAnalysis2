# Testing Guide

> **How to run tests and verify code quality**

## Test Stack

- **pytest** - Test framework
- **pytest-flask** - Flask testing utilities
- **unittest.mock** - Mocking dependencies

---

## Running Tests

### All Tests
```bash
# Using Makefile
make test

# Or directly
pytest tests/ -v
```

### Specific Test File
```bash
pytest tests/test_api.py -v
```

### Specific Test Function
```bash
pytest tests/test_api.py::test_health_endpoint -v
```

### With Coverage
```bash
pytest tests/ --cov=services --cov-report=html
open htmlcov/index.html
```

---

## Test Structure

```
tests/
├── conftest.py          # Fixtures
├── test_api.py          # API tests
├── test_worker.py       # Worker tests
└── test_integration.py  # Integration tests
```

---

## Writing Tests

### API Test Example
```python
def test_get_products(client):
    """Test products endpoint"""
    response = client.get('/api/data/products')
    assert response.status_code == 200
    data = response.get_json()
    assert 'products' in data
```

### Worker Test Example
```python
@pytest.mark.celery
def test_process_option_chain(celery_app):
    """Test Celery task"""
    result = process_option_chain.delay(mock_chain_data)
    assert result.get(timeout=10) is not None
```

---

## Code Quality

### Linting
```bash
# Using Makefile
make lint

# Or directly
flake8 services/
```

### Formatting
```bash
# Check formatting
black --check services/

# Auto-format
make format
```

---

## Manual Testing

### 1. REST APIs
```bash
cd examples
./curl-examples.sh
```

### 2. WebSocket
```bash
cd examples
node subscribe-example.js
```

### 3. Postman
Import `examples/postman-collection.json`

---

## Continuous Integration

**GitHub Actions** (`.github/workflows/test.yml`):
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          docker-compose up -d
          make test
```

---

## Related
- [Setup Guide](setup.md)
- [Contributing](contributing.md)
