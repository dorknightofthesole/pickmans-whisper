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
    knife = extract_function(main, "ProcessKnifeCreditFromWorldScan")
    if "SyncDecayForKnifeCorpse" in knife:
        fail("ProcessKnifeCreditFromWorldScan must NOT SyncDecay")
    if "FindActors" in knife:
        fail("ProcessKnifeCreditFromWorldScan must not FindActors")
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
    if "ProcessKnifeCreditFromWorldScan" in voice:
        fail("VoiceScan must not own knife credit")
    if "RegisterForCustomEvent" in voice:
        fail("VoiceScan must not CustomEvent-listen (direct HandleWorldScanVoice)")
    knife_fn = extract_function(main, "HandleWorldScanKnifeAimWarm")
    if "TickLookFixation" in knife_fn or "MaybeSpeakNoticeLine" in knife_fn:
        fail("HandleWorldScanKnifeAimWarm must not own voice (VoiceScan does)")
    if "StartDecaySyncLoop" in main:
        fail("retire StartDecaySyncLoop — overlays via WorldScan CallFunctionNoWait")
    if "StartWorldScanLoop()" not in extract_function(main, "ArmRuntimeLoops"):
        fail("ArmRuntimeLoops must StartWorldScanLoop")

    ensure = extract_function(main, "EnsureDecayForTrackedVictim")
    if "FindVictimSlot" not in ensure or "StampDecayKill" not in ensure:
        fail("EnsureDecayForTrackedVictim must FindVictimSlot + StampDecayKill")
    if "abApplyOverlays" not in ensure:
        fail("EnsureDecayForTrackedVictim must take abApplyOverlays (NoWait stamps without LooksMenu)")
    if "IsNonGameplayCorpse" not in ensure:
        fail("EnsureDecayForTrackedVictim must skip bed/lab corpses")
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    overlay = extract_function(decay, "SyncOverlaysFromWorldScanSnapshot")
    if "SyncDecayForKnifeCorpse" not in overlay:
        fail("SyncOverlaysFromWorldScanSnapshot must SyncDecayForKnifeCorpse")
    if "DecaySyncBackoffUntil" not in overlay:
        fail("SyncOverlaysFromWorldScanSnapshot must backoff on LooksMenu apply failure")
    if "FindActors" in overlay:
        fail("SyncOverlaysFromWorldScanSnapshot must not FindActors")
    if "EnsureDecayForTrackedVictim" not in overlay:
        fail("SyncOverlaysFromWorldScanSnapshot must stamp tracked victims without overlays first")
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
    ok("decay sync on WorldScan NoWait + bed gift not stamped")


def test_docs() -> None:
    slice_h = SLICE_H.read_text(encoding="utf-8")
    if "startHours" not in slice_h:
        fail("SLICE_H must document startHours")
    if "0.25" not in slice_h or "240" not in slice_h:
        fail("SLICE_H must document Pallor 0.25h and Black 240h thresholds")
    ok("SLICE_H documents P2 hour thresholds")


def test_mcm_decay_stage_row() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    if "WriteDecayStageStatusToMcm" not in main:
        fail("Main must WriteDecayStageStatusToMcm")
    if "FormatDecayStageStatusForActor" not in main:
        fail("Main must FormatDecayStageStatusForActor")
    if "sDecayStage:Victims" not in main:
        fail("Main must write MCM sDecayStage:Victims")
    if "sDecayStage:Debug" in main:
        fail("Decay stage row moved off Debug — must not write sDecayStage:Debug")
    push = extract_function(main, "PushVictimsPanelStrings")
    if "WriteDecayStageStatusToMcm" not in push:
        fail("PushVictimsPanelStrings must WriteDecayStageStatusToMcm")
    write = extract_function(main, "WriteDecayStageStatusToMcm")
    if "ResolveVictimsAimActor" not in write:
        fail("WriteDecayStageStatusToMcm must ResolveVictimsAimActor (MCM-open aim cache)")
    if "TickVictimsAimCache" not in main:
        fail("Main must TickVictimsAimCache so living aim enters Victims cache")
    cache = extract_function(main, "TickVictimsAimCache")
    if "IsFixationEligible" in cache:
        fail("TickVictimsAimCache must not use IsFixationEligible (rejects dead)")
    if "GetLastActivateTargetRef" in cache:
        fail("TickVictimsAimCache must not sticky-activate (regressed corpse cache)")
    if "GetFacedSeverCorpse" in extract_function(main, "ResolveVictimsAimActor"):
        fail("ResolveVictimsAimActor must not GetFacedSeverCorpse (MCM Refresh FindActors hitch)")
    if "OnWorldScanVictimsAim" not in main:
        fail("Main must OnWorldScanVictimsAim (fills aim cache from WorldScan event)")
    if "IsInMenuMode" not in extract_function(main, "EnsureDecayForTrackedVictim"):
        fail("EnsureDecayForTrackedVictim must defer overlays while MCM open")
    if "NoteVictimsAimActor" not in extract_function(main, "ProcessKnifeKill"):
        fail("ProcessKnifeKill must NoteVictimsAimActor")
    if "FormatDecayStageStatusForFormId" not in main:
        fail("Main must FormatDecayStageStatusForFormId (decay row without aim)")
    if "last kill" not in write and "DecayKillSlotCount" not in write:
        fail("WriteDecayStageStatusToMcm must fall back to last stamped knife kill")
    cfg = (ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json").read_text(
        encoding="utf-8"
    )
    if '"id": "sDecayStage:Victims"' not in cfg:
        fail("config.json missing sDecayStage:Victims on Victims page")
    if '"id": "sDecayStage:Debug"' in cfg:
        fail("config.json must not keep sDecayStage:Debug")
    settings = (ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini").read_text(
        encoding="utf-8"
    )
    if "sDecayStage=" not in settings:
        fail("settings.ini must default sDecayStage=")
    if "[Victims]" not in settings or "sDecayStage=" not in settings.split("[Victims]", 1)[1]:
        fail("settings.ini sDecayStage must live under [Victims]")
    ok("MCM Victims decay stage row wired")


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
