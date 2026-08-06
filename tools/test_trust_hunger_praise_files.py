#!/usr/bin/env python3
"""Trust / Hunger / Praise — files-only banks + ModConfig withdrawal toast.

Locks:
  - TrustLines.txt / HungerLines.txt / PraiseLines.txt exist under config/
  - Main Load* uses VoiceAlias.LoadStageBank (no UseBuiltin / no Pick hard-coded Returns)
  - DebugReloadLines fail-loud when VoiceAlias unbound; labels files-only
  - hungerWithdrawalToast in ModConfig.txt + ModConfigScript + Main withdrawal path
  - Deploy gate runs this contract

Usage:
  python tools/test_trust_hunger_praise_files.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Data" / "PickmansWhisper" / "config"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MOD = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
DEPLOY = ROOT / "tools" / "build-deploy-local.ps1"

BANKS = ("TrustLines.txt", "HungerLines.txt", "PraiseLines.txt")


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


def main() -> None:
    for name in BANKS:
        path = CONFIG / name
        if not path.is_file():
            fail(f"missing {path}")
        body = [
            ln.strip()
            for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if len(body) < 3:
            fail(f"{name} must ship usable lines (got {len(body)})")
    ok("Trust/Hunger/Praise .txt banks present with lines")

    main_psc = MAIN.read_text(encoding="utf-8", errors="replace")
    if "UseBuiltin" in main_psc:
        fail("Main must not keep UseBuiltin* fallbacks")
    for needle in (
        'Return "You hear me',
        'Return "The blade is hungry',
        'Return "Yes...',
        "The quiet ends. The knife remembers.",
        "A restless edge... the blade wants use.",
    ):
        if needle in main_psc:
            fail(f"Main must not hard-code spoken fallback {needle!r}")

    for fn, file_name in (
        ("LoadTrustLines", "TrustLines.txt"),
        ("LoadHungerLines", "HungerLines.txt"),
        ("LoadPraiseLines", "PraiseLines.txt"),
    ):
        body = extract_function(main_psc, fn)
        if f'LoadStageBank("{file_name}"' not in body:
            fail(f"{fn} must VoiceAlias.LoadStageBank({file_name!r})")
        if "VoiceAlias unbound" not in body:
            fail(f"{fn} must fail-loud when VoiceAlias unbound")

    for pick in ("PickTrustLine", "PickHungerLine", "PickPraiseLine"):
        body = extract_function(main_psc, pick)
        if 'Return ""' not in body:
            fail(f"{pick} must Return \"\" when bank empty (files-only)")
        if re.search(r'Return\s+"[^"]{8,}"', body):
            fail(f"{pick} must not Return a hard-coded spoken line")

    load_banks = extract_function(main_psc, "LoadLineBanks")
    for needle in (
        "ModConfigAlias.LoadModConfig()",
        "VoiceAlias.LoadVoiceBanks()",
        "LoadTrustLines()",
        "LoadHungerLines()",
        "LoadPraiseLines()",
        "LoadTargetOverrides()",
    ):
        if needle not in load_banks:
            fail(f"LoadLineBanks must call {needle}")
    if "ERROR LoadLineBanks — VoiceAlias unbound" not in load_banks:
        fail("LoadLineBanks must Trace when VoiceAlias unbound")
    ok("Main Load*/Pick*/LoadLineBanks files-only + fail-loud")

    reload_fn = extract_function(main_psc, "DebugReloadLines")
    if "If !VoiceAlias" not in reload_fn and "If VoiceAlias == None" not in reload_fn:
        # Papyrus uses If !VoiceAlias
        if "ERROR DebugReloadLines — VoiceAlias unbound" not in reload_fn:
            fail("DebugReloadLines must fail-loud when VoiceAlias unbound")
    if "ERROR DebugReloadLines — VoiceAlias unbound" not in reload_fn:
        fail("DebugReloadLines must Trace ERROR when VoiceAlias unbound")
    if "LoadLineBanks()" not in reload_fn:
        fail("DebugReloadLines must LoadLineBanks")
    if "builtin" in reload_fn.casefold():
        fail("DebugReloadLines must not label banks as builtin")
    if "Trust (files)" not in reload_fn:
        fail("DebugReloadLines must label Trust as files")
    ok("DebugReloadLines fail-loud + files-only labels")

    mod_txt = (CONFIG / "ModConfig.txt").read_text(encoding="utf-8", errors="replace")
    if "hungerWithdrawalToast=The quiet ends. The knife remembers." not in mod_txt:
        fail("ModConfig.txt must ship hungerWithdrawalToast default")
    mod_psc = MOD.read_text(encoding="utf-8", errors="replace")
    if "String Property HungerWithdrawalToast" not in mod_psc:
        fail("ModConfigScript must expose HungerWithdrawalToast")
    if 'key == "hungerWithdrawalToast"' not in mod_psc:
        fail("LoadModConfig must parse hungerWithdrawalToast")
    hunger = extract_function(main_psc, "RunHungerTick")
    if "HungerWithdrawalToast" not in hunger:
        fail("RunHungerTick must toast ModConfigAlias.HungerWithdrawalToast")
    if "The quiet ends" in hunger:
        fail("RunHungerTick must not hard-code withdrawal toast text")
    band = extract_function(main_psc, "MaybeToastHungerBand")
    if re.search(r'line\s*=\s*"[^"]+"', band):
        fail("MaybeToastHungerBand must not assign hard-coded fallback lines")
    ok("hungerWithdrawalToast ModConfig + no band hard-coded fallbacks")

    deploy = DEPLOY.read_text(encoding="utf-8", errors="replace")
    if "test_trust_hunger_praise_files.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_trust_hunger_praise_files.py")
    ok("deploy gate wires this contract")

    print("All Trust/Hunger/Praise files-only contracts passed.")


if __name__ == "__main__":
    main()
