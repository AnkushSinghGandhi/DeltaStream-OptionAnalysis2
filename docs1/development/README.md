# Development Guide

> **Setup, testing, and contribution guidelines**

## 🚀 Quick Links

- [Local Setup](setup.md) - Get DeltaStream running locally
- [Testing Guide](testing.md) - Run tests and verify functionality
- [Makefile Commands](makefile-guide.md) - CLI shortcuts
- [Contributing](contributing.md) - How to contribute

---

## 🎯 Prerequisites

### Required Software
- **Python 3.10+** - Backend runtime
- **Docker & Docker Compose** - Containerization
- **Git** - Version control

### Recommended Tools
- **VS Code** or **PyCharm** - IDE
- **Postman** or **Insomnia** - API testing
- **MongoDB Compass** - Database GUI
- **Redis Insight** - Redis GUI

---

## ⚡ Quick Start (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/deltastream.git
cd deltastream

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
make build
make up

# 4. Verify
curl http://localhost:8000/health
```

**That's it!** All services are running.

---

## 🛠️ Development Workflow

### 1. Make Changes
```bash
# Create feature branch
git checkout -b feature/my-feature

# Edit code
vim services/api-gateway/app.py

# Test locally
make restart
```

### 2. Run Tests
```bash
# Unit tests
make test

# Lint code
make lint

# Format code
make format
```

### 3. Commit & Push
```bash
git add .
git commit -m "feat: add new endpoint"
git push origin feature/my-feature
```

### 4. Create Pull Request
- Open PR on GitHub
- Wait for CI/CD checks
- Request review
- Merge after approval

---

## 📁 Project Structure

```
deltastream/
├── services/                  # Microservices
│   ├── api-gateway/          # API Gateway (8000)
│   ├── auth/                 # Auth Service (8001)
│   ├── socket-gateway/       # WebSocket (8002)
│   ├── storage/              # Storage Service (8003)
│   ├── analytics/            # Analytics (8004)
│   ├── logging-service/      # Logging (8005)
│   ├── ai-analyst/           # AI Service (8006)
│   ├── feed-generator/       # Data Generation
│   └── worker-enricher/      # Data Processing
│
├── tests/                    # Test suite
│   ├── conftest.py          # Pytest configuration
│   ├── test_api.py          # API tests
│   └── test_worker.py       # Worker tests
│
├── k8s/                      # Kubernetes manifests
├── observability/            # Monitoring configs
├── docs/                     # Documentation
├── examples/                 # Code examples
│
├── docker-compose.yml        # Local orchestration
├── Makefile                  # CLI shortcuts
├── .env.example              # Environment template
└── README.md                 # Project overview
```

---

## 🧪 Testing Strategy

### Unit Tests
```bash
pytest tests/test_api.py -v
```

### Integration Tests
```bash
pytest tests/ -v --integration
```

### Load Tests
```bash
locust -f tests/locustfile.py
```

### Manual Testing
```bash
# Test API
curl http://localhost:8000/api/data/products

# Test WebSocket
node examples/subscribe-example.js
```

---

## 🐛 Debugging

### View Logs
```bash
# All services
make logs

# Specific service
make logs-worker
make logs-api

# Follow logs
docker-compose logs -f worker-enricher
```

### Access Services
```bash
# Shell into container
make shell-worker

# Redis CLI
make shell-redis

# MongoDB shell
make shell-mongo
```

### Debug Mode
```python
# Add to app.py
app.run(host='0.0.0.0', port=8000, debug=True)
```

---

## 📊 Code Quality

### Formatting
```bash
make format        # Auto-format with Black
```

### Linting
```bash
make lint          # Flake8 + Black check
```

### Type Checking
```bash
mypy services/     # Optional type checking
```

---

## 🚀 Deployment

### Local (Docker Compose)
```bash
make up
```

### Staging (Kubernetes)
```bash
kubectl apply -f k8s/ --namespace=staging
```

### Production (Kubernetes)
```bash
kubectl apply -f k8s/ --namespace=production
```

---

## 📖 Learning Resources

### For Beginners
Start with the [Complete Tutorial](../tutorials/complete-guide/)

### For Contributors
- [Architecture Docs](../architecture/)
- [API Reference](../api-reference/)
- [Interview Prep](../interview-prep/) (Deep technical concepts)

---

## 🤝 Getting Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/deltastream/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/deltastream/discussions)
- **Email**: support@deltastream.com

---

## 📚 Next Steps

1. **Set up locally**: [Setup Guide](setup.md)
2. **Run tests**: [Testing Guide](testing.md)
3. **Learn commands**: [Makefile Guide](makefile-guide.md)
4. **Start contributing**: [Contributing Guide](contributing.md)
