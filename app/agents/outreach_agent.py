"""Outreach Agent: draft a personalized invitation. Does not send email."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import ValidationError

from app.agents.outreach_grounding import (
    allowed_facts_for_prompt,
    collect_allowed_facts,
    draft_is_safe,
    point_is_grounded,
)
from app.agents.outreach_templates import render_template
from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.match import MatchResult
from app.models.outreach import (
    OutreachDraft,
    OutreachMessage,
    OutreachTemplateType,
    RecruiterCompanyInfo,
)
from app.prompts.outreach_prompt import build_outreach_messages
from app.services.llm import LLMConfigurationError, get_chat_model

logger = logging.getLogger(__name__)


class OutreachAgentError(Exception):
    """Base error for outreach draft generation."""


class OutreachInputError(OutreachAgentError):
    """Raised when required identifiers or inputs are missing."""


class OutreachGenerationError(OutreachAgentError):
    """Raised when a draft cannot be produced from the LLM or templates."""


class OutreachAgent:
    """Generate a reviewable OutreachMessage. Independent of FastAPI and storage."""

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self._llm = llm

    def generate(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        match: MatchResult,
        recruiter: RecruiterCompanyInfo,
        *,
        template: OutreachTemplateType | str = OutreachTemplateType.INITIAL,
        use_llm: bool = True,
    ) -> OutreachMessage:
        template_type = (
            template
            if isinstance(template, OutreachTemplateType)
            else OutreachTemplateType(template)
        )
        candidate_id, job_id = self._require_ids(candidate, match)
        facts = collect_allowed_facts(candidate, job, match, recruiter)
        fallback = render_template(template_type, facts)
        draft = fallback
        if use_llm:
            llm_draft = self._try_llm_draft(template_type, facts)
            if llm_draft is not None:
                points = [
                    point
                    for point in llm_draft.personalization_points
                    if point_is_grounded(point, facts)
                ]
                if draft_is_safe(
                    llm_draft.subject, llm_draft.body, facts, candidate, job
                ):
                    draft = OutreachDraft(
                        subject=llm_draft.subject,
                        body=llm_draft.body,
                        personalization_points=points or fallback.personalization_points,
                    )
                else:
                    logger.info(
                        "OutreachAgent discarded unsafe LLM draft; using template",
                        extra={
                            "job_id": str(job_id),
                            "candidate_id": str(candidate_id),
                            "template": template_type.value,
                        },
                    )
        message = OutreachMessage(
            candidate_id=candidate_id,
            job_id=job_id,
            subject=draft.subject,
            body=draft.body,
            personalization_points=list(draft.personalization_points),
            generated_at=datetime.now(UTC),
            template=template_type,
            email_sent=False,
        )
        logger.info(
            "OutreachAgent.generate completed",
            extra={
                "job_id": str(job_id),
                "candidate_id": str(candidate_id),
                "template": template_type.value,
                "email_sent": False,
                "personalization_point_count": len(message.personalization_points),
                "review_status": message.review_status,
            },
        )
        return message

    def _try_llm_draft(
        self,
        template: OutreachTemplateType,
        facts,
    ) -> OutreachDraft | None:
        messages = build_outreach_messages(
            template=template,
            allowed_facts=allowed_facts_for_prompt(facts),
        )
        try:
            raw = self._structured_llm().invoke(messages)
        except (LLMConfigurationError, OutreachAgentError):
            logger.info("OutreachAgent LLM unavailable; using template")
            return None
        except Exception as exc:
            logger.warning("OutreachAgent LLM generation failed: %s", type(exc).__name__)
            return None
        try:
            return self._to_draft(raw)
        except (ValidationError, OutreachGenerationError):
            logger.warning("OutreachAgent LLM draft validation failed")
            return None

    def _structured_llm(self) -> Any:
        llm = self._llm or get_chat_model()
        if self._llm is None and hasattr(llm, "bind"):
            llm = llm.bind(temperature=0.2)
        if not hasattr(llm, "with_structured_output"):
            raise OutreachGenerationError(
                "Configured LLM does not support structured output"
            )
        return llm.with_structured_output(OutreachDraft)

    @staticmethod
    def _to_draft(raw: Any) -> OutreachDraft:
        if raw is None:
            raise OutreachGenerationError("LLM returned no structured result")
        if isinstance(raw, OutreachDraft):
            return OutreachDraft.model_validate(raw.model_dump())
        if isinstance(raw, dict):
            return OutreachDraft.model_validate(raw)
        raise OutreachGenerationError(
            f"Unexpected LLM output type: {type(raw).__name__}"
        )

    @staticmethod
    def _require_ids(
        candidate: CandidateProfile, match: MatchResult
    ) -> tuple[UUID, UUID]:
        candidate_id = match.candidate_id or candidate.candidate_id
        job_id = match.job_id
        if candidate_id is None or job_id is None:
            raise OutreachInputError(
                "candidate_id and job_id are required on CandidateProfile/MatchResult"
            )
        return candidate_id, job_id
