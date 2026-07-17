#!/usr/bin/env python3
"""Regression contracts for C5 P2 recognition lines (look-fixation voice).

Locks:
  - RecognitionLines.txt exists, files-only (no builtin mirror in PSC)
  - LoadRecognitionLines via LoadStageBank; LoadLineBanks calls it
  - Voice by count: 1 silent / 2 SpeakFixationStageWhisper / 3+ SpeakRecognitionLine
  - Retire debug toast "PW fixation:"
  - 2nd look uses ToastNoticeLine (stamps hour gate); 3rd+ does not
  - GetRecognitionBank(band) stub present for later multi-band
  - No rewrite of MaybeSpeakNoticeLine to own fixation

Usage:
  python tools/test_recognition_lines.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
CONFIG = ROOT / "Data" / "PickmansWhisper" / "config"
RECOG_FILE = CONFIG / "RecognitionLines.txt"

MIN_LINES = 6
MIN_NAMELESS = 3


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
    if not RECOG_FILE.is_file():
        fail(f"missing {RECOG_FILE}")
    lines = parse_lines(RECOG_FILE)
    if len(lines) < MIN_LINES:
        fail(f"RecognitionLines.txt needs >= {MIN_LINES} lines, got {len(lines)}")
    nameless = [ln for ln in lines if "{name}" not in ln]
    if len(nameless) < MIN_NAMELESS:
        fail(f"need >= {MIN_NAMELESS} nameless recognition lines, got {len(nameless)}")
    ok(f"RecognitionLines.txt ({len(lines)} lines, {len(nameless)} nameless)")


def test_psc(text: str) -> None:
    for name in (
        "LoadRecognitionLines",
        "GetRecognitionBank",
        "GetRecognitionBankCount",
        "PickRecognitionLine",
        "SpeakFixationStageWhisper",
        "SpeakRecognitionLine",
    ):
        extract_function(text, name)
    ok("P2 recognition helpers present")

    load_banks = extract_function(text, "LoadLineBanks")
    if "LoadRecognitionLines()" not in load_banks:
        fail("LoadLineBanks must call LoadRecognitionLines()")
    ok("LoadLineBanks loads recognition")

    load_recog = extract_function(text, "LoadRecognitionLines")
    if 'LoadStageBank("RecognitionLines.txt"' not in load_recog:
        fail('LoadRecognitionLines must LoadStageBank("RecognitionLines.txt"...)')
    # No hard-coded mirror of recognition lines in PSC
    sample = "There she is again."
    if sample in text:
        fail("PSC must not hard-code RecognitionLines.txt content")
    ok("files-only recognition load")

    tick = extract_function(text, "TickLookFixation")
    if "PW fixation:" in tick:
        fail('TickLookFixation must retire "PW fixation:" debug toast')
    if "SpeakFixationStageWhisper" not in tick:
        fail("TickLookFixation must call SpeakFixationStageWhisper on 2nd look")
    if "SpeakRecognitionLine" not in tick:
        fail("TickLookFixation must call SpeakRecognitionLine on 3rd+")
    if "count == 1" not in tick and "count==1" not in tick:
        fail("TickLookFixation must branch on count == 1 (silent)")
    if "count == 2" not in tick and "count==2" not in tick:
        fail("TickLookFixation must branch on count == 2 (stage whisper)")
    if "MaybeSpeakNoticeLine" in tick:
        fail("TickLookFixation must not call MaybeSpeakNoticeLine")
    ok("TickLookFixation voice by count (silent / stage / recognition)")

    stage = extract_function(text, "SpeakFixationStageWhisper")
    if "PickNoticeLine" not in stage:
        fail("SpeakFixationStageWhisper must use PickNoticeLine")
    if "ToastNoticeLine" not in stage:
        fail("SpeakFixationStageWhisper must ToastNoticeLine (stamps hour gate)")
    ok("2nd look uses stage bank + ToastNoticeLine")

    recog = extract_function(text, "SpeakRecognitionLine")
    if "PickRecognitionLine" not in recog:
        fail("SpeakRecognitionLine must PickRecognitionLine")
    if "ToastNoticeLine" in recog:
        fail("SpeakRecognitionLine must NOT ToastNoticeLine (no hour-gate stamp)")
    if "LastNoticeToastGameTime" in recog:
        fail("SpeakRecognitionLine must not stamp LastNoticeToastGameTime")
    if "ShowVoiceToast" not in recog:
        fail("SpeakRecognitionLine must ShowVoiceToast (HUD lead-glyph pad)")
    if "Debug.Notification(" in recog and "ShowVoiceToast" not in recog:
        fail("SpeakRecognitionLine must not bare-Notification the line")
    ok("3rd+ recognition toast without hunger hour stamp")

    notice = extract_function(text, "MaybeSpeakNoticeLine")
    if "SpeakRecognitionLine" in notice or "SpeakFixationStageWhisper" in notice:
        fail("MaybeSpeakNoticeLine must stay free of fixation voice ownership")
    ok("MaybeSpeakNoticeLine untouched by P2 voice")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_file()
    test_psc(text)
    print("All recognition-lines (C5 P2) contracts passed.")


if __name__ == "__main__":
    main()
