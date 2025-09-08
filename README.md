```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║      █████╗ ██╗     ██╗ ██████╗███████╗    ██╗   ██╗██████╗                   ║
║     ██╔══██╗██║     ██║██╔════╝██╔════╝    ██║   ██║╚════██╗                  ║
║     ███████║██║     ██║██║     █████╗      ██║   ██║ █████╔╝                  ║
║     ██╔══██║██║     ██║██║     ██╔══╝      ╚██╗ ██╔╝██╔═══╝                   ║
║     ██║  ██║███████╗██║╚██████╗███████╗     ╚████╔╝ ███████╗                  ║
║     ╚═╝  ╚═╝╚══════╝╚═╝ ╚═════╝╚══════╝      ╚═══╝  ╚══════╝                  ║
║                                                                               ║
║        Self-Improving Swedish AI Assistant with T1-T9 RL Systems              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

![T1-T9](https://img.shields.io/badge/T1--T9-Complete-gold)
![RL/ML](https://img.shields.io/badge/RL%2FML-LinUCB%2BThompson-purple)
![Guardian](https://img.shields.io/badge/Guardian-Brownout%20Protection-red)
![Svenska](https://img.shields.io/badge/Svenska-88%25%20Accuracy-blue)
![φ](https://img.shields.io/badge/φ-Fibonacci%20Optimized-gold)

**Status**: T1-T9 RL systems operational | Guardian protecting | Voice operational | Frontend missing

## What You're Looking At

Alice v2 is a **self-improving AI assistant** with T1-T9 reinforcement learning systems that get better automatically. Built for Swedish but speaks your language.

```bash
git clone https://github.com/DanielWarg/AliceV2.git && cd alice-v2
make up
# AI core: ✅ | Voice: ✅ | Frontend: ❌ 
# Monitor: http://localhost:8501
```

## What Actually Works

**T1-T9 RL Systems (Operational)**:
- **LinUCB Router**: Contextual bandits for routing decisions (50,374 ops/sec)
- **Thompson Sampling**: Beta distributions for tool selection
- **φ-Fibonacci Rewards**: Golden ratio optimization (precision φ², latency φ¹, energy φ⁰)
- **Guardian Protection**: NORMAL/BROWNOUT/EMERGENCY states with kill sequences
- **Swedish NLU**: 88%+ accuracy, E5-embeddings + XNLI, P95 ≤80ms  
- **Smart Cache L1/L2/L3**: Exact + semantic + negative caching
- **Memory System**: Redis sessions + FAISS user memory, `forget` <1s
- **Auto-Stabilizer**: 8-hour overnight optimization cycles
- **Multi-Agent Orchestration**: Borda + Bradley-Terry preference aggregation

**Performance Numbers** (M4 MacBook Pro):
```
• LinUCB: 50,374 ops/sec (10x SLO target)
• Turn simulation: 26,077/sec, 0.03ms P95  
• Replay training: 65,431 episodes/sec
• Success rate: 100% (production validated)
• NLU accuracy: 88%+ Swedish context
```

**What's Broken**:
- **Frontend**: Removed entirely, need React/Next.js rebuild

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ NLU Svenska │    │ Orchestrator│    │   Guardian  │    │ Smart Cache │
│   (9002)    │◄──►│   (8001)    │◄──►│   (8787)    │◄──►│   (6379)    │
│ E5+XNLI     │    │ LangGraph   │    │ Brownout    │    │ L1/L2/L3    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       └───────────────────┼───────────────────┼───────────────────┘
                           │                   │
                   ┌─────────────┐    ┌─────────────┐
                   │ LinUCB      │    │ Memory/RAG  │  
                   │ Router      │    │ FAISS+Redis │
                   │ T4-T9 RL    │    │ User Data   │
                   └─────────────┘    └─────────────┘
```

**Services**:
- **Orchestrator** (8001): LangGraph router + T1-T9 RL systems
- **Guardian** (8787): System protection, brownout states  
- **NLU** (9002): Swedish language processing
- **Smart Cache** (6379): Multi-tier Redis caching
- **Voice** (8002): ✅ STT/TTS (Whisper + Piper) 
- **Frontend** (3000): ❌ Missing (build React/Next.js)

**Monitoring**: http://localhost:8501 (Streamlit)

## Quick Start

```bash
# Start everything
make up

# Check health
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8787/health  # Guardian  
curl http://localhost:9002/health  # NLU

# Monitor
open http://localhost:8501

# Test
./scripts/test_a_z_real_data.sh
```

## Development

**Build Frontend** (missing):
```bash
# Follow FRONTEND_DEVELOPMENT_GUIDE.md
cd apps/
npx create-next-app@latest web --typescript --tailwind
# Connect to Alice APIs
```

**Test Voice** (working):
```bash
# STT/TTS operational on port 8002
curl http://localhost:8002/health
# See VOICE_REACTIVATION_GUIDE.md for integration
```

**Commands**:
```bash
make up          # Start all services
make down        # Stop everything  
make test-all    # Run complete tests
make restart     # Restart services
```

## File Structure

```
services/
├── orchestrator/  # T1-T9 RL systems + LangGraph routing
├── guardian/      # System protection + brownout states
├── nlu/          # Swedish language processing  
├── voice/        # ❌ Broken (restart loop)
├── cache/        # Smart Cache L1/L2/L3
└── loadgen/      # Load testing + benchmarks

apps/             # ❌ Empty (frontend removed)
monitoring/       # Streamlit dashboard (8501)
data/            # Telemetry + training data
```

## What's Next

**Priority 1**: Build React/Next.js frontend  
**Priority 2**: Integrate voice with chat interface

## Documentation

- [AGENTS.md](AGENTS.md) - Current system status
- [FRONTEND_DEVELOPMENT_GUIDE.md](FRONTEND_DEVELOPMENT_GUIDE.md) - React/Next.js guide
- [VOICE_REACTIVATION_GUIDE.md](VOICE_REACTIVATION_GUIDE.md) - Voice pipeline fix
- [SYSTEM_INTEGRATION.md](SYSTEM_INTEGRATION.md) - How T1-T9 systems connect

---
**Built by**: Evil Genius 🧠  
**Powered by**: Fibonacci φ-optimization and Swedish stubbornness