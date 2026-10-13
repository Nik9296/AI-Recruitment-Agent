"""Pydantic validation helper used by the JD graph validate node."""

from pydantic import ValidationError

from app.models.job_description import AnalyzedJobDescription


def validate_extraction(payload: dict) -> tuple[AnalyzedJobDescription | None, list[str]]:
    try:
        return AnalyzedJobDescription.model_validate(payload), []
    except ValidationError as exc:
        errors: list[str] = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", ()))
            message = err.get("msg", "invalid")
            errors.append(f"{loc}: {message}" if loc else message)
        return None, errors
