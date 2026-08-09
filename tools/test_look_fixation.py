#!/usr/bin/env python3
"""Regression contracts for C5 look-fixation (P1 table + P2 voice hooks).

Locks:
  - LookFixation runs BEFORE MaybeSpeakNoticeLine on killscan (look-edge first)
  - Fixation uses ExplainNoticeReject(..., True) / IsFixationEligible (ignores hunger cooldown)
  - FO4 structs: `new FixationEntry` required (bare locals → None struct errors → forever first look)
  - Table helpers: GetFixationEntry / GetOrCreateFixationEntry / UpdateFixationEntry /
    IncrementFixation(index, actorId) — create starts LookCount=0; increment bumps by index
  - Look-aim SSOT: TargetScan.GetLookingAt (GoE GetCameraTargetReference; NOT fake
    Game.GetCurrentCrosshairRef — that is not a FO4 native and silenced killscan)
  - Killscan OnTimer re-arms StartKillScanLoop BEFORE RunKillScanTick
  - FixationEntry[] table cap FIXATION_MAX = 32 with lowest-count eviction
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
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
MCM_SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


# --- Pure mirrors of Papyrus fixation table ops ---------------------------------


def get_or_create_fixation(
    ids: list[int], counts: list[int], form_id: int, max_slots: int = 32
) -> tuple[list[int], list[int], int]:
    """Mirror GetOrCreateFixationEntry (+ EvictLowest). Returns (ids, counts, index|-1).

    New rows start LookCount=0 (IncrementFixation is the sole bump).
    """
    for i, fid in enumerate(ids):
        if fid == form_id:
            return ids, counts, i
    if len(ids) >= max_slots:
        best = 0
        for i in range(1, len(ids)):
            if counts[i] < counts[best]:
                best = i
        ids.pop(best)
        counts.pop(best)
    if len(ids) >= max_slots:
        return ids, counts, -1
    ids.append(form_id)
    counts.append(0)
    return ids, counts, len(ids) - 1


def increment_fixation_at(
    ids: list[int], counts: list[int], index: int, actor_id: int
) -> int | None:
    """Mirror IncrementFixation(fixEntryId, actorId). New LookCount or None on error."""
    if index < 0 or index >= len(ids):
        return None
    if ids[index] != actor_id:
        return None
    counts[index] += 1
    return counts[index]


def test_table_helper_mirrors() -> None:
    ids: list[int] = []
    counts: list[int] = []

    ids, counts, idx = get_or_create_fixation(ids, counts, 0x100)
    assert idx == 0 and ids == [0x100] and counts == [0]
    n = increment_fixation_at(ids, counts, idx, 0x100)
    assert n == 1 and counts == [1]
    n = increment_fixation_at(ids, counts, idx, 0x100)
    assert n == 2 and counts == [2]
    assert increment_fixation_at(ids, counts, idx, 0x999) is None  # actorId mismatch
    assert increment_fixation_at(ids, counts, 5, 0x100) is None  # bad index

    ids, counts, idx2 = get_or_create_fixation(ids, counts, 0x200)
    assert idx2 == 1 and counts == [2, 0]
    assert increment_fixation_at(ids, counts, idx2, 0x200) == 1

    # Same actor → same index, no new row
    ids, counts, idx_again = get_or_create_fixation(ids, counts, 0x100)
    assert idx_again == 0 and len(ids) == 2

    # Fill to 32, insert 33rd — lowest count evicted (FormID 32 at count 1)
    ids = list(range(1, 33))
    counts = [10] * 31 + [1]
    ids, counts, idx = get_or_create_fixation(ids, counts, 99)
    assert idx >= 0 and 32 not in ids and 99 in ids and len(ids) == 32
    assert counts[ids.index(99)] == 0
    ok("get_or_create + increment_at + eviction mirrors")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:FixationEntry Function|Bool Function|Int Function|String Function|"
        rf"Actor Function|Function)\s+{re.escape(name)}\s*\(",
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


def test_fixation_entry_table_helpers(text: str) -> None:
    """PSC contracts for GetFixationEntry / GetOrCreate / Update / IncrementFixation."""
    get = extract_function(text, "GetFixationEntry")
    if "FixationEntry Function GetFixationEntry" not in text:
        fail("GetFixationEntry must return FixationEntry")
    if "e.ActorId == actorId" not in get:
        fail("GetFixationEntry must match Fixations[i].ActorId == actorId")
    if "Return None" not in get:
        fail("GetFixationEntry must Return None when actor is not in the table")
    if not re.search(r"If\s+actorId\s*==\s*0\s*\n\s*Return\s+None", get):
        fail("GetFixationEntry must early-out actorId==0 with Return None")
    ok("GetFixationEntry: lookup by ActorId + None miss")

    create = extract_function(text, "GetOrCreateFixationEntry")
    if "Int Function GetOrCreateFixationEntry" not in text:
        fail("GetOrCreateFixationEntry must return Int (table index)")
    if "new FixationEntry" not in create:
        fail("GetOrCreateFixationEntry must `new FixationEntry` (FO4 None-struct rule)")
    if "entry.LookCount = 0" not in create:
        fail("GetOrCreateFixationEntry must create with LookCount=0 (IncrementFixation bumps)")
    if "entry.lastFixation = 0.0" not in create and "entry.lastFixation = 0" not in create:
        fail("GetOrCreateFixationEntry must init lastFixation")
    if "EvictLowestFixation" not in create:
        fail("GetOrCreateFixationEntry must EvictLowestFixation when table full")
    if "Return -1" not in create:
        fail("GetOrCreateFixationEntry must Return -1 when still full after eviction")
    if "Return i" not in create:
        fail("GetOrCreateFixationEntry must Return i when actor already in table")
    if "Return CurFixationSlotCount" not in create and "return CurFixationSlotCount" not in create:
        fail("GetOrCreateFixationEntry must Return new slot index after append")
    # actorId==0 returns 0 — same ambiguous sentinel as index 0; lock current behavior.
    if not re.search(r"If\s+actorId\s*==\s*0\s*\n\s*Return\s+0", create):
        fail("GetOrCreateFixationEntry must Return 0 when actorId==0 (current contract)")
    ok("GetOrCreateFixationEntry: index / create LookCount=0 / full=-1")

    upd = extract_function(text, "UpdateFixationEntry")
    if "Bool Function UpdateFixationEntry" not in text:
        fail("UpdateFixationEntry must return Bool")
    if "Fixations[i] = NewFixationEntry" not in upd:
        fail("UpdateFixationEntry must write NewFixationEntry into the matching slot")
    if "Return True" not in upd:
        fail("UpdateFixationEntry must Return True on hit")
    if "Return False" not in upd:
        fail("UpdateFixationEntry must Return False when actor not found")
    if "e.ActorId == actorId" not in upd:
        fail("UpdateFixationEntry must match by ActorId")
    ok("UpdateFixationEntry: replace row by ActorId")

    inc = extract_function(text, "IncrementFixation")
    if "FixationEntry Function IncrementFixation" not in text:
        fail("IncrementFixation must return FixationEntry (None on mismatch)")
    if not re.search(
        r"IncrementFixation\s*\(\s*Int\s+fixEntryId\s*,\s*Int\s+actorId\s*\)",
        text,
    ):
        fail("IncrementFixation must take (Int fixEntryId, Int actorId)")
    if "e.ActorId != actorId" not in inc:
        fail("IncrementFixation must sanity-check actorId against the row")
    if "Return None" not in inc:
        fail("IncrementFixation must Return None on bad index / mismatch")
    if "ERROR IncrementFixation" not in inc:
        fail("IncrementFixation must Debug.Trace ERROR on failure paths")
    if "e.LookCount = e.LookCount + 1" not in inc:
        fail("IncrementFixation must bump LookCount on the indexed row")
    if "Fixations[fixEntryId] = e" not in inc:
        fail("IncrementFixation must write the bumped entry back to Fixations[fixEntryId]")
    if "EvictLowestFixation" in inc or "new FixationEntry" in inc:
        fail("IncrementFixation must not create/evict — GetOrCreateFixationEntry owns that")
    ok("IncrementFixation: index + actorId check, returns entry or None")

    skip = extract_function(text, "SkipFixation")
    if "Bool Function SkipFixation" not in text:
        fail("SkipFixation must return Bool")
    if not re.search(
        r"SkipFixation\s*\(\s*Int\s+fixEntryId\s*,\s*Int\s+actorId\s*\)",
        text,
    ):
        fail("SkipFixation must take (Int fixEntryId, Int actorId) like IncrementFixation")
    if "e.ActorId != actorId" not in skip:
        fail("SkipFixation must sanity-check actorId against the row")
    if "ERROR SkipFixation" not in skip:
        fail("SkipFixation must Debug.Trace ERROR on bad index / mismatch")
    if "GetCurrentRealTime" not in skip:
        fail("SkipFixation must use Utility.GetCurrentRealTime")
    if "e.lastFixation" not in skip:
        fail("SkipFixation must read/write FixationEntry.lastFixation")
    if "FIXATION_TOAST_GAP" not in skip:
        fail("SkipFixation must honor FIXATION_TOAST_GAP")
    if "Fixations[fixEntryId] = e" not in skip:
        fail("SkipFixation must write the stamped entry back to Fixations[fixEntryId]")
    if "Return True" not in skip or "Return False" not in skip:
        fail("SkipFixation must Return True after gap / False while cooling or on error")
    look = extract_function(text, "LookFixation")
    if "SkipFixation(fixEntryId, actorId)" not in look.replace(" ", ""):
        # allow normal spacing
        if not re.search(
            r"SkipFixation\s*\(\s*fixEntryId\s*,\s*actorId\s*\)",
            look,
        ):
            fail("LookFixation must call SkipFixation(fixEntryId, actorId)")
    ok("SkipFixation: per-NPC lastFixation gap 20s (wired in LookFixation)")


def test_psc_contracts(text: str) -> None:
    if "FIXATION_MAX = 32" not in text and "FIXATION_MAX=32" not in text:
        fail("FIXATION_MAX must be 32")
    ok("FIXATION_MAX = 32")
    if "Struct FixationEntry" not in text:
        fail("VoiceAlias must define Struct FixationEntry")
    if "FixationEntry[] Fixations" not in text:
        fail("VoiceAlias must use single FixationEntry[] Fixations table")
    if "Int[] FixationIds" in text or "Int[] FixationCounts" in text or "Int[] RecognitionToastCounts" in text:
        fail("parallel FixationIds/Counts/RecognitionToastCounts arrays retired — use Fixations")
    if "Float lastFixation" not in text:
        fail("FixationEntry must include Float lastFixation (per-NPC toast time)")
    ensure = extract_function(text, "EnsureFixationLists")
    if "new FixationEntry[32]" not in ensure:
        fail("EnsureFixationLists must allocate new FixationEntry[32]")
    if "Fixations[i] = new FixationEntry" not in ensure:
        fail(
            "EnsureFixationLists must new FixationEntry into each slot "
            "(FO4 struct arrays are None until new — bare FixationEntry locals throw)"
        )
    ok("FixationEntry[] SSOT table")

    test_fixation_entry_table_helpers(text)

    # Hold-aim poll throttle (SameAimPollCount / LOOK_SAME_AIM_POLLS) retired.
    if "SameAimPollCount" in text or "LOOK_SAME_AIM_POLLS" in text:
        fail("SameAimPollCount / LOOK_SAME_AIM_POLLS must stay retired (SkipFixation gap is spacing)")
    for name in (
        "LookFixation",
        "GetFixationEntry",
        "GetOrCreateFixationEntry",
        "UpdateFixationEntry",
        "IncrementFixation",
        "SkipFixation",
        "RemoveFixation",
        "EvictLowestFixation",
        "EnsureFixationLists",
        "WriteFixationStatusToMcm",
        "IsFixationEligible",
    ):
        if (
            f"Function {name}" not in text
            and f"Int Function {name}" not in text
            and f"Bool Function {name}" not in text
            and f"FixationEntry Function {name}" not in text
        ):
            fail(f"missing {name}")
    if "Function RemoveFixation(Actor ak)" not in text:
        fail("RemoveFixation must take Actor ak")
    remove = extract_function(text, "RemoveFixation")
    if "RemoveFixationByActorId" not in remove:
        fail("RemoveFixation must RemoveFixationByActorId(GetFormID)")
    by_id = extract_function(text, "RemoveFixationByActorId")
    if "FixationSlotCount -= 1" not in by_id:
        fail("RemoveFixationByActorId must drop a table slot")
    evict = extract_function(text, "EvictLowestFixation")
    if "RemoveFixation(ak)" not in evict:
        fail("EvictLowestFixation must call RemoveFixation when Actor resolves")
    if "FixationSlotCount -= 1" in evict:
        fail("EvictLowestFixation must not splice itself — RemoveFixation* owns cleanup")
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

    if "Function GetLookAimActor" in text or "GetLookAimActor()" in text:
        fail("VoiceAlias must not own GetLookAimActor — use TargetScan.GetLookingAt")
    target_scan = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperTargetScanScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    aim = extract_function(target_scan, "GetLookingAt")
    if "GardenOfEden3.GetCameraTargetReference()" not in aim:
        fail("GetLookingAt must use GardenOfEden3.GetCameraTargetReference")
    ok("look-aim SSOT: TargetScan.GetLookingAt (GoE camera)")
    scan_fn = extract_function(target_scan, "ScanAndCleanTargets")
    if 'CallFunctionNoWait("LookingAtTarget"' not in scan_fn and "CallFunctionNoWait(\"LookingAtTarget\"" not in scan_fn:
        fail(
            "TargetScan must CallFunctionNoWait LookingAtTarget "
            "(fire-and-forget; do not block scan on LookFixation)"
        )
    main = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    looking = extract_function(main, "LookingAtTarget")
    if "VoiceAlias.LookFixation(WhoIsThat)" not in looking:
        fail("Main.LookingAtTarget must call VoiceAlias.LookFixation")
    if "TickPendingRenameDeadline()" not in looking:
        fail("LookingAtTarget must TickPendingRenameDeadline (not ambient TargetScan cadence)")
    if "DesperateRename()" not in looking or "rename.DesperateRename(WhoIsThat)" not in looking:
        fail("LookingAtTarget must DesperateRename() façade then rename.DesperateRename(WhoIsThat)")
    if "TickPendingRenameDeadline" in scan_fn:
        fail("TargetScan ScanAndCleanTargets must not host TickPendingRenameDeadline")
    ok("TargetScan -> Main.LookingAtTarget -> LookFixation + rename deadline + DesperateRename")

    fix_el = extract_function(text, "IsFixationEligible")
    if "ExplainNoticeReject(ak, True)" not in fix_el and "ExplainNoticeReject(ak,True)" not in fix_el:
        fail("IsFixationEligible must call ExplainNoticeReject(ak, True) to ignore hunger cooldown")
    ok("IsFixationEligible ignores cooldown")

    if "Function LookFixation(Actor akTarget)" not in text:
        fail("LookFixation must take Actor akTarget (aim via TargetScan.GetLookingAt at call site)")
    tick = extract_function(text, "LookFixation")
    if "akTarget" not in tick:
        fail("LookFixation must use akTarget (not resolve aim itself)")
    if "IsFixationEligible" not in tick and "ExplainNoticeReject(akTarget, True)" not in tick:
        fail("LookFixation must gate eligibility (IsFixationEligible or ExplainNoticeReject(..., True))")
    if "GetOrCreateFixationEntry" not in tick:
        fail("LookFixation must GetOrCreateFixationEntry")
    if "IncrementFixation(" not in tick:
        fail("LookFixation must IncrementFixation(index, actorId)")
    if "IsNoticeCandidate" in tick:
        fail("LookFixation must not use IsNoticeCandidate (cooldown suppressed fixation)")
    if "PW fixation:" in tick:
        fail('LookFixation must not use retired "PW fixation:" debug toast (P2 voice)')
    if "SpeakFixationStageWhisper" not in tick or "SpeakRecognitionLine" not in tick:
        fail("LookFixation must route P2 voice (SpeakFixationStageWhisper / SpeakRecognitionLine)")
    stage_wh = extract_function(text, "SpeakFixationStageWhisper")
    if "PlayNoticeAudio" not in stage_wh:
        fail("SpeakFixationStageWhisper must PlayNoticeAudio (Desperate_Audio when stage 4; was toast-only)")
    if "GetVoiceDeliveryMode" not in stage_wh:
        fail("SpeakFixationStageWhisper must honor GetVoiceDeliveryMode")
    skip = extract_function(text, "SkipFixation")
    if "gap >= 0.0" not in skip and "gap >= 0" not in skip:
        fail("SkipFixation must allow when realtime gap is negative (post-load clock reset)")
    if "LOOK_COUNT_FIRST_SILENT" not in tick:
        fail("LookFixation must keep 1st look silent via LOOK_COUNT_FIRST_SILENT")
    if "MaybePromptNameHer" not in tick:
        fail("LookFixation must MaybePromptNameHer from look count (>= RECOGNITION_NAME_PROMPT_AT)")
    if "MaybeSpeakNoticeLine" in tick:
        fail("LookFixation must not call MaybeSpeakNoticeLine (ambient stays separate)")
    if "FIXATION_TOAST_COOLDOWN" in tick:
        fail("LookFixation must not use FIXATION_TOAST_COOLDOWN")
    ok("LookFixation aim + P2 voice + isolated from ambient")

    # VoiceAlias HandleWhisperVoice: ambient speak; fixation is LookFixation(akTarget)
    voice = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    if "Function HandleWhisperVoice" not in voice:
        fail("VoiceAlias must expose HandleWhisperVoice")
    if "MaybeSpeakNoticeLine(akTarget)" not in voice:
        fail("VoiceAlias must MaybeSpeakNoticeLine(akTarget)")
    if "ProcessKnifeCreditFromKillerScan" in voice:
        fail("VoiceScan must not own knife credit")
    if "RegisterForCustomEvent" in voice:
        fail("VoiceScan must not use CustomEvent (same-quest delivery was silent)")
    ok("VoiceAlias ambient speak + no knife ownership")

    notice = extract_function(text, "MaybeSpeakNoticeLine")
    if "LookFixation" in notice or "Fixations" in notice or "FixationEntry" in notice:
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
    test_table_helper_mirrors()
    test_psc_contracts(text)
    test_mcm_files()
    print("All look-fixation (C5) contracts passed.")


if __name__ == "__main__":
    main()
