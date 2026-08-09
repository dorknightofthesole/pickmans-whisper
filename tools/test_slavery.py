#!/usr/bin/env python3
"""Contracts for Slavery (enslave follow + slave-gear gate + teammate exception)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLAVERY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperSlaveryScript.psc"
PERK_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperSlaveryPerkScript.psc"
TRADE = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimTradeScript.psc"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MODCFG_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
MODCFG_TXT = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
ALIAS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
STUB_ACTOR = ROOT / "tools" / "stubs" / "Actor.psc"
STUB_FACTION = ROOT / "tools" / "stubs" / "Faction.psc"
PACKAGE = ROOT / "tools" / "package_mo2_zip.py"

FID_PERK = 0x0100087A
FID_COMPANION_FAC = 0x00023C01


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:^\s*(?:Bool|Int|Float|String|Actor|Perk)?\s*)?Function\s+{re.escape(name)}\s*\(",
        text,
        re.M,
    )
    if not m:
        fail(f"missing Function {name}")
    start = m.start()
    end = text.find("\nEndFunction", start)
    if end < 0:
        fail(f"unclosed Function {name}")
    return text[start : end + len("\nEndFunction")]


def test_stubs() -> None:
    actor = STUB_ACTOR.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"Function\s+SetPlayerTeammate\s*\(", actor):
        fail("Actor.psc stub must declare SetPlayerTeammate Native")
    if not re.search(r"Function\s+PathToReference\s*\(", actor):
        fail("Actor.psc stub must declare PathToReference Native")
    if not re.search(r"Function\s+IsInFaction\s*\(", actor):
        fail("Actor.psc stub must declare IsInFaction Native")
    if not re.search(r"Function\s+RemovePerk\s*\(", actor):
        fail("Actor.psc stub must declare RemovePerk Native")
    if "Event OnLocationChange" not in actor:
        fail("Actor.psc stub must declare OnLocationChange")
    if not STUB_FACTION.is_file():
        fail("Faction.psc stub missing")
    ok("stubs: SetPlayerTeammate + PathToReference + IsInFaction + RemovePerk + OnLocationChange + Faction")


def test_modconfig() -> None:
    txt = MODCFG_TXT.read_text(encoding="utf-8", errors="replace")
    if "slaveryMinCha=" not in txt:
        fail("ModConfig.txt must ship slaveryMinCha=")
    psc = MODCFG_PSC.read_text(encoding="utf-8", errors="replace")
    if "SlaveryMinCha" not in psc:
        fail("ModConfigScript must have SlaveryMinCha property")
    if 'key == "slaveryMinCha"' not in psc:
        fail("ModConfigScript must parse slaveryMinCha")
    getter = extract_function(psc, "GetSlaveryMinCha")
    if "Return SlaveryMinCha" not in getter:
        fail("GetSlaveryMinCha must return SlaveryMinCha")
    ok("ModConfig slaveryMinCha SSOT + getter")


def test_slavery_script() -> None:
    text = SLAVERY.read_text(encoding="utf-8", errors="replace")
    if "Scriptname PickmansWhisperSlaveryScript extends Quest" not in text:
        fail("SlaveryScript must extend Quest")
    body = extract_function(text, "InventoryHasSlaveItem")
    if 'GetItemIndexesByName(akTarget, "slave", False' not in body and "GetItemIndexesByName(akTarget, \"slave\", False" not in body:
        fail('InventoryHasSlaveItem must GetItemIndexesByName(..., "slave", False) for worn collars')
    if "GetEquippedItemIndexes" not in body:
        fail("InventoryHasSlaveItem must also check GetEquippedItemIndexes (worn after trade)")
    if "GetNthItemName" not in body:
        fail("InventoryHasSlaveItem must resolve names via GetNthItemName")
    start = extract_function(text, "StartSlavery")
    if "SetPlayerTeammate(True, False, False)" not in start and "SetPlayerTeammate(true, false, false)" not in start:
        fail("StartSlavery must SetPlayerTeammate(True, False, False)")
    if "StartSlaveFollowLoop" not in start:
        fail("StartSlavery must StartSlaveFollowLoop (teammate alone does not path-follow)")
    if "CurrentCompanionFaction" in start or "AddToFaction" in start:
        fail("StartSlavery must not add CurrentCompanionFaction")
    if "SetEssential" in start:
        fail("StartSlavery must not SetEssential")
    if "IsOurSlave" not in text or "GetSlave" not in text:
        fail("slavery must expose IsOurSlave / GetSlave latch")
    if "SyncSlaveryFromSlaveGear" not in text:
        fail("slavery must SyncSlaveryFromSlaveGear for Trade close")
    if "TryEnslaveFromActivate" not in text or "TryFreeSlaveFromActivate" not in text:
        fail("slavery must have Enslave/Free activate paths")
    enslave = extract_function(text, "TryEnslaveFromActivate")
    if "GetSlaveryMinCha()" not in enslave:
        fail("Enslave must read GetSlaveryMinCha()")
    if "InventoryHasSlaveItem" not in enslave:
        fail("Enslave must require slave gear")
    if "IsBladeEquipped" not in enslave:
        fail("Enslave must skip when IsBladeEquipped")
    sync = extract_function(text, "SyncSlaveryActivatePerk")
    if "AddPerk" not in sync or "RemovePerk" not in sync:
        fail("SyncSlaveryActivatePerk must AddPerk when allowed and RemovePerk when blade drawn")
    tick = extract_function(text, "TickSlaveFollow")
    if "PathToReference" not in tick:
        fail("TickSlaveFollow must PathToReference toward player")
    if "MoveTo" not in tick:
        fail("TickSlaveFollow must MoveTo when far/unloaded")
    if "Event OnTimer" not in text or "TIMER_SLAVE_FOLLOW" not in text:
        fail("slavery must OnTimer follow loop")
    sync_gear = extract_function(text, "SyncSlaveryFromSlaveGear")
    if "invCount=0" not in sync_gear and "invCount == 0" not in sync_gear and "n <= 0" not in sync_gear:
        fail("SyncSlaveryFromSlaveGear must not free on invCount=0 GoE lag")
    if "WarpSlaveToPlayerIfNeeded" not in text or "MoveTo" not in text:
        fail("slavery must WarpSlaveToPlayerIfNeeded via MoveTo")
    if "ClearSlave" not in text:
        fail("slavery must ClearSlave")
    if f"0x{FID_PERK & 0xFFFFFF:08X}" not in text and "0x0000087A" not in text:
        fail("slavery script must know local PERK FormID 0x87A")
    if f"0x{FID_COMPANION_FAC:08X}" not in text and "0x00023C01" not in text:
        fail("slavery must know CurrentCompanionFaction 0x23C01")
    ok("SlaveryScript enslave + PathToReference follow loop + slave-gear SSOT")


def test_perk_script() -> None:
    text = PERK_PSC.read_text(encoding="utf-8", errors="replace")
    if "extends Perk" not in text:
        fail("SlaveryPerkScript must extend Perk")
    if "TryEnslaveFromActivate" not in text or "TryFreeSlaveFromActivate" not in text:
        fail("perk must route Enslave and Free by entry id")
    if "auiEntryID" not in text:
        fail("perk must branch on auiEntryID")
    ok("SlaveryPerkScript OnEntryRun -> Main Enslave/Free")


def test_trade_glue() -> None:
    text = TRADE.read_text(encoding="utf-8", errors="replace")
    if "MaybeSyncSlaveryAfterTrade" not in text:
        fail("Trade must call MaybeSyncSlaveryAfterTrade after pacify")
    if "SyncSlaveryFromSlaveGear" not in text:
        fail("Trade glue must call SyncSlaveryFromSlaveGear")
    if 'StrFind(itemName, "slave"' in text:
        fail("Trade must not duplicate slave StrFind — SSOT is SlaveryScript")
    if "PickmansWhisperSlaveryScript" not in text:
        fail("Trade must forward slave scan to SlaveryScript")
    ok("Trade close syncs slavery; slave-item SSOT on Slavery")


def test_main_isvalidtarget() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")
    body = extract_function(text, "IsValidTarget")
    if "IsOurSlave" not in body:
        fail("IsValidTarget must exception our slave for teammate reject")
    if "IsPlayerTeammate" not in body:
        fail("IsValidTarget must still check IsPlayerTeammate")
    if "0x00023C01" not in body and "0x23C01" not in body:
        fail("IsValidTarget must reject CurrentCompanionFaction 0x23C01")
    if "TryEnslaveFromActivate" not in text or "TryFreeSlaveFromActivate" not in text:
        fail("Main must façade Enslave/Free")
    sync = extract_function(text, "SyncDialogActivatePerks")
    if "SyncSlaveryActivatePerk" not in sync:
        fail("SyncDialogActivatePerks must sync Slavery perk")
    ok("IsValidTarget teammate exception + companion faction reject + blade perk sync")


def test_player_alias_warp() -> None:
    text = ALIAS.read_text(encoding="utf-8", errors="replace")
    if "OnLocationChange" not in text:
        fail("PlayerAlias must implement OnLocationChange")
    if 'RegisterForRemoteEvent(p, "OnLocationChange")' not in text:
        fail("PlayerAlias must RegisterForRemoteEvent OnLocationChange")
    if "WarpSlaveToPlayerIfNeeded" not in text:
        fail("PlayerAlias OnLocationChange must call WarpSlaveToPlayerIfNeeded")
    ok("PlayerAlias location change warps slave")


def test_esp_builder() -> None:
    text = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if f"FID_PERK_SLAVERY = 0x{FID_PERK:08X}" not in text:
        fail(f"ESP builder must define FID_PERK_SLAVERY = 0x{FID_PERK:08X}")
    if "PW_SlaveryActivate" not in text:
        fail("ESP builder must emit PW_SlaveryActivate EDID")
    if '_activate_choice_entry("Enslave"' not in text and 'zstr("Enslave")' not in text:
        fail('ESP builder must set activate label Enslave')
    if '_activate_choice_entry("Free"' not in text and 'zstr("Free")' not in text:
        fail('ESP builder must set activate label Free')
    if '"PickmansWhisperSlaveryScript"' not in text:
        fail("ESP builder must attach SlaveryScript to Main VMAD")
    if "PickmansWhisperSlaveryPerkScript" not in text:
        fail("ESP builder must attach SlaveryPerkScript to PERK VMAD")
    if "SlaveryActivatePerk" not in text:
        fail("ESP builder must bind SlaveryActivatePerk property")
    if "NEXT_OID = 0x0000087B" not in text:
        fail("ESP builder NEXT_OID must be past slavery PERK")
    ok("ESP builder PERK Enslave/Free + VMAD wiring")


def test_deploy_gate() -> None:
    text = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperSlaveryScript.psc" not in text:
        fail("build-deploy-local.ps1 must compile SlaveryScript")
    if "PickmansWhisperSlaveryPerkScript.psc" not in text:
        fail("build-deploy-local.ps1 must compile SlaveryPerkScript")
    if "test_slavery.py" not in text:
        fail("build-deploy-local.ps1 must run test_slavery.py")
    pkg = PACKAGE.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperSlaveryScript" not in pkg:
        fail("package_mo2_zip.py must include SlaveryScript")
    if "PickmansWhisperSlaveryPerkScript" not in pkg:
        fail("package_mo2_zip.py must include SlaveryPerkScript")
    ok("deploy + package gate includes slavery scripts + contract")


def main() -> int:
    for path in (SLAVERY, PERK_PSC, TRADE, MAIN, MODCFG_PSC, MODCFG_TXT, ESP_BUILDER, DEPLOY_PS1):
        if not path.is_file():
            fail(f"missing {path}")
    test_stubs()
    test_modconfig()
    test_slavery_script()
    test_perk_script()
    test_trade_glue()
    test_main_isvalidtarget()
    test_player_alias_warp()
    test_esp_builder()
    test_deploy_gate()
    print("All slavery contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
