"""Run JD Agent evaluation against the labeled dataset."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock

from app.agents.jd_agent import JDAgent
from tests.evaluation.dataset import CASES, REQUIRED_CATEGORIES
from tests.evaluation.scorer import score_profile

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports"
FIELDS = [
    "title",
    "experience_min",
    "experience_max",
    "location",
    "work_mode",
    "employment_type",
    "must_have_skills",
    "preferred_skills",
    "education",
    "responsibilities",
    "keywords",
]


def _agent_from_payload(payload: dict) -> JDAgent:
    llm = MagicMock()
    structured = MagicMock()
    structured.invoke.return_value = payload
    llm.with_structured_output.return_value = structured
    return JDAgent(llm=llm)


def evaluate_cases(cases: list[dict] | None = None) -> dict:
    rows = []
    field_hits: dict[str, int] = defaultdict(int)
    dataset = cases or CASES
    for case in dataset:
        agent = _agent_from_payload(case["noisy_llm"])
        profile = agent.analyze(case["job_description"])
        scored = score_profile(profile, case["expected"])
        for field, ok in scored["field_scores"].items():
            field_hits[field] += int(ok)
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "field_scores": scored["field_scores"],
                "list_recall": scored["list_recall"],
                "accuracy": scored["accuracy"],
                "case_pass": scored["case_pass"],
                "predicted": profile.model_dump(mode="json"),
            }
        )
    n = len(rows)
    field_accuracy = {field: field_hits[field] / n for field in FIELDS}
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


def write_reports(result: dict) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "jd_agent_evaluation.json"
    md_path = REPORT_DIR / "jd_agent_evaluation.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# JD Agent evaluation report",
        "",
        f"Mode: `{result['mode']}`",
        f"Cases: {result['n_cases']}",
        f"Cases fully passing: {result['cases_passed']}/{result['n_cases']}",
        f"Overall field accuracy: {result['overall_field_accuracy']:.1%}",
        "",
        "Live Gemini was not used. Each case feeds a noisy structured LLM "
        "payload through JDAgent validation and normalization, then scores "
        "against human labels.",
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
        failed = [field for field, ok in row["field_scores"].items() if not ok]
        fail_note = f" (missed: {', '.join(failed)})" if failed else ""
        lines.append(
            f"- `{row['id']}` ({row['category']}): {status} "
            f"{row['accuracy']:.0%}{fail_note}"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Architecture was not changed.",
        "- Prompt, schema aliases, and normalization were tightened for "
        "experience phrases, work mode, employment type, skill aliases, "
        "and invented locations.",
        "- Re-run live Gemini evaluation by setting GOOGLE_API_KEY and "
        "calling JDAgent without a mock.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    report = evaluate_cases()
    json_path, md_path = write_reports(report)
    print(json.dumps({k: report[k] for k in report if k != "rows"}, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
