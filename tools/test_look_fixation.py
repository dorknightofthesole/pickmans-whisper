#!/usr/bin/env python3
"""Regression contracts for C5 look-fixation (P1 table + P2 voice hooks).

Locks:
  - TickLookFixation runs BEFORE MaybeSpeakNoticeLine on killscan (look-edge first)
  - Fixation uses IsFixationEligible (ignores hunger NPC cooldown)
  - Aim via GoE GetCameraTargetReference / GetLastActivateTargetRef (NOT fake
    Game.GetCurrentCrosshairRef — that is not a FO4 native and silenced killscan)
  - Killscan OnTimer re-arms StartKillScanLoop BEFORE RunKillScanTick
  - FormID shortlist cap FIXATION_MAX = 32 with lowest-count eviction
  - MCM sFixation:Debug; count in LastFixationStatus (no "PW fixation:" debug toast)
  - Ambient MaybeSpeakNoticeLine is not rewritten to own fixation
  - P2 voice detail: tools/test_recognition_lines.py

Usage:
  python tools/test_look_fixation.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
MCM_SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


# --- Pure mirrors of Papyrus fixation table ops ---------------------------------


def increment_fixation(
    ids: list[int], counts: list[int], form_id: int, max_slots: int = 32
) -> tuple[list[int], list[int], int]:
    """Mirror IncrementFixation + EvictLowestFixation. Returns (ids, counts, new_count)."""
    for i, fid in enumerate(ids):
        if fid == form_id:
            counts[i] += 1
            return ids, counts, counts[i]
    if len(ids) >= max_slots:
        best = 0
        for i in range(1, len(ids)):
            if counts[i] < counts[best]:
                best = i
        ids.pop(best)
        counts.pop(best)
    ids.append(form_id)
    counts.append(1)
    return ids, counts, 1


def test_increment_and_evict() -> None:
    ids: list[int] = []
    counts: list[int] = []
    ids, counts, n = increment_fixation(ids, counts, 0x100)
    assert n == 1 and ids == [0x100] and counts == [1]
    ids, counts, n = increment_fixation(ids, counts, 0x100)
    assert n == 2 and counts == [2]
    ids, counts, n = increment_fixation(ids, counts, 0x200)
    assert n == 1 and ids == [0x100, 0x200] and counts == [2, 1]

    # Fill to 32, then insert 33rd — lowest count (0x200 at 1) evicted first among ties by index
    ids = list(range(1, 33))
    counts = [10] * 31 + [1]  # last slot lowest
    ids, counts, n = increment_fixation(ids, counts, 99)
    assert n == 1
    assert 32 not in ids  # evicted FormID 32 (last, count 1)
    assert 99 in ids and len(ids) == 32
    ok("increment_fixation + eviction mirror")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Function|Bool Function|Int Function|String Function|Actor Function)\s+{name}\s*\(",
        text,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    # End at next top-level Function/Event (same indent level is hard; use EndFunction)
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
    return text[start : start + end_m.end()]


def extract_function_event(text: str, name: str) -> str:
    m = re.search(rf"Event\s+{name}\s*\(", text)
    if not m:
        fail(f"missing event {name}")
    start = m.start()
    end_m = re.search(r"\nEndEvent\b", text[start:])
    if not end_m:
        fail(f"no EndEvent for {name}")
    return text[start : start + end_m.end()]


def test_psc_contracts(text: str) -> None:
    if "FIXATION_MAX = 32" not in text and "FIXATION_MAX=32" not in text:
        fail("FIXATION_MAX must be 32")
    ok("FIXATION_MAX = 32")

    for name in (
        "TickLookFixation",
        "IncrementFixation",
        "EvictLowestFixation",
        "EnsureFixationLists",
        "WriteFixationStatusToMcm",
        "IsFixationEligible",
    ):
        if f"Function {name}" not in text and f"Int Function {name}" not in text and f"Bool Function {name}" not in text:
            fail(f"missing {name}")
    ok("fixation helpers present")

    if re.search(r"Game\.GetCurrentCrosshairRef\s*\(\s*\)", text):
        fail(
            "PSC must not call Game.GetCurrentCrosshairRef() "
            "(not a FO4 native; fake stub silenced killscan)"
        )
    ok("no Game.GetCurrentCrosshairRef() call in PSC")

    stub_game = (ROOT / "tools" / "stubs" / "Game.psc").read_text(encoding="utf-8")
    if "Function GetCurrentCrosshairRef" in stub_game:
        fail("tools/stubs/Game.psc must not declare fake GetCurrentCrosshairRef Native")
    ok("stub Game.psc has no fake GetCurrentCrosshairRef")

    if "Function GetLookAimActor" not in text:
        fail("missing GetLookAimActor")
    aim = extract_function(text, "GetLookAimActor")
    if "GardenOfEden3.GetCameraTargetReference()" not in aim:
        fail("GetLookAimActor must use GardenOfEden3.GetCameraTargetReference")
    if "GardenOfEden2.GetLastActivateTargetRef()" not in aim:
        fail("GetLookAimActor must fall back to GardenOfEden2.GetLastActivateTargetRef")
    ok("GetLookAimActor uses real GoE APIs")

    fix_el = extract_function(text, "IsFixationEligible")
    if "ExplainNoticeReject(ak, True)" not in fix_el and "ExplainNoticeReject(ak,True)" not in fix_el:
        fail("IsFixationEligible must call ExplainNoticeReject(ak, True) to ignore hunger cooldown")
    ok("IsFixationEligible ignores cooldown")

    tick = extract_function(text, "TickLookFixation")
    if "GetLookAimActor()" not in tick:
        fail("TickLookFixation must use GetLookAimActor()")
    if "IsFixationEligible" not in tick:
        fail("TickLookFixation must gate with IsFixationEligible (not IsNoticeCandidate)")
    if "IsNoticeCandidate" in tick:
        fail("TickLookFixation must not use IsNoticeCandidate (cooldown suppressed fixation)")
    if "PW fixation:" in tick:
        fail('TickLookFixation must not use retired "PW fixation:" debug toast (P2 voice)')
    if "SpeakFixationStageWhisper" not in tick or "SpeakRecognitionLine" not in tick:
        fail("TickLookFixation must route P2 voice (SpeakFixationStageWhisper / SpeakRecognitionLine)")
    if "MaybeSpeakNoticeLine" in tick:
        fail("TickLookFixation must not call MaybeSpeakNoticeLine (ambient stays separate)")
    if "FIXATION_TOAST_COOLDOWN" in tick:
        fail("TickLookFixation must not use FIXATION_TOAST_COOLDOWN")
    ok("TickLookFixation aim + P2 voice + isolated from ambient")

    # VoiceScan HandleKillerScanVoice: fixation BEFORE hunger (order lock)
    voice = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceScanScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    if "Function HandleKillerScanVoice" not in voice:
        fail("VoiceScan must expose HandleKillerScanVoice (direct KillerScan dispatch)")
    if "TickLookFixation()" not in voice or 'MaybeSpeakNoticeLine("killscan")' not in voice:
        fail("VoiceScan must TickLookFixation + MaybeSpeakNoticeLine(killscan)")
    i_ambient = voice.find('MaybeSpeakNoticeLine("killscan")')
    i_fix = voice.find("TickLookFixation()")
    if i_fix > i_ambient:
        fail("TickLookFixation must run BEFORE ambient MaybeSpeakNoticeLine in VoiceScan")
    if "ProcessKnifeCreditFromKillerScan" in voice:
        fail("VoiceScan must not own knife credit")
    if "RegisterForCustomEvent" in voice:
        fail("VoiceScan must not use CustomEvent (same-quest delivery was silent)")
    ok("VoiceScan order: TickLookFixation then ambient")

    # KillerScan OnTimer must re-arm before RunKillerScanTick (silence guard)
    world = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillerScanScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    on_timer = extract_function_event(world, "OnTimer")
    i_arm = on_timer.find("StartKillerScanLoop()")
    i_run = on_timer.find("RunKillerScanTick()")
    if i_arm < 0 or i_run < 0:
        fail("KillerScan OnTimer must call StartKillerScanLoop and RunKillerScanTick")
    if i_arm > i_run:
        fail("KillerScan OnTimer must StartKillerScanLoop BEFORE RunKillerScanTick (silence guard)")
    ok("KillerScan OnTimer re-arms before tick body")

    notice = extract_function(text, "MaybeSpeakNoticeLine")
    if "TickLookFixation" in notice or "FixationIds" in notice:
        fail("MaybeSpeakNoticeLine must not own fixation state (additive helper only)")
    ok("MaybeSpeakNoticeLine free of fixation ownership")

    if "sFixation:Debug" not in text:
        fail("PSC must write MCM sFixation:Debug")
    ok("MCM sFixation:Debug wired in PSC")


def test_mcm_files() -> None:
    cfg = MCM_CONFIG.read_text(encoding="utf-8")
    if '"id": "sFixation:Debug"' not in cfg:
        fail("config.json missing sFixation:Debug")
    ok("MCM config.json has sFixation:Debug")
    ini = MCM_SETTINGS.read_text(encoding="utf-8")
    if "sFixation=" not in ini:
        fail("settings.ini missing sFixation=")
    ok("MCM settings.ini has sFixation")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_increment_and_evict()
    test_psc_contracts(text)
    test_mcm_files()
    print("All look-fixation (C5) contracts passed.")


if __name__ == "__main__":
    main()
