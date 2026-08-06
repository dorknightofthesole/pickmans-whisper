#!/usr/bin/env python3
"""Contracts: voice silent exits must Trace / MCM status (no more guessing).

Locks:
  - NoteVoiceDispatch + sVoiceDispatch:Debug heartbeat from VoiceScan
  - MaybeSpeakNoticeLine skip paths Trace
  - ToastNoticeLine / ShowVoiceToast blade skips Trace
  - DebugVoicePathDump MCM entry
  - Papyrus logging documented for operators (MO2 custom.ini is machine-local)

Usage:
  python tools/test_voice_debug_trace.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
VOICE = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
SETTINGS = ROOT / "Data" / "MCM" / "Settings" / "PickmansWhisper.ini"
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


def test_voice_dispatch_heartbeat() -> None:
    voice = VOICE.read_text(encoding="utf-8", errors="replace")
    note = extract_function(voice, "NoteVoiceDispatch")
    if "sVoiceDispatch:Debug" not in note:
        fail("NoteVoiceDispatch must write sVoiceDispatch:Debug")
    if "Debug.Trace" not in note:
        fail("NoteVoiceDispatch must Trace")
    handle = extract_function(voice, "HandleWhisperVoice")
    if "NoteVoiceDispatch" not in handle:
        fail("HandleWhisperVoice must NoteVoiceDispatch every tick")
    if "ERROR HandleWhisperVoice — Main script missing" not in handle:
        fail("HandleWhisperVoice must Trace when Main() is missing (was silent Return)")
    ok("VoiceAlias dispatch heartbeat")


def test_notice_skip_traces() -> None:
    voice = VOICE.read_text(encoding="utf-8", errors="replace")
    speak = extract_function(voice, "MaybeSpeakNoticeLine")
    for needle in (
        "skip: voice off",
        "skip: no Pickman's Blade",
        "skip: hunger hour cooldown",
        "skip: no eligible target",
        'Debug.Trace("PickmansWhisper: notice skip |',
    ):
        if needle not in speak:
            fail(f"MaybeSpeakNoticeLine must include {needle!r}")
    toast = extract_function(voice, "ToastNoticeLine")
    if "ToastNoticeLine skip" not in toast or "Debug.Trace" not in toast:
        fail("ToastNoticeLine blade/empty skips must Trace")
    show = extract_function(voice, "ShowVoiceToast")
    if "ShowVoiceToast skip" not in show or "Debug.Trace" not in show:
        fail("ShowVoiceToast blade/empty skips must Trace")
    ok("Notice silent exits Trace")


def test_mcm_dump() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    voice = VOICE.read_text(encoding="utf-8", errors="replace")
    if "Function DebugVoicePathDump" not in main or "VoiceAlias.DebugVoicePathDump" not in extract_function(
        main, "DebugVoicePathDump"
    ):
        fail("Main must façade DebugVoicePathDump → VoiceAlias")
    dump = extract_function(voice, "DebugVoicePathDump")
    for needle in (
        "sVoiceDispatch:Debug",
        "LastNoticeStatus",
        "IsVoiceWeaponReady",
        "Papyrus.0.log",
    ):
        if needle not in dump:
            fail(f"DebugVoicePathDump must surface {needle}")
    note = extract_function(voice, "NoteVoiceDispatch")
    if "LastVoiceDispatchStatus" in note or "LastVoiceDispatchStatus" in voice:
        fail("LastVoiceDispatchStatus retired — dispatch lives in MCM sVoiceDispatch only")
    if "VoiceTick" in voice:
        fail("VoiceTick retired with prebond throttle")
    mcm = MCM.read_text(encoding="utf-8", errors="replace")
    if "DebugVoicePathDump" not in mcm:
        fail("MCM config must wire DebugVoicePathDump button")
    if "sVoiceDispatch:Debug" not in mcm:
        fail("MCM config must show sVoiceDispatch:Debug")
    settings = SETTINGS.read_text(encoding="utf-8", errors="replace")
    if "sVoiceDispatch=" not in settings:
        fail("MCM Settings defaults must include sVoiceDispatch")
    ok("MCM Voice Path Dump + dispatch field")


def test_deploy_runs_this() -> None:
    ps1 = DEPLOY.read_text(encoding="utf-8", errors="replace")
    if "test_voice_debug_trace.py" not in ps1:
        fail("build-deploy-local.ps1 must run test_voice_debug_trace.py")
    ok("Deploy gate includes voice debug contract")


def main() -> None:
    test_voice_dispatch_heartbeat()
    test_notice_skip_traces()
    test_mcm_dump()
    test_deploy_runs_this()
    print("All voice-debug-trace contracts passed.")


if __name__ == "__main__":
    main()
