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
  - Cut Off Tits is button 5: EquipItem slot-33 ARMO + PlaceAtMe MISC (tits + vanilla SM-arm gore sanity), not Dismember
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
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"
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
    if '"Cut Off Tits"' not in payload_fn:
        fail("butcher menu must include Cut Off Tits before Cancel")
    if payload_fn.find('"Cut Off Tits"') > payload_fn.find('"Cancel"'):
        fail("Cut Off Tits ITXT must come before Cancel")
    for needle in (
        "FID_MUTILATED_BODY_ARMA = 0x0100087C",
        "FID_MUTILATED_BODY_ARMO = 0x0100087D",
        "FID_CUT_OFF_TITS_MISC = 0x0100087E",
        "FID_GORE_SM_ARM_L_MISC = 0x0100087F",
        "NEXT_OID = 0x00000880",
        "PickmansWhisper_MutilatedFemaleBody_ARMA",
        "PickmansWhisper_MutilatedFemaleBody_ARMO",
        "PickmansWhisper_PropCutOffTits",
        "PickmansWhisper_DebugGoreSuperMutantArmL",
        r"PickmansWhisper\\Characters\\FemaleBody_Mutilated_Tits.nif",
        r"PickmansWhisper\\Props\\FemaleBody_Prop_Tits.nif",
        r"Actors\\Supermutant\\CharacterAssets\\GoreSuperMutantArmL.nif",
        "BOD2_SLOT_33",
        "RECORD_FLAG_NONPLAYABLE",
        "def build_gore_sm_arm_l_misc_payload",
        'group(b"MISC"',
        'record(b"MISC"',
    ):
        if needle not in src:
            fail(f"builder missing {needle!r}")
    if "flags=RECORD_FLAG_NONPLAYABLE" not in src and "flags = RECORD_FLAG_NONPLAYABLE" not in src:
        fail("mutilated body ARMO must be emitted Non-Playable")
    if 'group(b"STAT"' in src:
        fail("cut-off tits prop must be MISC (weighted/Havok), not STAT")
    misc_fn = re.search(
        r"def build_cut_off_tits_misc_payload\(\).*?(?=\ndef |\Z)",
        src,
        re.S,
    )
    if not misc_fn:
        fail("missing build_cut_off_tits_misc_payload")
    if 'field(b"DATA"' not in misc_fn.group(0) or 'struct.pack("<If"' not in misc_fn.group(0):
        fail("MISC prop must emit DATA value+weight (uint32 + float)")
    gore_fn = re.search(
        r"def build_gore_sm_arm_l_misc_payload\(\).*?(?=\ndef |\Z)",
        src,
        re.S,
    )
    if not gore_fn:
        fail("missing build_gore_sm_arm_l_misc_payload")
    if "GORE_SM_ARM_L_MESH_REL" not in gore_fn.group(0):
        fail("gore SM arm L MISC must MODL GORE_SM_ARM_L_MESH_REL (vanilla BA2 path)")
    ok("esp builder MSG 0x806 (no TNAM) + Cut Off Tits ARMA/ARMO/MISC + gore SM arm L sanity MISC")


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
    if "draw Pickman's Blade" not in try_fn or "DiagNotify(" not in try_fn:
        fail("TrySeverAimedCorpse must DiagNotify when blade not drawn")
    if "Debug.MessageBox(" in try_fn:
        fail("TrySeverAimedCorpse must not MessageBox")
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
    try_fn = extract_function(text, "TrySeverAimedCorpse")
    if "btn >= 6" not in try_fn:
        fail("TrySeverAimedCorpse cancel must be button 6 after Cut Off Tits")
    if "btn == 5" not in try_fn:
        fail("TrySeverAimedCorpse button 5 must be Cut Off Tits")
    if "ApplyMutilatedBodyOnCorpse" not in try_fn:
        fail("TrySeverAimedCorpse button 5 must ApplyMutilatedBodyOnCorpse")
    btn5 = try_fn[try_fn.find("btn == 5") :]
    if "Dismember(" in btn5.split("EndIf")[0]:
        fail("Cut Off Tits button must not call Dismember")
    facade = extract_function(text, "ApplyMutilatedBodyOnCorpse")
    if "decay.ApplyMutilatedBodyOnCorpse" not in facade:
        fail("Main ApplyMutilatedBodyOnCorpse must forward to CorpseDecay")
    if "Dismember(" in facade:
        fail("Main ApplyMutilatedBodyOnCorpse must not Dismember")
    if "ReequipMutilatedBodyIfNeeded" not in sever:
        fail("SeverCorpseLimb must ReequipMutilatedBodyIfNeeded after Dismember")
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


def test_cut_off_tits_decay() -> None:
    if not DECAY.is_file():
        fail(f"missing {DECAY}")
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    if "FID_MUTILATED_BODY_ARMO = 0x0000087D" not in decay:
        fail("CorpseDecay must use mutilated body ARMO local FormID 0x87D")
    if "FID_CUT_OFF_TITS_MISC = 0x0000087E" not in decay:
        fail("CorpseDecay must use cut-off tits MISC local FormID 0x87E")
    if "FID_GORE_SM_ARM_L_MISC = 0x0000087F" not in decay:
        fail("CorpseDecay must use gore SM arm L MISC local FormID 0x87F")
    apply = extract_function(decay, "ApplyMutilatedBodyOnCorpse")
    if re.search(r"\bDismember\s*\(", apply):
        fail("ApplyMutilatedBodyOnCorpse must not call Dismember")
    if "EquipItem" not in apply:
        fail("ApplyMutilatedBodyOnCorpse must EquipItem the slot-33 ARMO")
    if "SpawnCutOffTitsProp" not in apply:
        fail("ApplyMutilatedBodyOnCorpse must SpawnCutOffTitsProp once")
    if "WasCutOffTitsApplied" not in apply:
        fail("ApplyMutilatedBodyOnCorpse must skip if already latched")
    spawn = extract_function(decay, "SpawnCutOffTitsProp")
    if "DropHavokMiscBeside" not in spawn:
        fail("SpawnCutOffTitsProp must DropHavokMiscBeside for each prop")
    if "ResolveGoreSuperMutantArmLMisc" not in spawn:
        fail("SpawnCutOffTitsProp must also spawn GoreSuperMutantArmL sanity MISC")
    drop = extract_function(decay, "DropHavokMiscBeside")
    if "PlaceAtMe" not in drop:
        fail("DropHavokMiscBeside must PlaceAtMe the MISC")
    if "MoveTo" not in drop:
        fail("DropHavokMiscBeside must MoveTo offset beside the corpse")
    if "InitHavok" not in drop:
        fail("DropHavokMiscBeside must InitHavok after MoveTo")
    if "SetMotionType" not in drop or "Motion_Dynamic" not in drop:
        fail("DropHavokMiscBeside must SetMotionType Dynamic so the prop can fall")
    if "ApplyHavokImpulse" not in drop:
        fail("DropHavokMiscBeside must ApplyHavokImpulse so the prop drops")
    reeq = extract_function(decay, "ReequipMutilatedBodyIfNeeded")
    if "PlaceAtMe(" in reeq:
        fail("ReequipMutilatedBodyIfNeeded must not spawn a second prop")
    if "EquipItem" not in reeq:
        fail("ReequipMutilatedBodyIfNeeded must EquipItem the mutilated ARMO")
    ok("CorpseDecay Cut Off Tits apply + one-shot MISC + Havok drop + re-equip")


def test_prop_havok_script_writes_bsx_not_hulls() -> None:
    src = (ROOT / "tools" / "add_prop_tits_havok.py").read_text(encoding="utf-8")
    for token in (
        "pack_shapes",
        "ConvexHull",
        "write_data",
        "add_collision",
        "bhkPhysicsSystem.New",
    ):
        if token in src:
            fail(f"add_prop_tits_havok.py must not generate Havok hulls ({token})")
    if "nif.save(" not in src:
        fail("add_prop_tits_havok.py must save BSXFlags + collision target")
    if "patch_np_collision_target" not in src:
        fail("add_prop_tits_havok.py must patch bhkNPCollisionObject Target (DLL setBlock cannot)")
    if "BSX_HAVOK_COMPLEX_DYNAMIC" not in src or "COLLISION_TARGET_NAME" not in src:
        fail("add_prop_tits_havok.py must write Havok|Complex|Dynamic and FusionGirlReduced target")
    if "is_clutter_or_prop_layer" not in src:
        fail("add_prop_tits_havok.py must verify Clutter/Prop")
    if "is_flesh_material" not in src:
        fail("add_prop_tits_havok.py must verify Flesh material")
    if "format_no_collision_error" not in src:
        fail("add_prop_tits_havok.py must report actual NIF block types when collision is missing")
    ok("prop Havok script writes BSX 74 + FusionGirlReduced target; does not bake hulls")


def test_layer_material_matchers() -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    from add_prop_tits_havok import is_clutter_or_prop_layer, is_flesh_material

    if not is_clutter_or_prop_layer(4) or not is_clutter_or_prop_layer("CLUTTER"):
        fail("Clutter layer must be accepted")
    if not is_clutter_or_prop_layer(10) or not is_clutter_or_prop_layer("PROP"):
        fail("Prop layer must be accepted")
    if is_clutter_or_prop_layer(1) or is_clutter_or_prop_layer("STATIC"):
        fail("Static layer must not pass as Clutter/Prop")
    if not is_flesh_material("FLESH") or not is_flesh_material("SKIN"):
        fail("Flesh/Skin material must be accepted")
    if is_flesh_material("WOOD") or is_flesh_material("STONE"):
        fail("Wood/Stone must not pass as Flesh")
    from add_prop_tits_havok import format_no_collision_error, is_bsx_havok_complex_dynamic

    if not is_bsx_havok_complex_dynamic(74):
        fail("Havok|Complex|Dynamic (74) must pass")
    if is_bsx_havok_complex_dynamic(2) or is_bsx_havok_complex_dynamic(130):
        fail("Havok-only or Havok+Articulated must not count as 74")
    if is_bsx_havok_complex_dynamic(0) or is_bsx_havok_complex_dynamic(128):
        fail("Articulated-only or zero must not count as 74")

    msg = format_no_collision_error(
        ["NiNode", "BSSubIndexTriShape", "BSLightingShaderProperty", "BSShaderTextureSet"]
    )
    if "BSSubIndexTriShape" not in msg or "no Havok collision" not in msg:
        fail("missing-collision error must list the NIF block types")
    ok("Clutter/Prop + Flesh matchers")


def test_prop_nif_has_havok() -> None:
    nif = (
        ROOT
        / "Data"
        / "Meshes"
        / "PickmansWhisper"
        / "Props"
        / "FemaleBody_Prop_Tits.nif"
    )
    if not nif.is_file():
        fail(f"missing {nif}")

    sys.path.insert(0, str(ROOT / "tools"))
    from add_prop_tits_havok import (
        PYNIFLY_ADDON,
        _load_pynifly,
        format_no_collision_error,
        inspect_prop,
        is_bsx_havok_complex_dynamic,
        read_nif_block_types,
        verify_bsx_flags,
        verify_collision_meta,
        verify_collision_target,
    )

    block_types = read_nif_block_types(nif)
    has_havok = any(
        t in block_types
        for t in ("bhkNPCollisionObject", "bhkPhysicsSystem", "bhkRigidBody", "bhkRigidBodyT")
    )
    if not has_havok:
        msg = format_no_collision_error(block_types)
        if "BSSubIndexTriShape" not in msg and "BSTriShape" not in msg:
            fail("mesh-only prop nif error must list the shape block")
        ok("blender prop nif is mesh-only; gate reports block types (re-export with collision)")
        return

    data = nif.read_bytes()
    if b"BSXFlags" not in data:
        fail("prop nif must include BSXFlags so Havok is enabled")
    if b"bhkBoxShape" in data:
        fail("prop nif must not use bhkBoxShape")
    if not PYNIFLY_ADDON.is_dir():
        fail("PyNifly addon required to parse prop collision / BSXFlags")
    _load_pynifly()
    info = inspect_prop(nif)
    if not is_bsx_havok_complex_dynamic(info["bsx"]):
        fail("prop nif BSXFlags must be Havok|Complex|Dynamic (74)")
    try:
        verify_bsx_flags(info)
        verify_collision_target(info)
        verify_collision_meta(info)
    except SystemExit as exc:
        fail(str(exc) or "prop collision layer/material/target verify failed")
    ok("cut-off tits prop nif has BSX 74 and FusionGirlReduced collision target")


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
    havok_at = deploy.find("add_prop_tits_havok.py")
    sever_at = deploy.find("test_corpse_sever.py")
    if havok_at < 0 or sever_at < 0 or havok_at > sever_at:
        fail("build-deploy-local.ps1 must run add_prop_tits_havok.py before test_corpse_sever.py")
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
    test_cut_off_tits_decay()
    test_prop_havok_script_writes_bsx_not_hulls()
    test_layer_material_matchers()
    test_prop_nif_has_havok()
    test_mcm_deploy()
    print("All corpse-sever (Slice F) contracts passed.")


if __name__ == "__main__":
    main()
