#!/usr/bin/env python3
"""Contracts for force-trade via Talk activate menu (PERK Add Activate Choice)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRADE = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimTradeScript.psc"
PERK_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimTradePerkScript.psc"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MODCFG_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
MODCFG_TXT = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
ALIAS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
STUB_ACTOR = ROOT / "tools" / "stubs" / "Actor.psc"
STUB_PERK = ROOT / "tools" / "stubs" / "Perk.psc"
PACKAGE = ROOT / "tools" / "package_mo2_zip.py"

FID_PERK = 0x01000878
FID_CHA = 0x000002C5


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
    if not re.search(r"Function\s+OpenInventory\s*\(", actor):
        fail("Actor.psc stub must declare OpenInventory Native")
    if not re.search(r"Function\s+AddPerk\s*\(\s*Perk\s+akPerk", actor):
        fail("Actor.psc stub must declare AddPerk Native")
    if not re.search(r"Function\s+RemovePerk\s*\(\s*Perk\s+akPerk", actor):
        fail("Actor.psc stub must declare RemovePerk Native")
    perk = STUB_PERK.read_text(encoding="utf-8", errors="replace")
    if "Event OnEntryRun" not in perk:
        fail("Perk.psc stub must declare OnEntryRun event")
    ok("stubs: OpenInventory + AddPerk + RemovePerk + Perk.OnEntryRun")


def test_modconfig() -> None:
    txt = MODCFG_TXT.read_text(encoding="utf-8", errors="replace")
    if "victimTradeMinCha=" not in txt:
        fail("ModConfig.txt must ship victimTradeMinCha=")
    psc = MODCFG_PSC.read_text(encoding="utf-8", errors="replace")
    if "VictimTradeMinCha" not in psc:
        fail("ModConfigScript must have VictimTradeMinCha property")
    if 'key == "victimTradeMinCha"' not in psc:
        fail("ModConfigScript must parse victimTradeMinCha")
    getter = extract_function(psc, "GetVictimTradeMinCha")
    if "Return VictimTradeMinCha" not in getter:
        fail("GetVictimTradeMinCha must return VictimTradeMinCha")
    ok("ModConfig victimTradeMinCha SSOT + getter")


def test_trade_script() -> None:
    text = TRADE.read_text(encoding="utf-8", errors="replace")
    if "Scriptname PickmansWhisperVictimTradeScript extends Quest" not in text:
        fail("VictimTradeScript must extend Quest")
    body = extract_function(text, "TryForceVictimTradeFromActivate")
    if "OpenInventory(True)" not in body and "OpenInventory(true)" not in body:
        fail("TryForceVictimTradeFromActivate must call OpenInventory(True) (companion-style; not vendor ShowBarterMenu)")
    if "ShowBarterMenu()" in body:
        fail("must not use ShowBarterMenu — empty panes on non-vendor NPCs")
    if "MaybeForceStripForTrade(akTarget)" not in body:
        fail("trade must MaybeForceStripForTrade before OpenInventory (one-time unlock)")
    if "WasTradeStrippedOnce" not in text or "MarkTradeStrippedOnce" not in text:
        fail("trade must latch one-time strip per NPC so later Force Trades keep her gear")
    if "SetOutfit" not in text or "UnequipAll" not in text:
        fail("trade strip must SetOutfit + UnequipAll (outfit-locked gear)")
    if 'RegisterForMenuOpenCloseEvent("ContainerMenu")' not in text:
        fail("trade must watch ContainerMenu close for slave pacify")
    # Closing must not re-strip — that unequips player-equipped gear.
    close_idx = text.find("Event OnMenuOpenCloseEvent")
    if close_idx < 0:
        fail("missing OnMenuOpenCloseEvent")
    close_body = text[close_idx:]
    if "ForceStripForTrade(ak)" in close_body or "UnequipAll()" in close_body:
        fail("ContainerMenu close must not ForceStrip/UnequipAll (keeps gear player put on her)")
    if "InventoryHasSlaveItem" not in text or "MaybePacifyIfSlaveGear" not in text:
        fail("trade must scan for slave-named inventory and pacify")
    if "PickmansWhisperSlaveryScript" not in text:
        fail("trade slave scan must forward to SlaveryScript SSOT")
    if "MaybeSyncSlaveryAfterTrade" not in text:
        fail("ContainerMenu close must sync slavery after pacify")
    close_idx2 = text.find("Event OnMenuOpenCloseEvent")
    close_body2 = text[close_idx2:] if close_idx2 >= 0 else ""
    if "Utility.Wait" not in close_body2:
        fail("ContainerMenu close must Wait briefly so worn collar indexes settle before slavery sync")
    if "StopCombat()" not in text or "SetAttackActorOnSight(False)" not in text:
        fail("trade pacify must StopCombat + SetAttackActorOnSight(False)")
    if "MaybePacifyIfSlaveGear(ak)" not in text:
        fail("ContainerMenu close must call MaybePacifyIfSlaveGear")
    if "HungerLevel" not in body or "CALM_HUNGER_MAX" not in body:
        fail("trade must gate calm hunger via HungerLevel / CALM_HUNGER_MAX")
    if "GetVictimTradeMinCha()" not in body:
        fail("trade must read GetVictimTradeMinCha() — no hard-coded CHA min in gate")
    if "GetValue(avCha)" not in body:
        fail("trade must read player Charisma ActorValue")
    if "IsValidTarget(akTarget, True)" not in body and "IsValidTarget(akTarget, true)" not in body:
        fail("trade must call IsValidTarget(akTarget, True) so hostiles can Force Trade")
    if "IsDead()" not in body:
        fail("trade must reject dead targets")
    if "Debug.Trace" not in body or "Debug.Notification" not in body:
        fail("trade failures must Trace + Notification (no silent Return)")
    sync = extract_function(text, "SyncTradeActivatePerk")
    if "AddPerk" not in sync or "RemovePerk" not in sync:
        fail("SyncTradeActivatePerk must AddPerk when allowed and RemovePerk when blade drawn")
    if "IsBladeEquipped" not in body:
        fail("trade activate must skip when IsBladeEquipped")
    if f"0x{FID_PERK & 0xFFFFFF:08X}" not in text and "0x00000878" not in text:
        fail("trade script must know local PERK FormID 0x878")
    ok("VictimTradeScript gates + OpenInventory + strip + blade-hides perk")


def test_perk_script() -> None:
    text = PERK_PSC.read_text(encoding="utf-8", errors="replace")
    if "extends Perk" not in text:
        fail("VictimTradePerkScript must extend Perk")
    if "OnEntryRun" not in text:
        fail("perk script must implement OnEntryRun")
    if "TryForceVictimTradeFromActivate" not in text:
        fail("perk OnEntryRun must call TryForceVictimTradeFromActivate")
    if "MainQuest" not in text:
        fail("perk script must bind MainQuest")
    ok("VictimTradePerkScript OnEntryRun -> Main")


def test_main_facade() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")
    facade = extract_function(text, "TryForceVictimTradeFromActivate")
    if "PickmansWhisperVictimTradeScript" not in facade:
        fail("Main façade must cast to VictimTradeScript")
    if "VictimTrade()" not in facade and "as PickmansWhisperVictimTradeScript" not in facade:
        fail("Main façade must resolve VictimTradeScript")
    latch = extract_function(text, "SyncBladeDrawnDebugLatch")
    if "SyncDialogActivatePerks" not in latch:
        fail("SyncBladeDrawnDebugLatch must SyncDialogActivatePerks (hide Trade while blade drawn)")
    sync = extract_function(text, "SyncDialogActivatePerks")
    if "SyncTradeActivatePerk" not in sync:
        fail("SyncDialogActivatePerks must sync Trade perk")
    if "DialogActivateChoicesEnabled" not in sync:
        fail("SyncDialogActivatePerks must require DialogActivateChoicesEnabled toggle")
    if "Function ToggleDialogActivateChoices" not in text:
        fail("Main must ToggleDialogActivateChoices for ] key")
    ok("Main TryForceVictimTradeFromActivate façade + blade perk sync")


def test_no_hotkey() -> None:
    alias = ALIAS.read_text(encoding="utf-8", errors="replace")
    if "KEY_VICTIM_TRADE" in alias or "TryForceVictimTrade" in alias:
        fail("PlayerAlias must not register a trade hotkey (activate choice only)")
    if "KEY_DIALOG_ACTIVATE" not in alias or "ToggleDialogActivateChoices" not in alias:
        fail("PlayerAlias must register ] toggle for Trade/Enslave activate choices")
    trade = TRADE.read_text(encoding="utf-8", errors="replace")
    if "RegisterForKey" in trade:
        fail("VictimTradeScript must not RegisterForKey")
    ok("dialog activate toggle on PlayerAlias; Trade script has no key path")


def test_esp_builder() -> None:
    text = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if f"FID_PERK_VICTIM_TRADE = 0x{FID_PERK:08X}" not in text:
        fail(f"ESP builder must define FID_PERK_VICTIM_TRADE = 0x{FID_PERK:08X}")
    if "PW_VictimTradeActivate" not in text:
        fail("ESP builder must emit PW_VictimTradeActivate EDID")
    if '_activate_choice_entry("Force Trade"' not in text and 'zstr("Force Trade")' not in text:
        fail('ESP builder must set activate label Force Trade')
    if "0e0902" not in text:
        fail("ESP builder must use Activate/Add Activate Choice DATA 0e0902")
    if "2e000000" not in text:
        fail("ESP builder must CTDA GetDead==0 on Force Trade (leave corpses to Cannibal)")
    if "PW_EmptyOutfit" not in text or "FID_OTFT_EMPTY" not in text:
        fail("ESP builder must emit PW_EmptyOutfit OTFT for strip")
    if '"PickmansWhisperVictimTradeScript"' not in text:
        fail("ESP builder must attach VictimTradeScript to Main VMAD")
    if "PickmansWhisperVictimTradePerkScript" not in text:
        fail("ESP builder must attach VictimTradePerkScript to PERK VMAD")
    if "TradeActivatePerk" not in text:
        fail("ESP builder must bind TradeActivatePerk property")
    if "EmptyOutfit" not in text:
        fail("ESP builder must bind EmptyOutfit property")
    if "NEXT_OID = 0x0000087F" not in text:
        fail("ESP builder NEXT_OID must be past slavery PERK / execute MESG / mutilated body records")
    ok("ESP builder PERK Force Trade (living) + empty OTFT + VMAD wiring")


def test_deploy_gate() -> None:
    text = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperVictimTradeScript.psc" not in text:
        fail("build-deploy-local.ps1 must compile VictimTradeScript")
    if "PickmansWhisperVictimTradePerkScript.psc" not in text:
        fail("build-deploy-local.ps1 must compile VictimTradePerkScript")
    if "test_victim_trade.py" not in text:
        fail("build-deploy-local.ps1 must run test_victim_trade.py")
    pkg = PACKAGE.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperVictimTradeScript" not in pkg:
        fail("package_mo2_zip.py must include VictimTradeScript")
    if "PickmansWhisperVictimTradePerkScript" not in pkg:
        fail("package_mo2_zip.py must include VictimTradePerkScript")
    ok("deploy + package gate includes trade scripts + contract")


def main() -> int:
    for path in (TRADE, PERK_PSC, MAIN, MODCFG_PSC, MODCFG_TXT, ESP_BUILDER, DEPLOY_PS1):
        if not path.is_file():
            fail(f"missing {path}")
    test_stubs()
    test_modconfig()
    test_trade_script()
    test_perk_script()
    test_main_facade()
    test_no_hotkey()
    test_esp_builder()
    test_deploy_gate()
    print("All victim-trade contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
