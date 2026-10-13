from pathlib import Path

from run import ensure_env_file, read_env_value


def test_ensure_env_file_creates_from_example(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("RECRUITER_USERNAME=recruiter\n", encoding="utf-8")
    created = ensure_env_file(tmp_path)
    assert created is True
    assert (tmp_path / ".env").read_text(encoding="utf-8").strip() == "RECRUITER_USERNAME=recruiter"


def test_ensure_env_file_is_idempotent(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("KEEP=true\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("KEEP=false\n", encoding="utf-8")
    created = ensure_env_file(tmp_path)
    assert created is False
    assert (tmp_path / ".env").read_text(encoding="utf-8").strip() == "KEEP=true"


def test_read_env_value_returns_default_when_missing(tmp_path: Path) -> None:
    assert read_env_value(tmp_path, "RECRUITER_USERNAME", "recruiter") == "recruiter"


def test_read_env_value_reads_existing_value(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "RECRUITER_USERNAME=custom\nRECRUITER_PASSWORD=secret\n",
        encoding="utf-8",
    )
    assert read_env_value(tmp_path, "RECRUITER_USERNAME", "recruiter") == "custom"
