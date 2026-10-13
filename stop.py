"""Stop project containers started via run.py."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def detect_compose_command() -> list[str]:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed.")
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
    raise RuntimeError("Docker Compose is not available.")


def main() -> int:
    compose = detect_compose_command()
    subprocess.run([*compose, "down"], check=True, cwd=ROOT)
    print("Stopped AI Recruitment Agent.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI safety net
        print(exc)
        raise SystemExit(1) from exc
