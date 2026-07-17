#!/usr/bin/env python3
"""Contracts for optional TargetOverrides.txt (opt-in filter gates).

Locks:
  - TargetOverrides.txt is optional (missing → safe defaults, no user Notification)
  - TargetOverrides.example.txt ships with robot example only
  - PSC loads TargetOverrides.txt and gates child/robot rejects with allow helpers
  - Knife-kill paths honor the same helpers (full mod support when enabled)
  - Parse mirror: 1/true/yes/on enable; anything else false

Usage:
  python tools/test_target_overrides.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
CFG = ROOT / "Data" / "PickmansWhisper" / "config" / "TargetOverrides.txt"
EXAMPLE = ROOT / "Data" / "PickmansWhisper" / "config" / "TargetOverrides.example.txt"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def parse_override_truthy(v: str) -> bool:
    """Mirror ParseOverrideTruthy (Papyrus == is case-insensitive)."""
    if not v:
        return False
    return v.casefold() in {"1", "true", "yes", "on"}


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Function|Bool Function|Int Function|String Function)\s+{name}\s*\(",
        text,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
    return text[start : start + end_m.end()]


def test_example_file() -> None:
    if not EXAMPLE.is_file():
        fail(f"missing {EXAMPLE}")
    text = EXAMPLE.read_text(encoding="utf-8")
    if "AllowRobots=" not in text:
        fail("example must document AllowRobots=")
    if "AllowChildFemales" in text:
        fail("example must be robot-only (no AllowChildFemales line)")
    if "TargetOverrides.txt" not in text:
        fail("example must tell players to copy to TargetOverrides.txt")
    ok("TargetOverrides.example.txt is robot-only template")


def test_optional_live_file() -> None:
    """Live TargetOverrides.txt is optional; if present, defaults must stay safe."""
    if not CFG.is_file():
        ok("TargetOverrides.txt absent (optional)")
        return
    text = CFG.read_text(encoding="utf-8")
    if re.search(r"AllowChildFemales\s*=\s*1", text) or re.search(
        r"AllowRobots\s*=\s*1", text
    ):
        fail("if TargetOverrides.txt is shipped, flags must default to 0 not 1")
    ok("TargetOverrides.txt present with safe defaults (optional)")


def test_parse_mirror() -> None:
    assert parse_override_truthy("1") is True
    assert parse_override_truthy("true") is True
    assert parse_override_truthy("YES") is True
    assert parse_override_truthy("on") is True
    assert parse_override_truthy("0") is False
    assert parse_override_truthy("false") is False
    assert parse_override_truthy("") is False
    ok("ParseOverrideTruthy mirror")


def test_psc(text: str) -> None:
    if "Function LoadTargetOverrides" not in text:
        fail("missing LoadTargetOverrides")
    load = extract_function(text, "LoadTargetOverrides")
    if "TargetOverrides.txt" not in load:
        fail("LoadTargetOverrides must read TargetOverrides.txt")
    if "TargetOverrides.example.txt" not in load:
        fail("LoadTargetOverrides must mention TargetOverrides.example.txt (optional docs)")
    if "AllowChildFemales" not in load or "AllowRobots" not in load:
        fail("LoadTargetOverrides must parse both keys")
    if "Debug.Notification" in load:
        fail("LoadTargetOverrides must not Notification — file is optional (Trace only)")
    if "optional" not in load.casefold() and "OPTIONAL" not in load:
        fail("LoadTargetOverrides should document that the file is optional")
    if "LoadLineBanks" in text:
        banks = extract_function(text, "LoadLineBanks")
        if "LoadTargetOverrides()" not in banks:
            fail("LoadLineBanks must call LoadTargetOverrides")
    ok("LoadTargetOverrides optional + wired from LoadLineBanks")

    for name in ("IsChildTargetAllowed", "IsRobotTargetAllowed", "ParseOverrideTruthy"):
        if f"Function {name}" not in text and f"Bool Function {name}" not in text:
            fail(f"missing {name}")
    ok("allow helpers present")

    notice = extract_function(text, "ExplainNoticeReject")
    if "IsChildTargetAllowed" not in notice:
        fail("ExplainNoticeReject must gate child reject with IsChildTargetAllowed")
    ok("ExplainNoticeReject child gate")

    nonhuman = extract_function(text, "ExplainNonHumanForNotice")
    if "IsRobotTargetAllowed" not in nonhuman:
        fail("ExplainNonHumanForNotice must gate robot reject with IsRobotTargetAllowed")
    ok("ExplainNonHumanForNotice robot gate")

    adult = extract_function(text, "IsAdultFemale")
    if "IsChildTargetAllowed" not in adult:
        fail("IsAdultFemale must honor IsChildTargetAllowed for child females")
    ok("IsAdultFemale child override")

    knife = extract_function(text, "IsValidKnifeKillVictim")
    if "IsChildTargetAllowed" not in knife:
        fail("IsValidKnifeKillVictim must honor IsChildTargetAllowed (full mod support)")
    ok("IsValidKnifeKillVictim child gate")

    human = extract_function(text, "IsHumanNpc")
    if "IsRobotTargetAllowed" not in human:
        fail("IsHumanNpc must honor IsRobotTargetAllowed for knife kills")
    ok("IsHumanNpc robot gate")

    track = extract_function(text, "TrackLivingNear")
    if "IsChildTargetAllowed" not in track:
        fail("TrackLivingNear must honor IsChildTargetAllowed")
    ok("TrackLivingNear child gate")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_example_file()
    test_optional_live_file()
    test_parse_mirror()
    test_psc(text)
    print("All target-override contracts passed.")


if __name__ == "__main__":
    main()
