#!/usr/bin/env python3
"""Slice I decay-face ARMA/ARMO must be emitted by the ESP builder (survive deploy).

Locks:
  - FID_DECAY_FACE_BASE + biped slot 54
  - Discovers NecroBaseFemaleHead.nif (Base) + NecroBaseFemaleHead_<Color>.nif
  - EDID/FULL include color label for console Help
  - DecayFaceArmorIds.txt written
  - Built ESP contains matching ARMA + ARMO

Usage:
  python tools/test_decay_face_armor_esp.py
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
IDS = ROOT / "Data" / "PickmansWhisper" / "config" / "DecayFaceArmorIds.txt"
MESH_DIR = ROOT / "Data" / "Meshes" / "PickmansWhisper" / "Decay"
NIF_BASE = MESH_DIR / "NecroBaseFemaleHead.nif"
DEPLOY = ROOT / "tools" / "build-deploy-local.ps1"
AUDIO_POC = ROOT / "tools" / "test_audio_poc.py"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def parse_esp_types(data: bytes) -> list[tuple[str, int, bytes]]:
    """Walk top-level GRUPs and collect records (ARMA/ARMO/…)."""
    i = 0
    while i + 24 <= len(data):
        if data[i : i + 4] == b"TES4":
            size = struct.unpack_from("<I", data, i + 4)[0]
            i += 24 + size
            break
        i += 1
    out: list[tuple[str, int, bytes]] = []
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
                rtype = data[j : j + 4].decode("ascii", "replace")
                size = struct.unpack_from("<I", data, j + 4)[0]
                formid = struct.unpack_from("<I", data, j + 12)[0]
                body = data[j + 24 : j + 24 + size]
                out.append((rtype, formid, body))
                j += 24 + size
            i = end
            continue
        rtype = tag.decode("ascii", "replace")
        size = struct.unpack_from("<I", data, i + 4)[0]
        formid = struct.unpack_from("<I", data, i + 12)[0]
        body = data[i + 24 : i + 24 + size]
        out.append((rtype, formid, body))
        i += 24 + size
    return out


def fields(body: bytes) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    j = 0
    while j + 6 <= len(body):
        t = body[j : j + 4].decode("ascii", "replace")
        sz = struct.unpack_from("<H", body, j + 4)[0]
        out[t] = body[j + 6 : j + 6 + sz]
        j += 6 + sz
    return out


def zfield(blob: bytes) -> str:
    return blob.split(b"\x00", 1)[0].decode("latin1", "replace")


def expected_labels() -> list[tuple[str, str]]:
    """Mirror builder discovery: Base first, then color suffixes sorted."""
    out: list[tuple[str, str]] = []
    if NIF_BASE.is_file():
        out.append(("Base", r"PickmansWhisper\Decay\NecroBaseFemaleHead.nif"))
    suffix_re = re.compile(r"^NecroBaseFemaleHead_([A-Za-z][A-Za-z0-9]*)\.nif$")
    colored: list[tuple[str, str]] = []
    for nif in sorted(MESH_DIR.glob("NecroBaseFemaleHead_*.nif")):
        m = suffix_re.match(nif.name)
        if not m:
            continue
        colored.append((m.group(1), rf"PickmansWhisper\Decay\{nif.name}"))
    colored.sort(key=lambda t: t[0].lower())
    out.extend(colored)
    return out


def main() -> None:
    if not NIF_BASE.is_file():
        fail(f"missing Base NIF: {NIF_BASE.relative_to(ROOT)}")
    labels = expected_labels()
    if len(labels) < 2:
        fail(
            "expected Base + at least one NecroBaseFemaleHead_<Color>.nif "
            f"(found {labels!r})"
        )
    src = BUILDER.read_text(encoding="utf-8", errors="replace")
    for needle in (
        "FID_DECAY_FACE_BASE",
        "BOD2_SLOT_54",
        "0x01000000",
        "discover_decay_face_variants",
        "collect_decay_face_armor_records",
        "PickmansWhisper\\\\Decay\\\\NecroBaseFemaleHead.nif",
        "DecayFaceArmorIds.txt",
        'group(b"ARMA"',
        'group(b"ARMO"',
        "PW DecayFace ",
    ):
        if needle not in src:
            fail(f"build_hunger_spell_esp.py missing {needle!r}")
    if "NEXT_OID = 0x00000870" not in src and "NEXT_OID = 0x870" not in src:
        fail("NEXT_OID must sit past reserved decay-face armor FormIDs (0x870)")
    ok("builder declares decay-face ARMA/ARMO (slot 54, color variants)")

    import runpy

    runpy.run_path(str(BUILDER), run_name="__main__")
    if not ESP.is_file():
        fail("ESP not written")
    data = ESP.read_bytes()
    recs = parse_esp_types(data)
    armas = [(f, b) for t, f, b in recs if t == "ARMA"]
    armos = [(f, b) for t, f, b in recs if t == "ARMO"]
    if len(armas) != len(labels) or len(armos) != len(labels):
        fail(
            f"ESP ARMA/ARMO count mismatch: arma={len(armas)} armo={len(armos)} "
            f"labels={len(labels)} {labels!r}"
        )

    arma_by_edid = {}
    armo_by_edid = {}
    for fid, body in armas:
        af = fields(body)
        arma_by_edid[zfield(af.get("EDID", b""))] = (fid, af)
    for fid, body in armos:
        of = fields(body)
        armo_by_edid[zfield(of.get("EDID", b""))] = (fid, of)

    for i, (label, mesh_rel) in enumerate(labels):
        want_arma = f"PickmansWhisper_DecayFace_{label}_ARMA"
        want_armo = f"PickmansWhisper_DecayFace_{label}_ARMO"
        if want_arma not in arma_by_edid:
            fail(f"missing ARMA EDID {want_arma}")
        if want_armo not in armo_by_edid:
            fail(f"missing ARMO EDID {want_armo}")
        arma_fid, af = arma_by_edid[want_arma]
        armo_fid, of = armo_by_edid[want_armo]
        expect_arma = 0x01000850 + 2 * i
        expect_armo = 0x01000850 + 2 * i + 1
        if arma_fid != expect_arma or armo_fid != expect_armo:
            fail(
                f"{label} FormIDs wrong: ARMA 0x{arma_fid:08X}/ARMO 0x{armo_fid:08X} "
                f"want 0x{expect_arma:08X}/0x{expect_armo:08X}"
            )
        if af.get("BOD2") != struct.pack("<I", 0x01000000):
            fail(f"{label} ARMA BOD2 must be slot 54")
        if of.get("BOD2") != struct.pack("<I", 0x01000000):
            fail(f"{label} ARMO BOD2 must be slot 54")
        mod3 = zfield(af.get("MOD3", b""))
        if mod3 != mesh_rel:
            fail(f"{label} ARMA MOD3 wrong: {mod3!r} want {mesh_rel!r}")
        modl = struct.unpack("<I", of.get("MODL", b"\x00\x00\x00\x00"))[0]
        if modl != arma_fid:
            fail(f"{label} ARMO MODL must point at ARMA 0x{arma_fid:08X}")
        full = zfield(of.get("FULL", b""))
        if full != f"PW DecayFace {label}":
            fail(f"{label} ARMO FULL wrong: {full!r}")
        if label != "Base" and label not in full:
            fail(f"{label} must appear in FULL for console Help")

    ok(
        "ESP ARMA/ARMO for "
        + ", ".join(f"{lab}(0x{0x850 + 2 * i:03X}/0x{0x851 + 2 * i:03X})" for i, (lab, _) in enumerate(labels))
    )

    if not IDS.is_file():
        fail("DecayFaceArmorIds.txt not written")
    ids = IDS.read_text(encoding="utf-8", errors="replace")
    for label, _ in labels:
        if not re.search(rf"(?m)^{re.escape(label)}=\d+,\d+\s*$", ids):
            fail(f"DecayFaceArmorIds.txt must list {label}=arma,armo")
    ok("DecayFaceArmorIds.txt variant map present")

    ps1 = DEPLOY.read_text(encoding="utf-8", errors="replace")
    if "test_decay_face_armor_esp.py" not in ps1:
        fail("build-deploy-local.ps1 must run test_decay_face_armor_esp.py")
    ok("deploy gate includes decay-face armor contract")

    audio = AUDIO_POC.read_text(encoding="utf-8", errors="replace")
    if "NEXT_OID = 0x00000870" not in audio:
        fail("test_audio_poc.py must expect NEXT_OID = 0x00000870")
    ok("audio POC NEXT_OID aligned with decay-face reserve")

    print("All decay-face-armor ESP contracts passed.")


if __name__ == "__main__":
    main()
