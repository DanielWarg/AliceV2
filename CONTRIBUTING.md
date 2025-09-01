# Contributing to Alice v2

We love your interest in contributing to Alice v2! This document provides guidelines for how you can contribute to the project effectively.

## 🎯 Overview

Alice v2 is an enterprise-grade AI assistant system built with clean architecture. We value quality, security, and user experience above all else.

## 🤝 Ways to Contribute

### 1. Code Contributions
- New features according to roadmap
- Bug fixes and performance improvements
- Improved documentation and tests
- Translations and localization

### 2. Issue Reporting
- Detailed bug reporting with reproducible steps
- Feature requests with use cases and motivation
- Performance issues with profiling data
- Security vulnerabilities (see SECURITY.md)

### 3. Documentation
- API documentation and guides
- Code comments and inline documentation
- Architecture descriptions and decision rationale
- User guides and tutorials

## 🛠️ Development Setup

### Prerequisites
```bash
# Required tools
node --version    # v18+
python --version  # v3.11+
pnpm --version    # v8+
docker --version  # v24+
```

### Local Development
```bash
# Clone and setup
git clone https://github.com/your-org/alice-v2.git
cd alice-v2
pnpm install:all

# Start development environment  
docker compose up -d      # Infrastructure
pnpm dev:services        # Backend services
pnpm dev                 # Frontend app

# Verify setup
curl http://localhost:8000/health
curl http://localhost:8787/guardian/health
```

### Development Workflow

1. **Create Issue**: Describe problem/feature before you start coding
2. **Fork & Branch**: `git checkout -b feature/your-feature-name`
3. **Develop**: Follow code standards and write tests
4. **Test**: `pnpm test && pnpm test:e2e`
5. **Commit**: Use conventional commit format
6. **Pull Request**: Create PR with detailed description

## 📋 Code Standards

### TypeScript/JavaScript
```bash
# Linting and formatting
pnpm lint        # ESLint check
pnpm format      # Prettier formatting
pnpm type-check  # TypeScript validation
```

**Rules:**
- Strict TypeScript mode enabled
- ESLint rules enforced
- Prettier for consistent formatting
- JSDoc comments for public APIs

### Python
```bash
# Code quality tools
ruff check .     # Linting
ruff format .    # Formatting
mypy .          # Type checking
pytest          # Testing
```

**Rules:**
- Type hints mandatory for all functions
- Black/Ruff formatting enforced
- 100% test coverage for critical components
- Pydantic models for all data validation

### Git Commit Messages
We use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add new voice pipeline feature
fix: resolve memory leak in Guardian system
docs: update API documentation
test: add E2E tests for voice scenarios
refactor: simplify orchestrator routing logic
```

## 🧪 Testing Requirements

### Test Coverage
- **Unit Tests**: Minimum 80% coverage for all new code
- **Integration Tests**: Test service interactions
- **E2E Tests**: Validate complete user workflows
- **Performance Tests**: Ensure SLO compliance

### Test Execution
```bash
# Run all tests
pnpm test:all

# Run specific test suites
pnpm test:unit        # Unit tests
pnpm test:integration # Integration tests
pnpm test:e2e         # End-to-end tests
pnpm test:performance # Performance tests
```

## 🔒 Security Guidelines

### Code Review Security
- All code changes require security review
- No hardcoded secrets or API keys
- Validate all user inputs
- Follow OWASP security guidelines

### Vulnerability Reporting
- Report security issues privately (see SECURITY.md)
- Do not create public GitHub issues for security problems
- Include detailed reproduction steps
- Provide impact assessment

## 📚 Documentation Standards

### Code Documentation
- All public APIs must have JSDoc/type hints
- Complex algorithms require inline comments
- Architecture decisions must be documented
- Update README.md for new features

### API Documentation
- OpenAPI/Swagger specs for all endpoints
- Example requests and responses
- Error code documentation
- Rate limiting information

## 🚀 Release Process

### Pre-release Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Security review completed
- [ ] Performance benchmarks met
- [ ] Changelog updated

### Release Steps
1. **Version Bump**: Update version in package.json
2. **Changelog**: Document all changes
3. **Tag Release**: Create git tag
4. **Deploy**: Automated deployment via CI/CD
5. **Monitor**: Watch for issues post-release

## 🤝 Community Guidelines

### Communication
- Be respectful and inclusive
- Use clear, professional language
- Provide constructive feedback
- Help other contributors

### Code of Conduct
- Follow our Code of Conduct
- Report inappropriate behavior
- Maintain professional environment
- Respect project maintainers

## 📞 Getting Help

### Support Channels
- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and ideas
- **Security**: security@alice-ai.se for security issues
- **Documentation**: Check existing docs first

### Mentorship
- New contributors welcome
- Ask questions in discussions
- Request code review help
- Join community calls

---

**Thank you for contributing to Alice v2!** 🚀

Your contributions help make Alice v2 a better AI assistant for everyone.