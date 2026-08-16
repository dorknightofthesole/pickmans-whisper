#!/usr/bin/env python3
"""Contracts for Slavery (enslave follow + slave-gear gate + teammate exception).

The activate-menu "Free" choice was replaced by "Take Her" (Slice U AAF scene,
tools/test_slave_scene.py) — SlaveryScript.TryFreeSlaveFromActivate is unchanged and
still reachable via MainQuestScript's forwarder, just no longer from this PERK; the
direct one-click free path moved to PickmansWhisperVictimsScript.MCMFreeAimedSlave
(MCM Victims page button).
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP = ROOT / "Data" / "PickmansWhisper.esp"
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


def extract_event(text: str, signature_start: str) -> str:
    idx = text.find(signature_start)
    if idx < 0:
        fail(f"missing event {signature_start!r}")
    end_m = re.search(r"\nEndEvent\b", text[idx:])
    if not end_m:
        fail(f"no EndEvent for {signature_start!r}")
    return text[idx : idx + end_m.end()]


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
    if "HungerLevel" in enslave or "CALM_HUNGER_MAX" in enslave:
        fail("Enslave must NOT gate on blade-calm hunger level — that requirement is "
             "Force Trade-only (see tools/test_victim_trade.py)")
    if "CALM_HUNGER_MAX" in text:
        fail("SlaveryScript must not declare an unused CALM_HUNGER_MAX constant")
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
    if "TryEnslaveFromActivate" not in text or "TryStartSlaveSceneFromActivate" not in text:
        fail("perk must route Enslave and Take Her (Slice U scene)")
    if "TryFreeSlaveFromActivate" in text:
        fail("perk must NOT route Free anymore — replaced by Take Her (Slice U); "
             "direct free is now PickmansWhisperVictimsScript.MCMFreeAimedSlave (MCM button)")

    # auiEntryID must be the PRIMARY routing signal now that each entry has a real,
    # distinct EPFB (see test_esp_builder's binary check) — this was a real, confirmed
    # bug: every entry previously shared EPFB=0000, so "Enslave" and "Take Her" always
    # ran the exact same branch regardless of which was clicked. IsOurSlave may only
    # remain as a fallback for an unrecognized auiEntryID, never the primary path.
    entry_evt = extract_event(text, "Event OnEntryRun(Int auiEntryID, ObjectReference akTarget, Actor akOwner)")
    if "auiEntryID == 0" not in entry_evt or "auiEntryID == 1" not in entry_evt:
        fail("OnEntryRun must branch on auiEntryID == 0 (Enslave) and == 1 (Take Her) as "
             "the primary routing — not IsOurSlave state, which conflated the two "
             "(confirmed live: clicking Enslave on an already-owned NPC started an AAF "
             "scene instead of enslaving)")
    m0 = re.search(r"auiEntryID == 0.*?TryEnslaveFromActivate", entry_evt, re.S)
    if not m0 or (m0.end() - m0.start()) > 200:
        fail("auiEntryID == 0 branch must call TryEnslaveFromActivate (close by, not via a distant fallback)")
    m1 = re.search(r"auiEntryID == 1.*?TryStartSlaveSceneFromActivate", entry_evt, re.S)
    if not m1 or (m1.end() - m1.start()) > 200:
        fail("auiEntryID == 1 branch must call TryStartSlaveSceneFromActivate (close by, not via a distant fallback)")
    if "IsOurSlave" not in entry_evt:
        fail("OnEntryRun should still keep IsOurSlave as a fallback for an unrecognized auiEntryID")
    ok("SlaveryPerkScript OnEntryRun routes primarily on auiEntryID (0=Enslave, 1=Take Her), IsOurSlave fallback only")


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
    if "DialogActivateChoicesEnabled" not in sync:
        fail("Slavery activate perk must honor DialogActivateChoicesEnabled toggle")
    ok("IsValidTarget teammate exception + companion faction reject + blade perk sync")


def test_player_alias_warp() -> None:
    text = ALIAS.read_text(encoding="utf-8", errors="replace")
    if "OnLocationChange" not in text:
        fail("PlayerAlias must implement OnLocationChange")
    if 'RegisterForRemoteEvent(p, "OnLocationChange")' not in text:
        fail("PlayerAlias must RegisterForRemoteEvent OnLocationChange")
    if "WarpSlaveToPlayerIfNeeded" not in text:
        fail("PlayerAlias OnLocationChange must call WarpSlaveToPlayerIfNeeded")
    if "KEY_DIALOG_ACTIVATE" not in text or "221" not in text:
        fail("PlayerAlias must bind dialog-activate toggle key VK 221 (])")
    if "ToggleDialogActivateChoices" not in text:
        fail("PlayerAlias OnKeyDown must ToggleDialogActivateChoices")
    ok("PlayerAlias location warp + dialog activate toggle key")


def test_esp_builder() -> None:
    text = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if f"FID_PERK_SLAVERY = 0x{FID_PERK:08X}" not in text:
        fail(f"ESP builder must define FID_PERK_SLAVERY = 0x{FID_PERK:08X}")
    if "PW_SlaveryActivate" not in text:
        fail("ESP builder must emit PW_SlaveryActivate EDID")
    if '_activate_choice_entry("Enslave"' not in text and 'zstr("Enslave")' not in text:
        fail('ESP builder must set activate label Enslave (multi-activate dialog budget)')
    if '_activate_choice_entry("Take Her"' not in text and 'zstr("Take Her")' not in text:
        fail('ESP builder must set activate label "Take Her" (Slice U, replaced Free)')
    if '_activate_choice_entry("Free"' in text or 'zstr("Free")' in text:
        fail('ESP builder must NOT emit a Free activate label anymore — replaced by Take Her (Slice U)')
    if '_activate_choice_entry("Slavery"' in text:
        fail("ESP must not use single Slavery label — breaks multi-activate dialog")
    if '"PickmansWhisperSlaveryScript"' not in text:
        fail("ESP builder must attach SlaveryScript to Main VMAD")
    if "PickmansWhisperSlaveryPerkScript" not in text:
        fail("ESP builder must attach SlaveryPerkScript to PERK VMAD")
    if "SlaveryActivatePerk" not in text:
        fail("ESP builder must bind SlaveryActivatePerk property")
    if "NEXT_OID = 0x0000087C" not in text:
        fail("ESP builder NEXT_OID must be past slavery PERK (and Slice W's execute menu MESG)")
    if "'Perk Entry ID (unique)'" not in text and "Perk Entry ID" not in text:
        fail("_activate_choice_entry must document EPFB as xEdit's 'Perk Entry ID (unique)' "
             "field — this was a real, confirmed bug: every entry sharing EPFB=0000 meant "
             "auiEntryID could never distinguish Enslave from Take Her")
    ok("ESP builder PERK Enslave/Take Her + VMAD wiring")


def test_esp_binary_epfb_unique() -> None:
    """Real binary check, not just source text: parse the built ESP's PW_SlaveryActivate
    PERK record and confirm Enslave and Take Her actually have distinct EPFB values —
    locks in the auiEntryID-routing fix at the byte level, the same way the rest of this
    codebase verifies binary records rather than trusting the builder's own Python logic."""
    if not ESP.is_file():
        fail(f"missing built ESP: {ESP} (run tools/build_hunger_spell_esp.py)")
    data = ESP.read_bytes()
    needle = struct.pack("<I", FID_PERK)
    idx = data.find(needle)
    if idx < 0:
        fail(f"PERK FormID 0x{FID_PERK:08X} not found in built ESP")
    rec_start = data.rfind(b"PERK", 0, idx)
    if rec_start < 0:
        fail("could not locate PERK record header before FormID occurrence")
    size = struct.unpack_from("<I", data, rec_start + 4)[0]
    body = data[rec_start + 24 : rec_start + 24 + size]

    epfb_by_label: dict[str, int] = {}
    off = 0
    pending_epfb = None
    while off + 6 <= len(body):
        tag = body[off : off + 4]
        sz = struct.unpack_from("<H", body, off + 4)[0]
        val = body[off + 6 : off + 6 + sz]
        if tag == b"EPFB":
            if sz != 2:
                fail(f"EPFB field must be 2 bytes (u16), got {sz}")
            pending_epfb = struct.unpack("<H", val)[0]
        elif tag == b"EPF2":
            label = val.split(b"\x00", 1)[0].decode("ascii", "replace")
            if pending_epfb is None:
                fail(f"EPF2 label {label!r} had no preceding EPFB field")
            epfb_by_label[label] = pending_epfb
            pending_epfb = None
        off += 6 + sz

    if "Enslave" not in epfb_by_label or "Take Her" not in epfb_by_label:
        fail(f"expected EPF2 labels 'Enslave' and 'Take Her' in PW_SlaveryActivate, found {list(epfb_by_label)}")
    if epfb_by_label["Enslave"] == epfb_by_label["Take Her"]:
        fail(f"Enslave and Take Her share EPFB={epfb_by_label['Enslave']} — auiEntryID cannot "
             f"distinguish them, reintroducing the exact bug that made clicking Enslave start an AAF scene")
    ok(f"built ESP: Enslave EPFB={epfb_by_label['Enslave']}, Take Her EPFB={epfb_by_label['Take Her']} (distinct)")


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
    test_esp_binary_epfb_unique()
    test_deploy_gate()
    print("All slavery contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
