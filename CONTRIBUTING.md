# Contributing to DeltaStream - Option Analysis

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit and push
7. Create a Pull Request

## Development Setup

```bash
# Clone repository
git clone <repo-url>
cd deltastream-option-analysis

# Start services
docker-compose up -d

# Install development dependencies
pip install -r requirements-dev.txt
```

## Code Standards

### Python
- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Use Black for formatting: `black services/ tests/`
- Use flake8 for linting: `flake8 services/ tests/`

### JavaScript
- Use ES6+ features
- Follow Airbnb style guide
- Use meaningful variable names

### Git Commit Messages
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests

**Format:**
```
type(scope): short description

Longer description if needed

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Tests
```bash
pytest tests/test_worker.py -v
```

### Run Integration Tests
```bash
docker-compose up -d
pytest tests/ -v -m integration
```

### Coverage
```bash
pytest tests/ --cov=services --cov-report=html
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Request review from maintainers

### PR Checklist
- [ ] Code follows project style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] PR description clearly explains changes

## Areas for Contribution

### High Priority
- [ ] Add more unit tests
- [ ] Improve error handling
- [ ] Performance optimization
- [ ] Documentation improvements

### Features
- [ ] Add more option Greeks calculations
- [ ] Implement historical data analysis
- [ ] Add more analytics endpoints
- [ ] Create admin dashboard
- [ ] Add rate limiting

### Bug Fixes
- Check GitHub issues for open bugs
- Label: `bug`, `good first issue`

## Code Review

All submissions require review. We use GitHub pull requests for this purpose.

### Review Criteria
- Code quality and style
- Test coverage
- Documentation
- Performance impact
- Security considerations

## Questions?

Feel free to:
- Open an issue for questions
- Ask in pull request comments
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
