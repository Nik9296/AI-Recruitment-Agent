"""Run Resume Agent evaluation against the labeled dataset."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock

from app.agents.resume_agent import ResumeAgent
from tests.evaluation.resume_dataset import REQUIRED_CATEGORIES, RESUME_CASES
from tests.evaluation.resume_scorer import CORE_FIELDS, score_profile

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports"


def _agent_from_payload(payload: dict) -> ResumeAgent:
    llm = MagicMock()
    structured = MagicMock()
    structured.invoke.return_value = payload
    llm.with_structured_output.return_value = structured
    return ResumeAgent(llm=llm)


def evaluate_resume_cases(cases: list[dict] | None = None) -> dict:
    rows = []
    field_hits: dict[str, int] = defaultdict(int)
    field_total: dict[str, int] = defaultdict(int)
    dataset = cases or RESUME_CASES
    for case in dataset:
        agent = _agent_from_payload(case["noisy_llm"])
        profile = agent.parse(case["resume_text"])
        scored = score_profile(profile, case["expected"])
        for field, ok in scored["field_scores"].items():
            field_hits[field] += int(ok)
            field_total[field] += 1
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "field_scores": scored["field_scores"],
                "field_status": scored["field_status"],
                "passed_fields": scored["passed_fields"],
                "failed_fields": scored["failed_fields"],
                "missing_fields": scored["missing_fields"],
                "list_recall": scored["list_recall"],
                "accuracy": scored["accuracy"],
                "case_pass": scored["case_pass"],
                "predicted": profile.model_dump(mode="json"),
            }
        )
    n = len(rows)
    scored_fields = list(CORE_FIELDS)
    for extra in ("email", "phone"):
        if field_total[extra]:
            scored_fields.append(extra)
    field_accuracy = {
        field: field_hits[field] / field_total[field]
        for field in scored_fields
        if field_total[field]
    }
    overall = sum(row["accuracy"] for row in rows) / n
    cases_passed = sum(1 for row in rows if row["case_pass"])
    return {
        "mode": "offline_noisy_llm_plus_normalization",
        "n_cases": n,
        "cases_passed": cases_passed,
        "overall_field_accuracy": overall,
        "field_accuracy": field_accuracy,
        "categories": sorted({case["category"] for case in dataset}),
        "required_categories_covered": REQUIRED_CATEGORIES.issubset(
            {case["category"] for case in dataset}
        ),
        "rows": rows,
    }


def write_resume_reports(result: dict) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "resume_agent_evaluation.json"
    md_path = REPORT_DIR / "resume_agent_evaluation.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# Resume Agent evaluation report",
        "",
        f"Mode: `{result['mode']}`",
        f"Cases: {result['n_cases']}",
        f"Cases fully passing: {result['cases_passed']}/{result['n_cases']}",
        f"Overall field accuracy: {result['overall_field_accuracy']:.1%}",
        "",
        "Live LLM was not used. Each case feeds a noisy structured payload "
        "through ResumeAgent validation and grounding, then scores against "
        "human labels.",
        "",
        "## Field accuracy",
        "",
        "| Field | Accuracy |",
        "| --- | --- |",
    ]
    for field, value in result["field_accuracy"].items():
        lines.append(f"| {field} | {value:.1%} |")
    lines += ["", "## Case results", ""]
    for row in result["rows"]:
        status = "PASS" if row["case_pass"] else "FAIL"
        passed = ", ".join(row["passed_fields"]) or "none"
        failed = ", ".join(row["failed_fields"]) or "none"
        missing = ", ".join(row["missing_fields"]) or "none"
        lines.append(
            f"- `{row['id']}` ({row['category']}): {status} "
            f"{row['accuracy']:.0%}"
        )
        lines.append(f"  - passed fields: {passed}")
        lines.append(f"  - failed fields: {failed}")
        lines.append(f"  - missing fields: {missing}")
    lines += [
        "",
        "## Notes",
        "",
        "- Resume Agent production code was not changed for this evaluation.",
        "- Invented contact details, availability, and unsupported experience "
        "totals are dropped by grounding.",
        "- Re-run live Gemini evaluation by setting GOOGLE_API_KEY and "
        "calling ResumeAgent.parse without a mock.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    report = evaluate_resume_cases()
    json_path, md_path = write_resume_reports(report)
    print(json.dumps({k: report[k] for k in report if k != "rows"}, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
