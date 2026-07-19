#!/usr/bin/env python3
"""Contracts for Slice F — blade corpse sever (butcher menu + Dismember).

Locks:
  - Actor.Dismember / IsDismembered stubs are Native (no fake bodies)
  - Message.Show stub is Native
  - PlayerAlias RegisterForKey(191 = VK_OEM_2 /) + OnKeyDown → TrySeverAimedCorpse
  - F4SE keys are Windows VK (Necromantic N=78), not DX DIK
  - Main quest must NOT RegisterForKey (Quest key hooks are unreliable)
  - Quest stub must not shadow ScriptObject RegisterForKey
  - MESG builder: no TNAM (working FO4 menus omit it)
  - Dismember(part, False, True, False) — force sever, no BloodyMess (heads gib if True)
  - Gates: IsBladeEquipped, dead+3D, adult female human, skip NecroSceneActive
  - Aim: activate→camera→faced GoE female (Necromantic FindActors shape)→last
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
ALIAS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
ACTOR_STUB = ROOT / "tools" / "stubs" / "Actor.psc"
MSG_STUB = ROOT / "tools" / "stubs" / "Message.psc"
QUEST_STUB = ROOT / "tools" / "stubs" / "Quest.psc"
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
    if re.search(r"Function\s+Dismember\s*\([^)]*\)\s*\n\s*Return", actor):
        fail("Dismember must not have a stub body")
    if not MSG_STUB.is_file():
        fail("missing Message.psc stub")
    msg = MSG_STUB.read_text(encoding="utf-8")
    if not re.search(r"Int\s+Function\s+Show\s*\([^)]*\)\s*Native", msg, re.S):
        fail("Message.Show must be Native")
    quest = QUEST_STUB.read_text(encoding="utf-8")
    if re.search(r"Function\s+RegisterForKey\s*\(", quest):
        fail("Quest stub must not shadow ScriptObject RegisterForKey")
    if re.search(r"Function\s+UnregisterForKey\s*\(", quest):
        fail("Quest stub must not shadow ScriptObject UnregisterForKey")
    ok("Dismember / IsDismembered / Message.Show Native stubs; Quest key not shadowed")


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
    payload_fn = None
    m = re.search(
        r"def build_sever_limb_menu_payload\(\).*?(?=\ndef |\Z)",
        src,
        re.S,
    )
    if not m:
        fail("cannot find build_sever_limb_menu_payload body")
    payload_fn = m.group(0)
    if 'field(b"TNAM"' in payload_fn or "field(b'TNAM'" in payload_fn:
        fail("MESG builder must not emit TNAM field (breaks Message.Show vs working mod menus)")
    if "DNAM" not in payload_fn:
        fail("MESG builder must emit DNAM message-box flag")
    ok("esp builder MSG 0x806 (no TNAM)")


def test_alias(text: str) -> None:
    if "KEY_BUTCHER = 191" not in text and "KEY_BUTCHER=191" not in text:
        fail("alias KEY_BUTCHER must be 191 (VK_OEM_2 /)")
    if "Windows VK" not in text and "VK_OEM_2" not in text:
        fail("alias must document F4SE uses Windows VK codes")
    reg = extract_function(text, "RegisterButcherKey")
    if "RegisterForKey(KEY_BUTCHER)" not in reg and "RegisterForKey(191)" not in reg:
        fail("RegisterButcherKey must RegisterForKey KEY_BUTCHER")
    if "Event OnKeyDown(Int keyCode)" not in text:
        fail("alias missing OnKeyDown")
    if "TrySeverAimedCorpse" not in text:
        fail("alias OnKeyDown must call TrySeverAimedCorpse")
    if "RegisterButcherKey()" not in text:
        fail("alias must call RegisterButcherKey from init/load")
    ok("PlayerAlias butcher key contract")


def test_psc(text: str) -> None:
    if "FID_SEVER_MSG" not in text:
        fail("FID_SEVER_MSG missing")
    if "Event OnKeyDown(Int keyCode)" in text:
        fail("main quest must not own OnKeyDown (use PlayerAlias)")
    if "RegisterForKey(" in text:
        fail("main quest must not RegisterForKey (use PlayerAlias)")
    if "RegisterSeverKey" in text:
        fail("RegisterSeverKey retired — key lives on PlayerAlias")
    if "TIMER_BUTCHER" in text or "OpenButcherMenuNow" in text:
        fail("butcher must Show() directly — no TIMER_BUTCHER deferral")
    if "TrySeverAimedCorpse" not in text:
        fail("missing TrySeverAimedCorpse")
    try_fn = extract_function(text, "TrySeverAimedCorpse")
    if "IsBladeEquipped" not in try_fn:
        fail("TrySeverAimedCorpse must gate IsBladeEquipped")
    if "draw Pickman's Blade" not in try_fn:
        fail("TrySeverAimedCorpse must MessageBox when blade not drawn")
    if "NecroSceneActive" not in try_fn:
        fail("TrySeverAimedCorpse must skip NecroSceneActive")
    if "ResolveSeverCorpseAim" not in try_fn:
        fail("TrySeverAimedCorpse must ResolveSeverCorpseAim")
    if "SeverLimbMenu.Show" not in try_fn and ".Show()" not in try_fn:
        fail("TrySeverAimedCorpse must Message.Show directly")
    if "Game.GetCurrentCrosshairRef(" in text:
        fail("must not call Game.GetCurrentCrosshairRef (not base FO4/F4SE)")
    resolve = extract_function(text, "ResolveSeverCorpseAim")
    if "GetFacedSeverCorpse" not in resolve:
        fail("ResolveSeverCorpseAim must use GetFacedSeverCorpse")
    if "GetLastActivateTargetRef" not in resolve:
        fail("ResolveSeverCorpseAim must try activate target before camera")
    # Last butcher before FindActors — avoids scan hitch on repeat presses
    last_idx = resolve.find("LastButcherCorpse")
    faced_call = resolve.find("GetFacedSeverCorpse()")
    if last_idx < 0 or faced_call < 0 or last_idx > faced_call:
        fail("ResolveSeverCorpseAim must try LastButcherCorpse before GetFacedSeverCorpse")
    faced = extract_function(text, "GetFacedSeverCorpse")
    if "GetHeadingAngle" not in faced or "FindActors" not in faced:
        fail("GetFacedSeverCorpse must FindActors + GetHeadingAngle")
    if faced.count("FindActors") != 1:
        fail("GetFacedSeverCorpse must use exactly one FindActors (was a Show() hitch)")
    if not re.search(
        r"FindActors\([^)]*0\s*,\s*1\s*,\s*-1\s*,\s*1\s*,",
        faced,
    ):
        fail("GetFacedSeverCorpse FindActors must filter dead+female (sex=1)")
    if "TIMER_BUTCHER" in text or "StartTimer(0.05" in text:
        fail("butcher path must not use a deferral timer")
    elig = extract_function(text, "IsSeverCorpseEligible")
    if "IsDead" not in elig or "Is3DLoaded" not in elig:
        fail("IsSeverCorpseEligible must require dead + 3D loaded")
    if "IsAdultFemale" not in elig or "IsHumanNpc" not in elig:
        fail("IsSeverCorpseEligible must use adult female human filters")
    sever = extract_function(text, "SeverCorpseLimb")
    if "IsDismembered" not in sever:
        fail("SeverCorpseLimb must check IsDismembered")
    if not re.search(
        r"Dismember\s*\(\s*partName\s*,\s*False\s*,\s*True\s*,\s*False\s*\)",
        sever,
    ):
        fail("SeverCorpseLimb must Dismember(..., False, True, False) — no BloodyMess")
    if re.search(r"Dismember\s*\(\s*[^,]+,\s*True\s*,", sever):
        fail("SeverCorpseLimb must not force-explode (first bool True)")
    if re.search(r"Dismember\s*\(\s*partName\s*,\s*False\s*,\s*True\s*,\s*True\s*\)", sever):
        fail("SeverCorpseLimb must not ForceBloodyMess (heads explode)")
    if "EnsureSeverLimbMenu()" not in text:
        fail("must call EnsureSeverLimbMenu from init/load")
    debug_open = extract_function(text, "DebugOpenButcherMenu")
    if "TrySeverAimedCorpse" not in debug_open or "True" not in debug_open:
        fail("DebugOpenButcherMenu must TrySeverAimedCorpse(True)")
    debug = extract_function(text, "DebugTestSeverAimedHead")
    if "Head1" not in debug:
        fail("DebugTestSeverAimedHead must sever Head1")
    kill = extract_function(text, "IsBladeKillWeaponReady")
    if not re.search(r"Return\s+IsBladeEquipped\s*\(\s*\)", kill):
        fail("IsBladeKillWeaponReady must still alias IsBladeEquipped")
    ok("PSC butcher menu + Dismember contract")


def test_mcm_deploy() -> None:
    cfg = MCM.read_text(encoding="utf-8")
    if "DebugOpenButcherMenu" not in cfg:
        fail("MCM Debug missing Open butcher menu button")
    if "DebugTestSeverAimedHead" not in cfg:
        fail("MCM Debug missing Test sever aimed head button")
    if "butcher menu" not in cfg.lower():
        fail("MCM How To Use should mention butcher menu")
    if "press <b>/</b>" not in cfg and "press /" not in cfg.lower():
        fail("MCM How To Use should mention / butcher key")
    deploy = DEPLOY.read_text(encoding="utf-8", errors="replace")
    if "test_corpse_sever.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_corpse_sever.py")
    ok("MCM + deploy gate")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    if not ALIAS.is_file():
        fail(f"missing {ALIAS}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    alias = ALIAS.read_text(encoding="utf-8", errors="replace")
    test_stubs()
    test_builder()
    test_alias(alias)
    test_psc(text)
    test_mcm_deploy()
    print("All corpse-sever (Slice F) contracts passed.")


if __name__ == "__main__":
    main()
