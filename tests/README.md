# Tests

## Running Tests

### Unit Tests
```bash
pytest tests/ -v
```

### Integration Tests
```bash
# Start services first
docker-compose up -d

# Run integration tests
pytest tests/ -v -m integration
```

### Coverage
```bash
pytest tests/ --cov=services --cov-report=html
open htmlcov/index.html
```

## Test Structure

- `conftest.py`: Pytest fixtures and configuration
- `test_feed_generator.py`: Feed generator unit tests
- `test_worker.py`: Worker enricher unit tests
- `test_integration.py`: Full pipeline integration tests
