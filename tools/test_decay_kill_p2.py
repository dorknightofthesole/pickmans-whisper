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
    prep = extract_function(victims, "PrepAimedDecayStage")
    for needle in (
        "ResolveVictimsAimActor",
        "IsDead()",
        "ForceDecayKillClockToStage",
        "SetDecayKillLastStage",
        "StampDecayKill",
    ):
        if needle not in prep:
            fail(f"PrepAimedDecayStage must use {needle}")
    if "ApplyDecayStageOverlays" in prep:
        fail("PrepAimedDecayStage must NOT ApplyDecayStageOverlays (clock only)")
    reset_body = extract_function(victims, "ResetAimedDecayKillClock")
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
    mcm_apply = extract_function(victims, "MCMApplyAimedDecayStage")
    if "iVictimDecayStage:Victims" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must read iVictimDecayStage:Victims")
    if "PrepAimedDecayStage" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must PrepAimedDecayStage (clock only)")
    if "ApplyDecayStageOverlays" in mcm_apply:
        fail("MCMApplyAimedDecayStage must NOT ApplyDecayStageOverlays — KillerScan SyncDecay owns apply")
    if "StartTimer" in mcm_apply:
        fail("MCMApplyAimedDecayStage must not StartTimer (nudge parked)")
    if "PARKED" not in mcm_apply:
        fail("MCMApplyAimedDecayStage MessageBox must say PARKED")
    if "MessageBox" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must MessageBox result")
    if "KillerScan" not in mcm_apply:
        fail("MCMApplyAimedDecayStage MessageBox must mention KillerScan")
    if "McmDecayButtonBusy" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must ignore re-entrant CallFunction spam")
    if "WriteDecayStageStatusToMcmForActor(aimed, False)" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must not SyncVictimDecayStageStepper mid-button")
    mcm_reset = extract_function(victims, "MCMResetAimedDecayKillClock")
    if "ResetAimedDecayKillClock" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must ResetAimedDecayKillClock")
    if 'iVictimDecayStage:Victims", 0' not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must force selector to stage 0")
    if "ApplyDecayStageOverlays" in mcm_reset:
        fail("MCMResetAimedDecayKillClock must NOT ApplyDecayStageOverlays")
    if "McmDecayButtonBusy" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must ignore re-entrant CallFunction spam")
    # Legacy +1 entry — clock only
    mcm_adv = extract_function(victims, "MCMAdvanceAimedDecayStage")
    if "ApplyDecayStageOverlays" in mcm_adv:
        fail("MCMAdvanceAimedDecayStage must NOT ApplyDecayStageOverlays")
    if "QueueAimedDecayAdvance" not in mcm_adv:
        fail("MCMAdvanceAimedDecayStage must QueueAimedDecayAdvance")
    if "NoteForcedDecayClockForTest" not in prep:
        fail("PrepAimedDecayStage must NoteForcedDecayClockForTest (clear KillerScan rate-limit)")
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
    ok("MCM Victims decay test harness is clock-only; KillerScan SyncDecay applies")


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
