#!/usr/bin/env python3
"""Contracts for Slice D D0-POC — Debug play EndIt SNDR.

Locks:
  - Sound.psc real Play Native; no path-play fakes
  - DebugPlayTestWhisper + FID_WHISPER_ENDIT + GetFormFromFile + Play
  - MCM Debug button calls DebugPlayTestWhisper
  - EndIt.xwm under Data/Sound/PickmansWhisper/
  - Desperate_Audio.txt row 0 is EndIt.xwm (.xwm keys)
  - Esp builder preserves/emits SNDR 0x01000807

Usage:
  python tools/test_audio_poc.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
SOUND_STUB = ROOT / "tools" / "stubs" / "Sound.psc"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
XWM = ROOT / "Data" / "Sound" / "PickmansWhisper" / "EndIt.xwm"
DESPERATE_AUDIO = ROOT / "Data" / "PickmansWhisper" / "config" / "Desperate_Audio.txt"


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


def test_stub() -> None:
    if not SOUND_STUB.is_file():
        fail(f"missing {SOUND_STUB}")
    stub = SOUND_STUB.read_text(encoding="utf-8")
    if "Scriptname Sound extends Form" not in stub:
        fail("Sound.psc must extend Form")
    if not re.search(r"Int\s+Function\s+Play\s*\(\s*ObjectReference\s+\w+\s*\)\s*Native", stub):
        fail("Sound.Play must be Int Function Play(ObjectReference) Native")
    for banned in ("PlaySoundFile", "PlayFile", "PlayPath", "IsKeyPressed"):
        if banned in stub:
            fail(f"Sound.psc must not invent {banned}")
    ok("Sound.psc real Play Native")


def test_psc(text: str) -> None:
    if "FID_WHISPER_ENDIT" not in text:
        fail("PSC must declare FID_WHISPER_ENDIT")
    if "0x00000807" not in text:
        fail("FID_WHISPER_ENDIT must be 0x00000807")
    fn = extract_function(text, "DebugPlayTestWhisper")
    if "GetFormFromFile(FID_WHISPER_ENDIT" not in fn and "GetFormFromFile(FID_WHISPER_ENDIT," not in fn:
        fail("DebugPlayTestWhisper must GetFormFromFile(FID_WHISPER_ENDIT, ...)")
    if "as Sound" not in fn:
        fail("DebugPlayTestWhisper must cast to Sound")
    if ".Play(" not in fn and "snd.Play(" not in fn:
        fail("DebugPlayTestWhisper must call Sound.Play")
    if "Debug.MessageBox" not in fn:
        fail("DebugPlayTestWhisper must MessageBox diagnostics (instance id / xwm)")
    if "DoesFileExist" not in fn:
        fail("DebugPlayTestWhisper must check loose EndIt.xwm via DoesFileExist")
    if "instanceId=" not in fn and "instanceId" not in fn:
        fail("DebugPlayTestWhisper must report Sound.Play instance id")
    notice = extract_function(text, "MaybeSpeakNoticeLine")
    if "DebugPlayTestWhisper" in notice or "FID_WHISPER_ENDIT" in notice:
        fail("MaybeSpeakNoticeLine must stay free of D0-POC audio ownership")
    ok("DebugPlayTestWhisper wired + MessageBox diagnostics; notice path untouched")


def test_mcm() -> None:
    raw = MCM.read_text(encoding="utf-8")
    if "DebugPlayTestWhisper" not in raw:
        fail("MCM config.json must CallFunction DebugPlayTestWhisper")
    if "Play test whisper" not in raw:
        fail("MCM Debug button label should mention Play test whisper")
    ok("MCM Debug Play test whisper button")


def test_assets() -> None:
    if not XWM.is_file():
        fail(f"missing {XWM}")
    if XWM.stat().st_size < 100:
        fail("EndIt.xwm looks empty")
    ok("EndIt.xwm present")

    lines = [
        ln.strip()
        for ln in DESPERATE_AUDIO.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not lines:
        fail("Desperate_Audio.txt empty")
    if lines[0] != "EndIt.xwm":
        fail(f"Desperate_Audio.txt row 0 must be EndIt.xwm, got {lines[0]!r}")
    if any(ln.endswith(".mp3") for ln in lines):
        fail("Desperate_Audio.txt must use .xwm keys, not .mp3")
    ok("Desperate_Audio.txt row 0 EndIt.xwm")


def test_builder() -> None:
    src = BUILDER.read_text(encoding="utf-8")
    for needle in (
        "collect_sndr_records",
        "FID_WHISPER_BASE",
        "0x01000807",
        "build_whisper_sndr_payload",
        "Desperate_Audio.txt",
        "WhisperSndrIds.txt",
        "NEXT_OID = 0x00000850",
    ):
        if needle not in src:
            fail(f"build_hunger_spell_esp.py missing {needle!r}")
    if 'group(b"SNDR"' not in src and "group(b'SNDR'" not in src:
        fail("builder must emit SNDR group")
    # E5 intimacy maps need headroom past Desperate-only 0x820.
    if "Intimacy_Start_Audio.txt" not in src or "Intimacy_End_Audio.txt" not in src:
        fail("builder must also emit E5 intimacy SNDRs from Intimacy_*_Audio.txt")
    ok("esp builder clones Desperate + E5 intimacy SNDRs")

    deploy_ps1 = (ROOT / "tools" / "build-deploy-local.ps1").read_text(encoding="utf-8")
    if "Sound\\PickmansWhisper" not in deploy_ps1 and "Sound/PickmansWhisper" not in deploy_ps1:
        fail("build-deploy-local.ps1 must deploy Sound\\PickmansWhisper")
    if "EndIt.xwm" not in deploy_ps1:
        fail("build-deploy-local.ps1 must require EndIt.xwm on deploy")
    fomod = (ROOT / "fomod" / "ModuleConfig.xml").read_text(encoding="utf-8")
    if 'source="Sound"' not in fomod:
        fail("fomod/ModuleConfig.xml must install Sound folder")
    ok("deploy/FOMOD ship Sound\\PickmansWhisper\\*.xwm")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_stub()
    test_psc(text)
    test_mcm()
    test_assets()
    test_builder()
    print("All audio D0-POC contracts passed.")


if __name__ == "__main__":
    main()
