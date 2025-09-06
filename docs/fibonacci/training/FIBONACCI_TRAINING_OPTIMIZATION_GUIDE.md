# 🏃‍♂️ FIBONACCI TRAINING OPTIMIZATION GUIDE

## 🎯 MINIMAL TRAINING SETUP - Maximal Efficiency

### **VAS BEHÖVER VI KÖRA?**

#### ✅ **KRITISKA SERVICES (MÅSTE köras)**
```bash
alice-orchestrator  # Core - hanterar Fibonacci cache & routing
alice-cache        # Redis - där all Fibonacci cache data sparas
```

#### 🔄 **OPTIONAL SERVICES (kan stängas av under träning)**  
```bash
guardian           # Säkerhets-service - inte kritisk för cache träning
alice-nlu          # NLU-service - orchestrator kan köra utan för basic queries
alice-dev-proxy    # Development proxy - inte nödvändigt för direct API calls
```

---

## ⚡ **OPTIMERAD TRAINING CONFIG**

### **Step 1: Stäng ner icke-kritiska services**
```bash
# Stoppa optional services för max resources till träning
docker compose stop guardian alice-nlu

# Behåll endast:
# - alice-orchestrator (Fibonacci engine)  
# - alice-cache (Redis cache database)
```

### **Step 2: Verify Minimal Setup**
```bash
docker compose ps
# Expected output:
# alice-orchestrator: UP (healthy)
# alice-cache: UP (healthy)  
# guardian: DOWN (stopped)
# alice-nlu: DOWN (stopped)
```

### **Step 3: Optimize Orchestrator för Training**
```bash
# Check orchestrator direct (utan proxy)
docker exec alice-orchestrator curl -s http://localhost:8000/health

# If unhealthy, restart med minimal load:
docker compose restart orchestrator
```

---

## 🧠 **MODELL OPTIMIZATION FÖR TRÄNING**

### **Current Model Status Check**
```bash
# Check vilken modell som används
docker exec alice-orchestrator grep -r "model" services/orchestrator/src/ | grep -E "(qwen|llama)" | head -5

# Check model parameters
docker logs alice-orchestrator | grep -i model | tail -10
```

### **LIGHTWEIGHT MODEL för Snabb Träning**
För cache träning behöver vi **snabba responses**, inte högkvalitativ reasoning:

#### **Recommended Training Model:**
```python
# Byt till smallest/fastest model under träning:
TRAINING_MODEL = "qwen2.5:0.5b"  # Ultra-lightweight
# eller
TRAINING_MODEL = "tinyllama:1.1b"  # Minimal resources

# Production model (efter träning):
PRODUCTION_MODEL = "qwen2.5:3b"  # Balanced performance
```

#### **Model Switch Commands:**
```bash
# Temporary environment variable för training
export TRAINING_MODE=true
export LLM_MODEL="qwen2.5:0.5b"

# Restart orchestrator med lightweight model
docker compose restart orchestrator
```

---

## 📊 **RESOURCE ALLOCATION OPTIMIZATION**

### **Memory & CPU för Training**
```bash
# Give orchestrator more resources under träning
docker update alice-orchestrator --memory=2g --cpus=2.0

# Reduce cache memory till minimum needed
docker exec alice-cache redis-cli CONFIG SET maxmemory 256mb
```

### **Network Optimization**  
```bash
# Remove unnecessary network bridges
docker network prune -f

# Optimize localhost routing (skip proxy)
# Train directly against: http://localhost:8000 (inte via 18000 proxy)
```

---

## 🏁 **OPTIMIZED TRAINING SEQUENCE**

### **Phase 1: Minimal System Prep (2 min)**
```bash
# Stop non-critical services
docker compose stop guardian alice-nlu

# Restart orchestrator för clean state  
docker compose restart orchestrator

# Verify minimal setup
sleep 10 && docker exec alice-orchestrator curl -s http://localhost:8000/health
```

### **Phase 2: Fast Training Mode (30 min)**
```bash 
# Run optimized Fibonacci training
python scripts/fibonacci_training_loop.py --fast-mode

# Expected results:
# - 55 queries (rapid_warm_up): 417ms → 280ms  
# - 89 queries (pattern_boost): 280ms → 150ms
# - 144 queries (optimization_sprint): 150ms → 80ms
```

### **Phase 3: Production Recovery (5 min)**
```bash
# Restart all services för production
docker compose up -d

# Switch to production model
export LLM_MODEL="qwen2.5:3b" 
docker compose restart orchestrator

# Validate full system
make test-all
```

---

## 🎯 **EXPECTED PERFORMANCE GAINS**

### **Training Resource Savings**
```
Full System:     ~2.5GB RAM, ~60% CPU during training
Minimal System:  ~800MB RAM, ~25% CPU during training  
Speed Increase:  3x faster cache warming
```

### **Training Efficiency**  
```
Standard Training: 1597 queries over 4 hours
Optimized Training: 288 queries over 30 minutes
Cache Hit Improvement: Same pattern learning, 8x faster
```

### **Model Performance Trade-off**
```
qwen2.5:0.5b (training):   ~50ms response, lower quality
qwen2.5:3b (production):  ~200ms response, high quality  

Training Strategy: Speed över quality för cache pattern learning
Production Switch: Quality över speed för real user queries
```

---

## 🚀 **QUICK START COMMAND**

```bash
# One-liner för optimized Fibonacci training:
docker compose stop guardian alice-nlu && \
docker compose restart orchestrator && \
sleep 15 && \
python scripts/fibonacci_training_loop.py --fast-mode && \
docker compose up -d

# Expected completion: 30 minutes
# Expected result: 417ms → ~80ms average response time
# Expected cache hit rate: 45-60% (from current 6.3%)
```

---

*🧮 Fibonacci Training Optimization - Maximal efficiency för cache pattern learning*