#!/usr/bin/env python3
"""VoiceAlias on PickmansWhisperMain — KillerScan voice listener host.

Locks:
  - Main ALST 6 VoiceAlias UniqueActor=Player
  - ANAM 7 (past VoiceAlias ALST 6)
  - VMAD attaches PickmansWhisperVoiceAliasScript on ALST 6 (not quest script list)
  - Nested alias object header is ofmt-2 (unk=0, aliasId, quest) — not (aliasId, 0)
  - Main.VoiceAlias Auto Const + VMAD Object bind to ALST 6
  - VoiceAliasScript extends ReferenceAlias; Main via GetOwningQuest
  - KillerScan DispatchListeners uses m.VoiceAlias.HandleWhisperVoice
  - Deploy compiles + ships VoiceAliasScript + runs this contract

Usage:
  python tools/test_voice_alias.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
VOICE_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
KILLER_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillerScanScript.psc"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"

FID_QUEST = 0x01000800
ALIAS_VOICE_ID = 6
ANAM_NEXT = ALIAS_VOICE_ID + 1


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def parse_fields(body: bytes) -> list[tuple[bytes, bytes]]:
    out: list[tuple[bytes, bytes]] = []
    j = 0
    while j + 6 <= len(body):
        t = body[j : j + 4]
        sz = struct.unpack_from("<H", body, j + 4)[0]
        out.append((t, body[j + 6 : j + 6 + sz]))
        j += 6 + sz
    return out


def zfield(sd: bytes) -> str:
    if not sd:
        return ""
    if sd[-1:] == b"\x00":
        sd = sd[:-1]
    return sd.decode("utf-8", errors="replace")


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
                typ = vmad[off]
                if typ == 1:
                    alias_id = struct.unpack_from("<h", vmad, off + 2 + 2)[0]
                    form_id = struct.unpack_from("<I", vmad, off + 2 + 2 + 2)[0]
                    out.append((alias_id, form_id))
        i = j + 1
    return out


def parse_nested_alias_object(
    vmad: bytes, script_name: str
) -> tuple[int, int, int]:
    """Return (unk, alias_id, quest_fid) preceding a nested alias script attach.

    Layout immediately before the alias script wstring:
      int16 unk=0, int16 aliasId, uint32 questFid, HHH(ver=6, ofmt=2, scriptCount=1)
    Wrong packing used (aliasId, 0) and bound scripts to the wrong target.
    """
    name_b = script_name.encode("utf-8")
    j = vmad.find(name_b)
    if j < 2:
        fail(f"VMAD missing nested alias script {script_name}")
    ln = struct.unpack_from("<H", vmad, j - 2)[0]
    if ln != len(name_b):
        fail(f"{script_name} wstring length mismatch")
    hdr = j - 2 - 6
    if hdr < 8:
        fail(f"{script_name} nested alias header too short")
    ver, ofmt, scount = struct.unpack_from("<HHH", vmad, hdr)
    if ver != 6 or ofmt != 2 or scount != 1:
        fail(
            f"{script_name} nested VMAD header must be (6,2,1), "
            f"got ({ver},{ofmt},{scount})"
        )
    unk, alias_id, quest_fid = struct.unpack_from("<hhI", vmad, hdr - 8)
    return unk, alias_id, quest_fid


def main() -> None:
    builder = BUILDER.read_text(encoding="utf-8", errors="replace")
    for needle, label in (
        ("ALIAS_VOICE_ID = 6", "Voice ALST"),
        ('zstr("VoiceAlias")', "Voice ALID"),
        ('"PickmansWhisperVoiceAliasScript"', "alias script attach"),
        ("build_voice_alias_fields()", "alias field builder call"),
        ('struct.pack("<hhI", 0, alias_id', "alias object ofmt-2 packing"),
        ("voice_alias_prop", "Main.VoiceAlias VMAD bind"),
    ):
        if needle not in builder:
            fail(f"builder missing {label}: {needle}")
    if '"PickmansWhisperVoiceAliasScript"' in builder.split("main_scripts")[1].split("]")[0]:
        fail("VoiceAliasScript must not remain in main quest script list")
    ok("builder declares VoiceAlias ALST 6 + VMAD alias script + Main Object bind")

    if not VOICE_PSC.is_file():
        fail("PickmansWhisperVoiceAliasScript.psc missing")
    voice = VOICE_PSC.read_text(encoding="utf-8", errors="replace")
    if "Scriptname PickmansWhisperVoiceAliasScript extends ReferenceAlias" not in voice:
        fail("VoiceAliasScript must extend ReferenceAlias")
    if "GetOwningQuest() as PickmansWhisperMainQuestScript" not in voice:
        fail("VoiceAliasScript Main() must use GetOwningQuest")
    if "(Self as Quest) as PickmansWhisperMainQuestScript" in voice:
        fail("VoiceAliasScript must not cast Self as Quest (alias script)")
    if "Function HandleWhisperVoice" not in voice:
        fail("VoiceAliasScript must expose HandleWhisperVoice")
    ok("VoiceAliasScript: ReferenceAlias + GetOwningQuest + HandleWhisperVoice")

    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperVoiceAliasScript Property VoiceAlias Auto Const" not in psc:
        fail("Main must declare VoiceAlias Auto Const (ESP Object bind)")
    if "Function EnsureFeatureAliases" not in psc:
        fail("Main must keep EnsureFeatureAliases fail-loud check")
    if "(Self as Quest) as PickmansWhisperVoiceAliasScript" in psc:
        fail("Main must not quest-cast VoiceAliasScript")
    if "Function VoiceScan()" in psc:
        fail("Main VoiceScan() quest cast helper must be removed (use VoiceAlias)")
    ok("MainQuestScript declares VoiceAlias Auto Const")

    killer = KILLER_PSC.read_text(encoding="utf-8", errors="replace")
    if "m.VoiceAlias.HandleWhisperVoice(FacedLiving)" not in killer:
        fail("KillerScan DispatchListeners must call m.VoiceAlias.HandleWhisperVoice(FacedLiving)")
    if "(Self as Quest) as PickmansWhisperVoiceAliasScript" in killer:
        fail("KillerScan must not quest-cast VoiceAliasScript")
    ok("KillerScan dispatches via Main.VoiceAlias")

    if not ESP.is_file():
        fail(f"ESP missing: {ESP}")
    data = ESP.read_bytes()
    qust = find_qust(data, FID_QUEST)
    if not qust:
        fail("PickmansWhisperMain QUST missing")
    fields = parse_fields(qust)
    anam = None
    aliases: list[tuple[int, str, int]] = []
    i = 0
    while i < len(fields):
        st, sd = fields[i]
        if st == b"ANAM" and len(sd) >= 4:
            anam = struct.unpack_from("<I", sd, 0)[0]
        if st == b"ALST" and len(sd) >= 4:
            aid = struct.unpack_from("<I", sd, 0)[0]
            alid = ""
            fnam = 0
            j = i + 1
            while j < len(fields) and fields[j][0] != b"ALED":
                if fields[j][0] == b"ALID":
                    alid = zfield(fields[j][1])
                elif fields[j][0] == b"FNAM" and len(fields[j][1]) >= 4:
                    fnam = struct.unpack_from("<I", fields[j][1], 0)[0]
                j += 1
            aliases.append((aid, alid, fnam))
            i = j
        else:
            i += 1

    va = [a for a in aliases if a[1] == "VoiceAlias"]
    if not va or va[0][0] != ALIAS_VOICE_ID:
        fail(f"VoiceAlias ALST must be {ALIAS_VOICE_ID}, got {va}")
    if anam != ANAM_NEXT:
        fail(f"Main ANAM must be {ANAM_NEXT}, got {anam}")
    ok(f"ESP VoiceAlias ALST={ALIAS_VOICE_ID}; ANAM={anam}")

    vmad = dict(fields).get(b"VMAD", b"")
    if not vmad or b"PickmansWhisperVoiceAliasScript" not in vmad:
        fail("Main VMAD must attach PickmansWhisperVoiceAliasScript")
    binds = find_vmad_object_prop(vmad, "VoiceAlias")
    if not binds or binds[0] != (ALIAS_VOICE_ID, FID_QUEST):
        fail(f"Main VMAD must Object-bind VoiceAlias → ALST {ALIAS_VOICE_ID}, got {binds}")
    # Nested alias attach targets (regression for swapped ofmt-2 packing).
    if b"PickmansWhisperKillRewardScript" in vmad:
        fail("Main VMAD must not attach retired PickmansWhisperKillRewardScript")
    for script, expect_aid in (
        ("PickmansWhisperModConfigScript", 5),
        ("PickmansWhisperVoiceAliasScript", ALIAS_VOICE_ID),
    ):
        unk, aid, qfid = parse_nested_alias_object(vmad, script)
        if unk != 0 or aid != expect_aid or qfid != FID_QUEST:
            fail(
                f"nested {script} object must be (0,{expect_aid},0x{FID_QUEST:08X}), "
                f"got ({unk},{aid},0x{qfid:08X}) — swapped packing binds wrong target"
            )
    ok("VMAD: VoiceAlias Object bind + nested alias objects (0, aliasId, quest)")

    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperVoiceAliasScript.psc" not in deploy:
        fail("build-deploy-local.ps1 must Caprica-compile VoiceAliasScript")
    if "test_voice_alias.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_voice_alias.py")
    ok("deploy gate compiles VoiceAliasScript + runs this contract")

    print("All VoiceAlias contracts passed.")


if __name__ == "__main__":
    main()
