# GitHub Repository Setup Guide

## 🚀 Quick Setup Instructions

### 1. Create GitHub Repository
Go to [GitHub](https://github.com) and:

1. Click "New repository"
2. **Repository name**: alice-v2
3. **Description**: Alice v2 AI Assistant - Next-generation AI assistant with deterministic safety and real-time voice pipeline
4. **Visibility**: ✅ **Private** (important!)
5. **DON'T** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### 2. Connect Local Repository

```bash
cd /Users/evil/Desktop/EVIL/PROJECT/alice-v2

# Add GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/alice-v2.git

# Push initial commit
git push -u origin main
```

### 3. Repository Settings (Recommended)

After creating the repo, go to Settings and configure:

#### General Settings
- ✅ Restrict pushes that create files larger than 100 MB
- ✅ Allow merge commits
- ✅ Allow squash merging
- ✅ Allow rebase merging
- ✅ Automatically delete head branches

#### Branch Protection (for main branch)
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
- ✅ Restrict pushes that create files larger than 100 MB

#### Security & Analysis
- ✅ Dependency graph
- ✅ Dependabot alerts
- ✅ Dependabot security updates

## 📂 Repository Structure Verification

Check that these files/folders exist in your repo:

```
alice-v2/
├── README.md                    ✅ Professional overview
├── ROADMAP.md                   ✅ 17-step implementation plan
├── ALICE_SYSTEM_BLUEPRINT.md    ✅ System architecture
├── CONTRIBUTING.md              ✅ Contribution guidelines
├── .gitignore                   ✅ Proper exclusions
├── package.json                 ✅ Monorepo root
├── pnpm-workspace.yaml          ✅ Workspace configuration
├── services/
│   ├── orchestrator/            ✅ Core orchestration service
│   ├── guardian/                ✅ Safety system
│   └── memory/                  ✅ Memory and RAG system
├── apps/
│   ├── web/                     ✅ Next.js frontend
│   └── hud/                     ✅ Monitoring dashboard
├── monitoring/                  ✅ Observability tools
├── scripts/                     ✅ Development automation
└── docs/                        ✅ Documentation
```

## 🧪 Verification Commands

After pushing to GitHub, test locally:

```bash
# Install dependencies
pnpm install

# Start development environment
make up

# Run integration tests
./scripts/auto_verify.sh

# Should show: All tests PASS ✅
```

## 🎯 Success Criteria

You know the setup succeeded when:

1. ✅ Repository is **private** on GitHub
2. ✅ All files pushed correctly (100+ files in first commit)
3. ✅ README.md displays nicely on GitHub with project overview
4. ✅ Integration tests pass locally (`auto_verify.sh` green)
5. ✅ `make up` works without errors
6. ✅ Repository has professional structure and documentation

## 🔧 Additional Configuration

### Environment Variables
Set up required environment variables:

```bash
# OpenAI (for Hybrid Planner)
export OPENAI_API_KEY=sk-your-key-here
export OPENAI_DAILY_BUDGET_USD=1.00
export OPENAI_WEEKLY_BUDGET_USD=3.00

# n8n Security
export N8N_ENCRYPTION_KEY=change-me
export N8N_WEBHOOK_SECRET=your-secret

# User Opt-in
export CLOUD_OK=false
```

### Pre-commit Hooks
Install pre-commit hooks for code quality:

```bash
# Python
pre-commit install

# JavaScript/TypeScript
pnpm dlx husky-init && pnpm i
```

## 🚨 Troubleshooting

### Common Issues

**"Permission denied" when pushing:**
- Check that you have write access to the repository
- Verify your GitHub credentials are correct

**"Branch protection rules" blocking push:**
- Create a feature branch: `git checkout -b feature/your-feature`
- Push to feature branch: `git push origin feature/your-feature`
- Create a Pull Request to merge into main

**"Dependencies not found":**
- Run `pnpm install:all` to install all workspace dependencies
- Check that Node.js version is 18+ and Python is 3.11+

## 📚 Next Steps

After successful setup:

1. **Read the Architecture**: Review `ALICE_SYSTEM_BLUEPRINT.md`
2. **Check Roadmap**: See `ROADMAP.md` for current status
3. **Review Contributing**: Read `CONTRIBUTING.md` for guidelines
4. **Start Development**: Begin with current milestone in roadmap

---

**Need help?** Create an issue in the repository or check the documentation in `docs/`.
