# Mänsklig A/B-utvärdering

1. Generera kandidater: python tools/ab_runner.py
2. Låt panel bedöma varje rad i ab_candidates.jsonl och skapa en fil eval/human/judgments.jsonl med fält:
   {"prompt": "...", "winner": "A"|"B", "notes": "valfritt"}
3. Aggreggera: python eval/human/aggregate.py → eval/human/human_report.json