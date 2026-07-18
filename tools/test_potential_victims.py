#!/usr/bin/env python3
"""Contracts for C5 P3+P4 Potential Victims (name ↔ FormID + SetDisplayName).

Locks:
  - VictimIds / VictimNames / VICTIM_MAX = 32
  - GetVictimOverrideName looks up FormID table (not empty stub)
  - ApplyVictimName calls SetDisplayName(..., True) and UpsertVictim
  - GetActorDisplayName prefers override, then GetDisplayName, then base name
  - EnsureVictimDisplayName re-applies when display drifts
  - Optional VictimsHold RefCollectionAlias AddRef when present
  - MCM Victims page + MCMNameAimedVictim / MCMRefreshVictimsPanel
  - RefreshVictimsPanel re-pushes strings AFTER RefreshMenu (settings.ini wipe)
  - ResolveVictimsAimActor uses live aim or last look cache (MCM kills camera target)
  - No StrFind->SubStr index slicing in victim helpers
  - SetDisplayName stub is real F4SE (present); no fake natives

Usage:
  python tools/test_potential_victims.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
MCM_SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
OBJ_STUB = ROOT / "tools" / "stubs" / "ObjectReference.psc"
ALIAS_STUB = ROOT / "tools" / "stubs" / "RefCollectionAlias.psc"


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


def test_psc(text: str) -> None:
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
        "MCMNameAimedVictim",
        "RefreshVictimsPanel",
        "WriteVictimsSummaryToMcm",
    ):
        extract_function(text, name)
    ok("victim helpers present")

    override = extract_function(text, "GetVictimOverrideName")
    if "GetVictimNameByFormId" not in override and "FindVictimSlot" not in override:
        fail("GetVictimOverrideName must look up the FormID table")
    if re.search(r"Return\s+\"\"\s*\nEndFunction", override) and "GetFormID" not in override:
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

    # Ban StrFind index slicing inside victim helpers
    for name in ("ApplyVictimName", "UpsertVictim", "GetVictimOverrideName", "FindVictimSlot"):
        body = extract_function(text, name)
        if "StrFind(" in body and "SubStr(" in body:
            fail(f"{name} must not SubStr using StrFind (count!=index)")
    ok("no StrFind->SubStr in victim core")

    if "MCMNameAimedVictim" not in text:
        fail("MCMNameAimedVictim missing")
    mcm_fn = extract_function(text, "MCMNameAimedVictim")
    if "ResolveVictimsAimActor" not in mcm_fn or "sVictimName:Victims" not in mcm_fn:
        fail("MCMNameAimedVictim must ResolveVictimsAimActor + read sVictimName:Victims")
    ok("MCMNameAimedVictim wired")

    for name in (
        "NoteVictimsAimActor",
        "ResolveVictimsAimActor",
        "PushVictimsPanelStrings",
        "MCMRefreshVictimsPanel",
        "WriteVictimsAimedToMcm",
    ):
        extract_function(text, name)
    refresh = extract_function(text, "RefreshVictimsPanel")
    if "PushVictimsPanelStrings" not in refresh:
        fail("RefreshVictimsPanel must PushVictimsPanelStrings")
    if "MCM.RefreshMenu()" not in refresh:
        fail("RefreshVictimsPanel may RefreshMenu")
    # After RefreshMenu, must re-push (settings.ini wipe) — WriteVictimsAimedToMcm after RefreshMenu
    after = refresh.split("MCM.RefreshMenu()", 1)
    if len(after) < 2 or "WriteVictimsAimedToMcm" not in after[1]:
        fail("RefreshVictimsPanel must re-push aimed strings AFTER RefreshMenu")
    tick = extract_function(text, "TickLookFixation")
    if "NoteVictimsAimActor" not in tick:
        fail("TickLookFixation must NoteVictimsAimActor for MCM cache")
    ok("Victims MCM aim cache + RefreshMenu re-push")


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
    ):
        if needle not in cfg:
            fail(f"Victims MCM missing {needle}")
    if '"function": "RefreshVictimsPanel"' in cfg:
        fail("MCM button must call MCMRefreshVictimsPanel (not RefreshVictimsPanel with Bool)")
    ok("MCM Victims page")
    ini = MCM_SETTINGS.read_text(encoding="utf-8")
    if "[Victims]" not in ini or "sVictimName=" not in ini:
        fail("settings.ini missing [Victims]")
    ok("settings.ini [Victims]")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_stubs()
    test_psc(text)
    test_mcm()
    print("All potential-victims (C5 P3+P4) contracts passed.")


if __name__ == "__main__":
    main()
