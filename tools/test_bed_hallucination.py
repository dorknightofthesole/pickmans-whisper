#!/usr/bin/env python3
"""Contracts for Slice G1 — bed corpse hallucination (Actor NPC).

Locks:
  - FO4 sleep stubs; PlayerAlias owns RegisterForPlayerSleep
  - Logic on PickmansWhisperBedGiftScript; Main keeps thin façades
  - Single gameplay PlaceAtMe: MaybeWarmBedGiftBody → DiamondCityResidentF01NoodleMarket
  - SnapIntoInteraction + KillSilent; SleepStart/Stop never spawn
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
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
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


def test_alias(alias_text: str) -> None:
    if not ALIAS.is_file():
        fail(f"missing {ALIAS}")
    reg = extract_function(alias_text, "RegisterBedGiftSleep")
    if "RegisterForPlayerSleep" not in reg:
        fail("alias RegisterBedGiftSleep must RegisterForPlayerSleep")
    if "RegisterBedGiftSleep()" not in alias_text:
        fail("alias must call RegisterBedGiftSleep from init/load")
    if "Event OnPlayerSleepStart" not in alias_text or "Event OnPlayerSleepStop" not in alias_text:
        fail("alias must own OnPlayerSleepStart/Stop")
    if "HandlePlayerSleepStart" not in alias_text or "HandlePlayerSleepStop" not in alias_text:
        fail("alias sleep events must forward to main HandlePlayerSleep*")
    ok("PlayerAlias owns bed gift sleep registration")


def test_main_facade(main: str) -> None:
    if re.search(r"\bRegisterForPlayerSleep\s*\(", main):
        fail("main quest must not RegisterForPlayerSleep — use PlayerAlias")
    if "Event OnPlayerSleepStart" in main or "Event OnPlayerSleepStop" in main:
        fail("main quest must not declare OnPlayerSleep*")
    if "TIMER_BED_DESPAWN" in main and "aiTimerID == TIMER_BED_DESPAWN" in main:
        fail("Main OnTimer must not handle TIMER_BED_DESPAWN — BedGift owns it")
    bed_fn = extract_function(main, "BedGift")
    if "as PickmansWhisperBedGiftScript" not in bed_fn:
        fail("Main BedGift() must cast to PickmansWhisperBedGiftScript")
    if "as Quest" not in bed_fn:
        fail("Main BedGift() must cast via Quest (Caprica sibling-script rule)")
    for name in (
        "MaybeWarmBedGiftBody",
        "HandlePlayerSleepStart",
        "HandlePlayerSleepStop",
        "DebugForceBedGift",
        "DebugClearBedGift",
    ):
        body = extract_function(main, name)
        if "BedGift()" not in body:
            fail(f"Main {name} must forward via BedGift()")
        if "PlaceAtMe" in body:
            fail(f"Main {name} must not PlaceAtMe (façade only)")
    if "MaybeWarmBedGiftBody()" not in main:
        fail("killscan must call MaybeWarmBedGiftBody")
    load = extract_function(main, "LoadLineBanks")
    if "LoadModConfig()" not in load:
        fail("LoadLineBanks must LoadModConfig (bedGiftWakeToast)")
    if "LoadBedGiftLines" in main:
        fail("LoadBedGiftLines retired — wake toast is ModConfig bedGiftWakeToast")
    load_mod = extract_function(main, "LoadModConfig")
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
    if "GetBedGiftWakeToast" not in main:
        fail("Main must expose GetBedGiftWakeToast for BedGift")
    if "GetBedGiftCooldownDays" not in main:
        fail("Main must expose GetBedGiftCooldownDays for BedGift")
    if "GetBedGiftWoundAlpha" not in main:
        fail("Main must expose GetBedGiftWoundAlpha for CorpseDecay bed path")
    ok("Main bed gift façades + ModConfig wake toast + cooldown")


def test_bed_script(bed: str) -> None:
    if "Scriptname PickmansWhisperBedGiftScript extends Quest" not in bed:
        fail("BedGift must extend Quest")
    if "OnKillerScanDeadlines" not in bed:
        fail("BedGift must OnKillerScanDeadlines (Killer Orchestrator)")
    if "BedDespawnAtReal" not in bed or "BedOverlaysAtReal" not in bed:
        fail("BedGift must use BedDespawnAtReal / BedOverlaysAtReal deadlines")
    if "StartTimer(" in bed:
        fail("BedGift must not StartTimer")
    if "Actor BedCorpse" not in bed:
        fail("BedCorpse must be Actor on BedGift")
    create = extract_function(bed, "CreateBedCorpseAt")
    if "FID_BED_SPAWN_NPC" not in create or "PlaceAtMe" not in create:
        fail("CreateBedCorpseAt must PlaceAtMe DiamondCityResidentF01NoodleMarket")
    # Warm path must not kill inline; death happens in PoseBedCorpseInFurniture (wake/debug).
    if re.search(r"\bKillSilent\s*\(", create) or re.search(r"\bKillBedCorpse\s*\(", create):
        fail("CreateBedCorpseAt warm path must keep NPC alive until Present pose")
    if "ParkWarmedBedCorpse" not in create or "PoseBedCorpseInFurniture" not in create:
        fail("CreateBedCorpseAt must park (warm) or PoseBedCorpseInFurniture (debug)")
    if not re.search(r"PlaceAtMe\([^)]*False\s*\)", create):
        fail("CreateBedCorpseAt PlaceAtMe should use InitiallyDisabled=False")
    assign_at = create.find("BedCorpse = corpse")
    pose_at = create.find("PoseBedCorpseInFurniture")
    park_at = create.find("ParkWarmedBedCorpse")
    if assign_at < 0 or (pose_at >= 0 and assign_at > pose_at) or (park_at >= 0 and assign_at > park_at):
        fail("CreateBedCorpseAt must assign BedCorpse before park/pose")
    if re.search(r"\bSetSilent\s*\(", bed):
        fail("PSC must not call SetSilent — not a FO4 native")
    if "MuteBedCorpseVoice" in bed or "SetOverrideVoiceType" in bed:
        fail("bed gift mute path retired — no MuteBedCorpseVoice / SetOverrideVoiceType")
    pose = extract_function(bed, "PoseBedCorpseInFurniture")
    if "SnapIntoInteraction" not in pose or "KillBedCorpse" not in pose:
        fail("PoseBedCorpseInFurniture must SnapIntoInteraction + KillBedCorpse")
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
    handle = extract_function(main_txt, "HandlePotentialKnifeKill")
    if "KnifeKillCreditSuppressed" not in handle or "IsNonGameplayCorpse" not in handle:
        fail("HandlePotentialKnifeKill must skip bed gift / wound lab corpses")
    if "SatiateHunger" in handle:
        fail("HandlePotentialKnifeKill must not call SatiateHunger directly (ProcessKnifeKill does)")
    track = extract_function(main_txt, "TrackLivingNear")
    if "IsNonGameplayCorpse" not in track:
        fail("TrackLivingNear must skip bed gift / wound lab corpses")
    if re.search(r"\bSetProtected\s*\(", bed):
        fail("must not SetProtected on shared ActorBase")
    if "Utility.Wait" not in pose:
        fail("PoseBedCorpseInFurniture must Wait briefly after snap")
    if "IsInMenuMode" not in pose:
        fail("PoseBedCorpseInFurniture must skip Wait while MCM/menu is open")
    if "SnapBedCorpseToAnchor" not in pose:
        fail("PoseBedCorpseInFurniture must ragdoll-fallback if snap fails")
    if "Debug.Notification" not in pose or "SnapIntoInteraction FAILED" not in pose:
        fail("PoseBedCorpseInFurniture must always toast clearly when snap fails")
    warm = extract_function(bed, "MaybeWarmBedGiftBody")
    if "CreateBedCorpseAt" not in warm or "BedPresentedThisSleep" not in warm:
        fail("MaybeWarmBedGiftBody must CreateBedCorpseAt and skip during presented cycle")
    start = extract_function(bed, "HandlePlayerSleepStart")
    if "TrySpawnBedCorpse" in start or "CreateBedCorpseAt" in start or "PlaceAtMe" in start:
        fail("HandlePlayerSleepStart must not spawn (anchor only)")
    stop = extract_function(bed, "HandlePlayerSleepStop")
    if "PresentBedCorpseOnWake" not in stop:
        fail("HandlePlayerSleepStop must PresentBedCorpseOnWake when corpse ready")
    if "TrySpawnBedCorpse" in stop or "CreateBedCorpseAt" in stop or "PlaceAtMe" in stop:
        fail("HandlePlayerSleepStop must not spawn")
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
    if "BedDespawnAtReal" not in present:
        fail("PresentBedCorpseOnWake must set BedDespawnAtReal deadline")
    if "ScheduleBedGiftDecayOverlays" not in present:
        fail("PresentBedCorpseOnWake must ScheduleBedGiftDecayOverlays fallback if not pre-applied")
    if "MaybeApplyBedGiftDecayOverlays()" in present:
        fail("PresentBedCorpseOnWake must not sync-apply decay overlays")
    warm = extract_function(bed, "MaybeWarmBedGiftBody")
    if "ScheduleBedGiftDecayOverlays" not in warm:
        fail("MaybeWarmBedGiftBody must schedule decay while parked/disabled")
    sleep_start = extract_function(bed, "HandlePlayerSleepStart")
    if "MaybeApplyBedGiftDecayOverlays" not in sleep_start:
        fail("HandlePlayerSleepStart must finish pending decay before wake Enable")
    if "MaybeSpeakBedGiftWakeToast" not in present:
        fail("PresentBedCorpseOnWake must MaybeSpeakBedGiftWakeToast")
    wake = extract_function(bed, "MaybeSpeakBedGiftWakeToast")
    if "GetBedGiftWakeToast" not in wake:
        fail("MaybeSpeakBedGiftWakeToast must use ModConfig via GetBedGiftWakeToast")
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
    settings = SETTINGS.read_text(encoding="utf-8")
    if "bBedGiftEverySleep=1" not in settings:
        fail("settings.ini must default bBedGiftEverySleep=1 for testing")
    bed = BED_PSC.read_text(encoding="utf-8", errors="replace")
    if "BED_GIFT_COOLDOWN_DAYS" in bed:
        fail("BedGift must not hardcode BED_GIFT_COOLDOWN_DAYS — use ModConfig")
    m = re.search(r"Bool Function BedGiftCooldownReady\(\)(.*?)EndFunction", bed, re.S)
    if not m or "IsBedGiftEverySleep" not in m.group(1):
        fail("BedGiftCooldownReady must honor IsBedGiftEverySleep")
    if "GetBedGiftCooldownDays" not in m.group(1):
        fail("BedGiftCooldownReady must use GetBedGiftCooldownDays from ModConfig")
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
    test_alias(alias)
    test_main_facade(main_text)
    test_bed_script(bed_text)
    test_esm(find_esm(args.esm))
    test_config_mcm_deploy()
    print("All bed-hallucination (G1) contracts passed.")


if __name__ == "__main__":
    main()
