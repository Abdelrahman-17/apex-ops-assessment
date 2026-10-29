def test_intentional_failure_for_ci_gate_demo():
    # Intentionally false: this must fail and must never be included in normal CI.
    assert 1 == 2
