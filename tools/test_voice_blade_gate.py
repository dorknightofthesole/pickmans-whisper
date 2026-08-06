#!/usr/bin/env python3
"""Voice features and Bed Gift require Pickman's Blade EQUIPPED (drawn) — same
requirement as kill crediting. Was ownership-only ("on the player, not necessarily
drawn") until confirmed live that let ambient notice lines speak with the blade merely
owned/sheathed; the blade is what "speaks," so it must be in hand.

Locks:
  - IsVoiceWeaponReady() on VoiceAlias returns Main().IsBladeEquipped() (drawn)
  - IsBladeKillWeaponReady still aliases IsBladeEquipped (kill path untouched)
  - Toast / notice / fixation / audio entry points gate via IsVoiceWeaponReady
  - Kill-scan praise / blade detect still call IsBladeEquipped directly
  - BedGiftScript's two real spawn triggers (MaybeWarmBedGiftBody, TrySpawnBedCorpse's
    non-force path) now also require IsBladeEquipped() — previously had NO blade
    requirement at all beyond gating the wake TOAST text, not the spawn itself

Usage:
  python tools/test_voice_blade_gate.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
VOICE_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
BED_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperBedGiftScript.psc"


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
    main_text = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    voice_text = VOICE_PSC.read_text(encoding="utf-8", errors="replace")

    voice = extract_function(voice_text, "IsVoiceWeaponReady")
    if not re.search(r"Return\s+Main\(\)\.IsBladeEquipped\s*\(\s*\)", voice):
        fail(
            "IsVoiceWeaponReady must Return Main().IsBladeEquipped() (drawn) — "
            "same requirement as kill crediting"
        )
    if re.search(r"Return\s+PlayerHasBlade\s*\(\s*\)", voice):
        fail(
            "IsVoiceWeaponReady must not go back to ownership-only (PlayerHasBlade) — "
            "confirmed live this let whispers speak with the blade merely owned/sheathed"
        )
    ok("IsVoiceWeaponReady aliases Main().IsBladeEquipped (drawn, not just owned)")

    kill = extract_function(main_text, "IsBladeKillWeaponReady")
    if "IsBladeEquipped()" not in kill:
        fail("IsBladeKillWeaponReady must still alias IsBladeEquipped")
    ok("IsBladeKillWeaponReady aliases IsBladeEquipped")

    for name in (
        "ShowVoiceToast",
        "ToastNoticeLine",
        "MaybeSpeakNoticeLine",
        "TickLookFixation",
        "PlayNoticeAudio",
        "PlayWhisperXwmByFile",
        "MaybeSpeakNamedIntimacyEvent",
    ):
        body = extract_function(voice_text, name)
        if "IsVoiceWeaponReady" not in body:
            fail(f"{name} must gate with IsVoiceWeaponReady (VoiceAlias)")
    for name in (
        "ToastVoice",
        "ToastHungerLine",
        "ToastPraiseLine",
        "MaybeSpeakTrustLine",
        "MaybeSpeakNamedKillVoice",
    ):
        body = extract_function(main_text, name)
        if "IsVoiceWeaponReady" not in body:
            fail(f"{name} must gate with IsVoiceWeaponReady (via VoiceAlias)")
    ok("toast / notice / fixation / audio / named-E paths gated")

    for name in (
        "LastTrustToastRealTime",
        "LastHungerToastRealTime",
        "LastPraiseToastRealTime",
        "TRUST_TOAST_COOLDOWN",
        "HUNGER_TOAST_COOLDOWN",
        "PRAISE_TOAST_COOLDOWN",
    ):
        if f"Float {name}" in main_text or f"\n{name} =" in main_text:
            # Declarations must live on VoiceAlias; Main may only reference VoiceAlias.*
            if f"Float {name}" in main_text:
                fail(f"{name} must be declared on VoiceAlias, not Main")
        if f"Float Property {name}" not in voice_text and f"Float {name}" not in voice_text:
            fail(f"{name} must be declared on VoiceAlias")
        # Cross-script access from Main requires Property (not a plain script var).
        if f"Float Property {name}" not in voice_text:
            fail(f"{name} must be Property on VoiceAlias (Main reads/writes it)")
        if f"VoiceAlias.{name}" not in main_text:
            fail(f"Main toast paths must use VoiceAlias.{name}")
    ok("trust/hunger/praise toast cools owned by VoiceAlias")

    if "IsBladeKillWeaponReady" not in main_text:
        fail("IsBladeKillWeaponReady missing")
    if "IsBladeEquipped()" not in main_text:
        fail("IsBladeEquipped calls must remain for kill logic")
    ok("blade detection still referenced for kills")

    notice = extract_function(voice_text, "MaybeSpeakNoticeLine")
    if "skip: no Pickman's Blade" not in notice:
        fail(
            "MaybeSpeakNoticeLine skip status copy must be present "
            "(unchanged text; underlying gate is now drawn-required)"
        )
    ok("notice skip copy unchanged (gate logic is what changed, not the message)")

    bed = BED_PSC.read_text(encoding="utf-8", errors="replace")
    warm = extract_function(bed, "MaybeWarmBedGiftBody")
    if "m.IsBladeEquipped()" not in warm:
        fail(
            "MaybeWarmBedGiftBody must require m.IsBladeEquipped() — previously had "
            "NO blade requirement on the spawn itself"
        )
    spawn = extract_function(bed, "TrySpawnBedCorpse")
    if "m.IsBladeEquipped()" not in spawn:
        fail(
            "TrySpawnBedCorpse must require m.IsBladeEquipped() in its non-force "
            "(!abForce) gated path"
        )
    # abForce=True is the deliberate MCM Debug bypass-everything path — must stay untouched.
    force_idx = spawn.find("If !abForce")
    blade_idx = spawn.find("m.IsBladeEquipped()")
    if force_idx < 0 or blade_idx < force_idx:
        fail(
            "TrySpawnBedCorpse's blade check must live inside the !abForce block, "
            "not before it (force path must still bypass everything)"
        )
    ok(
        "Bed Gift spawn triggers (MaybeWarmBedGiftBody, TrySpawnBedCorpse non-force) "
        "require IsBladeEquipped"
    )

    print("All voice-blade-gate contracts passed.")


if __name__ == "__main__":
    main()
