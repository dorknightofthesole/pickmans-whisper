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


def _scan_body(psc: str) -> str:
    start = psc.find("Function ScanAndCleanTargets()")
    if start < 0:
        fail("missing Function ScanAndCleanTargets")
    end = psc.find("\nEndFunction", start)
    if end < 0:
        fail("unclosed ScanAndCleanTargets")
    return psc[start : end + len("\nEndFunction")]


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
    if 'CallFunctionNoWait("RunHungerTick"' not in psc:
        fail("ScanAndCleanTargets must CallFunctionNoWait RunHungerTick (Slice A hunger host)")
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    if "Function RunHungerTick()" not in main:
        fail("Main must own RunHungerTick (hunger advance body)")
    hunger = main[main.find("Function RunHungerTick()") : main.find("EndFunction", main.find("Function RunHungerTick()")) + len("EndFunction")]
    if "ApplyHungerDelta" not in hunger or "GetHungerTimeGainPerHour" not in hunger:
        fail("RunHungerTick must apply unused-knife-time hunger gain")
    if "MaybeSpeakNoticeLine" in hunger:
        fail("RunHungerTick must not drive ambient notice (RegisterTarget / LookFixation)")
    if "HungerWithdrawalToast" not in hunger:
        fail("RunHungerTick must toast HungerWithdrawalToast on withdrawal onset")
    if KILLER.is_file():
        fail("PickmansWhisperKillerScanScript.psc must be retired")
    if "KILL_WATCH_RADIUS = 800.0" in main or "KILL_CORPSE_RADIUS = 400.0" in main:
        fail("Main must not redefine scan radii — TargetScan Properties are SSOT")
    if "Function TargetScan()" not in main:
        fail("Main must expose TargetScan() façade")
    scan = _scan_body(psc)
    for optional in ("NoteVictimsAimActor", "TickEssential"):
        if optional in scan:
            ok(f"TargetScan ScanAndCleanTargets hosts {optional}")
    if "ReconcileBladeTagged" in scan:
        fail("TargetScan must not host ReconcileBladeTagged (BladeTagged retired)")
    if "LastReadyToGiveBeating" not in psc:
        fail("TargetScan must store LastReadyToGiveBeating for IsReadyToGiveBeating edge")
    if "LastPickmansBladeEquipped" in psc:
        fail("LastPickmansBladeEquipped retired — edge is IsReadyToGiveBeating only")
    if "BeatingModeEdgePrimed" in psc or "BeatModeEdgedThisScan" in psc:
        fail("Edge latch retired — MaybeRekickBeatOnBeatingModeEdge owns LastReady compare + commit")
    if "LastReadyToGiveBeating = MainQuest.PlayerAlias.IsReadyToGiveBeating" not in psc:
        fail("Init must seed LastReadyToGiveBeating from PlayerAlias")
    if "LastReadyToGiveBeating = MainQuest.PlayerAlias.IsReadyToGiveBeating" in scan:
        fail("ScanAndCleanTargets must not commit LastReady — that lives in MaybeRekickBeatOnBeatingModeEdge")
    edge_start = psc.find("Function MaybeRekickBeatOnBeatingModeEdge")
    if edge_start < 0:
        fail("TargetScan must expose MaybeRekickBeatOnBeatingModeEdge(Actor)")
    edge = psc[edge_start : psc.find("\nEndFunction", edge_start)]
    if "TrackedTargets" in edge:
        fail("MaybeRekickBeatOnBeatingModeEdge must not walk TrackedTargets")
    if "IsReadyToGiveBeating" not in edge or "LastReadyToGiveBeating" not in edge:
        fail("MaybeRekickBeatOnBeatingModeEdge must compare IsReadyToGiveBeating to LastReadyToGiveBeating")
    if "LastReadyToGiveBeating = ready" not in edge:
        fail("MaybeRekickBeatOnBeatingModeEdge must commit LastReadyToGiveBeating = ready on edge")
    if "CheckForBeatDown(akTarget)" not in edge:
        fail("MaybeRekickBeatOnBeatingModeEdge must CheckForBeatDown(akTarget) on edge")
    if "Return True" not in edge or "Return False" not in edge:
        fail("MaybeRekickBeatOnBeatingModeEdge must return Bool (edge yes/no)")
    if 'CallFunctionNoWait("RegisterTarget"' in edge:
        fail("MaybeRekickBeatOnBeatingModeEdge must not RegisterTarget — ProcessTargets ElseIf beatDownChange does")
    check_start = psc.find("Function CheckForBeatDown")
    if check_start < 0:
        fail("TargetScan must expose CheckForBeatDown(Actor)")
    check = psc[check_start : psc.find("\nEndFunction", check_start)]
    if "HandleBeatBeforeKill(akTarget)" in check:
        fail("CheckForBeatDown must not call HandleBeatBeforeKill synchronously")
    if 'CallFunctionNoWait("HandleBeatBeforeKill"' not in check:
        fail("CheckForBeatDown must CallFunctionNoWait HandleBeatBeforeKill")
    proc_start = psc.find("Function ProcessTargets")
    if proc_start < 0:
        fail("TargetScan must expose ProcessTargets")
    proc = psc[proc_start : psc.find("\nEndFunction", proc_start)]
    if "beatDownChange = MaybeRekickBeatOnBeatingModeEdge(potentialTarget)" not in proc:
        fail("ProcessTargets must capture MaybeRekickBeatOnBeatingModeEdge result as beatDownChange")
    if "ElseIf beatDownChange" not in proc:
        fail("ProcessTargets must ElseIf beatDownChange re-RegisterTarget for already-tracked")
    edged_branch = proc[proc.find("ElseIf beatDownChange") : proc.find("Else", proc.find("ElseIf beatDownChange") + 1)]
    if 'CallFunctionNoWait("RegisterTarget"' not in edged_branch:
        fail("ElseIf beatDownChange must CallFunctionNoWait RegisterTarget")
    if "TrackedTargets.Add" in edged_branch:
        fail("ElseIf beatDownChange must not Add (already tracked)")
    ok("TargetScan edge Bool + ElseIf beatDownChange re-RegisterTarget")

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
