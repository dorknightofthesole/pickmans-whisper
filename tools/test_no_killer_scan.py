#!/usr/bin/env python3
"""KillerScan retirement — script/builder/deploy must not reference the scanner.

Usage:
  python tools/test_no_killer_scan.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = ROOT / "Data" / "Scripts" / "Source" / "User"
KILLER_PSC = USER / "PickmansWhisperKillerScanScript.psc"
MAIN = USER / "PickmansWhisperMainQuestScript.psc"
TARGET_SCAN = USER / "PickmansWhisperTargetScanScript.psc"
ESP_BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
PACKAGE = ROOT / "tools" / "package_mo2_zip.py"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(src: str, name: str) -> str:
    m = re.search(rf"(?:Bool |Float |Int |String |Function )?Function {re.escape(name)}\(", src)
    if not m:
        m = re.search(rf"Function {re.escape(name)}\(", src)
    if not m:
        fail(f"missing Function {name}")
    start = m.start()
    end = src.find("\nEndFunction", start)
    if end < 0:
        fail(f"unclosed Function {name}")
    return src[start : end + len("\nEndFunction")]


def main() -> None:
    if KILLER_PSC.is_file():
        fail("PickmansWhisperKillerScanScript.psc must be deleted")
    ok("PickmansWhisperKillerScanScript.psc absent")

    esp = ESP_BUILDER.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperKillerScanScript" in esp:
        fail("build_hunger_spell_esp.py main_scripts must not include PickmansWhisperKillerScanScript")
    ok("ESP builder has no KillerScan script")

    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperKillerScanScript" in deploy or "$PscKillerScan" in deploy:
        fail("build-deploy-local.ps1 must not compile/deploy KillerScan")
    if "test_killer_scan_bus.py" in deploy:
        fail("build-deploy-local.ps1 must not run test_killer_scan_bus.py")
    if "test_no_killer_scan.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_no_killer_scan.py")
    ok("deploy gate: no KillerScan; runs test_no_killer_scan.py")

    package = PACKAGE.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperKillerScanScript" in package:
        fail("package_mo2_zip.py must not list PickmansWhisperKillerScanScript")
    ok("package_mo2_zip has no KillerScan stem")

    target = TARGET_SCAN.read_text(encoding="utf-8", errors="replace")
    scan = extract_function(target, "ScanAndCleanTargets")
    if 'CallFunctionNoWait("RunHungerTick"' not in scan:
        fail('TargetScan ScanAndCleanTargets must CallFunctionNoWait("RunHungerTick"')
    ok("TargetScan ScanAndCleanTargets CallFunctionNoWait RunHungerTick")
    if "VoiceAlias.CallFunctionNoWait" not in scan or 'CallFunctionNoWait("MaybeSpeakTrustLine"' not in scan:
        fail(
            "TargetScan must CallFunctionNoWait MaybeSpeakTrustLine on MainQuest.VoiceAlias "
            "(not Main)"
        )
    ok("TargetScan hosts MaybeSpeakTrustLine via VoiceAlias")

    main_txt = MAIN.read_text(encoding="utf-8", errors="replace")
    if re.search(r"Function\s+KillerScan\s*\(", main_txt):
        fail('Main must not declare Function KillerScan(')
    if "PickmansWhisperKillerScanScript" in main_txt:
        fail("Main must not reference PickmansWhisperKillerScanScript")
    ok("Main has no KillerScan facade / type refs")

    print("All KillerScan retirement contracts passed.")


if __name__ == "__main__":
    main()
