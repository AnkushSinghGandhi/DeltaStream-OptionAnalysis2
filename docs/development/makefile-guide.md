# Makefile Guide

> **CLI shortcuts for development workflow**

## Build Commands

### `make build`
Build all Docker images
```bash
make build
```
Equivalent to: `docker-compose build`

---

## Service Management

### `make up`
Start all services in background
```bash
make up
```
Equivalent to: `docker-compose up -d`

### `make down`
Stop all services
```bash
make down
```

### `make restart`
Restart all services
```bash
make restart
```

### `make clean`
Stop and remove all containers, volumes
```bash
make clean
```
**Warning**: Deletes all data!

---

## Logs

### `make logs`
View all service logs
```bash
make logs
```

### Service-specific logs
```bash
make logs-api        # API Gateway
make logs-worker     # Worker Enricher
make logs-socket     # Socket Gateway
make logs-storage    # Storage Service
```

---

## Testing

### `make test`
Run all tests
```bash
make test
```

### `make lint`
Check code quality
```bash
make lint
```

### `make format`
Auto-format code with Black
```bash
make format
```

---

## Shell Access

### `make shell-mongo`
MongoDB shell
```bash
make shell-mongo
```

### `make shell-redis`
Redis CLI
```bash
make shell-redis
```

### `make shell-worker`
Worker container bash
```bash
make shell-worker
```

---

## Development Workflow

**Typical daily workflow**:
```bash
# 1. Start services
make up

# 2. View logs
make logs-api

# 3. Make code changes
vim services/api-gateway/app.py

# 4. Restart to apply changes
make restart

# 5. Run tests
make test

# 6. Stop when done
make down
```

---

## Custom Commands

To add your own commands, edit `Makefile`:
```makefile
my-command:
	@echo "Running my command"
	docker-compose exec api-gateway python my_script.py
```

Then run: `make my-command`

---

## Related
- [Setup](setup.md)
- [Testing](testing.md)
