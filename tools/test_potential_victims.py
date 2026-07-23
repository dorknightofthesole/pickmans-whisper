#!/usr/bin/env python3
"""Contracts for C5 P3+P4 Potential Victims (name ↔ FormID + SetDisplayName).

Locks:
  - VictimIds / VictimNames / VICTIM_MAX = 32 on Main
  - GetVictimOverrideName looks up the FormID table (not empty stub)
  - ApplyVictimName calls SetDisplayName(..., True) and UpsertVictim
  - GetActorDisplayName prefers override, then GetDisplayName, then base name
  - EnsureVictimDisplayName re-applies when display drifts
  - Optional VictimsHold RefCollectionAlias AddRef when present
  - MCM Victims CallFunctions target PickmansWhisperVictimsScript (own lock)
  - Aim cache + Refresh / Name / Advance bodies on VictimsScript
  - Main keeps thin façades for internal callers
  - No StrFind->SubStr index slicing in victim helpers
  - SetDisplayName stub is real F4SE (present); no fake natives

Usage:
  python tools/test_potential_victims.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
VICTIMS_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimsScript.psc"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
MCM_SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
OBJ_STUB = ROOT / "tools" / "stubs" / "ObjectReference.psc"
ALIAS_STUB = ROOT / "tools" / "stubs" / "RefCollectionAlias.psc"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Function|Bool Function|Int Function|String Function|Actor Function)\s+{name}\s*\(",
        text,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
    return text[start : start + end_m.end()]


def test_stubs() -> None:
    obj = OBJ_STUB.read_text(encoding="utf-8")
    if "Function SetDisplayName" not in obj:
        fail("ObjectReference.psc must declare F4SE SetDisplayName")
    if "Native" not in obj.split("SetDisplayName")[1][:80]:
        fail("SetDisplayName must be Native")
    ok("SetDisplayName stub present")
    if not ALIAS_STUB.is_file():
        fail("missing RefCollectionAlias.psc stub")
    alias = ALIAS_STUB.read_text(encoding="utf-8")
    for fn in ("AddRef", "Find", "GetAt", "GetCount"):
        if f"Function {fn}" not in alias:
            fail(f"RefCollectionAlias stub missing {fn}")
    ok("RefCollectionAlias stub present")


def test_main_naming(text: str) -> None:
    if "VICTIM_MAX = 32" not in text and "VICTIM_MAX=32" not in text:
        fail("VICTIM_MAX must be 32")
    ok("VICTIM_MAX = 32")

    for name in (
        "EnsureVictimLists",
        "FindVictimSlot",
        "GetVictimNameByFormId",
        "GetVictimOverrideName",
        "UpsertVictim",
        "HoldVictimRef",
        "EnsureVictimDisplayName",
        "ApplyVictimName",
        "WriteVictimsSummaryToMcm",
        "CountVictimNameOccurrences",
        "VictimNameAlreadyListed",
        "Victims",
    ):
        extract_function(text, name)
    ok("victim helpers present on Main")

    summary = extract_function(text, "WriteVictimsSummaryToMcm")
    if "CountVictimNameOccurrences" not in summary or "VictimNameAlreadyListed" not in summary:
        fail("WriteVictimsSummaryToMcm must collapse duplicate names (Leslie x2)")
    if '" x"' not in summary and " x" not in summary:
        fail("WriteVictimsSummaryToMcm must append xN for duplicate names")
    # Pure mirror: two FormIDs named Leslie -> one "Leslie x2" row.
    names = ["Cindy", "Jane", "Leslie", "Leslie"]
    rows: list[str] = []
    for i, n in enumerate(names):
        if any(names[j] == n for j in range(i)):
            continue
        copies = sum(1 for x in names if x == n)
        rows.append(f"{n} x{copies}" if copies > 1 else n)
    if "; ".join(rows) != "Cindy; Jane; Leslie x2":
        fail(f"named-victims summary mirror wrong: {rows}")
    ok("WriteVictimsSummary collapses duplicate names")

    if "as PickmansWhisperVictimsScript" not in extract_function(text, "Victims"):
        fail("Main Victims() must cast to PickmansWhisperVictimsScript")
    ok("Main Victims() cast")

    override = extract_function(text, "GetVictimOverrideName")
    if "GetVictimNameByFormId" not in override and "FindVictimSlot" not in override:
        fail("GetVictimOverrideName must look up the FormID table")
    if re.search(r'Return\s+""\s*\nEndFunction', override) and "GetFormID" not in override:
        fail("GetVictimOverrideName must not remain an empty stub")
    ok("GetVictimOverrideName uses FormID table")

    apply = extract_function(text, "ApplyVictimName")
    if "SetDisplayName" not in apply:
        fail("ApplyVictimName must call SetDisplayName")
    if "SetDisplayName(useName, True)" not in apply and "SetDisplayName(useName,True)" not in apply:
        fail("ApplyVictimName must SetDisplayName(..., True) to force alias overwrite")
    if "UpsertVictim" not in apply:
        fail("ApplyVictimName must UpsertVictim")
    if "HoldVictimRef" not in apply:
        fail("ApplyVictimName must HoldVictimRef (optional alias)")
    if "IsUsableWhisperName" not in apply:
        fail("ApplyVictimName must reject unusable names")
    ok("ApplyVictimName SetDisplayName + store")

    get_name = extract_function(text, "GetActorDisplayName")
    if "GetVictimOverrideName" not in get_name:
        fail("GetActorDisplayName must check GetVictimOverrideName first")
    if "GetDisplayName()" not in get_name:
        fail("GetActorDisplayName must try F4SE GetDisplayName")
    if "EnsureVictimDisplayName" not in get_name:
        fail("GetActorDisplayName must EnsureVictimDisplayName for overrides (load re-apply)")
    ok("GetActorDisplayName override -> GetDisplayName -> base")

    ensure = extract_function(text, "EnsureVictimDisplayName")
    if "SetDisplayName" not in ensure:
        fail("EnsureVictimDisplayName must SetDisplayName when drifted")
    ok("EnsureVictimDisplayName re-applies")

    hold = extract_function(text, "HoldVictimRef")
    if "VictimsHold" not in hold or "AddRef" not in hold:
        fail("HoldVictimRef must AddRef on VictimsHold when present")
    ok("HoldVictimRef optional alias")

    if "RefCollectionAlias Property VictimsHold" not in text:
        fail("VictimsHold RefCollectionAlias property missing")
    ok("VictimsHold property declared")

    for name in ("ApplyVictimName", "UpsertVictim", "GetVictimOverrideName", "FindVictimSlot"):
        body = extract_function(text, name)
        if "StrFind(" in body and "SubStr(" in body:
            fail(f"{name} must not SubStr using StrFind (count!=index)")
    ok("no StrFind->SubStr in victim core")

    # Main façades must forward to VictimsScript
    for name in (
        "NoteVictimsAimActor",
        "ResolveVictimsAimActor",
        "PushVictimsPanelStrings",
        "RefreshVictimsPanel",
        "MCMRefreshVictimsPanel",
        "MCMNameAimedVictim",
        "MCMAdvanceAimedDecayStage",
        "MCMApplyAimedDecayStage",
        "MCMResetAimedDecayKillClock",
        "TickVictimsAimCache",
    ):
        body = extract_function(text, name)
        if "Victims()" not in body:
            fail(f"Main {name} must façade via Victims()")
    ok("Main Victims façades present")

    if "WriteDecayStageStatusToMcmForActor" not in text:
        fail("Main must WriteDecayStageStatusToMcmForActor (deadlock-safe Push)")
    if "WriteVictimsMcmAuxRows" not in text:
        fail("Main must WriteVictimsMcmAuxRows (NoWait from Victims Refresh)")
    if "FormatNoAimVictimsAimLine" not in text:
        fail("Main must FormatNoAimVictimsAimLine")
    if "Int TIMER_DECAY_ADVANCE" not in text:
        fail("Main must keep TIMER_DECAY_ADVANCE declared (save OnTimer compatibility)")
    ok("Main Victims helpers for Push")

    aim = extract_function(text, "OnWorldScanVictimsAim")
    if "NoteVictimsAimActor" not in aim:
        fail("OnWorldScanVictimsAim must NoteVictimsAimActor")
    knife_fn = extract_function(text, "HandleWorldScanKnifeAimWarm")
    if "OnWorldScanVictimsAim" not in knife_fn:
        fail("HandleWorldScanKnifeAimWarm must OnWorldScanVictimsAim")
    knife = extract_function(text, "ProcessKnifeKill")
    if "NoteVictimsAimActor" not in knife:
        fail("ProcessKnifeKill must NoteVictimsAimActor for Victims/decay MCM")
    dbg = extract_function(text, "RefreshDebugStatus")
    after_dbg = dbg.split("MCM.RefreshMenu()", 1)
    if len(after_dbg) < 2 or "PushVictimsPanelStrings" not in after_dbg[-1]:
        fail("RefreshDebugStatus must PushVictimsPanelStrings AFTER RefreshMenu (Victims wipe)")
    ok("WorldScan / knife / Debug Victims wiring")


def test_victims_script(victims: str) -> None:
    if "Scriptname PickmansWhisperVictimsScript extends Quest" not in victims:
        fail("missing PickmansWhisperVictimsScript")
    for name in (
        "NoteVictimsAimActor",
        "ResolveVictimsAimActor",
        "PushVictimsPanelStrings",
        "RefreshVictimsPanel",
        "MCMRefreshVictimsPanel",
        "MCMNameAimedVictim",
        "MCMAdvanceAimedDecayStage",
        "MCMApplyAimedDecayStage",
        "MCMResetAimedDecayKillClock",
        "ResetAimedDecayKillClock",
        "QueueAimedDecayAdvance",
        "QueueAimedDecayStage",
        "PrepAimedDecayStage",
        "RunPendingDecayAdvance",
        "TickVictimsAimCache",
        "WriteVictimsAimedToMcm",
    ):
        extract_function(victims, name)
    ok("VictimsScript MCM + aim surface")

    resolve = extract_function(victims, "ResolveVictimsAimActor")
    if "GetFacedSeverCorpse(" in resolve or "FindActors(" in resolve:
        fail("ResolveVictimsAimActor must not call FindActors/GetFacedSeverCorpse")
    if "ResolveSeverCorpseAim(" in resolve:
        fail("ResolveVictimsAimActor must not call ResolveSeverCorpseAim")
    if "GetLiveAimActor" not in resolve or "LastVictimsAimActor" not in resolve:
        fail("ResolveVictimsAimActor must use GetLiveAimActor + LastVictimsAimActor cache")
    live = extract_function(victims, "GetLiveAimActor")
    if "GetCameraTargetReference" not in live:
        fail("GetLiveAimActor must use GardenOfEden3.GetCameraTargetReference")
    if "GetLastActivateTargetRef" not in live:
        fail("GetLiveAimActor must fall back to GetLastActivateTargetRef")
    if "Main()" in live or "GetLookAimActor" in live:
        fail("GetLiveAimActor must not call Main (Refresh hung waiting on Main lock)")
    ok("ResolveVictimsAimActor cheap cache (no Main)")

    cache = extract_function(victims, "TickVictimsAimCache")
    if "GetLiveAimActor" not in cache:
        fail("TickVictimsAimCache must use GetLiveAimActor")
    if "IsFixationEligible" in cache:
        fail("TickVictimsAimCache must not gate on IsFixationEligible")
    ok("TickVictimsAimCache via GetLiveAimActor")

    refresh = extract_function(victims, "RefreshVictimsPanel")
    if "PushVictimsAimedOnly" not in refresh:
        fail("RefreshVictimsPanel must PushVictimsAimedOnly")
    after = refresh.split("MCM.RefreshMenu()", 1)
    if len(after) < 2 or "PushVictimsAimedOnly" not in after[1]:
        fail("RefreshVictimsPanel must re-push aimed AFTER RefreshMenu")
    ok("RefreshVictimsPanel re-push")

    push = extract_function(victims, "PushVictimsPanelStrings")
    if "PushVictimsAimedOnly" not in push:
        fail("PushVictimsPanelStrings must PushVictimsAimedOnly first")
    if "WriteVictimsMcmAuxRows" not in push:
        fail("PushVictimsPanelStrings must CallFunctionNoWait WriteVictimsMcmAuxRows")
    if "WriteDecayStageStatusToMcm()" in push:
        fail("PushVictimsPanelStrings must not call WriteDecayStageStatusToMcm() (deadlock)")
    aimed_only = extract_function(victims, "PushVictimsAimedOnly")
    if "Main()" in aimed_only:
        fail("PushVictimsAimedOnly must not call Main (Refresh hung waiting on Main)")
    ok("Push deadlock-safe (aimed local; Main aux NoWait)")

    mcm_refresh = extract_function(victims, "MCMRefreshVictimsPanel")
    if "MessageBox" not in mcm_refresh:
        fail("MCMRefreshVictimsPanel must MessageBox")
    if "Debug.Notification" not in mcm_refresh:
        fail("MCMRefreshVictimsPanel must Notification immediately")
    if "PushVictimsAimedOnly" not in mcm_refresh:
        fail("MCMRefreshVictimsPanel must PushVictimsAimedOnly (not Main-bound Push)")
    note_i = mcm_refresh.find("Debug.Notification")
    box_i = mcm_refresh.find("Debug.MessageBox")
    if note_i < 0 or box_i < 0 or note_i > box_i:
        fail("MCMRefreshVictimsPanel must Notification before MessageBox")
    if "FindActors(" in mcm_refresh:
        fail("MCMRefreshVictimsPanel must not FindActors")
    if "NoteFromWorldScanSnapshot" not in victims:
        fail("VictimsScript must NoteFromWorldScanSnapshot")
    world = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperWorldScanScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    dispatch = extract_function(world, "DispatchListeners")
    if "NoteFromWorldScanSnapshot" not in dispatch:
        fail("WorldScan DispatchListeners must CallFunctionNoWait NoteFromWorldScanSnapshot")
    ok("MCMRefreshVictimsPanel entry + WorldScan aim NoWait")

    mcm_fn = extract_function(victims, "MCMNameAimedVictim")
    if "ResolveVictimsAimActor" not in mcm_fn or "sVictimName:Victims" not in mcm_fn:
        fail("MCMNameAimedVictim must ResolveVictimsAimActor + read sVictimName:Victims")
    ok("MCMNameAimedVictim wired")

    if "TIMER_DECAY_ADVANCE" not in victims:
        fail("VictimsScript must declare TIMER_DECAY_ADVANCE")
    if "aiTimerID == TIMER_DECAY_ADVANCE" not in victims:
        fail("VictimsScript OnTimer must handle TIMER_DECAY_ADVANCE")
    idx = victims.find("aiTimerID == TIMER_DECAY_ADVANCE")
    if idx < 0 or "RunPendingDecayAdvance()" not in victims[idx : idx + 200]:
        fail("Victims OnTimer TIMER_DECAY_ADVANCE must RunPendingDecayAdvance()")
    ok("Victims decay advance timer")


def test_mcm() -> None:
    cfg = MCM_CONFIG.read_text(encoding="utf-8")
    if '"pageDisplayName": "Victims"' not in cfg:
        fail("config.json missing Victims page")
    for needle in (
        '"id": "sVictimName:Victims"',
        '"id": "sVictimAimed:Victims"',
        '"id": "sVictimsSummary:Victims"',
        '"function": "MCMNameAimedVictim"',
        '"function": "MCMRefreshVictimsPanel"',
        '"function": "MCMApplyAimedDecayStage"',
        '"function": "MCMResetAimedDecayKillClock"',
        '"id": "iVictimDecayStage:Victims"',
        "Load targeted corpse",
        "Apply name",
        "Set decay stage",
        "Reset decay stage",
        "Pick stage",
        '"text": "Corpse"',
        '"text": "Name / rename"',
        '"text": "Decay stage options"',
        '"scriptName": "PickmansWhisperVictimsScript"',
        "CallGlobalFunction",
        "MCM PING",
    ):
        if needle not in cfg:
            fail(f"Victims MCM missing {needle}")
    if "Refresh aimed / list" in cfg:
        fail("Victims MCM must rename Refresh aimed / list -> Load targeted corpse")
    if "Name aimed NPC" in cfg:
        fail("Victims MCM must rename Name aimed NPC -> Apply name")
    if "Set decay clock" in cfg:
        fail("Victims MCM must rename Set decay clock -> Set decay stage")
    if "Reset kill clock" in cfg:
        fail("Victims MCM must rename Reset kill clock -> Reset decay stage")
    if '"function": "RefreshVictimsPanel"' in cfg:
        fail("MCM button must call MCMRefreshVictimsPanel (not RefreshVictimsPanel with Bool)")
    # Page order: Corpse (fields then Load) → Name (field then Apply) → Decay
    # (Pick stage stepper, then Set decay stage, then Reset decay stage).
    victims_page = cfg.split('"pageDisplayName": "Victims"', 1)[1].split(
        '"pageDisplayName":', 1
    )[0]
    order = [
        ('"text": "Corpse"', "Corpse section"),
        ('"id": "sVictimAimed:Victims"', "Aimed now"),
        ('"id": "sDecayStage:Victims"', "Decay stage (current)"),
        ('"id": "sVictimsSummary:Victims"', "Named victims"),
        ('"function": "MCMRefreshVictimsPanel"', "Load targeted corpse"),
        ('"text": "Name / rename"', "Name / rename section"),
        ('"id": "sVictimName:Victims"', "New name"),
        ('"function": "MCMNameAimedVictim"', "Apply name"),
        ('"text": "Decay stage options"', "Decay stage options section"),
        ('"id": "iVictimDecayStage:Victims"', "Pick stage stepper"),
        ('"function": "MCMApplyAimedDecayStage"', "Set decay stage"),
        ('"function": "MCMResetAimedDecayKillClock"', "Reset decay stage"),
    ]
    last = -1
    for needle, label in order:
        idx = victims_page.find(needle)
        if idx < 0:
            fail(f"Victims page missing {label} ({needle})")
        if idx < last:
            fail(f"Victims page order wrong: {label} must come after prior section items")
        last = idx
    # Load button must sit after Named victims (not between Aimed and Last apply).
    load_idx = victims_page.find('"function": "MCMRefreshVictimsPanel"')
    summary_idx = victims_page.find('"id": "sVictimsSummary:Victims"')
    aimed_idx = victims_page.find('"id": "sVictimAimed:Victims"')
    if not (aimed_idx < summary_idx < load_idx):
        fail("Load targeted corpse must come after Aimed + Named victims fields")
    apply_idx = victims_page.find('"function": "MCMApplyAimedDecayStage"')
    reset_idx = victims_page.find('"function": "MCMResetAimedDecayKillClock"')
    if apply_idx < 0 or reset_idx < 0 or apply_idx >= reset_idx:
        fail("Set decay stage button must be a separate button above Reset decay stage")
    # Help text quotes button names.
    for quoted in (
        '\\"Load targeted corpse\\"',
        '\\"Apply name\\"',
        '\\"Set decay stage\\"',
        '\\"Reset decay stage\\"',
    ):
        if quoted not in victims_page:
            fail(f"Victims help text must quote button name {quoted}")
    if "several seconds" not in victims_page:
        fail("Victims decay help must mention several seconds for overlays")

    data = json.loads(cfg)
    missing_script = 0
    victims_buttons = 0
    for page in data.get("pages", []):
        for item in page.get("content", []):
            action = item.get("action") if isinstance(item, dict) else None
            if not action or action.get("type") != "CallFunction":
                continue
            if action.get("form") != "PickmansWhisper.esp|800":
                continue
            if not action.get("scriptName"):
                missing_script += 1
            fn = action.get("function")
            if fn in (
                "MCMNameAimedVictim",
                "MCMRefreshVictimsPanel",
                "MCMApplyAimedDecayStage",
                "MCMResetAimedDecayKillClock",
            ):
                victims_buttons += 1
                if action.get("scriptName") != "PickmansWhisperVictimsScript":
                    fail(f"{fn} must use scriptName PickmansWhisperVictimsScript")
    if missing_script:
        fail(f"{missing_script} CallFunction actions missing scriptName (multi-script quest)")
    if victims_buttons < 4:
        fail("Victims page must wire Load / Apply name / Set / Reset to VictimsScript")
    ok("MCM Victims page targets VictimsScript")

    main = PSC.read_text(encoding="utf-8", errors="replace")
    if "Function MCMQuestPing(" not in main:
        fail("Main must MCMQuestPing for Debug quest CallFunction test")
    ok("MCMQuestPing on Main")

    ini = MCM_SETTINGS.read_text(encoding="utf-8")
    if "[Victims]" not in ini or "sVictimName=" not in ini:
        fail("settings.ini missing [Victims]")
    ok("settings.ini [Victims]")


def test_build_wiring() -> None:
    esp = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperVictimsScript" not in esp:
        fail("build_hunger_spell_esp.py must attach PickmansWhisperVictimsScript")
    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperVictimsScript" not in deploy:
        fail("build-deploy-local.ps1 must compile/deploy VictimsScript")
    ok("ESP + deploy include VictimsScript")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    if not VICTIMS_PSC.is_file():
        fail(f"missing {VICTIMS_PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    victims = VICTIMS_PSC.read_text(encoding="utf-8", errors="replace")
    test_stubs()
    test_main_naming(text)
    test_victims_script(victims)
    test_mcm()
    test_build_wiring()
    print("All potential-victims (C5 P3+P4) contracts passed.")


if __name__ == "__main__":
    main()
