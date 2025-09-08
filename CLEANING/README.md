# 🧹 CLEANING - Deprecated Files Archive

**Created**: 2025-09-08 (post T9 Multi-Agent completion)  
**Git Tag**: v2.9.0-t9-complete  
**Reason**: Repository hygiene after T8/T9 system completion

## 📁 Directory Structure

```
CLEANING/
├── root-docs/          # Outdated documentation from root
├── legacy-python/      # Old Python scripts no longer used  
├── old-scripts/        # Deprecated shell/Python scripts
├── legacy-training/    # Old training artifacts
├── legacy-md/          # Superseded markdown documentation
├── legacy-results/     # Old JSON results and metrics
└── README.md          # This file
```

## 🗂️ Files Moved to Archive

### **root-docs/** - Superseded Documentation
- `ALICE_VNEXT_STEP1_CHECKLIST.md` → Replaced by AGENTS.md + PROJECT_STATUS.md
- `ALICE_PRODUCTION_CHECKLIST.md` → Replaced by PRIORITIZED_BACKLOG.md
- `T1_T6_HARDENING_CHECKLIST.md` → Obsolete, replaced by T8/T9 system
- `STATUS.md` → Consolidated into PROJECT_STATUS.md
- `SYSTEM_INVENTORY.md` → Information moved to AGENTS.md
- `VERSIONING.md` → Using git tags instead

### **legacy-python/** - Outdated Python Scripts
- `alice_parallel_evolution.py` → Replaced by T8/T9 multi-agent system
- `fix_system_health.py` → Services now have proper health checks
- `night_test.py` → Replaced by T8 overnight optimizer
- `test_t5_gates.py` → T5 phase completed, now in T8/T9
- `T1_T6_GO_NOGO_VALIDATION.py` → Replaced by morning checklist

### **legacy-md/** - Superseded Documentation  
- `T8_*.md` files → Consolidated into AGENTS.md and PRIORITIZED_BACKLOG.md
- `DAYTIME_CLAUDE_TASKS.md` → Tasks completed or integrated into workflows
- `GPT_VS_REALITY_COMPARISON.md` → Historical document, no longer relevant
- `COMPLETE_TRAINING_CODE_REFERENCE.md` → Training code now in active T8/T9 system
- `T9_CLAUDE_CODE_INSTRUCTIONS.md` → T9 system now implemented

### **old-scripts/** - Deprecated Scripts
- `cleanup.sh` → Replaced by this structured cleanup process
- `purge_analysis.py` → Analysis completed
- `warm_cache.py` → Cache warming now automated
- `setup-cron.sh` → Using GitHub Actions instead

### **legacy-results/** - Historical Metrics
- Various JSON training results and metrics files
- Replaced by T8/T9 telemetry and reporting system

## 🎯 Current Active Documentation

**Core Documentation** (kept in root):
- `AGENTS.md` - Complete system status and implementation details
- `PROJECT_STATUS.md` - Current development status 
- `PRIORITIZED_BACKLOG.md` - Current priorities and roadmap
- `README.md` - System overview and quick start
- `ROADMAP.md` - Future development plans

**Operational Documentation**:
- `ops/checklists/MORNING_CHECKLIST.md` - Daily operational routine
- `T8_README.md` - T8 stabilization system
- `T9_README.md` - T9 multi-agent system

## 🔄 Restoration Instructions

If any of these files are needed in the future:

```bash
# Restore individual file
cp CLEANING/category/filename.ext ./

# Restore entire category
cp -r CLEANING/category/* ./

# View what was moved
ls -la CLEANING/*/
```

## ⚠️ Safe to Delete

These files can be safely deleted after confirming no dependencies exist:
- All files have been superseded by newer implementations
- Git history preserves all content via tag v2.9.0-t9-complete
- Active system no longer references any moved files

---

**Repository State**: Clean and focused on T8/T9 integration  
**Next Phase**: T8 overnight soak + T9 nightly evaluation → production integration