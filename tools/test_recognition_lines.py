#!/usr/bin/env python3
"""Regression contracts for C5 P2 recognition lines (look-fixation voice).

Locks:
  - RecognitionLines.txt exists, files-only (no builtin mirror in PSC)
  - LoadRecognitionLines via LoadStageBank; LoadLineBanks calls it
  - Voice by count: 1 silent / 2 SpeakRecognitionLine / 3+ SpeakFixationStageWhisper
  - Retire debug toast "PW fixation:"
  - 3rd+ hunger stage uses ToastNoticeLine (stamps hour gate); 2nd recognition does not
  - GetRecognitionBank(band) stub present for later multi-band
  - No rewrite of MaybeSpeakNoticeLine to own fixation

Usage:
  python tools/test_recognition_lines.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MODCFG = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
CONFIG = ROOT / "Data" / "PickmansWhisper" / "config"
RECOG_FILE = CONFIG / "RecognitionLines.txt"
MOD_CONFIG = CONFIG / "ModConfig.txt"
RENAME_PROMPT_DEFAULT = (
    "What's her name I wonder? ...I should name her. [see MCM menu]"
)

MIN_LINES = 6
MIN_NAMELESS = 3


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def parse_lines(path: Path) -> list[str]:
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


def test_file() -> None:
    if not RECOG_FILE.is_file():
        fail(f"missing {RECOG_FILE}")
    lines = parse_lines(RECOG_FILE)
    if len(lines) < MIN_LINES:
        fail(f"RecognitionLines.txt needs >= {MIN_LINES} lines, got {len(lines)}")
    nameless = [ln for ln in lines if "{name}" not in ln]
    if len(nameless) < MIN_NAMELESS:
        fail(f"need >= {MIN_NAMELESS} nameless recognition lines, got {len(nameless)}")
    ok(f"RecognitionLines.txt ({len(lines)} lines, {len(nameless)} nameless)")


def test_psc(text: str) -> None:
    for name in (
        "LoadRecognitionLines",
        "GetRecognitionBank",
        "GetRecognitionBankCount",
        "PickRecognitionLine",
        "SpeakFixationStageWhisper",
        "SpeakRecognitionLine",
    ):
        extract_function(text, name)
    ok("P2 recognition helpers present")

    load_banks = extract_function(text, "LoadVoiceBanks")
    if "LoadRecognitionLines()" not in load_banks:
        fail("LoadVoiceBanks must call LoadRecognitionLines()")
    ok("LoadVoiceBanks loads recognition")

    load_recog = extract_function(text, "LoadRecognitionLines")
    if 'LoadStageBank("RecognitionLines.txt"' not in load_recog:
        fail('LoadRecognitionLines must LoadStageBank("RecognitionLines.txt"...)')
    # No hard-coded mirror of recognition lines in PSC
    sample = "There she is again."
    if sample in text:
        fail("PSC must not hard-code RecognitionLines.txt content")
    ok("files-only recognition load")

    tick = extract_function(text, "LookFixation")
    if "PW fixation:" in tick:
        fail('LookFixation must retire "PW fixation:" debug toast')
    if "LOOK_COUNT_FIRST_SILENT" not in tick:
        fail("LookFixation must gate 1st look with LOOK_COUNT_FIRST_SILENT (silent)")
    if "SpeakRecognitionLine" not in tick:
        fail("LookFixation must call SpeakRecognitionLine on 2nd look")
    if "SpeakFixationStageWhisper" not in tick:
        fail("LookFixation must call SpeakFixationStageWhisper on 3rd+")
    if "LOOK_COUNT_SECOND_RECOGNITION" not in text:
        fail("VoiceAlias must name LOOK_COUNT_SECOND_RECOGNITION (recognition look)")
    if "count == LOOK_COUNT_SECOND_RECOGNITION" not in tick and "count==LOOK_COUNT_SECOND_RECOGNITION" not in tick.replace(" ", ""):
        fail("LookFixation must branch on LOOK_COUNT_SECOND_RECOGNITION (recognition)")
    if "MaybePromptNameHer(akTarget, count)" not in tick and "MaybePromptNameHer(akTarget,count)" not in tick.replace(" ", ""):
        fail("LookFixation must MaybePromptNameHer(akTarget, count) from look count")
    i_silent = tick.find("LOOK_COUNT_FIRST_SILENT")
    i_recog = tick.find("SpeakRecognitionLine")
    i_stage = tick.find("SpeakFixationStageWhisper")
    if i_silent < 0 or i_recog < 0 or i_stage < 0 or not (i_silent < i_recog < i_stage):
        fail("LookFixation must silent (1) then SpeakRecognitionLine (2) then SpeakFixationStageWhisper (3+)")
    if "MaybeSpeakNoticeLine" in tick:
        fail("LookFixation must not call MaybeSpeakNoticeLine")
    ok("LookFixation voice by count (1 silent / 2 recognition / 3+ hunger-stage)")

    stage = extract_function(text, "SpeakFixationStageWhisper")
    if "PickNoticeLine" not in stage:
        fail("SpeakFixationStageWhisper must use PickNoticeLine")
    if "ToastNoticeLine" not in stage:
        fail("SpeakFixationStageWhisper must ToastNoticeLine (stamps hour gate)")
    ok("3rd+ look uses hunger-stage bank + ToastNoticeLine")

    recog = extract_function(text, "SpeakRecognitionLine")
    if "PickRecognitionLine" not in recog:
        fail("SpeakRecognitionLine must PickRecognitionLine")
    if "ToastNoticeLine" in recog:
        fail("SpeakRecognitionLine must NOT ToastNoticeLine (no hour-gate stamp)")
    if "LastNoticeToastGameTime" in recog:
        fail("SpeakRecognitionLine must not stamp LastNoticeToastGameTime")
    if "ShowVoiceToast" not in recog:
        fail("SpeakRecognitionLine must ShowVoiceToast (HUD lead-glyph pad)")
    if "IncrementRecognitionToast" in recog:
        fail("SpeakRecognitionLine must not IncrementRecognitionToast (rename uses look count)")
    if "MaybePromptNameHer" in recog:
        fail("SpeakRecognitionLine must not MaybePromptNameHer (LookFixation owns name-her)")
    if "RecognitionLineCount <= 0" not in recog:
        fail("SpeakRecognitionLine must only claim RecognitionLines.txt missing when count <= 0")
    if "pick empty" not in recog:
        fail("SpeakRecognitionLine must distinguish pick-empty from missing file")
    pick = extract_function(text, "PickRecognitionLine")
    if "ApplyNamePlaceholder" not in pick or "Main().ApplyNamePlaceholder" not in pick:
        fail("PickRecognitionLine must Main().ApplyNamePlaceholder inside retry loop")
    load_awake = extract_function(text, "LoadRecognitionLines")
    if not re.search(
        r"RecognitionLineCount\s*=\s*0\s*\n\s*RecognitionLines\s*=\s*new",
        load_awake,
    ):
        fail("LoadRecognitionLines must zero count before new String[64]")
    ok("2nd look recognition toast without hunger hour stamp")

    if 'RECOGNITION_NAME_PROMPT_AT = 3' not in text and "RECOGNITION_NAME_PROMPT_AT=3" not in text:
        fail("RECOGNITION_NAME_PROMPT_AT must be 3")
    if "Function IncrementRecognitionToast" in text:
        fail("IncrementRecognitionToast retired — name-her uses LookCount")
    prompt = extract_function(text, "MaybePromptNameHer")
    if "RenamePromptFemaleNPC" not in prompt:
        fail("MaybePromptNameHer must use RenamePromptFemaleNPC (from ModConfig.txt)")
    if "GetVictimOverrideName" not in prompt:
        fail("MaybePromptNameHer must skip when already named")
    if "ShowVoiceToast" in prompt:
        fail("MaybePromptNameHer must NOT ShowVoiceToast (clobbers recognition); queue timer instead")
    if "PendingRenameAtReal" not in prompt:
        fail("MaybePromptNameHer must set PendingRenameAtReal deadline (LookingAtTarget TickPendingRenameDeadline)")
    if "StartTimer" in prompt:
        fail("MaybePromptNameHer must not StartTimer")
    if "PendingRenamePrompt" not in prompt:
        fail("MaybePromptNameHer must set PendingRenamePrompt")
    if "aiLookCount < RECOGNITION_NAME_PROMPT_AT" not in prompt and "aiLookCount<RECOGNITION_NAME_PROMPT_AT" not in prompt.replace(" ", ""):
        fail("MaybePromptNameHer must gate on aiLookCount >= RECOGNITION_NAME_PROMPT_AT")
    if RENAME_PROMPT_DEFAULT in text:
        fail("PSC must not hard-code renamePromptFemaleNPC text (ModConfig.txt is source of truth)")
    main_text = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    target_scan = (
        ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperTargetScanScript.psc"
    )
    ts_text = target_scan.read_text(encoding="utf-8", errors="replace") if target_scan.is_file() else ""
    if "Function TickPendingRenameDeadline(" in main_text:
        deadline = extract_function(main_text, "TickPendingRenameDeadline")
        if "PendingRenameAtReal" not in deadline or "ShowVoiceToast" not in deadline:
            fail("TickPendingRenameDeadline must fire PendingRenameAtReal → ShowVoiceToast")
        looking = extract_function(main_text, "LookingAtTarget")
        if "TickPendingRenameDeadline()" not in looking:
            fail("LookingAtTarget must TickPendingRenameDeadline (aim path owns name-her fire)")
        if "TickPendingRenameDeadline" in ts_text:
            fail("TargetScan must not CallFunctionNoWait TickPendingRenameDeadline (moved to LookingAtTarget)")
    elif "PendingRenameAtReal" not in main_text:
        fail("PendingRenameAtReal must still exist (rename prompt deadline)")
    load_banks_main = extract_function(main_text, "LoadLineBanks")
    if "ModConfigAlias.LoadModConfig()" not in load_banks_main:
        fail("LoadLineBanks must ModConfigAlias.LoadModConfig (resume/reload refresh)")
    modcfg = MODCFG.read_text(encoding="utf-8", errors="replace")
    load_mod = extract_function(modcfg, "LoadModConfig")
    if "ModConfig.txt" not in load_mod:
        fail("LoadModConfig must read ModConfig.txt")
    if "renamePromptFemaleNPC" not in load_mod:
        fail("LoadModConfig must parse renamePromptFemaleNPC")
    if "Debug.Notification" in load_mod:
        fail("LoadModConfig must not Notification (clobbers voice toasts); Trace only")
    ok("name-her prompt deadline + ModConfig files-only")

    notice = extract_function(text, "MaybeSpeakNoticeLine")
    if "SpeakRecognitionLine" in notice or "SpeakFixationStageWhisper" in notice:
        fail("MaybeSpeakNoticeLine must stay free of fixation voice ownership")
    ok("MaybeSpeakNoticeLine untouched by P2 voice")


def test_mod_config_file() -> None:
    if not MOD_CONFIG.is_file():
        fail(f"missing {MOD_CONFIG}")
    body = MOD_CONFIG.read_text(encoding="utf-8", errors="replace")
    found = ""
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("renamePromptFemaleNPC="):
            found = line.split("=", 1)[1].strip()
            break
    if not found:
        fail("ModConfig.txt missing renamePromptFemaleNPC=")
    if found != RENAME_PROMPT_DEFAULT:
        fail(f"renamePromptFemaleNPC expected default prompt, got {found!r}")
    ok("ModConfig.txt renamePromptFemaleNPC present")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_file()
    test_mod_config_file()
    test_psc(text)
    print("All recognition-lines (C5 P2) contracts passed.")


if __name__ == "__main__":
    main()
