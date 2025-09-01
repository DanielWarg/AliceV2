# Development Control Commands

## 🚀 **Stack Management**

### **Start Stack**
```bash
make up          # Start development stack (requires Docker)
```

**Fails gracefully if:**
- Docker not running → Clear error message
- Ports occupied → Instructions to run cleanup first

### **Stop Stack**
```bash
make down        # Graceful stop with Docker fallback
make force-down  # Force stop (no Docker dependency)
make docker-down # Strict Docker-only stop
```

**Robust fallback behavior:**
- ✅ **Docker running**: Uses `docker compose down`
- ⚠️ **Docker down**: Automatically falls back to `ports-kill.sh`
- 💥 **Force mode**: Always works, kills processes directly

### **Restart & Status**
```bash
make restart     # down → up with fallbacks
make preflight  # Check Docker status + port usage
```

## 🛡️ **Fallback Strategy**

### **Why Fallbacks?**
- **Docker daemon crashes** during development
- **CI/CD environments** where Docker might not be available
- **Port conflicts** from previous runs
- **System reboots** leaving orphaned processes

### **Fallback Chain**
```
make down
├── Docker available → docker compose down
├── Docker down → ports-kill.sh
└── Always succeeds
```

## 🔧 **Port Management**

### **Standard Ports**
- **8000**: Orchestrator API
- **8501**: Streamlit HUD
- **8787**: Guardian service
- **11434**: Ollama (if running)
- **18000**: Dev proxy

### **Port Cleanup**
```bash
./scripts/ports-kill.sh  # Kill processes on all ports
./scripts/ports-kill.sh  # Idempotent - safe to run multiple times
```

## 📋 **Common Scenarios**

### **Scenario 1: Docker Running**
```bash
make up          # ✅ Starts stack normally
make down        # ✅ Stops with docker compose down
```

### **Scenario 2: Docker Daemon Down**
```bash
make up          # ❌ Fails with clear message
make down        # ✅ Falls back to ports-kill, succeeds
make force-down  # ✅ Always works
```

### **Scenario 3: Port Conflicts**
```bash
make preflight   # 🔍 Shows what's using ports
make force-down  # 💥 Clears all ports
make up          # ✅ Starts clean
```

### **Scenario 4: CI/CD Environment**
```bash
make force-down  # 💥 No Docker dependency
make clean       # 🧹 Clean build artifacts
make up          # 🚀 Fresh start
```

## 🚨 **Troubleshooting**

### **"make down hangs"**
```bash
# Kill the hanging process
Ctrl+C

# Use force mode
make force-down

# Check what happened
make preflight
```

### **"Port already in use"**
```bash
# See what's using ports
make preflight

# Force clear everything
make force-down

# Start fresh
make up
```

### **"Docker connection failed"**
```bash
# Check Docker status
docker info

# If Docker is down, use force mode
make force-down

# Restart Docker app, then
make up
```

## 📚 **Command Reference**

| Command | Purpose | Docker Required | Fallback |
|---------|---------|----------------|----------|
| `make up` | Start stack | ✅ Yes | ❌ None |
| `make down` | Stop stack | ⚠️ Preferred | ✅ ports-kill |
| `make force-down` | Force stop | ❌ No | ❌ None |
| `make restart` | Restart stack | ⚠️ Preferred | ✅ ports-kill |
| `make preflight` | Check status | ❌ No | ❌ None |

## 🎯 **Best Practices**

### **Development Workflow**
1. **Start**: `make up`
2. **Work**: Develop and test
3. **Stop**: `make down` (automatic fallback)
4. **Restart**: `make restart` (if needed)

### **CI/CD Workflow**
1. **Pre-build**: `make force-down` (guaranteed cleanup)
2. **Build**: `make up`
3. **Test**: Run tests
4. **Post-build**: `make force-down` (guaranteed cleanup)

### **Emergency Cleanup**
```bash
# Nuclear option - clears everything
make force-down
./scripts/ports-kill.sh
docker system prune -f  # If Docker available
```

---

**🎯 Resultat**: Alice v2 har nu robusta dev control commands som fungerar oavsett Docker-status. `make down` hänger aldrig igen, och alla fallbacks är automatiska.
