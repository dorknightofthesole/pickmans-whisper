#!/usr/bin/env python3
"""Contracts for PickmansWhisperBuffTrackerScript — Slice H P5 bonus (END buff for eating
a ripe corpse), and the general shape it should keep for future buffs added to this file.

Locks:
  - Endurance ActorValue FormID (0x000002C4) verified against Fallout4.esm
  - ApplyEatRipeCorpseEndBuff: reads amount/max/hours from Main (ModConfig-sourced),
    fails loud (no baked fallback) if any are missing/invalid
  - Cap clamps the per-application amount to remaining headroom; at cap, no ModValue
    but the game-time expiry timer still refreshes
  - Expiry is self-contained StartTimerGameTime / OnTimerGameTime (game-time hours)
  - InitBuffTracker from Main RegisterBuffTracker on quest init / load (re-arm or expire)
  - BuffTracker owns StartTimerGameTime expiry (no TickEndBuffExpiry)
  - Script attached to Main quest VMAD; ModConfig ateRipeCorpseEndBuff* parsed + reset

Usage:
  python tools/test_buff_tracker.py
  python tools/test_buff_tracker.py --esm "<path>/Fallout4.esm"
"""
from __future__ import annotations

import argparse
import re
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
BUFF = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperBuffTrackerScript.psc"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MODCFG = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
STUB_SCRIPT_OBJECT = ROOT / "tools" / "stubs" / "ScriptObject.psc"
MOD_CONFIG = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"

FID_AV_ENDURANCE = 0x000002C4
EDID_ENDURANCE = b"Endurance"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Function|Bool Function|Int Function|String Function|Float Function)\s+{name}\s*\(",
        text,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
    return text[start : start + end_m.end()]


def extract_event(text: str, name: str) -> str:
    m = re.search(rf"Event\s+{name}\s*\(", text)
    if not m:
        fail(f"missing event {name}")
    start = m.start()
    end_m = re.search(r"\nEndEvent\b", text[start:])
    if not end_m:
        fail(f"no EndEvent for {name}")
    return text[start : start + end_m.end()]


def parse_modconfig_active_keys(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip()
    return out


def test_modconfig() -> None:
    keys = parse_modconfig_active_keys(MOD_CONFIG)
    for key, want in (
        ("ateRipeCorpseEndBuffAmount", "2"),
        ("ateRipeCorpseEndBuffMaxDelta", "4"),
        ("ateRipeCorpseEndBuffHours", "2"),
    ):
        if key not in keys or not keys[key]:
            fail(f"ModConfig must ship {key}")
        if keys[key] != want:
            fail(f"ModConfig {key} = {keys[key]!r}, expected {want!r}")
    ok("ModConfig END buff keys ship with expected shipped values (2 / 4 / 2h)")


def test_stubs() -> None:
    stub = STUB_SCRIPT_OBJECT.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"Function\s+StartTimerGameTime\s*\(\s*Float", stub):
        fail("tools/stubs/ScriptObject.psc must declare StartTimerGameTime (real FO4)")
    if not re.search(r"Function\s+CancelTimerGameTime\s*\(\s*Int", stub):
        fail("tools/stubs/ScriptObject.psc must declare CancelTimerGameTime (real FO4)")
    if "Event OnTimerGameTime(Int aiTimerID)" not in stub:
        fail("tools/stubs/ScriptObject.psc must declare OnTimerGameTime")
    ok("ScriptObject stub declares StartTimerGameTime / CancelTimerGameTime / OnTimerGameTime")


def test_buff_script() -> None:
    if not BUFF.is_file():
        fail(f"missing {BUFF}")
    text = BUFF.read_text(encoding="utf-8", errors="replace")

    if "extends Quest" not in text.splitlines()[0]:
        fail("PickmansWhisperBuffTrackerScript must extend Quest (attached to Main quest VMAD)")
    if "FID_AV_ENDURANCE = 0x000002C4" not in text:
        fail("FID_AV_ENDURANCE must be 0x000002C4 (Fallout4.esm Endurance)")
    if "TickEndBuffExpiry" in text:
        fail("TickEndBuffExpiry retired — BuffTracker owns StartTimerGameTime expiry")

    apply_fn = extract_function(text, "ApplyEatRipeCorpseEndBuff")
    for needle in (
        "ModConfigAlias.GetEatRipeCorpseEndBuffAmount()",
        "ModConfigAlias.GetEatRipeCorpseEndBuffMaxDelta()",
        "ModConfigAlias.GetEatRipeCorpseEndBuffHours()",
    ):
        if needle not in apply_fn:
            fail(f"ApplyEatRipeCorpseEndBuff must call Main().{needle}")
    if "amount <= 0.0 || maxDelta <= 0.0 || hours <= 0.0" not in apply_fn:
        fail("ApplyEatRipeCorpseEndBuff must fail loud when ModConfig values are missing/invalid (no baked fallback)")
    if "maxDelta - EndBuffAppliedDelta" not in apply_fn:
        fail("ApplyEatRipeCorpseEndBuff must compute headroom as maxDelta - EndBuffAppliedDelta")
    if "addAmount > headroom" not in apply_fn:
        fail("ApplyEatRipeCorpseEndBuff must clamp the per-application amount to remaining headroom")
    if "player.ModValue(EnduranceAV, addAmount)" not in apply_fn:
        fail("ApplyEatRipeCorpseEndBuff must ModValue the clamped amount, not the raw configured amount")
    if "now + (hours / 24.0)" not in apply_fn:
        fail("ApplyEatRipeCorpseEndBuff must set expiry to now + hours/24 (game-time days bookkeeping)")
    if "headroom <= 0.0" not in apply_fn:
        fail("ApplyEatRipeCorpseEndBuff must handle the at-cap case explicitly (no ModValue, but still refresh expiry)")
    if apply_fn.count("ArmEndBuffExpiryTimer(hours)") < 2:
        fail("ApplyEatRipeCorpseEndBuff must ArmEndBuffExpiryTimer on both cap-refresh and apply paths")

    arm = extract_function(text, "ArmEndBuffExpiryTimer")
    if "StartTimerGameTime(hours, TIMER_END_BUFF)" not in arm:
        fail("ArmEndBuffExpiryTimer must StartTimerGameTime(hours, TIMER_END_BUFF) (interval = game hours)")
    if "CancelTimerGameTime(TIMER_END_BUFF)" not in arm:
        fail("ArmEndBuffExpiryTimer must CancelTimerGameTime before re-arm")

    on_timer = extract_event(text, "OnTimerGameTime")
    if "ExpireEndBuff(" not in on_timer:
        fail("OnTimerGameTime must call ExpireEndBuff")
    if "TIMER_END_BUFF" not in on_timer:
        fail("OnTimerGameTime must gate on TIMER_END_BUFF")

    expire = extract_function(text, "ExpireEndBuff")
    if "player.ModValue(EnduranceAV, -EndBuffAppliedDelta)" not in expire:
        fail("ExpireEndBuff must remove the full applied delta in one ModValue call")
    if "EndBuffAppliedDelta = 0.0" not in expire or "EndBuffExpiryGameTime = 0.0" not in expire:
        fail("ExpireEndBuff must clear both bookkeeping fields after removal")

    init = extract_function(text, "InitBuffTracker")
    if "ReconcileEndBuffTimer()" not in init:
        fail("InitBuffTracker must ReconcileEndBuffTimer (load re-arm / expire)")

    reconcile = extract_function(text, "ReconcileEndBuffTimer")
    if "ExpireEndBuff(" not in reconcile:
        fail("ReconcileEndBuffTimer must ExpireEndBuff when load finds past expiry")
    if "ArmEndBuffExpiryTimer(" not in reconcile:
        fail("ReconcileEndBuffTimer must ArmEndBuffExpiryTimer for remaining hours")

    ok("BuffTrackerScript apply + StartTimerGameTime expiry + load reconcile")


def test_main_wiring() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")
    facade = extract_function(text, "BuffTracker")
    if "PickmansWhisperBuffTrackerScript" not in facade:
        fail("MainQuestScript.BuffTracker() facade must cast to PickmansWhisperBuffTrackerScript")

    reg = extract_function(text, "RegisterBuffTracker")
    if "InitBuffTracker()" not in reg:
        fail("RegisterBuffTracker must call buffs.InitBuffTracker()")
    if "BuffTracker script missing" not in reg:
        fail("RegisterBuffTracker must fail loud when BuffTracker unbound")

    quest_init = extract_event(text, "OnQuestInit")
    if "RegisterBuffTracker()" not in quest_init:
        fail("OnQuestInit must RegisterBuffTracker")
    resume = extract_function(text, "HandleGameResume")
    if "RegisterBuffTracker()" not in resume:
        fail("HandleGameResume must RegisterBuffTracker")
    arm = extract_function(text, "ArmRuntimeLoops")
    if "RegisterBuffTracker()" not in arm:
        fail("ArmRuntimeLoops must RegisterBuffTracker (load re-arm path)")

    if "ModConfigAlias Auto" not in text:
        fail("Main must expose ModConfigAlias for BuffTracker END buff keys")

    modcfg = MODCFG.read_text(encoding="utf-8", errors="replace")
    load_cfg = extract_function(modcfg, "LoadModConfig")
    for key in ("ateRipeCorpseEndBuffAmount", "ateRipeCorpseEndBuffMaxDelta", "ateRipeCorpseEndBuffHours"):
        if f'key == "{key}"' not in load_cfg:
            fail(f"LoadModConfig must parse {key}")
    for field in (
        "nextEatRipeCorpseEndBuffAmount = -1.0",
        "nextEatRipeCorpseEndBuffMaxDelta = -1.0",
        "nextEatRipeCorpseEndBuffHours = -1.0",
    ):
        if field not in load_cfg:
            fail(f"LoadModConfig must reset {field} at the top like other ModConfig fields")

    ok("MainQuestScript RegisterBuffTracker on init/load + ModConfig parse/reset")


def test_buff_expiry_self_contained() -> None:
    text = BUFF.read_text(encoding="utf-8", errors="replace")
    if "StartTimerGameTime" not in text:
        fail("BuffTracker must use StartTimerGameTime for expiry")
    if "TickEndBuffExpiry" in text:
        fail("BuffTracker must not define TickEndBuffExpiry (self-contained timer)")
    ok("BuffTracker StartTimerGameTime expiry; no TickEndBuffExpiry")


def test_esp_builder() -> None:
    text = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if '"PickmansWhisperBuffTrackerScript"' not in text:
        fail("build_hunger_spell_esp.py must attach PickmansWhisperBuffTrackerScript to the Main quest VMAD")
    ok("ESP builder attaches BuffTrackerScript to Main quest")


def test_deploy_gate() -> None:
    for path, needle in (
        (DEPLOY_PS1, "PickmansWhisperBuffTrackerScript.psc"),
        (DEPLOY_SH, "PickmansWhisperBuffTrackerScript.psc"),
    ):
        text = path.read_text(encoding="utf-8", errors="replace")
        if needle not in text:
            fail(f"{path.name} must compile/deploy PickmansWhisperBuffTrackerScript")
    text = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "test_buff_tracker.py" not in text:
        fail("build-deploy-local.ps1 must run test_buff_tracker.py")
    ok("deploy gate compiles BuffTrackerScript + runs this contract test")


def find_esm(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    load_dotenv()
    import os

    env = os.environ.get("FALLOUT4_ESM")
    if env and Path(env).is_file():
        return Path(env)
    return None


def get_record_edid_zlib(data: bytes, sig: bytes, fid: int) -> bytes | None:
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
        print("SKIP ESM checks: Fallout4.esm not found (set FALLOUT4_ESM in .env, env, or --esm)")
        return
    data = esm.read_bytes()
    got = get_record_edid_zlib(data, b"AVIF", FID_AV_ENDURANCE)
    if got != EDID_ENDURANCE:
        fail(f"FID 0x{FID_AV_ENDURANCE:06X} EDID {got!r} != {EDID_ENDURANCE!r}")
    ok("Endurance ActorValue FormID verified against Fallout4.esm")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--esm", default=None, help="Path to Fallout4.esm")
    args = ap.parse_args()

    test_modconfig()
    test_stubs()
    test_buff_script()
    test_main_wiring()
    test_buff_expiry_self_contained()
    test_esp_builder()
    test_deploy_gate()
    test_esm(find_esm(args.esm))
    print("All buff tracker (Slice H P5 bonus) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
