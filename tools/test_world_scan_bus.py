#!/usr/bin/env python3
"""Contracts for WorldScan event bus — one scanner, direct listener dispatch.

Locks:
  - PickmansWhisperWorldScanScript: FindActors + snapshot + DispatchListeners
  - Voice FIRST via VoiceScan.HandleWorldScanVoice (sync; not same-quest CustomEvent)
  - Knife/overlays via CallFunctionNoWait (LooksMenu Wait isolation)
  - No second FindActors in overlay path

Usage:
  python tools/test_world_scan_bus.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
WORLD = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperWorldScanScript.psc"
VOICE = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceScanScript.psc"
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"
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
        m = re.search(rf"Event\s+(?:[\w.]+\.)?{name}\s*\(", text)
    if not m:
        fail(f"missing function/event {name}")
    start = m.start()
    end_m = re.search(r"\n(?:EndFunction|EndEvent)\b", text[start:])
    if not end_m:
        fail(f"no End for {name}")
    return text[start : start + end_m.end()]


def test_world_scan_producer() -> None:
    if not WORLD.is_file():
        fail("missing PickmansWhisperWorldScanScript.psc")
    text = WORLD.read_text(encoding="utf-8", errors="replace")
    run = extract_function(text, "RunWorldScanTick")
    if "FindActors" not in run:
        fail("RunWorldScanTick must FindActors (single producer)")
    if "ScanAlive" not in run or "ScanDead" not in run:
        fail("RunWorldScanTick must fill ScanAlive / ScanDead snapshot")
    if "DispatchListeners()" not in run:
        fail("RunWorldScanTick must DispatchListeners after snapshot")
    if "Utility.Wait" in run or "SyncDecayForKnifeCorpse" in run:
        fail("RunWorldScanTick must not Wait or SyncDecay")
    dispatch = extract_function(text, "DispatchListeners")
    i_voice = dispatch.find("HandleWorldScanVoice")
    i_knife = dispatch.find('CallFunctionNoWait("HandleWorldScanKnifeAimWarm"')
    i_overlay = dispatch.find('CallFunctionNoWait("SyncOverlaysFromWorldScanSnapshot"')
    if i_voice < 0:
        fail("DispatchListeners must call VoiceScan.HandleWorldScanVoice")
    if i_knife < 0:
        fail("DispatchListeners must CallFunctionNoWait HandleWorldScanKnifeAimWarm")
    if i_overlay < 0:
        fail("DispatchListeners must CallFunctionNoWait SyncOverlaysFromWorldScanSnapshot")
    if not (i_voice < i_knife):
        fail("voice HandleWorldScanVoice must run BEFORE knife NoWait")
    on_timer = extract_function(text, "OnTimer")
    i_arm = on_timer.find("StartWorldScanLoop()")
    i_run = on_timer.find("RunWorldScanTick()")
    if i_arm < 0 or i_run < 0 or i_arm > i_run:
        fail("WorldScan OnTimer must re-arm BEFORE RunWorldScanTick")
    ok("WorldScan producer + direct dispatch + re-arm guard")


def test_main_listeners() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    if "StartWorldScanLoop()" not in extract_function(main, "ArmRuntimeLoops"):
        fail("ArmRuntimeLoops must StartWorldScanLoop")
    if "StartDecaySyncLoop" in main:
        fail("retire StartDecaySyncLoop")
    if "Function RunKillScanTick(" in main:
        fail("retire RunKillScanTick kitchen sink")
    if "Event PickmansWhisperWorldScanScript.OnWorldScan" in main:
        fail("Main must not CustomEvent-listen OnWorldScan (direct/NoWait dispatch)")
    knife = extract_function(main, "HandleWorldScanKnifeAimWarm")
    if "ProcessKnifeCreditFromWorldScan" not in knife:
        fail("HandleWorldScanKnifeAimWarm must ProcessKnifeCreditFromWorldScan")
    if "OnWorldScanVictimsAim" not in knife:
        fail("HandleWorldScanKnifeAimWarm must OnWorldScanVictimsAim")
    if "TickLookFixation" in knife or "MaybeSpeakNoticeLine" in knife:
        fail("HandleWorldScanKnifeAimWarm must not own voice")
    credit = extract_function(main, "ProcessKnifeCreditFromWorldScan")
    if "FindActors" in credit:
        fail("ProcessKnifeCreditFromWorldScan must not FindActors")
    if not VOICE.is_file():
        fail("missing PickmansWhisperVoiceScanScript.psc")
    voice = VOICE.read_text(encoding="utf-8", errors="replace")
    if "RegisterForCustomEvent" in voice:
        fail("VoiceScan must not RegisterForCustomEvent (same-quest CustomEvent was silent)")
    handle = extract_function(voice, "HandleWorldScanVoice")
    if "TickLookFixation()" not in handle:
        fail("HandleWorldScanVoice must TickLookFixation")
    if 'MaybeSpeakNoticeLine("killscan")' not in handle:
        fail("HandleWorldScanVoice must MaybeSpeakNoticeLine(killscan)")
    if "ProcessKnifeCreditFromWorldScan" in handle:
        fail("VoiceScan must not own knife credit")
    if "Utility.Wait" in handle or "SyncDecayForKnifeCorpse" in handle:
        fail("VoiceScan must not Wait or SyncDecay")
    ok("Main knife NoWait + VoiceScan direct whisper path")


def test_corpse_decay_nowait() -> None:
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    if "RegisterForCustomEvent" in decay and "OnWorldScan" in decay:
        # allow other events; ban OnWorldScan CustomEvent listener
        if "RegisterForCustomEvent(scan, \"OnWorldScan\")" in decay:
            fail("CorpseDecay must not RegisterForCustomEvent OnWorldScan")
    if "Event PickmansWhisperWorldScanScript.OnWorldScan" in decay:
        fail("CorpseDecay must not CustomEvent-listen OnWorldScan")
    sync = extract_function(decay, "SyncOverlaysFromWorldScanSnapshot")
    if "FindActors" in sync:
        fail("SyncOverlaysFromWorldScanSnapshot must not FindActors")
    if "SyncDecayForKnifeCorpse" not in sync:
        fail("SyncOverlaysFromWorldScanSnapshot must SyncDecayForKnifeCorpse")
    if "DecaySyncBackoffUntil" not in sync:
        fail("SyncOverlaysFromWorldScanSnapshot must honor DecaySyncBackoffUntil")
    ok("CorpseDecay NoWait overlay path")


def test_esp_deploy_docs() -> None:
    esp = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperWorldScanScript" not in esp:
        fail("ESP builder must attach PickmansWhisperWorldScanScript")
    if "PickmansWhisperVoiceScanScript" not in esp:
        fail("ESP builder must attach PickmansWhisperVoiceScanScript")
    ps1 = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    sh = DEPLOY_SH.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperWorldScanScript.psc" not in ps1:
        fail("build-deploy-local.ps1 must compile WorldScan")
    if "PickmansWhisperVoiceScanScript.psc" not in ps1:
        fail("build-deploy-local.ps1 must compile VoiceScan")
    if "PickmansWhisperVoiceScanScript" not in sh:
        fail("build-deploy-local.sh must compile VoiceScan")
    if "test_world_scan_bus.py" not in ps1:
        fail("build-deploy-local.ps1 must run test_world_scan_bus.py")
    slice_h = SLICE_H.read_text(encoding="utf-8", errors="replace")
    if "WorldScan" not in slice_h:
        fail("SLICE_H must document WorldScan bus")
    roadmap = ROADMAP.read_text(encoding="utf-8", errors="replace")
    if "WorldScan" not in roadmap:
        fail("ROADMAP must mention WorldScan bus")
    ok("ESP + deploy + docs WorldScan")


def main() -> None:
    test_world_scan_producer()
    test_main_listeners()
    test_corpse_decay_nowait()
    test_esp_deploy_docs()
    print("All world-scan bus contracts passed.")


if __name__ == "__main__":
    main()
