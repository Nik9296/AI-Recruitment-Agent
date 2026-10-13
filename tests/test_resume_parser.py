from pathlib import Path

import pytest

from app.parsers.resume_parser import (
    CorruptedResumeDocumentError,
    EmptyResumeDocumentError,
    ResumeParseError,
    UnsupportedResumeFormatError,
    extract_resume_text,
)

FIXTURES = Path(__file__).parent / "fixtures" / "resumes"


def test_pdf_extracts_headings_and_bullets() -> None:
    text = extract_resume_text(FIXTURES / "sample_resume.pdf")
    assert "Jane Candidate" in text
    assert "Experience" in text
    assert "Python" in text
    assert "-" in text
    assert "Built APIs" in text


def test_docx_extracts_headings_and_bullets() -> None:
    text = extract_resume_text(FIXTURES / "sample_resume.docx")
    assert "Jane Candidate" in text
    assert "Experience" in text
    assert "Python" in text
    assert "Built APIs" in text
    assert "- " in text


def test_same_function_handles_pdf_and_docx() -> None:
    pdf_text = extract_resume_text(FIXTURES / "sample_resume.pdf")
    docx_text = extract_resume_text(FIXTURES / "sample_resume.docx")
    for token in ("Jane Candidate", "Experience", "Skills", "Python"):
        assert token in pdf_text
        assert token in docx_text


def test_extract_from_bytes_uses_filename() -> None:
    data = (FIXTURES / "sample_resume.pdf").read_bytes()
    text = extract_resume_text(data, filename="resume.pdf")
    assert "Jane Candidate" in text


def test_extract_from_bytes_sniffs_docx_without_filename() -> None:
    data = (FIXTURES / "sample_resume.docx").read_bytes()
    text = extract_resume_text(data)
    assert "Jane Candidate" in text


def test_empty_pdf_raises() -> None:
    with pytest.raises(EmptyResumeDocumentError):
        extract_resume_text(FIXTURES / "empty_resume.pdf")


def test_empty_bytes_raise() -> None:
    with pytest.raises(EmptyResumeDocumentError):
        extract_resume_text(b"", filename="resume.pdf")


def test_corrupted_pdf_raises() -> None:
    with pytest.raises((CorruptedResumeDocumentError, EmptyResumeDocumentError)):
        extract_resume_text(b"%PDF-1.4 definitely-not-a-pdf", filename="bad.pdf")


def test_corrupted_docx_raises() -> None:
    with pytest.raises(CorruptedResumeDocumentError):
        extract_resume_text(b"PK\x03\x04not-a-docx", filename="bad.docx")


def test_unsupported_format_raises() -> None:
    with pytest.raises(UnsupportedResumeFormatError):
        extract_resume_text(b"plain text resume", filename="resume.txt")


def test_missing_file_raises() -> None:
    with pytest.raises(ResumeParseError):
        extract_resume_text(FIXTURES / "does_not_exist.pdf")


def test_parser_has_no_llm_imports() -> None:
    source = Path("app/parsers/resume_parser.py").read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langchain" not in lowered
    assert "openai" not in lowered
    assert "gemini" not in lowered
    assert "get_chat_model" not in source
