#!/usr/bin/env python3
"""TrackedNPCs RefCollectionAlias on PickmansWhisperMain.

Locks:
  - Main QUST has ALST alias EDID TrackedNPCs
  - VMAD on PickmansWhisperMainQuestScript binds property TrackedNPCs → that alias
  - Papyrus Property TrackedNPCs Auto Const + Find/AddRef/RemoveRef usage
  - Stub exposes AddRef / RemoveRef / Find

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
STUB = ROOT / "tools" / "stubs" / "RefCollectionAlias.psc"

FID_QUEST = 0x01000800
FID_PLAYER_QUEST = 0x01000805
ALIAS_TRACKED_NPCS_SEED_ID = 0
ALIAS_TRACKED_NPCS_ID = 1


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


def find_qust(data: bytes, fid: int) -> bytes | None:
    i = 0
    while i + 24 <= len(data):
        if data[i : i + 4] == b"TES4":
            i += 24 + struct.unpack_from("<I", data, i + 4)[0]
            break
        i += 1
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
                rtype = data[j : j + 4]
                size = struct.unpack_from("<I", data, j + 4)[0]
                rfid = struct.unpack_from("<I", data, j + 12)[0]
                if rtype == b"QUST" and rfid == fid:
                    return data[j + 24 : j + 24 + size]
                j += 24 + size
            i = end
            continue
        i += 24 + struct.unpack_from("<I", data, i + 4)[0]
    return None


def main() -> None:
    builder = BUILDER.read_text(encoding="utf-8", errors="replace")
    if "ALIAS_TRACKED_NPCS_SEED_ID = 0" not in builder:
        fail("builder must declare ALIAS_TRACKED_NPCS_SEED_ID = 0")
    if "ALIAS_TRACKED_NPCS_ID = 1" not in builder:
        fail("builder must declare ALIAS_TRACKED_NPCS_ID = 1")
    if "build_tracked_npcs_alias_fields" not in builder:
        fail("builder must define build_tracked_npcs_alias_fields")
    if 'zstr("TrackedNPCs")' not in builder:
        fail("builder must emit ALID TrackedNPCs")
    if 'zstr("TrackedNPCsSeed")' not in builder:
        fail("builder must emit ALID TrackedNPCsSeed (ALCS pointer)")
    if 'field(b"ALCS"' not in builder:
        fail("builder must emit ALCS so TrackedNPCs is typed as RefCollectionAlias")
    if 'field(b"ALMI"' not in builder:
        fail("builder must emit ALMI after ALCS (vanilla trailer)")
    if '"TrackedNPCs", ALIAS_TRACKED_NPCS_ID' not in builder:
        fail("builder must VMAD-bind TrackedNPCs property on MainQuestScript")
    if '"PlayerAlias", 0, FID_PLAYER_QUEST' not in builder:
        fail("builder must VMAD-bind PlayerAlias → PlayerCombat ALST 0")
    # ALCS must follow seed ALED, not sit inside an alias body before VTCK.
    seed_fn = builder.split("def build_tracked_npcs_alias_fields", 1)[1].split(
        "\ndef ", 1
    )[0]
    alcs_at = seed_fn.find('field(b"ALCS"')
    aled_seed = seed_fn.find('field(b"ALED"')
    if alcs_at < 0 or aled_seed < 0 or alcs_at < aled_seed:
        fail("ALCS must be emitted after TrackedNPCsSeed ALED (vanilla trailer order)")
    ok("builder declares TrackedNPCs RefCollectionAlias + post-ALED ALCS/ALMI + VMAD bind")

    if not STUB.is_file():
        fail("RefCollectionAlias stub missing")
    stub = STUB.read_text(encoding="utf-8", errors="replace")
    for fn in ("AddRef", "RemoveRef", "Find", "GetAt", "GetCount"):
        if f"Function {fn}" not in stub:
            fail(f"RefCollectionAlias stub missing {fn}")
    ok("RefCollectionAlias stub has collection natives")

    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    if "RefCollectionAlias Property TrackedNPCs Auto Const" not in psc:
        fail("MainQuestScript must declare TrackedNPCs Auto Const")
    if "PickmansWhisperPlayerAliasScript Property PlayerAlias Auto Const" not in psc:
        fail("MainQuestScript must declare PlayerAlias Auto Const")
    if "Function PlayerAlias()" in psc:
        fail("MainQuestScript must not keep PlayerAlias() facade (conflicts with property)")
    if "TrackedNPCs.AddRef" not in psc:
        fail("MainQuestScript must AddRef into TrackedNPCs")
    if "TrackedNPCs.RemoveRef" not in psc:
        fail("MainQuestScript must RemoveRef from TrackedNPCs")
    if "TrackedNPCs.Find" not in psc:
        fail("MainQuestScript must use TrackedNPCs.Find (not .find)")
    if "TrackedNPCs.find" in psc:
        fail("MainQuestScript must not call lowercase TrackedNPCs.find")
    ok("MainQuestScript TrackedNPCs property + Find/AddRef/RemoveRef")

    if not ESP.is_file():
        fail(f"missing ESP {ESP}")
    body = find_qust(ESP.read_bytes(), FID_QUEST)
    if body is None:
        fail(f"ESP missing QUST 0x{FID_QUEST:08X}")
    fields = parse_fields(body)
    anam = None
    aliases: list[tuple[int, str, int]] = []
    # Vanilla: ALCS/ALMI trailers sit AFTER seed ALED, before collection ALST.
    trailers_after: dict[int, dict[str, int]] = {}
    cur_id = None
    cur_name = None
    cur_fnam = None
    last_closed_id: int | None = None
    for st, sd in fields:
        if st == b"ANAM" and len(sd) >= 4:
            anam = struct.unpack("<I", sd)[0]
        if st == b"ALST" and len(sd) >= 4:
            cur_id = struct.unpack("<I", sd)[0]
            cur_name = None
            cur_fnam = None
        elif st == b"ALID" and cur_id is not None:
            cur_name = sd.split(b"\x00", 1)[0].decode("latin1", "replace")
        elif st == b"FNAM" and cur_id is not None and len(sd) >= 4:
            cur_fnam = struct.unpack("<I", sd)[0]
        elif st == b"ALED" and cur_id is not None and cur_name is not None:
            aliases.append((cur_id, cur_name, cur_fnam if cur_fnam is not None else -1))
            last_closed_id = cur_id
            cur_id = None
        elif st == b"ALCS" and last_closed_id is not None and len(sd) >= 4:
            trailers_after.setdefault(last_closed_id, {})["ALCS"] = struct.unpack(
                "<I", sd
            )[0]
        elif st == b"ALMI" and last_closed_id is not None:
            trailers_after.setdefault(last_closed_id, {})["ALMI"] = (
                sd[0] if sd else -1
            )
    tracked = [a for a in aliases if a[1] == "TrackedNPCs"]
    if not tracked:
        fail("Main QUST missing ALST alias TrackedNPCs")
    aid, _name, fnam = tracked[0]
    if aid != ALIAS_TRACKED_NPCS_ID:
        fail(f"TrackedNPCs ALST must be {ALIAS_TRACKED_NPCS_ID}, got {aid}")
    if fnam != 0x20:
        fail(f"TrackedNPCs FNAM must be 0x20 (collection), got 0x{fnam:X}")
    seed = [a for a in aliases if a[1] == "TrackedNPCsSeed"]
    if not seed:
        fail("Main QUST missing ALST alias TrackedNPCsSeed (ALCS pointer)")
    sid, _sname, sfnam = seed[0]
    if sid != ALIAS_TRACKED_NPCS_SEED_ID:
        fail(f"TrackedNPCsSeed ALST must be {ALIAS_TRACKED_NPCS_SEED_ID}, got {sid}")
    seed_trail = trailers_after.get(sid, {})
    salcs = seed_trail.get("ALCS")
    if salcs != ALIAS_TRACKED_NPCS_ID:
        fail(f"post-ALED ALCS after seed must point to {ALIAS_TRACKED_NPCS_ID}, got {salcs}")
    if "ALMI" not in seed_trail:
        fail("post-ALED ALMI missing after TrackedNPCsSeed")
    if anam != ALIAS_TRACKED_NPCS_ID + 1:
        fail(f"Main ANAM must be {ALIAS_TRACKED_NPCS_ID + 1}, got {anam}")
    ok(
        f"ESP TrackedNPCs ALST={aid} FNAM=0x{fnam:X}; "
        f"seed ALST={sid} FNAM=0x{sfnam:X} ALCS={salcs} ALMI=0x{seed_trail['ALMI']:X}; "
        f"ANAM={anam}"
    )

    vmad = next((sd for st, sd in fields if st == b"VMAD"), None)
    if not vmad or b"TrackedNPCs" not in vmad:
        fail("Main VMAD must contain property name TrackedNPCs")
    # Property blob: name + type1 status1 + 0 + aliasId + questFid
    idx = vmad.find(b"TrackedNPCs")
    # back up 2 for wstring length
    if idx < 2:
        fail("TrackedNPCs property name offset invalid")
    nlen = struct.unpack_from("<H", vmad, idx - 2)[0]
    if nlen != len("TrackedNPCs"):
        fail("TrackedNPCs wstring length mismatch")
    off = idx + nlen
    ptype, pstat = vmad[off], vmad[off + 1]
    zero, alias_id, quest_fid = struct.unpack_from("<hhI", vmad, off + 2)
    if ptype != 1 or pstat != 1:
        fail(f"TrackedNPCs property type/status must be 1/1, got {ptype}/{pstat}")
    if zero != 0 or alias_id != ALIAS_TRACKED_NPCS_ID:
        fail(f"TrackedNPCs property alias bind must be id {ALIAS_TRACKED_NPCS_ID}, got zero={zero} alias={alias_id}")
    if quest_fid != FID_QUEST:
        fail(f"TrackedNPCs property quest form must be 0x{FID_QUEST:08X}, got 0x{quest_fid:08X}")
    ok(f"VMAD TrackedNPCs Object property bound to Main ALST {ALIAS_TRACKED_NPCS_ID}")

    if b"PlayerAlias" not in vmad:
        fail("Main VMAD must contain property name PlayerAlias")
    pidx = vmad.find(b"PlayerAlias")
    if pidx < 2:
        fail("PlayerAlias property name offset invalid")
    pnlen = struct.unpack_from("<H", vmad, pidx - 2)[0]
    if pnlen != len("PlayerAlias"):
        fail("PlayerAlias wstring length mismatch")
    poff = pidx + pnlen
    pptype, ppstat = vmad[poff], vmad[poff + 1]
    pzero, palias_id, pquest_fid = struct.unpack_from("<hhI", vmad, poff + 2)
    if pptype != 1 or ppstat != 1:
        fail(f"PlayerAlias property type/status must be 1/1, got {pptype}/{ppstat}")
    if pzero != 0 or palias_id != 0:
        fail(f"PlayerAlias must bind alias id 0, got zero={pzero} alias={palias_id}")
    if pquest_fid != FID_PLAYER_QUEST:
        fail(
            f"PlayerAlias property quest form must be 0x{FID_PLAYER_QUEST:08X}, "
            f"got 0x{pquest_fid:08X}"
        )
    ok("VMAD PlayerAlias Object property bound to PlayerCombat ALST 0")

    print("All TrackedNPCs RefCollectionAlias contracts passed.")


if __name__ == "__main__":
    main()
