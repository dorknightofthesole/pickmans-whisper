#!/usr/bin/env python3
"""Contracts for Slice G1 — bed corpse hallucination (Actor NPC).

Locks:
  - FO4 sleep stubs; BedGift owns RegisterForPlayerSleep + OnPlayerSleep*
  - PlayerAlias re-arms via GetBedGift().RegisterBedGiftSleep every load
  - Self-contained BedGiftScript (no KillerScan); Main shared callbacks only
  - Sole gameplay PlaceAtMe: SleepStart → TrySpawnBedCorpse → Present (experiment)
  - Own timers: TIMER_BED_OVERLAYS / TIMER_BED_POSE / TIMER_BED_DESPAWN
  - SleepStop: empty no-op (no Clear/Present — avoids Start/Stop race)
  - FID_BED_SPAWN_NPC matches Fallout4.esm DiamondCityResidentF01NoodleMarket (unnamed Resident)
  - ESP attaches both Main + BedGift scripts; Caprica/deploy compile BedGift

Usage:
  python tools/test_bed_hallucination.py
  python tools/test_bed_hallucination.py --esm "<path>/Fallout4.esm"
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MODCFG = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
BED_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperBedGiftScript.psc"
ALIAS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
SCRIPT_STUB = ROOT / "tools" / "stubs" / "ScriptObject.psc"
MOD_CONFIG = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"

FID_BED_SPAWN = 0x00004DEC
EDID_BED_SPAWN = b"DiamondCityResidentF01NoodleMarket"
BED_SPAWN_SIG = b"NPC_"


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
        m = re.search(rf"Event\s+(?:[\w.]+\.)?{name}\s*\(", text)
    if not m:
        fail(f"missing function/event {name}")
    start = m.start()
    end_m = re.search(r"\n(?:EndFunction|EndEvent)\b", text[start:])
    if not end_m:
        fail(f"no End for {name}")
    return text[start : start + end_m.end()]


def find_esm(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    load_dotenv()
    env = __import__("os").environ.get("FALLOUT4_ESM")
    if env and Path(env).is_file():
        return Path(env)
    return None


def get_record_edid(data: bytes, sig: bytes, fid: int) -> bytes | None:
    target = fid.to_bytes(4, "little")
    start = 0
    while True:
        i = data.find(sig, start)
        if i < 0 or i + 16 > len(data):
            break
        if data[i + 12 : i + 16] == target:
            sz = int.from_bytes(data[i + 4 : i + 8], "little")
            body = data[i + 24 : i + 24 + sz]
            j = body.find(b"EDID")
            if j >= 0 and j + 6 <= len(body):
                esz = int.from_bytes(body[j + 4 : j + 6], "little")
                return body[j + 6 : j + 6 + esz].split(b"\x00")[0]
            return b""
        start = i + 4
    return None


def test_stubs() -> None:
    so = SCRIPT_STUB.read_text(encoding="utf-8")
    if not re.search(r"Function\s+RegisterForPlayerSleep\s*\(\s*\)\s*Native", so):
        fail("ScriptObject must declare RegisterForPlayerSleep Native")
    if "Event OnPlayerSleepStart" not in so or "Event OnPlayerSleepStop" not in so:
        fail("ScriptObject must declare OnPlayerSleepStart/Stop")
    actor = (ROOT / "tools" / "stubs" / "Actor.psc").read_text(encoding="utf-8")
    if not re.search(r"Function\s+KillSilent\s*\(", actor):
        fail("Actor.psc must declare KillSilent Native")
    if not re.search(r"Bool\s+Function\s+SnapIntoInteraction\s*\(", actor):
        fail("Actor.psc must declare SnapIntoInteraction Native")
    if re.search(r"Function\s+SetSilent\s*\(", actor):
        fail("Actor.SetSilent is not FO4 — do not stub it")
    ok("FO4 sleep + SnapIntoInteraction / KillSilent stubs")


def test_alias_rearms_bed_sleep(alias_text: str) -> None:
    if not ALIAS.is_file():
        fail(f"missing {ALIAS}")
    if re.search(r"\bRegisterForPlayerSleep\s*\(", alias_text):
        fail("alias must not RegisterForPlayerSleep — BedGift owns it")
    if "Event OnPlayerSleepStart" in alias_text or "Event OnPlayerSleepStop" in alias_text:
        fail("alias must not declare OnPlayerSleep* — BedGift owns them")
    if "GetBedGift()" not in alias_text:
        fail("alias must resolve BedGift via GetBedGift()")
    if "RegisterBedGiftSleep()" not in alias_text:
        fail("alias must call bed.RegisterBedGiftSleep from init/load")
    if "main.RegisterBedGiftSleep" in alias_text:
        fail("alias must not call Main.RegisterBedGiftSleep — façade removed")
    get_bed = extract_function(alias_text, "GetBedGift")
    if "GetOwningQuest" in get_bed:
        fail(
            "GetBedGift must NOT use GetOwningQuest — PlayerAlias owns PlayerCombat "
            "(0x805); BedGift is on Main (0x800)"
        )
    if "GetFormFromFile" not in get_bed or "FID_MAIN_QUEST" not in get_bed:
        fail("GetBedGift must GetFormFromFile(FID_MAIN_QUEST) then cast BedGift")
    ok("PlayerAlias re-arms BedGift sleep directly")


def test_bed_sleep_registration(bed: str) -> None:
    reg = extract_function(bed, "RegisterBedGiftSleep")
    if "RegisterForPlayerSleep" not in reg:
        fail("BedGift RegisterBedGiftSleep must RegisterForPlayerSleep")
    if "Event OnPlayerSleepStart" not in bed or "Event OnPlayerSleepStop" not in bed:
        fail("BedGift must own OnPlayerSleepStart/Stop")
    start = extract_function(bed, "OnPlayerSleepStart")
    stop = extract_function(bed, "OnPlayerSleepStop")
    if "HandlePlayerSleepStart" not in start:
        fail("BedGift OnPlayerSleepStart must call HandlePlayerSleepStart")
    if "BED_MIN_SLEEP_HOURS" not in start and "BED_MIN_SLEEP_HOURS" not in bed:
        fail("BedGift must declare BED_MIN_SLEEP_HOURS")
    if "BED_MIN_SLEEP_HOURS = 3.0" not in bed and "BED_MIN_SLEEP_HOURS=3.0" not in bed:
        fail("BED_MIN_SLEEP_HOURS must be 3.0")
    if "/ 24.0" not in start and "/24.0" not in start:
        fail("OnPlayerSleepStart must compare planned sleep in game days (hours/24)")
    if "HandlePlayerSleepStart" not in start:
        fail("OnPlayerSleepStart must still call HandlePlayerSleepStart when duration ok")
    # Gate must Return before spawn path when short — status/trace, no silent skip.
    if "sleep start skip" not in start and "SetBedGiftStatus" not in start:
        fail("OnPlayerSleepStart short-sleep gate must SetBedGiftStatus / not silent")
    if "ClearBedCorpse" in stop or "PresentBedCorpseOnWake" in stop or "TrySpawnBedCorpse" in stop:
        fail("OnPlayerSleepStop must be a no-op — no Clear/Present/spawn (Start/Stop race)")
    if "HandlePlayerSleepStop" in bed:
        fail("HandlePlayerSleepStop retired — SleepStop is empty")
    ok("BedGift owns bed gift sleep registration")


def test_killer_scan_isolated_from_bed_gift() -> None:
    ks = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillerScanScript.psc"
    if not ks.is_file():
        fail(f"missing {ks}")
    text = ks.read_text(encoding="utf-8", errors="replace")
    dispatch = extract_function(text, "DispatchListeners")
    if "OnKillerScanDeadlines" in dispatch or "MaybeWarmBedGiftBody" in dispatch:
        fail("KillerScan DispatchListeners must not touch BedGift")
    if re.search(r"Function\s+BedGift\s*\(", text):
        fail("KillerScan must not expose BedGift() facade")
    ok("KillerScan isolated from BedGift")


def test_main_shared_only(main: str) -> None:
    if re.search(r"\bRegisterForPlayerSleep\s*\(", main):
        fail("main quest must not RegisterForPlayerSleep — BedGift owns it")
    if "Event OnPlayerSleepStart" in main or "Event OnPlayerSleepStop" in main:
        fail("main quest must not declare OnPlayerSleep*")
    if "TIMER_BED_DESPAWN" in main and "aiTimerID == TIMER_BED_DESPAWN" in main:
        fail("Main OnTimer must not handle TIMER_BED_DESPAWN — BedGift owns it")
    if re.search(r"^(?:PickmansWhisperBedGiftScript\s+)?Function\s+BedGift\s*\(", main, re.M):
        fail("Main must not expose BedGift() façade — callers cast/own BedGift")
    for name in (
        "MaybeWarmBedGiftBody",
        "RegisterBedGiftSleep",
        "HandlePlayerSleepStart",
        "DebugForceBedGift",
        "DebugClearBedGift",
        "OnKillerScanDeadlines",
    ):
        if re.search(rf"Function\s+{name}\s*\(", main):
            fail(f"Main must not own {name} — lives on BedGiftScript or removed")
    if re.search(r"\b(?:String\s+)?Property\s+LastBedGiftStatus\b", main):
        fail("Main must not mirror LastBedGiftStatus — BedGift owns it")
    status_cb = extract_function(main, "OnBedGiftStatus")
    if "ToastDebug" not in status_cb:
        fail("Main OnBedGiftStatus must ToastDebug (shared debug path)")
    knife_warm = extract_function(main, "HandleKillerScanKnifeAimWarm")
    if "MaybeWarmBedGiftBody" in knife_warm:
        fail("HandleKillerScanKnifeAimWarm must not warm bed gift")
    nongame = extract_function(main, "IsNonGameplayCorpse")
    if "IsBedGiftCorpse" not in nongame:
        fail("IsNonGameplayCorpse must query BedGift.IsBedGiftCorpse")
    if "as PickmansWhisperBedGiftScript" not in nongame:
        fail("IsNonGameplayCorpse must cast BedGift via Quest (no Main.BedGift façade)")
    load = extract_function(main, "LoadLineBanks")
    if "ModConfigAlias.LoadModConfig()" not in load:
        fail("LoadLineBanks must ModConfigAlias.LoadModConfig (resume/reload refresh)")
    if "LoadBedGiftLines" in main:
        fail("LoadBedGiftLines retired — wake toast is ModConfig bedGiftWakeToast")
    modcfg = MODCFG.read_text(encoding="utf-8", errors="replace")
    load_mod = extract_function(modcfg, "LoadModConfig")
    if "bedGiftWakeToast" not in load_mod:
        fail("LoadModConfig must parse bedGiftWakeToast")
    if "bedGiftCooldownDays" not in load_mod:
        fail("LoadModConfig must parse bedGiftCooldownDays")
    if "bedGiftWoundAlpha" not in load_mod:
        fail("LoadModConfig must parse bedGiftWoundAlpha")
    if "BedGiftCooldownDays = -1.0" not in load_mod:
        fail("LoadModConfig must reset BedGiftCooldownDays to sentinel -1.0")
    if "BedGiftWoundAlpha = -1.0" not in load_mod:
        fail("LoadModConfig must reset BedGiftWoundAlpha to sentinel -1.0")
    if "ModConfigAlias Auto" not in main:
        fail("Main must expose ModConfigAlias for BedGift/CorpseDecay")
    bed = BED_PSC.read_text(encoding="utf-8", errors="replace")
    if "ModConfigAlias.GetBedGiftWakeToast" not in bed:
        fail("BedGift must read wake toast via ModConfigAlias")
    if "ModConfigAlias.GetBedGiftCooldownDays" not in bed:
        fail("BedGift must read cooldown via ModConfigAlias")
    if "OnBedGiftStatus" not in bed:
        fail("BedGift SetBedGiftStatus must callback Main.OnBedGiftStatus")
    if "m.LastBedGiftStatus" in bed:
        fail("BedGift must not mirror status onto Main.LastBedGiftStatus")
    ok("Main shared callbacks only + ModConfigAlias bed gift wiring")


def test_bed_script(bed: str) -> None:
    if "Scriptname PickmansWhisperBedGiftScript extends Quest" not in bed:
        fail("BedGift must extend Quest")
    if "OnKillerScanDeadlines" in bed or "MaybeWarmBedGiftBody" in bed:
        fail("BedGift must not use KillerScan warm/deadlines — sleep/timer self-contained")
    if "BedDespawnScanCount" in bed or "BED_DESPAWN_SCANS" in bed:
        fail("BedGift must not despawn by KillerScan pulse count")
    if "BedOverlaysAtReal" in bed or "ScheduleBedGiftDecayOverlays" in bed:
        fail("BedGift must not use BedOverlaysAtReal deadline polling")
    if "TIMER_BED_DESPAWN" not in bed or "BED_DESPAWN_SECONDS" not in bed:
        fail("BedGift must TIMER_BED_DESPAWN + BED_DESPAWN_SECONDS")
    if "BED_DESPAWN_SECONDS = 4.0" not in bed and "BED_DESPAWN_SECONDS=4.0" not in bed:
        fail("BED_DESPAWN_SECONDS must be 4.0")
    if "TIMER_BED_OVERLAYS" not in bed or "KickBedOverlayOnesHot" not in bed:
        fail("BedGift must TIMER_BED_OVERLAYS + KickBedOverlayOnesHot (oneshot overlay)")
    on_timer = extract_function(bed, "OnTimer")
    if "MaybeApplyBedGiftDecayOverlays" not in on_timer:
        fail("BedGift OnTimer must MaybeApplyBedGiftDecayOverlays")
    if "TIMER_BED_POSE" not in on_timer or "AdvanceBedPoseSequence" not in on_timer:
        fail("BedGift OnTimer must dispatch TIMER_BED_POSE to AdvanceBedPoseSequence")
    if "TIMER_BED_DESPAWN" not in on_timer or "OnBedDespawnTimer" not in on_timer:
        fail("BedGift OnTimer must dispatch TIMER_BED_DESPAWN to OnBedDespawnTimer")
    if "StartTimer(" in on_timer:
        fail("BedGift OnTimer must not StartTimer inline (dispatch only)")
    arm = extract_function(bed, "ArmBedDespawnTimer")
    if "StartTimer(" not in arm or "TIMER_BED_DESPAWN" not in arm:
        fail("ArmBedDespawnTimer must StartTimer(TIMER_BED_DESPAWN)")
    despawn = extract_function(bed, "OnBedDespawnTimer")
    if "ClearBedCorpse" not in despawn:
        fail("OnBedDespawnTimer must ClearBedCorpse")
    if "BedOverlaysBusy" not in despawn:
        fail("OnBedDespawnTimer must honor BedOverlaysBusy hold/watchdog")
    kick = extract_function(bed, "KickBedOverlayOnesHot")
    if "StartTimer(" not in kick or "TIMER_BED_OVERLAYS" not in kick:
        fail("KickBedOverlayOnesHot must StartTimer(TIMER_BED_OVERLAYS)")
    clear = extract_function(bed, "ClearBedCorpse")
    if "CancelTimer(TIMER_BED_OVERLAYS)" not in clear:
        fail("ClearBedCorpse must CancelTimer(TIMER_BED_OVERLAYS)")
    if "CancelTimer(TIMER_BED_POSE)" not in clear:
        fail("ClearBedCorpse must CancelTimer(TIMER_BED_POSE) (abort in-flight pose sequence)")
    if "CancelTimer(TIMER_BED_DESPAWN)" not in clear:
        fail("ClearBedCorpse must CancelTimer(TIMER_BED_DESPAWN)")
    if "Actor BedCorpse" not in bed:
        fail("BedCorpse must be Actor on BedGift")
    create = extract_function(bed, "CreateBedCorpseAt")
    if "FID_BED_SPAWN_NPC" not in create or "PlaceAtMe" not in create:
        fail("CreateBedCorpseAt must PlaceAtMe DiamondCityResidentF01NoodleMarket")
    # Warm path must not kill inline; death happens in PoseBedCorpseInFurniture (wake/debug).
    if re.search(r"\bKillSilent\s*\(", create) or re.search(r"\bKillBedCorpse\s*\(", create):
        fail("CreateBedCorpseAt warm path must keep NPC alive until Present pose")
    if "ParkWarmedBedCorpse" not in create or "SnapBedCorpseToAnchor" not in create:
        fail("CreateBedCorpseAt must park (warm) or SnapBedCorpseToAnchor (bed place; pose deferred)")
    if "PoseBedCorpseInFurniture" in create:
        fail("CreateBedCorpseAt must not Pose/Wait — Present poses on wake (SleepStart must stay snappy)")
    if not re.search(r"PlaceAtMe\([^)]*False\s*\)", create):
        fail("CreateBedCorpseAt PlaceAtMe should use InitiallyDisabled=False")
    assign_at = create.find("BedCorpse = corpse")
    park_at = create.find("ParkWarmedBedCorpse")
    snap_at = create.find("SnapBedCorpseToAnchor")
    if assign_at < 0 or (park_at >= 0 and assign_at > park_at) or (snap_at >= 0 and assign_at > snap_at):
        fail("CreateBedCorpseAt must assign BedCorpse before park/snap")
    if re.search(r"\bSetSilent\s*\(", bed):
        fail("PSC must not call SetSilent — not a FO4 native")
    if "MuteBedCorpseVoice" in bed or "SetOverrideVoiceType" in bed:
        fail("bed gift mute path retired — no MuteBedCorpseVoice / SetOverrideVoiceType")
    # Pose is a re-arming TIMER_BED_POSE state machine — never a blocking Utility.Wait
    # loop on the SleepStop wake stack (that stalled KillerScan's shared timer).
    if "WaitForBedCorpse3D" in bed:
        fail("WaitForBedCorpse3D retired — poll Is3DLoaded via TIMER_BED_POSE, not Utility.Wait")
    pose = extract_function(bed, "PoseBedCorpseInFurniture")
    if "TIMER_BED_POSE" not in pose:
        fail("PoseBedCorpseInFurniture must arm TIMER_BED_POSE (re-arming poll)")
    if "Utility.Wait" in pose:
        fail("PoseBedCorpseInFurniture must not Utility.Wait — that blocks the wake stack")

    advance = extract_function(bed, "AdvanceBedPoseSequence")
    if "Is3DLoaded" not in advance:
        fail("AdvanceBedPoseSequence must poll Is3DLoaded")
    if "Utility.Wait" in advance:
        fail("AdvanceBedPoseSequence must not Utility.Wait — re-arm TIMER_BED_POSE instead")
    if "StartTimer(" not in advance or "TIMER_BED_POSE" not in advance:
        fail("AdvanceBedPoseSequence must re-arm TIMER_BED_POSE while waiting for 3D")
    if "BedPoseTriesRemaining" not in advance:
        fail("AdvanceBedPoseSequence must bound retries via BedPoseTriesRemaining")
    if "RagdollBedPoseFallback" not in advance:
        fail("AdvanceBedPoseSequence must ragdoll-fallback once 3D tries are exhausted")

    snap = extract_function(bed, "DoBedPoseSnap")
    if "SnapIntoInteraction" not in snap:
        fail("DoBedPoseSnap must SnapIntoInteraction")
    if "Utility.Wait" in snap:
        fail("DoBedPoseSnap must not Utility.Wait — settle via TIMER_BED_POSE instead")
    if "RagdollBedPoseFallback" not in snap:
        fail("DoBedPoseSnap must ragdoll-fallback when SnapIntoInteraction fails")
    if "StartTimer(" not in snap or "TIMER_BED_POSE" not in snap:
        fail("DoBedPoseSnap must arm the settle delay via TIMER_BED_POSE")

    finish_snap = extract_function(bed, "FinishBedPoseSnap")
    if "KillBedCorpse" not in finish_snap:
        fail("FinishBedPoseSnap must KillBedCorpse after the settle delay")
    if "FinishBedPresentTail" not in finish_snap:
        fail("FinishBedPoseSnap must FinishBedPresentTail (despawn arm / overlay kick / toast)")

    ragdoll = extract_function(bed, "RagdollBedPoseFallback")
    if "SnapBedCorpseToAnchor" not in ragdoll:
        fail("RagdollBedPoseFallback must SnapBedCorpseToAnchor")
    if "KillBedCorpse" not in ragdoll:
        fail("RagdollBedPoseFallback must KillBedCorpse")
    if "Debug.Notification" not in ragdoll or "SnapIntoInteraction FAILED" not in ragdoll:
        fail("RagdollBedPoseFallback must always toast clearly when snap/3D fails")
    if "FinishBedPresentTail" not in ragdoll:
        fail("RagdollBedPoseFallback must FinishBedPresentTail so despawn/overlay still arm")
    if "actor 3D not loaded" not in advance and "actor 3D not loaded" not in ragdoll:
        fail("Pose sequence must ragdoll without Snap when 3D never loads")
    kill = extract_function(bed, "KillBedCorpse")
    if "GetPlayer" not in kill or "KillSilent" not in kill:
        fail("KillBedCorpse must KillSilent with player killer (Protected ActorBases)")
    if "SetKnifeKillCreditSuppressed" not in kill:
        fail("KillBedCorpse must suppress knife-kill credit (no hunger satiation)")
    if "NoteBackgroundDead" not in kill:
        fail("KillBedCorpse must NoteBackgroundDead so dead-scan ignores the body")
    if "Function IsBedGiftCorpse" not in bed:
        fail("BedGift must expose IsBedGiftCorpse for Main killscan ignore")
    main_txt = PSC.read_text(encoding="utf-8", errors="replace")
    if "IsNonGameplayCorpse" not in main_txt:
        fail("Main must expose IsNonGameplayCorpse for bed/lab ignore")
    handle = extract_function(main_txt, "HandleNPCDeath")
    if "KnifeKillCreditSuppressed" not in handle or "IsNonGameplayCorpse" not in handle:
        fail("HandleNPCDeath must skip bed gift / wound lab corpses")
    if "SatiateHunger" in handle:
        fail("HandleNPCDeath must not call SatiateHunger directly (ProcessKnifeKill does)")
    track = extract_function(main_txt, "TrackLivingNear")
    if "IsNonGameplayCorpse" not in track:
        fail("TrackLivingNear must skip bed gift / wound lab corpses")
    if re.search(r"\bSetProtected\s*\(", bed):
        fail("must not SetProtected on shared ActorBase")
    spawn = extract_function(bed, "TrySpawnBedCorpse")
    if "CreateBedCorpseAt" not in spawn:
        fail("TrySpawnBedCorpse must CreateBedCorpseAt")
    if "KickBedOverlayOnesHot" not in spawn:
        fail("TrySpawnBedCorpse must KickBedOverlayOnesHot after PlaceAtMe")
    if "m.IsBladeEquipped()" not in spawn:
        fail("TrySpawnBedCorpse non-force path must require IsBladeEquipped")
    if "skip:" not in spawn:
        fail("TrySpawnBedCorpse must Trace/status skip reasons (no silent Return)")
    start = extract_function(bed, "HandlePlayerSleepStart")
    if "TrySpawnBedCorpse" not in start:
        fail("HandlePlayerSleepStart must TrySpawnBedCorpse (sole gameplay spawn)")
    if "PresentBedCorpseOnWake" not in start:
        fail("HandlePlayerSleepStart must PresentBedCorpseOnWake (SleepStart-present experiment)")
    if "PlaceAtMe" in start:
        fail("HandlePlayerSleepStart must spawn via TrySpawnBedCorpse (not raw PlaceAtMe)")
    if "MaybeApplyBedGiftDecayOverlays" in start:
        fail("HandlePlayerSleepStart must not sync-apply LooksMenu decay")
    if "TIMER_BED_PRESENT" in bed:
        fail("TIMER_BED_PRESENT retired — no wake retries")
    strip = extract_function(bed, "StripBedCorpse")
    if "UnequipAll" not in strip or "RemoveAllItems" not in strip:
        fail("StripBedCorpse must UnequipAll + RemoveAllItems")
    snap = extract_function(bed, "SnapBedCorpseToAnchor")
    if "SetPosition" not in snap or "ForceAddRagdollToWorld" not in snap:
        fail("SnapBedCorpseToAnchor must SetPosition + ForceAddRagdollToWorld")
    if "MoveTo" in snap:
        fail("SnapBedCorpseToAnchor must not MoveTo furniture")
    present = extract_function(bed, "PresentBedCorpseOnWake")
    if "PoseBedCorpseInFurniture" not in present:
        fail("PresentBedCorpseOnWake must PoseBedCorpseInFurniture when still alive")
    if "PlaceAtMe" in present:
        fail("PresentBedCorpseOnWake must not PlaceAtMe")
    if "Utility.Wait" in present:
        fail("PresentBedCorpseOnWake must not Utility.Wait — pose finishes async via TIMER_BED_POSE")
    if "FinishBedPresentTail" not in present:
        fail("PresentBedCorpseOnWake must FinishBedPresentTail on the no-pose-needed paths")

    tail = extract_function(bed, "FinishBedPresentTail")
    if "ArmBedDespawnTimer" in tail:
        fail("FinishBedPresentTail must not ArmBedDespawnTimer — short despawn arms after overlays")
    if "TIMER_BED_DESPAWN" not in tail or "StartTimer" not in tail:
        fail("FinishBedPresentTail must arm long despawn safety (overlay oneshot can miss)")
    if "BED_OVERLAY_BUSY_TIMEOUT_SECONDS" not in tail:
        fail("FinishBedPresentTail safety delay must include BED_OVERLAY_BUSY_TIMEOUT_SECONDS")
    if "BedOverlaysBusy" not in bed:
        fail("BedGift must track BedOverlaysBusy against overlay re-entry")
    if "BedOverlaysApplied = False" not in tail:
        fail("FinishBedPresentTail must clear BedOverlaysApplied after pose (re-paint)")
    if "KickBedOverlayOnesHot" not in tail:
        fail("FinishBedPresentTail must KickBedOverlayOnesHot after pose")
    if 'CallFunctionNoWait("MaybeApplyBedGiftDecayOverlays"' in tail:
        fail("FinishBedPresentTail must not CallFunctionNoWait MaybeApply")
    if "MaybeApplyBedGiftDecayOverlays()" in tail:
        fail("FinishBedPresentTail must not sync-apply decay overlays")
    if "BedWakeHandledThisSleep" in bed:
        fail("BedWakeHandledThisSleep retired with SleepStop handling")
    if "MaybeSpeakBedGiftWakeToast" not in tail:
        fail("FinishBedPresentTail must MaybeSpeakBedGiftWakeToast")
    apply = extract_function(bed, "MaybeApplyBedGiftDecayOverlays")
    if "ArmBedDespawnTimer" not in apply:
        fail("MaybeApplyBedGiftDecayOverlays must ArmBedDespawnTimer after paint (or skip)")
    wake = extract_function(bed, "MaybeSpeakBedGiftWakeToast")
    if "ModConfigAlias.GetBedGiftWakeToast" not in wake:
        fail("MaybeSpeakBedGiftWakeToast must use ModConfig via ModConfigAlias")
    if "BedGiftLines" in bed or "LoadBedGiftLines" in bed:
        fail("BedGiftLines bank retired — use ModConfig bedGiftWakeToast")
    if "0x00004DEC" not in bed:
        fail("BedGift must declare FID_BED_SPAWN_NPC = 0x00004DEC")
    if "LCharRaiderFemale" in bed or "0x000D39F5" in bed:
        fail("Bed gift spawn retired LCharRaiderFemale — use DiamondCityResidentF01NoodleMarket")
    if "EncWorkshopNPCFemaleFarmer02" in bed or "0x00113347" in bed:
        fail("Bed gift spawn retired EncWorkshopNPCFemaleFarmer02 — use DiamondCityResidentF01NoodleMarket")
    extract_function(bed, "DebugForceBedGift")
    extract_function(bed, "DebugClearBedGift")
    ok("BedGift SnapIntoInteraction + KillSilent + ModConfig wake toast")


def get_record_edid_zlib(data: bytes, sig: bytes, fid: int) -> bytes | None:
    """FO4 NPC_ records are often zlib-compressed; EDID lives in decompressed payload."""
    import zlib

    target = fid.to_bytes(4, "little")
    start = 0
    while True:
        i = data.find(sig, start)
        if i < 0 or i + 24 > len(data):
            return None
        if data[i + 12 : i + 16] != target:
            start = i + 4
            continue
        size = int.from_bytes(data[i + 4 : i + 8], "little")
        flags = int.from_bytes(data[i + 8 : i + 12], "little")
        payload = data[i + 24 : i + 24 + size]
        if flags & 0x00040000:
            try:
                payload = zlib.decompress(payload[4:])
            except Exception:
                return None
        k = payload.find(b"EDID")
        if k < 0 or k + 6 > len(payload):
            return None
        esz = int.from_bytes(payload[k + 4 : k + 6], "little")
        return payload[k + 6 : k + 6 + esz].split(b"\x00", 1)[0]


def test_esm(esm: Path | None) -> None:
    if not esm:
        fail("Fallout4.esm not found — set FALLOUT4_ESM or pass --esm")
    data = esm.read_bytes()
    edid = get_record_edid_zlib(data, BED_SPAWN_SIG, FID_BED_SPAWN)
    if edid is None:
        edid = get_record_edid(data, BED_SPAWN_SIG, FID_BED_SPAWN)
    if edid is None:
        fail(f"NPC_ {hex(FID_BED_SPAWN)} not found in {esm}")
    if edid != EDID_BED_SPAWN:
        fail(f"FID {hex(FID_BED_SPAWN)} EDID {edid!r} != {EDID_BED_SPAWN!r}")
    ok(f"FID_BED_SPAWN_NPC = DiamondCityResidentF01NoodleMarket ({esm.name})")


def test_config_mcm_deploy() -> None:
    if not MOD_CONFIG.is_file():
        fail(f"missing {MOD_CONFIG}")
    mod = MOD_CONFIG.read_text(encoding="utf-8")
    if "bedGiftWakeToast=" not in mod:
        fail("ModConfig.txt must ship bedGiftWakeToast=")
    if "bedGiftCooldownDays=" not in mod:
        fail("ModConfig.txt must ship bedGiftCooldownDays=")
    if "bedGiftWoundAlpha=" not in mod:
        fail("ModConfig.txt must ship bedGiftWoundAlpha=")
    if (ROOT / "Data" / "PickmansWhisper" / "config" / "BedGiftLines.txt").is_file():
        fail("BedGiftLines.txt retired — wake toast lives in ModConfig.txt")
    mcm = MCM.read_text(encoding="utf-8")
    if "bBedGift:Voice" not in mcm or "DebugForceBedGift" not in mcm:
        fail("MCM must have bed gift voice + debug force")
    for fn in ("DebugForceBedGift", "DebugClearBedGift"):
        m = re.search(
            rf'"function":\s*"{fn}"\s*,\s*"scriptName":\s*"([^"]+)"',
            mcm,
        )
        if not m:
            fail(f"MCM {fn} must declare scriptName immediately after function")
        if m.group(1) != "PickmansWhisperBedGiftScript":
            fail(f"MCM {fn} must target PickmansWhisperBedGiftScript, got {m.group(1)}")
    settings = SETTINGS.read_text(encoding="utf-8")
    if "bBedGiftEverySleep=1" not in settings:
        fail("settings.ini must default bBedGiftEverySleep=1 for testing")
    bed = BED_PSC.read_text(encoding="utf-8", errors="replace")
    if "BED_GIFT_COOLDOWN_DAYS" in bed:
        fail("BedGift must not hardcode BED_GIFT_COOLDOWN_DAYS — use ModConfig")
    m = re.search(r"Bool Function BedGiftCooldownReady\(\)(.*?)EndFunction", bed, re.S)
    if not m or "IsBedGiftEverySleep" not in m.group(1):
        fail("BedGiftCooldownReady must honor IsBedGiftEverySleep")
    if "ModConfigAlias.GetBedGiftCooldownDays" not in m.group(1):
        fail("BedGiftCooldownReady must use ModConfigAlias.GetBedGiftCooldownDays")
    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "test_bed_hallucination.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_bed_hallucination.py")
    if "PickmansWhisperBedGiftScript" not in deploy:
        fail("build-deploy-local.ps1 must compile/deploy BedGift script")
    esp = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperBedGiftScript" not in esp:
        fail("build_hunger_spell_esp.py must attach BedGift script to Main quest")
    if "build_vmad_scripts" not in esp:
        fail("ESP builder must support multi-script VMAD")
    ok("ModConfig bedGiftWakeToast + cooldown + MCM + ESP/deploy BedGift attach")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--esm", default=None)
    args = ap.parse_args()
    if not PSC.is_file():
        fail(f"missing {PSC}")
    if not BED_PSC.is_file():
        fail(f"missing {BED_PSC}")
    main_text = PSC.read_text(encoding="utf-8", errors="replace")
    bed_text = BED_PSC.read_text(encoding="utf-8", errors="replace")
    alias = ALIAS.read_text(encoding="utf-8", errors="replace")
    test_stubs()
    test_alias_rearms_bed_sleep(alias)
    test_bed_sleep_registration(bed_text)
    test_main_shared_only(main_text)
    test_killer_scan_isolated_from_bed_gift()
    test_bed_script(bed_text)
    test_esm(find_esm(args.esm))
    test_config_mcm_deploy()
    print("All bed-hallucination (G1) contracts passed.")


if __name__ == "__main__":
    main()
