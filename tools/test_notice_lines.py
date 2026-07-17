#!/usr/bin/env python3
"""Regression tests for notice whisper text + PSC contracts (C2 + C3 staging).

Locks:
  - Generic labels (Settler, etc.) must NOT appear in rendered toast text
  - StripNamePlaceholder must never insert the word "them"
  - Named NPCs still get {name} substitution
  - ExplainNoticeReject must not use IsHostileToActor (settler false positives)
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
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
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


def notice_name_for_line(npc_name: str) -> str:
    """Mirror of NoticeNameForLine (Papyrus compare is case-insensitive)."""
    if not npc_name:
        return ""
    lower = npc_name.casefold()
    for g in GENERIC_NAMES:
        if lower == g.casefold():
            return ""
    if "settler" in lower:
        return ""
    return npc_name


def strip_name_placeholder(line: str) -> str:
    """Mirror StripNamePlaceholder: remove {name}, never insert 'them'."""
    if not line or "{name}" not in line:
        return line
    p = line.index("{name}")
    before = line[:p]
    after = line[p + 6:]
    if after.startswith(". "):
        after = after[2:]
    out = before + after
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
            for gname in ("Settler", "settler", "Raider", "Gunner"):
                out = pick_notice_line(lines, gname, rng_index=i)
                assert gname.casefold() not in out.casefold(), f"stage {name}: {out!r} contains {gname!r}"
                assert out.casefold() != "them"
                assert len(out) >= 8


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


def test_psc_contracts() -> None:
    text = PSC.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    for needle in (
        "Function NoticeNameForLine",
        "Function GetNoticeStage",
        "Function GetNoticeBankForStage",
        "Function GetNoticeCountForStage",
        "Function LoadStageBank",
        "Function ExplainNonHumanForNotice",
        "Function OnNoticeSpoken",
        "Function CommitNearbyPickSummary",
        "Function WriteNearbyStatusToMcm",
        "Function WriteNoticeLoadStatusToMcm",
        "Function NoticeLoadFailureList",
        "GardenOfEden2.GetLinesFromFile",
        "LastNoticeLine",
        "LastStageLoadStatus",
        'npcName == "Settler"',
    ):
        if needle not in text:
            errors.append(f"missing {needle!r} in quest script")

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

    # LoadStageBank mirrors Necromantic's proven loader: fixed ".\Data\..\config\"
    # path, DoesFileExist -> GetLinesFromFile -> "!raw || raw.Length == 0" guard.
    lsb = re.search(r"Int Function LoadStageBank\(String fileName, String\[\] bank\)(.*?)EndFunction", text, re.S)
    if not lsb:
        errors.append("LoadStageBank not found")
    else:
        lsb_body = lsb.group(1)
        if "LastStageLoadStatus =" not in lsb_body:
            errors.append("LoadStageBank must set LastStageLoadStatus (per-file MCM debug)")
        if "LastStageLoadDiag" not in lsb_body:
            errors.append("LoadStageBank must build LastStageLoadDiag (Necromantic-style load trace)")
        if "GardenOfEden2.DoesFileExist(" not in lsb_body or "GardenOfEden2.GetLinesFromFile(" not in lsb_body:
            errors.append("LoadStageBank must use GoE2 DoesFileExist + GetLinesFromFile (Necromantic pattern)")
        if "raw.Length == 0" not in lsb_body:
            errors.append("LoadStageBank must guard '!raw || raw.Length == 0' like Necromantic")
    # Proven fixed path, exactly mirroring Necromantic's ".\Data\<Mod>\config\".
    ncp = re.search(r"String Function NoticeConfigPath\(\)(.*?)EndFunction", text, re.S)
    if not ncp:
        errors.append("NoticeConfigPath helper missing (fixed proven GoE2 path)")
    elif r'".\\Data\\PickmansWhisper\\config\\"' not in ncp.group(1):
        errors.append(r"NoticeConfigPath must return '.\Data\PickmansWhisper\config\' (Necromantic-proven form)")

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
    for fn_name in ("ApplyNamePlaceholder", "StripNamePlaceholder", "PickNoticeLine"):
        m = re.search(rf"(?:String )?Function {fn_name}\(.*?(?:EndFunction)", text, re.S)
        if m and "StringUtil." in m.group(0):
            errors.append(f"{fn_name} must not call StringUtil (use GoE StrFind/SubStr/ReplaceStr)")

    # Forced MessageBox load report (Necromantic ReportConfigLoadStatus pattern).
    rns = re.search(r"Function ReportNoticeLoadStatus\(\)(.*?)EndFunction", text, re.S)
    if not rns:
        errors.append("ReportNoticeLoadStatus missing (forced load MessageBox)")
    elif "Debug.MessageBox(" not in rns.group(1) or "NoticeLoadDiag" not in rns.group(1):
        errors.append("ReportNoticeLoadStatus must MessageBox NoticeLoadDiag")
    if "ReportNoticeLoadStatus()" not in text:
        errors.append("init/load path must call ReportNoticeLoadStatus()")
    # Reload on MCM open (Necromantic OnMCMMenuOpen pattern).
    mcm_open = re.search(r"Function OnMCMMenuOpen\(String modName\)(.*?)EndFunction", text, re.S)
    if not mcm_open:
        errors.append("OnMCMMenuOpen not found")
    else:
        mcm_body = mcm_open.group(1)
        if "LoadNoticeLines()" not in mcm_body:
            errors.append("OnMCMMenuOpen must reload notice files (LoadNoticeLines)")
        # RefreshMenu before load — otherwise settings.ini defaults wipe the rows.
        rm = mcm_body.find("MCM.RefreshMenu()")
        ln = mcm_body.find("LoadNoticeLines()")
        if rm == -1 or ln == -1 or rm > ln:
            errors.append("OnMCMMenuOpen must RefreshMenu BEFORE LoadNoticeLines (MCM wipe bug)")

    # Refresh status must reload files and re-push rows AFTER RefreshMenu.
    rds = re.search(r"Function RefreshDebugStatus\(\)(.*?)EndFunction", text, re.S)
    if not rds:
        errors.append("RefreshDebugStatus not found")
    else:
        rbody = rds.group(1)
        if "LoadNoticeLines()" not in rbody:
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

    # On-demand: reload + full load-trace MessageBox (Necromantic ShowConfigLoadInfo).
    dtnf = re.search(r"Function DebugTestNoticeFiles\(\)(.*?)EndFunction", text, re.S)
    if not dtnf:
        errors.append("DebugTestNoticeFiles probe missing (on-demand GoE2 file check)")
    else:
        body = dtnf.group(1)
        if "LoadNoticeLines()" not in body:
            errors.append("DebugTestNoticeFiles must reload via LoadNoticeLines")
        if "ReportNoticeLoadStatus()" not in body:
            errors.append("DebugTestNoticeFiles must show ReportNoticeLoadStatus MessageBox")
        if "Debug.Notification(" not in body:
            errors.append("DebugTestNoticeFiles must toast a found/not-found summary")

    # The facepalm bug — must never come back
    if re.search(r'\+\s*"them"', text):
        errors.append('StripNamePlaceholder must not concatenate +"them"')

    # Detection must not use IsHostileToActor inside ExplainNoticeReject
    m = re.search(r"String Function ExplainNoticeReject\(Actor ak\)(.*?)EndFunction", text, re.S)
    if not m:
        errors.append("ExplainNoticeReject not found")
    else:
        body = m.group(1)
        if re.search(r"(?<!;)\s*IsHostileToActor\s*\(", body) or re.search(r"^\s*If.*IsHostileToActor", body, re.M):
            errors.append("ExplainNoticeReject must not call IsHostileToActor")
        if "ExplainNonHumanForNotice" not in body:
            errors.append("ExplainNoticeReject must call ExplainNonHumanForNotice")
        if "IsAdultFemale" not in body:
            errors.append("ExplainNoticeReject must call IsAdultFemale")

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

    # Toast must not depend on notice-poll debug dialogs
    speak = re.search(r"Function MaybeSpeakNoticeLine\(String source\)(.*?)EndFunction", text, re.S)
    if not speak:
        errors.append("MaybeSpeakNoticeLine not found")
    else:
        body = speak.group(1)
        if "ToastNoticeLine(line)" not in body:
            errors.append("MaybeSpeakNoticeLine must call ToastNoticeLine")
        ok_dialog = body.find("RESULT: TOAST")
        toast_at = body.find("ToastNoticeLine(line)")
        if toast_at < 0 or ok_dialog < 0 or toast_at > ok_dialog:
            errors.append("ToastNoticeLine must run before the RESULT: TOAST dialog")
        if re.search(r"If IsNoticePollDebugEnabled\(\)\s*\n\s*NoticeCoolCount\s*=\s*0", body):
            errors.append("MaybeSpeakNoticeLine must not clear cooldowns only when notice-poll debug is on")
        # Files-only: empty line must skip (return) BEFORE toast/cooldown, not fake a line.
        # Length check uses GoE StrLength (FO4 has no StringUtil).
        empty_guard = re.search(
            r"If !line \|\| GardenOfEden\.StrLength\(line\) < 1(.*?)EndIf", body, re.S
        )
        if not empty_guard:
            errors.append("MaybeSpeakNoticeLine must guard empty line via GoE StrLength (files-only skip)")
        elif "Return" not in empty_guard.group(1):
            errors.append("MaybeSpeakNoticeLine empty-line guard must Return (skip), not fall through to toast")

    pick = re.search(r"Actor Function PickNoticeTarget\(\)(.*?)EndFunction", text, re.S)
    if not pick:
        errors.append("PickNoticeTarget not found")
    else:
        body = pick.group(1)
        if "PickBestNoticeFromList(living)" not in body:
            errors.append("PickNoticeTarget must call PickBestNoticeFromList(living)")
        if "WriteNearbyStatusToMcm()" in body:
            errors.append("PickNoticeTarget must not write MCM mid-pick")

    commit = re.search(r"Function CommitNearbyPickSummary\(Int nLive, Actor best\)(.*?)EndFunction", text, re.S)
    if not commit:
        errors.append("CommitNearbyPickSummary not found")
    elif "WriteNearbyStatusToMcm()" in commit.group(1):
        errors.append("CommitNearbyPickSummary must be memory-only")

    probe = re.search(r"Function DebugScanNearbyNpcs\(\)(.*?)EndFunction", text, re.S)
    if not probe:
        errors.append("DebugScanNearbyNpcs not found")
    elif "MarkNoticeCooldown" in probe.group(1):
        errors.append("DebugScanNearbyNpcs must not call MarkNoticeCooldown (probe must not starve auto poll)")

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
    """A lone nearby female must still whisper regularly.

    The notice poll fires every KILL_SCAN_SECONDS * (killscan modulo) seconds.
    If the cooldowns creep back up (e.g. 20s per-NPC), a sparse settlement with
    one eligible woman goes effectively silent — exactly the 'no toasts' report.
    Lock the cadence so it can't regress.
    """
    text = PSC.read_text(encoding="utf-8", errors="replace")
    toast_cd = _psc_float(text, "NOTICE_TOAST_COOLDOWN")
    npc_cd = _psc_float(text, "NOTICE_NPC_COOLDOWN")
    scan_secs = _psc_float(text, "KILL_SCAN_SECONDS")

    m = re.search(r"KillScanTickCount % (\d+)\) == 0\s*\n\s*MaybeSpeakNoticeLine\(\"killscan\"\)", text)
    if not m:
        raise AssertionError("could not find killscan -> MaybeSpeakNoticeLine cadence in quest script")
    poll_secs = scan_secs * int(m.group(1))

    errors: list[str] = []
    if toast_cd <= 0:
        errors.append("NOTICE_TOAST_COOLDOWN must be > 0")
    if toast_cd > npc_cd:
        errors.append(f"global toast cooldown ({toast_cd}) should not exceed per-NPC cooldown ({npc_cd})")
    # A lone nearby female must re-whisper often enough to feel alive.
    if npc_cd > 15.0:
        errors.append(f"NOTICE_NPC_COOLDOWN {npc_cd} too long — lone female goes silent; keep <= 15s")
    # Global cooldown should not starve the ~poll cadence so a fresh target can speak.
    if toast_cd > poll_secs + 2.0:
        errors.append(f"NOTICE_TOAST_COOLDOWN {toast_cd} > poll cadence {poll_secs}+2 — whispers get throttled off")

    if errors:
        raise AssertionError("notice cadence failures:\n  - " + "\n  - ".join(errors))


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
    """Every shipped config .txt must actually be read by the quest script.

    We removed TrustLines/HungerLines/PraiseLines/NoticeLines.txt because the code
    never read them (editing did nothing). Guard so unread 'editable' files can't
    ship again and mislead users.
    """
    if not CONFIG.is_dir():
        raise AssertionError(f"missing config dir {CONFIG}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    orphans = [
        p.name for p in sorted(CONFIG.glob("*.txt"))
        if p.name not in text
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
        test_named_keeps_name()
        test_no_immediate_repeat()
        test_strip_never_inserts_them()
        test_psc_contracts()
        test_notice_cadence()
        test_mcm_exposes_load_rows()
        test_notice_stage_control()
        test_no_dead_config_files()
    except AssertionError as e:
        print(f"FAIL: {e}")
        return 1
    print("PASS notice line / detection contracts")
    print("  5 hunger stages parse; generic settlers -> nameless whisper (not 'them')")
    print("  PickNoticeLine: stage-select + no-immediate-repeat; probe/toast invariants held")
    print("  cadence: lone female still whispers (toast<=6s poll, npc<=15s)")
    print("  files-only notice banks: builtins retired, per-file MCM load status + error toast")
    print("  stage control: MCM dropdown + force toggle; GetNoticeStage honors override")
    print("  no dead config: every shipped .txt is read by the quest script")
    return 0


if __name__ == "__main__":
    sys.exit(main())
