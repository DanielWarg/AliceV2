# Status & Metrics - Graceful Degradation

## 🎯 **Översikt**

Alice v2 använder en robust status- och metrics-arkitektur som **alltid returnerar 200** även när Guardian-tjänsten inte kan nås. Detta säkerställer att observability inte tar ned hela systemet.

## 🚦 **Status Endpoints**

### `/api/status/simple` - Alltid 200

```json
{
  "v": "1",
  "ok": true,
  "timestamp": "2025-01-01T12:00:00Z",
  "metrics": {
    /* route P95s, error rates */
  },
  "guardian": {
    "available": true,
    "state": "NORMAL",
    "details": {
      /* full Guardian health */
    }
  },
  "issues": []
}
```

**Graceful Degradation:**

- ✅ **Guardian tillgänglig**: Full status + metrics
- ⚠️ **Guardian nere**: Cached data + `"guardian_unreachable"` flagga
- 🔴 **System-fel**: Error info men fortfarande 200

### `/api/status/guardian` - Guardian-specifik

```json
{
  "ok": true,
  "guardian": {
    "state": "NORMAL",
    "ram_pct": 45.2,
    "p95": { "health_check_ms": 12.3 }
  }
}
```

## 🔄 **Guardian Health Check**

### **Retry Logic (3 försök)**

```python
# Exponential backoff: 0.2s, 0.4s, 0.8s
for attempt in range(3):
    try:
        response = await client.get("/health", timeout=2.0)
        return response.json()
    except Exception:
        if attempt < 2:
            await asyncio.sleep(0.2 * (2 ** attempt))
```

### **90s Cache**

- **Första misslyckandet**: Använd cache om < 90s gammal
- **Längre nere**: Returnera `UNREACHABLE` status
- **Recovery**: Automatisk återställning när Guardian kommer tillbaka

## 📊 **Prometheus Metrics**

### **Job Labels**

```yaml
# config/prometheus.yml
- job_name: 'alice_guardian'
  labels:
    service: 'guardian'
    environment: 'production'

- job_name: 'alice_orchestrator'
  labels:
    service: 'orchestrator'
    environment: 'production'
```

### **Key Metrics**

- `up{job="alice_guardian"}` - Guardian tillgänglighet
- `alice_guardian_ram_pct` - RAM-användning
- `alice_orchestrator_p95_ms` - Response time P95
- `alice_system_health_score` - System health (0-100)

## 🚨 **Alerting**

### **Guardian Alerts**

```yaml
- alert: GuardianUnreachable
  expr: up{job="alice_guardian"} == 0
  for: 5m
  severity: critical
```

### **System Health Alerts**

```yaml
- alert: SystemDegraded
  expr: alice_system_health_score < 70
  for: 2m
  severity: warning
```

## 🛡️ **Fail-Safe Design**

### **Princip: "Observability ska inte krascha systemet"**

1. **Status endpoints**: Alltid 200, även vid fel
2. **Guardian cache**: 90s fallback för metrics
3. **Retry logic**: 3 försök med exponential backoff
4. **Graceful degradation**: Varningar istället för krasch

### **SLO Status Logik**

- **GREEN**: Allt OK
- **YELLOW**: Guardian nere eller varningar
- **RED**: Endast vid kritiska system-fel (inte Guardian-nere)

## 🔧 **Konfiguration**

### **Environment Variables**

```bash
GUARDIAN_HEALTH_URL=http://guardian:8787/health
GUARDIAN_BASE=http://guardian:8787
```

### **Timeout & Retry**

```python
timeout = 2.0        # 2s per request
max_retries = 3      # 3 försök totalt
cache_ttl = 90.0     # 90s cache
```

## 📈 **Monitoring Dashboard**

### **HUD Integration**

- **Guardian Panel**: Real-time status + cache info
- **Metrics Panel**: Route P95s + error rates
- **System Panel**: Health score + issues

### **Grafana/Prometheus**

- **Service Uptime**: `up{job="alice_*"}`
- **Response Times**: `alice_*_p95_ms`
- **System Health**: `alice_system_health_score`

---

**🎯 Resultat**: Alice v2 kan nu hantera Guardian-nedtid utan att krascha observability. Status endpoints returnerar alltid 200 med relevant information, och systemet fungerar i degraded mode med cached Guardian-data.
