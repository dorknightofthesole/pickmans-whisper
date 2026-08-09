#!/usr/bin/env python3
"""Contracts for Killer Orchestrator — sole KillerScan timer + TargetSnapshot dispatch.

Locks:
  - PickmansWhisperKillerScanScript only FindActors producer
  - No PickmansWhisperKillerScanScript leftovers
  - Voice sync first; knife/overlays/cadence NoWait
  - Main ArmRuntimeLoops starts KillerScan only (no hunger/bond StartTimer)
  - Version 1.3.0 + Killer Orchestrator banner
  - KillerScan StartTimer may be parked (0); other features inventory: BedGift
    TIMER_BED_OVERLAYS / TIMER_BED_POSE

Usage:
  python tools/test_killer_scan_bus.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = ROOT / "Data" / "Scripts" / "Source" / "User"
MAIN = USER / "PickmansWhisperMainQuestScript.psc"
KILLER = USER / "PickmansWhisperKillerScanScript.psc"
VOICE = USER / "PickmansWhisperVoiceAliasScript.psc"
DECAY = USER / "PickmansWhisperCorpseDecayScript.psc"
VICTIMS = USER / "PickmansWhisperVictimsScript.psc"
BED = USER / "PickmansWhisperBedGiftScript.psc"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
FOMOD = ROOT / "fomod" / "info.xml"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"


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
        m = re.search(rf"Event\s+(?:[\w.]+\.)?{name}\s*\(", text)
    if not m:
        fail(f"missing function/event {name}")
    start = m.start()
    end_m = re.search(r"\n(?:EndFunction|EndEvent)\b", text[start:])
    if not end_m:
        fail(f"no End for {name}")
    return text[start : start + end_m.end()]


def test_no_worldscan_leftovers() -> None:
    if (USER / "PickmansWhisperWorldScanScript.psc").is_file():
        fail("PickmansWhisperWorldScanScript.psc must be deleted")
    for p in USER.glob("*.psc"):
        text = p.read_text(encoding="utf-8", errors="replace")
        if "PickmansWhisperWorldScanScript" in text or "StartWorldScanLoop" in text:
            fail(f"{p.name} still references WorldScan script/API")
        if re.search(r"\bWorldScan\b", text):
            fail(f"{p.name} still contains WorldScan token")
    esp = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if "WorldScan" in esp:
        fail("build_hunger_spell_esp.py still mentions WorldScan")
    if "PickmansWhisperKillerScanScript" not in esp:
        fail("ESP builder must attach PickmansWhisperKillerScanScript")
    ok("no WorldScan leftovers; KillerScan in ESP builder")


def test_killer_scan_producer() -> None:
    if not KILLER.is_file():
        fail("missing PickmansWhisperKillerScanScript.psc")
    text = KILLER.read_text(encoding="utf-8", errors="replace")
    run = extract_function(text, "RunKillerScanTick")
    if "BuildTargetSnapshot()" not in run:
        fail("RunKillerScanTick must BuildTargetSnapshot")
    if "DispatchListeners()" not in run:
        fail("RunKillerScanTick must DispatchListeners")
    build = extract_function(text, "BuildTargetSnapshot")
    if "FindActors" not in build:
        fail("BuildTargetSnapshot must FindActors (sole producer)")
    if "ScanAlive" not in build or "ScanDead" not in build:
        fail("BuildTargetSnapshot must fill ScanAlive / ScanDead")
    if "Utility.Wait" in build or "SyncDecayForKnifeCorpse" in build:
        fail("BuildTargetSnapshot must not Wait or SyncDecay")
    dispatch = extract_function(text, "DispatchListeners")
    i_voice = dispatch.find("HandleWhisperVoice")
    i_knife = dispatch.find('CallFunctionNoWait("HandleKillerScanKnifeAimWarm"')
    i_cadence = dispatch.find('CallFunctionNoWait("OnKillerScanCadence"')
    if i_voice < 0:
        fail("DispatchListeners must call VoiceAlias.HandleWhisperVoice")
    if i_knife < 0:
        fail("DispatchListeners must CallFunctionNoWait HandleKillerScanKnifeAimWarm")
    if i_cadence < 0:
        fail("DispatchListeners must CallFunctionNoWait OnKillerScanCadence")
    # Ambient decay moved to TargetScan / RegisterTarget → HandleCorpseDecay.
    if "SyncOverlaysFromKillerScanSnapshot" in dispatch or "CheckPendingAimedDecayApply" in dispatch:
        fail("DispatchListeners must not CallFunctionNoWait CorpseDecay sync/pending (HandleCorpseDecay owns ambient)")
    if "NoteFromKillerScanSnapshot" not in dispatch:
        fail("DispatchListeners must CallFunctionNoWait NoteFromKillerScanSnapshot")
    if "OnKillerScanDeadlines" in dispatch or "MaybeWarmBedGiftBody" in dispatch:
        fail("DispatchListeners must not touch BedGift (self-contained sleep/timers)")
    if "SyncFromKillerScanSnapshot" in dispatch:
        fail("DispatchListeners must not SyncFromKillerScanSnapshot — Slice I rename is aim-driven")
    if not (i_voice < i_knife):
        fail("voice HandleWhisperVoice must run BEFORE knife NoWait")
    on_timer = extract_function(text, "OnTimer")
    i_arm = on_timer.find("StartKillerScanLoop()")
    i_run = on_timer.find("RunKillerScanTick()")
    if i_arm < 0 or i_run < 0 or i_arm > i_run:
        fail("KillerScan OnTimer must re-arm BEFORE RunKillerScanTick")
    if "TickBusy" not in on_timer:
        fail("KillerScan OnTimer must gate RunKillerScanTick with TickBusy")
    if "BusySkipCount" not in on_timer:
        fail("KillerScan OnTimer must count busy skips")
    if "BUSY_MAX_SKIPS" not in on_timer:
        fail("KillerScan OnTimer must use BUSY_MAX_SKIPS for busy-skip cap")
    if not re.search(r"BusySkipCount\s*<=\s*BUSY_MAX_SKIPS", on_timer):
        fail("OnTimer must skip while BusySkipCount <= BUSY_MAX_SKIPS")
    if "Utility.Wait" in on_timer:
        fail("KillerScan OnTimer must not Utility.Wait (latent overlap)")
    # Busy must not block re-arm: StartKillerScanLoop before any TickBusy Return.
    i_busy_return = on_timer.find("tick busy")
    if i_busy_return >= 0 and i_arm > i_busy_return:
        fail("StartKillerScanLoop must run before busy-skip Return")
    if "BUSY_MAX_SKIPS = 2" not in text and "BUSY_MAX_SKIPS=2" not in text:
        fail("BUSY_MAX_SKIPS must be 2 (two skips, then force-run)")
    if "BUSY_SKIP_FORCE_AFTER" in text:
        fail("BUSY_SKIP_FORCE_AFTER renamed to BUSY_MAX_SKIPS")
    if "v1.3.0 Killer Orchestrator" not in text:
        fail("KillerScan must Trace v1.3.0 Killer Orchestrator banner")
    ok("KillerScan producer + dispatch + re-arm + busy gate + banner")


def test_starttimer_inventory() -> None:
    starts = []
    for p in USER.glob("*.psc"):
        text = p.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if "StartTimer(" in line and not line.strip().startswith(";"):
                starts.append(f"{p.name}:{i}:{line.strip()}")
    killer = [s for s in starts if "PickmansWhisperKillerScanScript.psc" in s]
    bed = [s for s in starts if "PickmansWhisperBedGiftScript.psc" in s]
    reward = [s for s in starts if "PickmansWhisperKillRewardScript.psc" in s]
    target_scan = [s for s in starts if "PickmansWhisperTargetScanScript.psc" in s]
    other = [
        s
        for s in starts
        if s not in killer
        and s not in bed
        and s not in reward
        and s not in target_scan
    ]
    # TargetScan / retired KillReward may still have StartTimer in source; ignore in "other".
    # KillerScan loop may be parked (StartTimer commented) while KillScanLoop source
    # remains for a possible port — do not require an active StartTimer.
    if killer and any("TIMER_KILLER_SCAN" not in s for s in killer):
        fail(f"KillerScan StartTimer must only use TIMER_KILLER_SCAN, got {killer}")
    bed_overlays = [s for s in bed if "TIMER_BED_OVERLAYS" in s]
    bed_pose = [s for s in bed if "TIMER_BED_POSE" in s]
    bed_despawn = [s for s in bed if "TIMER_BED_DESPAWN" in s]
    if len(bed_overlays) != 1:
        fail(f"expected exactly 1 BedGift StartTimer(TIMER_BED_OVERLAYS) oneshot, got {bed_overlays}")
    if len(bed_pose) < 1:
        fail(f"expected BedGift StartTimer(TIMER_BED_POSE) re-arming poll, got {bed_pose}")
    if len(bed_despawn) < 1:
        fail(f"expected BedGift StartTimer(TIMER_BED_DESPAWN), got {bed_despawn}")
    if len(bed_overlays) + len(bed_pose) + len(bed_despawn) != len(bed):
        fail(
            f"unexpected BedGift StartTimer beyond overlays/pose/despawn, got {bed}"
        )
    if other:
        fail(f"no other feature StartTimer allowed, got {other}")
    ok(
        f"StartTimer inventory: KillerScan parked-or-TIMER_KILLER_SCAN ({len(killer)}); "
        "BedGift overlays/pose/despawn"
    )


def test_main_arming_and_cadence() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    arm = extract_function(main, "ArmRuntimeLoops")
    if "StartKillerScanLoop()" not in arm:
        fail("ArmRuntimeLoops must StartKillerScanLoop")
    if "StartTimer(" in arm:
        fail("ArmRuntimeLoops must not StartTimer")
    if "StartHungerPoll" in arm or "StartBondPoll" in arm:
        fail("ArmRuntimeLoops must not StartHunger/Bond poll timers")
    if "OnKillerScanCadence" not in main:
        fail("Main must OnKillerScanCadence")
    cadence = extract_function(main, "OnKillerScanCadence")
    for needle in ("RunBondPoll", "RunHungerTick", "MaybeSpeakTrustLine", "MaybeSpeakNoticeLine()"):
        if needle not in cadence:
            fail(f"OnKillerScanCadence must call {needle}")
    boot = extract_function(main, "ScheduleBootArm")
    if "StartTimer(" in boot:
        fail("ScheduleBootArm must use deadline not StartTimer")
    if "BootArmDeadlineReal" not in boot:
        fail("ScheduleBootArm must set BootArmDeadlineReal")
    if 'MOD_VERSION = "1.3.0"' not in main:
        fail("Main must declare MOD_VERSION 1.3.0")
    if "=== v1.3.0 Killer Orchestrator loaded ===" not in main:
        fail("Main OnQuestInit must Trace Killer Orchestrator banner")
    knife = extract_function(main, "HandleKillerScanKnifeAimWarm")
    if "ProcessKnifeCreditFromKillerScan" not in knife:
        fail("HandleKillerScanKnifeAimWarm must ProcessKnifeCreditFromKillerScan")
    if "LookFixation" in knife or "MaybeSpeakNoticeLine" in knife:
        fail("HandleKillerScanKnifeAimWarm must not own voice")
    ok("Main arming cadence + version banner")


def test_listeners() -> None:
    voice = VOICE.read_text(encoding="utf-8", errors="replace")
    handle = extract_function(voice, "HandleWhisperVoice")
    if "FindActors" in handle:
        fail("HandleWhisperVoice must not FindActors (KillerScan owns TargetSnapshot)")
    if "MaybeSpeakNoticeLine(akTarget)" not in handle:
        fail("HandleWhisperVoice must MaybeSpeakNoticeLine(akTarget)")
    if "voice-prebond" in handle or "VoiceTick" in handle:
        fail("HandleWhisperVoice must not keep prebond / VoiceTick throttle")
    tick = extract_function(voice, "LookFixation")
    if "FindActors" in tick:
        fail("LookFixation must not FindActors")
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    if "Function SyncOverlaysFromKillerScanSnapshot" in decay:
        fail("SyncOverlaysFromKillerScanSnapshot retired — HandleCorpseDecay owns ambient")
    if "FindActors" in extract_function(decay, "HandleCorpseDecay"):
        fail("HandleCorpseDecay must not FindActors")
    victims = VICTIMS.read_text(encoding="utf-8", errors="replace")
    if "StartTimer(" in victims:
        fail("VictimsScript must not StartTimer (decay nudge parked)")
    bed = BED.read_text(encoding="utf-8", errors="replace")
    if "OnKillerScanDeadlines" in bed or "MaybeWarmBedGiftBody" in bed:
        fail("BedGift must not use KillerScan warm/deadlines")
    if "TIMER_BED_OVERLAYS" not in bed or "KickBedOverlayOnesHot" not in bed:
        fail("BedGift must TIMER_BED_OVERLAYS + KickBedOverlayOnesHot")
    if "TIMER_BED_DESPAWN" not in bed or "ArmBedDespawnTimer" not in bed:
        fail("BedGift must TIMER_BED_DESPAWN + ArmBedDespawnTimer")
    on_timer = extract_function(bed, "OnTimer")
    if "MaybeApplyBedGiftDecayOverlays" not in on_timer:
        fail("BedGift OnTimer must MaybeApplyBedGiftDecayOverlays")
    if "OnBedDespawnTimer" not in on_timer:
        fail("BedGift OnTimer must dispatch OnBedDespawnTimer")
    if "StartTimer(" in on_timer:
        fail("BedGift OnTimer must not StartTimer inline (dispatch only)")
    kick = extract_function(bed, "KickBedOverlayOnesHot")
    if "StartTimer(" not in kick or "TIMER_BED_OVERLAYS" not in kick:
        fail("KickBedOverlayOnesHot must StartTimer(TIMER_BED_OVERLAYS)")
    if "CancelTimer(TIMER_BED_OVERLAYS)" not in kick:
        fail("KickBedOverlayOnesHot must CancelTimer before StartTimer (replace, no stack)")
    if "ForceApplyMcmDecayStage" in decay or "TIMER_MCM_FORCE_APPLY" in decay:
        fail("CorpseDecay must not keep retired MCM ForceApply path")
    if "StartTimer(" in decay:
        fail("CorpseDecay must not StartTimer")
    ok("listeners consume snapshot; BedGift oneshot overlay timer allowed")


def test_version_packaging() -> None:
    info = FOMOD.read_text(encoding="utf-8", errors="replace")
    if "<Version>1.3.0</Version>" not in info:
        fail("fomod/info.xml must be Version 1.3.0")
    mcm = MCM.read_text(encoding="utf-8", errors="replace")
    if "Version 1.3.0" not in mcm:
        fail("MCM config.json must show Version 1.3.0")
    if "Killer Orchestrator" not in mcm:
        fail("MCM How To Use must mention Killer Orchestrator")
    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "test_killer_scan_bus.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_killer_scan_bus.py")
    if "PickmansWhisperKillerScanScript" not in deploy:
        fail("deploy must compile KillerScan")
    ok("version 1.3.0 packaging + deploy gate")


def main() -> int:
    test_no_worldscan_leftovers()
    test_killer_scan_producer()
    test_starttimer_inventory()
    test_main_arming_and_cadence()
    test_listeners()
    test_version_packaging()
    print("All Killer Orchestrator / KillerScan contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
