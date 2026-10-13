"""Create a local .env from .env.example. Never overwrites an existing file."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"


def main() -> int:
    if TARGET.exists():
        print(f"Using existing {TARGET} (not overwritten)")
        return 0
    if not EXAMPLE.exists():
        print("Missing .env.example")
        return 1
    TARGET.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Created {TARGET} from .env.example")
    print("Demo login: recruiter / recruiter-review")
    print("Optional: add GOOGLE_API_KEY for JD analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
