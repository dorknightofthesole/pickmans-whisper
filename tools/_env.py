"""Minimal .env loader for dev tooling (no external dependencies).

Reads KEY=VALUE lines from <repo-root>/.env and populates os.environ WITHOUT
overriding variables already set in the real environment. The .env file is
git-ignored so each machine keeps its own paths (Fallout4.esm, MO2 mods dir)
instead of hardcoding them into the repo.

Supported line forms:
    KEY=value
    export KEY=value
    # comments and blank lines are ignored
Surrounding single/double quotes around the value are stripped.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_dotenv(text: str) -> dict[str, str]:
    """Parse .env text into a dict (does not touch os.environ)."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        if key:
            out[key] = val
    return out


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Load <repo-root>/.env into os.environ (real env vars win). Returns the
    parsed dict. Missing file is a no-op."""
    env_path = path or (ROOT / ".env")
    try:
        text = env_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    parsed = parse_dotenv(text)
    for key, val in parsed.items():
        if key not in os.environ:
            os.environ[key] = val
    return parsed
