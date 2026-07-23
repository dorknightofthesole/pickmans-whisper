#!/usr/bin/env python3
"""Contracts for Slice H P0.1 — MCM decay wound lab.

Locks:
  - PickmansWhisperDecayWoundLabScript sticky spawn/clear (no despawn timer)
  - Apply = selected DecayWoundOverlays.txt template × N with MCM tint
  - MCM menu options order == DecayWoundOverlays.txt
  - No BedGift refactor; lab is a separate quest script
  - ESP/deploy compile DecayWoundLab

Usage:
  python tools/test_decay_wound_lab.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
BED = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperBedGiftScript.psc"
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"
LAB = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperDecayWoundLabScript.psc"
WOUND_FILE = ROOT / "Data" / "PickmansWhisper" / "config" / "DecayWoundOverlays.txt"
SKIN_FILE = ROOT / "Data" / "PickmansWhisper" / "config" / "DecaySkinOverlays.txt"
FACE_FILE = ROOT / "Data" / "PickmansWhisper" / "config" / "DecayFaceOverlays.txt"
SFT_API_STUB = ROOT / "tools" / "stubs" / "SFT" / "SFT_API.psc"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"
PACKAGE = ROOT / "tools" / "package_mo2_zip.py"
FOMOD = ROOT / "fomod" / "ModuleConfig.xml"
SLICE_H = ROOT / "docs" / "SLICE_H_CORPSE_DECAY.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"


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


def wound_ids_from_config() -> list[str]:
    if not WOUND_FILE.is_file():
        fail(f"missing {WOUND_FILE}")
    ids: list[str] = []
    for line in WOUND_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        ids.append(s)
    if len(ids) < 3:
        fail("DecayWoundOverlays.txt must list at least 3 template ids")
    return ids


def test_lab_script(lab: str) -> None:
    if "Scriptname PickmansWhisperDecayWoundLabScript extends Quest" not in lab:
        fail("DecayWoundLab must extend Quest")
    if "TIMER_BED_DESPAWN" in lab or "BED_DESPAWN_SECONDS" in lab or "StartTimer" in lab:
        fail("wound lab must not auto-despawn (no bed-gift timer)")
    if "HandlePlayerSleep" in lab or "MaybeWarmBedGiftBody" in lab or "IsBedGiftEverySleep" in lab:
        fail("wound lab spawn must not be sleep-tied")
    if re.search(r"\bBedCorpse\s*=", lab) or "Function ClearBedCorpse" in lab:
        fail("wound lab must not share BedGift BedCorpse state")
    if "LabCorpse" not in lab:
        fail("wound lab must track LabCorpse")
    status_fn = extract_function(lab, "SetWoundLabStatus")
    if "ToastDebug(" in status_fn or "Debug.Notification(" in status_fn:
        fail("SetWoundLabStatus must not toast/notify (overlay Apply HUD spam)")
    # Spawn keeps its own Debug.Notification calls.
    pose_early = extract_function(lab, "PoseLabCorpseInFurniture")
    create_early = extract_function(lab, "CreateLabCorpseAt")
    if "Debug.Notification(" not in pose_early and "Debug.Notification(" not in create_early:
        fail("spawn path must keep Debug.Notification on Snap/PlaceAtMe failures")
    decay_status = extract_function(
        DECAY.read_text(encoding="utf-8", errors="replace"), "SetCorpseDecayStatus"
    )
    if "ToastDebug(" in decay_status or "Debug.Notification(" in decay_status:
        fail("SetCorpseDecayStatus must not toast/notify (overlay Apply HUD spam)")
    # BedGift DebugForceBedGift sequence: Clear → TrySpawn → Present.
    spawn = extract_function(lab, "DebugSpawnWoundLabCorpse")
    if "ClearLabCorpse()" not in spawn:
        fail("DebugSpawnWoundLabCorpse must ClearLabCorpse first")
    if "TrySpawnLabCorpse" not in spawn or "PresentLabCorpse" not in spawn:
        fail("DebugSpawnWoundLabCorpse must TrySpawnLabCorpse + PresentLabCorpse (Force bed gift parity)")
    if "ResolveBedAnchor(None)" not in spawn:
        fail("DebugSpawnWoundLabCorpse must ResolveBedAnchor(None) like Force bed gift")
    if "anchor = player" not in spawn and "anchor=player" not in spawn.replace(" ", ""):
        fail("DebugSpawnWoundLabCorpse must fall back to player when no bed")
    # Keep Clear identical to BedGift — no LooksMenu RemoveAll (stalls MCM Spawn).
    if "StripAllOverlaysForActor" in spawn:
        fail("DebugSpawnWoundLabCorpse must not strip overlays (Clear only)")
    try_spawn = extract_function(lab, "TrySpawnLabCorpse")
    if "CreateLabCorpseAt" not in try_spawn:
        fail("TrySpawnLabCorpse must CreateLabCorpseAt")
    if "BondStarted" in try_spawn or "BedGiftCooldown" in try_spawn or "IsBedGiftEnabled" in try_spawn:
        fail("TrySpawnLabCorpse must not gate on bond/cooldown/MCM bed gift")
    create = extract_function(lab, "CreateLabCorpseAt")
    if "akAnchor.PlaceAtMe" not in create:
        fail("CreateLabCorpseAt must PlaceAtMe on akAnchor (BedGift CreateBedCorpseAt parity)")
    if "PoseLabCorpseInFurniture" not in create:
        fail("CreateLabCorpseAt must PoseLabCorpseInFurniture")
    if "Disable(False)" not in create:
        fail("CreateLabCorpseAt must Disable after pose (Present re-Enables — BedGift parity)")
    if "ParkWarmed" in create or "BED_WARM_PARK" in create:
        fail("CreateLabCorpseAt must not park/warm (no sleep path)")
    assign_at = create.find("LabCorpse = corpse")
    if assign_at < 0:
        fail("CreateLabCorpseAt must assign LabCorpse")
    pose_at = create.find("PoseLabCorpseInFurniture")
    if pose_at >= 0 and assign_at > pose_at:
        fail("CreateLabCorpseAt must assign LabCorpse before Pose/KillSilent")
    present = extract_function(lab, "PresentLabCorpse")
    if "Enable(False)" not in present:
        fail("PresentLabCorpse must Enable (sticky show after Create Disable)")
    if "StartTimer" in present or "MaybeSpeakBedGift" in present:
        fail("PresentLabCorpse must not despawn-timer or wake toast")
    pose = extract_function(lab, "PoseLabCorpseInFurniture")
    if "SnapIntoInteraction" not in pose:
        fail("PoseLabCorpseInFurniture must SnapIntoInteraction")
    if "IsInMenuMode" not in pose:
        fail("PoseLabCorpseInFurniture must skip Utility.Wait while MCM is open (BedGift parity)")
    kill = extract_function(lab, "KillLabCorpse")
    if "SetKnifeKillCreditSuppressed" not in kill:
        fail("KillLabCorpse must suppress knife-kill credit")
    if "Function IsWoundLabCorpse" not in lab:
        fail("lab must expose IsWoundLabCorpse")
    clear = extract_function(lab, "DebugClearWoundLabCorpse")
    if "ClearLabCorpse()" not in clear:
        fail("DebugClearWoundLabCorpse must ClearLabCorpse")
    clear_body = extract_function(lab, "ClearLabCorpse")
    if "StripAllOverlaysForActor" in clear_body or "Overlays.RemoveAll" in clear_body:
        fail("ClearLabCorpse must match BedGift Clear — no LooksMenu RemoveAll (hangs MCM Spawn)")
    if "KillLabCorpse" not in clear_body or "Delete()" not in clear_body:
        fail("ClearLabCorpse must KillLabCorpse + Delete like BedGift ClearBedCorpse")
    resolve = extract_function(lab, "ResolveBedAnchor")
    if "320.0" not in resolve:
        fail("ResolveBedAnchor must use BedGift 320 radius")
    if "768.0" in resolve:
        fail("ResolveBedAnchor must match BedGift (no extra 768 pass)")
    apply = extract_function(lab, "DebugApplyWoundLabOverlays")
    if "ApplyTintedWoundTemplateN" not in apply:
        fail("DebugApplyWoundLabOverlays must call ApplyTintedWoundTemplateN")
    if "iWoundLabTemplate:WoundLab" not in apply:
        fail("Apply must read iWoundLabTemplate:WoundLab")
    if "fWoundLabTintA:WoundLab" not in apply:
        fail("Apply must read tint sliders")
    if "iWoundLabCount:WoundLab" not in apply:
        fail("Apply must read iWoundLabCount:WoundLab")
    apply_all = extract_function(lab, "DebugApplyAllWoundLabOverlays")
    if "ApplyTintedAllWoundTemplates" not in apply_all:
        fail("DebugApplyAllWoundLabOverlays must call ApplyTintedAllWoundTemplates")
    skin = extract_function(lab, "DebugApplySkinLabOverlays")
    if "ApplyTintedSkinTemplateN" not in skin:
        fail("DebugApplySkinLabOverlays must call ApplyTintedSkinTemplateN")
    if "iSkinLabTemplate:WoundLab" not in skin:
        fail("Skin apply must read iSkinLabTemplate:WoundLab")
    if "iSkinLabTemplate2:WoundLab" not in skin:
        fail("Skin apply must read iSkinLabTemplate2:WoundLab (optional layer)")
    if "LabSkinTemplates, 0)" not in skin and "LabSkinTemplates,0)" not in skin.replace(" ", ""):
        fail("second skin apply must pass clearCount 0 so first layer is kept")
    skin_all = extract_function(lab, "DebugApplyAllSkinLabOverlays")
    if "ApplyTintedAllSkinTemplates" not in skin_all:
        fail("DebugApplyAllSkinLabOverlays must call ApplyTintedAllSkinTemplates")
    scars_all = extract_function(lab, "DebugApplyAllScarLabOverlays")
    if "ApplyTintedAllSkinTemplatesKeepExisting" not in scars_all:
        fail("DebugApplyAllScarLabOverlays must ApplyTintedAllSkinTemplatesKeepExisting (keep SkinTexture)")
    if "ApplyTintedAllSkinTemplates(" in scars_all.replace("ApplyTintedAllSkinTemplatesKeepExisting", ""):
        fail("DebugApplyAllScarLabOverlays must not clear via ApplyTintedAllSkinTemplates")
    if "IsScarSkinTemplate" not in lab:
        fail("lab must IsScarSkinTemplate (Scars_ prefix filter)")
    if 'SubStr(templateId, 0, 6) == "Scars_"' not in lab and "Scars_" not in extract_function(lab, "IsScarSkinTemplate"):
        fail("IsScarSkinTemplate must match Scars_ prefix")
    decay_txt_full = DECAY.read_text(encoding="utf-8", errors="replace")
    decay_keep = extract_function(decay_txt_full, "ApplyTintedAllSkinTemplatesKeepExisting")
    if "ApplyTintedAllTemplates" not in decay_keep or "False" not in decay_keep:
        fail("ApplyTintedAllSkinTemplatesKeepExisting must ApplyTintedAllTemplates(..., False) no-clear")
    all_tmpl = extract_function(decay_txt_full, "ApplyTintedAllTemplates")
    if "abClearMatching" not in all_tmpl:
        fail("ApplyTintedAllTemplates must take abClearMatching")
    if "If abClearMatching" not in all_tmpl:
        fail("ApplyTintedAllTemplates must only RemoveMatchingOverlays when abClearMatching")
    if "ClearSkinBankOverlays" not in decay_txt_full:
        fail("CorpseDecay must ClearSkinBankOverlays for stage apply")
    stage_apply = extract_function(lab, "DebugApplyDecayStageLab")
    if "ClearSkinBankOverlays" not in stage_apply:
        fail("DebugApplyDecayStageLab must ClearSkinBankOverlays before stage textures")
    if "ApplyDecayStageOverlays" not in stage_apply:
        fail("DebugApplyDecayStageLab must ApplyDecayStageOverlays (shared with bed gift)")
    if "DecayStagesReady" not in stage_apply:
        fail("DebugApplyDecayStageLab must gate on DecayStagesReady")
    if "iDecayLabStage:WoundLab" not in stage_apply:
        fail("DebugApplyDecayStageLab must read iDecayLabStage:WoundLab")
    if "GetDecayStageTintA" not in stage_apply:
        fail("DebugApplyDecayStageLab must read GetDecayStageTintA from ModConfig")
    if "tintA = 1.0" in stage_apply or "tintA=1.0" in stage_apply.replace(" ", ""):
        fail("DebugApplyDecayStageLab must not hardcode tintA = 1.0 (alpha is ModConfig field a)")
    if "GetModSettingFloat(MOD_NAME, \"fWoundLabTintA:WoundLab\")" in stage_apply:
        fail("DebugApplyDecayStageLab must not read MCM Tint A (stage alpha is ModConfig)")
    if "stage >= 3" in stage_apply or "stage>=3" in stage_apply.replace(" ", ""):
        fail("DebugApplyDecayStageLab must not hardcode stage>=3 scars (ModConfig scars flag)")
    if "0.650" in lab or "SkinTexture_07" in lab:
        fail("lab script must not bake decay stage RGB/skins (ModConfig is source)")
    if "DebugSpawnWoundLabCorpse" in stage_apply or "CreateLabCorpseAt" in stage_apply:
        fail("DebugApplyDecayStageLab must not touch spawn")
    decay_stage = extract_function(decay_txt_full, "ApplyDecayStageOverlays")
    if "FillDecayStageSkins" not in decay_stage:
        fail("ApplyDecayStageOverlays must FillDecayStageSkins from ModConfig")
    if "GetDecayStageAllScars" not in decay_stage:
        fail("ApplyDecayStageOverlays must use GetDecayStageAllScars from ModConfig")
    if "ClearSkinBankOverlays" not in decay_stage:
        fail("ApplyDecayStageOverlays must ClearSkinBankOverlays (Victims/WorldScan share path)")
    if "ApplyTintedAllSkinTemplatesKeepExisting" not in decay_stage:
        fail("ApplyDecayStageOverlays must ApplyTintedAllSkinTemplatesKeepExisting")
    if decay_stage.find("ClearSkinBankOverlays") > decay_stage.find(
        "ApplyTintedAllSkinTemplatesKeepExisting"
    ):
        fail("ApplyDecayStageOverlays must clear before KeepExisting")
    if decay_stage.find("ApplyDecayFaceArmorForStage") < decay_stage.find(
        "ApplyTintedAllSkinTemplatesKeepExisting"
    ):
        fail("ApplyDecayStageOverlays must equip face AFTER body skins (Update strips ARMO)")
    # Overlay Update Wait must not freeze MCM CallFunction applies.
    for fn_name in ("ApplyTintedTemplateN", "ApplyTintedAllTemplates"):
        fn_body = extract_function(decay_txt_full, fn_name)
        if "IsInMenuMode" not in fn_body:
            fail(f"{fn_name} must skip Utility.Wait while MCM/menu is open")
    mod_cfg = (ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt").read_text(encoding="utf-8")
    expected_stages = [
        ("decayStage0", "Freshly Deceased", "0.650", "0.520", "0.480", "1.0", "0", "none", False),
        ("decayStage1", "Pallor Mortis", "0.300", "0.750", "0.720", "1.0", "0.25", "none", False),
        ("decayStage2", "Livor Mortis", "0.480", "0.140", "0.300", "1.0", "2", "SkinTexture_15+SkinTexture_09", False),
        ("decayStage3", "Putrefaction", "0.369", "0.451", "0.318", "1.0", "48", "SkinTexture_17+SkinTexture_18", True),
        ("decayStage4", "Black Putrefaction", "0.149", "0.118", "0.102", "1.0", "240", "SkinTexture_03+SkinTexture_18", True),
    ]
    for key, name, r, g, b, a, start_h, skins, scars in expected_stages:
        line = next((ln for ln in mod_cfg.splitlines() if ln.startswith(key + "=")), "")
        if not line:
            fail(f"ModConfig missing {key}=")
        val = line.split("=", 1)[1]
        parts = val.split(";")
        if len(parts) < 7:
            fail(f"{key} must be name;r;g;b;a;startHours;skins[;scars] — got {val!r}")
        if (
            parts[0] != name
            or parts[1] != r
            or parts[2] != g
            or parts[3] != b
            or parts[4] != a
            or parts[5] != start_h
            or parts[6] != skins
        ):
            fail(f"{key} value mismatch: {val!r}")
        has_scars = len(parts) >= 8 and parts[7] == "scars"
        if has_scars != scars:
            fail(f"{key} scars flag expected {scars}, got {has_scars}")
    main_txt = MAIN.read_text(encoding="utf-8", errors="replace")
    load_mod = extract_function(main_txt, "LoadModConfig")
    if "decayStage0" not in load_mod or "ParseDecayStageValue" not in load_mod:
        fail("LoadModConfig must parse decayStage0..4 via ParseDecayStageValue")
    if "SplitByChar" not in main_txt or "FillDecayStageSkins" not in main_txt:
        fail("Main must SplitByChar + FillDecayStageSkins for ModConfig stages")
    if "GetDecayStageTintA" not in main_txt or "DecayStageTintA" not in main_txt:
        fail("Main must store/expose DecayStageTintA / GetDecayStageTintA")
    slice_h = SLICE_H.read_text(encoding="utf-8")
    if "ModConfig.txt" not in slice_h or "decayStage0" not in slice_h:
        fail("SLICE_H must document ModConfig decayStage0..4 as source of truth")
    if "name;r;g;b;a;startHours;skins" not in slice_h and "startHours" not in slice_h:
        fail("SLICE_H must document name;r;g;b;a;startHours;skins format")
    for name in ("Freshly Deceased", "Pallor Mortis", "Livor Mortis", "Putrefaction", "Black Putrefaction"):
        if name not in slice_h or name not in mod_cfg:
            fail(f"stage name {name!r} must appear in SLICE_H and ModConfig")
    face = extract_function(lab, "DebugApplyFaceLabOverlays")
    if "ApplyTintedFaceTemplateN" not in face:
        fail("DebugApplyFaceLabOverlays must call ApplyTintedFaceTemplateN")
    if "iFaceLabTemplate:WoundLab" not in face:
        fail("Face apply must read iFaceLabTemplate:WoundLab")
    if "iFaceLabTemplate2:WoundLab" not in face:
        fail("Face apply must read iFaceLabTemplate2:WoundLab (optional layer)")
    if "LabFaceTemplates, 0)" not in face and "LabFaceTemplates,0)" not in face.replace(" ", ""):
        fail("second face apply must pass clearCount 0 so first layer is kept")
    face_all = extract_function(lab, "DebugApplyAllFaceLabOverlays")
    if "ApplyTintedAllFaceTemplates" not in face_all:
        fail("DebugApplyAllFaceLabOverlays must call ApplyTintedAllFaceTemplates")
    decay_txt = DECAY.read_text(encoding="utf-8", errors="replace")
    if "RemoveMatchingOverlays" not in decay_txt:
        fail("CorpseDecay must RemoveMatchingOverlays (stack banks)")
    extract_function(decay_txt, "ApplyTintedAllWoundTemplates")
    extract_function(decay_txt, "ApplyTintedAllSkinTemplates")
    extract_function(decay_txt, "ApplyTintedAllFaceTemplates")
    face_apply = extract_function(decay_txt, "ApplyTintedFaceTemplateN")
    if "ResolveSFTHeadParts" not in face_apply and "GetHeadPartsByFullName" not in face_apply:
        fail("ApplyTintedFaceTemplateN must resolve via GoE2 GetHeadPartsByFullName")
    if "ChangeSFTHeadParts" not in face_apply and "ChangeHeadPart" not in face_apply:
        fail("ApplyTintedFaceTemplateN must ChangeHeadPart")
    if "GardenOfEden2.GetHeadPartsByFullName" not in decay_txt:
        fail("CorpseDecay face path must use GardenOfEden2.GetHeadPartsByFullName (SFT's own lookup)")
    if "ChangeHeadPart" not in decay_txt or "QueueUpdate" not in decay_txt:
        fail("CorpseDecay face path must ChangeHeadPart + QueueUpdate")
    if "Resurrect" not in decay_txt:
        fail("CorpseDecay face path must Resurrect dead lab corpses before ChangeHeadPart")
    if "FID_SFT_DAMAGE_F" not in decay_txt or "0x000008D" not in decay_txt:
        fail("CorpseDecay must soft-load SFT_Damage FormList 0x8D")
    if "FID_SFT_DAMAGE_M" not in decay_txt or "0x00000B2" not in decay_txt:
        fail("CorpseDecay must soft-load SFT_Damage_M FormList 0xB2")
    if re.search(r"\bas\s+SFT:SFT_API\b", decay_txt):
        fail("CorpseDecay must NOT hard-type SFT:SFT_API (breaks script load if SFT missing)")
    if "SoftFaceDepsReady" not in decay_txt:
        fail("CorpseDecay must SoftFaceDepsReady for SFT")
    goe2 = (ROOT / "tools" / "stubs" / "GardenOfEden2.psc").read_text(encoding="utf-8", errors="replace")
    if "Function GetHeadPartsByFullName" not in goe2:
        fail("GardenOfEden2 stub must declare real GetHeadPartsByFullName")
    # Spawn must stay independent of SFT / face apply.
    lab_txt = LAB.read_text(encoding="utf-8", errors="replace")
    for fname in (
        "DebugSpawnWoundLabCorpse",
        "TrySpawnLabCorpse",
        "CreateLabCorpseAt",
        "PresentLabCorpse",
        "ClearLabCorpse",
    ):
        spawn = extract_function(lab_txt, fname)
        if "SFT" in spawn or "SoftSFT" in spawn or "ChangeHeadPart" in spawn or "Resurrect" in spawn:
            fail(f"{fname} must not call SFT/face apply")
    if "DecayWoundOverlays.txt" not in lab:
        fail("lab must load DecayWoundOverlays.txt (single source)")
    if "DecaySkinOverlays.txt" not in lab:
        fail("lab must load DecaySkinOverlays.txt (single source)")
    if "DecayFaceOverlays.txt" not in lab:
        fail("lab must load DecayFaceOverlays.txt (single source)")
    ok("DecayWoundLabScript sticky spawn + wound/skin/face apply")


def test_wiring(main: str, bed: str, decay: str) -> None:
    if "Function DecayWoundLab()" not in main:
        fail("Main must expose DecayWoundLab() façade")
    for name in (
        "DebugSpawnWoundLabCorpse",
        "DebugClearWoundLabCorpse",
        "DebugApplyWoundLabOverlays",
        "DebugApplyAllWoundLabOverlays",
        "DebugApplySkinLabOverlays",
        "DebugApplyAllSkinLabOverlays",
        "DebugApplyAllScarLabOverlays",
        "DebugApplyDecayStageLab",
        "DebugApplyFaceLabOverlays",
        "DebugApplyAllFaceLabOverlays",
    ):
        if name not in main:
            fail(f"Main must façade {name}")
    if "ApplyTintedWoundTemplateN" not in decay:
        fail("CorpseDecay must expose ApplyTintedWoundTemplateN")
    if "ApplyTintedAllWoundTemplates" not in decay:
        fail("CorpseDecay must expose ApplyTintedAllWoundTemplates")
    if "ApplyTintedSkinTemplateN" not in decay:
        fail("CorpseDecay must expose ApplyTintedSkinTemplateN")
    if "ApplyTintedFaceTemplateN" not in decay:
        fail("CorpseDecay must expose ApplyTintedFaceTemplateN")
    # BedGift must remain untouched for lab (no lab imports / shared LabCorpse).
    if "DecayWoundLab" in bed or "LabCorpse" in bed:
        fail("BedGift must not be refactored for wound lab")
    ok("Main + CorpseDecay wiring; BedGift untouched")


def skin_ids_from_config() -> list[str]:
    if not SKIN_FILE.is_file():
        fail(f"missing {SKIN_FILE}")
    ids: list[str] = []
    for line in SKIN_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        ids.append(s)
    if len(ids) < 10:
        fail("DecaySkinOverlays.txt must list scars/skin templates")
    for tid in ids:
        if tid.startswith("Pimples_") or tid.startswith("Moles_"):
            fail(f"DecaySkinOverlays should exclude pimples/moles, got {tid}")
        if not (tid.startswith("Scars_") or tid.startswith("SkinTexture_")):
            fail(f"DecaySkinOverlays unexpected id {tid}")
    return ids


EXPECTED_SFT_FACE = [
    "Boxer - 12 Rounds",
    "Boxer - Broken Nose",
    "Boxer - Black Eye",
    "Boxer - Fat Lip",
]


def face_ids_from_config() -> list[str]:
    if not FACE_FILE.is_file():
        fail(f"missing {FACE_FILE}")
    ids: list[str] = []
    for line in FACE_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        ids.append(s)
    if ids != EXPECTED_SFT_FACE:
        fail(f"DecayFaceOverlays.txt must be SFT Damage Boxer set\n  got={ids}\n  want={EXPECTED_SFT_FACE}")
    banned = ("fuck", "whore", "cum", "cock", "rape", "slave", "hickey", "breed", "spit")
    for tid in ids:
        low = tid.lower()
        if any(k in low for k in banned):
            fail(f"DecayFaceOverlays must stay non-sexual, got {tid}")
    return ids


def test_face_sft() -> None:
    face_ids = face_ids_from_config()
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    if "GardenOfEden2.GetHeadPartsByFullName" not in decay or "FID_SFT_DAMAGE_F" not in decay:
        fail("CorpseDecay must apply SFT via GoE2 FULL-name lookup + sex FormList filter")
    if re.search(r"\bas\s+SFT:SFT_API\b", decay):
        fail("CorpseDecay must not use typed SFT:SFT_API cast")
    actor_stub = (ROOT / "tools" / "stubs" / "Actor.psc").read_text(encoding="utf-8", errors="replace")
    if "Function ChangeHeadPart" not in actor_stub or "Function QueueUpdate" not in actor_stub:
        fail("Actor stub must declare real FO4 ChangeHeadPart + QueueUpdate")
    goe2 = (ROOT / "tools" / "stubs" / "GardenOfEden2.psc").read_text(encoding="utf-8", errors="replace")
    if "Function GetHeadPartsByFullName" not in goe2:
        fail("GardenOfEden2 stub must declare GetHeadPartsByFullName")
    if not (ROOT / "tools" / "stubs" / "HeadPart.psc").is_file():
        fail("missing tools/stubs/HeadPart.psc")
    if not (ROOT / "tools" / "stubs" / "FormList.psc").is_file():
        fail("missing tools/stubs/FormList.psc")
    slice_h = SLICE_H.read_text(encoding="utf-8")
    if "SkinTexture_15" not in slice_h:
        fail("SLICE_H must document SkinTexture_15 (Livor / first body change)")
    if "SkinTexture_17" not in slice_h or "SkinTexture_03" not in slice_h:
        fail("SLICE_H must lock late-stage SkinTexture map (17+18 / 3+18)")
    if "none" not in slice_h.lower() and "`none`" not in slice_h:
        fail("SLICE_H must document skins=none for Freshly Deceased body")
    if "Boxer - Black Eye" not in slice_h or "all" not in slice_h.lower():
        fail("SLICE_H must lock applying all SFT Boxer face bruises")
    load_dotenv()
    sft_esp = os.environ.get("SFT_ESP", "").strip()
    if sft_esp:
        esp_path = Path(sft_esp)
        if not esp_path.is_file():
            fail(f"SFT_ESP not a file: {esp_path}")
        raw = esp_path.read_bytes()
        for name in face_ids:
            if name.encode("utf-8") not in raw and name.encode("ascii", errors="ignore") not in raw:
                fail(f"SFT.esp missing FULL name {name!r}")
        if b"SFT_Damage\x00" not in raw:
            fail("SFT.esp missing SFT_Damage FormList EDID")
        ok(f"SFT.esp has {len(face_ids)} Boxer FULL names + SFT_Damage")
    else:
        print("SKIP: set SFT_ESP in .env to verify FULL names against installed SFT.esp")
    ok(f"face lab SFT GoE2 FULL-name bank ({len(face_ids)} Boxer tints)")


def test_mcm_matches_wound_file() -> None:
    ids = wound_ids_from_config()
    skin_ids = skin_ids_from_config()
    face_ids = face_ids_from_config()
    mcm = json.loads(MCM.read_text(encoding="utf-8"))
    wound_opts: list[str] | None = None
    skin_opts: list[str] | None = None
    skin2_opts: list[str] | None = None
    face_opts: list[str] | None = None
    face2_opts: list[str] | None = None
    stage_opts: list[str] | None = None
    stage_type = ""
    wound_type = ""
    skin_type = ""
    skin2_type = ""
    face_type = ""
    face2_type = ""
    wound_lab_content: list[dict] = []
    page_names = [p.get("pageDisplayName") for p in mcm.get("pages", [])]
    if "Wound Lab" not in page_names:
        fail("MCM must have Wound Lab page")
    for page in mcm.get("pages", []):
        if page.get("pageDisplayName") == "Wound Lab":
            wound_lab_content = page.get("content", [])
        for item in page.get("content", []):
            if item.get("id") == "iWoundLabTemplate:WoundLab":
                wound_opts = item.get("valueOptions", {}).get("options")
                wound_type = item.get("type", "")
            if item.get("id") == "iSkinLabTemplate:WoundLab":
                skin_opts = item.get("valueOptions", {}).get("options")
                skin_type = item.get("type", "")
            if item.get("id") == "iSkinLabTemplate2:WoundLab":
                skin2_opts = item.get("valueOptions", {}).get("options")
                skin2_type = item.get("type", "")
            if item.get("id") == "iFaceLabTemplate:WoundLab":
                face_opts = item.get("valueOptions", {}).get("options")
                face_type = item.get("type", "")
            if item.get("id") == "iFaceLabTemplate2:WoundLab":
                face2_opts = item.get("valueOptions", {}).get("options")
                face2_type = item.get("type", "")
            if item.get("id") == "iDecayLabStage:WoundLab":
                stage_opts = item.get("valueOptions", {}).get("options")
                stage_type = item.get("type", "")
    if wound_opts is None:
        fail("MCM missing iWoundLabTemplate:WoundLab stepper")
    if wound_type != "stepper":
        fail("Wound template must be type stepper (dropdown/cycle)")
    if wound_opts != ids:
        fail(f"MCM wound stepper must match DecayWoundOverlays.txt order\n  file={ids}\n  mcm={wound_opts}")
    if skin_opts is None:
        fail("MCM missing iSkinLabTemplate:WoundLab stepper")
    if skin_type != "stepper":
        fail("Skin template must be type stepper")
    if skin_opts != skin_ids:
        fail(f"MCM skin stepper must match DecaySkinOverlays.txt\n  file={skin_ids}\n  mcm={skin_opts}")
    if skin2_opts is None:
        fail("MCM missing iSkinLabTemplate2:WoundLab stepper")
    if skin2_type != "stepper":
        fail("Skin template 2 must be type stepper")
    if not skin2_opts or skin2_opts[0] not in ("(none)", "", "—", "-"):
        fail("Skin template 2 first option must be blank/none (skip)")
    if skin2_opts[1:] != skin_ids:
        fail(f"Skin template 2 must be (none)+DecaySkinOverlays\n  got={skin2_opts}")
    if face_opts is None:
        fail("MCM missing iFaceLabTemplate:WoundLab stepper")
    if face_type != "stepper":
        fail("Face template must be type stepper")
    if face_opts != face_ids:
        fail(f"MCM face stepper must match DecayFaceOverlays.txt\n  file={face_ids}\n  mcm={face_opts}")
    if face2_opts is None:
        fail("MCM missing iFaceLabTemplate2:WoundLab stepper")
    if face2_type != "stepper":
        fail("Face template 2 must be type stepper")
    if not face2_opts or face2_opts[0] not in ("(none)", "", "—", "-"):
        fail("Face template 2 first option must be blank/none (skip)")
    if face2_opts[1:] != face_ids:
        fail(f"Face template 2 must be (none)+DecayFaceOverlays\n  got={face2_opts}")
    mcm_text = MCM.read_text(encoding="utf-8")
    for fn in (
        "DebugSpawnWoundLabCorpse",
        "DebugClearWoundLabCorpse",
        "DebugApplyWoundLabOverlays",
        "DebugApplyAllWoundLabOverlays",
        "DebugApplySkinLabOverlays",
        "DebugApplyAllSkinLabOverlays",
        "DebugApplyAllScarLabOverlays",
        "DebugApplyDecayStageLab",
        "DebugApplyFaceLabOverlays",
        "DebugApplyAllFaceLabOverlays",
    ):
        if fn not in mcm_text:
            fail(f"MCM must wire {fn}")
    if "Apply all wounds" not in mcm_text or "Apply all skin overlays" not in mcm_text:
        fail("MCM must have Apply all wounds + Apply all skin overlays")
    if "Apply all scars" not in mcm_text:
        fail("MCM must have Apply all scars button")
    if "Apply stage" not in mcm_text or "iDecayLabStage:WoundLab" not in mcm_text:
        fail("MCM must have Decay stage stepper + Apply stage")
    expected_stages = [
        "Freshly Deceased",
        "Pallor Mortis",
        "Livor Mortis",
        "Putrefaction",
        "Black Putrefaction",
    ]
    mod_names: list[str] = []
    mod_txt = (ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt").read_text(encoding="utf-8")
    for i in range(5):
        line = next((ln for ln in mod_txt.splitlines() if ln.startswith(f"decayStage{i}=")), "")
        if not line:
            fail(f"ModConfig missing decayStage{i}= for MCM name check")
        mod_names.append(line.split("=", 1)[1].split(";")[0])
    if stage_opts != expected_stages or stage_opts != mod_names:
        fail(
            f"MCM Decay stage options must match ModConfig decayStage0..4 names\n"
            f"  mcm={stage_opts}\n  mod={mod_names}"
        )
    if stage_type != "stepper":
        fail("Decay stage must be type stepper (left/right cycle with stage names)")
    # Stage block must lead the page; Lab tools section HR separates it from settings below.
    if not wound_lab_content:
        fail("Wound Lab content empty")
    first_texts = [c.get("text", "") for c in wound_lab_content[:8]]
    if first_texts[0] != "Decay stage (P2)":
        fail(f"Wound Lab must start with Decay stage section, got {first_texts[0]!r}")
    if wound_lab_content[0].get("type") != "section":
        fail("Decay stage header must be type section")
    if "Lab tools" not in first_texts:
        fail("Wound Lab must have Lab tools section HR after stage + spawn controls")
    stage_idx = next((i for i, c in enumerate(wound_lab_content) if c.get("id") == "iDecayLabStage:WoundLab"), -1)
    wound_idx = next((i for i, c in enumerate(wound_lab_content) if c.get("id") == "iWoundLabTemplate:WoundLab"), -1)
    if stage_idx < 0 or wound_idx < 0 or stage_idx >= wound_idx:
        fail("Decay stage control must appear above Wound template settings")
    lab_tools_idx = next((i for i, c in enumerate(wound_lab_content) if c.get("text") == "Lab tools" and c.get("type") == "section"), -1)
    if lab_tools_idx < 0 or lab_tools_idx <= stage_idx or lab_tools_idx >= wound_idx:
        fail("Lab tools section must sit between Decay stage and the settings below")
    spawn_idx = next(
        (
            i
            for i, c in enumerate(wound_lab_content)
            if (c.get("action") or {}).get("function") == "DebugSpawnWoundLabCorpse"
        ),
        -1,
    )
    apply_stage_idx = next((i for i, c in enumerate(wound_lab_content) if c.get("text") == "Apply stage"), -1)
    if spawn_idx < 0 or apply_stage_idx < 0 or spawn_idx <= apply_stage_idx:
        fail("Spawn wound lab corpse must sit directly under Apply stage")
    if spawn_idx >= lab_tools_idx:
        fail("Spawn must be above Lab tools section (not buried under wound/skin settings)")
    stage_apply_fn = extract_function(
        LAB.read_text(encoding="utf-8", errors="replace"), "DebugApplyDecayStageLab"
    )
    if "MCM.RefreshMenu" in stage_apply_fn:
        fail("DebugApplyDecayStageLab must not MCM.RefreshMenu (stalls later Spawn CallFunction)")
    if "Apply all face overlays" not in mcm_text:
        fail("MCM must have Apply all face overlays")
    for sid in (
        "fWoundLabTintR:WoundLab",
        "fWoundLabTintG:WoundLab",
        "fWoundLabTintB:WoundLab",
        "fWoundLabTintA:WoundLab",
        "iWoundLabCount:WoundLab",
        "iSkinLabTemplate:WoundLab",
        "iSkinLabTemplate2:WoundLab",
        "iFaceLabTemplate:WoundLab",
        "iFaceLabTemplate2:WoundLab",
        "iWoundLabTintPreset:WoundLab",
    ):
        if sid not in mcm_text:
            fail(f"MCM missing {sid}")
    preset_opts: list[str] | None = None
    preset_type = ""
    for page in mcm.get("pages", []):
        for item in page.get("content", []):
            if item.get("id") == "iWoundLabTintPreset:WoundLab":
                preset_opts = item.get("valueOptions", {}).get("options")
                preset_type = item.get("type", "")
    if preset_opts is None:
        fail("MCM missing iWoundLabTintPreset:WoundLab")
    if preset_type != "menu":
        fail("Tint preset must be type menu (dropdown)")
    expected_presets = [
        "P1 pale",
        "Death decay green",
        "Body decay red",
        "Ashen gray",
    ]
    if preset_opts != expected_presets:
        fail(f"Tint preset options mismatch\n  got={preset_opts}\n  want={expected_presets}")
    lab_txt = LAB.read_text(encoding="utf-8", errors="replace")
    apply_preset = extract_function(lab_txt, "ApplyWoundLabTintPreset")
    if "SetModSettingFloat" not in apply_preset:
        fail("ApplyWoundLabTintPreset must write tint RGB via SetModSettingFloat")
    if "0.35" not in apply_preset or "0.55" not in apply_preset:
        fail("ApplyWoundLabTintPreset must define death decay green RGB")
    if "0.78" not in apply_preset or "0.22" not in apply_preset:
        fail("ApplyWoundLabTintPreset must define body decay red RGB")
    if "0.52" not in apply_preset:
        fail("ApplyWoundLabTintPreset must define ashen gray RGB")
    main_txt = MAIN.read_text(encoding="utf-8", errors="replace")
    on_change = extract_function(main_txt, "OnMCMSettingChange")
    if "iWoundLabTintPreset:WoundLab" not in on_change or "ApplyWoundLabTintPreset" not in on_change:
        fail("OnMCMSettingChange must apply tint preset when dropdown changes")
    settings = SETTINGS.read_text(encoding="utf-8")
    if "[WoundLab]" not in settings:
        fail("settings.ini must have [WoundLab] section")
    if "iWoundLabTemplate=" not in settings or "iSkinLabTemplate=" not in settings:
        fail("settings.ini must default wound + skin lab MCM keys")
    if "iSkinLabTemplate2=" not in settings:
        fail("settings.ini must default iSkinLabTemplate2=(none)")
    if "iFaceLabTemplate=" not in settings or "iFaceLabTemplate2=" not in settings:
        fail("settings.ini must default face lab MCM keys")
    if "iDecayLabStage=" not in settings:
        fail("settings.ini must default iDecayLabStage")
    if "iWoundLabTintPreset=" not in settings:
        fail("settings.ini must default iWoundLabTintPreset")
    load_dotenv()
    porc_env = os.environ.get("PORC_OVERLAYS_JSON", "").strip()
    if porc_env:
        porc_json = Path(porc_env)
        if not porc_json.is_file():
            fail(f"PORC_OVERLAYS_JSON not a file: {porc_json}")
        known = {o["id"] for o in json.loads(porc_json.read_text(encoding="utf-8"))}
        missing = [i for i in skin_ids if i not in known]
        if missing:
            fail(f"DecaySkinOverlays ids missing from Porcupine JSON: {missing}")
        ok(f"skin ids subset of Porcoverlays.esl ({len(skin_ids)})")
    else:
        print("SKIP: set PORC_OVERLAYS_JSON in .env to verify ids against Porcupine pack")
    ok("MCM Wound Lab page; wound + skin + face steppers match banks")


def test_esp_deploy_docs() -> None:
    esp = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperDecayWoundLabScript" not in esp:
        fail("build_hunger_spell_esp.py must attach DecayWoundLab")
    deploy_ps1 = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    deploy_sh = DEPLOY_SH.read_text(encoding="utf-8", errors="replace")
    if "test_decay_wound_lab.py" not in deploy_ps1 or "test_decay_wound_lab.py" not in deploy_sh:
        fail("deploy scripts must run test_decay_wound_lab.py")
    if "PickmansWhisperDecayWoundLabScript.psc" not in deploy_ps1:
        fail("build-deploy-local.ps1 must Caprica-compile DecayWoundLab")
    if 'PSC_WOUND_LAB="PickmansWhisperDecayWoundLabScript.psc"' not in deploy_sh:
        fail("build-deploy-local.sh must define PSC_WOUND_LAB")
    if "SFT:SFT_API" not in DEPLOY_PS1.read_text(encoding="utf-8", errors="replace") and "stubs\\SFT" not in deploy_ps1 and "stubs/SFT" not in deploy_ps1:
        # Caprica -i stubs root is enough if SFT folder lives under stubs; lock stub presence instead.
        pass
    if not (ROOT / "tools" / "stubs" / "HeadPart.psc").is_file():
        fail("deploy compile needs tools/stubs/HeadPart.psc")
    pkg = PACKAGE.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperDecayWoundLabScript" not in pkg:
        fail("package_mo2_zip.py must include DecayWoundLab script")
    slice_h = SLICE_H.read_text(encoding="utf-8")
    if "P0.1" not in slice_h and "wound lab" not in slice_h.lower():
        fail("SLICE_H must document P0.1 wound lab")
    if "P0.2" not in slice_h or "porcOverlays" not in slice_h:
        fail("SLICE_H must document P0.2 Porcupine skin")
    if "SFT" not in slice_h and "Scripted Face Tints" not in slice_h:
        fail("SLICE_H must document SFT face soft dep")
    road = ROADMAP.read_text(encoding="utf-8")
    if "P0.1" not in road or "P0.2" not in road:
        fail("ROADMAP Slice H must list P0.1 and P0.2")
    if "SFT" not in road and "Scripted Face" not in road:
        fail("ROADMAP Slice H must mention SFT face path")
    ok("ESP + deploy + docs lock P0.1/P0.2 wound lab + SFT face")


def main() -> int:
    lab = LAB.read_text(encoding="utf-8", errors="replace")
    main_txt = MAIN.read_text(encoding="utf-8", errors="replace")
    bed = BED.read_text(encoding="utf-8", errors="replace")
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    test_lab_script(lab)
    test_wiring(main_txt, bed, decay)
    test_face_sft()
    test_mcm_matches_wound_file()
    test_esp_deploy_docs()
    print("All decay wound lab (H P0.1) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
