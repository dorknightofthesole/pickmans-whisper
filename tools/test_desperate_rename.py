#!/usr/bin/env python3
"""Contracts for Slice I — desperate hunger NPC rename suffix."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = ROOT / "Data" / "Scripts" / "Source" / "User"
MAIN = USER / "PickmansWhisperMainQuestScript.psc"
MODCFG = USER / "PickmansWhisperModConfigScript.psc"
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
    aim = extract_function(rename, "DesperateRename")
    # Feature method is DesperateRename(Actor) — extract_function may hit façade on Main; body is on rename.
    if "Function DesperateRename(Actor akTarget)" not in rename:
        fail("DesperateRenameScript must expose DesperateRename(Actor akTarget)")
    if "GetNoticeStage()" not in aim and "GetNoticeStage()" not in rename:
        fail("DesperateRename must gate on GetNoticeStage")
    if "ApplySuffixToActor(akTarget" not in aim and "ApplySuffixToActor(akTarget, suffix)" not in rename:
        fail("DesperateRename(Actor) must ApplySuffixToActor(akTarget, …) when desperate")
    if "StripSuffixFromActor(akTarget" not in rename:
        fail("DesperateRename(Actor) must StripSuffixFromActor(akTarget, …) when not desperate")
    if re.search(r"^\s*[^;]*\bFindActors\b", rename, re.M):
        fail("DesperateRename must not call FindActors")
    if "SetDisplayName" not in rename or "GardenOfEden2" not in rename:
        fail("DesperateRename must GardenOfEden2.SetDisplayName")
    # Hard gate + living; identity checklist lives on Main.IsValidTarget only.
    elig = extract_function(rename, "IsRenameEligible")
    if "IsValidTarget" not in elig:
        fail("IsRenameEligible must call Main.IsValidTarget (hard gate)")
    if "IsDead" not in elig:
        fail("IsRenameEligible must require living (feature: !IsDead)")
    if "IsHostileToActor" in elig:
        fail("IsRenameEligible must not re-check IsHostileToActor — hard gate + living only")
    if "IsStoryEssential" in elig or "IsChildNpc" in elig or "IsHumanNpc" in elig:
        fail("IsRenameEligible must not duplicate hard-checklist (owned by IsValidTarget)")
    if "ExplainNoticeReject" in rename:
        fail("DesperateRename must not fall back to the shared ambient notice filter")
    if "ModConfigAlias.GetDesperateNameSuffix" not in rename:
        fail("DesperateRename must read suffix via ModConfigAlias")
    maybe = extract_function(rename, "MaybeSuffixDisplayName")
    if "GetNoticeStage() != 4" not in maybe and "GetNoticeStage() == 4" not in maybe:
        fail("MaybeSuffixDisplayName must only suffix at stage 4")

    voice_txt = (USER / "PickmansWhisperVoiceAliasScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    gad = extract_function(voice_txt, "GetActorDisplayName")
    if "MaybeSuffixDisplayName" not in gad:
        fail("GetActorDisplayName must MaybeSuffixDisplayName (toast matches HUD)")
    if "PickmansWhisperDesperateRenameScript Function DesperateRename()" not in main_txt:
        fail("Main must DesperateRename() façade (returns sibling script)")
    looking = extract_function(main_txt, "LookingAtTarget")
    if "DesperateRename()" not in looking:
        fail("LookingAtTarget must resolve DesperateRename() façade like VoiceAlias")
    if "rename.DesperateRename(WhoIsThat)" not in looking:
        fail("LookingAtTarget must rename.DesperateRename(WhoIsThat) (VoiceAlias-style unbound check)")
    if re.search(r"^\s*DesperateRename\s*\(\s*WhoIsThat\s*\)", looking, re.M):
        fail("LookingAtTarget must not call DesperateRename(WhoIsThat) on Main — use façade then method")
    if "ModConfigAlias Auto" not in main_txt:
        fail("Main must expose ModConfigAlias")
    # Leading space preserved — must not ConfigFieldTrim the suffix value.
    modcfg = MODCFG.read_text(encoding="utf-8", errors="replace")
    load = extract_function(modcfg, "LoadModConfig")
    if 'key == "desperateNameSuffix"' not in load:
        fail("LoadModConfig must parse desperateNameSuffix")
    if re.search(
        r'desperateNameSuffix[\s\S]{0,120}ConfigFieldTrim\(val\)',
        load,
    ):
        fail("desperateNameSuffix must not ConfigFieldTrim(val) — keeps leading space")

    dispatch = extract_function(killer, "DispatchListeners")
    if "SyncFromKillerScanSnapshot" in dispatch:
        fail("KillerScan must not SyncFromKillerScanSnapshot — rename is aim-driven via LookingAtTarget")
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
    if "Slow hunger stages" not in road or "| **L** | Slow hunger" not in road:
        fail("ROADMAP must keep slow hunger as Slice L")
    if "| **K** | Victim" not in road:
        fail("ROADMAP must keep victim beat-before-kill as Slice K (after J)")
    if "| **Q** | Private cells" not in road:
        fail("ROADMAP must keep private cells + quests as Slice Q")
    if "| **J** | Retire KillerScan" not in road:
        fail("ROADMAP must list Slice J as retire KillerScan + Alias refactor")

    ok("Slice I desperate rename script + ModConfig + KillerScan + toast name")
    print("All desperate-rename (Slice I) contracts passed.")


if __name__ == "__main__":
    main()
