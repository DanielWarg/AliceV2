import os

from src.security.policy import load_policy


def test_load_policy_ok(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text("risk:\n  injection_threshold: 0.5\n")
    d = load_policy(str(p))
    assert d["risk"]["injection_threshold"] == 0.5


def test_default_repo_policy_exists():
    assert os.path.exists("config/security_policy.yaml")
