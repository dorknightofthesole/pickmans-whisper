#!/usr/bin/env python3
"""Contracts for Slice H P2 knife-kill decay stamp + killscan sync.

Usage:
  python tools/test_decay_kill_p2.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"
BED = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperBedGiftScript.psc"
SLICE_H = ROOT / "docs" / "SLICE_H_CORPSE_DECAY.md"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(src: str, name: str) -> str:
    m = re.search(rf"(?:Bool |Float |Int |String |Function )?Function {re.escape(name)}\(", src)
    if not m:
        # Bool Function ...
        m = re.search(rf"Function {re.escape(name)}\(", src)
    if not m:
        fail(f"missing Function {name}")
    start = m.start()
    end = src.find("\nEndFunction", start)
    if end < 0:
        fail(f"unclosed Function {name}")
    return src[start : end + len("\nEndFunction")]


def test_registry_and_stamp() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    if "DECAY_KILL_MAX = 32" not in main:
        fail("Main must DECAY_KILL_MAX = 32")
    if "DecayKillIds" not in main or "DecayKillGameTime" not in main or "DecayKillLastStage" not in main:
        fail("Main must declare DecayKillIds / GameTime / LastStage")
    for name in (
        "StampDecayKill",
        "FindDecayKillSlot",
        "GetDecayKillGameTime",
        "GetDecayKillLastStage",
        "SetDecayKillLastStage",
        "ResolveDecayStageForKill",
        "EvictOldestDecayKill",
    ):
        extract_function(main, name)
    stamp = extract_function(main, "StampDecayKill")
    if "GetCurrentGameTime" not in stamp:
        fail("StampDecayKill must stamp Utility.GetCurrentGameTime")
    if "LastKnifeActivityGameTime" in stamp:
        fail("StampDecayKill must not reuse LastKnifeActivityGameTime")
    if "DecayKillLastStage" not in stamp or "-1" not in stamp:
        fail("StampDecayKill must reset lastStage to -1")
    process = extract_function(main, "ProcessKnifeKill")
    if "StampDecayKill" not in process:
        fail("ProcessKnifeKill must StampDecayKill")
    if "SyncDecayForKnifeCorpse" in process:
        fail("ProcessKnifeKill must NOT SyncDecay (Utility.Wait starved Notice/Recognition)")
    ok("kill registry + ProcessKnifeKill stamp only")


def test_killscan_sync() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    knife = extract_function(main, "ProcessKnifeCreditFromKillerScan")
    if "SyncDecayForKnifeCorpse" in knife:
        fail("ProcessKnifeCreditFromKillerScan must NOT SyncDecay")
    if "FindActors" in knife:
        fail("ProcessKnifeCreditFromKillerScan must not FindActors")
    if "EnsureDecayForTrackedVictim" in knife:
        fail("knife credit must not EnsureDecay (CorpseDecay NoWait owns stamps + overlays)")
    voice_path = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceScanScript.psc"
    if not voice_path.is_file():
        fail("VoiceScan script missing")
    voice = voice_path.read_text(encoding="utf-8", errors="replace")
    if 'MaybeSpeakNoticeLine("killscan")' not in voice or "TickLookFixation()" not in voice:
        fail("VoiceScan must TickLookFixation + MaybeSpeakNoticeLine(killscan)")
    if "SyncDecayForKnifeCorpse" in voice:
        fail("VoiceScan must not SyncDecay")
    if "ProcessKnifeCreditFromKillerScan" in voice:
        fail("VoiceScan must not own knife credit")
    if "RegisterForCustomEvent" in voice:
        fail("VoiceScan must not CustomEvent-listen (direct HandleKillerScanVoice)")
    knife_fn = extract_function(main, "HandleKillerScanKnifeAimWarm")
    if "TickLookFixation" in knife_fn or "MaybeSpeakNoticeLine" in knife_fn:
        fail("HandleKillerScanKnifeAimWarm must not own voice (VoiceScan does)")
    if "StartDecaySyncLoop" in main:
        fail("retire StartDecaySyncLoop — overlays via KillerScan CallFunctionNoWait")
    if "StartKillerScanLoop()" not in extract_function(main, "ArmRuntimeLoops"):
        fail("ArmRuntimeLoops must StartKillerScanLoop")

    ensure = extract_function(main, "EnsureDecayForTrackedVictim")
    if "FindVictimSlot" not in ensure or "StampDecayKill" not in ensure:
        fail("EnsureDecayForTrackedVictim must FindVictimSlot + StampDecayKill")
    if "abApplyOverlays" not in ensure:
        fail("EnsureDecayForTrackedVictim must take abApplyOverlays (NoWait stamps without LooksMenu)")
    if "IsNonGameplayCorpse" not in ensure:
        fail("EnsureDecayForTrackedVictim must skip bed/lab corpses")
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    overlay = extract_function(decay, "SyncOverlaysFromKillerScanSnapshot")
    if "SyncDecayForKnifeCorpse" not in overlay:
        fail("SyncOverlaysFromKillerScanSnapshot must SyncDecayForKnifeCorpse")
    if "DecaySyncBackoffUntil" not in overlay:
        fail("SyncOverlaysFromKillerScanSnapshot must backoff on LooksMenu apply failure")
    if "FindActors" in overlay:
        fail("SyncOverlaysFromKillerScanSnapshot must not FindActors")
    if "EnsureDecayForTrackedVictim" not in overlay:
        fail("SyncOverlaysFromKillerScanSnapshot must stamp tracked victims without overlays first")
    for needle in (
        "CorpseDecay sync skip | rate-limit",
        "CorpseDecay sync skip | ScanDead empty",
        "CorpseDecay sync skip | already running",
        "CorpseDecay sync begin",
        "CorpseDecay sync done",
        "CorpseDecay sync apply",
    ):
        if needle not in overlay:
            fail(f"SyncOverlaysFromKillerScanSnapshot must Trace {needle!r} (no silent skip)")
    if "OverlaySyncBusy" not in overlay:
        fail("SyncOverlaysFromKillerScanSnapshot must OverlaySyncBusy (block NoWait re-entry during LooksMenu Wait)")
    if "OVERLAY_SYNC_BUSY_MAX_SECONDS" not in decay:
        fail("CorpseDecay must OVERLAY_SYNC_BUSY_MAX_SECONDS watchdog for stuck OverlaySyncBusy")
    if "Function QueueAimedDecayApply" not in decay:
        fail("CorpseDecay must QueueAimedDecayApply (MCM Set/Reset paint path)")
    if "Function RunPendingAimedDecayApply" not in decay:
        fail("CorpseDecay must RunPendingAimedDecayApply")
    if "AimedDecayApplyCode" not in decay:
        fail("CorpseDecay must AimedDecayApplyCode so logs prove new PEX loaded")
    if "SyncDecay skip | stage==last" not in decay:
        fail("SyncDecayForKnifeCorpse must Trace stage==last skips (no silent no-op)")
    victims_src = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimsScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    refresh = extract_function(victims_src, "MCMRefreshVictimsPanel")
    if "WriteVictimsMcmAuxRows()" not in refresh:
        fail("MCMRefreshVictimsPanel must sync-write aux/decay (not only NoWait)")
    if "FormatDecayStageStatusForActor" not in refresh:
        fail("MCMRefreshVictimsPanel must FormatDecayStageStatusForActor for dialog (fresh line)")
    if "CallFunctionNoWait(\"WriteVictimsMcmAuxRows\"" in refresh:
        fail("MCMRefreshVictimsPanel must not NoWait aux rows (decay looked empty until later poll)")
    fmt = extract_function(main, "FormatDecayStageStatusForActor")
    if "EnsureDecayForTrackedVictim(ak, False)" not in fmt:
        fail("FormatDecayStageStatusForActor must stamp without overlays in MCM")
    if "not knife-tracked" in main:
        fail("retire unclear 'not knife-tracked' MCM copy")
    if "no decay clock" not in extract_function(main, "FormatDecayStageStatusForFormId"):
        fail("untracked corpses must say 'no decay clock'")
    sync = extract_function(decay, "SyncDecayForKnifeCorpse")
    if "ResolveDecayStageForKill" not in sync:
        fail("SyncDecayForKnifeCorpse must ResolveDecayStageForKill")
    if "ApplyDecayStageOverlays" not in sync:
        fail("SyncDecayForKnifeCorpse must ApplyDecayStageOverlays")
    if "SetDecayKillLastStage" not in sync:
        fail("SyncDecayForKnifeCorpse must SetDecayKillLastStage on success")
    if "GetDecayKillLastStage" not in sync:
        fail("SyncDecayForKnifeCorpse must skip when stage unchanged")
    if "SyncDecayForKnifeCorpse apply stage=" not in sync:
        fail("SyncDecayForKnifeCorpse must Trace before ApplyDecayStageOverlays")
    if "ApplyDecayStageOverlays failed" not in sync:
        fail("SyncDecayForKnifeCorpse must Trace ERROR when ApplyDecayStageOverlays returns false")
    killer = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillerScanScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    # AMBIENT DECAY DISPATCH DISABLED (deliberately) — the "unchanged" stamp trap plus
    # QueueUpdate's confirmed inability to render body overlays on a never-disabled
    # corpse made this path untestable. Simplified to MCM-only for now: Set/Reset decay
    # stage still applies immediately via QueueAimedDecayApply → OnMCMMenuClose, fully
    # independent of this dispatch. Lock that the call stays commented out, not gone —
    # it should come back once overlays are confirmed working end-to-end via MCM.
    active_dispatch_lines = [
        ln for ln in killer.splitlines()
        if 'CallFunctionNoWait("SyncOverlaysFromKillerScanSnapshot"' in ln and not ln.strip().startswith(";")
    ]
    if active_dispatch_lines:
        fail("KillerScan must NOT actively dispatch SyncOverlaysFromKillerScanSnapshot (disabled — MCM-only for now)")
    if 'CallFunctionNoWait("SyncOverlaysFromKillerScanSnapshot"' not in killer:
        fail("KillerScan Dispatch → CorpseDecay SyncOverlays call must still exist, commented out (not deleted)")
    if "AMBIENT DECAY DISPATCH DISABLED" not in killer:
        fail("KillerScan must document why the CorpseDecay dispatch is commented out")
    bed = BED.read_text(encoding="utf-8", errors="replace")
    if "StampDecayKill" in bed:
        fail("BedGift must not StampDecayKill (hallucination stays out of kill registry)")
    ok("decay sync on KillerScan NoWait + bed gift not stamped")


def test_docs() -> None:
    slice_h = SLICE_H.read_text(encoding="utf-8")
    if "startHours" not in slice_h:
        fail("SLICE_H must document startHours")
    if "0.25" not in slice_h or "240" not in slice_h:
        fail("SLICE_H must document Pallor 0.25h and Black 240h thresholds")
    ok("SLICE_H documents P2 hour thresholds")


def test_mcm_decay_stage_row() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    victims_path = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimsScript.psc"
    if not victims_path.is_file():
        fail(f"missing {victims_path}")
    victims = victims_path.read_text(encoding="utf-8", errors="replace")
    if "WriteDecayStageStatusToMcm" not in main:
        fail("Main must WriteDecayStageStatusToMcm")
    if "WriteDecayStageStatusToMcmForActor" not in main:
        fail("Main must WriteDecayStageStatusToMcmForActor")
    if "FormatDecayStageStatusForActor" not in main:
        fail("Main must FormatDecayStageStatusForActor")
    if "sDecayStage:Victims" not in main:
        fail("Main must write MCM sDecayStage:Victims")
    if "sDecayStage:Debug" in main:
        fail("Decay stage row moved off Debug — must not write sDecayStage:Debug")
    push = extract_function(victims, "PushVictimsPanelStrings")
    if "WriteVictimsMcmAuxRows" not in push and "PushVictimsAimedOnly" not in push:
        fail("PushVictimsPanelStrings must PushVictimsAimedOnly + WriteVictimsMcmAuxRows")
    if "WriteVictimsMcmAuxRows" not in main:
        fail("Main must WriteVictimsMcmAuxRows for Victims NoWait aux push")
    write = extract_function(main, "WriteDecayStageStatusToMcmForActor")
    if "FormatDecayStageStatusForActor" not in write:
        fail("WriteDecayStageStatusToMcmForActor must FormatDecayStageStatusForActor")
    if "last kill" not in write and "DecayKillSlotCount" not in write:
        fail("WriteDecayStageStatusToMcmForActor must fall back to last stamped knife kill")
    write_wrap = extract_function(main, "WriteDecayStageStatusToMcm")
    if "ResolveVictimsAimActor" not in write_wrap:
        fail("WriteDecayStageStatusToMcm must ResolveVictimsAimActor (MCM-open aim cache)")
    if "TickVictimsAimCache" not in main:
        fail("Main must TickVictimsAimCache façade")
    cache = extract_function(victims, "TickVictimsAimCache")
    if "IsFixationEligible" in cache:
        fail("TickVictimsAimCache must not use IsFixationEligible (rejects dead)")
    if "GetLastActivateTargetRef" in cache:
        fail("TickVictimsAimCache must not sticky-activate (regressed corpse cache)")
    if "GetFacedSeverCorpse" in extract_function(victims, "ResolveVictimsAimActor"):
        fail("ResolveVictimsAimActor must not GetFacedSeverCorpse (MCM Refresh FindActors hitch)")
    if "OnKillerScanVictimsAim" not in main:
        fail("Main must OnKillerScanVictimsAim (fills aim cache from KillerScan event)")
    if "IsInMenuMode" not in extract_function(main, "EnsureDecayForTrackedVictim"):
        fail("EnsureDecayForTrackedVictim must defer overlays while MCM open")
    if "NoteVictimsAimActor" not in extract_function(main, "ProcessKnifeKill"):
        fail("ProcessKnifeKill must NoteVictimsAimActor")
    if "FormatDecayStageStatusForFormId" not in main:
        fail("Main must FormatDecayStageStatusForFormId (decay row without aim)")
    cfg = (ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json").read_text(
        encoding="utf-8"
    )
    if '"id": "sDecayStage:Victims"' not in cfg:
        fail("config.json missing sDecayStage:Victims on Victims page")
    if '"id": "sDecayStage:Debug"' in cfg:
        fail("config.json must not keep sDecayStage:Debug")
    if '"function": "MCMApplyAimedDecayStage"' not in cfg:
        fail("config.json Victims page must have Set decay stage -> MCMApplyAimedDecayStage")
    if '"function": "MCMResetAimedDecayKillClock"' not in cfg:
        fail("config.json Victims page must have Reset decay stage -> MCMResetAimedDecayKillClock")
    if '"id": "iVictimDecayStage:Victims"' not in cfg:
        fail("config.json Victims page must have iVictimDecayStage stepper")
    if '"scriptName": "PickmansWhisperVictimsScript"' not in cfg:
        fail("config.json Set / Reset / Load / Apply must target PickmansWhisperVictimsScript")
    if '"text": "Set decay stage"' not in cfg:
        fail("config.json missing Set decay stage button label")
    if '"text": "Reset decay stage"' not in cfg:
        fail("config.json missing Reset decay stage button label")
    if "Set decay clock" in cfg or "Reset kill clock" in cfg:
        fail("config.json must use Set/Reset decay stage labels (not clock/kill clock)")
    if "Apply decay stage" in cfg:
        fail("config.json must not keep Apply decay stage (clock-only test harness)")
    settings = (ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini").read_text(
        encoding="utf-8"
    )
    if "sDecayStage=" not in settings:
        fail("settings.ini must default sDecayStage=")
    if "[Victims]" not in settings or "sDecayStage=" not in settings.split("[Victims]", 1)[1]:
        fail("settings.ini sDecayStage must live under [Victims]")
    if "iVictimDecayStage=" not in settings.split("[Victims]", 1)[1]:
        fail("settings.ini iVictimDecayStage must live under [Victims]")

    if "ForceDecayKillClockToStage" not in main:
        fail("Main must ForceDecayKillClockToStage (backdate clock for MCM set stage)")
    force = extract_function(main, "ForceDecayKillClockToStage")
    if "DecayKillGameTime" not in force or "GetDecayStageStartHours" not in force:
        fail("ForceDecayKillClockToStage must set DecayKillGameTime from startHours")
    if "elapsedH / 24.0" not in force and "needH / 24.0" not in force:
        fail("ForceDecayKillClockToStage must subtract startHours/24 from now")
    if "needH + 0.001" not in force:
        fail("ForceDecayKillClockToStage must pad startHours>0 by 0.001h")
    if "SyncVictimDecayStageStepper" not in main:
        fail("Main must SyncVictimDecayStageStepper (keep Victims stepper current)")
    # PrepAimedDecayStage / ResetAimedDecayKillClock share aim+validity checks via
    # ResolveValidDecayTarget instead of duplicating ResolveVictimsAimActor/IsDead()/
    # IsNonGameplayCorpse in each.
    validator = extract_function(victims, "ResolveValidDecayTarget")
    for needle in ("ResolveVictimsAimActor", "IsDead()", "IsNonGameplayCorpse"):
        if needle not in validator:
            fail(f"ResolveValidDecayTarget must use {needle}")
    prep = extract_function(victims, "PrepAimedDecayStage")
    for needle in (
        "ResolveValidDecayTarget",
        "ForceDecayKillClockToStage",
        "SetDecayKillLastStage",
        "StampDecayKill",
    ):
        if needle not in prep:
            fail(f"PrepAimedDecayStage must use {needle}")
    if "ApplyDecayStageOverlays" in prep:
        fail("PrepAimedDecayStage must NOT ApplyDecayStageOverlays (clock only)")
    reset_body = extract_function(victims, "ResetAimedDecayKillClock")
    if "ResolveValidDecayTarget" not in reset_body:
        fail("ResetAimedDecayKillClock must use ResolveValidDecayTarget")
    if "StampDecayKill" not in reset_body:
        fail("ResetAimedDecayKillClock must StampDecayKill (murder time = now)")
    if 'iVictimDecayStage:Victims", 0' not in reset_body:
        fail("ResetAimedDecayKillClock must set stage selector to 0")
    if "ApplyDecayStageOverlays" in reset_body:
        fail("ResetAimedDecayKillClock must NOT ApplyDecayStageOverlays")
    queue = extract_function(victims, "QueueAimedDecayStage")
    if "PrepAimedDecayStage" not in queue:
        fail("QueueAimedDecayStage must PrepAimedDecayStage (legacy deferred)")
    if "ApplyDecayStageOverlays" in queue:
        fail("QueueAimedDecayStage must NOT ApplyDecayStageOverlays")
    adv = extract_function(victims, "QueueAimedDecayAdvance")
    if "QueueAimedDecayStage" not in adv:
        fail("QueueAimedDecayAdvance must wrap QueueAimedDecayStage (+1)")
    run = extract_function(victims, "RunPendingDecayAdvance")
    if "ApplyDecayStageOverlays" in run:
        fail("RunPendingDecayAdvance must NOT ApplyDecayStageOverlays (KillerScan owns apply)")
    if "StartTimer" in run:
        fail("RunPendingDecayAdvance parked — must not StartTimer")
    # MCMApplyAimedDecayStage / MCMResetAimedDecayKillClock share their report tail
    # (push status, latch stepper, queue paint, DiagNotify) via FinishMcmDecayStageAction.
    tail = extract_function(victims, "FinishMcmDecayStageAction")
    if "QueueAimedDecayApply" not in tail:
        fail("FinishMcmDecayStageAction must QueueAimedDecayApply (paint aimed corpse after MCM close)")
    if "DiagNotify(" not in tail:
        fail("FinishMcmDecayStageAction must DiagNotify result")
    if "Debug.MessageBox(" in tail:
        fail("FinishMcmDecayStageAction must not MessageBox")
    if "WriteDecayStageStatusToMcmForActor(aimed, False)" not in tail:
        fail("FinishMcmDecayStageAction must not SyncVictimDecayStageStepper mid-button")
    if "McmDecayButtonBusy" in victims:
        fail("VictimsScript must not use McmDecayButtonBusy (swallowed Set/Reset)")

    mcm_apply = extract_function(victims, "MCMApplyAimedDecayStage")
    if "iVictimDecayStage:Victims" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must read iVictimDecayStage:Victims")
    if "PrepAimedDecayStage" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must PrepAimedDecayStage (clock only)")
    if "ApplyDecayStageOverlays" in mcm_apply:
        fail("MCMApplyAimedDecayStage must NOT ApplyDecayStageOverlays (queue CorpseDecay aimed apply)")
    if "FinishMcmDecayStageAction" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must FinishMcmDecayStageAction (shared report tail)")
    if "ForceApply" in mcm_apply or "ForceApply" in prep:
        fail("MCM ForceApply path retired — clock + QueueAimedDecayApply")
    if "PARKED" in mcm_apply:
        fail("MCMApplyAimedDecayStage DiagNotify must not say PARKED")
    if "within ~1s" not in mcm_apply.lower() and "aimed corpse" not in mcm_apply.lower():
        fail("MCMApplyAimedDecayStage DiagNotify must say aimed corpse applies within ~1s")
    mcm_reset = extract_function(victims, "MCMResetAimedDecayKillClock")
    if "ResetAimedDecayKillClock" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must ResetAimedDecayKillClock")
    if "FinishMcmDecayStageAction" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must FinishMcmDecayStageAction (shared report tail)")
    if "FinishMcmDecayStageAction" in mcm_reset and ", 0)" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must force selector to stage 0 (FinishMcmDecayStageAction(..., 0))")
    if "ApplyDecayStageOverlays" in mcm_reset:
        fail("MCMResetAimedDecayKillClock must NOT ApplyDecayStageOverlays")
    mcm_adv = extract_function(victims, "MCMAdvanceAimedDecayStage")
    if "ApplyDecayStageOverlays" in mcm_adv:
        fail("MCMAdvanceAimedDecayStage must NOT ApplyDecayStageOverlays")
    if "QueueAimedDecayAdvance" not in mcm_adv:
        fail("MCMAdvanceAimedDecayStage must QueueAimedDecayAdvance")
    if "NoteDecayClockChangedForSync" not in prep:
        fail("PrepAimedDecayStage must NoteDecayClockChangedForSync (clear sync rate-limit)")
    if "ArmMcmForceApply" in prep or "ForceApplyMcmDecayStage" in prep:
        fail("PrepAimedDecayStage must not use MCM ForceApply")
    close = extract_function(victims, "OnMCMMenuClose")
    if "ForceApply" in close:
        fail("OnMCMMenuClose must not ForceApply")
    if "RunPendingAimedDecayApply" not in close:
        fail("OnMCMMenuClose must CallFunctionNoWait RunPendingAimedDecayApply")
    decay = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    if "Function ForceApplyMcmDecayStage" in decay or "Function ArmMcmForceApply" in decay:
        fail("CorpseDecay must not declare MCM ForceApply helpers")
    if "TIMER_MCM_FORCE_APPLY" in decay or "Event OnTimer" in decay:
        fail("CorpseDecay must not own MCM force-apply timer (use menu-close NoWait)")
    if "StartTimer(" in decay:
        fail("CorpseDecay must not StartTimer (Killer Orchestrator)")
    if "Function NoteDecayClockChangedForSync" not in decay:
        fail("CorpseDecay must NoteDecayClockChangedForSync")
    # OnMCMMenuClose (an MCM broadcast event) is not a reliable trigger — confirmed in
    # testing that RunPendingAimedDecayApply can go a whole session without firing even
    # once via that path. KillerScan's own tick is the fallback: cheap, no timer owned
    # by CorpseDecay (respects Killer Orchestrator), and independent of the disabled
    # ambient sweep so it survives even with SyncOverlaysFromKillerScanSnapshot off.
    check_pending = extract_function(decay, "CheckPendingAimedDecayApply")
    if "PendingAimedDecayActor" not in check_pending:
        fail("CheckPendingAimedDecayApply must check PendingAimedDecayActor")
    if "IsInMenuMode" not in check_pending:
        fail("CheckPendingAimedDecayApply must gate on Utility.IsInMenuMode")
    if "RunPendingAimedDecayApply" not in check_pending:
        fail("CheckPendingAimedDecayApply must call RunPendingAimedDecayApply")
    killer_full = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillerScanScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    dispatch_full = extract_function(killer_full, "DispatchListeners")
    active_check_lines = [
        ln for ln in dispatch_full.splitlines()
        if 'CallFunctionNoWait("CheckPendingAimedDecayApply"' in ln and not ln.strip().startswith(";")
    ]
    if not active_check_lines:
        fail("KillerScan DispatchListeners must actively CallFunctionNoWait CheckPendingAimedDecayApply")
    if "TIMER_DECAY_ADVANCE" not in victims:
        fail("VictimsScript must declare TIMER_DECAY_ADVANCE (CancelTimer only)")
    if "StartTimer(" in victims:
        fail("VictimsScript must not StartTimer")
    if "Victims()" not in extract_function(main, "MCMApplyAimedDecayStage"):
        fail("Main MCMApplyAimedDecayStage must façade via Victims()")
    if "Victims()" not in extract_function(main, "MCMResetAimedDecayKillClock"):
        fail("Main MCMResetAimedDecayKillClock must façade via Victims()")
    if "Victims()" not in extract_function(main, "MCMAdvanceAimedDecayStage"):
        fail("Main MCMAdvanceAimedDecayStage must façade via Victims()")
    ok("MCM Victims decay H P2: clock + QueueAimedDecayApply; ambient KillerScan sync kept")


def main() -> int:
    if not MAIN.is_file():
        fail(f"missing {MAIN}")
    test_registry_and_stamp()
    test_killscan_sync()
    test_docs()
    test_mcm_decay_stage_row()
    print("All decay-kill P2 contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
