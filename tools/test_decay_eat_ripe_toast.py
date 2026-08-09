#!/usr/bin/env python3
"""Contracts for Slice H P4 — Cannibal-perk "eat her before she's too ripe" nag toast.

Locks:
  - ModConfig eatRipeCorpseToast ships with {name} support
  - LoadModConfig parses eatRipeCorpseToast
  - MainQuestScript.MaybeToastEatRipeCorpse: Cannibal-perk gate, {name} -> "her" fallback
    when unnamed, once-per-game-hour shared cooldown, no MCM toggle (ModConfig-only)
  - PlayerHasCannibalPerk checks all three Fallout4.esm Cannibal ranks (additive ranks)
  - ResolveVanillaForms lazy-loads the three Cannibal perk forms from Fallout4.esm
  - CorpseDecay HandleCorpseDecay calls MaybeToastEatRipeCorpse when the corpse is
    AT the max decay stage (not gated on stage-changed)
  - tools/stubs/Actor.psc declares HasPerk(Perk) Native; tools/stubs/Perk.psc exists

Usage:
  python tools/test_decay_eat_ripe_toast.py
  python tools/test_decay_eat_ripe_toast.py --esm "<path>/Fallout4.esm"
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
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MODCFG = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"
MOD_CONFIG = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
STUB_ACTOR = ROOT / "tools" / "stubs" / "Actor.psc"
STUB_PERK = ROOT / "tools" / "stubs" / "Perk.psc"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"

FID_CANNIBAL_1 = 0x0004B259
FID_CANNIBAL_2 = 0x001D1A62
FID_CANNIBAL_3 = 0x001D1A63
EDID_CANNIBAL = {
    FID_CANNIBAL_1: b"Cannibal01",
    FID_CANNIBAL_2: b"Cannibal02",
    FID_CANNIBAL_3: b"Cannibal03",
}


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
    if not MOD_CONFIG.is_file():
        fail(f"missing {MOD_CONFIG}")
    keys = parse_modconfig_active_keys(MOD_CONFIG)
    if "eatRipeCorpseToast" not in keys or not keys["eatRipeCorpseToast"]:
        fail("ModConfig must ship eatRipeCorpseToast")
    if "{name}" not in keys["eatRipeCorpseToast"]:
        fail("eatRipeCorpseToast should support {name}")
    ok("ModConfig eatRipeCorpseToast ships with {name}")


def test_main_wiring() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")
    modcfg = MODCFG.read_text(encoding="utf-8", errors="replace")
    load_cfg = extract_function(modcfg, "LoadModConfig")
    if 'key == "eatRipeCorpseToast"' not in load_cfg:
        fail("LoadModConfig must parse eatRipeCorpseToast")

    for name in ("PlayerHasCannibalPerk", "MaybeToastEatRipeCorpse", "ResolveVanillaForms"):
        extract_function(text, name)

    resolve = extract_function(text, "ResolveVanillaForms")
    for fid in ("FID_PERK_CANNIBAL_1", "FID_PERK_CANNIBAL_2", "FID_PERK_CANNIBAL_3"):
        if fid not in resolve:
            fail(f"ResolveVanillaForms must lazy-load {fid}")
    for fid, hexval in (
        ("FID_PERK_CANNIBAL_1", f"0x{FID_CANNIBAL_1:08X}"),
        ("FID_PERK_CANNIBAL_2", f"0x{FID_CANNIBAL_2:08X}"),
        ("FID_PERK_CANNIBAL_3", f"0x{FID_CANNIBAL_3:08X}"),
    ):
        if f"{fid} = {hexval}" not in text:
            fail(f"{fid} must be declared as {hexval} (Fallout4.esm Cannibal rank)")

    has_perk = extract_function(text, "PlayerHasCannibalPerk")
    for perk in ("CannibalPerk1", "CannibalPerk2", "CannibalPerk3"):
        if f"HasPerk({perk})" not in has_perk:
            fail(f"PlayerHasCannibalPerk must check HasPerk({perk}) (ranks are additive)")

    toast = extract_function(text, "MaybeToastEatRipeCorpse")
    if "PlayerHasCannibalPerk()" not in toast:
        fail("MaybeToastEatRipeCorpse must gate on PlayerHasCannibalPerk")
    if "GetVictimOverrideName" not in toast:
        fail("MaybeToastEatRipeCorpse must resolve the victim's override name")
    if '= "her"' not in toast:
        fail('MaybeToastEatRipeCorpse must fall back to "her" when unnamed')
    if "ApplyNamePlaceholder" not in toast:
        fail("MaybeToastEatRipeCorpse must ApplyNamePlaceholder for {name} substitution")
    if "LastEatRipeCorpseToastGameTime" not in toast:
        fail("MaybeToastEatRipeCorpse must track LastEatRipeCorpseToastGameTime")
    if "EAT_RIPE_CORPSE_TOAST_MIN_GAME_HOURS" not in toast:
        fail("MaybeToastEatRipeCorpse must gate on EAT_RIPE_CORPSE_TOAST_MIN_GAME_HOURS")
    if "GetCurrentGameTime" not in toast:
        fail("MaybeToastEatRipeCorpse cooldown must use game time (Utility.GetCurrentGameTime)")
    if "Debug.Notification" not in toast:
        fail("MaybeToastEatRipeCorpse must Debug.Notification the toast")
    if "EAT_RIPE_CORPSE_TOAST_MIN_GAME_HOURS = 1.0" not in text:
        fail("EAT_RIPE_CORPSE_TOAST_MIN_GAME_HOURS must be 1.0 (once per game-hour)")

    # Every early-return must Trace why — silent skips cost a full log-archaeology round
    # trip to diagnose (see: the ModConfig-not-reloaded bug this locked down).
    for needle in (
        "eat-ripe-corpse skip | no eatRipeCorpseToast",
        "eat-ripe-corpse skip | player lacks Cannibal perk",
        "eat-ripe-corpse skip | cooldown",
        "eat-ripe-corpse skip | empty line after placeholder",
    ):
        if needle not in toast:
            fail(f"MaybeToastEatRipeCorpse must Trace {needle!r} (no silent skip)")

    if 'MCM.GetModSettingBool(MOD_NAME, "bEatRipeCorpseToast' in text:
        fail("P4 toast is ModConfig-only (empty key = off) — no MCM toggle expected")

    # EnsureDecayStagesLoaded short-circuits LoadModConfig once decay stages already look
    # "ready" (persisted from an earlier load) — a brand-new ModConfig key added later in
    # the same save never gets read until something forces LoadModConfig to run again
    # (MCM Voice > Reload line banks, or a fresh load). LoadModConfig's own reset block
    # must clear EatRipeCorpseToast like every other ModConfig string, so a key removed
    # on a later reload doesn't leave a stale toast behind.
    modcfg = MODCFG.read_text(encoding="utf-8", errors="replace")
    load_cfg = extract_function(modcfg, "LoadModConfig")
    if "EatRipeCorpseToast = \"\"" not in load_cfg:
        fail("LoadModConfig must reset EatRipeCorpseToast at the top like the other ModConfig strings")

    ok("MainQuestScript ModConfig parse + Cannibal perk gate + {name}/her toast wiring")


def test_ambient_dispatch() -> None:
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    handle = extract_function(decay, "HandleCorpseDecay")
    if "MaybeToastEatRipeCorpse" not in handle:
        fail("HandleCorpseDecay must call MaybeToastEatRipeCorpse for corpses at max stage")
    if "ResolveDecayStageForKill(id) == (DECAY_STAGE_COUNT - 1)" not in handle:
        fail("HandleCorpseDecay must check max decay stage (DECAY_STAGE_COUNT - 1) before nagging")
    ok("HandleCorpseDecay calls MaybeToastEatRipeCorpse at max stage")


def test_stubs() -> None:
    actor = STUB_ACTOR.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"Bool\s+Function\s+HasPerk\s*\(\s*Perk\s+\w+\s*\)\s*Native", actor):
        fail("tools/stubs/Actor.psc must declare Bool Function HasPerk(Perk akPerk) Native")
    if not STUB_PERK.is_file():
        fail("missing tools/stubs/Perk.psc")
    perk = STUB_PERK.read_text(encoding="utf-8", errors="replace")
    if "Scriptname Perk extends Form" not in perk:
        fail("tools/stubs/Perk.psc must declare Scriptname Perk extends Form")
    ok("Actor.HasPerk(Perk) stub + Perk.psc stub present")


def test_deploy_gate() -> None:
    text = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "test_decay_eat_ripe_toast.py" not in text:
        fail("build-deploy-local.ps1 must run test_decay_eat_ripe_toast.py")
    ok("deploy gate includes decay eat-ripe-toast contract")


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
    for fid, edid in EDID_CANNIBAL.items():
        got = get_record_edid_zlib(data, b"PERK", fid)
        if got != edid:
            fail(f"FID 0x{fid:06X} EDID {got!r} != {edid!r}")
    ok("Cannibal01/02/03 FormIDs verified against Fallout4.esm PERK records")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--esm", default=None, help="Path to Fallout4.esm")
    args = ap.parse_args()

    if not MAIN.is_file() or not DECAY.is_file():
        fail("missing MainQuestScript or CorpseDecayScript PSC")
    test_modconfig()
    test_main_wiring()
    test_ambient_dispatch()
    test_stubs()
    test_deploy_gate()
    test_esm(find_esm(args.esm))
    print("All decay eat-ripe-toast (Slice H P4) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
