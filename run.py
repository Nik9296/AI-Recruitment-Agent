"""One-command project startup for any device.

Usage:
  python run.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
READY_URL = "http://127.0.0.1:8000/ready"
DASHBOARD_URL = "http://localhost:3000"


def ensure_env_file(root: Path) -> bool:
    """Create .env from .env.example when missing."""
    env_path = root / ".env"
    if env_path.exists():
        return False
    example_path = root / ".env.example"
    if not example_path.exists():
        raise FileNotFoundError("Missing .env.example")
    env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def read_env_value(root: Path, key: str, default: str) -> str:
    env_path = root / ".env"
    if not env_path.exists():
        return default
    prefix = f"{key}="
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            return value or default
    return default


def detect_compose_command() -> list[str]:
    if shutil.which("docker") is None:
        raise RuntimeError(
            "Docker is not installed. Install Docker Desktop and run again."
        )
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return ["docker", "compose"]
    except subprocess.CalledProcessError:
        pass
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    raise RuntimeError("Docker Compose is not available. Update Docker Desktop.")


def wait_for_ready(url: str, timeout_seconds: int = 120) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return True
        except urllib.error.URLError:
            time.sleep(2)
    return False


def main() -> int:
    print("Starting AI Recruitment Agent...")
    created = ensure_env_file(ROOT)
    if created:
        print("Created .env from .env.example")
    else:
        print("Using existing .env")

    compose = detect_compose_command()
    subprocess.run([*compose, "up", "--build", "-d"], check=True, cwd=ROOT)

    if wait_for_ready(READY_URL):
        print("API is ready.")
    else:
        print("API is still starting. Check logs with: docker compose logs backend")

    username = read_env_value(ROOT, "RECRUITER_USERNAME", "recruiter")
    password = read_env_value(ROOT, "RECRUITER_PASSWORD", "recruiter-review")
    print(f"Dashboard: {DASHBOARD_URL}")
    print(f"Login: {username} / {password}")
    print("Stop later with: python stop.py")
    webbrowser.open(DASHBOARD_URL)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Startup command failed: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:  # pragma: no cover - CLI safety net
        print(exc)
        raise SystemExit(1) from exc
