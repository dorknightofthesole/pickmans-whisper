#!/usr/bin/env python3
"""Set BSXFlags + collision target on FemaleBody_Prop_Tits.nif.

Does not generate bhkNPCollisionObject, convex-hull verts, or packfile bytes.
Blender is the only source of hull geometry.

This script:
  1. Parses the NIF (collision must already exist from Blender/PyNifly)
  2. Writes BSXFlags = Havok | Complex | Dynamic (74)
  3. Points bhkNPCollisionObject Target at FusionGirlReduced (not Scene Root)
  4. Verifies collision layer is Clutter or Prop, and material is Flesh, when those fields are readable
"""
from __future__ import annotations

import struct
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NIF_PATH = ROOT / "Data" / "Meshes" / "PickmansWhisper" / "Props" / "FemaleBody_Prop_Tits.nif"
PYNIFLY_ADDON = (
    Path.home()
    / "AppData"
    / "Roaming"
    / "Blender Foundation"
    / "Blender"
    / "5.2"
    / "scripts"
    / "addons"
    / "io_scene_nifly"
)

# NifSkope BSXFlags: Havok (2) + Complex (8) + Dynamic (64) = 74.
BSX_HAVOK = 2
BSX_COMPLEX = 8
BSX_DYNAMIC = 64
BSX_HAVOK_COMPLEX_DYNAMIC = BSX_HAVOK | BSX_COMPLEX | BSX_DYNAMIC
COLLISION_TARGET_NAME = "FusionGirlReduced"

# Bethesda collision layers (same numbering on FO4 COLU / SkyrimCollisionLayer).
LAYER_CLUTTER = 4
LAYER_PROPS = 10
LAYER_OK = {LAYER_CLUTTER, LAYER_PROPS}
LAYER_OK_NAMES = {"CLUTTER", "PROPS", "PROP"}

# PyNifly/NifSkope have no FLESH token; Skin / Meat / Organic are the flesh impacts.
FLESH_NAME_NEEDLES = ("FLESH", "SKIN", "MEAT", "ORGANIC")


def _load_pynifly() -> None:
    pkg = types.ModuleType("io_scene_nifly")
    pkg.__path__ = [str(PYNIFLY_ADDON)]
    pkg.__package__ = "io_scene_nifly"
    sys.modules["io_scene_nifly"] = pkg
    pyn = types.ModuleType("io_scene_nifly.pyn")
    pyn.__path__ = [str(PYNIFLY_ADDON / "pyn")]
    pyn.__package__ = "io_scene_nifly.pyn"
    sys.modules["io_scene_nifly.pyn"] = pyn


def _norm_token(raw) -> str:
    if raw is None:
        return ""
    if hasattr(raw, "name"):
        raw = raw.name
    text = str(raw).strip()
    if "." in text:
        text = text.split(".")[-1]
    for prefix in ("SKY_HAV_MAT_", "FO4_HAV_MAT_", "HAV_MAT_", "L_"):
        if text.upper().startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.upper().replace("-", "_").replace(" ", "_")


def is_clutter_or_prop_layer(raw) -> bool:
    """True if the collision layer is Clutter or Prop/Props."""
    if raw is None:
        return False
    if hasattr(raw, "value"):
        try:
            if int(raw.value) in LAYER_OK:
                return True
        except (TypeError, ValueError):
            pass
    try:
        if int(raw) in LAYER_OK:
            return True
    except (TypeError, ValueError):
        pass
    token = _norm_token(raw)
    return token in LAYER_OK_NAMES


def _as_int(raw):
    if raw is None:
        return None
    if hasattr(raw, "value"):
        raw = raw.value
    try:
        if isinstance(raw, str):
            return int(raw, 0)
        return int(raw)
    except (TypeError, ValueError):
        return None


def is_flesh_material(raw) -> bool:
    """True if the Havok material is Flesh (or Skin/Meat/Organic equivalents)."""
    if raw is None:
        return False
    token = _norm_token(raw)
    if any(needle in token for needle in FLESH_NAME_NEEDLES):
        return True
    ival = _as_int(raw)
    if ival is None:
        return False
    try:
        from io_scene_nifly.pyn.nifconstants import SkyrimHavokMaterial

        named = SkyrimHavokMaterial.get_name(ival)
    except Exception:
        return False
    return any(needle in _norm_token(named) for needle in FLESH_NAME_NEEDLES)


def _enum_name(raw) -> str:
    if raw is None:
        return "<missing>"
    if hasattr(raw, "name"):
        return str(raw.name)
    try:
        from io_scene_nifly.pyn.nifconstants import SkyrimCollisionLayer, SkyrimHavokMaterial

        ival = int(raw)
        try:
            return SkyrimCollisionLayer(ival).name
        except Exception:
            pass
        named = SkyrimHavokMaterial.get_name(ival)
        if named and named != str(ival):
            return named
        return str(ival)
    except (TypeError, ValueError):
        return str(raw)


def parse_nif_header(path: Path) -> dict:
    """FO4 NIF block table: types, sizes, file offsets, strings."""
    data = path.read_bytes()
    nl = data.find(b"\n")
    if nl < 0:
        return {"data": data, "types": [], "sizes": [], "starts": [], "strings": []}
    off = nl + 1
    off += 4 + 1 + 4  # version, endian, user version
    num_blocks = int.from_bytes(data[off : off + 4], "little")
    off += 4
    off += 4  # user version 2
    for _ in range(4):
        ln = data[off]
        off += 1 + ln
    num_block_types = int.from_bytes(data[off : off + 2], "little")
    off += 2
    type_names: list[str] = []
    for _ in range(num_block_types):
        ln = int.from_bytes(data[off : off + 4], "little")
        off += 4
        type_names.append(data[off : off + ln].decode("utf-8", errors="replace"))
        off += ln
    index = [
        int.from_bytes(data[off + i * 2 : off + i * 2 + 2], "little")
        for i in range(num_blocks)
    ]
    off += num_blocks * 2
    sizes = [
        int.from_bytes(data[off + i * 4 : off + i * 4 + 4], "little")
        for i in range(num_blocks)
    ]
    off += num_blocks * 4
    num_strings = int.from_bytes(data[off : off + 4], "little")
    off += 4
    off += 4  # max string length
    strings: list[str] = []
    for _ in range(num_strings):
        ln = int.from_bytes(data[off : off + 4], "little")
        off += 4
        strings.append(data[off : off + ln].decode("utf-8", errors="replace"))
        off += ln
    num_groups = int.from_bytes(data[off : off + 4], "little")
    off += 4
    off += num_groups * 4
    types = [type_names[i] for i in index if 0 <= i < len(type_names)]
    starts = []
    cursor = off
    for size in sizes:
        starts.append(cursor)
        cursor += size
    return {
        "data": data,
        "types": types,
        "sizes": sizes,
        "starts": starts,
        "strings": strings,
    }


def read_nif_block_types(path: Path) -> list[str]:
    """Header block-type list. Does not depend on PyNifly collision links."""
    return parse_nif_header(path)["types"]


def format_no_collision_error(block_types: list[str]) -> str:
    listed = ", ".join(block_types) if block_types else "<none>"
    return (
        "PickmansWhisper Error: FemaleBody_Prop_Tits.nif has no Havok collision "
        f"(blocks: {listed}). Export a collision object from Blender/PyNifly."
    )


def _iter_nodes(nif):
    # Force node table load; names are not unique, so walk node_ids + shapes.
    _ = nif.nodes
    seen = set()
    for node in list(nif.node_ids.values()) + list(nif.shapes):
        nid = id(node)
        if nid in seen:
            continue
        seen.add(nid)
        yield node


def _physics_blobs(nif) -> tuple[bytes, ...]:
    blobs = []
    for node in _iter_nodes(nif):
        co = getattr(node, "collision_object", None)
        if co is None or getattr(co, "blockname", "") != "bhkNPCollisionObject":
            continue
        ps = co.physics_system
        if ps is None:
            continue
        blobs.append(bytes(ps.data or b""))
    return tuple(blobs)


def _np_layers(packfile: bytes) -> list[int]:
    from io_scene_nifly.pyn.bhk_autounpack import (
        parse_local_fixups,
        parse_section_headers,
        parse_virtual_fixups,
        u32,
    )

    hdrs = parse_section_headers(packfile)
    if "__data__" not in hdrs or "__classnames__" not in hdrs:
        return []
    data_hdr = hdrs["__data__"]
    data_start = data_hdr.abs_start
    cn_start = hdrs["__classnames__"].abs_start
    fixups = parse_local_fixups(packfile, data_hdr)
    objects = parse_virtual_fixups(packfile, data_hdr, cn_start)
    layers = []
    for rel, cls in objects:
        if "hknpPhysicsSystemData" not in cls:
            continue
        psd_abs = data_start + rel
        body_count = u32(packfile, psd_abs + 0x40 + 8) & 0x3FFFFFFF
        body_arr = fixups.get(rel + 0x40)
        if body_arr is None or body_count == 0:
            continue
        for i in range(body_count):
            body_abs = data_start + body_arr + i * 0x60
            if body_abs + 0x11 > len(packfile):
                continue
            layers.append(packfile[body_abs + 0x10])
    return layers


def _np_material_candidates(packfile: bytes) -> list:
    from io_scene_nifly.pyn.bhk_autounpack import (
        parse_section_headers,
        parse_virtual_fixups,
    )
    from io_scene_nifly.pyn.nifconstants import SkyrimHavokMaterial

    hdrs = parse_section_headers(packfile)
    if "__data__" not in hdrs or "__classnames__" not in hdrs:
        return []
    data_hdr = hdrs["__data__"]
    data_start = data_hdr.abs_start
    cn_start = hdrs["__classnames__"].abs_start
    objects = parse_virtual_fixups(packfile, data_hdr, cn_start)
    known = {int(m) for m in SkyrimHavokMaterial if int(m)}
    found = []
    ascii_hits = []
    for needle in (b"FLESH", b"Flesh", b"SKIN", b"Skin"):
        if needle in packfile:
            ascii_hits.append(needle.decode("ascii"))
    found.extend(ascii_hits)
    for rel, cls in objects:
        if "hknpBSMaterialProperties" not in cls:
            continue
        abs_off = data_start + rel
        blob = packfile[abs_off : abs_off + 0x50]
        for off in range(0, len(blob) - 3, 4):
            val = struct.unpack_from("<I", blob, off)[0]
            if val in known:
                found.append(val)
            elif is_flesh_material(val):
                found.append(val)
    return found


def _walk_classic_shapes(shape):
    if shape is None:
        return
    yield shape
    children = getattr(shape, "children", None) or []
    for child in children:
        yield from _walk_classic_shapes(child)
    child = getattr(shape, "child", None)
    if child is not None:
        yield from _walk_classic_shapes(child)


def inspect_prop(path: Path) -> dict:
    """Read collision + BSXFlags. Never writes."""
    from io_scene_nifly.pyn.pynifly import NifFile

    nif = NifFile(str(path))
    bsx = nif.root.get_extra_data(blockname="BSXFlags")
    layers = []
    materials = []
    np_count = 0
    classic_count = 0
    collision_targets = []
    blobs = _physics_blobs(nif)

    for node in _iter_nodes(nif):
        co = getattr(node, "collision_object", None)
        if co is None:
            continue
        block = getattr(co, "blockname", "")
        if block == "bhkNPCollisionObject":
            np_count += 1
            targ = getattr(co, "target", None)
            collision_targets.append(getattr(targ, "name", "") if targ else "")
            ps = co.physics_system
            raw = bytes(ps.data or b"") if ps is not None else b""
            if not raw:
                continue
            for layer in _np_layers(raw):
                layers.append(layer)
            for mat in _np_material_candidates(raw):
                materials.append(mat)
            continue

        body = getattr(co, "body", None)
        if body is None:
            continue
        classic_count += 1
        props = getattr(body, "properties", None)
        if props is not None and hasattr(props, "collisionFilter_layer"):
            layers.append(props.collisionFilter_layer)
        for shape in _walk_classic_shapes(getattr(body, "shape", None)):
            sp = getattr(shape, "properties", None)
            if sp is not None and hasattr(sp, "bhkMaterial"):
                materials.append(sp.bhkMaterial)

    block_types = read_nif_block_types(path)
    if np_count == 0 and "bhkNPCollisionObject" in block_types:
        np_count = 1
    if classic_count == 0 and any(
        t in block_types for t in ("bhkRigidBody", "bhkRigidBodyT", "bhkCollisionObject")
    ):
        classic_count = 1

    info = {
        "bsx": int(bsx.flags) if bsx is not None else None,
        "np_count": np_count,
        "classic_count": classic_count,
        "layers": layers,
        "materials": materials,
        "packfile_blobs": blobs,
        "block_types": block_types,
        "collision_targets": collision_targets,
    }
    del nif
    return info


def _usable_layers(layers) -> list:
    """Drop FO4 NP unidentified defaults (0 / 255) that are not real dropdowns."""
    usable = []
    for layer in layers:
        n = _as_int(layer)
        if n in (None, 0, 255, 0xFF) and not is_clutter_or_prop_layer(layer):
            continue
        usable.append(layer)
    return usable


def verify_collision_meta(info: dict) -> None:
    if info["np_count"] == 0 and info["classic_count"] == 0:
        raise SystemExit(format_no_collision_error(info.get("block_types") or []))

    # Classic bhkRigidBody exposes NifSkope Layer/Material. FO4 NP polytopes often
    # do not; only fail those when a real value is readable and wrong.
    if info["classic_count"]:
        if not any(is_clutter_or_prop_layer(layer) for layer in info["layers"]):
            found = ", ".join(_enum_name(layer) for layer in info["layers"]) or "<missing>"
            raise SystemExit(
                "PickmansWhisper Error: collision layer must be Clutter or Prop; "
                f"found {found}"
            )
        if not any(is_flesh_material(mat) for mat in info["materials"]):
            found = ", ".join(_enum_name(mat) for mat in info["materials"]) or "<missing>"
            raise SystemExit(
                "PickmansWhisper Error: collision material must be Flesh; "
                f"found {found}"
            )
        return

    usable = _usable_layers(info["layers"])
    if usable and not any(is_clutter_or_prop_layer(layer) for layer in usable):
        found = ", ".join(_enum_name(layer) for layer in usable)
        raise SystemExit(
            "PickmansWhisper Error: collision layer must be Clutter or Prop; "
            f"found {found}"
        )
    mats = [m for m in info["materials"] if m is not None]
    if mats and not any(is_flesh_material(mat) for mat in mats):
        found = ", ".join(_enum_name(mat) for mat in mats)
        raise SystemExit(
            "PickmansWhisper Error: collision material must be Flesh; "
            f"found {found}"
        )


def is_bsx_havok_complex_dynamic(flags) -> bool:
    """True if BSXFlags is exactly Havok | Complex | Dynamic (74)."""
    return _as_int(flags) == BSX_HAVOK_COMPLEX_DYNAMIC


def verify_bsx_flags(info: dict) -> None:
    if info.get("bsx") is None:
        raise SystemExit(
            "PickmansWhisper Error: BSXFlags missing after write"
        )
    if not is_bsx_havok_complex_dynamic(info["bsx"]):
        raise SystemExit(
            "PickmansWhisper Error: BSXFlags must be "
            f"{BSX_HAVOK_COMPLEX_DYNAMIC} (Havok|Complex|Dynamic); "
            f"found {info['bsx']}"
        )


def verify_collision_target(info: dict) -> None:
    targets = [t for t in (info.get("collision_targets") or []) if t]
    if COLLISION_TARGET_NAME not in targets:
        found = ", ".join(targets) if targets else "<none>"
        raise SystemExit(
            "PickmansWhisper Error: bhkNPCollisionObject target must be "
            f"{COLLISION_TARGET_NAME}; found {found}"
        )
    extras = [t for t in targets if t != COLLISION_TARGET_NAME]
    if extras:
        raise SystemExit(
            "PickmansWhisper Error: bhkNPCollisionObject target must not be "
            f"{', '.join(extras)}"
        )


def _fusion_girl_reduced(nif):
    matches = [s for s in nif.shapes if s.name == COLLISION_TARGET_NAME]
    if not matches:
        raise SystemExit(
            f"PickmansWhisper Error: shape {COLLISION_TARGET_NAME!r} missing"
        )
    if len(matches) != 1:
        raise SystemExit(
            "PickmansWhisper Error: expected one "
            f"{COLLISION_TARGET_NAME!r} shape, found {len(matches)}"
        )
    return matches[0]


def _np_collision_owner(nif):
    for node in _iter_nodes(nif):
        co = getattr(node, "collision_object", None)
        if co is not None and getattr(co, "blockname", "") == "bhkNPCollisionObject":
            return node, co
    for shape in nif.shapes:
        co = getattr(shape, "collision_object", None)
        if co is not None and getattr(co, "blockname", "") == "bhkNPCollisionObject":
            return shape, co
    raise SystemExit(
        "PickmansWhisper Error: bhkNPCollisionObject missing — export collision from Blender"
    )


def apply_bsx_and_retarget(path: Path) -> None:
    """Write BSXFlags 74, hang collision on FusionGirlReduced, patch NP Target.

    PyNifly setBlock on bhkNPCollisionObject is routed to the physics-system
    setter and fails, so the 14-byte Target link is patched in the file after save.
    Hull / packfile bytes are not rewritten.
    """
    from io_scene_nifly.pyn.nifconstants import NODEID_NONE
    from io_scene_nifly.pyn.pynifly import BSXFlags, NifFile

    nif = NifFile(str(path))
    root = nif.root
    bsx = root.get_extra_data(blockname="BSXFlags")
    if bsx is None:
        BSXFlags.New(nif, name="BSX", flags=BSX_HAVOK_COMPLEX_DYNAMIC, parent=root)
    else:
        bsx.flags = BSX_HAVOK_COMPLEX_DYNAMIC

    fusion = _fusion_girl_reduced(nif)
    owner, coll = _np_collision_owner(nif)
    fusion.properties.collisionID = coll.id
    fusion.write_properties()
    if owner.id != fusion.id:
        owner.properties.collisionID = NODEID_NONE
        owner.write_properties()

    nif.save()
    del nif
    patch_np_collision_target(path, COLLISION_TARGET_NAME)


def patch_np_collision_target(path: Path, target_name: str) -> None:
    """Set the unique bhkNPCollisionObject Target link to the named BSTriShape."""
    parsed = parse_nif_header(path)
    types = parsed["types"]
    np_ids = [i for i, name in enumerate(types) if name == "bhkNPCollisionObject"]
    if len(np_ids) != 1:
        raise SystemExit(
            "PickmansWhisper Error: expected one bhkNPCollisionObject; "
            f"found {len(np_ids)}"
        )
    fusion_ids = []
    for i, name in enumerate(types):
        if name != "BSTriShape":
            continue
        start = parsed["starts"][i]
        name_id = int.from_bytes(parsed["data"][start : start + 4], "little")
        strings = parsed["strings"]
        if 0 <= name_id < len(strings) and strings[name_id] == target_name:
            fusion_ids.append(i)
    if len(fusion_ids) != 1:
        raise SystemExit(
            f"PickmansWhisper Error: expected one {target_name!r} BSTriShape; "
            f"found {len(fusion_ids)}"
        )
    np_i = np_ids[0]
    size = parsed["sizes"][np_i]
    if size < 4:
        raise SystemExit(
            f"PickmansWhisper Error: bhkNPCollisionObject block too small ({size})"
        )
    start = parsed["starts"][np_i]
    blob = bytearray(parsed["data"])
    blob[start : start + 4] = int(fusion_ids[0]).to_bytes(4, "little")
    path.write_bytes(bytes(blob))


def main() -> int:
    if not NIF_PATH.is_file():
        print(f"PickmansWhisper Error: missing {NIF_PATH}", file=sys.stderr)
        return 1
    if not PYNIFLY_ADDON.is_dir():
        print(f"PickmansWhisper Error: missing PyNifly addon at {PYNIFLY_ADDON}", file=sys.stderr)
        return 1

    _load_pynifly()
    info = inspect_prop(NIF_PATH)
    if info["np_count"] == 0 and info["classic_count"] == 0:
        print(format_no_collision_error(info.get("block_types") or []), file=sys.stderr)
        return 1
    try:
        apply_bsx_and_retarget(NIF_PATH)
        info = inspect_prop(NIF_PATH)
        verify_bsx_flags(info)
        verify_collision_target(info)
        verify_collision_meta(info)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    targets = ", ".join(info.get("collision_targets") or []) or "<none>"
    print(
        f"wrote {NIF_PATH.name}: BSXFlags={info['bsx']} (Havok|Complex|Dynamic), "
        f"np target={targets}, np={info['np_count']} classic={info['classic_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
