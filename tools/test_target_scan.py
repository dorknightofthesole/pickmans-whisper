#!/usr/bin/env python3
"""TargetScan — MainQuest VMAD form bind only (TrackedTargets is runtime Auto).

Usage:
  python tools/test_target_scan.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY = ROOT / "tools" / "build-deploy-local.ps1"
PACKAGE = ROOT / "tools" / "package_mo2_zip.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperTargetScanScript.psc"
PEX = ROOT / "Data" / "Scripts" / "PickmansWhisperTargetScanScript.pex"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
KILLER = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillerScanScript.psc"
FID_QUEST = 0x01000800


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def find_qust(data: bytes, fid: int) -> bytes | None:
    i = 0
    while True:
        j = data.find(b"QUST", i)
        if j < 0:
            return None
        if j + 24 <= len(data):
            rec_fid = struct.unpack_from("<I", data, j + 12)[0]
            data_size = struct.unpack_from("<I", data, j + 4)[0]
            if rec_fid == fid and j + 24 + data_size <= len(data):
                return data[j + 24 : j + 24 + data_size]
        i = j + 4


def parse_fields(body: bytes) -> list[tuple[bytes, bytes]]:
    out: list[tuple[bytes, bytes]] = []
    j = 0
    while j + 6 <= len(body):
        t = body[j : j + 4]
        sz = struct.unpack_from("<H", body, j + 4)[0]
        out.append((t, body[j + 6 : j + 6 + sz]))
        j += 6 + sz
    return out


def find_vmad_object_prop(vmad: bytes, prop_name: str) -> list[tuple[int, int]]:
    name_b = prop_name.encode("utf-8")
    out: list[tuple[int, int]] = []
    i = 0
    while True:
        j = vmad.find(name_b, i)
        if j < 0:
            break
        if j >= 2:
            ln = struct.unpack_from("<H", vmad, j - 2)[0]
            if ln == len(name_b) and j + ln + 2 + 2 + 4 <= len(vmad):
                off = j + ln
                if vmad[off] == 1:
                    alias_id = struct.unpack_from("<h", vmad, off + 2 + 2)[0]
                    form_id = struct.unpack_from("<I", vmad, off + 2 + 2 + 2)[0]
                    out.append((alias_id, form_id))
        i = j + 1
    return out


def main() -> None:
    psc = PSC.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperMainQuestScript Property MainQuest Auto Const Mandatory" not in psc:
        fail("TargetScan must declare MainQuest Auto Const Mandatory")
    if "PickmansWhisperVoiceAliasScript Property VoiceAlias" in psc:
        fail("TargetScan must not declare VoiceAlias — route via MainQuest.LookingAtTarget")
    if "Actor[] Property TrackedTargets Auto" not in psc:
        fail("TargetScan must declare TrackedTargets Auto")
    if 'CallFunctionNoWait("RegisterTarget"' not in psc:
        fail("TargetScan must CallFunctionNoWait RegisterTarget (fire-and-forget)")
    if "MainQuest.RegisterTarget(" in psc:
        fail("TargetScan must not call RegisterTarget synchronously")
    if "Actor Function GetLookingAt()" not in psc:
        fail("TargetScan must expose GetLookingAt()")
    if "GardenOfEden3.GetCameraTargetReference()" not in psc:
        fail("GetLookingAt must use GardenOfEden3.GetCameraTargetReference")
    if "TODO do something with this in Main" in psc:
        fail("TargetScan must not leave LookFixation TODO stub")
    if "Float Property KILL_CORPSE_RADIUS = 400.0 Auto Const" not in psc:
        fail("TargetScan must own KILL_CORPSE_RADIUS Property Auto Const (SSOT)")
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    killer = KILLER.read_text(encoding="utf-8", errors="replace")
    if "KILL_WATCH_RADIUS = 800.0" in main or "KILL_CORPSE_RADIUS = 400.0" in main:
        fail("Main must not redefine scan radii — TargetScan Properties are SSOT")
    if "KILL_WATCH_RADIUS = 800.0" in killer or "KILL_CORPSE_RADIUS = 400.0" in killer:
        fail("KillerScan must not redefine scan radii — TargetScan Properties are SSOT")
    if "Function TargetScan()" not in main:
        fail("Main must expose TargetScan() façade")

    builder = BUILDER.read_text(encoding="utf-8", errors="replace")
    if '"PickmansWhisperTargetScanScript"' not in builder:
        fail("ESP builder must attach PickmansWhisperTargetScanScript on Main")
    if "target_scan_main_prop" not in builder:
        fail("ESP builder must VMAD-bind TargetScan.MainQuest")
    if "target_scan_voice_prop" in builder:
        fail("ESP builder must not VMAD-bind TargetScan.VoiceAlias")

    deploy = DEPLOY.read_text(encoding="utf-8", errors="replace")
    if "$PscTargetScan" not in deploy or "PickmansWhisperTargetScanScript.psc" not in deploy:
        fail("build-deploy-local must Caprica-compile TargetScan")
    if "PickmansWhisperTargetScanScript.pex" not in deploy:
        fail("build-deploy-local must deploy TargetScan .pex")
    package = PACKAGE.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperTargetScanScript" not in package:
        fail("package_mo2_zip must ship TargetScan .pex/.psc")
    if not PEX.is_file():
        fail("TargetScan .pex missing — Caprica must compile it before contracts")

    qust = find_qust(ESP.read_bytes(), FID_QUEST)
    if not qust:
        fail("PickmansWhisperMain QUST missing")
    vmad = dict(parse_fields(qust)).get(b"VMAD", b"")
    if b"PickmansWhisperTargetScanScript" not in vmad:
        fail("Main VMAD must attach PickmansWhisperTargetScanScript")
    binds = find_vmad_object_prop(vmad, "MainQuest")
    if not binds or binds[0] != (-1, FID_QUEST):
        fail(f"TargetScan MainQuest must form-bind Main 0x{FID_QUEST:08X}, got {binds}")
    if find_vmad_object_prop(vmad, "TrackedTargets"):
        fail("TrackedTargets must not be ESP Object-bound")
    ok("MainQuest VMAD form-bound; TrackedTargets runtime Auto")
    print("All TargetScan contracts passed.")


if __name__ == "__main__":
    main()
