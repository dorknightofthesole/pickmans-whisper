#!/usr/bin/env python3
"""Contracts for Slice H P1 — ROF DeadOverlays via LooksMenu.

Locks:
  - tools/stubs/Overlays.psc matches real LooksMenu AddEntry/Add/Update API
  - DecayWoundOverlays.txt is the template-id source; ids ⊆ ROF DeadOverlays JSON
  - CorpseDecay soft-checks LooksMenu + INVB_OverlayFramework_DeadOverlays.esp
  - No PlayImpactEffect / IPDS path; no ESP master on ROF
  - BedGift present + ApplyBedGiftDecayOverlays path
  - ESP/deploy compile CorpseDecay
  - DebugForceCorpseDecayOverlays retired (no CorpseDecay impl)

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
    if "IsScarSkinTemplate" in stage_fn:
        fail("ApplyDecayStageOverlays must not expand scars (simplified dirt/tint body)")
    if "IsDecayVisualsEnabled" not in stage_fn:
        fail("ApplyDecayStageOverlays must gate paint on IsDecayVisualsEnabled")
    if "visuals OFF" not in stage_fn:
        fail("ApplyDecayStageOverlays must soft-succeed when visuals OFF (stage clock still advances)")
    if "Function IsDecayVisualsEnabled" not in decay:
        fail("CorpseDecay must IsDecayVisualsEnabled (MCM bDecayVisuals, default on)")
    if 'bDecayVisuals:Victims' not in decay:
        fail("IsDecayVisualsEnabled must read bDecayVisuals:Victims")
    bed = extract_function(decay, "ApplyBedGiftDecayOverlays")
    if "IsDecayVisualsEnabled" in bed:
        fail("ApplyBedGiftDecayOverlays must NOT gate on IsDecayVisualsEnabled (vignette always paints)")
    if "ApplyDecayStageOverlays(akCorpse, stage, True)" not in bed and "ApplyDecayStageOverlays(akCorpse, stage,True)" not in bed:
        fail("ApplyBedGiftDecayOverlays must ApplyDecayStageOverlays(..., True) force paint")
    if "abForcePaint" not in stage_fn:
        fail("ApplyDecayStageOverlays must accept abForcePaint (bed gift bypasses MCM visuals off)")
    # Face first (mask lands even if LooksMenu stalls); re-equip after body strip.
    if "face-first" not in stage_fn:
        fail("ApplyDecayStageOverlays must Trace face-first")
    if "IsCorpseLimbsIntact" not in stage_fn:
        fail("ApplyDecayStageOverlays must IsCorpseLimbsIntact (no body overlays on stumps)")
    if "abForcePaint" not in stage_fn or "limbsIntact = True" not in stage_fn:
        fail("ApplyDecayStageOverlays must skip stump gate when abForcePaint (bed gift)")
    if "FaceArmorLoadBusy" not in decay:
        fail("CorpseDecay must FaceArmorLoadBusy to stop known=[] race")
    if "limbs missing" not in stage_fn:
        fail("ApplyDecayStageOverlays must skip/clear body when limbs missing (stump halo)")
    if "ClearCumBankOverlays" not in stage_fn:
        fail("ApplyDecayStageOverlays must ClearCumBankOverlays when limbs missing (white halo)")
    # QueueUpdate(bDoEquipment=True) rebuilds the biped from the base race + equipped
    # items — confirmed in testing this can regenerate a limb a native Dismember()
    # call already gibbed (visible disappear/reappear pop, severed limb restored).
    # Must not run when limbs are already known missing; nothing in that branch needs
    # a mesh refresh anyway since body/face overlay work was already skipped there.
    queue_idx = stage_fn.rfind("QueueUpdate(True, 0)")
    if queue_idx < 0:
        fail("ApplyDecayStageOverlays must QueueUpdate(True, 0) to refresh the mesh")
    gate_idx = stage_fn.rfind("If limbsIntact", 0, queue_idx)
    if gate_idx < 0:
        fail("ApplyDecayStageOverlays must gate the final QueueUpdate on limbsIntact (don't regenerate severed limbs)")
    # MCM bDecayMissingLimbs:Victims (default off) — overrides the stump-halo skip so
    # a dismembered corpse can be painted like a fully-limbed one, on request.
    if "Function IsDecayMissingLimbsAllowed" not in decay:
        fail("CorpseDecay must IsDecayMissingLimbsAllowed (MCM bDecayMissingLimbs, default off)")
    missing_limbs_fn = extract_function(decay, "IsDecayMissingLimbsAllowed")
    if "bDecayMissingLimbs:Victims" not in missing_limbs_fn:
        fail("IsDecayMissingLimbsAllowed must read bDecayMissingLimbs:Victims")
    if "bypassLimbGate" not in stage_fn:
        fail("ApplyDecayStageOverlays must compute bypassLimbGate (abForcePaint or IsDecayMissingLimbsAllowed)")
    if "IsDecayMissingLimbsAllowed" not in stage_fn:
        fail("ApplyDecayStageOverlays must gate bypassLimbGate on IsDecayMissingLimbsAllowed")
    if stage_fn.count("bypassLimbGate") < 4:
        fail("ApplyDecayStageOverlays must reuse bypassLimbGate for every Head1 dismember gate, not just the body one")
    face_idx = stage_fn.find("ApplyDecayFaceArmorForStage")
    skin_idx = stage_fn.find("ApplyTintedAllSkinTemplatesKeepExisting")
    if face_idx < 0 or skin_idx < 0 or face_idx > skin_idx:
        fail("ApplyDecayStageOverlays must ApplyDecayFaceArmorForStage BEFORE body skin apply")
    if "body skipped" not in stage_fn:
        fail("ApplyDecayStageOverlays must soft-skip body (face still succeeds) when skins/deps fail")
    if "Function StripDecayCorpseClothing" not in decay:
        fail("CorpseDecay must StripDecayCorpseClothing (ambient victims aren't nude like Bed Gift)")
    if "StripDecayCorpseClothing" not in stage_fn:
        fail("ApplyDecayStageOverlays must StripDecayCorpseClothing before body skins (worn armor hides the tint)")
    strip_idx = stage_fn.find("StripDecayCorpseClothing")
    apply_skins_idx = stage_fn.rfind("ApplyTintedAllSkinTemplatesKeepExisting")
    if strip_idx < 0 or apply_skins_idx < 0 or strip_idx > apply_skins_idx:
        fail("ApplyDecayStageOverlays must StripDecayCorpseClothing BEFORE applying body skins")
    # ForceCorpseMeshRefresh (Disable/Enable) was tried and reverted — it did make the
    # body overlay render, but tearing down/rebuilding an ambient corpse's 3D while
    # she's actively ragdolled broke IsDismembered ("Cannot find limb") and visually
    # looked like the NPC was being killed again. Must not come back without a
    # refresh method that doesn't touch the skeleton.
    if "Function ForceCorpseMeshRefresh" in decay:
        fail("ForceCorpseMeshRefresh was reverted (killed-again visual bug) — must not be reintroduced")
    if "Function IsCorpseLimbsIntact" not in decay:
        fail("CorpseDecay must IsCorpseLimbsIntact")
    if "Function QueueStripBodyDecayAfterDismember" not in decay:
        fail("CorpseDecay must QueueStripBodyDecayAfterDismember after butcher")
    if "CumOverlayIds.txt" not in decay or "Function ClearCumBankOverlays" not in decay:
        fail("CorpseDecay must load CumOverlayIds.txt + ClearCumBankOverlays (soft strip)")
    strip_fn = extract_function(decay, "StripBodyDecayOverlaysForDismember")
    if "ClearCumBankOverlays" not in strip_fn:
        fail("StripBodyDecayOverlaysForDismember must ClearCumBankOverlays")
    sever = extract_function(
        (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc").read_text(
            encoding="utf-8", errors="replace"
        ),
        "SeverCorpseLimb",
    )
    if "QueueStripBodyDecayAfterDismember" not in sever:
        fail("SeverCorpseLimb must QueueStripBodyDecayAfterDismember (clear stump halo)")
    cum_bank = ROOT / "Data" / "PickmansWhisper" / "config" / "CumOverlayIds.txt"
    if not cum_bank.is_file():
        fail("CumOverlayIds.txt must ship (CumOverlays strip bank)")
    cum_ids = [
        ln.strip()
        for ln in cum_bank.read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if len(cum_ids) < 10 or "Belly_1" not in cum_ids:
        fail("CumOverlayIds.txt must list CumOverlays template ids (e.g. Belly_1)")
    if len(cum_ids) > 64:
        fail("CumOverlayIds.txt exceeds LoadStageBank String[64] capacity")
    # Optional: set CUMOVERLAYS_JSON in .env to prove strip bank matches installed CumOverlays.
    cum_json_env = os.environ.get("CUMOVERLAYS_JSON", "").strip()
    if cum_json_env:
        cum_json = Path(cum_json_env)
        if not cum_json.is_file():
            fail(f"CUMOVERLAYS_JSON not a file: {cum_json}")
        src_ids = [e["id"] for e in json.loads(cum_json.read_text(encoding="utf-8"))]
        if sorted(cum_ids) != sorted(src_ids):
            fail(f"CumOverlayIds.txt must match {cum_json} ids (drift)")
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
    if "DebugForceCorpseDecayOverlays" in decay:
        fail("DebugForceCorpseDecayOverlays retired — must not return on CorpseDecay")
    ok("CorpseDecayScript ROF/LooksMenu tinted apply helper")

    # ReapplyDecayBodySkinsOnly (periodic body-skin self-heal) was tried and reverted —
    # confirmed QueueUpdate still never composites a new body texture onto an already-
    # loaded, never-disabled corpse; the retry just visibly flickered and settled back
    # to the base skin every time. Ambient body-texture decay is out of reach without a
    # refresh method that doesn't touch the skeleton (same conclusion as
    # ForceCorpseMeshRefresh above). Must not come back without solving that first.
    if "ReapplyDecayBodySkinsOnly" in decay:
        fail("ReapplyDecayBodySkinsOnly was reverted (confirmed QueueUpdate can't render it — just flickers) — must not be reintroduced")
    if "DECAY_BODY_REAPPLY_COOLDOWN_SECONDS" in decay:
        fail("DECAY_BODY_REAPPLY_COOLDOWN_SECONDS was reverted alongside ReapplyDecayBodySkinsOnly")


def test_wiring(bed: str, main: str) -> None:
    present = extract_function(bed, "PresentBedCorpseOnWake")
    if "MaybeApplyBedGiftDecayOverlays()" in present or "decay.ApplyBedGiftDecayOverlays" in present:
        fail("PresentBedCorpseOnWake must NOT sync-apply overlays (stalls SleepStop / MCM Force)")
    if 'CallFunctionNoWait("MaybeApplyBedGiftDecayOverlays"' in present:
        fail("PresentBedCorpseOnWake must not CallFunctionNoWait MaybeApply")
    # Pose (still-alive branch) finishes async via TIMER_BED_POSE; the overlay kick /
    # re-paint reset live on the shared FinishBedPresentTail, not inline in Present.
    tail = extract_function(bed, "FinishBedPresentTail")
    if "MaybeApplyBedGiftDecayOverlays()" in tail or "decay.ApplyBedGiftDecayOverlays" in tail:
        fail("FinishBedPresentTail must NOT sync-apply overlays (stalls SleepStop / MCM Force)")
    if "BedOverlaysApplied = False" not in tail:
        fail("FinishBedPresentTail must clear BedOverlaysApplied after pose (re-paint)")
    if "KickBedOverlayOnesHot" not in tail:
        fail("FinishBedPresentTail must KickBedOverlayOnesHot after pose")
    if 'CallFunctionNoWait("MaybeApplyBedGiftDecayOverlays"' in tail:
        fail("FinishBedPresentTail must not CallFunctionNoWait MaybeApply")
    spawn = extract_function(bed, "TrySpawnBedCorpse")
    if "KickBedOverlayOnesHot" not in spawn:
        fail("TrySpawnBedCorpse must KickBedOverlayOnesHot after PlaceAtMe (pre-Enable)")
    sleep_start = extract_function(bed, "HandlePlayerSleepStart")
    if "MaybeApplyBedGiftDecayOverlays" in sleep_start:
        fail("HandlePlayerSleepStart must not sync-apply LooksMenu decay")
    if "TrySpawnBedCorpse" not in sleep_start:
        fail("HandlePlayerSleepStart must TrySpawnBedCorpse (sole gameplay spawn)")
    if "MaybeApplyBedGiftDecayOverlays" not in bed:
        fail("BedGift must still MaybeApplyBedGiftDecayOverlays (from TIMER_BED_OVERLAYS OnTimer)")
    if "OnKillerScanDeadlines" in bed or "ScheduleBedGiftDecayOverlays" in bed:
        fail("BedGift must not use KillerScan overlay deadlines")
    if "BedOverlaysBusy" not in bed:
        fail("BedGift must BedOverlaysBusy against overlay re-entry")
    if "TIMER_BED_OVERLAYS" not in bed or "KickBedOverlayOnesHot" not in bed:
        fail("BedGift must TIMER_BED_OVERLAYS + KickBedOverlayOnesHot")
    maybe = extract_function(bed, "MaybeApplyBedGiftDecayOverlays")
    if "ApplyBedGiftDecayOverlays" not in maybe:
        fail("MaybeApplyBedGiftDecayOverlays must call ApplyBedGiftDecayOverlays")
    if "ParkWarmedBedCorpse" in maybe or "BedCorpseWarmed" in maybe:
        fail("MaybeApplyBedGiftDecayOverlays must not re-park — warm-park path retired")
    if "BedOverlaysApplied = True" not in maybe and "BedOverlaysApplied=True" not in maybe.replace(" ", ""):
        fail("MaybeApplyBedGiftDecayOverlays must set BedOverlaysApplied")
    if "CreateBedCorpseAt" in maybe or "PlaceAtMe" in maybe:
        fail("MaybeApplyBedGiftDecayOverlays must not touch spawn")
    clear = extract_function(bed, "ClearBedCorpse")
    if "CancelTimer(TIMER_BED_OVERLAYS)" not in clear:
        fail("ClearBedCorpse must CancelTimer(TIMER_BED_OVERLAYS)")
    if "BedOverlaysApplied = False" not in clear and "BedOverlaysApplied=False" not in clear.replace(" ", ""):
        fail("ClearBedCorpse must reset BedOverlaysApplied")
    if "Function CorpseDecay()" not in main:
        fail("Main must expose CorpseDecay() façade")
    if "DebugForceCorpseDecayOverlays" in main:
        fail("DebugForceCorpseDecayOverlays retired — must not remain on Main")
    if "PlayImpactEffect" in bed or "PlayImpactEffect" in main:
        fail("user scripts must not call PlayImpactEffect for Slice H")
    # TODO: review after ModConfigAlias move — bedGiftWoundAlpha may live on
    # ModConfigAlias / CorpseDecay only; Main GetBedGiftWoundAlpha may be gone.
    # if "bedGiftWoundAlpha" not in main or "GetBedGiftWoundAlpha" not in main:
    #     fail("Main must load/expose bedGiftWoundAlpha for bed gift wound opacity")
    if "DecayKillLastBodyReapplyReal" in main:
        fail("DecayKillLastBodyReapplyReal was reverted with ReapplyDecayBodySkinsOnly — must not be reintroduced")
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
    if "DebugForceCorpseDecayOverlays" in mcm:
        fail("MCM must not keep retired Force corpse decay overlays button")
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
