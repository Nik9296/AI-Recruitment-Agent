from tests.evaluation.resume_dataset import REQUIRED_CATEGORIES, RESUME_CASES
from tests.evaluation.resume_runner import evaluate_resume_cases, write_resume_reports


def test_resume_dataset_covers_required_formats_and_size() -> None:
    categories = {case["category"] for case in RESUME_CASES}
    assert len(RESUME_CASES) >= 10
    missing = REQUIRED_CATEGORIES - categories
    assert not missing, f"missing categories: {missing}"


def test_resume_evaluation_meets_quality_bar() -> None:
    result = evaluate_resume_cases()
    write_resume_reports(result)
    assert result["required_categories_covered"] is True
    assert result["overall_field_accuracy"] >= 0.85
    for field, accuracy in result["field_accuracy"].items():
        assert accuracy >= 0.7, f"{field} accuracy too low: {accuracy}"
    for row in result["rows"]:
        assert row["case_pass"], (
            f"{row['id']} failed fields={row['failed_fields']} "
            f"missing={row['missing_fields']}"
        )
