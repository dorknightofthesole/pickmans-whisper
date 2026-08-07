#!/usr/bin/env python3
"""Regression tests for notice whisper text + PSC contracts (C2 + C3 staging).

Locks:
  - Generic labels (Settler, etc.) must NOT appear in rendered toast text
  - StripNamePlaceholder must never insert the word "them"
  - Named NPCs still get {name} substitution
  - ExplainNoticeReject must not use IsHostileToActor; hard gate via IsValidTarget
  - C3: five hunger-stage files exist and parse; PickNoticeLine selects by stage
    with a no-immediate-repeat guard and prefers nameless lines for unnamed targets
  - Prior fixes stay: toast-before-dialog, PickBestNoticeFromList, Scan probe

Usage:
  python tools/test_notice_lines.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Voice / notice banks live on VoiceAlias (moved off Main).
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
CONFIG = ROOT / "Data" / "PickmansWhisper" / "config"

GENERIC_NAMES = {
    "Settler",
    "Raider",
    "Gunner",
    "Tramp",
    "Scavenger",
    "Farmer",
    "Wastelander",
    "Survivor",
    "Resident",
    "Citizen",
    "Neighbor",
    "Worker",
    "Unnamed",
    "unnamed",
}

# Files-only design: this old hardcoded fallback must NOT exist in the script
# anymore. When a stage file fails to load, callers skip (return "") instead.
RETIRED_FALLBACK = "A soft one nearby. Do you feel it?"

# Ordered stages (index 0..4) mapped to their editable files.
STAGE_FILES = [
    ("calm", "NoticeLines_Calm.txt"),
    ("restless", "NoticeLines_Restless.txt"),
    ("hungry", "NoticeLines_Hungry.txt"),
    ("starving", "NoticeLines_Starving.txt"),
    ("desperate", "NoticeLines_Desperate.txt"),
]

MIN_LINES_PER_STAGE = 6
MIN_NAMELESS_PER_STAGE = 3  # unnamed settlers are the common target


def parse_lines(path: Path) -> list[str]:
    """Mirror LoadStageBank: trim, drop blank + '#' comment lines."""
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def is_usable_whisper_name(npc_name: str) -> bool:
    """Mirror of IsUsableWhisperName — ASCII name glyphs + at least one letter."""
    if not npc_name:
        return False
    s = npc_name.strip()
    if len(s) < 2:
        return False
    # Papyrus StrFind(allowed, c) is case-insensitive for A–Z.
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789 -'.")
    letters = set("abcdefghijklmnopqrstuvwxyz")
    has_letter = False
    for ch in s:
        key = ch.lower() if ch.isalpha() else ch
        if key not in allowed:
            return False
        if key in letters:
            has_letter = True
    return has_letter


def notice_name_for_line(npc_name: str) -> str:
    """Mirror of NoticeNameForLine (Papyrus compare is case-insensitive)."""
    if not npc_name:
        return ""
    if not is_usable_whisper_name(npc_name):
        return ""
    lower = npc_name.casefold()
    for g in GENERIC_NAMES:
        if lower == g.casefold():
            return ""
    if "settler" in lower or "resident" in lower:
        return ""
    return npc_name


def strip_leading_name_separator(s: str) -> str:
    """Mirror StripLeadingNameSeparator."""
    if not s:
        return ""
    if s.startswith(". "):
        return s[2:]
    if s.startswith(" - "):
        return s[3:]
    if s.startswith(" — "):
        return s[3:]
    if s.startswith("— "):
        return s[2:]
    if s == ".":
        return ""
    return s


def strip_name_placeholder(line: str) -> str:
    """Mirror StripNamePlaceholder via ReplaceStr (GoE StrFind is not an index)."""
    if not line or "{name}" not in line:
        return line
    out = line
    for pat in ("{name}. ", "{name} - ", "{name} — ", "{name}— ", "{name}.", "{name}"):
        out = out.replace(pat, "")
    out = strip_leading_name_separator(out.strip())
    if len(out) < 8:
        # Degenerate user line (e.g. just "{name}") -> skip, no fake fallback.
        return ""
    return out


def apply_name_placeholder(line: str, npc_name: str) -> str:
    if not line:
        return ""
    if not npc_name:
        return strip_name_placeholder(line)
    if "{name}" not in line:
        return line
    return line.replace("{name}", npc_name, 1)


def pick_notice_line(stage_lines: list[str], npc_name: str, last: str = "", rng_index: int = 0) -> str:
    """Mirror PickNoticeLine (files-only): returns "" when the stage has no lines."""
    n = len(stage_lines)
    if n == 0:
        return ""  # stage file not loaded -> caller skips the whisper
    use_name = notice_name_for_line(npc_name)
    want_nameless = use_name == ""
    idx = rng_index % n
    raw = stage_lines[idx]
    tries = 0
    while tries < 8 and n > 1 and (raw == last or (want_nameless and "{name}" in raw)):
        idx = (idx + 1) % n
        raw = stage_lines[idx]
        tries += 1
    if not raw:
        return ""
    return apply_name_placeholder(raw, use_name)


def load_all_stages() -> dict[str, list[str]]:
    stages: dict[str, list[str]] = {}
    for name, fname in STAGE_FILES:
        path = CONFIG / fname
        assert path.is_file(), f"missing stage file {path}"
        stages[name] = parse_lines(path)
    return stages


def test_stage_files_parse() -> None:
    stages = load_all_stages()
    for name, lines in stages.items():
        assert len(lines) >= MIN_LINES_PER_STAGE, f"stage {name} has too few lines: {len(lines)}"
        nameless = [ln for ln in lines if "{name}" not in ln]
        assert len(nameless) >= MIN_NAMELESS_PER_STAGE, (
            f"stage {name} needs >= {MIN_NAMELESS_PER_STAGE} nameless lines for generic settlers; "
            f"has {len(nameless)}"
        )


def test_generic_never_in_toast() -> None:
    stages = load_all_stages()
    for name, lines in stages.items():
        for i in range(len(lines)):
            for gname in ("Settler", "settler", "Raider", "Gunner", "Resident", "Citizen"):
                out = pick_notice_line(lines, gname, rng_index=i)
                assert gname.casefold() not in out.casefold(), f"stage {name}: {out!r} contains {gname!r}"
                assert out.casefold() != "them"
                assert len(out) >= 8
    assert notice_name_for_line("Resident") == ""
    assert notice_name_for_line("Sanctuary Resident") == ""


def test_unprintable_name_treated_as_nameless() -> None:
    """Engine glyph junk (toast solid squares) must not enter {name}."""
    junk = (
        "\u25a0\u25a0",  # ■■ solid squares
        "\ufffd\ufffd",  # replacement chars
        "\x01\x02",
        "A",  # too short
        "42",  # digits only
        "  ",
    )
    for bad in junk:
        assert notice_name_for_line(bad) == "", f"expected nameless for {bad!r}"
    # P3-style player labels + vanilla named NPCs must still pass
    for good in ("Piper", "Anne-Marie", "O'Malley", "Dr. Amari", "Lilith"):
        assert notice_name_for_line(good) == good, f"usable name rejected: {good!r}"


def test_named_keeps_name() -> None:
    stages = load_all_stages()
    for name, lines in stages.items():
        named = [ln for ln in lines if "{name}" in ln]
        for i, _ in enumerate(named):
            # Force selection of a {name} line by searching all indices
            for j, ln in enumerate(lines):
                if "{name}" in ln:
                    out = apply_name_placeholder(ln, "Piper")
                    assert "Piper" in out, f"stage {name}: {ln!r} lost the name"
                    assert out != "Piper"
                    break


def test_no_immediate_repeat() -> None:
    stages = load_all_stages()
    for name, lines in stages.items():
        if len(lines) < 2:
            continue
        # If rng lands on the same template as last, it must reroll to a different one.
        last = lines[0]
        # Named target so nameless-preference does not interfere with the check.
        out = pick_notice_line(lines, "Piper", last=last, rng_index=0)
        # The chosen raw template must differ from `last` (rendered may substitute name).
        assert out != apply_name_placeholder(last, "Piper") or lines.count(last) > 1, (
            f"stage {name}: immediate repeat not avoided"
        )


def test_strip_never_inserts_them() -> None:
    samples = [
        "{name}",
        "{name}. There's something calming about her.",
        "Look — {name}.",
        "That one. {name}. Do you see her too?",
        "They don't deserve {name}'s attention. You do.",
    ]
    for s in samples:
        out = strip_name_placeholder(s)
        assert out.casefold() != "them", f"strip produced them from {s!r}"
        assert "them" not in out.casefold() or "them" in s.casefold()


def test_strip_removes_following_separators() -> None:
    """Nameless strip must not leave '. ' / ' - ' / ' — ' that followed {name}."""
    cases = [
        ("Oh — {name}. Back again.", "Oh — Back again."),
        ("{name}. Familiar face.", "Familiar face."),
        ("{name} — you keep finding her.", "you keep finding her."),
        ("{name} - still here somehow.", "still here somehow."),
        ("Look — {name}.", ""),  # leftover too short after strip
        ("That one. {name}. Do you see her too?", "That one. Do you see her too?"),
    ]
    for raw, expect in cases:
        out = strip_name_placeholder(raw)
        assert out == expect, f"strip {raw!r}: got {out!r}, want {expect!r}"
        assert "{name}" not in out and not out.startswith("{"), f"leftover brace junk: {out!r}"
    # Named path must keep separators around the real name
    assert apply_name_placeholder("Oh — {name}. Back again.", "Piper") == (
        "Oh — Piper. Back again."
    )
    # Regression: GoE StrFind is a COUNT — slicing with it produced "{amiliar face."
    assert strip_name_placeholder("{name}. Familiar face.") == "Familiar face."
    assert strip_name_placeholder("{name} — you keep finding her.") == "you keep finding her."


def test_psc_contracts() -> None:
    text = PSC.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    for needle in (
        "Function NoticeNameForLine",
        "Function IsUsableWhisperName",
        "Function GetNoticeStage",
        "Function GetNoticeBankForStage",
        "Function GetNoticeCountForStage",
        "Function LoadStageBank",
        "Function OnNoticeSpoken",
        "Function CommitNearbyPickSummary",
        "Function WriteNearbyStatusToMcm",
        "Function WriteNoticeLoadStatusToMcm",
        "Function NoticeLoadFailureList",
        "GardenOfEden2.GetLinesFromFile",
        "LastNoticeLine",
        "LastStageLoadStatus",
        'npcName == "Settler"',
        'npcName == "Resident"',
        'npcName == "Unnamed"',
        'StrContains(npcName, "Resident")',  # may be Main().StrContains after move
    ):
        if needle == 'StrContains(npcName, "Resident")':
            if 'StrContains(npcName, "Resident")' not in text:
                errors.append(f"missing {needle!r} in VoiceAlias script")
        elif needle not in text:
            errors.append(f"missing {needle!r} in VoiceAlias script")
    main_text = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    if "Function GetVictimOverrideName" not in main_text:
        errors.append("Main must still own GetVictimOverrideName (VoiceAlias reads via Main())")
    if "Function ExplainNonHumanForNotice" not in main_text:
        errors.append("Main must still own ExplainNonHumanForNotice (keyword filters)")

    get_name = re.search(
        r"String Function GetActorDisplayName\(Actor ak\)(.*?)EndFunction",
        text,
        re.S,
    )
    if not get_name or "GetVictimOverrideName" not in get_name.group(1):
        errors.append("GetActorDisplayName must call GetVictimOverrideName (P3 name hook)")
    usable = re.search(
        r"Bool Function IsUsableWhisperName\(String npcName\)(.*?)EndFunction",
        text,
        re.S,
    )
    if not usable:
        errors.append("IsUsableWhisperName missing body")
    elif "StringUtil." in usable.group(1):
        errors.append("IsUsableWhisperName must use GoE only (no StringUtil)")
    elif "abcdefghijklmnopqrstuvwxyz" not in usable.group(1):
        errors.append("IsUsableWhisperName must allowlist printable name glyphs")

    # The retired index-range nameless hack must be gone.
    if "PickNamelessNoticeLine" in text:
        errors.append("PickNamelessNoticeLine should be retired (C3 uses per-stage strip)")

    # Files-only: hardcoded builtin banks + overlay must be GONE.
    for retired in (
        "FillCalmBuiltin",
        "FillRestlessBuiltin",
        "FillHungryBuiltin",
        "FillStarvingBuiltin",
        "FillDesperateBuiltin",
        "OverlayStageBank",
    ):
        if retired in text:
            errors.append(f"{retired!r} must be removed (notice whispers are files-only)")

    # The old hardcoded fallback line must not exist anywhere.
    if RETIRED_FALLBACK in text:
        errors.append(f"retired hardcoded fallback {RETIRED_FALLBACK!r} must be removed (files-only skips instead)")

    # LoadNoticeLines: files-only, records per-stage status, and warns on failure.
    lnl = re.search(r"Function LoadNoticeLines\(\)(.*?)EndFunction", text, re.S)
    if not lnl:
        errors.append("LoadNoticeLines not found")
    else:
        body = lnl.group(1)
        if "FillCalmBuiltin" in body or "OverlayStageBank" in body:
            errors.append("LoadNoticeLines must not use builtins/overlay (files-only)")
        if "LoadStageBank(" not in body:
            errors.append("LoadNoticeLines must read stage files via LoadStageBank")
        if "WriteNoticeLoadStatusToMcm()" not in body:
            errors.append("LoadNoticeLines must push per-stage load status to MCM")
        if "Debug.Notification(" not in body or "NoticeLoadFailureList()" not in body:
            errors.append("LoadNoticeLines must raise a load-time error toast on failure")
        # A GoE2 native abort must NOT be swallowed: the sentinel + MCM push must
        # happen BEFORE the first LoadStageBank so a dead row is never "(not loaded)".
        first_write = body.find("WriteNoticeLoadStatusToMcm()")
        first_load = body.find("LoadStageBank(")
        if first_write == -1 or first_load == -1 or first_write > first_load:
            errors.append("LoadNoticeLines must pre-write MCM status before the first LoadStageBank (no swallowed GoE2 abort)")
        if "aborted" not in body.lower():
            errors.append("LoadNoticeLines must pre-arm rows with a GoE2-abort sentinel")

    # LoadStageBank / LoadStageBankAt mirror Necromantic's proven loader:
    # DoesFileExist -> GetLinesFromFile -> "!raw || raw.Length == 0" guard.
    # LoadStageBank may thin-wrap LoadStageBankAt(NoticeConfigPath()).
    lsb = re.search(r"Int Function LoadStageBank\(String fileName, String\[\] bank\)(.*?)EndFunction", text, re.S)
    lsb_at = re.search(
        r"Int Function LoadStageBankAt\(String fileName, String\[\] bank, String path\)(.*?)EndFunction",
        text,
        re.S,
    )
    if not lsb:
        errors.append("LoadStageBank not found")
    elif not lsb_at:
        # Legacy: all load logic inside LoadStageBank
        lsb_body = lsb.group(1)
        if "LastStageLoadStatus =" not in lsb_body:
            errors.append("LoadStageBank must set LastStageLoadStatus (per-file MCM debug)")
        if "LastStageLoadDiag" not in lsb_body:
            errors.append("LoadStageBank must build LastStageLoadDiag (Necromantic-style load trace)")
        if "GardenOfEden2.DoesFileExist(" not in lsb_body or "GardenOfEden2.GetLinesFromFile(" not in lsb_body:
            errors.append("LoadStageBank must use GoE2 DoesFileExist + GetLinesFromFile (Necromantic pattern)")
        if "raw.Length == 0" not in lsb_body:
            errors.append("LoadStageBank must guard '!raw || raw.Length == 0' like Necromantic")
    else:
        wrap = lsb.group(1)
        if "LoadStageBankAt" not in wrap:
            errors.append("LoadStageBank must delegate to LoadStageBankAt")
        at_body = lsb_at.group(1)
        if "LastStageLoadStatus =" not in at_body:
            errors.append("LoadStageBankAt must set LastStageLoadStatus (per-file MCM debug)")
        if "LastStageLoadDiag" not in at_body:
            errors.append("LoadStageBankAt must build LastStageLoadDiag (Necromantic-style load trace)")
        if "GardenOfEden2.DoesFileExist(" not in at_body or "GardenOfEden2.GetLinesFromFile(" not in at_body:
            errors.append("LoadStageBankAt must use GoE2 DoesFileExist + GetLinesFromFile (Necromantic pattern)")
        if "raw.Length == 0" not in at_body:
            errors.append("LoadStageBankAt must guard '!raw || raw.Length == 0' like Necromantic")
    # Proven fixed path, exactly mirroring Necromantic's ".\Data\<Mod>\config\".
    ncp = re.search(r"String Function NoticeConfigPath\(\)(.*?)EndFunction", text, re.S)
    if not ncp:
        errors.append("NoticeConfigPath helper missing (fixed proven GoE2 path)")
    elif r'".\\Data\\PickmansWhisper\\config\\"' not in ncp.group(1):
        errors.append(r"NoticeConfigPath must return '.\Data\PickmansWhisper\config\' (Necromantic-proven form)")
    ncro = re.search(r"String Function NecromanticConfigPath\(\)(.*?)EndFunction", text, re.S)
    if ncro and r"necromantic" not in ncro.group(1):
        errors.append("NecromanticConfigPath must include necromantic subdir")

    # FO4 has no StringUtil — notice parse/trim must use real GoE natives.
    trim = re.search(r"String Function TrimString\(String s\)(.*?)EndFunction", text, re.S)
    if not trim:
        errors.append("TrimString not found")
    elif "GetWordsInStringAsArray" not in trim.group(1):
        errors.append("TrimString must use GardenOfEden2.GetWordsInStringAsArray (no fake StringUtil)")
    if "StringUtil." in (trim.group(1) if trim else ""):
        errors.append("TrimString must not call StringUtil (fake FO4 stub)")
    prb = re.search(r"Int Function ParseRawIntoBank\(String\[\] raw, String\[\] bank\)(.*?)EndFunction", text, re.S)
    if not prb:
        errors.append("ParseRawIntoBank not found")
    elif "GardenOfEden.SubStr(" not in prb.group(1):
        errors.append("ParseRawIntoBank must use GardenOfEden.SubStr for '#' comments")
    for fn_name in (
        "ApplyNamePlaceholder",
        "PickNoticeLine",
    ):
        m = re.search(rf"(?:String )?Function {fn_name}\(.*?(?:EndFunction)", text, re.S)
        if m and "StringUtil." in m.group(0):
            errors.append(f"{fn_name} must not call StringUtil (use GoE StrFind/SubStr/ReplaceStr)")
    # Strip helpers stay on Main; VoiceAlias.ApplyNamePlaceholder calls them via Main().
    for fn_name in (
        "StripNamePlaceholder",
        "StripLeadingNameSeparator",
    ):
        m = re.search(rf"(?:String )?Function {fn_name}\(.*?(?:EndFunction)", main_text, re.S)
        if m and "StringUtil." in m.group(0):
            errors.append(f"{fn_name} must not call StringUtil (use GoE StrFind/SubStr/ReplaceStr)")
    strip = re.search(
        r"String Function StripNamePlaceholder\(String line\)(.*?)EndFunction",
        main_text,
        re.S,
    )
    if not strip:
        errors.append("StripNamePlaceholder missing (Main)")
    else:
        body = strip.group(1)
        for needle in ('"{name}. "', '"{name} - "', '"{name} — "', 'ReplaceStr'):
            if needle not in body:
                errors.append(f"StripNamePlaceholder must use ReplaceStr patterns incl. {needle}")
        if "StrFind(" in body and "SubStr(" in body:
            errors.append("StripNamePlaceholder must not SubStr using StrFind (GoE count≠index)")
    if "Function StrContains(" not in main_text:
        errors.append("StrContains helper missing on Main (ReplaceStr-based contains)")
    lead = re.search(
        r"String Function StripLeadingNameSeparator\(String s\)(.*?)EndFunction",
        main_text,
        re.S,
    )
    if not lead:
        errors.append("StripLeadingNameSeparator missing (Main)")
    elif "SubStr(s, 0," not in lead.group(1):
        errors.append("StripLeadingNameSeparator must use SubStr prefix checks (not StrFind==0)")

    # Load-trace DiagNotify is MCM "Test notice file load" only — not init/load.
    rns = re.search(r"Function ReportNoticeLoadStatus\(\)(.*?)EndFunction", text, re.S)
    if not rns:
        errors.append("ReportNoticeLoadStatus missing (MCM button DiagNotify)")
    elif "DiagNotify(" not in rns.group(1) or "NoticeLoadDiag" not in rns.group(1):
        errors.append("ReportNoticeLoadStatus must DiagNotify NoticeLoadDiag")
    oqi = re.search(r"Event OnQuestInit\(\)(.*?)EndEvent", main_text, re.S)
    if oqi and "ReportNoticeLoadStatus()" in oqi.group(1):
        errors.append("OnQuestInit must not ReportNoticeLoadStatus (no launch diag dump)")
    hgr = re.search(r"Function HandleGameResume\(String reason\)(.*?)EndFunction", main_text, re.S)
    if hgr and "ReportNoticeLoadStatus()" in hgr.group(1):
        errors.append("HandleGameResume must not ReportNoticeLoadStatus (no launch diag dump)")
    # Reload on MCM open (Necromantic OnMCMMenuOpen pattern) — Main owns MCM hooks.
    mcm_open = re.search(
        r"Function OnMCMMenuOpen\(String modName\)(.*?)EndFunction", main_text, re.S
    )
    if not mcm_open:
        errors.append("OnMCMMenuOpen not found")
    else:
        mcm_body = mcm_open.group(1)
        if "VoiceAlias.LoadNoticeLines()" not in mcm_body and "LoadNoticeLines()" not in mcm_body:
            errors.append("OnMCMMenuOpen must reload notice files (VoiceAlias.LoadNoticeLines)")
        # RefreshMenu before load — otherwise settings.ini defaults wipe the rows.
        rm = mcm_body.find("MCM.RefreshMenu()")
        ln = mcm_body.find("LoadNoticeLines()")
        if rm == -1 or ln == -1 or rm > ln:
            errors.append("OnMCMMenuOpen must RefreshMenu BEFORE LoadNoticeLines (MCM wipe bug)")

    # Refresh status must reload files and re-push rows AFTER RefreshMenu.
    rds = re.search(r"Function RefreshDebugStatus\(\)(.*?)EndFunction", main_text, re.S)
    if not rds:
        errors.append("RefreshDebugStatus not found")
    else:
        rbody = rds.group(1)
        if "VoiceAlias.LoadNoticeLines()" not in rbody and "LoadNoticeLines()" not in rbody:
            errors.append("RefreshDebugStatus must LoadNoticeLines (Refresh status was a no-op)")
        # Last WriteNoticeLoadStatusToMcm must come after RefreshMenu.
        last_write = rbody.rfind("WriteNoticeLoadStatusToMcm()")
        last_refresh = rbody.rfind("MCM.RefreshMenu()")
        if last_write == -1 or last_refresh == -1 or last_write < last_refresh:
            errors.append("RefreshDebugStatus must WriteNoticeLoadStatusToMcm AFTER RefreshMenu (MCM wipe bug)")

    # The five per-stage MCM debug rows must be written.
    wls = re.search(r"Function WriteNoticeLoadStatusToMcm\(\)(.*?)EndFunction", text, re.S)
    if not wls:
        errors.append("WriteNoticeLoadStatusToMcm not found")
    else:
        for row in ("sNoticeCalm:Debug", "sNoticeRestless:Debug", "sNoticeHungry:Debug",
                    "sNoticeStarving:Debug", "sNoticeDesperate:Debug"):
            if row not in wls.group(1):
                errors.append(f"WriteNoticeLoadStatusToMcm must write MCM row {row!r}")

    if "sNearby:Debug" not in text:
        errors.append("quest script must write MCM sNearby:Debug")
    if "WriteNearbyStatusToMcm()" not in text:
        errors.append("Refresh/pick path must call WriteNearbyStatusToMcm()")

    # On-demand: reload + full load-trace DiagNotify (Necromantic ShowConfigLoadInfo).
    dtnf = re.search(r"Function DebugTestNoticeFiles\(\)(.*?)EndFunction", text, re.S)
    if not dtnf:
        errors.append("DebugTestNoticeFiles probe missing (on-demand GoE2 file check)")
    else:
        body = dtnf.group(1)
        if "LoadNoticeLines()" not in body:
            errors.append("DebugTestNoticeFiles must reload via LoadNoticeLines")
        if "ReportNoticeLoadStatus()" not in body:
            errors.append("DebugTestNoticeFiles must show ReportNoticeLoadStatus DiagNotify")
        if "Debug.Notification(" not in body:
            errors.append("DebugTestNoticeFiles must toast a found/not-found summary")

    # The facepalm bug — must never come back
    if re.search(r'\+\s*"them"', text) or re.search(r'\+\s*"them"', main_text):
        errors.append('StripNamePlaceholder must not concatenate +"them"')

    # Detection must not use IsHostileToActor; hard gate is Main.IsValidTarget
    m = re.search(
        r"String Function ExplainNoticeReject\(Actor ak(?:, Bool abIgnoreCooldown = False)?\)(.*?)EndFunction",
        text,
        re.S,
    )
    if not m:
        errors.append("ExplainNoticeReject not found")
    else:
        body = m.group(1)
        if re.search(r"(?<!;)\s*IsHostileToActor\s*\(", body) or re.search(r"^\s*If.*IsHostileToActor", body, re.M):
            errors.append("ExplainNoticeReject must not call IsHostileToActor")
        if "IsValidTarget" not in body:
            errors.append("ExplainNoticeReject must call IsValidTarget (hard gate)")
        if "ExplainNonHumanForNotice" in body:
            errors.append("ExplainNoticeReject must not call ExplainNonHumanForNotice — hard gate owns human check")
        if re.search(r"\bak\.IsChild\s*\(", body):
            errors.append("ExplainNoticeReject must not call ak.IsChild() directly")

    # Child filter: FO4 IsChild() alone is incomplete; keyword 0x1157E8 required (Main)
    if "Function IsChildNpc" not in main_text and "Bool Function IsChildNpc" not in main_text:
        errors.append("IsChildNpc helper missing")
    else:
        child_fn = re.search(
            r"Bool Function IsChildNpc\(Actor ak\)(.*?)EndFunction", main_text, re.S
        )
        if not child_fn:
            errors.append("IsChildNpc body not found")
        else:
            cbody = child_fn.group(1)
            if "IsChild()" not in cbody:
                errors.append("IsChildNpc must still check native IsChild()")
            if "KW_ActorTypeChild" not in cbody or "HasKeyword" not in cbody:
                errors.append("IsChildNpc must check KW_ActorTypeChild keyword")
        if "0x001157E8" not in main_text:
            errors.append("ActorTypeChild FormID 0x001157E8 must be loaded in EnsureFilterKeywords")
        else:
            # Lock FormID against Fallout4.esm when available (same pattern as blade contract).
            try:
                from _env import load_dotenv
                import os
                from pathlib import Path as _P

                load_dotenv()
                esm = os.environ.get("FALLOUT4_ESM")
                if esm and _P(esm).is_file():
                    data = _P(esm).read_bytes()
                    if b"ActorTypeChild\x00" not in data:
                        errors.append("Fallout4.esm missing EDID ActorTypeChild")
                    else:
                        target = (0x001157E8).to_bytes(4, "little")
                        edid = b"ActorTypeChild\x00"
                        pos = 0
                        found = False
                        while True:
                            j = data.find(edid, pos)
                            if j < 0:
                                break
                            k = data.rfind(b"KYWD", max(0, j - 200), j)
                            if k >= 0 and data[k + 12 : k + 16] == target:
                                found = True
                                break
                            pos = j + 1
                        if not found:
                            errors.append(
                                "0x001157E8 must be KYWD ActorTypeChild in Fallout4.esm"
                            )
            except Exception as ex:  # pragma: no cover — env optional
                pass
    adult = re.search(
        r"Bool Function IsAdultFemale\(Actor ak\)(.*?)EndFunction", main_text, re.S
    )
    if adult:
        abody = adult.group(1)
        if "IsChildNpc" not in abody:
            errors.append("IsAdultFemale must check IsChildNpc")
        if "IsChildTargetAllowed" not in abody:
            errors.append("IsAdultFemale must honor IsChildTargetAllowed (TargetOverrides)")

    # PickNoticeLine must select by stage + guard immediate repeat.
    pnl = re.search(r"String Function PickNoticeLine\(String npcName\)(.*?)EndFunction", text, re.S)
    if not pnl:
        errors.append("PickNoticeLine not found")
    else:
        body = pnl.group(1)
        if "GetNoticeStage()" not in body:
            errors.append("PickNoticeLine must select via GetNoticeStage()")
        if "LastNoticeLine" not in body:
            errors.append("PickNoticeLine must check LastNoticeLine (no-immediate-repeat)")
        if 'Return ""' not in body:
            errors.append("PickNoticeLine must return \"\" when the stage bank is empty (files-only skip)")

    commit = re.search(r"Function CommitNearbyPickSummary\(Int nLive, Actor best\)(.*?)EndFunction", text, re.S)
    if not commit:
        errors.append("CommitNearbyPickSummary not found")
    elif "WriteNearbyStatusToMcm()" in commit.group(1):
        errors.append("CommitNearbyPickSummary must be memory-only")

    probe = re.search(
        r"Function DebugScanNearbyNpcs\(\)(.*?)EndFunction", main_text, re.S
    )
    if not probe:
        errors.append("DebugScanNearbyNpcs not found")
    else:
        pbody = probe.group(1)
        if "MarkNoticeCooldown" in pbody:
            errors.append("DebugScanNearbyNpcs must not call MarkNoticeCooldown (probe must not starve auto poll)")
        if "DiagNotify(" not in pbody:
            errors.append("DebugScanNearbyNpcs must DiagNotify (MCM Scan nearby; no pause)")

    if errors:
        raise AssertionError("PSC contract failures:\n  - " + "\n  - ".join(errors))


def _psc_float(text: str, name: str) -> float:
    m = re.search(rf"^\s*Float\s+{re.escape(name)}\s*=\s*([0-9.]+)", text, re.M)
    if not m:
        raise AssertionError(f"missing Float {name} in quest script")
    return float(m.group(1))


def _psc_int(text: str, name: str) -> int:
    m = re.search(rf"^\s*(?:Float|Int)\s+{re.escape(name)}\s*=\s*([0-9.]+)", text, re.M)
    if not m:
        raise AssertionError(f"missing {name} in quest script")
    return int(float(m.group(1)))


def test_notice_cadence() -> None:
    """Hunger whispers are rare; the killscan poll stays frequent for fixation.

    Ambient hunger: ~1 per game hour (NOTICE_MIN_GAME_HOURS).
    Killscan timer: KILL_SCAN_SECONDS < 10 so look-fixation can edge often.
    """
    text = PSC.read_text(encoding="utf-8", errors="replace")
    main_text = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    scan_secs = _psc_float(main_text, "KILL_SCAN_SECONDS")
    hour_gate = _psc_float(text, "NOTICE_MIN_GAME_HOURS")

    errors: list[str] = []
    if scan_secs <= 0 or scan_secs >= 10.0:
        errors.append(f"KILL_SCAN_SECONDS {scan_secs} must be in (0, 10)")
    if hour_gate < 1.0:
        errors.append(f"NOTICE_MIN_GAME_HOURS {hour_gate} must be >= 1 (max ~1 hunger toast / game hour)")

    toast = re.search(r"Function ToastNoticeLine\(String line\)(.*?)EndFunction", text, re.S)
    if not toast or "LastNoticeToastGameTime" not in toast.group(1):
        errors.append("ToastNoticeLine must stamp LastNoticeToastGameTime")
    if not toast or "ShowVoiceToast" not in toast.group(1):
        errors.append("ToastNoticeLine must ShowVoiceToast (HUD lead-glyph clip pad)")
    fmt = re.search(r"String Function FormatVoiceToast\(String line\)(.*?)EndFunction", text, re.S)
    if not fmt:
        errors.append("FormatVoiceToast missing — FO4 clips leading toast glyphs")
    elif "Debug.Notification" in fmt.group(1):
        errors.append("FormatVoiceToast must only pad, not Notification")
    else:
        pad_m = re.search(r'Return "([^"]*)" \+ line', fmt.group(1))
        if not pad_m or not pad_m.group(1) or any(ord(c) != 0xA0 for c in pad_m.group(1)):
            errors.append("FormatVoiceToast pad must be NBSP (U+00A0); ASCII spaces are LTRIM'd by FO4 HUD")
        elif len(pad_m.group(1)) < 2:
            errors.append("FormatVoiceToast needs >= 2 NBSP to cover typical 1–3 glyph clip")
    show = re.search(r"Function ShowVoiceToast\(String line\)(.*?)EndFunction", text, re.S)
    if not show or "FormatVoiceToast" not in show.group(1) or "Debug.Notification" not in show.group(1):
        errors.append("ShowVoiceToast must Notification(FormatVoiceToast(line))")
    # Voice paths must not bare-Notification the raw line (clip bug).
    # ToastVoice/Hunger/Praise stay on Main; SpeakRecognitionLine is on VoiceAlias.
    main_blob = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    for fn_name, blob in (
        ("ToastVoice", main_blob),
        ("ToastHungerLine", main_blob),
        ("ToastPraiseLine", main_blob),
        ("SpeakRecognitionLine", text),
    ):
        m = re.search(rf"Function {fn_name}\(.*?\n(.*?)EndFunction", blob, re.S)
        if not m:
            errors.append(f"missing {fn_name}")
        elif "ShowVoiceToast" not in m.group(1):
            errors.append(f"{fn_name} must ShowVoiceToast (not bare Debug.Notification for voice)")

    voice_path = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
    world_path = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillerScanScript.psc"
    if not voice_path.is_file():
        errors.append("PickmansWhisperVoiceAliasScript.psc missing (KillerScan bus voice path)")
    else:
        body = voice_path.read_text(encoding="utf-8", errors="replace")
        if "Function HandleWhisperVoice" not in body:
            errors.append("VoiceAlias must HandleWhisperVoice(Actor)")
    if world_path.is_file():
        wbody = world_path.read_text(encoding="utf-8", errors="replace")
        if "HandleWhisperVoice" not in wbody or "DispatchListeners" not in wbody:
            errors.append("KillerScan must DispatchListeners → HandleWhisperVoice")


    if errors:
        raise AssertionError("notice cadence failures:\n  - " + "\n  - ".join(errors))


def test_notice_approach_c4_parked() -> None:
    """C4 is parked until ambient C3 whispers are verified again in-game.

    Prior C4 wiring (0.5s timer / extra FindActors on killscan) silenced all
    notices. This contract locks the restore: KillerScan ambient only, no approach
    hot path, no 0.5s StartTimer.
    """
    text = PSC.read_text(encoding="utf-8", errors="replace")
    main_text = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    for blob, label in ((text, "VoiceAlias"), (main_text, "Main")):
        if "NOTICE_APPROACH_SECONDS" in blob:
            errors.append(f"{label}: NOTICE_APPROACH_SECONDS must stay removed")
        if "Function TickNoticeApproach()" in blob:
            errors.append(f"{label}: TickNoticeApproach must stay removed while C4 is parked")
        if "Function SpeakNoticeToTarget(" in blob:
            errors.append(f"{label}: SpeakNoticeToTarget must stay removed while C4 is parked")
        if "StartTimer(NOTICE_APPROACH_SECONDS" in blob or "StartTimer(0.5" in blob:
            errors.append(f"{label}: must not StartTimer a 0.5s approach poll")

    if "TickNoticeApproach" in text:
        errors.append("VoiceAlias must not call TickNoticeApproach while C4 is parked")
    if "RegisterForCustomEvent" in text:
        errors.append("VoiceAlias must not RegisterForCustomEvent (whispers stayed silent)")

    ont = re.search(
        r"ElseIf aiTimerID == TIMER_NOTICE_APPROACH\s*\n(.*?)ElseIf", main_text, re.S
    )
    if ont:
        branch = ont.group(1)
        if "StartTimer(" in branch or "TickNoticeApproach" in branch:
            errors.append("OnTimer TIMER_NOTICE_APPROACH must only CancelTimer (legacy cleanup)")

    if errors:
        raise AssertionError("C4 parked / ambient restore failures:\n  - " + "\n  - ".join(errors))


def test_ambient_notice_no_dialog_mcm_scan_keeps_dialog() -> None:
    """Auto paths: no modal MessageBox. MCM Debug uses DiagNotify (toast + Papyrus log)."""
    text = PSC.read_text(encoding="utf-8", errors="replace")
    main_text = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    if "Function DiagNotify(" not in main_text:
        errors.append("Main must define DiagNotify (Trace + Notification; no MessageBox pause)")
    if "Debug.MessageBox(" in main_text:
        errors.append("Main must not Debug.MessageBox (use DiagNotify)")
    if "Debug.MessageBox(" in text:
        errors.append("VoiceAlias must not Debug.MessageBox (use Main().DiagNotify)")

    run = re.search(
        r"Function HandleKillerScanKnifeAimWarm\(\)(.*?)EndFunction",
        main_text,
        re.S,
    )
    if run and ("Debug.MessageBox(" in run.group(1) or "DiagNotify(" in run.group(1)):
        errors.append("HandleKillerScanKnifeAimWarm must not MessageBox/DiagNotify (heartbeat is ToastDebug only)")


    arm_ann = re.search(
        r"Function AnnounceKillScanArmed\(\)(.*?)EndFunction", main_text, re.S
    )
    if arm_ann and ("Debug.MessageBox(" in arm_ann.group(1) or "DiagNotify(" in arm_ann.group(1)):
        errors.append("AnnounceKillScanArmed must not MessageBox/DiagNotify (fires on load/arm)")

    for name, pattern in (
        ("OnQuestInit", r"Event OnQuestInit\(\)(.*?)EndEvent"),
        ("HandleGameResume", r"Function HandleGameResume\(String reason\)(.*?)EndFunction"),
        ("OnInit", r"Event OnInit\(\)(.*?)EndEvent"),
    ):
        m = re.search(pattern, main_text, re.S)
        if not m:
            continue
        if "Debug.MessageBox(" in m.group(1) or "ReportNoticeLoadStatus()" in m.group(1):
            errors.append(f"{name} must not show MessageBox / ReportNoticeLoadStatus on launch")

    probe = re.search(
        r"Function DebugScanNearbyNpcs\(\)(.*?)EndFunction", main_text, re.S
    )
    if not probe:
        errors.append("DebugScanNearbyNpcs missing")
    elif "DiagNotify(" not in probe.group(1):
        errors.append("DebugScanNearbyNpcs must DiagNotify for MCM button (no pause)")

    dtnf = re.search(r"Function DebugTestNoticeFiles\(\)(.*?)EndFunction", text, re.S)
    if not dtnf:
        errors.append("DebugTestNoticeFiles missing")
    elif "ReportNoticeLoadStatus()" not in dtnf.group(1):
        errors.append("DebugTestNoticeFiles must still call ReportNoticeLoadStatus (MCM load diag)")

    rns = re.search(r"Function ReportNoticeLoadStatus\(\)(.*?)EndFunction", text, re.S)
    if not rns or "DiagNotify(" not in rns.group(1):
        errors.append("ReportNoticeLoadStatus must DiagNotify when MCM button calls it")

    if errors:
        raise AssertionError("ambient dialog UX failures:\n  - " + "\n  - ".join(errors))


def test_mcm_exposes_load_rows() -> None:
    """The five per-file load-status rows must exist on the MCM Debug page."""
    cfg = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
    if not cfg.is_file():
        raise AssertionError(f"missing MCM config {cfg}")
    text = cfg.read_text(encoding="utf-8", errors="replace")
    for row in ("sNoticeCalm:Debug", "sNoticeRestless:Debug", "sNoticeHungry:Debug",
                "sNoticeStarving:Debug", "sNoticeDesperate:Debug"):
        if row not in text:
            raise AssertionError(f"MCM config.json missing per-file debug row {row!r}")


def test_notice_stage_control() -> None:
    """Debug stage dropdown + Force toggle must exist and be honored by the script."""
    errors: list[str] = []
    cfg = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
    cfg_text = cfg.read_text(encoding="utf-8", errors="replace")
    for needle in ('"iNoticeStage:Debug"', '"type": "menu"', '"bForceNoticeStage:Debug"'):
        if needle not in cfg_text:
            errors.append(f"config.json missing {needle}")
    for opt in ("1 Calm", "2 Restless", "3 Hungry", "4 Starving", "5 Desperate"):
        if opt not in cfg_text:
            errors.append(f"config.json stage dropdown missing option {opt!r}")

    # Both settings files must declare defaults for the new int/bool keys.
    for ini in (
        ROOT / "Data" / "MCM" / "Settings" / "PickmansWhisper.ini",
        ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini",
    ):
        itext = ini.read_text(encoding="utf-8", errors="replace")
        for key in ("iNoticeStage=", "bForceNoticeStage="):
            if key not in itext:
                errors.append(f"{ini.name} missing default {key}")

    # GetNoticeStage must honor the force override before falling back to hunger.
    text = PSC.read_text(encoding="utf-8", errors="replace")
    gns = re.search(r"Int Function GetNoticeStage\(\)(.*?)EndFunction", text, re.S)
    if not gns:
        errors.append("GetNoticeStage not found")
    else:
        body = gns.group(1)
        if "IsNoticeStageForced()" not in body:
            errors.append("GetNoticeStage must check IsNoticeStageForced() override")
        if 'iNoticeStage:Debug' not in body:
            errors.append("GetNoticeStage must read the iNoticeStage:Debug dropdown when forced")
        force_at = body.find("IsNoticeStageForced()")
        hunger_at = body.find("HungerLevel")
        if force_at < 0 or hunger_at < 0 or force_at > hunger_at:
            errors.append("GetNoticeStage must apply the override before the hunger thresholds")
    if "Function IsNoticeStageForced" not in text:
        errors.append("IsNoticeStageForced helper missing")

    if errors:
        raise AssertionError("notice stage control failures:\n  - " + "\n  - ".join(errors))


def test_no_dead_config_files() -> None:
    """Every shipped notice-bank .txt must actually be read by a user quest script.

    We removed TrustLines/HungerLines/PraiseLines/NoticeLines.txt because the code
    never read them (editing did nothing). Guard so unread 'editable' files can't
    ship again and mislead users.

    Scans all ``Data/Scripts/Source/User/*.psc`` (Main + feature scripts like BedGift).

    Exception: ``WhisperSndrIds.txt`` / ``DecayFaceArmorIds.txt`` are generated by the
    esp build (FormID tables). ``DecayFaceStages.txt`` is read by CorpseDecay.
    Exception: ``*.example.txt`` are optional templates (e.g. TargetOverrides.example.txt).
    """
    if not CONFIG.is_dir():
        raise AssertionError(f"missing config dir {CONFIG}")
    user_src = ROOT / "Data" / "Scripts" / "Source" / "User"
    text = ""
    for psc in sorted(user_src.glob("*.psc")):
        text += psc.read_text(encoding="utf-8", errors="replace")
    generated_ok = {
        "WhisperSndrIds.txt",
        "DecayFaceArmorIds.txt",
    }
    orphans = [
        p.name
        for p in sorted(CONFIG.glob("*.txt"))
        if p.name not in text
        and p.name not in generated_ok
        and not p.name.endswith(".example.txt")
    ]
    if orphans:
        raise AssertionError(
            "config .txt not referenced by quest script (dead/unread): "
            + ", ".join(orphans)
        )


def main() -> int:
    if not PSC.is_file():
        print(f"FAIL: missing {PSC}")
        return 1
    try:
        test_stage_files_parse()
        test_generic_never_in_toast()
        test_unprintable_name_treated_as_nameless()
        test_named_keeps_name()
        test_no_immediate_repeat()
        test_strip_never_inserts_them()
        test_strip_removes_following_separators()
        test_psc_contracts()
        test_notice_cadence()
        test_notice_approach_c4_parked()
        test_ambient_notice_no_dialog_mcm_scan_keeps_dialog()
        test_mcm_exposes_load_rows()
        test_notice_stage_control()
        test_no_dead_config_files()
    except AssertionError as e:
        print(f"FAIL: {e}")
        return 1
    print("PASS notice line / detection contracts")
    print("  5 hunger stages parse; generic settlers -> nameless whisper (not 'them')")
    print("  unprintable/glyph names -> nameless; P3 GetVictimOverrideName hook in GetActorDisplayName")
    print("  PickNoticeLine: stage-select + no-immediate-repeat; probe/toast invariants held")
    print("  cadence: killscan <10s; hunger ~1/game hour; fixation separate")
    print("  C4 parked: ambient killscan ToastNoticeLine only (C3 restore)")
    print("  ambient UX: no MessageBox in notice loop; MCM Scan nearby uses DiagNotify")
    print("  files-only notice banks: builtins retired, per-file MCM load status + error toast")
    print("  stage control: MCM dropdown + force toggle; GetNoticeStage honors override")
    print("  no dead config: every shipped .txt is read by the quest script")
    return 0


if __name__ == "__main__":
    sys.exit(main())
