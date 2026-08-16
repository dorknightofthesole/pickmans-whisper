#!/usr/bin/env python3
"""Contracts for Slice U — two-actor AAF slave scene ("Take Her" activate choice).

This is a deliberate, scoped reversal of the "no AAF in this mod" product rule (see
docs/DIRECTION.md and docs/ROADMAP.md, both updated alongside this feature) — the only
AAF entry point in this mod, gated on MainQuest.IsOurSlave(target).

Design (verified against D:\\GitHub\\aaf-necromantic — same author, same AAF Papyrus
API, hard-won CTD-avoidance patterns from that mod's own production history):
  - AAF resolves via Game.GetFormFromFile(0xF99/0x915A, "AAF.esm") at runtime — no ESP
    master, no VMAD property.
  - actors = new Actor[2] (player + target) — unlike Necromantic's solo new Actor[1]
    (its "corpse" is a positioned prop, never a real AAF participant).
  - Exact-position clone of Necromantic's own setup (not tag-based auto-select, which was
    tried first and abandoned — see git history): this mod ships its own AAF data
    (Data\\AAF\\PickmansWhisper_positionData.xml / _animationData.xml), cloned from
    Necromantic's curated 7-position list as genuine two-actor pairs using verified real
    F+M idleForm pairs from rxl_bp70_animations.esp. settings.position is an exact id read
    from Data\\PickmansWhisper\\config\\SlaveScenePositions.txt (first non-comment line —
    no in-game U/P cycling, script-driven only).
  - CTD-avoidance parity with Necromantic: interior-only by default,
    EnsureAAFStoppedForRestart before every StartScene, a watchdog poll timer + a hard
    max-duration timer (OnSceneEnd is flaky), careful event re-registration on OnAAFReady.
  - NOT reused: Necromantic's per-corpse player ghost/align logic — both actors here are
    real AAF participants, so AAF's own StartScene positioning handles placement.

Locks:
  - manifest-free bank pattern for the position id (same LoadStageBankAt loader as every
    other bank in this mod) — stub + script + AAF data + ModConfig + ESP + config.json +
    deploy wiring, all statically checked
  - PickmansWhisperSlaveSceneScript: new Actor[2], exact settings.position from
    GetSlaveScenePositionId()/EnsureSlaveScenePositionBank (SlaveScenePositions.txt,
    fresh random pick per scene via Utility.RandomInt, no persisted cycling state),
    ModConfig-sourced duration (not a literal baked in),
    EnsureAAFStoppedForRestart, SceneGeneration, watchdog polls AAF_ActorBusy, OnSceneEnd +
    OnAnimationStop both present, interior gate
  - SlaveryPerkScript: Take Her replaces Free (see tools/test_slavery.py for that side)
  - MainQuestScript: SlaveScene() cast, TryStartSlaveSceneFromActivate forwarder,
    RegisterFeatureScripts calls LoadAAF, WriteSlaveSceneStatusToMcm wired into
    WriteVictimsMcmAuxRows
  - VictimsScript: MCMFreeAimedSlave (direct one-click free, replaces the old activate
    choice)
  - ModConfigScript/ModConfig.txt: aafSlaveSceneDurationSeconds only — no
    aafSlaveSceneIncludeTags (removed with the tag-based-selection pivot)
  - Data\\AAF\\PickmansWhisper_positionData.xml / _animationData.xml: 7 genuine two-actor
    positions (both files); Data\\PickmansWhisper\\config\\SlaveScenePositions.txt: 7
    matching position ids, one per line
  - ESP builder: Take Her label, PickmansWhisperSlaveSceneScript attached to Main VMAD
  - config.json: status row + Free button (Victims), exterior toggle + Cancel button
    (Debug)
  - Deploy gate: both .ps1 and .sh compile/copy the new script, sync Data\\AAF, and run
    this test; package_mo2_zip.py + fomod/ModuleConfig.xml also ship Data\\AAF

Usage:
  python tools/test_slave_scene.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperSlaveSceneScript.psc"
PERK_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperSlaveryPerkScript.psc"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
VICTIMS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimsScript.psc"
MODCFG_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
MODCFG_TXT = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
STUB_AAF = ROOT / "tools" / "stubs" / "AAF" / "AAF_API.psc"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
SETTINGS_A = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
SETTINGS_B = ROOT / "Data" / "MCM" / "Settings" / "PickmansWhisper.ini"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"
PACKAGE = ROOT / "tools" / "package_mo2_zip.py"
FOMOD_MODULE_CONFIG = ROOT / "fomod" / "ModuleConfig.xml"
DIRECTION = ROOT / "docs" / "DIRECTION.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"
AAF_POSITION_DATA = ROOT / "Data" / "AAF" / "PickmansWhisper_positionData.xml"
AAF_ANIMATION_DATA = ROOT / "Data" / "AAF" / "PickmansWhisper_animationData.xml"
POSITIONS_TXT = ROOT / "Data" / "PickmansWhisper" / "config" / "SlaveScenePositions.txt"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:^\s*(?:Bool|Int|Float|String|Actor)?\s*)?Function\s+{re.escape(name)}\s*\(",
        text,
        re.M,
    )
    if not m:
        fail(f"missing Function {name}")
    start = m.start()
    end = text.find("\nEndFunction", start)
    if end < 0:
        fail(f"unclosed Function {name}")
    return text[start : end + len("\nEndFunction")]


def extract_event(text: str, signature_start: str) -> str:
    idx = text.find(signature_start)
    if idx < 0:
        fail(f"missing event {signature_start!r}")
    end_m = re.search(r"\nEndEvent\b", text[idx:])
    if not end_m:
        fail(f"no EndEvent for {signature_start!r}")
    return text[idx : idx + end_m.end()]


def test_stub() -> None:
    if not STUB_AAF.is_file():
        fail(f"missing {STUB_AAF}")
    text = STUB_AAF.read_text(encoding="utf-8", errors="replace")
    if "Scriptname AAF:AAF_API extends Quest" not in text:
        fail("AAF_API stub must declare Scriptname AAF:AAF_API extends Quest")
    if "Function StartScene(Actor[] actors, SceneSettings settings)" not in text:
        fail("AAF_API stub must declare StartScene(Actor[] actors, SceneSettings settings)")
    if "String position" not in text or "String includeTags" not in text:
        fail("AAF_API stub SceneSettings must declare position/includeTags fields")
    for evt in ("OnAAFReady", "OnSceneInit", "OnSceneEnd", "OnAnimationStart", "OnAnimationStop"):
        if f"CustomEvent {evt}" not in text:
            fail(f"AAF_API stub must declare CustomEvent {evt}")
    ok("AAF_API stub present, StartScene + SceneSettings + 5 CustomEvents")


def test_build_tag() -> None:
    text = SCENE.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'String SCENE_BUILD_TAG = "([^"]+)"', text)
    if not m:
        fail("SlaveSceneScript must declare String SCENE_BUILD_TAG — bump it on every "
             "meaningful change so the log/MCM status line alone confirms which build is "
             "actually running, rather than guessing from unchanged message text")
    tag = m.group(1)
    # Every diagnostically load-bearing trace line must include it — these are exactly
    # the lines checked when a user reports "same failure" after a fix, so a build that
    # forgot to thread the tag through defeats the point of having one.
    load_aaf = extract_function(text, "LoadAAF")
    if "SCENE_BUILD_TAG" not in load_aaf:
        fail("LoadAAF's ready/not-found trace must include SCENE_BUILD_TAG")
    start_fn_raw = extract_function(text, "StartSlaveScene")
    if "SCENE_BUILD_TAG" not in start_fn_raw:
        fail("StartSlaveScene's trace must include SCENE_BUILD_TAG")
    scene_init = extract_event(text, "Event AAF:AAF_API.OnSceneInit(AAF:AAF_API akSender, Var[] akArgs)")
    if "SCENE_BUILD_TAG" not in scene_init:
        fail("OnSceneInit's trace (both ok and failed branches) must include SCENE_BUILD_TAG")
    if "LastOnSceneInitStatus" not in scene_init:
        fail("OnSceneInit must record LastOnSceneInitStatus for later reference (status row, EndSlaveScene trace)")
    status_fn = extract_function(text, "GetSlaveSceneStatusLine")
    if "SCENE_BUILD_TAG" not in status_fn:
        fail("GetSlaveSceneStatusLine must surface SCENE_BUILD_TAG (MCM-visible, no log dive needed)")
    ok(f"SlaveSceneScript build tag '{tag}' threaded through LoadAAF/StartScene/OnSceneInit/MCM status")


def test_scene_script() -> None:
    if not SCENE.is_file():
        fail(f"missing {SCENE}")
    text = SCENE.read_text(encoding="utf-8", errors="replace")
    if "Scriptname PickmansWhisperSlaveSceneScript extends Quest" not in text:
        fail("SlaveSceneScript must extend Quest")

    start_fn = extract_function(text, "StartSlaveScene")
    if "new Actor[2]" not in start_fn:
        fail("StartSlaveScene must build a 2-actor array (new Actor[2]) — this is a real two-actor scene, not Necromantic's solo new Actor[1]")
    if "new Actor[1]" in start_fn:
        fail("StartSlaveScene must NOT use new Actor[1] (that's Necromantic's solo-scene pattern, not this feature's)")
    if "settings.position = asPositionId" not in start_fn:
        fail("StartSlaveScene must set settings.position to the exact id passed in (asPositionId) — "
             "no tag-based auto-select (that approach was tried and abandoned)")
    if "settings.includeTags" in start_fn:
        fail("StartSlaveScene must NOT set settings.includeTags — tag-based auto-select was "
             "abandoned in favor of exact position ids (see SlaveScenePositions.txt)")
    if "EnsureAAFStoppedForRestart(akTarget)" not in start_fn:
        fail("StartSlaveScene must call EnsureAAFStoppedForRestart(akTarget) — checking only the "
             "player's busy state and never the target's was a confirmed real gap (a stale "
             "AAF_ActorBusy on the target from a prior aborted attempt would never be noticed)")
    if "SceneGeneration" not in start_fn:
        fail("StartSlaveScene must bump SceneGeneration")
    if "AAF_API.StartScene(actors, settings)" not in start_fn:
        fail("StartSlaveScene must call AAF_API.StartScene(actors, settings)")

    if "GetAafSlaveSceneDurationSeconds" not in text:
        fail("duration must be sourced from the ModConfig getter, not a literal baked into the script")
    if "GetAafSlaveSceneIncludeTags" in text or "AafSlaveSceneIncludeTags" in text:
        fail("SlaveSceneScript must NOT reference AafSlaveSceneIncludeTags — removed with the "
             "tag-based-selection pivot")

    for fn in ("LoadAAF", "EnsureAAFStoppedForRestart", "IsPlayerAAFBusy", "IsActorAAFBusy", "CanStartSceneInCurrentCell", "TryStartSlaveSceneFromActivate", "EndSlaveScene", "CancelSlaveScene", "EnsureSlaveScenePositionBank", "GetSlaveScenePositionId"):
        if f"Function {fn}(" not in text:
            fail(f"SlaveSceneScript missing {fn}")

    bank_fn = extract_function(text, "EnsureSlaveScenePositionBank")
    if "LoadStageBankAt" not in bank_fn:
        fail("EnsureSlaveScenePositionBank must load via VoiceAlias.LoadStageBankAt (same manifest-free bank pattern as every other bank in this mod)")
    if "SLAVE_SCENE_POSITIONS_FILE" not in bank_fn:
        fail("EnsureSlaveScenePositionBank must reference SLAVE_SCENE_POSITIONS_FILE (SlaveScenePositions.txt)")
    pos_id_fn = extract_function(text, "GetSlaveScenePositionId")
    if "Utility.RandomInt" not in pos_id_fn:
        fail("GetSlaveScenePositionId must pick a fresh random index via Utility.RandomInt each call — "
             "AAF's own in-scene Wizard was tried live and did not change position for these hidden "
             "positions, so random-per-scene is the variety fallback, not in-game cycling")
    if "SlaveScenePositionCount - 1" not in pos_id_fn and "SlaveScenePositionCount-1" not in pos_id_fn:
        fail("GetSlaveScenePositionId's RandomInt range must be bounded by SlaveScenePositionCount - 1")

    restart_fn = extract_function(text, "EnsureAAFStoppedForRestart")
    if "IsPlayerAAFBusy()" not in restart_fn or "IsActorAAFBusy(akOther)" not in restart_fn:
        fail("EnsureAAFStoppedForRestart must check BOTH IsPlayerAAFBusy() and IsActorAAFBusy(akOther) — "
             "player-only checking left a stale busy flag on the target NPC undetectable across attempts")

    end_fn = extract_function(text, "EndSlaveScene")
    if "IsPlayerAAFBusy()" not in end_fn or "IsActorAAFBusy(SceneTarget)" not in end_fn:
        fail("EndSlaveScene must check BOTH IsPlayerAAFBusy() and IsActorAAFBusy(SceneTarget) before "
             "deciding a stop is unnecessary — same gap as EnsureAAFStoppedForRestart, found in the same pass")

    cell_fn = extract_function(text, "CanStartSceneInCurrentCell")
    if "IsInterior()" not in cell_fn:
        fail("CanStartSceneInCurrentCell must check Cell.IsInterior()")
    if "bAllowExteriorSlaveScene:Debug" not in cell_fn:
        fail("CanStartSceneInCurrentCell must honor the MCM exterior-allow debug toggle")

    watchdog = extract_event(text, "Event OnTimer(Int aiTimerID)")
    if "IsPlayerAAFBusy()" not in watchdog:
        fail("OnTimer watchdog must poll IsPlayerAAFBusy/AAF_ActorBusy (OnSceneInit/OnAnimationStart are unreliable)")
    if "TIMER_SCENE_MAX" not in watchdog:
        fail("OnTimer must handle the hard max-duration fallback timer")

    if "AAF:AAF_API.OnSceneEnd" not in text or "AAF:AAF_API.OnAnimationStop" not in text:
        fail("SlaveSceneScript must implement both OnSceneEnd and OnAnimationStop (OnSceneEnd is flaky, especially with the player involved)")
    if "AAF:AAF_API.OnAAFReady" not in text:
        fail("SlaveSceneScript must implement OnAAFReady (AAF re-fires this on its own re-init)")

    apply_entry = extract_function(text, "TryStartSlaveSceneFromActivate")
    if "IsOurSlave" not in apply_entry:
        fail("TryStartSlaveSceneFromActivate must re-validate IsOurSlave")
    if "IsBladeEquipped" not in apply_entry:
        fail("TryStartSlaveSceneFromActivate must gate on blade sheathed (matches Enslave/Free convention)")
    if "SceneActive" not in apply_entry:
        fail("TryStartSlaveSceneFromActivate must refuse to double-start while SceneActive")
    if "GetSlaveScenePositionId()" not in apply_entry:
        fail("TryStartSlaveSceneFromActivate must resolve the position id via GetSlaveScenePositionId()")

    ok("SlaveSceneScript: 2-actor exact-position scene, CTD-avoidance parity, camera-free gameplay entry")


def test_perk_wiring() -> None:
    text = PERK_PSC.read_text(encoding="utf-8", errors="replace")
    if "TryStartSlaveSceneFromActivate" not in text:
        fail("SlaveryPerkScript must route the already-a-slave choice to TryStartSlaveSceneFromActivate")
    ok("SlaveryPerkScript routes to TryStartSlaveSceneFromActivate (see tools/test_slavery.py for Free removal)")


def test_main_wiring() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperSlaveSceneScript Function SlaveScene()" not in text:
        fail("MainQuestScript must declare a SlaveScene() cross-cast helper")
    forwarder = extract_function(text, "TryStartSlaveSceneFromActivate")
    if "scene.TryStartSlaveSceneFromActivate(akTarget)" not in forwarder:
        fail("MainQuestScript.TryStartSlaveSceneFromActivate must forward to SlaveScene()")
    register = extract_function(text, "RegisterFeatureScripts")
    if "scene.LoadAAF()" not in register:
        fail("RegisterFeatureScripts must call SlaveScene().LoadAAF() (re-registers AAF events every load)")
    status_fn = extract_function(text, "WriteSlaveSceneStatusToMcm")
    if "sSlaveScene:Victims" not in status_fn:
        fail("WriteSlaveSceneStatusToMcm must write sSlaveScene:Victims")
    aux = extract_function(text, "WriteVictimsMcmAuxRows")
    if "WriteSlaveSceneStatusToMcm()" not in aux:
        fail("WriteVictimsMcmAuxRows must call WriteSlaveSceneStatusToMcm")
    ok("MainQuestScript: SlaveScene() cast + forwarder + LoadAAF on every load + MCM status wiring")


def test_victims_free_button() -> None:
    text = VICTIMS.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperSlaveryScript Function Slavery()" not in text:
        fail("VictimsScript must declare a Slavery() cross-cast helper")
    fn = extract_function(text, "MCMFreeAimedSlave")
    if "ResolveVictimsAimActor()" not in fn:
        fail("MCMFreeAimedSlave must resolve the aimed actor via ResolveVictimsAimActor (same pattern as MCMToggleEssentialForAimed)")
    if "TryFreeSlaveFromActivate(aimed)" not in fn:
        fail("MCMFreeAimedSlave must call slavery.TryFreeSlaveFromActivate(aimed)")
    ok("VictimsScript.MCMFreeAimedSlave: direct one-click free via aim-cache pattern")


def test_modconfig() -> None:
    txt = MODCFG_TXT.read_text(encoding="utf-8", errors="replace")
    if "aafSlaveSceneDurationSeconds=" not in txt:
        fail("ModConfig.txt must ship aafSlaveSceneDurationSeconds=")
    if "aafSlaveSceneIncludeTags=" in txt:
        fail("ModConfig.txt must NOT ship aafSlaveSceneIncludeTags= — removed with the "
             "tag-based-selection pivot (position id now comes from SlaveScenePositions.txt)")
    psc = MODCFG_PSC.read_text(encoding="utf-8", errors="replace")
    if "AafSlaveSceneDurationSeconds" not in psc:
        fail("ModConfigScript must declare an AafSlaveSceneDurationSeconds property")
    if "AafSlaveSceneIncludeTags" in psc:
        fail("ModConfigScript must NOT reference AafSlaveSceneIncludeTags anywhere — removed with the tag-based-selection pivot")
    if 'key == "aafSlaveSceneDurationSeconds"' not in psc:
        fail("ModConfigScript must parse the aafSlaveSceneDurationSeconds key")
    if 'key == "aafSlaveSceneIncludeTags"' in psc:
        fail("ModConfigScript must NOT parse an aafSlaveSceneIncludeTags key")
    dur_getter = extract_function(psc, "GetAafSlaveSceneDurationSeconds")
    if "Return AafSlaveSceneDurationSeconds" not in dur_getter:
        fail("GetAafSlaveSceneDurationSeconds must return the property")
    if "Function GetAafSlaveSceneIncludeTags(" in psc:
        fail("ModConfigScript must NOT declare GetAafSlaveSceneIncludeTags — removed with the tag-based-selection pivot")
    if "AafSlaveSceneDurationSeconds <= 0.0" not in psc:
        fail("ModConfigScript must fail-loud Trace when aafSlaveSceneDurationSeconds is missing/invalid")
    ok("ModConfig aafSlaveSceneDurationSeconds: SSOT, parse, fail-loud, getter; no IncludeTags anywhere")


def test_aaf_data() -> None:
    for path in (AAF_POSITION_DATA, AAF_ANIMATION_DATA, POSITIONS_TXT):
        if not path.is_file():
            fail(f"missing {path}")

    pos_text = AAF_POSITION_DATA.read_text(encoding="utf-8", errors="replace")
    pos_ids = re.findall(r'<position id="([^"]+)"', pos_text)
    if len(pos_ids) != 7:
        fail(f"PickmansWhisper_positionData.xml must declare exactly 7 positions, found {len(pos_ids)}")
    for pid in pos_ids:
        if not pid.startswith("PW TakeHer "):
            fail(f"position id {pid!r} must start with 'PW TakeHer ' (namespaced, avoids colliding with other installed AAF packs)")

    anim_text = AAF_ANIMATION_DATA.read_text(encoding="utf-8", errors="replace")
    anim_blocks = re.findall(r'<animation id="([^"]+)"[^>]*>(.*?)</animation>', anim_text, re.S)
    if len(anim_blocks) != 7:
        fail(f"PickmansWhisper_animationData.xml must declare exactly 7 animations, found {len(anim_blocks)}")
    for anim_id, body in anim_blocks:
        actors = re.findall(r'<actor gender="([FM])" idleForm="([0-9A-Fa-f]+)"', body)
        if len(actors) != 2:
            fail(f"animation {anim_id!r} must declare exactly 2 <actor> entries (genuine two-actor pair, not Necromantic's solo new Actor[1]/1-actor idle), found {len(actors)}")
        genders = sorted(g for g, _ in actors)
        if genders != ["F", "M"]:
            fail(f"animation {anim_id!r} must have one F and one M actor, found genders {genders}")

    anim_ids = {a for a, _ in anim_blocks}
    ref_anim_ids = set(re.findall(r'animation="([^"]+)"', pos_text))
    missing = ref_anim_ids - anim_ids
    if missing:
        fail(f"position data references animation ids missing from animation data: {missing}")

    txt_lines = [
        line.strip()
        for line in POSITIONS_TXT.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not txt_lines:
        fail("SlaveScenePositions.txt must have at least one non-comment line")
    pos_id_set = set(pos_ids)
    for line in txt_lines:
        if line not in pos_id_set:
            fail(f"SlaveScenePositions.txt line {line!r} does not match any id in PickmansWhisper_positionData.xml")
    ok(f"AAF data: {len(pos_ids)} genuine two-actor positions, SlaveScenePositions.txt ids all resolve")


def test_esp_builder() -> None:
    text = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if '"PickmansWhisperSlaveSceneScript"' not in text:
        fail("ESP builder must attach PickmansWhisperSlaveSceneScript to the Main quest VMAD")
    if "NEXT_OID = 0x0000087C" not in text:
        fail("ESP builder NEXT_OID must match current reality (0x87C, past Slice W's execute menu MESG) — Slice U itself needs no new FormIDs")
    ok("ESP builder attaches SlaveSceneScript; no new FormIDs")


def test_mcm_config() -> None:
    data = json.loads(MCM_CONFIG.read_text(encoding="utf-8"))
    victims = next((p for p in data["pages"] if p.get("pageDisplayName") == "Victims"), None)
    if not victims:
        fail("config.json missing Victims page")
    by_id = {e["id"]: e for e in victims["content"] if "id" in e}
    if "sSlaveScene:Victims" not in by_id:
        fail("config.json Victims page missing sSlaveScene:Victims status row")
    free_btn = next(
        (e for e in victims["content"] if e.get("action", {}).get("function") == "MCMFreeAimedSlave"),
        None,
    )
    if not free_btn:
        fail("config.json Victims page missing Free button (CallFunction MCMFreeAimedSlave)")
    if free_btn["action"].get("scriptName") != "PickmansWhisperVictimsScript":
        fail("Free button must CallFunction on PickmansWhisperVictimsScript")

    debug = next((p for p in data["pages"] if p.get("pageDisplayName") == "Debug"), None)
    if not debug:
        fail("config.json missing Debug page")
    debug_by_id = {e["id"]: e for e in debug["content"] if "id" in e}
    if "bAllowExteriorSlaveScene:Debug" not in debug_by_id:
        fail("config.json Debug page missing bAllowExteriorSlaveScene:Debug toggle")
    cancel_btn = next(
        (e for e in debug["content"] if e.get("action", {}).get("function") == "CancelSlaveScene"),
        None,
    )
    if not cancel_btn:
        fail("config.json Debug page missing Cancel slave scene button")
    if cancel_btn["action"].get("scriptName") != "PickmansWhisperSlaveSceneScript":
        fail("Cancel button must CallFunction on PickmansWhisperSlaveSceneScript")
    ok("config.json: Victims status row + Free button, Debug exterior toggle + Cancel button")


def test_settings_defaults() -> None:
    for path in (SETTINGS_A, SETTINGS_B):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "sSlaveScene=" not in text:
            fail(f"{path} missing default sSlaveScene=")
        if "bAllowExteriorSlaveScene=" not in text:
            fail(f"{path} missing default bAllowExteriorSlaveScene=")
    ok("settings.ini (both copies) default sSlaveScene / bAllowExteriorSlaveScene")


def test_deploy_wiring() -> None:
    ps1 = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    sh = DEPLOY_SH.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperSlaveSceneScript.psc" not in ps1:
        fail("build-deploy-local.ps1 must compile PickmansWhisperSlaveSceneScript.psc")
    if "test_slave_scene.py" not in ps1:
        fail("build-deploy-local.ps1 must run test_slave_scene.py")
    if 'Sync-DataTree "AAF"' not in ps1:
        fail("build-deploy-local.ps1 must sync Data\\AAF (Slice U position/animation data)")
    if "PickmansWhisperSlaveSceneScript.psc" not in sh:
        fail("build-deploy-local.sh must compile PickmansWhisperSlaveSceneScript.psc")
    if "test_slave_scene.py" not in sh:
        fail("build-deploy-local.sh must run test_slave_scene.py")
    if 'sync_data_tree "AAF"' not in sh:
        fail("build-deploy-local.sh must sync Data/AAF (Slice U position/animation data)")
    pkg = PACKAGE.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperSlaveSceneScript" not in pkg:
        fail("package_mo2_zip.py must include PickmansWhisperSlaveSceneScript")
    if '"AAF"' not in pkg:
        fail("package_mo2_zip.py must stage Data/AAF into the FOMOD zip")
    fomod = FOMOD_MODULE_CONFIG.read_text(encoding="utf-8", errors="replace")
    if 'source="AAF"' not in fomod:
        fail("fomod/ModuleConfig.xml must install the AAF folder")
    ok("deploy (.ps1 + .sh), package_mo2_zip.py, and fomod/ModuleConfig.xml all ship Data/AAF; deploy runs this test")


def test_docs() -> None:
    direction = DIRECTION.read_text(encoding="utf-8", errors="replace")
    if re.search(r"\*\*No AAF\*\*, no sexual content", direction):
        fail("DIRECTION.md must no longer state an unconditional 'No AAF' rule — Slice U is a scoped exception")
    if "Slice U" not in direction:
        fail("DIRECTION.md must reference Slice U as the scoped AAF exception")
    roadmap = ROADMAP.read_text(encoding="utf-8", errors="replace")
    if "Slice U" not in roadmap:
        fail("ROADMAP.md must have a Slice U section")
    slice_u_doc = ROOT / "docs" / "SLICE_U_SLAVE_SCENE.md"
    if not slice_u_doc.is_file():
        fail("missing docs/SLICE_U_SLAVE_SCENE.md")
    ok("docs: DIRECTION.md/ROADMAP.md scope the AAF rule to Slice U; SLICE_U doc exists")


def main() -> int:
    for path in (
        SCENE, PERK_PSC, MAIN, VICTIMS, MODCFG_PSC, MODCFG_TXT, STUB_AAF, ESP_BUILDER,
        DEPLOY_PS1, DEPLOY_SH, PACKAGE, FOMOD_MODULE_CONFIG,
        AAF_POSITION_DATA, AAF_ANIMATION_DATA, POSITIONS_TXT,
    ):
        if not path.is_file():
            fail(f"missing {path}")
    test_stub()
    test_build_tag()
    test_scene_script()
    test_perk_wiring()
    test_main_wiring()
    test_victims_free_button()
    test_modconfig()
    test_aaf_data()
    test_esp_builder()
    test_mcm_config()
    test_settings_defaults()
    test_deploy_wiring()
    test_docs()
    print("All slave scene (Slice U) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
