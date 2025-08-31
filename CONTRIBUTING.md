# Contributing to Alice v2

Vi älskar ditt intresse för att bidra till Alice v2! Detta dokument ger riktlinjer för hur du kan bidra till projektet på ett effektivt sätt.

## 🎯 Overview

Alice v2 är ett enterprise-grade AI assistant system byggt med clean architecture. Vi värdesätter kvalitet, säkerhet och användarupplevelse över allt annat.

## 🤝 Ways to Contribute

### 1. Code Contributions
- Nya features enligt roadmap
- Bug fixes och performance improvements
- Förbättrad dokumentation och tester
- Översättningar och lokalisering

### 2. Issue Reporting
- Detaljerad buggrapportering med reproducible steps
- Feature requests med use cases och motivation
- Performance issues med profiling data
- Security vulnerabilities (se SECURITY.md)

### 3. Documentation
- API dokumentation och guides
- Code comments och inline documentation
- Arkitekturbeskrivningar och beslutsmotivering
- User guides och tutorials

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

1. **Create Issue**: Beskriv problem/feature innan du börjar koda
2. **Fork & Branch**: `git checkout -b feature/your-feature-name`
3. **Develop**: Följ code standards och skriv tester
4. **Test**: `pnpm test && pnpm test:e2e`
5. **Commit**: Använd conventional commit format
6. **Pull Request**: Skapa PR med detaljerad beskrivning

## 📋 Code Standards

### TypeScript/JavaScript
```bash
# Linting och formatting
pnpm lint        # ESLint check
pnpm format      # Prettier formatting
pnpm type-check  # TypeScript validation
```

**Rules:**
- Strict TypeScript mode enabled
- ESLint rules enforced
- Prettier for consistent formatting
- JSDoc comments för public APIs

### Python
```bash
# Code quality tools
ruff check .     # Linting
ruff format .    # Formatting
mypy .          # Type checking
pytest          # Testing
```

**Rules:**
- Type hints obligatoriska för alla functions
- Black/Ruff formatting enforced
- 100% test coverage för kritiska komponenter
- Pydantic models för all data validation

### Git Commit Messages
Vi använder [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: type(scope): description
feat(voice): add Swedish NLU support
fix(guardian): resolve memory leak in state machine
docs(api): update WebSocket client examples
test(e2e): add voice pipeline integration tests
perf(tts): optimize audio cache performance
```

**Types:**
- `feat`: Nya features
- `fix`: Bug fixes
- `docs`: Dokumentation changes
- `test`: Tester additions/changes
- `perf`: Performance improvements
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

## 🧪 Testing Requirements

### Unit Tests
```bash
# Python services
pytest services/*/tests/ -v --cov=src

# TypeScript packages
pnpm --filter @alice/api test
pnpm --filter web test
```

### Integration Tests
```bash
# Full system integration
pnpm test:e2e

# Guardian brownout simulation
python tests/integration/test_guardian_brownout.py

# Voice pipeline E2E
playwright test tests/e2e/voice-flow.spec.ts
```

### Performance Tests
```bash
# Voice latency benchmarking
python tests/performance/test_voice_latency.py

# Guardian response times
python tests/performance/test_guardian_sla.py
```

**Requirements:**
- All new features måste ha unit tests
- Integration tests för API changes
- Performance regression tests för critical paths
- E2E tests för user-facing features

## 📏 Pull Request Guidelines

### Before Submitting
- [ ] Fork repo och create feature branch
- [ ] Write clear commit messages
- [ ] Add/update tests för changes
- [ ] Update documentation if needed
- [ ] Run full test suite locally
- [ ] Check code linting passes

### PR Description Template
```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)  
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review performed
- [ ] Documentation updated
- [ ] No new warnings introduced
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests
2. **Code Review**: Maintainer reviews code quality
3. **Integration Testing**: Manual testing in staging environment
4. **Approval**: Two maintainer approvals required
5. **Merge**: Squash and merge to main branch

## 🔒 Security Considerations

### Security Guidelines
- Never commit secrets eller credentials
- Use environment variables för configuration
- Sanitize all user inputs
- Follow OWASP security practices
- Run dependency security scans

### Guardian System
- Guardian safety logic får ALDRIG ändras utan extensive review
- System safety har högsta prioritet över features
- Performance regression som påverkar Guardian måste fixas omedelbart

### Memory & Privacy
- All memory operations måste respektera user consent
- PII masking obligatoriskt i loggar
- User data får aldrig lämna enheten utan explicit tillåtelse

## 🐛 Bug Reports

### Bug Report Template
```markdown
## Bug Description
Clear och concise description

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

## Expected Behavior
What you expected to happen

## Actual Behavior  
What actually happened

## Environment
- OS: [e.g., macOS 14.0]
- Node version: [e.g., 18.17.0]
- Python version: [e.g., 3.11.5]
- Browser: [e.g., Chrome 118.0]

## Additional Context
Screenshots, logs, eller additional information
```

## 🚀 Feature Requests

### Feature Request Template
```markdown
## Feature Summary
One-line summary of the feature

## Problem Statement
What problem does this solve?

## Proposed Solution
Detailed description of your solution

## Alternatives Considered
Other approaches you've considered

## Additional Context
Use cases, mockups, eller examples
```

### Feature Review Process
1. **Community Discussion**: Issue discussion och feedback
2. **Technical Review**: Architecture och implementation planning
3. **Roadmap Integration**: Priority och timeline planning
4. **Implementation**: Development enligt agreed design
5. **Testing**: Comprehensive testing och validation

## 🎨 UI/UX Contributions

### Design Guidelines
- Follow design system i `packages/ui`
- Maintain accessibility standards (WCAG 2.1 AA)
- Responsive design för desktop + mobile
- Swedish language first, English fallback

### Component Development
```bash
# Create new UI component
cd packages/ui
pnpm create-component MyComponent

# Test component in isolation
pnpm storybook
```

## 📊 Performance Standards

### SLA Requirements
- **Voice Pipeline**: P95 latency <2000ms
- **Guardian Response**: <150ms for state transitions
- **API Responses**: P95 <500ms för standard endpoints
- **Frontend**: First Contentful Paint <1.5s

### Monitoring
- All new features måste include metrics
- Performance regression tests required
- Resource usage monitoring (RAM, CPU, network)

## 🌍 Internationalization

### Language Support
- **Primary**: Svenska (sv-SE)
- **Secondary**: English (en-US)
- **Future**: Norwegian, Danish, Finnish

### Translation Guidelines
```typescript
// Use i18n keys
t('voice.listening.status')
t('guardian.brownout.message')

// Provide context
t('error.network.title', { service: 'Guardian' })
```

## 📞 Communication

### Getting Help
- **GitHub Issues**: Technical questions och bug reports
- **GitHub Discussions**: Design discussions och feature requests
- **Discord**: Real-time chat med community (link in README)

### Code of Conduct
Vi följer [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Alla deltagare förväntas följa denna code.

## 🏆 Recognition

Vi värdesätter alla bidrag! Contributors kommer att:
- Listas i project CONTRIBUTORS.md
- Få recognition i release notes
- Bli invited till maintainer team vid significant contributions

---

**Tack för ditt bidrag till Alice v2! 🚀**

Together we build the future of AI assistance!