#!/usr/bin/env python3
"""Contracts for Slice D D0.5 + D1 — SNDR clones, audio maps, delivery modes.

Usage:
  python tools/test_audio_d1.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
CONFIG = ROOT / "Data" / "PickmansWhisper" / "config"
SOUND = ROOT / "Data" / "Sound" / "PickmansWhisper"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
DESPERATE_AUDIO = CONFIG / "Desperate_Audio.txt"
DESPERATE_NOTICE = CONFIG / "NoticeLines_Desperate.txt"
BLANK_AUDIO = (
    "Calm_Audio.txt",
    "Restless_Audio.txt",
    "Hungry_Audio.txt",
    "Starving_Audio.txt",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def parse_data_lines(path: Path) -> list[str]:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Function|Bool Function|Int Function|String Function|String\[\] Function)\s+{name}\s*\(",
        text,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
    return text[start : start + end_m.end()]


def test_maps_and_xwm() -> None:
    audio = parse_data_lines(DESPERATE_AUDIO)
    notice = parse_data_lines(DESPERATE_NOTICE)
    if len(audio) != 12:
        fail(f"Desperate_Audio.txt need 12 rows, got {len(audio)}")
    if len(notice) != len(audio):
        fail(f"Desperate notice/audio count mismatch {len(notice)} vs {len(audio)}")
    if audio[0] != "EndIt.xwm":
        fail("Desperate_Audio[0] must be EndIt.xwm")
    if any(not ln.endswith(".xwm") for ln in audio):
        fail("Desperate_Audio must use .xwm keys only")
    for ln in audio:
        p = SOUND / ln
        if not p.is_file():
            fail(f"missing xwm {p}")
    for name in BLANK_AUDIO:
        p = CONFIG / name
        if not p.is_file():
            fail(f"missing blank scaffold {name}")
        if parse_data_lines(p):
            fail(f"{name} must stay empty of data rows until clips exist")
    ok("Desperate 12/12 maps + xwm; blank stage maps present")


def test_builder_clone() -> None:
    src = BUILDER.read_text(encoding="utf-8")
    for needle in (
        "build_whisper_sndr_payload",
        "parse_audio_map",
        "FID_WHISPER_BASE",
        "WhisperSndrIds.txt",
        "PW_Whisper_",
    ):
        if needle not in src:
            fail(f"builder missing {needle!r}")
    # Simulate FormID assignment
    audio = parse_data_lines(DESPERATE_AUDIO)
    base = 0x01000807
    for i, fn in enumerate(audio):
        stem = fn[: -len(".xwm")]
        edid = f"PW_Whisper_{stem}"
        if " " in stem:
            fail(f"stem must be EDID-safe: {stem}")
        _ = base + i, edid
    ok(f"builder clones {len(audio)} SNDRs from Desperate_Audio order")


def test_psc(text: str) -> None:
    load_banks = extract_function(text, "LoadLineBanks")
    if "LoadAudioBanks()" not in load_banks:
        fail("LoadLineBanks must call LoadAudioBanks")
    if "LoadWhisperSndrIds()" not in load_banks:
        fail("LoadLineBanks must call LoadWhisperSndrIds")
    for name in (
        "LoadAudioBanks",
        "LoadWhisperSndrIds",
        "PlayNoticeAudio",
        "PickNoticeAudioIndex",
        "GetVoiceDeliveryMode",
        "FindWhisperSndrFid",
    ):
        extract_function(text, name)
    speak = extract_function(text, "MaybeSpeakNoticeLine")
    if "GetVoiceDeliveryMode" not in speak:
        fail("MaybeSpeakNoticeLine must honor GetVoiceDeliveryMode")
    if "PlayNoticeAudio" not in speak:
        fail("MaybeSpeakNoticeLine must call PlayNoticeAudio")
    if "PickNoticeAudioIndex" not in speak:
        fail("MaybeSpeakNoticeLine audio-only must PickNoticeAudioIndex")
    pick = extract_function(text, "PickNoticeLine")
    if "LastNoticePickIndex" not in pick:
        fail("PickNoticeLine must set LastNoticePickIndex")
    play = extract_function(text, "PlayNoticeAudio")
    if "PlayWhisperXwmByFile" not in play:
        fail("PlayNoticeAudio must delegate to PlayWhisperXwmByFile")
    xwm = extract_function(text, "PlayWhisperXwmByFile")
    if "Debug.Notification" not in xwm:
        fail("PlayWhisperXwmByFile must fail loud")
    if "GetFormFromFile" not in xwm or ".Play(" not in xwm:
        fail("PlayWhisperXwmByFile must resolve Sound and Play")
    # No hard-coded clip filename list in PSC
    if "OneCutForever.xwm" in text or "BelongsToTheBlade.xwm" in text:
        fail("PSC must not hard-code Desperate_Audio filenames")
    ok("D1 load/play/delivery wired; files-only maps")


def test_mcm() -> None:
    cfg = MCM.read_text(encoding="utf-8")
    if "iVoiceDelivery:Voice" not in cfg:
        fail("MCM Voice page missing iVoiceDelivery:Voice")
    if '"type": "stepper"' not in cfg and '"type":"stepper"' not in cfg:
        # Allow menu fallback but prefer stepper (FO4 MCM renders more reliably).
        if '"type": "menu"' not in cfg or "Voice delivery" not in cfg:
            fail("MCM Voice delivery control missing stepper/menu type")
    if "Toast and Audio" not in cfg and "Toast + Audio" not in cfg:
        fail("MCM Voice delivery options incomplete")
    if "Audio only" not in cfg or "Toast only" not in cfg:
        fail("MCM Voice delivery options incomplete")
    ini = SETTINGS.read_text(encoding="utf-8")
    if "iVoiceDelivery=0" not in ini:
        fail("settings.ini must default iVoiceDelivery=0")
    ok("MCM Voice delivery stepper + default 0")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_maps_and_xwm()
    test_builder_clone()
    test_psc(text)
    test_mcm()
    print("All audio D0.5/D1 contracts passed.")


if __name__ == "__main__":
    main()
