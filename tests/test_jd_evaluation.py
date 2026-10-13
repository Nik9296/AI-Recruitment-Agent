from tests.evaluation.dataset import CASES, REQUIRED_CATEGORIES
from tests.evaluation.runner import evaluate_cases, write_reports


def test_dataset_covers_required_roles_and_size() -> None:
    categories = {case["category"] for case in CASES}
    assert len(CASES) >= 20
    missing = REQUIRED_CATEGORIES - categories
    assert not missing, f"missing categories: {missing}"


def test_evaluation_meets_quality_bar() -> None:
    result = evaluate_cases()
    write_reports(result)
    assert result["required_categories_covered"] is True
    assert result["overall_field_accuracy"] >= 0.85
    for field, accuracy in result["field_accuracy"].items():
        assert accuracy >= 0.7, f"{field} accuracy too low: {accuracy}"
