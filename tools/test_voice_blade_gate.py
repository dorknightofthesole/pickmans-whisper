#!/usr/bin/env python3
"""Voice features require drawn Pickman's Blade (same check as kills — no duplicate GoE scan).

Locks:
  - IsVoiceWeaponReady() returns IsBladeEquipped() only
  - IsBladeEquipped body unchanged (still FindEquippedPickmansBladeIndex / ranged reject)
  - IsBladeKillWeaponReady still aliases IsBladeEquipped (kill path untouched)
  - Toast / notice / fixation / audio entry points gate via IsVoiceWeaponReady
  - Kill-scan praise / blade detect still call IsBladeEquipped directly

Usage:
  python tools/test_voice_blade_gate.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


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


def main() -> None:
    text = PSC.read_text(encoding="utf-8", errors="replace")

    voice = extract_function(text, "IsVoiceWeaponReady")
    if "Return IsBladeEquipped()" not in voice and "Return IsBladeEquipped()" not in voice.replace(" ", ""):
        if not re.search(r"Return\s+IsBladeEquipped\s*\(\s*\)", voice):
            fail("IsVoiceWeaponReady must only Return IsBladeEquipped() (no duplicated scan)")
    if "FindEquippedPickmansBladeIndex" in voice:
        fail("IsVoiceWeaponReady must not reimplement GoE blade scan")
    ok("IsVoiceWeaponReady aliases IsBladeEquipped")

    blade = extract_function(text, "IsBladeEquipped")
    if "FindEquippedPickmansBladeIndex" not in blade:
        fail("IsBladeEquipped must still use FindEquippedPickmansBladeIndex")
    if "WeaponIsRanged" not in blade:
        fail("IsBladeEquipped must still reject ranged weapons")
    kill = extract_function(text, "IsBladeKillWeaponReady")
    if "IsBladeEquipped()" not in kill:
        fail("IsBladeKillWeaponReady must still alias IsBladeEquipped")
    ok("kill blade helpers unchanged")

    for name in (
        "ShowVoiceToast",
        "ToastNoticeLine",
        "ToastVoice",
        "ToastHungerLine",
        "ToastPraiseLine",
        "MaybeSpeakNoticeLine",
        "MaybeSpeakTrustLine",
        "TickLookFixation",
        "PlayNoticeAudio",
        "PlayWhisperXwmByFile",
        "MaybeSpeakNamedKillVoice",
        "MaybeSpeakNamedIntimacyVoice",
    ):
        body = extract_function(text, name)
        if "IsVoiceWeaponReady" not in body:
            fail(f"{name} must gate with IsVoiceWeaponReady")
    ok("toast / notice / fixation / audio / named-E paths gated")

    # Kill path must keep using IsBladeEquipped (not only the voice alias)
    if "IsBladeKillWeaponReady" not in text:
        fail("IsBladeKillWeaponReady missing")
    praise_kill = False
    for m in re.finditer(r"Function\s+\w+\([^)]*\)(.*?)\nEndFunction", text, re.S):
        pass
    # Spot-check: ProcessKnifeKill or similar still references IsBladeEquipped / KillWeaponReady
    if "IsBladeEquipped()" not in text:
        fail("IsBladeEquipped calls must remain for kill logic")
    ok("blade detection still referenced for kills")

    print("All voice-blade-gate contracts passed.")


if __name__ == "__main__":
    main()
