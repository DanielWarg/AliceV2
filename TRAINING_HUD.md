# 🧮 Alice v2 Training HUD

En modern, interaktiv chat-liknande interface för att monitora alla träningsaktiviteter i Alice v2-systemet.

## 🎯 Features

### Real-time Chat Interface
- **Live chat-feed** med meddelanden från alla aktiva träningssessions
- **Färgkodade meddelanden** (info, success, warning, error)
- **Session badges** för att identifiera källa  
- **Tidsstämplar** för varje meddelande

### Multi-Training Support
- **🧮 Fibonacci Optimization** - Golden ratio performance optimization (φ=1.618)
- **🔄 Fibonacci Training Loop** - Multi-phase Fibonacci training pipeline
- **🤖 RL Pipeline** - Reinforcement learning automation
- **💾 Cache Bandit RL** - Cache optimization reinforcement learning

### Progress Tracking
- **Real-time metrics** för varje träningssession
- **Session status** (starting, running, completed, failed)
- **Uptime tracking** med minuter:sekunder format
- **Message counters** för aktivitetsnivå
- **Export metrics** till JSON för extern analys

### Interactive Controls
- **Start/stop sessions** med enkla kommandon
- **Status queries** för detaljerad sessioninfo
- **Batch operations** (stop-all, clear chat)
- **Auto-start** från kommandorad

## 🚀 Användning

### Starta HUD
```bash
# Grundläggande start
python training_hud.py

# Auto-starta träningar
python training_hud.py --auto-start fibonacci,rl_pipeline

# Custom refresh rate
python training_hud.py --refresh-rate 0.5
```

### Interaktiva Kommandon

Efter att HUD startat, tryck `Ctrl+C` för att komma till kommandoprompten:

```bash
training-hud> help                    # Visa alla kommandon
training-hud> start fibonacci         # Starta Fibonacci träning
training-hud> start rl_pipeline       # Starta RL pipeline
training-hud> status                  # Visa detaljerad session-status
training-hud> stop fibonacci_123456   # Stoppa specifik session
training-hud> stop-all                # Stoppa alla sessions
training-hud> metrics                 # Exportera metrics till JSON
training-hud> clear                   # Rensa chat-historik
training-hud> quit                    # Avsluta HUD
```

## 📊 Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🧮 Alice v2 Training HUD  •  2 aktiva / 3 totalt          │
├─────────────────────┬───────────────────────────────────────┤
│ 📊 Aktiva Sessions  │ 💬 Training Chat                      │
│                     │                                       │
│ fibonacci_140521    │ 14:05:23 [fibonacci_140521] 🚀 Startar│
│ ● Running  02:15    │ 14:05:25 [fibonacci_140521] Phase 1...│  
│ 🧮 Fibonacci Opt    │ 14:05:28 [rl_140522    ] 🤖 RL start │
│                     │ 14:05:30 [fibonacci_140521] ✅ Success│
│ rl_140522          │ 14:05:32 [rl_140522    ] Training... │
│ ● Starting  00:12   │                                       │
│ 🤖 RL Pipeline      │                                       │
├─────────────────────┴───────────────────────────────────────┤
│ 🎮 start <type> | stop <name> | status | metrics | quit    │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Teknisk Implementation

### Session Monitoring
- **Subprocess management** för att köra träningsskript
- **Real-time stdout/stderr capture** med live parsing
- **Thread-based monitoring** för att inte blockera UI
- **Process lifecycle management** med clean shutdown

### Chat System
- **Ring buffer** för meddelanden (max 50 per session)
- **Level-based färgkodning** (info/success/warning/error)
- **Timestamp syncing** mellan olika sessions
- **Message aggregation** från alla aktiva sessions

### Enterprise Integration
- **JSON metrics export** kompatibel med befintligt monitoring
- **Session telemetry** med uptime och performance data
- **Standards compliance** med Alice v2 logging format
- **Schema validation** för exported data

## 🎯 Use Cases

### Utveckling
- **Parallel training** av flera algorithms samtidigt
- **Real-time debugging** med live chat-feed
- **Performance comparison** mellan träningstyper
- **Quick start/stop** för iterativ utveckling

### Monitoring
- **Production training oversight** med live status
- **Historical session tracking** via metrics export
- **Alert system** genom färgkodade meddelanden
- **Uptime monitoring** för långkörande träningar

### Research
- **Multi-algorithm comparison** side-by-side
- **Training pipeline orchestration** för experiments
- **Data collection** via structured metrics export
- **Session replay** genom sparad chat-historik

## 🚀 Integration med Alice v2

### Befintliga System
- **Kompatibel** med alla befintliga träningsskript
- **Använder** standard Alice v2 logging format
- **Integrerar** med enterprise monitoring via JSON export
- **Respekterar** virtual environment och dependencies

### Future Enhancements
- **CLI interface** för remote monitoring
- **Database integration** för persistent session history
- **Alert webhooks** för kritiska events
- **ML model integration** för predictive monitoring

---

**💡 Pro tip:** Använd `--auto-start fibonacci,rl_pipeline` för att starta flera träningar samtidigt och jämföra deras prestanda i real-time!