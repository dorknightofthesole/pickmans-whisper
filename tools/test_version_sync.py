#!/usr/bin/env python3
"""Mod version stays in sync across the three places that show it.

`fomod/info.xml` is the source of truth — `package_mo2_zip.read_version()` reads it
to name the dist zip. The Papyrus `MOD_VERSION` and the MCM header are display
copies, so this asserts they still agree instead of pinning any literal version.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFO_XML = ROOT / "fomod" / "info.xml"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MCM_JSON = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def source_version() -> str:
    version = ET.parse(INFO_XML).getroot().findtext("Version")
    if not version or not version.strip():
        fail(f"{INFO_XML.name} must declare a non-empty <Version>")
        return ""
    version = version.strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail(f"{INFO_XML.name} <Version> must be major.minor.patch; found {version!r}")
    return version


def test_papyrus_version(version: str) -> None:
    src = MAIN_PSC.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'(?m)^String MOD_VERSION\s*=\s*"([^"]+)"', src)
    if not m:
        fail(f"{MAIN_PSC.name} must declare String MOD_VERSION")
        return
    if m.group(1) != version:
        fail(f"{MAIN_PSC.name} MOD_VERSION is {m.group(1)!r}; info.xml says {version!r}")
        return

    # Any other version literal in Main is a copy that will go stale.
    strays = {
        found
        for found in re.findall(r'"[^"]*?(\d+\.\d+\.\d+)[^"]*?"', src)
        if found != version
    }
    if strays:
        fail(
            f"{MAIN_PSC.name} has stale version literal(s) {sorted(strays)}; "
            "build strings from MOD_VERSION instead"
        )
        return
    ok(f"Main MOD_VERSION matches info.xml ({version}) with no stray literals")


def test_mcm_version(version: str) -> None:
    txt = MCM_JSON.read_text(encoding="utf-8", errors="ignore")
    shown = re.findall(r"Version (\d+\.\d+\.\d+)", txt)
    if not shown:
        fail(f"{MCM_JSON.name} must show a 'Version <x.y.z>' header")
        return
    wrong = [v for v in shown if v != version]
    if wrong:
        fail(f"{MCM_JSON.name} shows version {wrong}; info.xml says {version!r}")
        return
    ok(f"MCM header shows {version}")


def test_deploy_gate_runs_this() -> None:
    for rel in ("tools/build-deploy-local.ps1", "tools/build-deploy-local.sh"):
        script = ROOT / rel
        if not script.is_file():
            continue
        if "test_version_sync.py" not in script.read_text(encoding="utf-8", errors="ignore"):
            fail(f"{rel} must run test_version_sync.py")
            return
    ok("deploy gate runs this test")


def main() -> int:
    version = source_version()
    if version:
        test_papyrus_version(version)
        test_mcm_version(version)
    test_deploy_gate_runs_this()
    if failures:
        print(f"\n{len(failures)} version-sync contract(s) failed.")
        return 1
    print("All version-sync contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
