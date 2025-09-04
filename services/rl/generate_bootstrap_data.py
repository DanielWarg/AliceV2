#!/usr/bin/env python3
"""
Generate realistic bootstrap data for Alice RL training.
Skapar realistisk syntetisk data baserat på Alice's design patterns.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger(__name__)


class AliceBootstrapGenerator:
    """Genererar realistisk bootstrap data för Alice RL training."""

    def __init__(self):
        # Realistiska intent patterns baserat på Alice's domän
        self.intents = [
            ("greeting", 0.15, ["hej", "hallo", "god morgon", "tjena"]),
            ("weather", 0.12, ["väder", "regn", "temperatur", "prognos"]),
            (
                "calculation",
                0.08,
                ["räkna", "beräkna", "plus", "minus", "multiplicera"],
            ),
            ("search", 0.10, ["sök", "hitta", "googla", "leta efter"]),
            ("complex_query", 0.20, ["förklara", "analysera", "jämför", "sammanfatta"]),
            ("time", 0.05, ["tid", "klocka", "datum", "idag"]),
            ("help", 0.08, ["hjälp", "support", "vad kan du", "hur fungerar"]),
            ("translation", 0.07, ["översätt", "translate", "engelska", "svenska"]),
            ("creative", 0.10, ["skriv", "skapa", "generera", "dikta"]),
            ("other", 0.05, ["annat", "övrigt", "diverse"]),
        ]

        # Route performance baserat på complexity
        self.route_preferences = {
            "greeting": {"micro": 0.9, "planner": 0.1, "deep": 0.0},
            "weather": {"micro": 0.3, "planner": 0.6, "deep": 0.1},
            "calculation": {"micro": 0.7, "planner": 0.3, "deep": 0.0},
            "search": {"micro": 0.2, "planner": 0.7, "deep": 0.1},
            "complex_query": {"micro": 0.1, "planner": 0.4, "deep": 0.5},
            "time": {"micro": 0.8, "planner": 0.2, "deep": 0.0},
            "help": {"micro": 0.6, "planner": 0.3, "deep": 0.1},
            "translation": {"micro": 0.2, "planner": 0.6, "deep": 0.2},
            "creative": {"micro": 0.0, "planner": 0.3, "deep": 0.7},
            "other": {"micro": 0.4, "planner": 0.4, "deep": 0.2},
        }

        # Tool mapping per intent
        self.intent_tools = {
            "greeting": ["none"],
            "weather": ["weather.lookup", "location.get"],
            "calculation": ["calculator", "math.solver"],
            "search": ["search", "web.lookup"],
            "complex_query": ["search", "knowledge.query", "reasoning"],
            "time": ["time.current", "calendar"],
            "help": ["none", "help.system"],
            "translation": ["translate", "language.detect"],
            "creative": ["text.generate", "creative.write"],
            "other": ["none", "search"],
        }

        # Baseline performance per route (success rates)
        self.route_baselines = {
            "micro": {"success": 0.85, "latency_base": 150, "cost_base": 0.001},
            "planner": {"success": 0.78, "latency_base": 450, "cost_base": 0.003},
            "deep": {"success": 0.72, "latency_base": 800, "cost_base": 0.005},
        }

    def generate_realistic_episode(
        self, timestamp: datetime, episode_id: int
    ) -> Dict[str, Any]:
        """Generera en realistisk episode."""

        # Välj intent baserat på sannolikheter
        intent_name = random.choices(
            [intent[0] for intent in self.intents],
            weights=[intent[1] for intent in self.intents],
        )[0]

        # Generera text baserat på intent
        intent_words = next(
            intent[2] for intent in self.intents if intent[0] == intent_name
        )
        text_length = (
            random.choice(
                [
                    random.randint(5, 20),  # Korta frågor (70%)
                    random.randint(20, 60),  # Medel frågor (25%)
                    random.randint(60, 150),  # Långa frågor (5%)
                ]
            )
            if random.random() < 0.95
            else random.randint(60, 150)
        )

        # Välj optimal route för denna intent
        route_probs = self.route_preferences[intent_name]
        optimal_route = max(route_probs.keys(), key=lambda k: route_probs[k])

        # Simulera suboptimal routing (realistic mistake rate)
        if random.random() < 0.15:  # 15% suboptimal routing
            route = random.choice([r for r in route_probs.keys() if r != optimal_route])
        else:
            route = optimal_route

        # Route performance
        route_perf = self.route_baselines[route]
        intent_fit = route_probs[route]  # Hur bra route passar intent

        # Success baserat på route + intent fit + lite noise
        base_success = route_perf["success"] * intent_fit
        success = 1 if random.random() < (base_success + random.gauss(0, 0.1)) else 0

        # Latency baserat på route + text_length + success
        latency_base = route_perf["latency_base"]
        latency_penalty = 1.5 if success == 0 else 1.0  # Failures take longer
        length_factor = 1 + (text_length / 100) * 0.3  # Longer text = more time
        latency = int(
            latency_base * latency_penalty * length_factor * random.gauss(1.0, 0.2)
        )
        latency = max(50, latency)  # Minimum 50ms

        # Cost baserat på route + latency
        cost = (
            route_perf["cost_base"]
            * (1 + latency / 1000 * 0.1)
            * random.gauss(1.0, 0.1)
        )
        cost = max(0.0001, cost)

        # Tool selection
        available_tools = self.intent_tools[intent_name]
        if len(available_tools) == 1:
            selected_tool = available_tools[0]
            tool_success = success  # Perfect tool selection when only one choice
        else:
            # Simulera tool selection accuracy
            if random.random() < 0.8:  # 80% correct tool selection
                selected_tool = available_tools[0]  # First is usually optimal
                tool_success = success
            else:
                selected_tool = random.choice(available_tools[1:])  # Suboptimal
                tool_success = max(
                    0, success - random.choice([0, 1])
                )  # Might reduce success

        # Cache hit simulation
        cache_probability = {
            "greeting": 0.7,  # Greetings cache well
            "time": 0.3,  # Time changes frequently
            "weather": 0.4,  # Weather updates regularly
            "calculation": 0.8,  # Math results cache well
            "search": 0.2,  # Search is usually unique
            "other": 0.3,
        }.get(intent_name, 0.3)

        cache_hit = 1 if random.random() < cache_probability else 0

        # Guardian state (mostly normal, sometimes alert)
        guardian_states = ["NORMAL", "NORMAL", "NORMAL", "ALERT", "NORMAL"]
        guardian_state = random.choice(guardian_states)
        guardian_penalty = 1 if guardian_state == "ALERT" else 0

        # Language (svenska dominant)
        lang = random.choices(["sv", "en", "other"], weights=[0.8, 0.15, 0.05])[0]

        # Intent confidence (realistic distribution)
        intent_confidence = (
            random.betavariate(3, 1) * 0.9 + 0.1
        )  # Skewed toward high confidence

        return {
            "episode_id": episode_id,
            "timestamp": timestamp.isoformat(),
            "intent": intent_name,
            "lang": lang,
            "text": f"Sample {intent_name} query with {text_length} chars",
            "text_len": text_length,
            "word_count": max(1, text_length // 6),  # Rough estimate
            "intent_confidence": round(intent_confidence, 3),
            "route": route,
            "optimal_route": optimal_route,
            "route_propensity": route_probs[route],  # Logging policy propensity
            "tool": selected_tool,
            "optimal_tool": available_tools[0] if available_tools else "none",
            "tool_propensity": 0.8 if selected_tool == available_tools[0] else 0.2,
            "success": success,
            "tool_success": tool_success,
            "latency_ms": latency,
            "cost_usd": round(cost, 6),
            "cache_hit": cache_hit,
            "guardian_state": guardian_state,
            "guardian_penalty": guardian_penalty,
        }

    def generate_bootstrap_dataset(
        self, num_episodes: int = 1000, days_back: int = 30, daily_pattern: bool = True
    ) -> List[Dict[str, Any]]:
        """Generera komplett bootstrap dataset."""

        episodes = []
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        # Fördela episodes över tid
        for i in range(num_episodes):
            # Tidsstämpel med realistisk fördelning
            if daily_pattern:
                # Simulera verkliga användningsmönster
                day_offset = random.uniform(0, days_back)
                hour = random.choices(
                    range(24),
                    weights=[
                        1,
                        1,
                        1,
                        1,
                        1,
                        2,
                        3,
                        5,
                        8,
                        10,
                        12,
                        14,
                        15,
                        14,
                        12,
                        10,
                        8,
                        6,
                        4,
                        3,
                        2,
                        1,
                        1,
                        1,
                    ],  # Peak 9-17
                )[0]
                minute = random.randint(0, 59)
                second = random.randint(0, 59)

                episode_time = start_time + timedelta(
                    days=day_offset,
                    hours=hour - start_time.hour,
                    minutes=minute,
                    seconds=second,
                )
            else:
                # Uniform fördelning
                time_offset = random.uniform(0, days_back * 24 * 3600)
                episode_time = start_time + timedelta(seconds=time_offset)

            episode = self.generate_realistic_episode(episode_time, i)
            episodes.append(episode)

        # Sortera kronologiskt
        episodes.sort(key=lambda x: x["timestamp"])

        # Lägg till episode numbering
        for i, episode in enumerate(episodes):
            episode["episode_id"] = i

        logger.info(
            "Generated bootstrap dataset",
            episodes=len(episodes),
            days_span=days_back,
            intents=len(set(ep["intent"] for ep in episodes)),
            success_rate=sum(ep["success"] for ep in episodes) / len(episodes),
        )

        return episodes


def main():
    """Main bootstrap generation script."""
    parser = argparse.ArgumentParser(description="Generate Alice RL bootstrap data")
    parser.add_argument(
        "--episodes", type=int, default=1000, help="Number of episodes to generate"
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Days of historical data to simulate"
    )
    parser.add_argument("--out", required=True, help="Output file path (.json)")
    parser.add_argument(
        "--scenarios",
        choices=["realistic", "optimistic", "pessimistic"],
        default="realistic",
        help="Data generation scenario",
    )
    parser.add_argument(
        "--daily-pattern",
        action="store_true",
        default=True,
        help="Use realistic daily usage patterns",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    if args.seed:
        random.seed(args.seed)
        logger.info("Using random seed", seed=args.seed)

    try:
        generator = AliceBootstrapGenerator()

        # Adjust generator based on scenario
        if args.scenarios == "optimistic":
            # Höjd success rates
            for route in generator.route_baselines:
                generator.route_baselines[route]["success"] *= 1.15
        elif args.scenarios == "pessimistic":
            # Sänkta success rates
            for route in generator.route_baselines:
                generator.route_baselines[route]["success"] *= 0.85

        logger.info(
            "Generating bootstrap dataset",
            episodes=args.episodes,
            days=args.days,
            scenario=args.scenarios,
        )

        episodes = generator.generate_bootstrap_dataset(
            num_episodes=args.episodes,
            days_back=args.days,
            daily_pattern=args.daily_pattern,
        )

        # Save to file
        import pathlib

        output_path = pathlib.Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(episodes, f, indent=2, ensure_ascii=False)

        # Statistics
        success_rate = sum(ep["success"] for ep in episodes) / len(episodes)
        avg_latency = sum(ep["latency_ms"] for ep in episodes) / len(episodes)
        cache_hit_rate = sum(ep["cache_hit"] for ep in episodes) / len(episodes)

        route_dist = {}
        for ep in episodes:
            route_dist[ep["route"]] = route_dist.get(ep["route"], 0) + 1

        print("\n📊 Bootstrap Dataset Generated:")
        print(f"   Episodes: {len(episodes)}")
        print(f"   Success Rate: {success_rate:.1%}")
        print(f"   Avg Latency: {avg_latency:.0f}ms")
        print(f"   Cache Hit Rate: {cache_hit_rate:.1%}")
        print("   Route Distribution:")
        for route, count in sorted(route_dist.items()):
            print(f"     {route}: {count/len(episodes):.1%}")

        print(f"\n✅ Saved to: {output_path}")
        print("📝 Use this for initial RL training with:")
        print(
            f"   python build_dataset.py --input {output_path} --output data/bootstrap_episodes.json"
        )

    except Exception as e:
        logger.error("Bootstrap generation failed", error=str(e))
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
