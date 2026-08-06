#!/usr/bin/env python3
"""TrackedNPCs retired — must not be on Main QUST / Main VMAD / live Property.

Usage:
  python tools/test_tracked_npcs_alias.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
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


def main() -> None:
    builder = BUILDER.read_text(encoding="utf-8", errors="replace")
    if "build_tracked_npcs_alias_fields" in builder:
        fail("ESP builder must not emit TrackedNPCs alias fields")
    if '"TrackedNPCs", ALIAS_TRACKED_NPCS_ID' in builder or 'zstr("TrackedNPCs")' in builder:
        fail("ESP builder must not bind/emit TrackedNPCs")
    ok("ESP builder has no TrackedNPCs alias / VMAD bind")

    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    live_prop = False
    for line in psc.splitlines():
        s = line.strip()
        if s.startswith(";"):
            continue
        if "RefCollectionAlias Property TrackedNPCs" in s:
            live_prop = True
            break
    if live_prop:
        fail("MainQuestScript must not declare live TrackedNPCs Property (comment it out)")
    ok("MainQuestScript TrackedNPCs Property commented out / absent")

    qust = find_qust(ESP.read_bytes(), FID_QUEST)
    if not qust:
        fail("PickmansWhisperMain QUST missing")
    fields = parse_fields(qust)
    vmad = dict(fields).get(b"VMAD", b"")
    if b"TrackedNPCs" in vmad:
        fail("Main VMAD must not contain TrackedNPCs property")
    alids = [payload[:-1].decode("latin-1", errors="replace") for t, payload in fields if t == b"ALID"]
    if "TrackedNPCs" in alids or "TrackedNPCsSeed" in alids:
        fail(f"Main QUST must not have TrackedNPCs ALST, got ALIDs={alids}")
    ok("ESP Main QUST has no TrackedNPCs alias / VMAD property")
    print("All TrackedNPCs retirement contracts passed.")


if __name__ == "__main__":
    main()
