#!/usr/bin/env python3
"""Contract for the dev-tooling .env setup.

Two guarantees:
  1. tools/_env.py parses KEY=VALUE (and `export KEY=value`) correctly, strips
     quotes, ignores comments/blanks, and never overrides a real env var.
  2. No machine-specific absolute path is hardcoded back into the build/deploy
     tooling — those must come from .env (git-ignored) or the environment.

Exit 0 = pass.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import parse_dotenv, load_dotenv

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

# Substrings that indicate a machine-specific path baked into tooling. These are
# exactly the defaults we removed; they must only ever live in a local .env.
BANNED = [
    "SteamLibrary",
    "Program Files (x86)\\Steam",
    ":\\mods\\",
    ":/mods/",
    "/d/mods/",
    "D:\\Games",
]

# Files that legitimately contain example paths for humans, not code defaults.
SCAN_SUFFIXES = (".py", ".ps1", ".sh")
SELF = Path(__file__).name


def test_parse() -> list[str]:
    errs: list[str] = []
    sample = "\n".join([
        "# comment",
        "",
        "FALLOUT4_ESM=C:\\Games\\Fallout 4\\Data\\Fallout4.esm",
        'PICKMANS_WHISPER_DEPLOY="C:\\my mods\\PickmansWhisper"',
        "export CAPRICA='C:\\tools\\Caprica.exe'",
        "IGNORED_NO_EQUALS",
    ])
    d = parse_dotenv(sample)
    if d.get("FALLOUT4_ESM") != "C:\\Games\\Fallout 4\\Data\\Fallout4.esm":
        errs.append(f"FALLOUT4_ESM parsed wrong: {d.get('FALLOUT4_ESM')!r}")
    if d.get("PICKMANS_WHISPER_DEPLOY") != "C:\\my mods\\PickmansWhisper":
        errs.append(f"quoted value not stripped: {d.get('PICKMANS_WHISPER_DEPLOY')!r}")
    if d.get("CAPRICA") != "C:\\tools\\Caprica.exe":
        errs.append(f"export/quoted value wrong: {d.get('CAPRICA')!r}")
    if "IGNORED_NO_EQUALS" in d:
        errs.append("line without '=' should be ignored")
    if "# comment" in d or "" in d:
        errs.append("comments/blanks should be ignored")
    return errs


def test_no_override(tmp: Path) -> list[str]:
    errs: list[str] = []
    key = "PW_TEST_ENV_OVERRIDE"
    os.environ[key] = "real-env-wins"
    tmp.write_text(f"{key}=from-dotenv\n", encoding="utf-8")
    try:
        load_dotenv(tmp)
        if os.environ.get(key) != "real-env-wins":
            errs.append("load_dotenv must NOT override an existing env var")
    finally:
        os.environ.pop(key, None)
        tmp.unlink(missing_ok=True)
    return errs


def test_no_hardcoded_paths() -> list[str]:
    errs: list[str] = []
    for path in sorted(TOOLS.iterdir()):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        if path.name == SELF:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in BANNED:
            if needle in text:
                errs.append(f"{path.name}: hardcoded machine path {needle!r} (move to .env)")
    return errs


def test_env_is_gitignored() -> list[str]:
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if not re.search(r"(?m)^\.env\s*$", gi):
        return [".gitignore must ignore '.env'"]
    if not (ROOT / ".env.example").is_file():
        return [".env.example template must exist"]
    return []


def main() -> int:
    errors: list[str] = []
    errors += test_parse()
    errors += test_no_override(TOOLS / "_pw_env_test.tmp")
    errors += test_no_hardcoded_paths()
    errors += test_env_is_gitignored()

    if errors:
        print("FAIL env loader / no-hardcoded-path contract")
        for e in errors:
            print("  - " + e)
        return 1
    print("PASS env loader / no-hardcoded-path contract")
    print("  .env parsing (quotes/export/comments) + real-env precedence")
    print("  no machine-specific paths baked into tools/*.{py,ps1,sh}")
    print("  .env is git-ignored; .env.example template present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
