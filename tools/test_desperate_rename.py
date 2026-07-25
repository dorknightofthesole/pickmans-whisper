#!/usr/bin/env python3
"""Contracts for Slice I — desperate hunger NPC rename suffix."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = ROOT / "Data" / "Scripts" / "Source" / "User"
MAIN = USER / "PickmansWhisperMainQuestScript.psc"
RENAME = USER / "PickmansWhisperDesperateRenameScript.psc"
KILLER = USER / "PickmansWhisperKillerScanScript.psc"
MOD = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
ESP = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY = ROOT / "tools" / "build-deploy-local.ps1"
DOC = ROOT / "docs" / "SLICE_I_DESPERATE_RENAME.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Bool|Int|Float|String|Function)\s+Function\s+{re.escape(name)}\s*\(",
        text,
    )
    if not m:
        m = re.search(rf"Function\s+{re.escape(name)}\s*\(", text)
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"unclosed {name}")
    return text[start : start + end_m.end()]


def main() -> None:
    if not RENAME.is_file():
        fail("missing PickmansWhisperDesperateRenameScript.psc")
    rename = RENAME.read_text(encoding="utf-8", errors="replace")
    main_txt = MAIN.read_text(encoding="utf-8", errors="replace")
    killer = KILLER.read_text(encoding="utf-8", errors="replace")
    mod = MOD.read_text(encoding="utf-8", errors="replace")

    if "Scriptname PickmansWhisperDesperateRenameScript extends Quest" not in rename:
        fail("DesperateRename must extend Quest")
    sync = extract_function(rename, "SyncFromKillerScanSnapshot")
    if "GetNoticeStage()" not in sync and "GetNoticeStage()" not in rename:
        fail("DesperateRename must gate on GetNoticeStage")
    if "ScanAlive" not in sync:
        fail("SyncFromKillerScanSnapshot must consume KillerScan.ScanAlive")
    if re.search(r"^\s*[^;]*\bFindActors\b", rename, re.M):
        fail("DesperateRename must not call FindActors")
    if "SetDisplayName" not in rename or "GardenOfEden2" not in rename:
        fail("DesperateRename must GardenOfEden2.SetDisplayName")
    if "ExplainNoticeReject" not in rename:
        fail("DesperateRename must use ExplainNoticeReject (skip essentials)")
    if "GetDesperateNameSuffix" not in rename:
        fail("DesperateRename must read suffix via Main GetDesperateNameSuffix")
    maybe = extract_function(rename, "MaybeSuffixDisplayName")
    if "GetNoticeStage() != 4" not in maybe and "GetNoticeStage() == 4" not in maybe:
        fail("MaybeSuffixDisplayName must only suffix at stage 4")

    gad = extract_function(main_txt, "GetActorDisplayName")
    if "MaybeSuffixDisplayName" not in gad:
        fail("GetActorDisplayName must MaybeSuffixDisplayName (toast matches HUD)")
    if "Function DesperateRename()" not in main_txt:
        fail("Main must DesperateRename() façade")
    if "GetDesperateNameSuffix" not in main_txt:
        fail("Main must GetDesperateNameSuffix")
    if 'key == "desperateNameSuffix"' not in main_txt:
        fail("LoadModConfig must parse desperateNameSuffix")
    # Leading space preserved — must not ConfigFieldTrim the suffix value.
    load = extract_function(main_txt, "LoadModConfig")
    if "desperateNameSuffix" not in load:
        fail("LoadModConfig must load desperateNameSuffix")
    if re.search(
        r'desperateNameSuffix[\s\S]{0,120}ConfigFieldTrim\(val\)',
        load,
    ):
        fail("desperateNameSuffix must not ConfigFieldTrim(val) — keeps leading space")

    dispatch = extract_function(killer, "DispatchListeners")
    if 'CallFunctionNoWait("SyncFromKillerScanSnapshot"' not in dispatch:
        fail("KillerScan must NoWait DesperateRename SyncFromKillerScanSnapshot")
    if "StartTimer(" in rename:
        fail("DesperateRename must not StartTimer")

    if "desperateNameSuffix=" not in mod:
        fail("ModConfig.txt must ship desperateNameSuffix=")
    if " Dumb Bitch" not in mod and "Dumb Bitch" not in mod:
        fail("ModConfig.txt must set a desperateNameSuffix example")

    esp = ESP.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperDesperateRenameScript" not in esp:
        fail("ESP builder must attach DesperateRename")
    deploy = DEPLOY.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperDesperateRenameScript" not in deploy:
        fail("build-deploy-local must compile/deploy DesperateRename")

    doc = DOC.read_text(encoding="utf-8", errors="replace")
    if "desperateNameSuffix" not in doc:
        fail("SLICE_I doc must document desperateNameSuffix")
    road = ROADMAP.read_text(encoding="utf-8", errors="replace")
    if "SLICE_I_DESPERATE_RENAME" not in road:
        fail("ROADMAP must link Slice I desperate rename")
    if "| **I** | Slow hunger" in road:
        fail("ROADMAP must have shifted old Slice I (slow hunger) off letter I")
    if "Slow hunger stages" not in road or "**J**" not in road:
        fail("ROADMAP must keep slow hunger as Slice J")

    ok("Slice I desperate rename script + ModConfig + KillerScan + toast name")
    print("All desperate-rename (Slice I) contracts passed.")


if __name__ == "__main__":
    main()
