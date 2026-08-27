#!/usr/bin/env python3
"""Blade hit / kill-credit ActorValue (AVIF) contracts.

Locks:
  - Main declares PW_HitWihPickmansBlade + PW_Credit_For_PickmansBlade_Kill Auto Const
  - ESP emits Variable AVIFs at 0x874 / 0x875 (+ tracker 0x877; reward-check 0x876 separate)
  - NEXT_OID past gore SM arm L MISC (0x87F) — currently 0x880
  - Main VMAD binds those properties to the AVIF FormIDs
  - Papyrus uses GetValue/SetValue (not Keyword APIs)

Usage:
  python tools/test_blade_hit_av.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"

FID_QUEST = 0x01000800
FID_AV_HIT = 0x01000874
FID_AV_CREDIT = 0x01000875
FID_AV_TRACKER = 0x01000877
PROP_HIT = "PW_HitWihPickmansBlade"
PROP_CREDIT = "PW_Credit_For_PickmansBlade_Kill"
PROP_TRACKER = "PW_TargetTrackerExpiration"
AVIF_FLAG_VARIABLE_DEFAULT0 = 0x00040000
AVIF_TYPE_VARIABLE = 8


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


def find_records(data: bytes, rtype: bytes) -> list[tuple[int, bytes]]:
    i = 0
    while i + 24 <= len(data):
        if data[i : i + 4] == b"TES4":
            i += 24 + struct.unpack_from("<I", data, i + 4)[0]
            break
        i += 1
    out: list[tuple[int, bytes]] = []
    while i + 24 <= len(data):
        tag = data[i : i + 4]
        if tag == b"GRUP":
            gsize = struct.unpack_from("<I", data, i + 4)[0]
            end = i + gsize
            j = i + 24
            while j + 24 <= end:
                if data[j : j + 4] == b"GRUP":
                    j += struct.unpack_from("<I", data, j + 4)[0]
                    continue
                rt = data[j : j + 4]
                size = struct.unpack_from("<I", data, j + 4)[0]
                fid = struct.unpack_from("<I", data, j + 12)[0]
                if rt == rtype:
                    out.append((fid, data[j + 24 : j + 24 + size]))
                j += 24 + size
            i = end
            continue
        i += 24 + struct.unpack_from("<I", data, i + 4)[0]
    return out


def zfield(blob: bytes) -> str:
    return blob.split(b"\x00", 1)[0].decode("latin1", "replace")


def parse_vmad_form_prop(vmad: bytes, name: str) -> tuple[int, int, int]:
    idx = vmad.find(name.encode("ascii"))
    if idx < 2:
        fail(f"VMAD missing property {name}")
    nlen = struct.unpack_from("<H", vmad, idx - 2)[0]
    if nlen != len(name):
        fail(f"{name} wstring length mismatch")
    off = idx + nlen
    ptype, pstat = vmad[off], vmad[off + 1]
    zero, alias_id, form_fid = struct.unpack_from("<hhI", vmad, off + 2)
    if ptype != 1 or pstat != 1:
        fail(f"{name} property type/status must be 1/1, got {ptype}/{pstat}")
    if zero != 0 or alias_id != -1:
        fail(f"{name} must be Form bind (alias=-1), got zero={zero} alias={alias_id}")
    return ptype, pstat, form_fid


def main() -> None:
    builder = BUILDER.read_text(encoding="utf-8", errors="replace")
    for needle, label in [
        ("FID_AV_HIT_WITH_BLADE = 0x01000874", "hit AVIF fid"),
        ("FID_AV_CREDIT_BLADE_KILL = 0x01000875", "credit AVIF fid"),
        ("FID_AV_TARGET_TRACKER_EXPIRATION = 0x01000877", "tracker AVIF fid"),
        ("NEXT_OID = 0x00000880", "NEXT_OID"),
        ('"PW_HitWihPickmansBlade", FID_AV_HIT_WITH_BLADE', "hit VMAD bind"),
        (
            '"PW_Credit_For_PickmansBlade_Kill", FID_AV_CREDIT_BLADE_KILL',
            "credit VMAD bind",
        ),
        (
            '"PW_TargetTrackerExpiration", FID_AV_TARGET_TRACKER_EXPIRATION',
            "tracker VMAD bind",
        ),
        ("build_variable_avif_payload", "AVIF payload helper"),
        ('b"AVIF"', "AVIF group"),
        ("avif_tracker_expiration", "tracker AVIF record"),
    ]:
        if needle not in builder:
            fail(f"builder must declare {label}: {needle}")
    ok("builder declares blade/tracker AVIF FormIDs + Main VMAD binds + NEXT_OID past AVIFs")

    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    if f"ActorValue Property {PROP_HIT} Auto Const" not in psc:
        fail(f"Main must declare ActorValue Property {PROP_HIT} Auto Const")
    if f"ActorValue Property {PROP_CREDIT} Auto Const" not in psc:
        fail(f"Main must declare ActorValue Property {PROP_CREDIT} Auto Const")
    if f"ActorValue Property {PROP_TRACKER} Auto Const" not in psc:
        fail(f"Main must declare ActorValue Property {PROP_TRACKER} Auto Const")
    if f"HasKeyword({PROP_HIT}" in psc or f"AddKeyword({PROP_HIT}" in psc:
        fail(f"{PROP_HIT} is ActorValue — must not use Keyword APIs")
    if f"HasKeyword({PROP_CREDIT}" in psc or f"AddKeyword({PROP_CREDIT}" in psc:
        fail(f"{PROP_CREDIT} is ActorValue — must not use Keyword APIs")
    ok("Main Papyrus ActorValue properties + GetValue/SetValue usage")

    if not ESP.is_file():
        fail(f"missing ESP {ESP} — run build_hunger_spell_esp.py first")
    data = ESP.read_bytes()
    avifs = {fid: body for fid, body in find_records(data, b"AVIF")}
    for fid, edid in (
        (FID_AV_HIT, PROP_HIT),
        (FID_AV_CREDIT, PROP_CREDIT),
        (FID_AV_TRACKER, PROP_TRACKER),
    ):
        body = avifs.get(fid)
        if body is None:
            fail(f"ESP missing AVIF 0x{fid:08X} ({edid})")
        fields = dict(parse_fields(body))
        if zfield(fields.get(b"EDID", b"")) != edid:
            fail(
                f"AVIF 0x{fid:08X} EDID {zfield(fields.get(b'EDID', b''))!r} != {edid!r}"
            )
        nam0 = fields.get(b"NAM0", b"")
        if len(nam0) != 4 or struct.unpack("<f", nam0)[0] != 0.0:
            fail(f"AVIF {edid} NAM0 must be 0.0")
        avfl = fields.get(b"AVFL", b"")
        if len(avfl) != 4 or struct.unpack("<I", avfl)[0] != AVIF_FLAG_VARIABLE_DEFAULT0:
            fail(f"AVIF {edid} AVFL must be 0x{AVIF_FLAG_VARIABLE_DEFAULT0:08X}")
        nam1 = fields.get(b"NAM1", b"")
        if len(nam1) != 4 or struct.unpack("<I", nam1)[0] != AVIF_TYPE_VARIABLE:
            fail(f"AVIF {edid} NAM1 must be Variable ({AVIF_TYPE_VARIABLE})")
    ok(
        f"ESP AVIF 0x{FID_AV_HIT:08X}/{PROP_HIT} + "
        f"0x{FID_AV_CREDIT:08X}/{PROP_CREDIT} + "
        f"0x{FID_AV_TRACKER:08X}/{PROP_TRACKER} (Variable)"
    )

    qusts = {fid: body for fid, body in find_records(data, b"QUST")}
    main_body = qusts.get(FID_QUEST)
    if main_body is None:
        fail(f"ESP missing Main QUST 0x{FID_QUEST:08X}")
    vmad = next((sd for st, sd in parse_fields(main_body) if st == b"VMAD"), None)
    if not vmad:
        fail("Main QUST missing VMAD")
    _, _, hit_fid = parse_vmad_form_prop(vmad, PROP_HIT)
    _, _, credit_fid = parse_vmad_form_prop(vmad, PROP_CREDIT)
    _, _, tracker_fid = parse_vmad_form_prop(vmad, PROP_TRACKER)
    if hit_fid != FID_AV_HIT:
        fail(f"{PROP_HIT} VMAD form must be 0x{FID_AV_HIT:08X}, got 0x{hit_fid:08X}")
    if credit_fid != FID_AV_CREDIT:
        fail(
            f"{PROP_CREDIT} VMAD form must be 0x{FID_AV_CREDIT:08X}, "
            f"got 0x{credit_fid:08X}"
        )
    if tracker_fid != FID_AV_TRACKER:
        fail(
            f"{PROP_TRACKER} VMAD form must be 0x{FID_AV_TRACKER:08X}, "
            f"got 0x{tracker_fid:08X}"
        )
    ok("Main VMAD binds blade + tracker ActorValue properties to AVIF forms")
    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "test_blade_hit_av.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_blade_hit_av.py")
    ok("deploy gate includes blade-hit AVIF contract")

    print("All blade-hit ActorValue contracts passed.")


if __name__ == "__main__":
    main()
