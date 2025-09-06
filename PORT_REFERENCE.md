# 🔌 Alice v2 Dedicated Port Assignment

**VERIFIED WORKING PORTS - 2025-09-06**

## 🎯 Core Services - TESTED 2025-09-06

| Service | Port | Type | Status | Response Time | Health Check | Purpose |
|---------|------|------|--------|---------------|--------------|---------|
| **Alice API** | `18000` | External | ❌ TIMEOUT | 5000ms+ | `curl http://localhost:18000/health` | Main API endpoint via Caddy |
| **Guardian** | `8787` | Direct | ✅ WORKING | 2.1ms | `curl http://localhost:8787/health` | Service monitoring & control |
| **NLU** | `9002` | Direct | ✅ WORKING | 4.2ms | `curl http://localhost:9002/health` | Natural Language Understanding |
| **Redis Cache** | `6379` | Direct | ✅ WORKING | 5ms | `redis-cli -p 6379 ping` | Caching & session storage |

## 🖥️ Development & Monitoring Tools

| Service | Port | Type | Status | Access URL | Purpose |
|---------|------|------|--------|------------|---------|
| **Training HUD** | `8081` | Web | 🔄 On-demand | `http://localhost:8081` | Real-time training monitoring |
| **Streamlit Dashboard** | `8501` | Web | 📊 Profile | `http://localhost:8501` | Performance analytics |
| **N8N Workflows** | `5678` | Web | ⚙️ Automation | `http://localhost:5678` | Workflow automation |

## 🏗️ Internal Services (No External Access)

| Service | Internal Port | Docker Container | Access Method |
|---------|---------------|------------------|---------------|
| **Orchestrator** | `8000` | alice-orchestrator | Via Caddy proxy (port 18000) |

## 🎯 DEDICATED PORT POLICY

**RULE 1:** Each service has ONE dedicated port that NEVER changes
- ❌ Alice API: `18000` (BROKEN - 5s timeout)
- ✅ Guardian: `8787` (WORKING - 2ms) 
- ✅ NLU: `9002` (WORKING - 4ms)
- ✅ Redis: `6379` (WORKING - 5ms)

**RULE 2:** ❌ Training scripts CANNOT use port `18000` (broken)
**RULE 3:** ✅ Use Guardian `8787` for health checks instead
**RULE 4:** ✅ Direct access to working ports REQUIRED

## 🚀 Quick Start & Health Verification

```bash
# Start all services
make up

# Verify WORKING ports only (tested 2025-09-06)
curl -s http://localhost:8787/health && echo "✅ Guardian (2ms)"  
curl -s http://localhost:9002/health && echo "✅ NLU (4ms)"
redis-cli -p 6379 ping && echo "✅ Redis Cache (5ms)"

# BROKEN - DO NOT USE:
# curl -s http://localhost:18000/health  # ❌ 5s timeout
```

## 📋 Port Assignment Rules - REALITY CHECK

1. ❌ **18000** - Alice API (BROKEN - 5s timeout)
2. ✅ **8787** - Guardian (WORKING - 2ms response)
3. ✅ **9002** - NLU (WORKING - 4ms response)  
4. ✅ **6379** - Redis (WORKING - 5ms response)
5. 🔄 **8081** - Training HUD (development monitoring)
6. 📊 **8501** - Streamlit Dashboard (analytics) 
7. ⚙️ **5678** - N8N Workflows (automation)

## 🚨 CRITICAL FINDINGS

**PORT 18000 IS BROKEN** - All training scripts that use port 18000 will fail with 5s timeouts.

**WORKING ALTERNATIVES:**
- Use Guardian (8787) for health checks
- Direct service access required until 18000 fixed

---

**❌ STATUS:** Port 18000 confirmed broken, alternatives documented
**📅 Updated:** 2025-09-06 15:13 UTC  
**🎯 PURPOSE:** Prevent wasting time on broken endpoints