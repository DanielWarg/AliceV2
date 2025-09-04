# Docker Cache Lessons Learned

## 🚨 **Problem vi stötte på**

### **Symptom:**

- Kod-ändringar tog inte effekt i containern
- `docker compose restart` fungerade inte för kod-ändringar
- Containern hade gammal kod trots att host-filen var uppdaterad
- Vi gick runt i cirklar med små fel som inte löstes

### **Exempel på problem:**

```bash
# Host hade rätt kod:
sed -n '288,292p' services/orchestrator/src/routers/chat.py
# Visade: if orchestrator_response and hasattr(orchestrator_response, 'metadata')

# Container hade fel kod:
docker exec alice-orchestrator sed -n '288,292p' /app/src/routers/chat.py
# Visade: if hasattr(orchestrator_response, 'metadata')
```

## 🔍 **Roten till problemet**

### **1. Docker Cache Problem**

```bash
# Detta fungerar INTE för kod-ändringar:
docker compose restart orchestrator

# Detta fungerar INTE heller:
docker compose build orchestrator && docker compose restart orchestrator

# Detta fungerar bara ibland:
docker compose build --no-cache orchestrator
```

**Orsak**: Docker använder cached layers. När vi ändrar Python-kod, kopieras den gamla koden från cache istället för den nya.

### **2. Fil-synkronisering Problem**

**Orsak**: Docker COPY-kommandot kopierar inte alltid de senaste ändringarna.

### **3. Dependency Chain Problem**

```python
# Vi ändrar ModelType enum
class ModelType(str, Enum):
    OPENAI_GPT4O_MINI = "openai:gpt-4o-mini"  # NYTT

# Men ChatResponse använder fortfarande gammal enum
class ChatResponse(BaseResponse):
    model_used: ModelType = Field(...)  # Använder gammal enum
```

**Orsak**: Python-moduler laddas om inte automatiskt när vi ändrar dependencies.

## 🛠️ **Lösningar som fungerar**

### **Lösning 1: Fullständig Rebuild**

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### **Lösning 2: Volym Mount (Development)**

```yaml
# I docker-compose.yml
volumes:
  - ./services/orchestrator:/app
```

### **Lösning 3: Hot Reload**

```python
# Använd uvicorn med --reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🎯 **Varför fastnade VI**

1. **Vi försökte snabba lösningar** (`restart` istället för `build`)
2. **Vi tror att cache fungerar** när den inte gör det
3. **Vi fixar ett problem** men skapar ett nytt
4. **Vi följer inte dependency chain** korrekt

## 🚀 **Bästa praxis för framtiden**

### **För olika typer av ändringar:**

```bash
# För kod-ändringar:
make down
make up

# För konfigurationsändringar:
docker compose restart [service]

# För debugging:
docker compose logs -f [service]
```

### **Snabb utveckling:**

```bash
# Snabb utveckling (bara kärntjänster):
make dev-fast

# Full stack när vi behöver allt:
make up

# Snabb kod-ändring (om volym mount finns):
docker compose restart orchestrator
```

## 📊 **Prestanda-jämförelse**

| Kommando                 | Tid     | Tjänster     | Användning       |
| ------------------------ | ------- | ------------ | ---------------- |
| `make up`                | ~5 min  | Alla         | Full stack       |
| `make dev-fast`          | ~2 min  | Kärntjänster | Snabb utveckling |
| `docker compose restart` | ~15 sek | En tjänst    | Konfiguration    |

## 🔧 **Vad vi implementerade**

### **1. Snabb utvecklingsmiljö**

- `scripts/dev_up_fast.sh` - Startar bara kärntjänster
- `make dev-fast` - Snabb utveckling utan voice/memory/redis

### **2. Tydlig separation**

- **Kärntjänster**: guardian, orchestrator, nlu, dev-proxy
- **Valfria tjänster**: voice, memory, redis, dashboard, etc.

### **3. Bättre feedback**

- Tydliga meddelanden om vad som startar
- Varningar om vad som saknas
- Snabbare health checks

## 🎉 **Resultat**

- **60% snabbare omstarter** för utveckling
- **Tydligare separation** mellan kärn- och valfria tjänster
- **Bättre förståelse** för när olika kommandon ska användas
- **Mindre frustration** med Docker-cachen

## 📝 **Lärdomar**

1. **Docker cache är inte din vän** för kod-ändringar
2. **Fullständig rebuild** är ofta snabbare än att debugga cache-problem
3. **Volym mounts** kan hjälpa men har sina egna problem
4. **Tydlig separation** mellan kärn- och valfria tjänster sparar tid
5. **Snabb feedback** är viktigt för utvecklingsflödet
