#!/usr/bin/env python3
"""Diff our cut-off tits prop against a known-good vanilla Havok clutter NIF.

Read-only. Dumps BSXFlags, the bhkNPCollisionObject block, and the decoded Havok
packfile (bodies, motion, mass/inertia, shape) for both files so the difference
that keeps our prop frozen in the air is visible instead of guessed.

Usage:
  python tools/compare_prop_havok.py [reference.nif]
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from add_prop_tits_havok import (  # noqa: E402
    NIF_PATH,
    _load_pynifly,
    _physics_system_pack,
    parse_nif_header,
)

DEFAULT_REF = Path.home() / "Desktop" / "Meshes" / "Actors" / "Supermutant" / "CharacterAssets" / "GoreSuperMutantArmL.nif"


def dump_blocks(path: Path) -> dict:
    parsed = parse_nif_header(path)
    print(f"  blocks ({len(parsed['types'])}):")
    for i, (t, s, sz) in enumerate(zip(parsed["types"], parsed["starts"], parsed["sizes"])):
        print(f"    {i:3} {t:28} size={sz}")
    return parsed


def dump_bsx(parsed: dict) -> None:
    ids = [i for i, n in enumerate(parsed["types"]) if n == "BSXFlags"]
    if not ids:
        print("  BSXFlags: <none>")
        return
    for i in ids:
        start = parsed["starts"][i]
        val = int.from_bytes(parsed["data"][start + 4 : start + 8], "little")
        bits = []
        for bit, name in (
            (1, "ANIMATED"),
            (2, "HAVOK"),
            (4, "RAGDOLL"),
            (8, "COMPLEX"),
            (16, "ADDON"),
            (32, "EDITOR_MARKER"),
            (64, "DYNAMIC"),
            (128, "ARTICULATED"),
            (256, "NEEDS_XFORM_UPDATES"),
            (512, "EXTERNAL_EMIT"),
        ):
            if val & bit:
                bits.append(name)
        print(f"  BSXFlags = {val} ({'|'.join(bits) or 'none'})")


def dump_np_block(parsed: dict) -> None:
    ids = [i for i, n in enumerate(parsed["types"]) if n == "bhkNPCollisionObject"]
    if not ids:
        print("  bhkNPCollisionObject: <none>")
        return
    for i in ids:
        start = parsed["starts"][i]
        size = parsed["sizes"][i]
        blob = parsed["data"][start : start + size]
        target = int.from_bytes(blob[0:4], "little")
        flags = int.from_bytes(blob[4:6], "little")
        data_id = int.from_bytes(blob[6:10], "little")
        body_id = int.from_bytes(blob[10:14], "little")
        target_name = ""
        if 0 <= target < len(parsed["types"]):
            tstart = parsed["starts"][target]
            nid = int.from_bytes(parsed["data"][tstart : tstart + 4], "little")
            if 0 <= nid < len(parsed["strings"]):
                target_name = parsed["strings"][nid]
        co_bits = []
        for bit, name in (
            (1, "ACTIVE"),
            (4, "NOTIFY"),
            (8, "SET_LOCAL"),
            (16, "DBG_DISPLAY"),
            (32, "USE_VEL"),
            (64, "RESET"),
            (128, "SYNC_ON_UPDATE"),
            (1024, "ANIM_TARGETED"),
            (2048, "DISMEMBERED_LIMB"),
        ):
            if flags & bit:
                co_bits.append(name)
        print(
            f"  NP block size={size} target={target} ({target_name!r}) "
            f"flags={flags} ({'|'.join(co_bits) or 'none'}) data={data_id} bodyID={body_id}"
        )


def dump_packfile(path: Path, parsed: dict) -> None:
    from io_scene_nifly.pyn.bhk_autounpack import (
        f32,
        parse_bytes,
        parse_local_fixups,
        parse_physics_props,
        parse_section_headers,
        parse_virtual_fixups,
        u32,
    )

    try:
        _, pack = _physics_system_pack(parsed)
    except SystemExit as exc:
        print(f"  packfile: <unreadable> {exc}")
        return

    hdrs = parse_section_headers(pack)
    data_hdr = hdrs["__data__"]
    data_start = data_hdr.abs_start
    fixups = parse_local_fixups(pack, data_hdr)
    objects = parse_virtual_fixups(pack, data_hdr, hdrs["__classnames__"].abs_start)

    print(f"  packfile bytes={len(pack)}")
    print("  havok classes: " + ", ".join(sorted({cls for _, cls in objects})))

    props = parse_physics_props(pack, data_start, fixups, objects)
    if props is not None:
        print(
            f"  physics: dynamic={props.is_dynamic} mass={props.mass:.4f} "
            f"density={props.density:.4f} inertia={tuple(round(v, 6) for v in props.inertia)}"
        )
        print(
            f"           friction={props.friction:.3f} restitution={props.restitution:.3f} "
            f"gravity={props.gravity_factor:.3f} linDamp={props.linear_damping:.4f} "
            f"angDamp={props.angular_damping:.4f}"
        )

    for rel, cls in objects:
        if "hknpPhysicsSystemData" not in cls:
            continue
        psd_abs = data_start + rel
        body_count = u32(pack, psd_abs + 0x40 + 8) & 0x3FFFFFFF
        body_arr = fixups.get(rel + 0x40)
        print(f"  PSD bodies={body_count}")
        if body_arr is None:
            continue
        for i in range(body_count):
            body_abs = data_start + body_arr + i * 0x60
            raw = pack[body_abs : body_abs + 0x60]
            pos = struct.unpack_from("<4f", raw, 0x30)
            quat = struct.unpack_from("<4f", raw, 0x40)
            print(f"    body[{i}] full 0x60:")
            for off in range(0, 0x60, 16):
                print(f"      +{off:02X} " + " ".join(f"{b:02X}" for b in raw[off : off + 16]))
            print(
                f"    body[{i}] pos={tuple(round(v, 4) for v in pos)} "
                f"(game={tuple(round(v * HAVOK_TO_GAME, 2) for v in pos[:3])}) "
                f"quat={tuple(round(v, 4) for v in quat)}"
            )
        # dyn_motion (+0x20) / dyn_inertia (+0x30) presence
        for label, off in (("dyn_motion", 0x20), ("dyn_inertia", 0x30)):
            cnt = u32(pack, psd_abs + off + 8) & 0x3FFFFFFF
            arr = fixups.get(rel + off)
            print(f"  {label}: count={cnt} present={arr is not None}")
            if arr is None or cnt == 0:
                continue
            blob_abs = data_start + arr
            if label == "dyn_motion":
                print(
                    f"    motionType(+0x00)={pack[blob_abs]} "
                    f"gravity(+0x08)={f32(pack, blob_abs + 0x08):.4f} "
                    f"maxLinVel(+0x10)={f32(pack, blob_abs + 0x10):.3f}"
                )
                print(f"    first32={' '.join(f'{b:02X}' for b in pack[blob_abs:blob_abs + 32])}")
            else:
                inv_mass = f32(pack, blob_abs + 0x04)
                print(
                    f"    invMass={inv_mass:.6f} (mass={1.0 / inv_mass if inv_mass else 0:.4f}) "
                    f"density={f32(pack, blob_abs + 0x08):.4f} "
                    f"I=({f32(pack, blob_abs + 0x20):.6f}, {f32(pack, blob_abs + 0x24):.6f}, {f32(pack, blob_abs + 0x28):.6f})"
                )
                print(f"    first32={' '.join(f'{b:02X}' for b in pack[blob_abs:blob_abs + 32])}")

    try:
        shapes = parse_bytes(pack)
    except Exception as exc:
        print(f"  shapes: <unreadable> {exc}")
        return
    for s in shapes:
        vx = [v[0] for v in (s.verts or [])]
        vy = [v[1] for v in (s.verts or [])]
        vz = [v[2] for v in (s.verts or [])]
        extent = ""
        if vx:
            extent = (
                f" x=[{min(vx):.4f},{max(vx):.4f}] "
                f"y=[{min(vy):.4f},{max(vy):.4f}] z=[{min(vz):.4f},{max(vz):.4f}]"
            )
        print(
            f"  shape type={s.shape_type} name={s.name!r} verts={len(s.verts or [])} "
            f"faces={len(s.faces or [])} convexRadius={s.convex_radius:.5f}"
            f" children={len(s.children or [])}{extent}"
        )


HAVOK_TO_GAME = 69.99124908447266


def dump_geometry(path: Path) -> None:
    """Node transforms + mesh bounds, so hull vs visible mesh alignment is visible."""
    from io_scene_nifly.pyn.pynifly import NifFile

    nif = NifFile(str(path))
    for name, node in nif.nodes.items():
        xf = node.transform
        t = xf.translation
        print(
            f"  node {name!r} parent={getattr(node.parent, 'name', None)!r} "
            f"trans=({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}) scale={xf.scale:.4f}"
        )
    for shape in nif.shapes:
        verts = shape.verts
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        cz = (min(zs) + max(zs)) / 2
        print(
            f"  mesh {shape.name!r} verts={len(verts)} "
            f"center=({cx:.2f}, {cy:.2f}, {cz:.2f}) "
            f"x=[{min(xs):.2f},{max(xs):.2f}] y=[{min(ys):.2f},{max(ys):.2f}] z=[{min(zs):.2f},{max(zs):.2f}]"
        )


def report(label: str, path: Path) -> None:
    print("=" * 78)
    print(f"{label}: {path}")
    print("=" * 78)
    if not path.is_file():
        print("  MISSING")
        return
    parsed = dump_blocks(path)
    dump_bsx(parsed)
    dump_np_block(parsed)
    dump_geometry(path)
    dump_packfile(path, parsed)
    print()


def main() -> int:
    ref = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REF
    _load_pynifly()
    report("REFERENCE (works in-game)", ref)
    report("OURS (floats, unpushable)", NIF_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
