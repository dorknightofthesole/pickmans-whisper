"""Contract: knife hunger SPECIAL stand-in must not ModValue-stack across loads."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(src: str, name: str) -> str:
    m = re.search(
        rf"(?:Bool|Int|Float|String|Function)\s+Function\s+{re.escape(name)}\s*\(",
        src,
    )
    if not m:
        # Property-less Function
        m = re.search(rf"Function\s+{re.escape(name)}\s*\(", src)
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", src[start:])
    if not end_m:
        fail(f"unclosed function {name}")
    return src[start : start + end_m.end()]


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    src = PSC.read_text(encoding="utf-8", errors="replace")

    if "HungerSpecialPenaltyDepth" not in src:
        fail("Main must track HungerSpecialPenaltyDepth for SPECIAL ModValue bookkeeping")
    if "Function ReconcileHungerSpecialPenaltyFlags" not in src:
        fail("Main must ReconcileHungerSpecialPenaltyFlags on load")
    if "Function RepairHungerSpecialStacks" not in src:
        fail("Main must expose RepairHungerSpecialStacks for MCM stack repair")

    resume = extract_function(src, "HandleGameResume")
    if "ReconcileHungerSpecialPenaltyFlags" not in resume:
        fail("HandleGameResume must ReconcileHungerSpecialPenaltyFlags before Sync")
    if resume.find("ReconcileHungerSpecialPenaltyFlags") > resume.find("SyncHungerAddictionSpell"):
        fail("HandleGameResume must reconcile before SyncHungerAddictionSpell")

    if "Function GetSpecialModDelta" not in src:
        fail("Main must GetSpecialModDelta (GetValue - GetBaseValue)")
    if "Function IsSpecialModAtMinusTwoFloor" not in src:
        fail("Main must IsSpecialModAtMinusTwoFloor (delta <= -2)")
    delta = extract_function(src, "GetSpecialModDelta")
    if "GetBaseValue" not in delta or "GetValue" not in delta:
        fail("GetSpecialModDelta must use GetValue - GetBaseValue")
    floor = extract_function(src, "IsSpecialModAtMinusTwoFloor")
    if "<= -2.0" not in floor and "<= -2" not in floor:
        fail("IsSpecialModAtMinusTwoFloor must treat delta <= -2 as floor")

    apply = extract_function(src, "ApplyHungerStatPenalty")
    if "HungerSpecialPenaltyDepth" not in apply:
        fail("ApplyHungerStatPenalty must honor HungerSpecialPenaltyDepth")
    if "already applied" not in apply:
        fail("ApplyHungerStatPenalty must skip + Trace when already applied")
    if "IsSpecialModAtMinusTwoFloor" not in apply:
        fail("ApplyHungerStatPenalty must skip ModValue when SPECIAL mod already <= -2")
    if "mod already <= -2" not in apply:
        fail("ApplyHungerStatPenalty must Trace floor skip")
    if apply.count("ModValue") < 2:
        fail("ApplyHungerStatPenalty must ModValue AGI and CHA when first applying")

    clear = extract_function(src, "ClearHungerStatPenalty")
    if "While i < n" not in clear:
        fail("ClearHungerStatPenalty must restore ModValue for depth n")
    if "HungerSpecialPenaltyDepth = 0" not in clear:
        fail("ClearHungerStatPenalty must zero depth")

    sync = extract_function(src, "SyncHungerAddictionSpell")
    if "ReconcileHungerSpecialPenaltyFlags" not in sync:
        fail("SyncHungerAddictionSpell must reconcile flags/depth")
    if "HungerSpecialPenaltyDepth <= 0" not in sync:
        fail("SyncHungerAddictionSpell must not apply when depth already > 0")

    repair = extract_function(src, "RepairHungerSpecialStacks")
    if "SyncHungerAddictionSpell" in repair:
        fail("RepairHungerSpecialStacks must not Sync (would ModValue -1 again)")
    if "ModValue" not in repair:
        fail("RepairHungerSpecialStacks must ModValue +1")
    if "SPECIAL repair enter" not in repair:
        fail("RepairHungerSpecialStacks must Trace enter (proves MCM CallFunction ran)")
    if "Debug.Notification" not in repair:
        fail("RepairHungerSpecialStacks must Notification immediately on enter")

    mcm = MCM.read_text(encoding="utf-8", errors="replace")
    if "RepairHungerSpecialStacks" not in mcm:
        fail("MCM config.json must wire RepairHungerSpecialStacks button")

    ok("hunger SPECIAL depth + reconcile + repair + -2 floor (no ModValue stack)")
    print("All hunger-special-penalty contracts passed.")


if __name__ == "__main__":
    main()
