#!/usr/bin/env python3
"""Contracts for Slice G1 — bed corpse hallucination (Actor NPC).

Locks:
  - FO4 sleep stubs; PlayerAlias owns RegisterForPlayerSleep
  - Single gameplay PlaceAtMe: MaybeWarmBedGiftBody → LCharRaiderFemale + Kill + Strip
  - SleepStart/Stop never spawn; Present or skip; no retries
  - FID_BED_SPAWN_LVLN matches Fallout4.esm LCharRaiderFemale
  - MCM bBedGift + DebugForceBedGift / DebugClearBedGift
  - BedGiftLines.txt loaded via LoadLineBanks

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
ALIAS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
SCRIPT_STUB = ROOT / "tools" / "stubs" / "ScriptObject.psc"
BED_LINES = ROOT / "Data" / "PickmansWhisper" / "config" / "BedGiftLines.txt"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"

FID_BED_SPAWN = 0x000D39F5
EDID_BED_SPAWN = b"LCharRaiderFemale"


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


def get_lvln_edid(data: bytes, fid: int) -> bytes | None:
    target = fid.to_bytes(4, "little")
    start = 0
    while True:
        i = data.find(b"LVLN", start)
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


def test_psc(text: str) -> None:
    if re.search(r"\bRegisterForPlayerSleep\s*\(", text):
        fail("main quest must not RegisterForPlayerSleep — use PlayerAlias")
    if "Event OnPlayerSleepStart" in text or "Event OnPlayerSleepStop" in text:
        fail("main quest must not declare OnPlayerSleep*")
    start = extract_function(text, "HandlePlayerSleepStart")
    if "TrySpawnBedCorpse" in start or "CreateBedCorpseAt" in start or "PlaceAtMe" in start:
        fail("HandlePlayerSleepStart must not spawn (anchor only)")
    stop = extract_function(text, "HandlePlayerSleepStop")
    if "PresentBedCorpseOnWake" not in stop:
        fail("HandlePlayerSleepStop must PresentBedCorpseOnWake when corpse ready")
    if "TrySpawnBedCorpse" in stop or "CreateBedCorpseAt" in stop or "PlaceAtMe" in stop:
        fail("HandlePlayerSleepStop must not spawn")
    if "TIMER_BED_PRESENT" in text:
        fail("TIMER_BED_PRESENT retired — no wake retries")
    if "FID_BED_CORPSE_STAT" in text or "RaiderDismemberedBody01" in text:
        fail("STAT clutter path retired — use LCharRaiderFemale Actor")
    if "Actor BedCorpse" not in text:
        fail("BedCorpse must be Actor")
    create = extract_function(text, "CreateBedCorpseAt")
    if "FID_BED_SPAWN_LVLN" not in create or "PlaceAtMe" not in create:
        fail("CreateBedCorpseAt must PlaceAtMe LCharRaiderFemale")
    if ".Kill(" in create or "KillSilent" in create:
        fail("CreateBedCorpseAt warm path must keep NPC alive until Present pose")
    if "ParkWarmedBedCorpse" not in create or "PoseBedCorpseInFurniture" not in create:
        fail("CreateBedCorpseAt must park (warm) or PoseBedCorpseInFurniture (debug)")
    if not re.search(r"PlaceAtMe\([^)]*False\s*\)", create):
        fail("CreateBedCorpseAt PlaceAtMe should use InitiallyDisabled=False")
    pose = extract_function(text, "PoseBedCorpseInFurniture")
    if "SnapIntoInteraction" not in pose or "KillSilent" not in pose:
        fail("PoseBedCorpseInFurniture must SnapIntoInteraction + KillSilent")
    if "Utility.Wait" not in pose:
        fail("PoseBedCorpseInFurniture must Wait briefly after snap")
    if "SnapBedCorpseToAnchor" not in pose:
        fail("PoseBedCorpseInFurniture must ragdoll-fallback if snap fails")
    if "Debug.Notification" not in pose or "SnapIntoInteraction FAILED" not in pose:
        fail("PoseBedCorpseInFurniture must always toast clearly when snap fails")
    warm = extract_function(text, "MaybeWarmBedGiftBody")
    if "CreateBedCorpseAt" not in warm or "BedPresentedThisSleep" not in warm:
        fail("MaybeWarmBedGiftBody must CreateBedCorpseAt and skip during presented cycle")
    if "MaybeWarmBedGiftBody()" not in text:
        fail("killscan must call MaybeWarmBedGiftBody")
    strip = extract_function(text, "StripBedCorpse")
    if "UnequipAll" not in strip or "RemoveAllItems" not in strip:
        fail("StripBedCorpse must UnequipAll + RemoveAllItems")
    snap = extract_function(text, "SnapBedCorpseToAnchor")
    if "SetPosition" not in snap or "ForceAddRagdollToWorld" not in snap:
        fail("SnapBedCorpseToAnchor must SetPosition + ForceAddRagdollToWorld")
    if "MoveTo" in snap:
        fail("SnapBedCorpseToAnchor must not MoveTo furniture")
    present = extract_function(text, "PresentBedCorpseOnWake")
    if "PoseBedCorpseInFurniture" not in present:
        fail("PresentBedCorpseOnWake must PoseBedCorpseInFurniture when still alive")
    if "PlaceAtMe" in present:
        fail("PresentBedCorpseOnWake must not PlaceAtMe")
    if "TIMER_BED_DESPAWN" not in present:
        fail("PresentBedCorpseOnWake must StartTimer TIMER_BED_DESPAWN")
    if "0x000D39F5" not in text:
        fail("PSC must declare FID_BED_SPAWN_LVLN = 0x000D39F5")
    load = extract_function(text, "LoadLineBanks")
    if "LoadBedGiftLines()" not in load:
        fail("LoadLineBanks must LoadBedGiftLines")
    extract_function(text, "DebugForceBedGift")
    extract_function(text, "DebugClearBedGift")
    ok("PSC bed gift SnapIntoInteraction + KillSilent + single warm spawn")


def test_esm(esm: Path | None) -> None:
    if not esm:
        fail("Fallout4.esm not found — set FALLOUT4_ESM or pass --esm")
    data = esm.read_bytes()
    edid = get_lvln_edid(data, FID_BED_SPAWN)
    if edid is None:
        fail(f"LVLN {hex(FID_BED_SPAWN)} not found in {esm}")
    if edid != EDID_BED_SPAWN:
        fail(f"FID {hex(FID_BED_SPAWN)} EDID {edid!r} != {EDID_BED_SPAWN!r}")
    ok(f"FID_BED_SPAWN_LVLN = LCharRaiderFemale ({esm.name})")


def test_config_mcm() -> None:
    if not BED_LINES.is_file():
        fail(f"missing {BED_LINES}")
    mcm = MCM.read_text(encoding="utf-8")
    if "bBedGift:Voice" not in mcm or "DebugForceBedGift" not in mcm:
        fail("MCM must have bed gift voice + debug force")
    settings = SETTINGS.read_text(encoding="utf-8")
    if "bBedGiftEverySleep=1" not in settings:
        fail("settings.ini must default bBedGiftEverySleep=1 for testing")
    psc = PSC.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Bool Function BedGiftCooldownReady\(\)(.*?)EndFunction", psc, re.S)
    if not m or "IsBedGiftEverySleep" not in m.group(1):
        fail("BedGiftCooldownReady must honor IsBedGiftEverySleep")
    if "test_bed_hallucination.py" not in DEPLOY_PS1.read_text(encoding="utf-8", errors="replace"):
        fail("build-deploy-local.ps1 must run test_bed_hallucination.py")
    ok("BedGiftLines + MCM + deploy slot")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--esm", default=None)
    args = ap.parse_args()
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    alias = ALIAS.read_text(encoding="utf-8", errors="replace")
    test_stubs()
    test_alias(alias)
    test_psc(text)
    test_esm(find_esm(args.esm))
    test_config_mcm()
    print("All bed-hallucination (G1) contracts passed.")


if __name__ == "__main__":
    main()
