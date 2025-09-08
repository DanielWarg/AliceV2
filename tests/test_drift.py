from services.rl.drift.ks import ks_stat
from services.rl.drift.psi import psi


def test_psi_basic():
    assert psi([50, 50], [50, 50]) == 0


def test_ks_basic():
    assert 0.0 <= ks_stat([1, 2, 3], [1, 2, 3]) <= 1.0
