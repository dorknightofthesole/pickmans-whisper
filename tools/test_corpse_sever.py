#!/usr/bin/env python3
"""Contracts for Slice F — blade corpse sever (/ + MSG limb menu + Dismember).

Locks:
  - Actor.Dismember / IsDismembered stubs are Native (no fake bodies)
  - Message.Show stub is Native
  - PSC RegisterForKey(53), OnKeyDown → TrySeverAimedCorpse
  - Dismember(part, False, True, True) — force sever+blood, not explode-first
  - Gates: IsBladeEquipped, dead+3D, adult female human, skip NecroSceneActive / menu
  - Esp builder emits MESG 0x806 PW_SeverLimbMenu
  - Kill blade helpers unchanged

Usage:
  python tools/test_corpse_sever.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
ACTOR_STUB = ROOT / "tools" / "stubs" / "Actor.psc"
MSG_STUB = ROOT / "tools" / "stubs" / "Message.psc"
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
DEPLOY = ROOT / "tools" / "build-deploy-local.ps1"


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


def test_stubs() -> None:
    actor = ACTOR_STUB.read_text(encoding="utf-8")
    if not re.search(
        r"Function\s+Dismember\s*\([^)]*\)\s*Native",
        actor,
        re.S,
    ):
        fail("Actor.Dismember must be Native")
    if "IsDismembered" not in actor or "Native" not in actor.split("IsDismembered")[1][:40]:
        fail("Actor.IsDismembered must be Native")
    # No dummy Return body after Dismember Native
    if re.search(r"Function\s+Dismember\s*\([^)]*\)\s*\n\s*Return", actor):
        fail("Dismember must not have a stub body")
    if not MSG_STUB.is_file():
        fail("missing Message.psc stub")
    msg = MSG_STUB.read_text(encoding="utf-8")
    if not re.search(r"Int\s+Function\s+Show\s*\([^)]*\)\s*Native", msg, re.S):
        fail("Message.Show must be Native")
    ok("Dismember / IsDismembered / Message.Show Native stubs")


def test_builder() -> None:
    src = BUILDER.read_text(encoding="utf-8")
    if "FID_SEVER_MSG" not in src or "0x01000806" not in src:
        fail("builder must define FID_SEVER_MSG 0x01000806")
    if "PW_SeverLimbMenu" not in src:
        fail("builder must emit PW_SeverLimbMenu")
    if "build_sever_limb_menu_payload" not in src:
        fail("builder missing build_sever_limb_menu_payload")
    if 'group(b"MESG"' not in src and "group(b'MESG'" not in src:
        fail("builder must emit MESG group")
    if "Necromantic.esp" in src:
        fail("esp builder must not master Necromantic.esp")
    ok("esp builder MSG 0x806")


def test_psc(text: str) -> None:
    if "KEY_SEVER_SLASH = 53" not in text and "KEY_SEVER_SLASH=53" not in text:
        fail("KEY_SEVER_SLASH must be 53")
    if "FID_SEVER_MSG" not in text:
        fail("FID_SEVER_MSG missing")
    reg = extract_function(text, "RegisterSeverKey")
    if "RegisterForKey(KEY_SEVER_SLASH)" not in reg and "RegisterForKey(53)" not in reg:
        fail("RegisterSeverKey must RegisterForKey slash")
    if "Event OnKeyDown(Int keyCode)" not in text:
        fail("missing OnKeyDown")
    if "TrySeverAimedCorpse" not in text:
        fail("missing TrySeverAimedCorpse")
    try_fn = extract_function(text, "TrySeverAimedCorpse")
    if "IsBladeEquipped" not in try_fn:
        fail("TrySeverAimedCorpse must gate IsBladeEquipped")
    if "NecroSceneActive" not in try_fn:
        fail("TrySeverAimedCorpse must skip NecroSceneActive")
    if "IsInMenuMode" not in try_fn:
        fail("TrySeverAimedCorpse must skip menu mode")
    if "SeverLimbMenu.Show" not in try_fn and ".Show()" not in try_fn:
        fail("TrySeverAimedCorpse must Message.Show")
    if "IsSeverCorpseEligible" not in try_fn:
        fail("TrySeverAimedCorpse must check IsSeverCorpseEligible")
    elig = extract_function(text, "IsSeverCorpseEligible")
    if "IsDead" not in elig or "Is3DLoaded" not in elig:
        fail("IsSeverCorpseEligible must require dead + 3D loaded")
    if "IsAdultFemale" not in elig or "IsHumanNpc" not in elig:
        fail("IsSeverCorpseEligible must use adult female human filters")
    sever = extract_function(text, "SeverCorpseLimb")
    if "IsDismembered" not in sever:
        fail("SeverCorpseLimb must check IsDismembered")
    if "Dismember(partName, False, True, True)" not in sever.replace(" ", ""):
        # allow spaced form
        if not re.search(
            r"Dismember\s*\(\s*partName\s*,\s*False\s*,\s*True\s*,\s*True\s*\)",
            sever,
        ):
            fail("SeverCorpseLimb must Dismember(..., False, True, True)")
    if re.search(r"Dismember\s*\(\s*[^,]+,\s*True\s*,", sever):
        fail("SeverCorpseLimb must not force-explode (first bool True)")
    if "RegisterSeverKey()" not in text:
        fail("must call RegisterSeverKey from init/load")
    debug = extract_function(text, "DebugTestSeverAimedHead")
    if "Head1" not in debug:
        fail("DebugTestSeverAimedHead must sever Head1")
    kill = extract_function(text, "IsBladeKillWeaponReady")
    if not re.search(r"Return\s+IsBladeEquipped\s*\(\s*\)", kill):
        fail("IsBladeKillWeaponReady must still alias IsBladeEquipped")
    ok("PSC sever key + Dismember contract")


def test_mcm_deploy() -> None:
    cfg = MCM.read_text(encoding="utf-8")
    if "DebugTestSeverAimedHead" not in cfg:
        fail("MCM Debug missing Test sever aimed head button")
    if "press <b>/</b>" not in cfg and "press /" not in cfg.lower():
        fail("MCM How To Use should mention / sever")
    deploy = DEPLOY.read_text(encoding="utf-8", errors="replace")
    if "test_corpse_sever.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_corpse_sever.py")
    ok("MCM + deploy gate")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_stubs()
    test_builder()
    test_psc(text)
    test_mcm_deploy()
    print("All corpse-sever (Slice F) contracts passed.")


if __name__ == "__main__":
    main()
