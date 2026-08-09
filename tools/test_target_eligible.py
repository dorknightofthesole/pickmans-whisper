#!/usr/bin/env python3
"""Hard-gate eligibility — single IsValidTarget(Actor) on Main.

Owns the identity checklist plus living hostility and in-range/loaded
(TargetScan.KILL_WATCH_RADIUS SSOT — not same-cell). Notice cooldown must NOT
live in IsValidTarget. Corpses skip IsHostileToActor so decay RegisterTarget
still works. No LastKillIgnoreReason Autovar; reject reasons go to Debug.Trace only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
VOICE = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
MCM_CFG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Bool|String|Int|Float|Actor|Form)?\s*Function {re.escape(name)}\s*\((.*?)\)(.*?)EndFunction",
        text,
        re.S,
    )
    if not m:
        fail(f"{name} not found")
    return m.group(2)


def main() -> None:
    if not MAIN.is_file():
        fail(f"missing {MAIN}")
    text = MAIN.read_text(encoding="utf-8", errors="replace")

    if "LastKillIgnoreReason" in text:
        fail("LastKillIgnoreReason must be deleted — no Autovar reason side-channel")
    if "IsValidNamingTarget" in text:
        fail("IsValidNamingTarget must be deleted — use IsValidTarget")
    if "sLastKill" in text:
        fail("Main must not write sLastKill MCM")

    # Signature: hard gate only — no abRequireAlive
    if re.search(r"Bool Function IsValidTarget\s*\(\s*Actor ak\s*,", text):
        fail("IsValidTarget must not take abRequireAlive (alive/dead is feature-side)")
    if not re.search(r"Bool Function IsValidTarget\s*\(\s*Actor ak\s*\)", text):
        fail("IsValidTarget(Actor ak) hard-gate signature missing")

    body = extract_function(text, "IsValidTarget")
    for needle in (
        "IsChildNpc",
        "IsChildTargetAllowed",
        "IsPlayerTeammate",
        "IsStoryEssential",
        "IsHumanNpc",
        "IsAdultFemale",
        "IsDisabled",
        "IsHostileToActor",
    ):
        if needle not in body:
            fail(f"IsValidTarget must check {needle}")

    if "IsDead()" not in body:
        fail("IsValidTarget must skip hostility for corpses (!IsDead before IsHostileToActor)")

    if "KILL_WATCH_RADIUS" not in body or "TargetScan()" not in body:
        fail("IsValidTarget must range-gate via TargetScan().KILL_WATCH_RADIUS (SSOT)")
    if "Is3DLoaded()" not in body:
        fail("IsValidTarget must reject !Is3DLoaded (far/unloaded refs)")
    if "GetParentCell()" in body:
        fail("IsValidTarget must not use GetParentCell same-cell (breaks exterior borders)")

    for banned in (
        "WasFriendlySeen",
        "NoteFriendlySeen",
        "IsNoticeOnCooldown",
        "LastKillIgnoreReason",
        "ExplainNonHumanForNotice",
    ):
        if banned in body:
            fail(f"IsValidTarget must not contain feature/soft check {banned}")

    reject_traces = body.count('Debug.Trace("PickmansWhisper: target reject')
    if reject_traces < 8:
        fail(
            f"IsValidTarget must Trace each reject branch "
            f'(found {reject_traces} "target reject" traces, expected >= 8)'
        )
    ok("IsValidTarget: hard gate + living hostility + range/loaded Trace, no friendly-seen/cooldown Autovar")

    if MCM_CFG.is_file():
        mcm = MCM_CFG.read_text(encoding="utf-8", errors="replace")
        if "sLastKill" in mcm:
            fail("MCM config must not expose sLastKill:Debug")
        ok("MCM sLastKill removed")

    voice = VOICE.read_text(encoding="utf-8", errors="replace")
    if "FormatNoticeActorChecklist" in voice:
        fail("FormatNoticeActorChecklist must be deleted")
    notice = extract_function(voice, "ExplainNoticeReject")
    if "IsValidTarget" not in notice:
        fail("ExplainNoticeReject must call Main IsValidTarget for hard gate")
    if "ExplainNonHumanForNotice" in notice:
        fail("ExplainNoticeReject must not re-implement human via ExplainNonHumanForNotice")
    if "IsAdultFemale" in notice and "IsValidTarget" in notice:
        # hard checklist must not be duplicated in notice body
        if "IsStoryEssential" in notice or "IsPlayerTeammate" in notice:
            fail("ExplainNoticeReject must not duplicate hard-checklist (teammate/essential)")
    if "KillWatchRadius()" not in notice:
        fail("ExplainNoticeReject distance must use KillWatchRadius() (TargetScan SSOT)")
    if "Main().KILL_WATCH_RADIUS" in notice or "Main().KILL_WATCH_RADIUS" in voice:
        fail("VoiceAlias must not read Main.KILL_WATCH_RADIUS — TargetScan owns range")
    if "Float Function KillWatchRadius()" not in voice:
        fail("VoiceAlias must expose KillWatchRadius() reading TargetScan.KILL_WATCH_RADIUS")
    kill_r = extract_function(voice, "KillWatchRadius")
    if "ts.KILL_WATCH_RADIUS" not in kill_r and ".KILL_WATCH_RADIUS" not in kill_r:
        fail("KillWatchRadius must return TargetScan.KILL_WATCH_RADIUS")
    ok("ExplainNoticeReject: notice feature checks + IsValidTarget")

    print("test_target_eligible.py: all checks passed")


if __name__ == "__main__":
    main()
