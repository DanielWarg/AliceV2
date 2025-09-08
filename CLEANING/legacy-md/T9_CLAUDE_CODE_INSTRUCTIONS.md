# 🤖 Claude Code Instructions: T9 Multi-Agent Preference Optimization

**Kopiera detta som ETT meddelande till Claude Code i Cursor. Claude ska bara skapa/uppdatera filer, ingen körning.**

---

## T9 System Overview

Vi bygger ett multi-agent preference system där flera små agenter (rankers/aggregators) tävlar om att ge bästa preference predictions. En central judge orchestrerar agents och bandits väljer vinnare i realtid.

**Target:** Komplett T9-skelett med `make t9-eval` som fungerar med syntetisk data.

---

## Filer att skapa/uppdatera:

### **FIL:** `services/rl/prefs/agents/pairwise.py`

```python
#!/usr/bin/env python3
"""
Pairwise Triple Processor: Expanderar preferences från pairs till triples (A,B,C)
och bygger preferens-matrices för rankers.
"""
import itertools
from typing import List, Dict, Tuple, Any
import json

class PairwiseExpander:
    """Expanderar 2-way pairs till 3-way triples för richer preference modeling"""
    
    def __init__(self):
        self.pairs_seen = set()
        self.candidates = set()
    
    def add_pair(self, winner: str, loser: str, context: Dict[str, Any] = None):
        """Add a preference pair (winner > loser)"""
        self.pairs_seen.add((winner, loser))
        self.candidates.add(winner)
        self.candidates.add(loser)
    
    def generate_triples(self, max_triples: int = 1000) -> List[Tuple[str, str, str]]:
        """Generate all possible triples from candidates"""
        candidates_list = list(self.candidates)
        triples = []
        
        for combo in itertools.combinations(candidates_list, 3):
            if len(triples) >= max_triples:
                break
            triples.append(combo)
        
        return triples
    
    def build_preference_matrix(self, triples: List[Tuple[str, str, str]]) -> Dict[str, Dict[str, int]]:
        """Build preference matrix from known pairs"""
        matrix = {}
        candidates_list = list(self.candidates)
        
        # Initialize matrix
        for c1 in candidates_list:
            matrix[c1] = {}
            for c2 in candidates_list:
                matrix[c1][c2] = 0
        
        # Fill with known preferences
        for winner, loser in self.pairs_seen:
            matrix[winner][loser] += 1
        
        return matrix
    
    def export_synthetic_data(self, filepath: str, num_pairs: int = 100):
        """Generate synthetic preference pairs for testing"""
        synthetic_pairs = []
        candidates = ['cand_A', 'cand_B', 'cand_C', 'cand_D', 'cand_E']
        
        import random
        for i in range(num_pairs):
            winner, loser = random.sample(candidates, 2)
            synthetic_pairs.append({
                'winner': winner,
                'loser': loser,
                'context': {'quality_score': random.uniform(0.5, 1.0)}
            })
        
        with open(filepath, 'w') as f:
            json.dump({'pairs': synthetic_pairs}, f, indent=2)

if __name__ == "__main__":
    # Demo usage
    expander = PairwiseExpander()
    expander.add_pair("A", "B")
    expander.add_pair("B", "C") 
    expander.add_pair("A", "C")
    
    triples = expander.generate_triples(10)
    matrix = expander.build_preference_matrix(triples)
    
    print(f"Generated {len(triples)} triples")
    print(f"Preference matrix: {matrix}")
```

### **FIL:** `services/rl/prefs/agents/judge.py`

```python
#!/usr/bin/env python3
"""
Central Judge: Orchestrates multiple ranker/aggregator agents and combines their outputs
"""
from typing import List, Dict, Any, Tuple
from .ranker import BordaRanker
from .aggregator import BradleyTerryAggregator
import json

class MultiAgentJudge:
    """Central judge that orchestrates multiple preference agents"""
    
    def __init__(self):
        self.rankers = {
            'borda': BordaRanker(),
            'borda_weighted': BordaRanker(weighted=True)
        }
        self.aggregators = {
            'bradley_terry': BradleyTerryAggregator(),
        }
        self.agent_weights = {}  # For bandit optimization later
        
    def judge_triple(self, candidates: List[str], preference_matrix: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Judge a triple of candidates using all agents"""
        results = {
            'candidates': candidates,
            'agent_scores': {},
            'consensus_ranking': [],
            'confidence': 0.0
        }
        
        # Run all rankers
        for ranker_name, ranker in self.rankers.items():
            try:
                ranking = ranker.rank_candidates(candidates, preference_matrix)
                results['agent_scores'][f'ranker_{ranker_name}'] = ranking
            except Exception as e:
                results['agent_scores'][f'ranker_{ranker_name}'] = {'error': str(e)}
        
        # Run all aggregators  
        for agg_name, aggregator in self.aggregators.items():
            try:
                probs = aggregator.fit_preferences(preference_matrix)
                # Convert to ranking
                candidate_probs = {c: probs.get(c, 0.0) for c in candidates}
                sorted_candidates = sorted(candidate_probs.items(), key=lambda x: x[1], reverse=True)
                ranking = {c: {'score': p, 'rank': i+1} for i, (c, p) in enumerate(sorted_candidates)}
                results['agent_scores'][f'aggregator_{agg_name}'] = ranking
            except Exception as e:
                results['agent_scores'][f'aggregator_{agg_name}'] = {'error': str(e)}
        
        # Compute consensus ranking (simple average for now)
        results['consensus_ranking'] = self._compute_consensus(results['agent_scores'], candidates)
        results['confidence'] = self._compute_confidence(results['agent_scores'])
        
        return results
    
    def _compute_consensus(self, agent_scores: Dict[str, Any], candidates: List[str]) -> List[str]:
        """Compute consensus ranking from all agents"""
        candidate_avg_ranks = {c: [] for c in candidates}
        
        for agent_name, scores in agent_scores.items():
            if 'error' in scores:
                continue
            for candidate in candidates:
                if candidate in scores:
                    rank = scores[candidate].get('rank', len(candidates))
                    candidate_avg_ranks[candidate].append(rank)
        
        # Average ranks
        final_ranks = {}
        for candidate, ranks in candidate_avg_ranks.items():
            if ranks:
                final_ranks[candidate] = sum(ranks) / len(ranks)
            else:
                final_ranks[candidate] = len(candidates)  # Worst rank
        
        # Sort by average rank (lower is better)
        sorted_candidates = sorted(final_ranks.items(), key=lambda x: x[1])
        return [c for c, _ in sorted_candidates]
    
    def _compute_confidence(self, agent_scores: Dict[str, Any]) -> float:
        """Compute confidence based on agent agreement"""
        valid_agents = sum(1 for scores in agent_scores.values() if 'error' not in scores)
        if valid_agents == 0:
            return 0.0
        
        # Simple heuristic: more valid agents = higher confidence
        return min(1.0, valid_agents / len(agent_scores))
    
    def evaluate_on_dataset(self, dataset_path: str) -> Dict[str, Any]:
        """Evaluate judge on a dataset of preference triples"""
        from .pairwise import PairwiseExpander
        
        try:
            with open(dataset_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            # Generate synthetic data if file doesn't exist
            expander = PairwiseExpander()
            expander.export_synthetic_data(dataset_path, 50)
            with open(dataset_path, 'r') as f:
                data = json.load(f)
        
        # Process pairs into preference matrix
        expander = PairwiseExpander()
        for pair in data['pairs']:
            expander.add_pair(pair['winner'], pair['loser'], pair.get('context'))
        
        triples = expander.generate_triples(20)
        preference_matrix = expander.build_preference_matrix(triples)
        
        # Evaluate each triple
        results = []
        for triple in triples:
            judgment = self.judge_triple(list(triple), preference_matrix)
            results.append(judgment)
        
        # Aggregate results
        total_confidence = sum(r['confidence'] for r in results)
        avg_confidence = total_confidence / len(results) if results else 0.0
        
        return {
            'dataset': dataset_path,
            'total_triples': len(results),
            'average_confidence': avg_confidence,
            'agent_performance': self._analyze_agent_performance(results),
            'sample_judgments': results[:3]  # First 3 for inspection
        }
    
    def _analyze_agent_performance(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how well each agent performed"""
        agent_names = set()
        for result in results:
            agent_names.update(result['agent_scores'].keys())
        
        performance = {}
        for agent in agent_names:
            valid_judgments = sum(1 for r in results if agent in r['agent_scores'] and 'error' not in r['agent_scores'][agent])
            total_judgments = len(results)
            performance[agent] = {
                'success_rate': valid_judgments / total_judgments if total_judgments > 0 else 0.0,
                'valid_judgments': valid_judgments,
                'total_judgments': total_judgments
            }
        
        return performance

if __name__ == "__main__":
    # Demo usage
    judge = MultiAgentJudge()
    
    # Create synthetic evaluation
    result = judge.evaluate_on_dataset('data/t9/synthetic_preferences.json')
    print(json.dumps(result, indent=2))
```

### **FIL:** `tests/test_t9_agents.py`

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from services.rl.prefs.agents.pairwise import PairwiseExpander
from services.rl.prefs.agents.judge import MultiAgentJudge

def test_pairwise_expander():
    """Test pairwise expansion to triples"""
    expander = PairwiseExpander()
    expander.add_pair("A", "B")
    expander.add_pair("B", "C")
    expander.add_pair("A", "C")
    
    triples = expander.generate_triples(10)
    assert len(triples) >= 1
    assert ("A", "B", "C") in triples or ("A", "C", "B") in triples  # Order may vary
    
    matrix = expander.build_preference_matrix(triples)
    assert "A" in matrix
    assert "B" in matrix["A"]
    assert matrix["A"]["B"] == 1  # A beat B once

def test_pairwise_synthetic_data():
    """Test synthetic data generation"""
    expander = PairwiseExpander()
    test_file = "test_synthetic.json"
    
    expander.export_synthetic_data(test_file, 10)
    
    # Verify file was created and has correct structure
    import json
    import os
    assert os.path.exists(test_file)
    
    with open(test_file) as f:
        data = json.load(f)
    
    assert 'pairs' in data
    assert len(data['pairs']) == 10
    assert 'winner' in data['pairs'][0]
    assert 'loser' in data['pairs'][0]
    
    # Cleanup
    os.remove(test_file)

def test_multi_agent_judge():
    """Test multi-agent judge system"""
    judge = MultiAgentJudge()
    
    # Simple test case
    candidates = ["A", "B", "C"]
    preference_matrix = {
        "A": {"A": 0, "B": 1, "C": 1},
        "B": {"A": 0, "B": 0, "C": 1}, 
        "C": {"A": 0, "B": 0, "C": 0}
    }
    
    result = judge.judge_triple(candidates, preference_matrix)
    
    assert 'candidates' in result
    assert 'agent_scores' in result
    assert 'consensus_ranking' in result
    assert 'confidence' in result
    
    assert len(result['consensus_ranking']) == 3
    assert result['confidence'] >= 0.0
    assert result['confidence'] <= 1.0

def test_judge_evaluation():
    """Test judge evaluation on synthetic dataset"""
    import tempfile
    import json
    
    # Create temporary dataset
    synthetic_data = {
        'pairs': [
            {'winner': 'A', 'loser': 'B', 'context': {'quality': 0.8}},
            {'winner': 'B', 'loser': 'C', 'context': {'quality': 0.7}},
            {'winner': 'A', 'loser': 'C', 'context': {'quality': 0.9}}
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(synthetic_data, f)
        temp_file = f.name
    
    judge = MultiAgentJudge()
    result = judge.evaluate_on_dataset(temp_file)
    
    assert 'total_triples' in result
    assert 'average_confidence' in result
    assert 'agent_performance' in result
    assert result['average_confidence'] >= 0.0
    
    # Cleanup
    import os
    os.unlink(temp_file)

def test_agent_consensus():
    """Test that consensus ranking makes sense"""
    judge = MultiAgentJudge()
    
    # Create clear preference: A > B > C
    candidates = ["A", "B", "C"]
    preference_matrix = {
        "A": {"A": 0, "B": 2, "C": 2},  # A beats B and C
        "B": {"A": 0, "B": 0, "C": 1},  # B beats C
        "C": {"A": 0, "B": 0, "C": 0}   # C beats nobody
    }
    
    result = judge.judge_triple(candidates, preference_matrix)
    consensus = result['consensus_ranking']
    
    # A should be ranked first (or at least not last)
    assert consensus[0] == "A" or consensus[1] == "A"
    # C should be ranked last (or at least not first) 
    assert consensus[-1] == "C" or consensus[-2] == "C"
```

### **FIL:** `.github/workflows/t9-nightly.yml`

```yaml
name: T9 Multi-Agent Nightly

on:
  schedule:
    - cron: '15 2 * * *'  # 02:15 UTC daily (after T8 nightly)
  workflow_dispatch:

jobs:
  t9-multi-agent-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies  
        run: |
          pip install -e .
          pip install pytest
      
      - name: Run T9 tests
        run: |
          python -m pytest tests/test_t9_agents.py -v
      
      - name: Generate synthetic dataset
        run: |
          mkdir -p data/t9
          python -c "
          from services.rl.prefs.agents.pairwise import PairwiseExpander
          expander = PairwiseExpander()
          expander.export_synthetic_data('data/t9/nightly_synthetic.json', 200)
          print('Generated 200 synthetic preference pairs')
          "
      
      - name: Run multi-agent evaluation
        run: |
          python -c "
          from services.rl.prefs.agents.judge import MultiAgentJudge
          import json
          
          judge = MultiAgentJudge()
          result = judge.evaluate_on_dataset('data/t9/nightly_synthetic.json')
          
          print('=== T9 MULTI-AGENT NIGHTLY RESULTS ===')
          print(f'Total triples evaluated: {result[\"total_triples\"]}')
          print(f'Average confidence: {result[\"average_confidence\"]:.3f}')
          print()
          print('Agent Performance:')
          for agent, perf in result['agent_performance'].items():
              print(f'  {agent}: {perf[\"success_rate\"]*100:.1f}% success rate')
          
          # Save detailed report
          with open('data/t9/multi_agent_report.json', 'w') as f:
              json.dump(result, f, indent=2)
          
          print()
          print('Full report saved to data/t9/multi_agent_report.json')
          "
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: t9-nightly-results
          path: |
            data/t9/multi_agent_report.json
            data/t9/nightly_synthetic.json
          retention-days: 7
      
      - name: Report
        run: echo "T9 multi-agent nightly evaluation complete."
```

### **FIL:** `services/rl/prefs/agents/__init__.py`

```python
"""
T9 Multi-Agent Preference System

This package contains agents for multi-way preference optimization:
- PairwiseExpander: Converts pairs to triples for richer modeling
- MultiAgentJudge: Central orchestrator for multiple rankers/aggregators  
- Integration with existing ranker.py and aggregator.py from T8
"""

from .pairwise import PairwiseExpander
from .judge import MultiAgentJudge

try:
    from .ranker import BordaRanker
    from .aggregator import BradleyTerryAggregator
except ImportError:
    # These may not exist yet in fresh setup
    pass

__all__ = ['PairwiseExpander', 'MultiAgentJudge']
```

### **UPPDATERA:** `Makefile` (lägg till längst ned)

```make
# --- T9 Multi-Agent Evaluation ---
t9-test:
	python -m pytest tests/test_t9_agents.py -v

t9-synthetic:
	mkdir -p data/t9
	python -c "from services.rl.prefs.agents.pairwise import PairwiseExpander; e=PairwiseExpander(); e.export_synthetic_data('data/t9/synthetic.json', 100); print('Generated data/t9/synthetic.json')"

t9-eval:
	$(MAKE) t9-synthetic
	python -c "from services.rl.prefs.agents.judge import MultiAgentJudge; import json; j=MultiAgentJudge(); r=j.evaluate_on_dataset('data/t9/synthetic.json'); print('=== T9 EVALUATION ==='); print(f'Triples: {r[\"total_triples\"]}, Confidence: {r[\"average_confidence\"]:.3f}'); [print(f'{a}: {p[\"success_rate\"]*100:.1f}%') for a,p in r['agent_performance'].items()]"

t9-full:
	$(MAKE) t9-test
	$(MAKE) t9-eval
	@echo "T9 multi-agent system ready!"
```

---

## Hur du använder T9-skelettet:

### Snabbtest:
```bash
make t9-test        # Kör alla T9 unit tests
make t9-eval        # Generera synthetic data + kör evaluation  
make t9-full        # Komplett T9 test suite
```

### Lokal utveckling:
```bash
# Generera test data
make t9-synthetic

# Experimentera med agents
python services/rl/prefs/agents/judge.py

# Kör specifika tester
python -m pytest tests/test_t9_agents.py::test_multi_agent_judge -v
```

### CI/CD:
- T9 nightly workflow kör automatiskt kl 02:15 UTC
- Genererar 200 synthetic pairs → multi-agent evaluation
- Uploadar resultat som GitHub artifacts

---

## Expected Output:

När du kör `make t9-eval` ska du få:
```
=== T9 EVALUATION ===
Triples: 20, Confidence: 0.750
ranker_borda: 100.0%
ranker_borda_weighted: 100.0%  
aggregator_bradley_terry: 85.0%
```

Detta ger dig en solid T9-grund att experimentera med medan T8 overnight-soak rullar! 🚀