from pathlib import Path

from scripts.bootstrap_env import main


def test_bootstrap_creates_env_once(tmp_path: Path, monkeypatch) -> None:
    example = tmp_path / ".env.example"
    example.write_text("RECRUITER_USERNAME=recruiter\nGOOGLE_API_KEY=\n", encoding="utf-8")
    target = tmp_path / ".env"
    monkeypatch.setattr("scripts.bootstrap_env.EXAMPLE", example)
    monkeypatch.setattr("scripts.bootstrap_env.TARGET", target)
    assert main() == 0
    assert "recruiter" in target.read_text(encoding="utf-8")
    target.write_text("RECRUITER_USERNAME=keep-me\n", encoding="utf-8")
    assert main() == 0
    assert target.read_text(encoding="utf-8") == "RECRUITER_USERNAME=keep-me\n"


def test_env_example_has_demo_login_and_no_live_keys() -> None:
    text = Path(".env.example").read_text(encoding="utf-8")
    assert "RECRUITER_USERNAME=recruiter" in text
    assert "RECRUITER_PASSWORD=recruiter-review" in text
    assert "EMAIL_DRY_RUN=true" in text
    assert "CALENDAR_DRY_RUN=true" in text
    assert "AKIA" not in text
    assert "AIza" not in text
