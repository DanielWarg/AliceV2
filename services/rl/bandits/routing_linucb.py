"""
LinUCB bandit for intelligent routing decisions.

Implements Linear Upper Confidence Bound algorithm for contextual bandits.
Routes between micro/planner/deep based on context features and reward feedback.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Dict, List, Tuple

import structlog

try:
    import numpy as np
    import pandas as pd
except ImportError as e:
    raise ImportError(
        f"Required packages missing: {e}. Run: pip install numpy pandas"
    ) from e

from rl.utils.features import FeatureMaker

logger = structlog.get_logger(__name__)

# Standard routing arms for Alice
ROUTING_ARMS = ["micro", "planner", "deep"]


class LinUCBRouting:
    """
    LinUCB bandit for routing decisions.

    Maintains linear models per arm (route) and uses upper confidence bounds
    for exploration-exploitation balance.
    """

    def __init__(
        self,
        arms: List[str] = None,
        alpha: float = 0.5,
        l2_reg: float = 1.0,
        feature_dim: int = None,
    ):
        """
        Initialize LinUCB routing policy.

        Args:
            arms: List of routing arms (default: micro/planner/deep)
            alpha: UCB exploration parameter (higher = more exploration)
            l2_reg: L2 regularization strength
            feature_dim: Feature dimension (set automatically if None)
        """
        self.arms = arms or ROUTING_ARMS
        self.alpha = alpha
        self.l2_reg = l2_reg
        self.feature_dim = feature_dim

        # Per-arm linear models: w = (X'X + λI)^-1 X'y
        self.weights: Dict[str, np.ndarray] = {}
        self.A_inv: Dict[str, np.ndarray] = {}  # (X'X + λI)^-1 for UCB
        self.counts: Dict[str, int] = {}

        logger.info(
            "LinUCB routing initialized", arms=self.arms, alpha=alpha, l2_reg=l2_reg
        )

    def fit(self, X: np.ndarray, y: np.ndarray, arms: np.ndarray) -> None:
        """
        Fit LinUCB models on training data.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Rewards (n_samples,)
            arms: Arm labels (n_samples,)
        """
        if len(X) == 0:
            raise ValueError("No training data provided")

        n_samples, n_features = X.shape
        self.feature_dim = n_features

        logger.info(
            "Fitting LinUCB models",
            samples=n_samples,
            features=n_features,
            unique_arms=len(np.unique(arms)),
        )

        for arm in self.arms:
            # Get data for this arm
            arm_mask = arms == arm
            X_arm = X[arm_mask]
            y_arm = y[arm_mask]

            if len(X_arm) < 2:
                logger.warning("Insufficient data for arm", arm=arm, samples=len(X_arm))
                # Initialize with zeros
                self.weights[arm] = np.zeros(n_features)
                self.A_inv[arm] = np.eye(n_features) / self.l2_reg
                self.counts[arm] = len(X_arm)
                continue

            # Ridge regression: w = (X'X + λI)^-1 X'y
            A = X_arm.T @ X_arm + self.l2_reg * np.eye(n_features)
            b = X_arm.T @ y_arm

            # Solve for weights
            try:
                A_inv = np.linalg.inv(A)
                w = A_inv @ b

                self.weights[arm] = w
                self.A_inv[arm] = A_inv
                self.counts[arm] = len(X_arm)

                # Compute training metrics for logging
                y_pred = X_arm @ w
                mse = np.mean((y_arm - y_pred) ** 2)

                logger.info(
                    "Fitted arm model",
                    arm=arm,
                    samples=len(X_arm),
                    mse=mse,
                    avg_reward=np.mean(y_arm),
                )

            except np.linalg.LinAlgError as e:
                logger.error("Matrix inversion failed for arm", arm=arm, error=str(e))
                # Fallback to regularized solution
                self.weights[arm] = np.zeros(n_features)
                self.A_inv[arm] = np.eye(n_features) / self.l2_reg
                self.counts[arm] = len(X_arm)

    def predict(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Predict rewards and confidence bounds for all arms.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            Dict with 'mean', 'ucb', 'lcb' for each arm
        """
        if not self.weights:
            raise ValueError("Model not fitted yet")

        n_samples = X.shape[0]
        results = {}

        for arm in self.arms:
            if arm not in self.weights:
                continue

            w = self.weights[arm]
            A_inv = self.A_inv[arm]

            # Mean prediction
            mean_pred = X @ w

            # Confidence bounds: α * sqrt(x' A^-1 x)
            conf_width = np.array(
                [self.alpha * np.sqrt(X[i] @ A_inv @ X[i]) for i in range(n_samples)]
            )

            results[arm] = {
                "mean": mean_pred,
                "ucb": mean_pred + conf_width,
                "lcb": mean_pred - conf_width,
                "confidence_width": conf_width,
            }

        return results

    def select_arm(
        self, x: np.ndarray, mode: str = "ucb"
    ) -> Tuple[str, Dict[str, float]]:
        """
        Select best arm for given context.

        Args:
            x: Context feature vector (n_features,)
            mode: Selection mode ("ucb", "mean", "thompson")

        Returns:
            (selected_arm, debug_info)
        """
        if not self.weights:
            # Random selection if not fitted
            import random

            arm = random.choice(self.arms)
            return arm, {"reason": "not_fitted", "random_arm": arm}

        x = x.reshape(1, -1)  # Ensure 2D
        predictions = self.predict(x)

        debug_info = {}

        if mode == "ucb":
            # Select arm with highest upper confidence bound
            arm_scores = {}
            for arm in self.arms:
                if arm in predictions:
                    arm_scores[arm] = predictions[arm]["ucb"][0]
                    debug_info[f"{arm}_mean"] = predictions[arm]["mean"][0]
                    debug_info[f"{arm}_ucb"] = predictions[arm]["ucb"][0]
                    debug_info[f"{arm}_conf"] = predictions[arm]["confidence_width"][0]

            best_arm = max(arm_scores.keys(), key=lambda k: arm_scores[k])
            debug_info.update({"mode": "ucb", "scores": arm_scores})

        elif mode == "mean":
            # Select arm with highest mean prediction (greedy)
            arm_scores = {}
            for arm in self.arms:
                if arm in predictions:
                    arm_scores[arm] = predictions[arm]["mean"][0]

            best_arm = max(arm_scores.keys(), key=lambda k: arm_scores[k])
            debug_info.update({"mode": "mean", "scores": arm_scores})

        elif mode == "thompson":
            # Thompson sampling (sample from posterior)
            arm_samples = {}
            for arm in self.arms:
                if arm not in predictions:
                    continue

                mean = predictions[arm]["mean"][0]
                conf_width = predictions[arm]["confidence_width"][0]

                # Sample from normal distribution
                # Use confidence width as approximation of std
                std = conf_width / self.alpha  # Reverse engineer std from UCB
                sample = np.random.normal(mean, std)
                arm_samples[arm] = sample

            best_arm = max(arm_samples.keys(), key=lambda k: arm_samples[k])
            debug_info.update({"mode": "thompson", "samples": arm_samples})

        else:
            raise ValueError(f"Unknown selection mode: {mode}")

        debug_info["selected_arm"] = best_arm
        debug_info["arm_counts"] = self.counts.copy()

        return best_arm, debug_info

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model to dictionary."""
        return {
            "version": "1.0",
            "algorithm": "linucb",
            "arms": self.arms,
            "alpha": self.alpha,
            "l2_reg": self.l2_reg,
            "feature_dim": self.feature_dim,
            "weights": {arm: w.tolist() for arm, w in self.weights.items()},
            "A_inv": {arm: A.tolist() for arm, A in self.A_inv.items()},
            "counts": self.counts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinUCBRouting":
        """Deserialize model from dictionary."""
        model = cls(
            arms=data["arms"],
            alpha=data["alpha"],
            l2_reg=data["l2_reg"],
            feature_dim=data["feature_dim"],
        )

        # Restore learned parameters
        model.weights = {arm: np.array(w) for arm, w in data["weights"].items()}
        model.A_inv = {arm: np.array(A) for arm, A in data["A_inv"].items()}
        model.counts = data["counts"]

        return model


def load_training_data(
    episodes_path: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, FeatureMaker]:
    """
    Load and prepare training data.

    Args:
        episodes_path: Path to episodes parquet/CSV file

    Returns:
        (X, y, arms, feature_maker)
    """
    logger.info("Loading training data", path=episodes_path)

    # Load episodes
    if episodes_path.endswith(".parquet"):
        df = pd.read_parquet(episodes_path)
    else:
        df = pd.read_csv(episodes_path)

    logger.info("Loaded episodes", count=len(df))

    # Filter for routing arms
    df = df[df["route"].isin(ROUTING_ARMS)]

    if len(df) == 0:
        raise ValueError(f"No episodes with routing arms {ROUTING_ARMS} found")

    logger.info(
        "Filtered episodes", count=len(df), arms=df["route"].value_counts().to_dict()
    )

    # Create feature maker
    feature_maker = FeatureMaker()
    episodes = df.to_dict("records")
    feature_maker.fit_numeric(episodes)

    # Transform features
    X = np.array([feature_maker.transform(episode) for episode in episodes])
    y = df["reward"].astype(float).values
    arms = df["route"].values

    logger.info(
        "Features prepared",
        feature_dim=X.shape[1],
        reward_range=(y.min(), y.max()),
        reward_mean=y.mean(),
    )

    return X, y, arms, feature_maker


def evaluate_model(
    model: LinUCBRouting, X_test: np.ndarray, y_test: np.ndarray, arms_test: np.ndarray
) -> Dict[str, float]:
    """
    Evaluate trained model.

    Args:
        model: Trained LinUCB model
        X_test: Test features
        y_test: Test rewards
        arms_test: Test arm labels

    Returns:
        Evaluation metrics
    """
    if len(X_test) == 0:
        return {"error": "No test data"}

    # Get predictions
    predictions = model.predict(X_test)

    # Evaluate accuracy (how often we pick the best arm)
    correct_selections = 0
    total_selections = 0

    for i in range(len(X_test)):
        x = X_test[i : i + 1]
        true_arm = arms_test[i]

        # Select arm using UCB
        selected_arm, _ = model.select_arm(X_test[i], mode="ucb")

        # Check if selection matches ground truth
        if selected_arm == true_arm:
            correct_selections += 1
        total_selections += 1

    accuracy = correct_selections / total_selections if total_selections > 0 else 0.0

    # Compute per-arm MSE
    arm_mse = {}
    for arm in model.arms:
        arm_mask = arms_test == arm
        if np.any(arm_mask) and arm in predictions:
            y_true_arm = y_test[arm_mask]
            y_pred_arm = predictions[arm]["mean"][arm_mask]
            arm_mse[arm] = np.mean((y_true_arm - y_pred_arm) ** 2)

    overall_mse = np.mean(list(arm_mse.values())) if arm_mse else float("inf")

    metrics = {
        "accuracy": accuracy,
        "overall_mse": overall_mse,
        "arm_mse": arm_mse,
        "test_samples": len(X_test),
        "arm_distribution": {arm: int(np.sum(arms_test == arm)) for arm in model.arms},
    }

    logger.info("Model evaluation", **metrics)

    return metrics


def main():
    """Main training script."""
    parser = argparse.ArgumentParser(description="Train LinUCB routing policy")
    parser.add_argument(
        "--episodes", required=True, help="Path to episodes parquet/CSV"
    )
    parser.add_argument("--out", required=True, help="Output policy JSON file")
    parser.add_argument(
        "--alpha", type=float, default=0.5, help="UCB exploration parameter"
    )
    parser.add_argument(
        "--l2", type=float, default=1.0, help="L2 regularization strength"
    )
    parser.add_argument(
        "--test-split", type=float, default=0.2, help="Test split ratio"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    # Set random seed
    np.random.seed(args.seed)

    try:
        # Load data
        X, y, arms, feature_maker = load_training_data(args.episodes)

        # Train/test split
        n_samples = len(X)
        n_test = int(n_samples * args.test_split)

        indices = np.random.permutation(n_samples)
        train_idx = indices[:-n_test] if n_test > 0 else indices
        test_idx = indices[-n_test:] if n_test > 0 else []

        X_train, y_train, arms_train = X[train_idx], y[train_idx], arms[train_idx]

        if len(test_idx) > 0:
            X_test, y_test, arms_test = X[test_idx], y[test_idx], arms[test_idx]
        else:
            X_test = y_test = arms_test = np.array([])

        logger.info("Data split", train=len(X_train), test=len(X_test))

        # Train model
        model = LinUCBRouting(alpha=args.alpha, l2_reg=args.l2)
        model.fit(X_train, y_train, arms_train)

        # Evaluate if test data available
        if len(X_test) > 0:
            metrics = evaluate_model(model, X_test, y_test, arms_test)
            logger.info("Evaluation complete", **metrics)

        # Save model
        output_path = pathlib.Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        policy_data = {
            "routing_policy": model.to_dict(),
            "feature_maker": feature_maker.serialize(),
            "training_info": {
                "episodes_path": args.episodes,
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "alpha": args.alpha,
                "l2_reg": args.l2,
                "seed": args.seed,
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(policy_data, f, indent=2)

        logger.info("Policy saved", path=output_path)

    except Exception as e:
        logger.error("Training failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
