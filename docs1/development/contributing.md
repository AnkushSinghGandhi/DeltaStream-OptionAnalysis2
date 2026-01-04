# Contributing Guide

> **How to contribute to DeltaStream**

## Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/deltastream.git
   cd deltastream
   ```
3. **Follow [setup guide](setup.md)**

---

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/my-feature
```

Branch naming:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring

### 2. Make Changes
```bash
# Edit code
vim services/api-gateway/app.py

# Test locally
make up
make test
```

### 3. Commit Changes
```bash
git add .
git commit -m "feat: add new endpoint"
```

**Commit message format**:
```
type(scope): description

[optional body]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring

**Examples**:
```
feat(api): add product expiries endpoint
fix(worker): resolve PCR calculation bug
docs(readme): update installation steps
```

### 4. Push to Fork
```bash
git push origin feature/my-feature
```

### 5. Create Pull Request
- Go to GitHub
- Click "New Pull Request"
- Describe changes
- Link related issues

---

## Code Standards

### Python Style
- **PEP 8**: Follow Python style guide
- **Black**: Auto-format with `make format`
- **Flake8**: Lint with `make lint`
- **Type hints**: Use where applicable

**Example**:
```python
def calculate_pcr(calls: list, puts: list) -> float:
    """Calculate Put-Call Ratio.
    
    Args:
        calls: List of call option dicts
        puts: List of put option dicts
        
    Returns:
        PCR value (put OI / call OI)
    """
    # Implementation
```

### Testing
- Write tests for new features
- Maintain > 80% code coverage
- Test edge cases

### Documentation
- Update README if needed
- Add docstrings to functions
- Update API docs for new endpoints

---

## Pull Request Checklist

Before submitting PR:

- [ ] Code follows style guidelines (`make lint` passes)
- [ ] Tests added/updated (`make test` passes)
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] Branch is up to date with main

---

## Review Process

1. **Automated checks**: CI/CD runs tests
2. **Code review**: Maintainer reviews code
3. **Feedback**: Address review comments
4. **Approval**: PR approved
5. **Merge**: Merged to main

**Response time**: Usually 1-3 days

---

## Questions?

- **Issues**: [GitHub Issues](https://github.com/yourusername/deltastream/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/deltastream/discussions)

---

**Thank you for contributing!** 🎉
