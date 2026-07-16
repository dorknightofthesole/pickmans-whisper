#!/usr/bin/env python3
"""Build a minimal Fallout 4 ESP: start-game-enabled quest with PickmansWhisperMainQuestScript."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def zstring(s: str) -> bytes:
    return s.encode("ascii") + b"\x00"


def subrecord(sig: str, data: bytes) -> bytes:
    assert len(sig) == 4
    return sig.encode("ascii") + struct.pack("<H", len(data)) + data


def wstring(s: str) -> bytes:
    raw = s.encode("ascii")
    return struct.pack("<H", len(raw)) + raw


def record(sig: str, flags: int, form_id: int, body: bytes, version: int = 131) -> bytes:
    # FO4 record header: type(4) dataSize(4) flags(4) formID(4) timestamp(4) version(2) unknown(2)
    header = sig.encode("ascii")
    header += struct.pack("<I", len(body))
    header += struct.pack("<I", flags)
    header += struct.pack("<I", form_id)
    header += struct.pack("<I", 0)  # version control / timestamp
    header += struct.pack("<H", version)
    header += struct.pack("<H", 0)
    return header + body


def build_vmad_script(script_name: str) -> bytes:
    # FO4 VMAD: version 6, object format 2, one script, zero properties
    data = struct.pack("<HHH", 6, 2, 1)
    data += wstring(script_name)
    data += struct.pack("<B", 0)  # status
    data += struct.pack("<H", 0)  # property count
    return data


def build_tes4(masters: list[str]) -> bytes:
    body = b""
    # HEDR: version float 1.0, numRecords, nextObjectID
    body += subrecord("HEDR", struct.pack("<fII", 1.0, 1, 0x800))
    body += subrecord("CNAM", zstring("PickmansWhisper"))
    for master in masters:
        body += subrecord("MAST", zstring(master))
        body += subrecord("DATA", struct.pack("<Q", 0))
    body += subrecord("INTV", struct.pack("<I", 1))
    return record("TES4", 0, 0, body)


def build_quest(form_id: int, edid: str, script_name: str) -> bytes:
    body = b""
    body += subrecord("EDID", zstring(edid))
    body += subrecord("VMAD", build_vmad_script(script_name))
    body += subrecord("FULL", zstring(edid))
    # DNAM: flags 0x0011 (Start Game Enabled | Run Once-ish)
    body += subrecord("DNAM", bytes.fromhex("11005C730000000000000000"))
    body += subrecord("NEXT", b"")
    body += subrecord("ANAM", struct.pack("<I", 0))
    return record("QUST", 0, form_id, body)


def build_grup_quest(quests: bytes) -> bytes:
    label = b"QUST"
    group_type = 0  # top-level
    size = 24 + len(quests)
    header = b"GRUP" + struct.pack("<I", size) + label + struct.pack("<I", group_type)
    header += struct.pack("<I", 0)  # stamp
    header += struct.pack("<I", 0)  # unknown
    return header + quests


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "Data" / "PickmansWhisper.esp"
    out.parent.mkdir(parents=True, exist_ok=True)

    # Single master => local formIDs are 01xxxxxx
    tes4 = build_tes4(["Fallout4.esm"])
    quest = build_quest(0x01000800, "PickmansWhisperMain", "PickmansWhisperMainQuestScript")
    grup = build_grup_quest(quest)
    data = tes4 + grup
    out.write_bytes(data)
    print(f"Wrote {out} ({len(data)} bytes)")
    print(f"CRC32={zlib.crc32(data) & 0xffffffff:08x}")


if __name__ == "__main__":
    main()
