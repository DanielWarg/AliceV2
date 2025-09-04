# 🧹 CODE PURGE PLAN - ELIMINATION OF CRUFT

**Objective:** Purge alla onödiga, överflödiga, och legacy-rester från kodebasen för att skapa en lean, optimal codebase.

## 🎯 PURGE KATEGORIER

### 1. DEAD CODE ANALYSIS 💀
- **Unused imports** (F401) - redan detekterad av ruff
- **Unused variables** (F841) - redan detekterad av ruff  
- **Unused functions/methods** - behöver analys
- **Dead code paths** - unreachable code
- **Legacy endpoints/routes** - inte längre använda

### 2. DUPLICATED CODE 🔄
- **Duplicate functionality** - samma logik på flera ställen
- **Similar classes/functions** - kan konsolideras
- **Copy-paste code patterns** - behöver abstraktion

### 3. OVERSIZED FILES 📏
- **Mega-files** (>500 lines) - kan delas upp
- **God-objects** - för många ansvar i en klass
- **Monolith functions** - för långa funktioner

### 4. LEGACY CRUFT 🗑️
- **Old version remnants** - gammal kod från tidigare versioner
- **Commented-out code** - död kod som bara ligger kvar
- **Debug remnants** - debug-kod som inte behövs
- **Test cruft** - gamla/trasiga tester

### 5. DEPENDENCY BLOAT 📦
- **Unused dependencies** - packages som inte används
- **Duplicate dependencies** - samma funktionalitet från olika libs
- **Heavy dependencies** - kan ersättas med lättare alternativ

## 🔍 ANALYSIS METHODS

### Phase 1: Automated Detection
```bash
# Dead imports/variables
ruff check --select F401,F841

# Find large files
find . -name "*.py" -exec wc -l {} + | sort -nr | head -20

# Find duplicate code patterns  
python scripts/find_duplicates.py

# Dependency analysis
pip-audit --format=json > dependency_analysis.json
```

### Phase 2: Manual Review
- **Code smell detection** - look for anti-patterns
- **Architecture review** - identify structural issues
- **Performance bottlenecks** - profiling results
- **Security review** - potential vulnerabilities

### Phase 3: Strategic Decisions
- **Keep vs Kill** - what serves the core mission
- **Refactor vs Rewrite** - cost-benefit analysis
- **Dependencies consolidation** - reduce surface area

## 🎯 PURGE TARGETS (PRELIMINARY)

### High-Priority Purge Candidates:

#### 1. **Orchestrator Service** (largest surface area)
- `src/tests/` - 11 test files, many likely outdated
- `src/llm/` - multiple planner versions, consolidate?
- `src/routers/` - shadow/experimental routes
- `src/shadow/` - shadow mode, is it used?

#### 2. **Guardian Service** 
- Complex kill sequences - are all needed?
- Multiple brownout strategies
- Legacy monitoring code

#### 3. **Root Scripts**
- 20+ scripts in `/scripts/` - many single-use
- Multiple monitoring scripts with overlap
- Dev-only scripts mixed with production

#### 4. **Dependencies**
- Heavy ML libs (pandas, pyarrow) - needed everywhere?
- Multiple HTTP clients (httpx, requests)
- Testing frameworks overlap

### Medium-Priority:
- Voice service (mostly placeholder code)
- Eval harness (complex but might be needed)
- NLU service (compact but check for cruft)

### Low-Priority:
- Cache service (simple and clean)
- Docker configs (working, don't break)

## ⚡ EXECUTION STRATEGY

### Sprint 1: Quick Wins (2-4 hours)
1. **Automated cleanup** - ruff --fix everything possible
2. **Remove obvious dead code** - commented blocks, unused imports  
3. **Dependency audit** - remove unused packages
4. **Large file identification** - list top 10 biggest files

### Sprint 2: Structural Cleanup (4-8 hours)  
1. **Service consolidation** - merge similar functionality
2. **Test suite cleanup** - remove broken/outdated tests
3. **Script consolidation** - merge/remove duplicate scripts
4. **Route cleanup** - remove experimental/unused endpoints

### Sprint 3: Deep Optimization (8+ hours)
1. **Architecture refactoring** - improve structure
2. **Performance optimization** - remove bottlenecks
3. **Security hardening** - remove potential vulnerabilities  
4. **Documentation update** - reflect new clean structure

## 📊 SUCCESS METRICS

### Quantitative:
- **-50% file count** in `/scripts/`
- **-30% lines of code** overall
- **-25% dependencies** in requirements.txt
- **0 lint issues** (currently ~30)
- **<200ms startup time** for all services

### Qualitative:
- **Crystal clear architecture** - easy to understand
- **No code smells** - passes all static analysis
- **Performance optimal** - no unnecessary overhead
- **Security hardened** - minimal attack surface
- **Developer friendly** - easy to contribute to

## 🚨 SAFETY MEASURES

### Before ANY deletion:
1. **Full test suite run** - ensure nothing breaks
2. **Git branch** - work in purge branch
3. **Backup critical data** - any configs/data
4. **Stakeholder approval** - major architectural changes

### During purge:
1. **Incremental commits** - small, reviewable changes
2. **Test after each phase** - verify system still works  
3. **Performance monitoring** - ensure no regressions
4. **Rollback plan** - ability to revert quickly

---

**NEXT ACTION:** Run automated analysis scripts to identify specific purge targets.