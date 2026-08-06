#!/usr/bin/env python3
"""Contracts for Slice J — victim beat-before-kill (temp essential).

J1: manual MCM Victims toggle (dialog-free). J2: automatic trigger when the player
enters combat unarmed against an eligible NPC. J5: cleared ONLY on weapon-equip.

Design:
  - PickmansWhisperBeatBeforeKillScript tracks Actor refs it has personally set
    essential=True on (EssentialActors/EssentialCount) via two shared, UI-free helpers,
    AddEssentialTracked/RemoveEssentialTracked, used by both J1's manual toggle and
    J2's auto trigger. Turning essential ON requires passing MainQuestScript.IsValidTarget
    (same gate as knife-kill crediting — human, adult female, not essential/child/
    teammate, seen non-hostile, alive). Turning it back OFF only requires being in that
    tracked list — since IsValidTarget already refuses anyone currently essential,
    nothing not set by this script can ever appear there, so removal never touches an
    NPC essential for any other reason.
  - J2 auto trigger reuses the EXISTING Actor.OnCombatStateChanged remote handler on
    MainQuestScript (already registered on the player for TrackLivingNear) rather than
    adding new registration. aeCombatState: 0=not in combat, 1=in combat (verified
    against the real FO4 Actor.psc doc comment). State 1 -> apply (if unarmed + blade
    owned + eligible).
  - REMOVED — "out of combat -> clear" (both the direct aeCombatState==0 handler and
    TickEssentialReconcile's !IsInCombat() check): confirmed live in the Papyrus log
    that the reconcile poll stripped essential ~3s after an MCM toggle, before combat
    even started, because "not currently fighting" raced with the exact moment an
    essential actor "survives" lethal damage and collapses (combat state can flip to
    not-in-combat as PART of that same moment). Weapon-equip is the only reversal now.
  - J5 weapon-equip reversal hooks the EXISTING Actor.OnItemEquipped handler, clearing
    ALL tracked actors (not just one) on ANY weapon equip, Pickman's Blade included.
  - The debug dialog (Debug.MessageBox) is scoped to the AUTOMATIC path only —
    OnPlayerEnterCombatWith and ClearAllEssentialOnWeaponEquip call it explicitly.
    AddEssentialTracked/RemoveEssentialTracked stay UI-free so J1's MCM toggle (which
    has its own status-row feedback) never triggers a dialog.
  - TickEssentialReconcile is an ambient KillerScan-dispatched safety net (no StartTimer
    of its own) that ONLY re-checks player weapon state — not combat state.
  - MCM button/status row lives on the Victims page (targets PickmansWhisperVictimsScript,
    matching every other Victims MCM action).

Usage:
  python tools/test_beat_before_kill.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEAT = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperBeatBeforeKillScript.psc"
VICTIMS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimsScript.psc"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
KILLER_SCAN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillerScanScript.psc"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
MCM_SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
SETTINGS_LEGACY = ROOT / "Data" / "MCM" / "Settings" / "PickmansWhisper.ini"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"


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


def extract_event(text: str, signature_start: str) -> str:
    idx = text.find(signature_start)
    if idx < 0:
        fail(f"missing event {signature_start!r}")
    end_m = re.search(r"\nEndEvent\b", text[idx:])
    if not end_m:
        fail(f"no EndEvent for {signature_start!r}")
    return text[idx : idx + end_m.end()]


def test_tracking_core() -> None:
    if not BEAT.is_file():
        fail(f"missing {BEAT}")
    text = BEAT.read_text(encoding="utf-8", errors="replace")
    if "extends Quest" not in text.splitlines()[0]:
        fail("PickmansWhisperBeatBeforeKillScript must extend Quest (attached to Main quest VMAD)")
    if "StartTimer(" in text:
        fail("BeatBeforeKillScript must not StartTimer (Killer Orchestrator) — driven by native events + KillerScan dispatch only")
    if "Actor[] EssentialActors" not in text:
        fail("BeatBeforeKillScript must track Actor refs directly (EssentialActors), not just FormIDs — weapon-equip/reconcile sweeps need live refs")

    add_fn = extract_function(text, "AddEssentialTracked")
    if "ak.SetEssential(True)" not in add_fn:
        fail("AddEssentialTracked must SetEssential(True)")
    remove_fn = extract_function(text, "RemoveEssentialTracked")
    if "ak.SetEssential(False)" not in remove_fn:
        fail("RemoveEssentialTracked must SetEssential(False)")
    if "FindEssentialSlot(ak)" not in remove_fn:
        fail("RemoveEssentialTracked must only act on tracked actors (FindEssentialSlot)")

    ok("BeatBeforeKillScript shared Add/RemoveEssentialTracked helpers")


def test_manual_toggle() -> None:
    text = BEAT.read_text(encoding="utf-8", errors="replace")
    toggle = extract_function(text, "ToggleEssentialForAimed")
    if "FindEssentialSlot(ak)" not in toggle:
        fail("ToggleEssentialForAimed must check the tracked list via FindEssentialSlot")
    if "RemoveEssentialTracked(ak)" not in toggle:
        fail("ToggleEssentialForAimed off-path must use the shared RemoveEssentialTracked helper")
    if "AddEssentialTracked(ak)" not in toggle:
        fail("ToggleEssentialForAimed on-path must use the shared AddEssentialTracked helper")
    if "m.IsValidTarget(ak)" not in toggle:
        fail("ToggleEssentialForAimed must gate the ON path on IsValidTarget(ak)")
    if "ak.IsDead()" not in toggle:
        fail("ToggleEssentialForAimed ON path must require living (feature: !IsDead)")
    if "WasFriendlySeen(ak)" not in toggle:
        fail("ToggleEssentialForAimed ON path must require WasFriendlySeen (knife feature)")

    # Ordering: the off-path (tracked-list check) must come BEFORE the eligibility gate,
    # so removing essential from an already-tracked NPC never gets blocked by her now
    # being essential (which would always fail IsValidTarget).
    off_idx = toggle.find("FindEssentialSlot(ak)")
    gate_idx = toggle.find("IsValidTarget(ak)")
    if off_idx < 0 or gate_idx < 0 or off_idx > gate_idx:
        fail("ToggleEssentialForAimed must check the tracked list BEFORE the IsValidTarget gate (removal must not be blocked by her being essential)")

    if "EssentialCount >= ESSENTIAL_MAX" not in toggle:
        fail("ToggleEssentialForAimed must cap the tracked list (ESSENTIAL_MAX)")

    ok("BeatBeforeKillScript.ToggleEssentialForAimed (J1): track-first removal, gated addition, capped list")


def test_auto_trigger() -> None:
    text = BEAT.read_text(encoding="utf-8", errors="replace")

    # The two shared helpers must stay UI-free — J1's MCM path relies on that (its own
    # status row is its feedback); only the automatic path shows a dialog, and only by
    # calling ToastEssentialChange explicitly itself.
    for fn_name in ("AddEssentialTracked", "RemoveEssentialTracked"):
        fn = extract_function(text, fn_name)
        if "ToastEssentialChange" in fn:
            fail(f"{fn_name} must NOT call ToastEssentialChange — it must stay UI-free so J1's MCM toggle doesn't get a dialog")

    enter = extract_function(text, "OnPlayerEnterCombatWith")
    if "FindEssentialSlot(target)" not in enter:
        fail("OnPlayerEnterCombatWith must skip if already tracked")
    if "player.GetEquippedWeapon(0)" not in enter:
        fail("OnPlayerEnterCombatWith must check the player is unarmed (fists only)")
    if "m.PlayerHasBlade()" not in enter:
        fail("OnPlayerEnterCombatWith must hard-require PlayerHasBlade() (no blade owned = no beat-before-kill fantasy)")
    if "m.IsValidTarget(target)" not in enter:
        fail("OnPlayerEnterCombatWith must gate on IsValidTarget(target)")
    if "target.IsDead()" not in enter:
        fail("OnPlayerEnterCombatWith must require living (feature: !IsDead)")
    if "WasFriendlySeen(target)" not in enter:
        fail("OnPlayerEnterCombatWith must require WasFriendlySeen (knife feature)")
    if "AddEssentialTracked(target)" not in enter:
        fail("OnPlayerEnterCombatWith must call AddEssentialTracked(target) on success")
    if "EssentialCount >= ESSENTIAL_MAX" not in enter:
        fail("OnPlayerEnterCombatWith must respect the tracked-list cap")
    if "ToastEssentialChange(target, True)" not in enter:
        fail("OnPlayerEnterCombatWith must explicitly call ToastEssentialChange(target, True) after applying (auto path shows the dialog)")

    if "Function OnPlayerExitCombatWith" in text:
        fail("OnPlayerExitCombatWith must be removed — 'out of combat' reversal raced with an essential actor's own protected-collapse moment (confirmed live) and is gone for good, not just unused")

    clear_all = extract_function(text, "ClearAllEssentialOnWeaponEquip")
    if "RemoveEssentialTracked(ak)" not in clear_all:
        fail("ClearAllEssentialOnWeaponEquip must route through the shared RemoveEssentialTracked helper for every tracked actor")
    if "ToastEssentialChange(ak, False)" not in clear_all:
        fail("ClearAllEssentialOnWeaponEquip must explicitly call ToastEssentialChange(ak, False) per actor (auto path shows the dialog)")

    toast = extract_function(text, "ToastEssentialChange")
    if "Debug.MessageBox" not in toast:
        fail("ToastEssentialChange must Debug.MessageBox (blocking dialog, requires OK click — a toast was confirmed firing but easy to miss during combat)")
    if "VoiceAlias.GetActorDisplayName(ak)" not in toast and "GetActorDisplayName(ak)" not in toast:
        fail("ToastEssentialChange must resolve her name via VoiceAlias.GetActorDisplayName (Victim override -> world name -> base)")
    if "ESSENTIAL" not in toast or "NOT essential" not in toast:
        fail("ToastEssentialChange must say which state she's changing TO, both directions")
    if "ak.IsEssential() != abNowEssential" not in toast:
        fail("ToastEssentialChange must cross-check ak.IsEssential() against the intended state (ground truth, not just what we asked for)")

    reconcile = extract_function(text, "TickEssentialReconcile")
    if "EssentialCount <= 0" not in reconcile:
        fail("TickEssentialReconcile must no-op cheaply when nothing is tracked")
    if "GetEquippedWeapon(0)" not in reconcile:
        fail("TickEssentialReconcile must re-check player weapon state (safety net for a missed OnItemEquipped)")
    if "IsInCombat()" in reconcile:
        fail("TickEssentialReconcile must NOT re-check combat state — confirmed live this stripped essential within ~3s of an MCM toggle, before combat even started, because 'not currently fighting' raced with the essential-collapse moment it's supposed to protect")

    ok("BeatBeforeKillScript auto trigger (J2), weapon-equip-only reversal (J5), dialog scoped to the auto path only")


def test_main_wiring() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")

    combat_evt = extract_event(
        text, "Event Actor.OnCombatStateChanged(Actor akSender, Actor akTarget, Int aeCombatState)"
    )
    if "OnPlayerEnterCombatWith(akTarget)" not in combat_evt:
        fail("Actor.OnCombatStateChanged must call BeatBeforeKill().OnPlayerEnterCombatWith on aeCombatState==1")
    if "aeCombatState == 1" not in combat_evt:
        fail("Actor.OnCombatStateChanged must branch on aeCombatState==1 (verified against real FO4 Actor.psc: 0=not in combat, 1=in combat, 2=searching)")
    if "OnPlayerExitCombatWith" in combat_evt or "aeCombatState == 0" in combat_evt:
        fail("Actor.OnCombatStateChanged must NOT handle aeCombatState==0 for Slice J — confirmed live this raced with an essential actor's own protected-collapse moment and broke the feature; weapon-equip is the only reversal now")

    item_evt = extract_event(
        text, "Event Actor.OnItemEquipped(Actor akSender, Form akBaseObject, ObjectReference akReference)"
    )
    if "ClearAllEssentialOnWeaponEquip()" not in item_evt:
        fail("Actor.OnItemEquipped must call BeatBeforeKill().ClearAllEssentialOnWeaponEquip() on any weapon equip")
    # Must be in the "it's a weapon" branch (after the Weapon cast), not the non-weapon
    # early-return branch above it.
    weapon_cast_idx = item_evt.find("Weapon asW = akBaseObject as Weapon")
    clear_call_idx = item_evt.find("ClearAllEssentialOnWeaponEquip()")
    if weapon_cast_idx < 0 or clear_call_idx < weapon_cast_idx:
        fail("ClearAllEssentialOnWeaponEquip() must be called in the confirmed-weapon branch, not before the Weapon cast")

    facade = extract_function(text, "BeatBeforeKill")
    if "PickmansWhisperBeatBeforeKillScript" not in facade:
        fail("MainQuestScript.BeatBeforeKill() facade must cast to PickmansWhisperBeatBeforeKillScript")

    ok("MainQuestScript wiring: OnCombatStateChanged (enter only) + OnItemEquipped (any weapon) -> BeatBeforeKillScript")


def test_killer_scan_dispatch() -> None:
    text = KILLER_SCAN.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperBeatBeforeKillScript Function BeatBeforeKill" not in text:
        fail("KillerScanScript must have its own BeatBeforeKill() facade")
    dispatch = extract_function(text, "DispatchListeners")
    if 'beat.CallFunctionNoWait("TickEssentialReconcile", None)' not in dispatch:
        fail("DispatchListeners must CallFunctionNoWait TickEssentialReconcile every tick (ambient safety net)")
    ok("KillerScanScript dispatches TickEssentialReconcile (no StartTimer on BeatBeforeKillScript)")


def test_victims_wiring() -> None:
    text = VICTIMS.read_text(encoding="utf-8", errors="replace")
    facade = extract_function(text, "BeatBeforeKill")
    if "PickmansWhisperBeatBeforeKillScript" not in facade:
        fail("VictimsScript.BeatBeforeKill() facade must cast to PickmansWhisperBeatBeforeKillScript")

    mcm_fn = extract_function(text, "MCMToggleEssentialForAimed")
    if "ResolveVictimsAimActor()" not in mcm_fn:
        fail("MCMToggleEssentialForAimed must resolve the aim cache like other Victims MCM actions")
    if "BeatBeforeKill()" not in mcm_fn or "ToggleEssentialForAimed(aimed)" not in mcm_fn:
        fail("MCMToggleEssentialForAimed must delegate to BeatBeforeKill().ToggleEssentialForAimed(aimed)")
    if "RefreshVictimsPanel(True)" not in mcm_fn:
        fail("MCMToggleEssentialForAimed must refresh the Victims panel after acting")

    ok("VictimsScript BeatBeforeKill facade + MCMToggleEssentialForAimed wiring")


def test_mcm_config() -> None:
    cfg = MCM_CONFIG.read_text(encoding="utf-8", errors="replace")
    if '"function": "MCMToggleEssentialForAimed"' not in cfg:
        fail("config.json must wire a button to MCMToggleEssentialForAimed")
    idx = cfg.find('"function": "MCMToggleEssentialForAimed"')
    window = cfg[max(0, idx - 400) : idx + 100]
    if '"scriptName": "PickmansWhisperVictimsScript"' not in window:
        fail("Toggle essential button must target PickmansWhisperVictimsScript (same pattern as every other Victims MCM action)")
    if '"text": "Toggle essential"' not in cfg:
        fail("config.json missing the Toggle essential button label")

    # "Towards the top" — must land before the Name/rename section, not buried later.
    toggle_idx = cfg.find('"text": "Toggle essential"')
    name_section_idx = cfg.find('"text": "Name / rename"')
    if toggle_idx < 0 or name_section_idx < 0 or toggle_idx > name_section_idx:
        fail("Toggle essential button must appear before the Name / rename section (towards the top of the Victims page)")

    ok("config.json Toggle essential button wired to VictimsScript, positioned near the top")


def test_status_row() -> None:
    cfg = MCM_CONFIG.read_text(encoding="utf-8", errors="replace")
    if '"id": "sBeatEssential:Victims"' not in cfg:
        fail("config.json must have an sBeatEssential:Victims status row")
    status_idx = cfg.find('"id": "sBeatEssential:Victims"')
    toggle_idx = cfg.find('"text": "Toggle essential"')
    if status_idx < 0 or toggle_idx < 0 or status_idx > toggle_idx:
        fail("sBeatEssential:Victims row must appear BEFORE the Toggle essential button (state visible before you press it)")

    for settings_path in (MCM_SETTINGS, SETTINGS_LEGACY):
        settings = settings_path.read_text(encoding="utf-8", errors="replace")
        if "[Victims]" not in settings or "sBeatEssential=" not in settings.split("[Victims]", 1)[1]:
            fail(f"{settings_path.name} must default sBeatEssential under [Victims]")

    main = MAIN.read_text(encoding="utf-8", errors="replace")
    writer = extract_function(main, "WriteBeatEssentialStatusToMcm")
    if "IsTrackedEssential(aimed)" not in writer:
        fail("WriteBeatEssentialStatusToMcm must check IsTrackedEssential(aimed)")
    if "☑" not in writer:
        fail("WriteBeatEssentialStatusToMcm must use a checkmark glyph (☑) for the ON state")
    if "☐" not in writer:
        fail("WriteBeatEssentialStatusToMcm must use an empty-checkbox glyph (☐) for the OFF state")

    aux = extract_function(main, "WriteVictimsMcmAuxRows")
    if "WriteBeatEssentialStatusToMcm(aimed)" not in aux:
        fail("WriteVictimsMcmAuxRows must call WriteBeatEssentialStatusToMcm(aimed) so the status row refreshes alongside Aimed/Decay/Summary")

    ok("sBeatEssential status row: checkbox glyphs, positioned before the button, refreshed via WriteVictimsMcmAuxRows")


def test_esp_builder() -> None:
    text = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if '"PickmansWhisperBeatBeforeKillScript"' not in text:
        fail("build_hunger_spell_esp.py must attach PickmansWhisperBeatBeforeKillScript to the Main quest VMAD")
    ok("ESP builder attaches BeatBeforeKillScript to Main quest")


def test_deploy_gate() -> None:
    for path in (DEPLOY_PS1, DEPLOY_SH):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "PickmansWhisperBeatBeforeKillScript.psc" not in text:
            fail(f"{path.name} must compile/deploy PickmansWhisperBeatBeforeKillScript")
    if "test_beat_before_kill.py" not in DEPLOY_PS1.read_text(encoding="utf-8", errors="replace"):
        fail("build-deploy-local.ps1 must run test_beat_before_kill.py")
    ok("deploy gate compiles BeatBeforeKillScript + runs this contract test")


def main() -> int:
    if not MAIN.is_file():
        fail("missing MainQuestScript PSC")
    test_tracking_core()
    test_manual_toggle()
    test_auto_trigger()
    test_main_wiring()
    test_killer_scan_dispatch()
    test_victims_wiring()
    test_mcm_config()
    test_status_row()
    test_esp_builder()
    test_deploy_gate()
    print("All beat-before-kill (Slice J) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
