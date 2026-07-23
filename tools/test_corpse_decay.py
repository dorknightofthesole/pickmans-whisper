#!/usr/bin/env python3
"""Contracts for Slice H P1 — ROF DeadOverlays via LooksMenu.

Locks:
  - tools/stubs/Overlays.psc matches real LooksMenu AddEntry/Add/Update API
  - DecayWoundOverlays.txt is the template-id source; ids ⊆ ROF DeadOverlays JSON
  - CorpseDecay soft-checks LooksMenu + INVB_OverlayFramework_DeadOverlays.esp
  - No PlayImpactEffect / IPDS path; no ESP master on ROF
  - BedGift present + MCM DebugForceCorpseDecayOverlays wired
  - ESP/deploy compile CorpseDecay

Usage:
  python tools/test_corpse_decay.py
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
OVERLAYS_STUB = ROOT / "tools" / "stubs" / "Overlays.psc"
WOUND_FILE = ROOT / "Data" / "PickmansWhisper" / "config" / "DecayWoundOverlays.txt"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
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


def test_overlays_stub() -> None:
    if not OVERLAYS_STUB.is_file():
        fail("missing tools/stubs/Overlays.psc (LooksMenu F4EE API)")
    text = OVERLAYS_STUB.read_text(encoding="utf-8", errors="replace")
    if "Scriptname Overlays Native Hidden" not in text:
        fail("Overlays stub must be Native Hidden (LooksMenu)")
    if "Function AddEntry(Actor akActor, bool isFemale, int priority, string template) global" not in text:
        fail("Overlays stub must declare AddEntry helper")
    if not re.search(
        r"int\s+Function\s+Add\s*\(\s*Actor\s+akActor\s*,\s*bool\s+isFemale\s*,\s*Entry\s+overlay\s*\)\s*global\s+native",
        text,
    ):
        fail("Overlays stub must declare Add ... global native")
    if "Function Update(Actor akActor) global native" not in text:
        fail("Overlays stub must declare Update native")
    ok("Overlays.psc LooksMenu stub")


def test_decay_script(decay: str) -> None:
    if "Scriptname PickmansWhisperCorpseDecayScript extends Quest" not in decay:
        fail("CorpseDecay must extend Quest")
    if "PlayImpactEffect" in decay or "FID_DECAY_IPDS" in decay:
        fail("CorpseDecay must not use retired PlayImpactEffect / IPDS path")
    if "INVB_OverlayFramework.esp" in decay and "master" in decay.lower():
        fail("must not master INVB_OverlayFramework.esp")
    if 'PLUGIN_DEAD_OVERLAYS = "INVB_OverlayFramework_DeadOverlays.esp"' not in decay:
        fail("CorpseDecay must soft-check DeadOverlays.esp")
    if 'PLUGIN_LOOKSMENU = "LooksMenu.esp"' not in decay:
        fail("CorpseDecay must soft-check LooksMenu.esp")
    if "IsPluginInstalled" not in decay:
        fail("CorpseDecay must IsPluginInstalled soft deps")
    if "DecayWoundOverlays.txt" not in decay:
        fail("CorpseDecay must load DecayWoundOverlays.txt")
    if "Overlays.Add" not in decay or "Overlays.Update" not in decay:
        fail("CorpseDecay must Overlays.Add + Update")
    if "Overlays.AddEntry" in decay:
        fail("CorpseDecay must not use AddEntry (zero tint) — use tinted Overlays.Add")
    if "BED_GIFT_WOUND_COUNT = 6" not in decay:
        fail("CorpseDecay must BED_GIFT_WOUND_COUNT = 6 for coverage look-test")
    tint = extract_function(decay, "AddTintedOverlay")
    if "overlay.red" not in tint or "Overlays.Add" not in tint:
        fail("AddTintedOverlay must fill Entry and Overlays.Add")
    if "afR" not in tint or "afA" not in tint:
        fail("AddTintedOverlay must take tint rgba params")
    if "RemoveMatchingOverlays" not in decay:
        fail("CorpseDecay must RemoveMatchingOverlays for bank stacking")
    lab_n = extract_function(decay, "ApplyTintedWoundTemplateN")
    if "ApplyTintedTemplateN" not in lab_n:
        fail("ApplyTintedWoundTemplateN must call ApplyTintedTemplateN")
    if "SoftDepsReady" not in lab_n:
        fail("ApplyTintedWoundTemplateN must SoftDepsReady")
    skin_n = extract_function(decay, "ApplyTintedSkinTemplateN")
    if "SoftSkinDepsReady" not in skin_n or "ApplyTintedTemplateN" not in skin_n:
        fail("ApplyTintedSkinTemplateN must SoftSkinDepsReady + ApplyTintedTemplateN")
    if 'PLUGIN_PORC_OVERLAYS = "porcOverlays.esl"' not in decay:
        fail("CorpseDecay must soft-check porcOverlays.esl")
    if "DecaySkinOverlays.txt" not in decay:
        fail("CorpseDecay must reference DecaySkinOverlays.txt")
    apply = extract_function(decay, "ApplyDecayWoundOverlays")
    if "ApplyDecayWoundOverlaysTinted" not in apply:
        fail("ApplyDecayWoundOverlays must delegate to ApplyDecayWoundOverlaysTinted")
    if "WOUND_TINT_R" not in apply or "WOUND_TINT_A" not in apply:
        fail("ApplyDecayWoundOverlays must pass WOUND_TINT_* rgba defaults")
    tinted = extract_function(decay, "ApplyDecayWoundOverlaysTinted")
    if "AddTintedWoundOverlay" not in tinted:
        fail("ApplyDecayWoundOverlaysTinted must AddTintedWoundOverlay")
    if "SoftDepsReady" not in tinted and "IsPluginInstalled" not in tinted:
        fail("ApplyDecayWoundOverlaysTinted must gate on soft deps")
    stage_fn = extract_function(decay, "ApplyDecayStageOverlays")
    if "ApplyDecayFaceArmorForStage" not in stage_fn:
        fail("ApplyDecayStageOverlays must ApplyDecayFaceArmorForStage (Slice I)")
    if "FillDecayStageSkins" not in stage_fn:
        fail("ApplyDecayStageOverlays must FillDecayStageSkins from ModConfig")
    if "GetDecayStageTintA" not in stage_fn:
        fail("ApplyDecayStageOverlays must use GetDecayStageTintA")
    if "ClearSkinBankOverlays" not in stage_fn:
        fail("ApplyDecayStageOverlays must ClearSkinBankOverlays before stage skins (tint swap)")
    if "ApplyTintedAllSkinTemplatesKeepExisting" not in stage_fn:
        fail("ApplyDecayStageOverlays must ApplyTintedAllSkinTemplatesKeepExisting")
    if stage_fn.find("ClearSkinBankOverlays") > stage_fn.find("ApplyTintedAllSkinTemplatesKeepExisting"):
        fail("ApplyDecayStageOverlays must clear skin bank BEFORE KeepExisting apply")
    if "GetDecayStageAllScars" not in stage_fn:
        fail("ApplyDecayStageOverlays must honor ModConfig scars flag")
    # Face after body — Overlays.Update strips slot-54 if face is equipped first.
    face_idx = stage_fn.find("ApplyDecayFaceArmorForStage")
    skin_idx = stage_fn.find("ApplyTintedAllSkinTemplatesKeepExisting")
    if face_idx < 0 or skin_idx < 0 or face_idx < skin_idx:
        fail("ApplyDecayStageOverlays must ApplyDecayFaceArmorForStage AFTER body skin apply")
    if "body skipped" not in stage_fn:
        fail("ApplyDecayStageOverlays must soft-skip body (face still succeeds) when skins/deps fail")
    bed = extract_function(decay, "ApplyBedGiftDecayOverlays")
    if "ApplyDecayWoundOverlaysTinted" not in bed:
        fail("ApplyBedGiftDecayOverlays must ApplyDecayWoundOverlaysTinted (darkened wounds)")
    if "GetBedGiftWoundAlpha" not in bed:
        fail("ApplyBedGiftDecayOverlays must read ModConfig bedGiftWoundAlpha")
    if "GetDecayStageTintR" not in bed:
        fail("ApplyBedGiftDecayOverlays must tint wounds with decay stage RGB")
    if "ApplyDecayStageOverlays" not in bed:
        fail("ApplyBedGiftDecayOverlays must ApplyDecayStageOverlays (Black Putrefaction)")
    if "BED_GIFT_DECAY_STAGE" not in bed and "BED_GIFT_DECAY_STAGE = 4" not in decay:
        fail("CorpseDecay must BED_GIFT_DECAY_STAGE = 4 for Black Putrefaction")
    if "BED_GIFT_DECAY_STAGE = 4" not in decay:
        fail("CorpseDecay must BED_GIFT_DECAY_STAGE = 4")
    debug_force = extract_function(decay, "DebugForceCorpseDecayOverlays")
    if "ApplyBedGiftDecayOverlays" not in debug_force:
        fail("DebugForceCorpseDecayOverlays must use ApplyBedGiftDecayOverlays (same path)")
    ok("CorpseDecayScript ROF/LooksMenu tinted apply helper")


def test_wiring(bed: str, main: str) -> None:
    present = extract_function(bed, "PresentBedCorpseOnWake")
    if "MaybeApplyBedGiftDecayOverlays()" in present or "decay.ApplyBedGiftDecayOverlays" in present:
        fail("PresentBedCorpseOnWake must NOT sync-apply overlays (stalls SleepStop / MCM Force)")
    if "BedOverlaysApplied" not in present:
        fail("PresentBedCorpseOnWake must gate fallback on BedOverlaysApplied")
    if "ScheduleBedGiftDecayOverlays" not in present:
        fail("PresentBedCorpseOnWake must ScheduleBedGiftDecayOverlays as fallback only")
    warm = extract_function(bed, "MaybeWarmBedGiftBody")
    if "ScheduleBedGiftDecayOverlays" not in warm:
        fail("MaybeWarmBedGiftBody must ScheduleBedGiftDecayOverlays after PlaceAtMe (pre-Enable)")
    sleep_start = extract_function(bed, "HandlePlayerSleepStart")
    if "MaybeApplyBedGiftDecayOverlays" not in sleep_start:
        fail("HandlePlayerSleepStart must MaybeApplyBedGiftDecayOverlays if still pending")
    if "MaybeApplyBedGiftDecayOverlays" not in bed:
        fail("BedGift must still MaybeApplyBedGiftDecayOverlays")
    if "aiTimerID == TIMER_BED_OVERLAYS" not in bed and "aiTimerID==TIMER_BED_OVERLAYS" not in bed.replace(" ", ""):
        fail("BedGift OnTimer must handle TIMER_BED_OVERLAYS")
    maybe = extract_function(bed, "MaybeApplyBedGiftDecayOverlays")
    if "ApplyBedGiftDecayOverlays" not in maybe:
        fail("MaybeApplyBedGiftDecayOverlays must call ApplyBedGiftDecayOverlays")
    if "ParkWarmedBedCorpse" not in maybe:
        fail("MaybeApplyBedGiftDecayOverlays must re-park after LooksMenu Enable during warm")
    if "BedOverlaysApplied = True" not in maybe and "BedOverlaysApplied=True" not in maybe.replace(" ", ""):
        fail("MaybeApplyBedGiftDecayOverlays must set BedOverlaysApplied")
    if "CreateBedCorpseAt" in maybe or "PlaceAtMe" in maybe:
        fail("MaybeApplyBedGiftDecayOverlays must not touch spawn")
    clear = extract_function(bed, "ClearBedCorpse")
    if "TIMER_BED_OVERLAYS" not in clear:
        fail("ClearBedCorpse must CancelTimer TIMER_BED_OVERLAYS")
    if "BedOverlaysApplied = False" not in clear and "BedOverlaysApplied=False" not in clear.replace(" ", ""):
        fail("ClearBedCorpse must reset BedOverlaysApplied")
    if "Function CorpseDecay()" not in main:
        fail("Main must expose CorpseDecay() façade")
    if "DebugForceCorpseDecayOverlays" not in main:
        fail("Main must façade DebugForceCorpseDecayOverlays")
    if "PlayImpactEffect" in bed or "PlayImpactEffect" in main:
        fail("user scripts must not call PlayImpactEffect for Slice H")
    if "bedGiftWoundAlpha" not in main or "GetBedGiftWoundAlpha" not in main:
        fail("Main must load/expose bedGiftWoundAlpha for bed gift wound opacity")
    ok("BedGift + Main CorpseDecay wiring")


def test_wound_config_vs_rof() -> None:
    ids = wound_ids_from_config()
    for tid in ids:
        if not tid.startswith("Female_"):
            fail(f"P1 wound list should be Female_* DeathMarks only, got {tid}")
    ok(f"DecayWoundOverlays.txt ({len(ids)} Female_* ids)")
    load_dotenv()
    env_path = os.environ.get("ROF_DEAD_OVERLAYS_JSON", "").strip()
    if not env_path:
        print("SKIP: set ROF_DEAD_OVERLAYS_JSON in .env to verify ids against ROF pack")
        return
    rof_json = Path(env_path)
    if not rof_json.is_file():
        fail(f"ROF_DEAD_OVERLAYS_JSON not a file: {rof_json}")
    data = json.loads(rof_json.read_text(encoding="utf-8"))
    known = {o["id"] for o in data}
    missing = [i for i in ids if i not in known]
    if missing:
        fail(f"DecayWoundOverlays ids missing from ROF JSON: {missing}")
    ok(f"wound ids subset of ROF DeadOverlays JSON ({rof_json.parent.name})")


def test_mcm_esp_deploy_docs() -> None:
    mcm = MCM.read_text(encoding="utf-8")
    if "DebugForceCorpseDecayOverlays" not in mcm:
        fail("MCM must have Force corpse decay overlays button")
    if "DebugForceCorpseDecayDecals" in mcm:
        fail("MCM must not keep retired Force corpse decay decals")
    esp = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperCorpseDecayScript" not in esp:
        fail("build_hunger_spell_esp.py must attach CorpseDecay")
    deploy_ps1 = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    deploy_sh = DEPLOY_SH.read_text(encoding="utf-8", errors="replace")
    if "test_corpse_decay.py" not in deploy_ps1 or "test_corpse_decay.py" not in deploy_sh:
        fail("deploy scripts must run test_corpse_decay.py")
    if "PickmansWhisperCorpseDecayScript.psc" not in deploy_ps1:
        fail("build-deploy-local.ps1 must Caprica-compile CorpseDecay")
    if 'PSC_DECAY="PickmansWhisperCorpseDecayScript.psc"' not in deploy_sh:
        fail("build-deploy-local.sh must define PSC_DECAY")
    slice_h = SLICE_H.read_text(encoding="utf-8")
    if "DeadOverlays" not in slice_h and "LooksMenu" not in slice_h:
        fail("SLICE_H must document LooksMenu / ROF DeadOverlays path")
    if "PlayImpactEffect" not in slice_h or "retired" not in slice_h.lower():
        fail("SLICE_H must still note PlayImpactEffect retired")
    road = ROADMAP.read_text(encoding="utf-8")
    if "DeadOverlays" not in road and "LooksMenu" not in road:
        fail("ROADMAP Slice H must mention LooksMenu / DeadOverlays")
    ok("MCM + ESP + deploy + docs lock ROF/LooksMenu P1")


def main() -> int:
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    bed = BED.read_text(encoding="utf-8", errors="replace")
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    test_overlays_stub()
    test_decay_script(decay)
    test_wiring(bed, main)
    test_wound_config_vs_rof()
    test_mcm_esp_deploy_docs()
    print("All corpse-decay (H P1 ROF/LooksMenu) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
