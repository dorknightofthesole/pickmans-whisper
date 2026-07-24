#!/usr/bin/env python3
"""Contracts for C5 P5 sleep recognition lines.

Locks:
  - SleepRecognitionLines.txt exists, files-only, enough nameless + {name} lines
  - LoadSleepRecognitionLines via LoadStageBank; LoadLineBanks calls it
  - IsActorSleeping uses GetSleepState() >= 3
  - SpeakRecognitionLine picks sleep bank when asleep, awake bank otherwise
  - Actor.psc stub declares real FO4 GetSleepState Native
  - No hard-coded mirror of sleep lines in PSC
  - MaybeSpeakNoticeLine stays free of sleep ownership

Usage:
  python tools/test_sleep_recognition.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
CONFIG = ROOT / "Data" / "PickmansWhisper" / "config"
SLEEP_FILE = CONFIG / "SleepRecognitionLines.txt"
ACTOR_STUB = ROOT / "tools" / "stubs" / "Actor.psc"

MIN_LINES = 6
MIN_NAMELESS = 3
MIN_NAMED = 2


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def parse_lines(path: Path) -> list[str]:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Function|Bool Function|Int Function|String Function|String\[\] Function)\s+{name}\s*\(",
        text,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
    return text[start : start + end_m.end()]


def test_file() -> None:
    if not SLEEP_FILE.is_file():
        fail(f"missing {SLEEP_FILE}")
    lines = parse_lines(SLEEP_FILE)
    if len(lines) < MIN_LINES:
        fail(f"SleepRecognitionLines.txt needs >= {MIN_LINES} lines, got {len(lines)}")
    nameless = [ln for ln in lines if "{name}" not in ln]
    named = [ln for ln in lines if "{name}" in ln]
    if len(nameless) < MIN_NAMELESS:
        fail(f"need >= {MIN_NAMELESS} nameless sleep lines, got {len(nameless)}")
    if len(named) < MIN_NAMED:
        fail(f"need >= {MIN_NAMED} {{name}} sleep lines, got {len(named)}")
    # Tone markers — dream / watch / sleep should show up in the bank
    blob = " ".join(lines).casefold()
    if "dream" not in blob and "sleep" not in blob:
        fail("sleep bank should mention dreaming or sleeping")
    if "watch" not in blob and "hours" not in blob:
        fail("sleep bank should include watching / hours motif")
    ok(f"SleepRecognitionLines.txt ({len(lines)} lines, {len(nameless)} nameless, {len(named)} named)")


def test_stub() -> None:
    stub = ACTOR_STUB.read_text(encoding="utf-8")
    if "Function GetSleepState" not in stub:
        fail("Actor.psc stub must declare GetSleepState")
    if not re.search(r"Int\s+Function\s+GetSleepState\s*\(\s*\)\s*Native", stub):
        fail("GetSleepState must be Int Function ... Native (real FO4)")
    ok("Actor.GetSleepState stub is real FO4 Native")


def test_psc(text: str) -> None:
    for name in (
        "LoadSleepRecognitionLines",
        "IsActorSleeping",
        "PickSleepRecognitionLine",
        "SpeakRecognitionLine",
    ):
        extract_function(text, name)
    ok("P5 sleep helpers present")

    load_banks = extract_function(text, "LoadLineBanks")
    if "LoadSleepRecognitionLines()" not in load_banks:
        fail("LoadLineBanks must call LoadSleepRecognitionLines()")
    ok("LoadLineBanks loads sleep recognition")

    load_sleep = extract_function(text, "LoadSleepRecognitionLines")
    if 'LoadStageBank("SleepRecognitionLines.txt"' not in load_sleep:
        fail('LoadSleepRecognitionLines must LoadStageBank("SleepRecognitionLines.txt"...)')
    sample = "You could watch her for hours. Maybe you will."
    if sample in text:
        fail("PSC must not hard-code SleepRecognitionLines.txt content")
    ok("files-only sleep recognition load")

    sleeping = extract_function(text, "IsActorSleeping")
    if "GetSleepState()" not in sleeping:
        fail("IsActorSleeping must call GetSleepState()")
    if "st >= 3" not in sleeping and "st>=3" not in sleeping:
        fail("IsActorSleeping must treat GetSleepState >= 3 as asleep")
    ok("IsActorSleeping uses GetSleepState >= 3")

    speak = extract_function(text, "SpeakRecognitionLine")
    if "IsActorSleeping" not in speak:
        fail("SpeakRecognitionLine must check IsActorSleeping")
    if "PickSleepRecognitionLine" not in speak:
        fail("SpeakRecognitionLine must PickSleepRecognitionLine when asleep")
    if "PickRecognitionLine" not in speak:
        fail("SpeakRecognitionLine must still PickRecognitionLine when awake")
    if "ShowVoiceToast" not in speak:
        fail("SpeakRecognitionLine must ShowVoiceToast")
    # False "file not loaded" toast burned in-game when bank status was "15 lines".
    if "SleepRecognitionLineCount <= 0" not in speak:
        fail("SpeakRecognitionLine must only claim SleepRecognitionLines.txt missing when count <= 0")
    if "pick empty" not in speak:
        fail("SpeakRecognitionLine must Trace pick-empty separately from missing file")
    pick = extract_function(text, "PickSleepRecognitionLine")
    if "ApplyNamePlaceholder" not in pick:
        fail("PickSleepRecognitionLine must ApplyNamePlaceholder before return")
    if "While attempt" not in pick:
        fail("PickSleepRecognitionLine must retry when placeholder strip yields empty")
    load_sleep = extract_function(text, "LoadSleepRecognitionLines")
    if not re.search(
        r"SleepRecognitionLineCount\s*=\s*0\s*\n\s*SleepRecognitionLines\s*=\s*new",
        load_sleep,
    ):
        fail("LoadSleepRecognitionLines must zero count before new String[64] (stale-slot race)")
    ok("SpeakRecognitionLine branches sleep vs awake banks")

    notice = extract_function(text, "MaybeSpeakNoticeLine")
    if "PickSleepRecognitionLine" in notice or "IsActorSleeping" in notice:
        fail("MaybeSpeakNoticeLine must stay free of sleep recognition ownership")
    ok("MaybeSpeakNoticeLine untouched by P5")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_file()
    test_stub()
    test_psc(text)
    print("All sleep-recognition (C5 P5) contracts passed.")


if __name__ == "__main__":
    main()
