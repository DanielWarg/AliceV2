# Alice v2 Realistic Testing Guide
*Testning mot riktiga services utan mocks för verklig systemvalidering*

## 🎯 Filosofi: Realistic Testing

### **Problem med Mock-baserade Tester:**
- Döljer integration-problem 
- Ger falsk säkerhet om systemkvalitet
- 100% perfektionism som inte fungerar i verkligheten
- Testar inte vad systemet faktiskt gör

### **Vår Lösning: Realistic Testing:**
- Testa mot **riktiga services** - inga mocks
- **Realistiska toleranser** - 80-95% istället för 100%
- **End-to-end user journeys** - verkliga användningsfall
- **Chaos engineering** - testning under stress och fel

## 📁 Test Suite Struktur

```
src/tests/
├── test_integration.py              # Unit tests med mocks (snabba)
├── test_real_integration.py         # Integration mot riktiga services  
├── test_chaos_engineering.py        # Chaos/stress testing
└── test_orchestrator_comprehensive.py # Ursprungliga detaljerade tester
```

## 🚀 Köra Testerna

### **Snabbstart:**
```bash
# Automatisk - startar services och kör tester
./scripts/run-real-tests.sh --real --start-services

# Manuell - kör mot befintliga services  
./scripts/run-real-tests.sh --real

# Chaos engineering (destruktivt)
./scripts/run-real-tests.sh --chaos --start-services
```

### **Test Typer:**

#### **1. Unit Tests (Gamla Mock-baserade)**
```bash
./scripts/run-real-tests.sh --unit
```
- **Syfte**: Snabb feedback på logik
- **Kör**: Med mocks för isolerad testning
- **Tid**: ~10 sekunder

#### **2. Real Integration Tests** 
```bash
./scripts/run-real-tests.sh --real
```
- **Syfte**: Verifiera riktiga system-integrationer
- **Kör**: Mot faktiska services på localhost
- **Tid**: ~2-3 minuter
- **Kräver**: Orchestrator + Guardian services igång

#### **3. Chaos Engineering Tests**
```bash
./scripts/run-real-tests.sh --chaos  
```
- **Syfte**: Testning under stress och fel
- **Kör**: Skapar verkliga problem (timeouts, load, fel)
- **Tid**: ~5-10 minuter
- **Varning**: Kan påverka systemets prestanda temporärt

## 🧪 Real Integration Tests

### **Test Kategorier:**

#### **TestRealisticOrchestratorAPI**
```python
def test_chat_api_realistic_flow():
    # Testar riktiga svenska inputs:
    # "Hej Alice, vad är klockan?"
    # "Boka möte med Anna imorgon kl 14" 
    # "Vad är vädret idag?"
    
    # Realistisk förväntan: 80% success rate
    assert success_rate >= 0.8  # Not 100%!
```

**Vad som testas:**
- Riktig svensk NLU-hantering
- API versioning med graceful degradation
- Concurrent load handling (verklig trådning)
- Response time under realistic förhållanden

#### **TestGuardianIntegration**  
```python
@pytest.mark.skipif(not guardian_available)
def test_guardian_health_states_realistic():
    # Testar mot RIKTIG Guardian service
    # Inte mockat Guardian state
```

**Vad som testas:**
- Verklig Guardian HTTP-kommunikation
- Resource awareness baserat på faktisk systemstatus
- Graceful handling när Guardian är nere

#### **TestEndToEndUserJourneys**
```python
def test_swedish_conversation_flow():
    # Komplett konversation:
    # "Hej Alice!" → "Vad kan du hjälpa mig med?" → 
    # "Boka ett möte" → "Tack!"
```

**Vad som testas:**
- Hela användarresan från start till slut
- Session persistence mellan requests
- Error recovery inom conversation

## ⚡ Chaos Engineering Tests

### **Test Kategorier:**

#### **TestNetworkChaos**
```python
def test_connection_timeout_resilience():
    # Testar med timeouts: 0.1s, 0.5s, 1.0s, 5.0s
    # Realistisk förväntan: korta timeouts får misslyckas
```

#### **TestResourceChaos**
```python
def test_memory_pressure_behavior():
    # Skapar verklig minnespress med många requests
    # Monitörerar faktisk minnesanvändning
```

#### **TestGradualDegradation**  
```python
def test_increasing_load_degradation():
    # Load: 1 → 3 → 5 → 8 → 12 → 15 concurrent requests
    # Testar graceful degradation, inte cliff-drop
```

## 📊 Realistiska Förväntningar

### **Istället för 100% Perfektionism:**

| Test Scenario | Orealistisk | Realistisk | Motivering |
|---------------|-------------|------------|------------|
| API Success Rate | 100% | ≥95% | Nätverksproblem händer |
| NLU Accuracy | 100% | ≥80% | Svenska är komplext |
| Error Handling | 100% | ≥90% | Edge cases är svåra |
| Heavy Load | 100% | ≥30% | Överbelastning är normalt |
| Recovery Rate | 100% | ≥80% | Systems behöver tid |

### **Performance Förväntningar:**

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| P95 Response Time | <100ms | <200ms | >500ms |
| Concurrent Success | ≥95% | ≥80% | <50% |
| Memory Usage | <500MB | <1GB | >2GB |
| Recovery Time | <5s | <30s | >2min |

## 🔧 Kör Tester i Olika Miljöer

### **Utveckling (Lokalt):**
```bash
# Starta services
docker-compose up -d redis  # Om Redis behövs
cd services/orchestrator && source .venv/bin/activate
uvicorn main:app --port 8000 &

# Kör tester  
./scripts/run-real-tests.sh --real
```

### **CI/CD Pipeline:**
```bash
# I GitHub Actions / Jenkins
./scripts/run-real-tests.sh --all --start-services --no-stop
```

### **Staging/Pre-production:**
```bash
# Mot riktiga staging services
export ORCHESTRATOR_URL=https://alice-staging.example.com
export GUARDIAN_URL=https://guardian-staging.example.com
./scripts/run-real-tests.sh --real
```

## 📋 Test Service Requirements

### **Minimum för Real Tests:**
- **Orchestrator** på `localhost:8000` (KRÄVS)
- **Redis** för session storage (Rekommenderas)

### **Full Test Suite:**
- **Orchestrator** på `localhost:8000`  
- **Guardian** på `localhost:8787`
- **Redis** på `localhost:6379`

### **Automatisk Service Start:**
```bash
# Scriptet startar Orchestrator automatiskt
./scripts/run-real-tests.sh --real --start-services

# För manual kontroll:
./scripts/run-real-tests.sh --real --start-services --no-stop
```

## 🚨 Troubleshooting

### **"Service Not Running" Fel:**
```bash
# Kontrollera vad som körs
curl http://localhost:8000/
curl http://localhost:8787/health

# Starta manuellt
cd services/orchestrator
source .venv/bin/activate  
uvicorn main:app --port 8000
```

### **"Tests Too Slow" Problem:**
```bash
# Kör endast snabba tester
./scripts/run-real-tests.sh --unit

# Eller begränsa chaos tests
pytest src/tests/test_chaos_engineering.py::TestNetworkChaos -v
```

### **"Guardian Not Available" Warnings:**
```bash
# Normalt - Guardian tests skippas automatiskt
# För att inkludera Guardian:
cd services/guardian
python src/guardian.py &  # Start Guardian
./scripts/run-real-tests.sh --real
```

## 📈 Resultat & Analys

### **Test Data Samlas Automatiskt:**
- `test-results/raw-logs/` - Detaljerade event logs
- `test-results/analysis/` - AI-analys av rezultat  
- `test-results/baselines/` - Performance baselines

### **Alice Learning Integration:**
```python
# Varje test loggar strukturerad data för Alice
log_test_event("realistic_chat_test",
              input_text="Hej Alice",
              response_time_ms=67.3,
              success=True,
              guardian_state="NORMAL")
```

### **Continuous Improvement:**
- Real test results → Alice's training data
- Performance baselines → Regression detection
- Chaos insights → System resilience improvements

---

## 🎯 Slutsats: Varför Realistic Testing?

**Mock-tests säger:** *"Koden fungerar perfekt"*  
**Real tests säger:** *"Systemet fungerar under riktiga förhållanden"*

**Gamla approach:** 100% framgång på mockat system → krascher i produktion  
**Nya approach:** 85% framgång på riktigt system → stabil produktion

🚀 **Alice v2's realistic testing ger dig trygghet att systemet faktiskt fungerar när användarna kommer!**