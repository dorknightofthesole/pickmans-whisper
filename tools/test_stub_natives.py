#!/usr/bin/env python3
"""Forbid known fake / Skyrim-only Native stubs in tools/stubs.

Caps the no-fake-native-stubs rule: Caprica only sees stubs, so wishful Natives
compile green and die in-game. This list is burn history + audited landmines.

Usage:
  python tools/test_stub_natives.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "tools" / "stubs"
USER_SCRIPTS = ROOT / "Data" / "Scripts" / "Source" / "User"

# (relative stub file, regex that must NOT match a Native declaration / call)
FORBIDDEN = [
    (
        "Quest.psc",
        r"Bool\s+Function\s+IsRunning\s*\(\s*\)\s*\n\s*Return",
        "Quest.IsRunning dummy body (must be Native)",
    ),
    (
        "Game.psc",
        r"Function\s+GetCurrentCrosshairRef\s*\(",
        "Game.GetCurrentCrosshairRef (Skyrim SKSE / optional extender, not base FO4)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForUpdate\s*\(",
        "ScriptObject.RegisterForUpdate (removed in FO4; use StartTimer)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForSingleUpdate\s*\(",
        "ScriptObject.RegisterForSingleUpdate (removed in FO4; use StartTimer)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+UnregisterForUpdate\s*\(",
        "ScriptObject.UnregisterForUpdate (removed in FO4)",
    ),
    (
        "ScriptObject.psc",
        r"Event\s+OnUpdate\s*\(",
        "ScriptObject.OnUpdate (removed in FO4; use OnTimer)",
    ),
    (
        "Math.psc",
        r"Function\s+NumberOfSetBits\s*\(",
        "Math.NumberOfSetBits (not in FO4 Math.psc)",
    ),
    (
        "Input.psc",
        r"Function\s+IsKeyPressed\s*\(",
        "Input.IsKeyPressed (Skyrim SKSE; FO4 uses RegisterForKey + OnKeyDown)",
    ),
    (
        "Actor.psc",
        r"Function\s+HasLOS\s*\(",
        "Actor.HasLOS (Skyrim; FO4 uses HasDetectionLOS / RegisterForDirectLOS*)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForLOS\s*\(",
        "ScriptObject.RegisterForLOS (not FO4; use RegisterForDirectLOSGain/Lost)",
    ),
]

# Real FO4 APIs Slice G needs — must stay Native in stubs.
REQUIRED_NATIVES = [
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForPlayerSleep\s*\(\s*\)\s*Native",
        "RegisterForPlayerSleep",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForDirectLOSGain\s*\(",
        "RegisterForDirectLOSGain",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForDirectLOSLost\s*\(",
        "RegisterForDirectLOSLost",
    ),
    (
        "Actor.psc",
        r"Bool\s+Function\s+HasDetectionLOS\s*\(",
        "HasDetectionLOS",
    ),
    (
        "Actor.psc",
        r"Function\s+KillSilent\s*\(",
        "KillSilent",
    ),
    (
        "Actor.psc",
        r"Bool\s+Function\s+SnapIntoInteraction\s*\(",
        "SnapIntoInteraction",
    ),
]

# Calls in our scripts that must never appear (even if stub is gone).
FORBIDDEN_CALLS = [
    (r"Game\.GetCurrentCrosshairRef\s*\(\s*\)", "Game.GetCurrentCrosshairRef()"),
    (r"\bRegisterForUpdate\s*\(", "RegisterForUpdate("),
    (r"\bRegisterForSingleUpdate\s*\(", "RegisterForSingleUpdate("),
    (r"\bUnregisterForUpdate\s*\(", "UnregisterForUpdate("),
    (r"Math\.NumberOfSetBits\s*\(", "Math.NumberOfSetBits("),
    (r"Input\.IsKeyPressed\s*\(", "Input.IsKeyPressed("),
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not STUBS.is_dir():
        fail(f"missing stubs dir {STUBS}")

    for rel, pattern, why in FORBIDDEN:
        path = STUBS / rel
        if not path.is_file():
            # Input.psc must not exist with IsKeyPressed; absence is fine.
            if rel == "Input.psc":
                continue
            fail(f"missing stub {rel}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(pattern, text):
            fail(f"{rel}: forbidden Native/event — {why}")
        print(f"OK: {rel} clean of {why.split('(')[0].strip()}")

    # Input.psc must not be introduced as a Skyrim key-poll stub
    input_psc = STUBS / "Input.psc"
    if input_psc.is_file():
        text = input_psc.read_text(encoding="utf-8", errors="replace")
        if re.search(r"Function\s+IsKeyPressed\s*\(", text):
            fail("Input.psc: forbidden IsKeyPressed Native")

    for rel, pattern, label in REQUIRED_NATIVES:
        path = STUBS / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        if not re.search(pattern, text):
            fail(f"{rel}: missing required Native {label}")
        print(f"OK: {rel} declares {label}")

    for psc in sorted(USER_SCRIPTS.glob("*.psc")):
        text = psc.read_text(encoding="utf-8", errors="replace")
        for pattern, label in FORBIDDEN_CALLS:
            if re.search(pattern, text):
                fail(f"{psc.name}: forbidden call {label}")
        if re.search(r"\bHasLOS\s*\(", text):
            fail(f"{psc.name}: forbidden Skyrim HasLOS (use HasDetectionLOS / DirectLOS)")
        if re.search(r"\bRegisterForLOS\s*\(", text):
            fail(f"{psc.name}: forbidden RegisterForLOS (use RegisterForDirectLOSGain/Lost)")
    print("OK: user scripts have no forbidden Skyrim/fake native calls")
    print("All stub-native contracts passed.")


if __name__ == "__main__":
    main()
