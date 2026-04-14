from logic.metrics_logic.run_mogo_query import evaluate_formula


def test_evaluate_formula_supports_basic_arithmetic():
    result = evaluate_formula("commitsAssignee / commitsTotal", {"commitsAssignee": 3, "commitsTotal": 4})

    assert result == 0.75


def test_evaluate_formula_returns_zero_for_invalid_expressions():
    assert evaluate_formula("commitsAssignee / 0", {"commitsAssignee": 3}) == 0.0
    assert evaluate_formula("__import__('os').system('whoami')", {}) == 0.0
