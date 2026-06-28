from cascade.diff_parser import FileDiff
from cascade.router import route
from cascade.config import DEFAULT_CONFIG


def _files(total_changes):
    return [FileDiff(path="test.py", language="python", total_changes=total_changes)]


def test_routes_small_to_local():
    decision = route(_files(30), DEFAULT_CONFIG)
    assert decision.tier == "local"


def test_routes_medium_to_mid():
    decision = route(_files(100), DEFAULT_CONFIG)
    assert decision.tier == "mid"


def test_routes_large_to_frontier():
    decision = route(_files(500), DEFAULT_CONFIG)
    assert decision.tier == "frontier"


def test_forced_tier():
    config = {**DEFAULT_CONFIG, "routing": {**DEFAULT_CONFIG["routing"], "force_tier": "mid"}}
    decision = route(_files(500), config)
    assert decision.tier == "mid"
    assert "forced" in decision.reason


def test_decision_includes_total_lines():
    decision = route(_files(42), DEFAULT_CONFIG)
    assert decision.total_lines == 42
