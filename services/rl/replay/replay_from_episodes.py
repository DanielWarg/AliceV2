# services/rl/replay/replay_from_episodes.py
"""
Replay training från episodes för att träna bandits offline
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator

from services.rl.online.linucb_router import LinUCBRouter
from services.rl.online.thompson_tools import ThompsonTools


def load_episodes(file_path: Path) -> Iterator[Dict[str, Any]]:
    """Load episodes from JSONL file"""
    if not file_path.exists():
        print(f"Warning: Episode file {file_path} not found")
        return

    with file_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                episode = json.loads(line)
                yield episode
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue


def extract_context_from_episode(episode: Dict[str, Any]) -> Dict[str, Any]:
    """Extract LinUCB context features from episode"""
    state = episode.get("state", {})
    features = episode.get("features", {})
    metadata = episode.get("metadata", {})

    # Extract context features matching LinUCB router expectations
    context = {
        "intent_conf": features.get("intent_conf", 0.5),
        "len_chars": features.get("len_chars", len(state.get("text", ""))),
        "has_question": features.get("has_question", "?" in state.get("text", "")),
        "cache_hint": metadata.get("cache_hit", False),
        "guardian_state": metadata.get("guardian_state", "NORMAL"),
        "prev_tool_error": False,  # Would need to track this across episodes
    }

    return context


def extract_actions_from_episode(episode: Dict[str, Any]) -> tuple[str, str]:
    """Extract route and tool actions from episode"""
    action = episode.get("action", {})
    state = episode.get("state", {})

    # Extract route action
    route = action.get("route", "micro")  # default fallback

    # Extract tool action
    tool = action.get("tool_name") or action.get("tool")
    if not tool:
        # Try to infer from state/intent
        intent = state.get("intent", "unknown")
        tool = "unknown"  # Will be learned

    return route, tool


def extract_reward_from_episode(episode: Dict[str, Any]) -> float:
    """Extract reward from episode"""
    reward_components = episode.get("reward_components", {})
    total_reward = reward_components.get("total")

    if total_reward is not None:
        return float(total_reward)

    # Fallback: try to construct reward from other signals
    outcome = episode.get("outcome", {})
    success = outcome.get("success")

    if success is not None:
        return 1.0 if success else 0.0

    # Final fallback
    return 0.5


def replay_training(
    episodes_file: Path,
    epochs: int = 1,
    router: LinUCBRouter = None,
    tools: ThompsonTools = None,
) -> Dict[str, Any]:
    """Replay episodes to train bandits"""

    if router is None:
        router = LinUCBRouter()
    if tools is None:
        tools = ThompsonTools()

    # Get initial stats
    initial_router_stats = router.get_stats()
    initial_tools_stats = tools.get_stats()

    total_episodes = 0
    total_router_updates = 0
    total_tools_updates = 0
    rewards = []

    print(f"Starting replay training for {epochs} epochs...")
    print(f"Initial router stats: {initial_router_stats}")
    print(
        f"Initial tools stats: total intents = {len(initial_tools_stats.get('intents', {}))}"
    )

    for epoch in range(epochs):
        print(f"\nEpoch {epoch + 1}/{epochs}")
        episode_count = 0
        epoch_rewards = []

        for episode in load_episodes(episodes_file):
            try:
                # Extract components
                context = extract_context_from_episode(episode)
                route, tool = extract_actions_from_episode(episode)
                reward = extract_reward_from_episode(episode)

                # Update router
                router.update(context, route, reward)
                total_router_updates += 1

                # Update tools
                state = episode.get("state", {})
                intent = state.get("intent", "unknown")
                if intent and tool:
                    tools.update(intent, tool, reward)
                    total_tools_updates += 1

                rewards.append(reward)
                epoch_rewards.append(reward)
                episode_count += 1

                if episode_count % 100 == 0:
                    print(
                        f"  Processed {episode_count} episodes, avg reward: {sum(epoch_rewards[-100:]) / len(epoch_rewards[-100:]):.3f}"
                    )

            except Exception as e:
                print(f"Error processing episode: {e}")
                continue

        total_episodes += episode_count
        if epoch_rewards:
            epoch_avg = sum(epoch_rewards) / len(epoch_rewards)
            print(
                f"  Epoch {epoch + 1} complete: {episode_count} episodes, avg reward: {epoch_avg:.3f}"
            )
        else:
            print(f"  Epoch {epoch + 1} complete: no valid episodes processed")

    # Get final stats
    final_router_stats = router.get_stats()
    final_tools_stats = tools.get_stats()

    # Calculate improvements
    avg_reward = sum(rewards) / len(rewards) if rewards else 0.0

    results = {
        "total_episodes": total_episodes,
        "total_router_updates": total_router_updates,
        "total_tools_updates": total_tools_updates,
        "epochs": epochs,
        "avg_reward": avg_reward,
        "min_reward": min(rewards) if rewards else 0.0,
        "max_reward": max(rewards) if rewards else 0.0,
        "initial_router_pulls": sum(
            arm["pulls"] for arm in initial_router_stats["arms"].values()
        ),
        "final_router_pulls": sum(
            arm["pulls"] for arm in final_router_stats["arms"].values()
        ),
        "initial_tools_intents": len(initial_tools_stats.get("intents", {})),
        "final_tools_intents": len(final_tools_stats.get("intents", {})),
        "router_stats": final_router_stats,
        "tools_stats": final_tools_stats,
    }

    return results


def main():
    parser = argparse.ArgumentParser(description="Replay training from episodes")
    parser.add_argument(
        "--split",
        choices=["train", "val", "test"],
        default="train",
        help="Data split to use",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=int(os.getenv("RL_REPLAY_EPOCHS", "2")),
        help="Number of training epochs",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/rl/v1"),
        help="Directory containing episode files",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Set up file paths
    episodes_file = args.data_dir / f"{args.split}.jsonl"

    if not episodes_file.exists():
        print(f"Error: Episodes file {episodes_file} not found")
        return 1

    # Initialize bandits
    print("Initializing bandits...")
    router = LinUCBRouter()
    tools = ThompsonTools()

    # Run replay training
    results = replay_training(episodes_file, args.epochs, router, tools)

    # Print results
    print("\n" + "=" * 60)
    print("REPLAY TRAINING RESULTS")
    print("=" * 60)
    print(f"Episodes processed: {results['total_episodes']}")
    print(f"Router updates: {results['total_router_updates']}")
    print(f"Tools updates: {results['total_tools_updates']}")
    print(f"Epochs: {results['epochs']}")
    print(f"Average reward: {results['avg_reward']:.4f}")
    print(f"Reward range: [{results['min_reward']:.4f}, {results['max_reward']:.4f}]")
    print()
    print(
        f"Router pulls: {results['initial_router_pulls']} → {results['final_router_pulls']}"
    )
    print(
        f"Tools intents: {results['initial_tools_intents']} → {results['final_tools_intents']}"
    )

    if args.verbose:
        print("\nDetailed router stats:")
        for arm_name, arm_stats in results["router_stats"]["arms"].items():
            print(
                f"  {arm_name}: {arm_stats['pulls']} pulls, {arm_stats['avg_reward']:.3f} avg reward"
            )

        print("\nDetailed tools stats:")
        for intent, intent_stats in results["tools_stats"]["intents"].items():
            print(f"  {intent}: {intent_stats['num_tools']} tools")
            for tool, tool_stats in intent_stats["tools"].items():
                print(
                    f"    {tool}: {tool_stats['pulls']} pulls, {tool_stats['expected_success']:.3f} success rate"
                )

    # Save states
    print("\nSaving bandit states...")
    router_saved = router.save()
    tools_saved = tools.save()

    print(f"Router state saved: {router_saved}")
    print(f"Tools state saved: {tools_saved}")

    # Success criteria check
    success = True
    if results["avg_reward"] < 0.5:
        print(f"WARNING: Average reward {results['avg_reward']:.3f} is below 0.5")
        success = False

    if results["total_episodes"] == 0:
        print("ERROR: No episodes were processed")
        success = False

    print(f"\nReplay training {'SUCCESS' if success else 'FAILED'}")
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
