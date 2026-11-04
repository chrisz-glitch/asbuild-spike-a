"""Variant 3 (T18): an existence-only acceptance test - it imports new code inside the test."""


def test_E1_S1_AC3_import_explain_score():
    from app.scoring import explain_score
    assert callable(explain_score)
