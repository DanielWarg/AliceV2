# LOOSE THREADS INVENTORY - Alice v2
*Alla lösa trådar, buggar och skräp som måste fixas innan nästa AI*

---

## 🔍 **IDENTIFIED ISSUES**

### **1. OBSOLETE DIRECTORIES & FILES**

**❌ `services/tester/` - OLD TESTER SERVICE**
- **Problem**: Gammal tester service som inte längre används
- **Solution**: Ta bort hela directoryn
- **Impact**: Cleanup, förvirring för nästa AI
```bash
rm -rf services/tester/
```

### **2. CODE TODOS & FIXMES**

**❌ TODO i `test_nightly_scenarios.py:261`**
- **Problem**: `# TODO: Get real Guardian state` 
- **Solution**: Replace med faktisk Guardian client call
- **Impact**: Real Guardian integration i test logging
```python
# Current:
guardian_state={"state": "NORMAL"},  # TODO: Get real Guardian state

# Fix:
guardian_state = self._get_guardian_state(),
```

### **3. DOCKER COMPOSE WARNINGS**

**⚠️ Obsolete version warning**
- **Problem**: `version` attribute i docker-compose.yml
- **Solution**: Ta bort version line
- **Impact**: Clean docker-compose output

### **4. MISSING ORCHESTRATOR DOCKERFILE**

**❌ Missing Dockerfile för services/orchestrator**
- **Problem**: Loadgen och Guardian har Dockerfile, men orchestrator saknar
- **Solution**: Skapa orchestrator/Dockerfile
- **Impact**: Cannot deploy orchestrator via Docker

### **5. IMPORT PATH INCONSISTENCIES**

**⚠️ Relative vs absolute imports**
- **Problem**: Några filer använder relative imports, andra absolute
- **Location**: Fixed in status_router.py, mw_metrics.py men kolla main.py
- **Solution**: Konsistent import style

### **6. MISSING HEALTH CHECKS**

**❌ Missing curl i Docker images**
- **Problem**: Healthcheck använder curl men images installerar det inte
- **Location**: Guardian och loadgen Dockerfiles
- **Solution**: Add `RUN apt-get update && apt-get install -y curl`

---

## 🚨 **CRITICAL FIXES NEEDED**

### **Fix 1: Remove Old Tester Service**
```bash
rm -rf services/tester/
```

### **Fix 2: Create Orchestrator Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies  
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Fix 3: Add curl to Guardian Dockerfile**
```dockerfile
# Add after line 6 in services/guardian/Dockerfile:
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

### **Fix 4: Fix TODO in test_nightly_scenarios.py**
```python
def _get_guardian_state(self):
    """Get real Guardian state"""
    try:
        response = self.guardian_client.get("/health")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"state": "UNKNOWN"}

# Replace line 261:
guardian_state=self._get_guardian_state(),
```

### **Fix 5: Remove version from docker-compose.yml**
```yaml
# Remove this line:
version: '3.8'

# Keep only:
services:
  guardian:
    ...
```

---

## ✅ **VERIFICATION CHECKLIST**

After fixes, verify:
- [ ] `docker compose config` runs without warnings
- [ ] `docker compose up -d` builds all services successfully  
- [ ] `curl http://localhost:8000/health` works (orchestrator)
- [ ] `curl http://localhost:8787/health` works (guardian)
- [ ] `pytest src/tests/test_nightly_scenarios.py -v` runs without TODO warnings
- [ ] No obsolete directories remain in `services/`

---

## 🎯 **POST-FIX STATUS**

After alla fixes är klara:
- ✅ Clean Docker deployment stack
- ✅ No obsolete code or directories
- ✅ All services have proper Dockerfiles  
- ✅ Guardian state properly integrated in tests
- ✅ No TODOs or FIXMEs in critical paths
- ✅ Ready för nästa AI to focus på LLM integration

**Result**: Robust, clean, production-ready platform ready for next development phase.

---

*Inventory completed 2025-08-31 by Claude Code - No skräp left behind! 🧹*