# Alice RL System 🤖

Reinforcement Learning system för Alice v2 med contextual bandits, intelligent routing, och verktygsval.

## 🚀 Quick Start

### Automatisk deployment (rekommenderat)
```bash
# Från alice-v2 root directory
cd services/rl
./quick_deploy.sh
```

### Manuell körning
```bash
# Full pipeline
python automate_rl_pipeline.py

# Med custom config
python automate_rl_pipeline.py --config config.json

# Individuella steg
python automate_rl_pipeline.py --step dataset
python automate_rl_pipeline.py --step routing
python automate_rl_pipeline.py --step eval
```

### Monitoring
```bash
# Kontinuerlig monitoring
python monitor_rl.py

# En gång check
python monitor_rl.py --once

# Custom interval
python monitor_rl.py --interval 60
```

## 📊 System Architecture

### Core Components

1. **Contextual Bandits**
   - `routing_linucb.py` - LinUCB för routing decisions
   - `tool_thompson.py` - Thompson Sampling för verktygsval
   - `cache_bandit.py` - Multi-armed bandit för cache strategi

2. **Feature Engineering**
   - `utils/features.py` - Hashing trick + z-score normalization
   - Kategoriska features: intent, language, guardian_state
   - Numeriska features: text_len, confidence, latency, cost

3. **Offline Evaluation**
   - `eval/offline_ips_eval.py` - Inverse Propensity Scoring
   - Säker policy evaluation utan production deployment
   - Confidence intervals och variance estimering

4. **Deployment Pipeline**
   - `deploy/export_policies.py` - Packa policies för deployment  
   - `deploy/promote.py` - Canary → Production deployment
   - Hot-reloading utan service restart

## 🧠 RL Models

### LinUCB Routing
- **Input**: Text features, context, user metadata
- **Arms**: micro, planner, deep
- **Exploration**: Upper Confidence Bound
- **Learning**: Ridge regression per arm

### Thompson Sampling Tools
- **Input**: Intent, available tools
- **Priors**: Beta(α=1, β=1) per intent-tool pair
- **Exploration**: Beta sampling
- **Learning**: Online Bayesian updates

### Cache Bandit
- **Input**: Query features, cache tiers
- **Strategy**: ε-greedy med decay
- **Tiers**: L1 (exact), L2 (semantic), L3 (negative)

## 📈 Performance Metrics

### Reward Function
```python
reward = 2.0 * success + 1.0 * tool_ok - 0.001 * latency_ms - 0.5 * cost_usd + 0.4 * cache_hit - 0.7 * guardian_flag
```

### Key Metrics
- **Success Rate**: Task completion rate
- **Tool Precision**: Correct tool selection rate  
- **Latency**: P95 response time
- **Cost**: Average cost per request
- **Cache Hit Rate**: Cache effectiveness

## 🔧 Configuration

### Default Config (`config.json`)
```json
{
  "dataset": {
    "min_episodes": 5,
    "lookback_days": 30
  },
  "training": {
    "routing": {"alpha": 0.5, "feature_dim": 64},
    "tools": {"alpha_prior": 1.0, "beta_prior": 1.0}
  },
  "evaluation": {
    "min_policy_value": 0.4,
    "max_variance": 0.3
  },
  "deployment": {
    "canary_traffic_pct": 5.0,
    "prod_after_canary": true
  }
}
```

## 📁 Directory Structure

```
services/rl/
├── automate_rl_pipeline.py    # Main automation script
├── quick_deploy.sh            # Fast deployment script
├── monitor_rl.py             # Performance monitoring
├── config.json               # Configuration
├── reward.py                 # Reward calculation
├── build_dataset.py          # Telemetry → Episodes
├── utils/
│   ├── io.py                 # JSONL parsing
│   └── features.py           # Feature engineering
├── bandits/
│   ├── routing_linucb.py     # LinUCB routing
│   ├── tool_thompson.py      # Thompson sampling tools
│   └── cache_bandit.py       # Cache strategy
├── eval/
│   └── offline_ips_eval.py   # IPS evaluation
├── deploy/
│   ├── export_policies.py    # Policy packaging
│   └── promote.py           # Canary/Prod deployment
├── data/                     # Generated datasets
├── models/                   # Trained policies  
├── eval_runs/               # Evaluation results
└── deploy/                  # Deployment packages
```

## 🔄 Deployment Flow

1. **Dataset Building**: Telemetry → Episodes
2. **Training**: LinUCB + Thompson Sampling + Cache bandits
3. **Offline Evaluation**: IPS safety check
4. **Packaging**: Bundle policies med metadata
5. **Canary**: 5% traffic deployment
6. **Monitoring**: Stability check (1-5 min)
7. **Production**: 100% traffic deployment

## 🚨 Safety Features

### Fallback Mechanisms
- Rule-based routing fallback
- Default tool selection
- Cache-miss handling
- Circuit breaker pattern

### Quality Gates
- Minimum episode count
- Policy value thresholds
- Variance limits
- Stability monitoring

### Rollback
```bash
# Auto-rollback vid instabilitet
python deploy/promote.py --rollback --stage canary

# Manual rollback
python deploy/promote.py --rollback --stage prod
```

## 📊 Monitoring & Alerts

### Real-time Monitoring
- Success rate drops
- Latency increases  
- Policy performance degradation
- System health checks

### Dashboards
```bash
# Live dashboard
python monitor_rl.py

# Export metrics
# See AGENTS.md for current API endpoint and port
curl [API_ENDPOINT]/rl-status
```

## 🧪 Testing

### Unit Tests
```bash
cd services/rl
python -m pytest tests/ -v
```

### Integration Tests
```bash
# Test med riktig telemetri data
python automate_rl_pipeline.py --dry-run
```

### A/B Testing
Canary deployment ger naturlig A/B test mellan gamla och nya policies.

## 🐛 Troubleshooting

### Common Issues

**No telemetry data**
```bash
# Check telemetry file
ls -la services/orchestrator/telemetry.jsonl

# Generate demo data
./quick_deploy.sh  # Creates demo telemetry
```

**Policy loading failed**
```bash
# Check policy files
ls -la services/orchestrator/src/policies/live/

# Validate package
python deploy/export_policies.py --validate-only --routing models/routing_policy.json
```

**Performance degradation**
```bash
# Monitor performance
python monitor_rl.py --once

# Rollback if needed
python deploy/promote.py --rollback --stage prod
```

### Debug Commands
```bash
# Verbose logging
python automate_rl_pipeline.py --step eval 2>&1 | tee debug.log

# Check orchestrator logs
docker-compose logs orchestrator | tail -50
```

## 🎯 Performance Targets

### Current State (Step 8.5)
- Tool Precision: 54.7% → 85%+
- P95 Latency: 9580ms → <900ms
- Routing Precision: 40% → 100%
- Cache Hit Rate: 10% → 60%+

### RL Improvements
- **Intelligent Routing**: Context-aware micro/planner/deep selection
- **Smart Tool Selection**: Intent-based tool matching
- **Adaptive Caching**: Multi-tier cache optimization
- **Continuous Learning**: Online policy updates

## 🤝 Contributing

1. Kör tests innan commit
2. Uppdatera metrics efter changes
3. Dokumentera nya features
4. Följ naming conventions

## 📚 References

- [LinUCB Paper](https://arxiv.org/abs/1003.0146) - Contextual bandits
- [Thompson Sampling](https://en.wikipedia.org/wiki/Thompson_sampling) - Bayesian exploration
- [IPS Evaluation](https://arxiv.org/abs/1112.1984) - Offline policy evaluation

---
**Alice RL System** - Making Alice helt jävla grym! 🚀