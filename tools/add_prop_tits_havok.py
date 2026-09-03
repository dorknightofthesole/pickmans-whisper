#!/usr/bin/env python3
"""Set BSXFlags + collision target on FemaleBody_Prop_Tits.nif.

Does not generate bhkNPCollisionObject, convex-hull verts, or packfile bytes.
Blender is the only source of hull geometry.

This script:
  1. Parses the NIF (collision must already exist from Blender/PyNifly)
  2. Writes BSXFlags = Havok | Dynamic | Articulated (194) — vanilla Baseball/TinCan
  3. Points bhkNPCollisionObject Target at Scene Root (PlaceAtMe motion root)
  4. Writes bodyID 0 and ACTIVE|SET_LOCAL|SYNC_ON_UPDATE flags (PyNifly leaves
     bodyID as NODEID_NONE, which FO4 uses as a body-array index and crashes;
     gore-only SYNC_ON_UPDATE does not simulate world clutter)
  5. Grows the short hknpMotionCinfo array to its real 0x70 element size and
     links each body to its motion (PyNifly leaves the motion id invalid, which
     makes the body static: it collides and loots but never falls or pushes)
  6. Writes inverse inertia from the existing hull AABB (PyNifly leaves it 0)
  7. Verifies collision layer is Clutter or Prop, and material is Flesh, when those fields are readable

See docs/Severed_Part_Guide.md for the whole pipeline and docs/SLICE_F_CORPSE_SEVER.md
for the field-by-field diff against vanilla GoreSuperMutantArmL.nif.
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

# Vanilla lootable MISC (Baseball.nif / TinCan01.nif): Havok (2) + Dynamic (64) + Articulated (128) = 194.
# 74 (Havok|Complex|Dynamic) is the gore-piece pattern and does not fall as clutter.
BSX_HAVOK = 2
BSX_DYNAMIC = 64
BSX_ARTICULATED = 128
BSX_LOOT_CLUTTER = BSX_HAVOK | BSX_DYNAMIC | BSX_ARTICULATED
COLLISION_TARGET_NAME = "Scene Root"
COLLISION_TARGET_BLOCK = "NiNode"

# On-disk bhkNPCollisionObject is 14 bytes: Target u32, Flags u16, Data u32, BodyID u32.
# PyNifly defaults BodyID to NODEID_NONE (0xFFFFFFFF). FO4 CreateInstance uses that as a
# packfile body index and access-violates (Buffout: MISC PickmansWhisper_PropCutOffTits).
NP_BODY_INDEX_NONE = 0xFFFFFFFF
NP_BODY_INDEX = 0
# bhkCOFlags: ACTIVE | SET_LOCAL | SYNC_ON_UPDATE. Gore pieces use SYNC only (128);
# world clutter needs ACTIVE or the body will not take gravity/pushes.
NP_CO_ACTIVE = 1
NP_CO_SET_LOCAL = 8
NP_CO_SYNC_ON_UPDATE = 128
NP_COLLISION_FLAGS = NP_CO_ACTIVE | NP_CO_SET_LOCAL | NP_CO_SYNC_ON_UPDATE
# Cut cap — SSOT path (docs/SLICE_F_CORPSE_SEVER.md). Blender re-export can drop it.
GORE_CAP_BGSM = r"Materials\Gore\GoreHumanLeg.BGSM"
GORE_CAP_SHAPE = "SeveredTitsBack002"

# hknpPhysicsSystemData array slots (Havok 2014.1), measured against vanilla
# Meshes/Actors/Supermutant/CharacterAssets/GoreSuperMutantArmL.nif.
PSD_MOTION_CINFOS = 0x30
PSD_BODY_CINFOS = 0x40

# sizeof(hknpMotionCinfo). Blender's exporter stops after centerOfMassWorld and
# allocates only 0x40, so the engine reads m_orientation out of the bodyCinfo
# array that follows and gets 0x7FFFFFFF (NaN) for two of its components.
MOTION_CINFO_STRIDE = 0x70
MOTION_CINFO_INV_MASS = 0x04
MOTION_CINFO_INV_INERTIA = 0x20
MOTION_CINFO_ORIENTATION = 0x40

# Havok stores 1/I here, not I — the sibling field at +0x04 is 1/mass. Across all
# three vanilla gore bodies, stored * boxInertia == 2/3 on every axis.
INV_INERTIA_BOX_FACTOR = 2.0 / 3.0

BODY_CINFO_STRIDE = 0x60
BODY_CINFO_MOTION_ID = 0x0C
BODY_CINFO_LAYER = 0x10
BODY_CINFO_ORIENTATION = 0x40

# hknpBodyCinfo::m_motionId default. A body left on this sentinel has no motion,
# which is exactly how Havok spells "static": it collides and can be looted, but
# never falls and cannot be pushed.
MOTION_ID_INVALID = 0x7FFFFFFF

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
    sizes_off = off
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
        "sizes_off": sizes_off,
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
    inertias = []
    for raw in blobs:
        inertias.extend(_np_inertia_tensors(raw))
    if not inertias:
        try:
            _, pack = _physics_system_pack(parse_nif_header(path))
            inertias.extend(_np_inertia_tensors(pack))
        except SystemExit:
            pass

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

    disk = read_np_collision_disk(path)
    motion = read_np_motion_disk(path)
    gore = _inspect_gore_cap(nif)
    info = {
        "bsx": read_bsx_disk_flags(path),
        "np_count": np_count,
        "classic_count": classic_count,
        "layers": layers,
        "materials": materials,
        "packfile_blobs": blobs,
        "block_types": block_types,
        "collision_targets": collision_targets,
        "np_body_id": disk.get("body_id"),
        "np_flags": disk.get("flags"),
        "gore_has_cap": gore["has_cap"],
        "gore_facegen": gore["facegen"],
        "gore_double_sided": gore["double_sided"],
        "gore_skin_tint": gore["gore_skin_tint"],
        "gore_shader_type": gore["gore_shader_type"],
        "np_inertia": inertias,
        "np_motion_alloc": motion.get("motion_alloc") or {},
        "np_motion_ids": motion.get("motion_ids") or [],
        "np_inv_inertia": motion.get("inv_inertia") or [],
        "np_inv_inertia_expected": motion.get("inv_inertia_expected") or [],
        "np_motion_orientations": motion.get("motion_orientations") or [],
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
    if not any(is_clutter_or_prop_layer(layer) for layer in usable):
        found = ", ".join(_enum_name(layer) for layer in (info["layers"] or [])) or "<missing>"
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


def is_bsx_loot_clutter(flags) -> bool:
    """True if BSXFlags is exactly Havok | Dynamic | Articulated (194)."""
    return _as_int(flags) == BSX_LOOT_CLUTTER


def verify_bsx_flags(info: dict) -> None:
    if info.get("bsx") is None:
        raise SystemExit(
            "PickmansWhisper Error: BSXFlags missing after write"
        )
    if not is_bsx_loot_clutter(info["bsx"]):
        raise SystemExit(
            "PickmansWhisper Error: BSXFlags must be "
            f"{BSX_LOOT_CLUTTER} (Havok|Dynamic|Articulated, vanilla junk); "
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


def verify_np_instance_fields(info: dict) -> None:
    """Reject NODEID_NONE bodyID — FO4 CreateInstance crashes on that sentinel."""
    if info.get("np_count", 0) == 0:
        return
    body_id = info.get("np_body_id")
    if body_id is None or body_id == NP_BODY_INDEX_NONE:
        raise SystemExit(
            "PickmansWhisper Error: bhkNPCollisionObject bodyID is NODEID_NONE "
            "(FO4 CreateInstance crash)"
        )
    flags = info.get("np_flags")
    if flags != NP_COLLISION_FLAGS:
        raise SystemExit(
            "PickmansWhisper Error: bhkNPCollisionObject flags must be "
            f"ACTIVE|SET_LOCAL|SYNC_ON_UPDATE ({NP_COLLISION_FLAGS}); found {flags}"
        )


def verify_np_inertia(info: dict) -> None:
    """Reject inertia Havok cannot simulate: missing, zero, or stored as I not 1/I."""
    if info.get("np_count", 0) == 0:
        return
    tensors = info.get("np_inertia") or []
    if not tensors:
        raise SystemExit(
            "PickmansWhisper Error: hknpMotionCinfo missing — Havok will not simulate"
        )
    for tensor in tensors:
        if all(abs(v) <= 1e-12 for v in tensor):
            raise SystemExit(
                "PickmansWhisper Error: inverse inertia is all zero — that is infinite "
                "inertia, so the body can never rotate"
            )

    got = info.get("np_inv_inertia") or []
    want = info.get("np_inv_inertia_expected") or []
    for i, (have, expect) in enumerate(zip(got, want)):
        for axis, (a, b) in enumerate(zip(have, expect)):
            if b <= 0.0 or abs(a - b) > max(1e-4, abs(b) * 1e-3):
                raise SystemExit(
                    f"PickmansWhisper Error: motion[{i}] axis {axis} inverse inertia is "
                    f"{a:.6g}, expected {b:.6g} — Havok stores 1/I here, not I"
                )


def verify_motion_cinfo_stride(info: dict) -> None:
    """Reject a short hknpMotionCinfo array — Havok reads NaN past its end."""
    if info.get("np_count", 0) == 0:
        return
    alloc = info.get("np_motion_alloc") or {}
    if not alloc:
        raise SystemExit(
            "PickmansWhisper Error: no hknpMotionCinfo array — the body has no motion"
        )
    if alloc["allocated"] < alloc["needed"]:
        raise SystemExit(
            f"PickmansWhisper Error: hknpMotionCinfo array is {alloc['allocated']} bytes "
            f"for {alloc['count']} element(s); Havok reads {alloc['needed']} and would "
            "take m_orientation from the bodyCinfo array"
        )
    for i, quat in enumerate(info.get("np_motion_orientations") or []):
        if not 0.75 <= sum(v * v for v in quat) <= 1.25:
            raise SystemExit(
                f"PickmansWhisper Error: motion[{i}] orientation {quat} is not a unit "
                "quaternion — Havok will produce NaN transforms"
            )


def verify_body_motion_ids(info: dict) -> None:
    """Reject bodies left on the default motion id — that is how Havok spells static."""
    if info.get("np_count", 0) == 0:
        return
    ids = info.get("np_motion_ids") or []
    if not ids:
        raise SystemExit("PickmansWhisper Error: no hknpBodyCinfo to check for a motion")
    motions = len(info.get("np_inv_inertia") or [])
    for i, motion_id in enumerate(ids):
        if motion_id == MOTION_ID_INVALID:
            raise SystemExit(
                f"PickmansWhisper Error: body[{i}] motionId is the invalid sentinel — "
                "the prop would collide and loot but never fall or push"
            )
        if motion_id >= motions:
            raise SystemExit(
                f"PickmansWhisper Error: body[{i}] motionId {motion_id} has no matching "
                f"motion (only {motions})"
            )


def _collision_host(nif):
    root = nif.root
    if not root or getattr(root, "name", "") != COLLISION_TARGET_NAME:
        raise SystemExit(
            f"PickmansWhisper Error: nif root must be named {COLLISION_TARGET_NAME!r}"
        )
    return root


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


def _pack_layout(packfile: bytes):
    """(data section header, local fixups, virtual fixups) for a Havok packfile."""
    from io_scene_nifly.pyn.bhk_autounpack import (
        parse_local_fixups,
        parse_section_headers,
        parse_virtual_fixups,
    )

    hdrs = parse_section_headers(packfile)
    if "__data__" not in hdrs or "__classnames__" not in hdrs:
        return None, {}, []
    data_hdr = hdrs["__data__"]
    return (
        data_hdr,
        parse_local_fixups(packfile, data_hdr),
        parse_virtual_fixups(packfile, data_hdr, hdrs["__classnames__"].abs_start),
    )


def _iter_psd_arrays(packfile: bytes, slot: int, stride: int) -> list[int]:
    """Packfile-absolute start of every element of one hknpPhysicsSystemData array."""
    from io_scene_nifly.pyn.bhk_autounpack import u32

    data_hdr, fixups, objects = _pack_layout(packfile)
    if data_hdr is None:
        return []
    data_start = data_hdr.abs_start
    offsets = []
    for rel, cls in objects:
        if "hknpPhysicsSystemData" not in cls:
            continue
        count = u32(packfile, data_start + rel + slot + 8) & 0x3FFFFFFF
        arr = fixups.get(rel + slot)
        if arr is None or count == 0:
            continue
        for i in range(count):
            start = data_start + arr + i * stride
            if start + stride > len(packfile):
                continue
            offsets.append(start)
    return offsets


def _iter_body_cinfo_abs(packfile: bytes) -> list[int]:
    """Packfile-absolute start of each hknpBodyCinfo."""
    return _iter_psd_arrays(packfile, PSD_BODY_CINFOS, BODY_CINFO_STRIDE)


def _iter_np_body_layer_pack_offsets(packfile: bytes) -> list[int]:
    """Offsets of BodyCInfo collision-layer bytes inside a Havok packfile."""
    return [abs_off + BODY_CINFO_LAYER for abs_off in _iter_body_cinfo_abs(packfile)]


def _iter_dyn_inertia_abs(packfile: bytes) -> list[int]:
    """Packfile-absolute starts of each hknpMotionCinfo blob."""
    return _iter_psd_arrays(packfile, PSD_MOTION_CINFOS, MOTION_CINFO_STRIDE)


def _motion_cinfo_alloc(packfile: bytes) -> dict:
    """Where the hknpMotionCinfo array lives and how many bytes it was given.

    The allocation is the run up to the next array the packfile points at, so a
    short-writing exporter is detectable without trusting a declared size.
    """
    from io_scene_nifly.pyn.bhk_autounpack import u32

    data_hdr, fixups, objects = _pack_layout(packfile)
    if data_hdr is None:
        return {}
    for rel, cls in objects:
        if "hknpPhysicsSystemData" not in cls:
            continue
        count = u32(packfile, data_hdr.abs_start + rel + PSD_MOTION_CINFOS + 8) & 0x3FFFFFFF
        arr = fixups.get(rel + PSD_MOTION_CINFOS)
        if arr is None or count == 0:
            continue
        data_end = data_hdr.local_fix - data_hdr.abs_start
        later = [dst for dst in fixups.values() if dst > arr] + [data_end]
        return {
            "psd_rel": rel,
            "arr_rel": arr,
            "count": count,
            "allocated": min(later) - arr,
            "needed": count * MOTION_CINFO_STRIDE,
        }
    return {}


def _np_inertia_tensors(packfile: bytes) -> list[tuple[float, float, float]]:
    tensors = []
    for start in _iter_dyn_inertia_abs(packfile):
        ixx, iyy, izz = struct.unpack_from("<fff", packfile, start + 0x20)
        tensors.append((ixx, iyy, izz))
    return tensors


def _hull_half_extents(packfile: bytes) -> tuple[float, float, float]:
    """Half-extents of the existing hull AABB. Does not rewrite hull verts."""
    from io_scene_nifly.pyn.bhk_autounpack import parse_bytes

    try:
        shapes = parse_bytes(packfile)
    except Exception as exc:
        raise SystemExit(
            f"PickmansWhisper Error: cannot read hull AABB for inertia ({exc})"
        ) from exc
    verts: list[tuple[float, float, float]] = []
    extra = 0.0
    stack = list(shapes)
    while stack:
        shape = stack.pop()
        verts.extend(shape.verts or [])
        extra = max(extra, float(getattr(shape, "convex_radius", 0.0) or 0.0))
        radius = float(getattr(shape, "sphere_radius", 0.0) or 0.0)
        if radius > 0.0 and not (shape.verts or []):
            verts.extend(
                (
                    (-radius, 0.0, 0.0),
                    (radius, 0.0, 0.0),
                    (0.0, -radius, 0.0),
                    (0.0, radius, 0.0),
                    (0.0, 0.0, -radius),
                    (0.0, 0.0, radius),
                )
            )
        stack.extend(shape.children or [])
    if not verts:
        raise SystemExit(
            "PickmansWhisper Error: hull has no verts — cannot derive inertia from AABB"
        )
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    hx = (max(xs) - min(xs)) * 0.5 + extra
    hy = (max(ys) - min(ys)) * 0.5 + extra
    hz = (max(zs) - min(zs)) * 0.5 + extra
    min_half = 1e-4
    return (max(hx, min_half), max(hy, min_half), max(hz, min_half))


def _box_inertia(
    mass: float, hx: float, hy: float, hz: float
) -> tuple[float, float, float]:
    ax, ay, az = hx * 2.0, hy * 2.0, hz * 2.0
    ixx = mass / 12.0 * (ay * ay + az * az)
    iyy = mass / 12.0 * (ax * ax + az * az)
    izz = mass / 12.0 * (ax * ax + ay * ay)
    return (ixx, iyy, izz)


def _physics_system_pack(parsed: dict) -> tuple[int, bytes]:
    """Return (file offset of packfile bytes, packfile) for the unique physics system."""
    ids = [i for i, name in enumerate(parsed["types"]) if name == "bhkPhysicsSystem"]
    if len(ids) != 1:
        raise SystemExit(
            "PickmansWhisper Error: expected one bhkPhysicsSystem; "
            f"found {len(ids)}"
        )
    i = ids[0]
    start = parsed["starts"][i]
    size = parsed["sizes"][i]
    if size < 8:
        raise SystemExit(f"PickmansWhisper Error: bhkPhysicsSystem block too small ({size})")
    num = int.from_bytes(parsed["data"][start : start + 4], "little")
    payload_off = start + 4
    if payload_off + num > len(parsed["data"]) or num + 4 > size:
        raise SystemExit("PickmansWhisper Error: bhkPhysicsSystem data length mismatch")
    return payload_off, bytes(parsed["data"][payload_off : payload_off + num])


def _is_gore_cap_shader(shader) -> bool:
    name = (getattr(shader, "name", "") or "").replace("\\", "/").lower()
    return "gorehumanleg" in name


def _is_gore_cap_shape(shape) -> bool:
    name = getattr(shape, "name", "") or ""
    return name == GORE_CAP_SHAPE or name.startswith(GORE_CAP_SHAPE + ":")


def restore_gore_cap_material(nif) -> None:
    """Point the cut cap at GoreHumanLeg.BGSM if Blender exported skin on both shapes."""
    found = False
    for shape in nif.shapes:
        if not _is_gore_cap_shape(shape):
            continue
        found = True
        sp = getattr(shape, "shader", None)
        if sp is None:
            raise SystemExit(
                f"PickmansWhisper Error: {GORE_CAP_SHAPE} has no shader to restore GoreHumanLeg"
            )
        sp.name = GORE_CAP_BGSM
    if not found:
        raise SystemExit(
            f"PickmansWhisper Error: missing cut cap shape {GORE_CAP_SHAPE!r}"
        )


def _inspect_gore_cap(nif) -> dict:
    from io_scene_nifly.pyn.nifconstants import BSLSPShaderType, ShaderFlags1, ShaderFlags2

    has_cap = False
    facegen = None
    double_sided = None
    shader_type = None
    for shape in nif.shapes:
        if not _is_gore_cap_shape(shape):
            continue
        has_cap = True
        sp = getattr(shape, "shader", None)
        if sp is None:
            continue
        props = sp.properties
        if hasattr(props, "Shader_Type"):
            shader_type = int(props.Shader_Type)
        if not hasattr(props, "Shader_Flags_1"):
            continue
        flags1 = int(props.Shader_Flags_1)
        flags2 = int(props.Shader_Flags_2)
        facegen = bool(flags1 & int(ShaderFlags1.FACEGEN_RGB_TINT))
        double_sided = bool(flags2 & int(ShaderFlags2.DOUBLE_SIDED))
        has_cap = has_cap or _is_gore_cap_shader(sp)
    return {
        "has_cap": has_cap,
        "facegen": facegen,
        "double_sided": double_sided,
        "gore_shader_type": shader_type,
        "gore_skin_tint": shader_type == int(BSLSPShaderType.Skin_Tint),
    }


def patch_gore_cap_shader(nif) -> None:
    """MISC has no actor tint. Skin Tint + FACEGEN on a dropped mesh does not draw."""
    from io_scene_nifly.pyn.nifconstants import BSLSPShaderType, ShaderFlags1, ShaderFlags2

    for shape in nif.shapes:
        if not _is_gore_cap_shape(shape):
            continue
        sp = getattr(shape, "shader", None)
        if sp is None:
            continue
        props = sp.properties
        if not hasattr(props, "shaderflags1_clear"):
            continue
        props.Shader_Type = int(BSLSPShaderType.Default)
        if hasattr(props, "bslspShaderType"):
            props.bslspShaderType = int(BSLSPShaderType.Default)
        props.shaderflags1_clear(ShaderFlags1.FACEGEN_RGB_TINT)
        props.shaderflags1_clear(ShaderFlags1.SKINNED)
        props.shaderflags2_set(ShaderFlags2.DOUBLE_SIDED)
        sp.write_properties()


def verify_gore_cap_shader(info: dict) -> None:
    if not info.get("gore_has_cap"):
        raise SystemExit(
            f"PickmansWhisper Error: missing cut cap shape {GORE_CAP_SHAPE!r}"
        )
    if info.get("gore_skin_tint"):
        raise SystemExit(
            "PickmansWhisper Error: cut cap must not use Skin Tint (invisible on a MISC)"
        )
    if info.get("gore_facegen"):
        raise SystemExit(
            "PickmansWhisper Error: cut cap must not use FACEGEN_RGB_TINT on a MISC"
        )
    if not info.get("gore_double_sided"):
        raise SystemExit(
            "PickmansWhisper Error: cut cap must be DOUBLE_SIDED"
        )


def apply_bsx_and_retarget(path: Path) -> None:
    """Write BSXFlags 194, hang collision on Scene Root, patch NP Target/body/flags/layer/motion.

    PyNifly setBlock on bhkNPCollisionObject is routed to the physics-system
    setter and fails, so the 14-byte NP block and everything inside the Havok
    packfile are patched in the file after save. Hull verts are not rewritten.
    """
    from io_scene_nifly.pyn.nifconstants import NODEID_NONE
    from io_scene_nifly.pyn.pynifly import BSXFlags, NifFile

    nif = NifFile(str(path))
    root = nif.root
    bsx = root.get_extra_data(blockname="BSXFlags")
    if bsx is None:
        BSXFlags.New(nif, name="BSX", flags=BSX_LOOT_CLUTTER, parent=root)
    else:
        bsx.flags = BSX_LOOT_CLUTTER

    host = _collision_host(nif)
    owner, coll = _np_collision_owner(nif)
    host.properties.collisionID = coll.id
    host.write_properties()
    if owner.id != host.id:
        owner.properties.collisionID = NODEID_NONE
        owner.write_properties()

    restore_gore_cap_material(nif)
    patch_gore_cap_shader(nif)

    nif.save()
    del nif
    patch_np_collision_target(path, COLLISION_TARGET_NAME)
    patch_np_collision_flags(path)
    patch_np_body_id(path)
    # Resize the motion array before anything reads offsets inside it, then give
    # the body a motion to follow — those two are what make the prop dynamic.
    patch_motion_cinfo_stride(path)
    patch_body_motion_id(path)
    patch_np_clutter_layer(path)
    patch_np_inertia_from_hull(path)
    patch_gore_cap_shader_type(path)
    # nif.save() writes gore-style 74 (Havok|Complex|Dynamic). Write loot 194 last
    # so a later PyNifly open cannot be the source of truth for verification.
    patch_bsx_loot_flags(path)


def _write_physics_system_pack(path: Path, parsed: dict, new_pack: bytes) -> None:
    """Splice a resized Havok packfile back into the NIF, fixing both length fields."""
    ids = [i for i, name in enumerate(parsed["types"]) if name == "bhkPhysicsSystem"]
    if len(ids) != 1:
        raise SystemExit(
            f"PickmansWhisper Error: expected one bhkPhysicsSystem; found {len(ids)}"
        )
    i = ids[0]
    start = parsed["starts"][i]
    old_size = parsed["sizes"][i]
    old_num = int.from_bytes(parsed["data"][start : start + 4], "little")
    grow = len(new_pack) - old_num

    blob = bytearray(parsed["data"])
    blob[start : start + old_size] = len(new_pack).to_bytes(4, "little") + new_pack

    # The NIF block-size table is a second length field; leaving it stale makes
    # every block after this one unreadable.
    size_at = parsed["sizes_off"] + i * 4
    blob[size_at : size_at + 4] = (old_size + grow).to_bytes(4, "little")
    path.write_bytes(bytes(blob))


def patch_motion_cinfo_stride(path: Path) -> None:
    """Grow a short-written hknpMotionCinfo array to the real 0x70 element size.

    Blender writes 0x40 per element, so Havok reads m_orientation (+0x40) out of
    the bodyCinfo array that follows and gets a NaN quaternion. The array is
    re-emitted at the end of the data section rather than expanded in place, so
    no existing fixup offset has to move.
    """
    from io_scene_nifly.pyn.bhk_autounpack import parse_section_headers

    parsed = parse_nif_header(path)
    payload_off, pack = _physics_system_pack(parsed)
    alloc = _motion_cinfo_alloc(pack)
    if not alloc:
        raise SystemExit(
            "PickmansWhisper Error: no hknpMotionCinfo array — Havok has no motion to attach"
        )
    if alloc["allocated"] >= alloc["needed"]:
        return

    count = alloc["count"]
    old_stride = alloc["allocated"] // count
    if old_stride <= 0:
        raise SystemExit(
            f"PickmansWhisper Error: hknpMotionCinfo allocation {alloc['allocated']} "
            f"cannot hold {count} element(s)"
        )

    hdrs = parse_section_headers(pack)
    data_hdr = hdrs["__data__"]
    for name, hdr in hdrs.items():
        if name != "__data__" and hdr.abs_start > data_hdr.abs_start:
            raise SystemExit(
                f"PickmansWhisper Error: section {name!r} follows __data__; cannot append"
            )

    bodies = _iter_body_cinfo_abs(pack)
    new_arr = bytearray(alloc["needed"])
    for i in range(count):
        src = data_hdr.abs_start + alloc["arr_rel"] + i * old_stride
        keep = min(old_stride, MOTION_CINFO_STRIDE)
        dst = i * MOTION_CINFO_STRIDE
        new_arr[dst : dst + keep] = pack[src : src + keep]

        # Vanilla keeps the motion orientation equal to its body's; anything
        # unnormalised here feeds NaN straight into the solver.
        quat = (0.0, 0.0, 0.0, 1.0)
        if i < len(bodies):
            body_q = struct.unpack_from("<4f", pack, bodies[i] + BODY_CINFO_ORIENTATION)
            if sum(v * v for v in body_q) > 0.25:
                quat = body_q
        struct.pack_into("<4f", new_arr, dst + MOTION_CINFO_ORIENTATION, *quat)

    insert_at = data_hdr.local_fix
    if (insert_at - data_hdr.abs_start) % 16 or len(new_arr) % 16:
        raise SystemExit(
            "PickmansWhisper Error: hknpMotionCinfo append would break 16-byte alignment"
        )
    new_dst = insert_at - data_hdr.abs_start

    new_pack = bytearray(pack)
    new_pack[insert_at:insert_at] = new_arr

    # Everything the section header points at (fixup tables, exports, imports,
    # end) sits after the data content, so each offset shifts by the new bytes.
    sec_base = None
    for i in range(3):
        base = 0x40 + i * 0x40
        if new_pack[base : base + 19].split(b"\x00")[0] == b"__data__":
            sec_base = base
            break
    if sec_base is None:
        raise SystemExit("PickmansWhisper Error: no __data__ section header to re-offset")
    for field in (0x18, 0x1C, 0x20, 0x24, 0x28, 0x2C):
        at = sec_base + field
        cur = int.from_bytes(new_pack[at : at + 4], "little")
        new_pack[at : at + 4] = (cur + len(new_arr)).to_bytes(4, "little")

    # Repoint the array at its new home. The fixup table moved, so re-read it.
    moved = parse_section_headers(bytes(new_pack))["__data__"]
    want_src = alloc["psd_rel"] + PSD_MOTION_CINFOS
    pos = moved.local_fix
    while pos + 8 <= moved.global_fix:
        if int.from_bytes(new_pack[pos : pos + 4], "little") == want_src:
            new_pack[pos + 4 : pos + 8] = int(new_dst).to_bytes(4, "little")
            break
        pos += 8
    else:
        raise SystemExit(
            "PickmansWhisper Error: no local fixup for the hknpMotionCinfo array"
        )

    _write_physics_system_pack(path, parsed, bytes(new_pack))


def patch_body_motion_id(path: Path) -> None:
    """Point every hknpBodyCinfo at its motion. Without this the body is static."""
    parsed = parse_nif_header(path)
    payload_off, pack = _physics_system_pack(parsed)
    bodies = _iter_body_cinfo_abs(pack)
    motions = len(_iter_dyn_inertia_abs(pack))
    if not bodies:
        raise SystemExit("PickmansWhisper Error: no hknpBodyCinfo to link to a motion")
    if motions < len(bodies):
        raise SystemExit(
            f"PickmansWhisper Error: {len(bodies)} body/bodies but only {motions} motion(s)"
        )

    blob = bytearray(parsed["data"])
    for i, abs_off in enumerate(bodies):
        at = payload_off + abs_off + BODY_CINFO_MOTION_ID
        blob[at : at + 4] = int(i).to_bytes(4, "little")
    path.write_bytes(bytes(blob))


def patch_np_clutter_layer(path: Path) -> None:
    """Write COLU Clutter into BodyCInfo layer bytes. Does not touch hull verts."""
    parsed = parse_nif_header(path)
    payload_off, pack = _physics_system_pack(parsed)
    layer_offs = _iter_np_body_layer_pack_offsets(pack)
    if not layer_offs:
        raise SystemExit(
            "PickmansWhisper Error: no BodyCInfo layer bytes to patch as Clutter"
        )
    blob = bytearray(parsed["data"])
    for rel in layer_offs:
        blob[payload_off + rel] = LAYER_CLUTTER
    path.write_bytes(bytes(blob))


def _inverse_box_inertia(pack: bytes, abs_off: int) -> tuple[float, float, float]:
    """m_inverseInertiaLocal for one hknpMotionCinfo, derived from the hull AABB."""
    inv_mass = struct.unpack_from("<f", pack, abs_off + MOTION_CINFO_INV_MASS)[0]
    if inv_mass <= 0.0:
        raise SystemExit(
            "PickmansWhisper Error: hknpMotionCinfo inverse mass is 0 — cannot derive inertia"
        )
    ixx, iyy, izz = _box_inertia(1.0 / inv_mass, *_hull_half_extents(pack))
    if ixx <= 0.0 or iyy <= 0.0 or izz <= 0.0:
        raise SystemExit("PickmansWhisper Error: derived box inertia is zero")
    return (
        INV_INERTIA_BOX_FACTOR / ixx,
        INV_INERTIA_BOX_FACTOR / iyy,
        INV_INERTIA_BOX_FACTOR / izz,
    )


def patch_np_inertia_from_hull(path: Path) -> None:
    """Write m_inverseInertiaLocal from the hull AABB. Does not rewrite hull verts."""
    parsed = parse_nif_header(path)
    payload_off, pack = _physics_system_pack(parsed)
    starts = _iter_dyn_inertia_abs(pack)
    if not starts:
        raise SystemExit(
            "PickmansWhisper Error: no hknpMotionCinfo to patch from hull AABB"
        )
    blob = bytearray(parsed["data"])
    for abs_off in starts:
        inv = _inverse_box_inertia(pack, abs_off)
        struct.pack_into(
            "<fff", blob, payload_off + abs_off + MOTION_CINFO_INV_INERTIA, *inv
        )
    path.write_bytes(bytes(blob))


def patch_gore_cap_shader_type(path: Path) -> None:
    """Force the cut-cap lighting shader to Default, not Skin Tint (type 5)."""
    parsed = parse_nif_header(path)
    shader_i = None
    for i, block_type in enumerate(parsed["types"]):
        if block_type != "BSTriShape":
            continue
        start = parsed["starts"][i]
        name_id = int.from_bytes(parsed["data"][start : start + 4], "little")
        name = (
            parsed["strings"][name_id]
            if 0 <= name_id < len(parsed["strings"])
            else ""
        )
        if name != GORE_CAP_SHAPE and not name.startswith(GORE_CAP_SHAPE + ":"):
            continue
        for j in range(i + 1, len(parsed["types"])):
            if parsed["types"][j] == "BSLightingShaderProperty":
                shader_i = j
                break
        break
    if shader_i is None:
        raise SystemExit(
            f"PickmansWhisper Error: no lighting shader after {GORE_CAP_SHAPE}"
        )
    start = parsed["starts"][shader_i]
    blob = bytearray(parsed["data"])
    blob[start : start + 4] = (0).to_bytes(4, "little")
    path.write_bytes(bytes(blob))


def read_bsx_disk_flags(path: Path) -> int | None:
    """Read BSXFlags integerData from the NIF bytes the game loads. Never writes."""
    parsed = parse_nif_header(path)
    ids = [i for i, name in enumerate(parsed["types"]) if name == "BSXFlags"]
    if len(ids) != 1:
        return None
    i = ids[0]
    if parsed["sizes"][i] < 8:
        return None
    start = parsed["starts"][i]
    return int.from_bytes(parsed["data"][start + 4 : start + 8], "little")


def read_np_motion_disk(path: Path) -> dict:
    """Read motion linkage + inertia from the NIF bytes the game loads. Never writes."""
    from io_scene_nifly.pyn.bhk_autounpack import u32

    parsed = parse_nif_header(path)
    if "bhkPhysicsSystem" not in parsed["types"]:
        return {}
    try:
        _, pack = _physics_system_pack(parsed)
    except SystemExit:
        return {}

    motions = _iter_dyn_inertia_abs(pack)
    return {
        "motion_alloc": _motion_cinfo_alloc(pack),
        "motion_ids": [
            u32(pack, abs_off + BODY_CINFO_MOTION_ID) for abs_off in _iter_body_cinfo_abs(pack)
        ],
        "inv_inertia": [
            struct.unpack_from("<fff", pack, abs_off + MOTION_CINFO_INV_INERTIA)
            for abs_off in motions
        ],
        "inv_inertia_expected": [_inverse_box_inertia(pack, abs_off) for abs_off in motions],
        "motion_orientations": [
            struct.unpack_from("<4f", pack, abs_off + MOTION_CINFO_ORIENTATION)
            for abs_off in motions
        ],
    }


def patch_bsx_loot_flags(path: Path) -> None:
    """Write Havok|Dynamic|Articulated (194) into the unique BSXFlags block."""
    parsed = parse_nif_header(path)
    bsx_ids = [i for i, name in enumerate(parsed["types"]) if name == "BSXFlags"]
    if len(bsx_ids) != 1:
        raise SystemExit(
            f"PickmansWhisper Error: expected one BSXFlags block; found {len(bsx_ids)}"
        )
    i = bsx_ids[0]
    size = parsed["sizes"][i]
    if size < 8:
        raise SystemExit(f"PickmansWhisper Error: BSXFlags block too small ({size})")
    start = parsed["starts"][i]
    blob = bytearray(parsed["data"])
    blob[start + 4 : start + 8] = int(BSX_LOOT_CLUTTER).to_bytes(4, "little")
    path.write_bytes(bytes(blob))


def _nif_blocks_named(parsed: dict, block_type: str, target_name: str) -> list[int]:
    found = []
    strings = parsed["strings"]
    for i, name in enumerate(parsed["types"]):
        if name != block_type:
            continue
        start = parsed["starts"][i]
        name_id = int.from_bytes(parsed["data"][start : start + 4], "little")
        if 0 <= name_id < len(strings) and strings[name_id] == target_name:
            found.append(i)
    return found


def _unique_np_block(parsed: dict) -> tuple[int, int, int]:
    """Return (block_index, start, size) for the unique 14-byte NP collision block."""
    np_ids = [i for i, name in enumerate(parsed["types"]) if name == "bhkNPCollisionObject"]
    if len(np_ids) != 1:
        raise SystemExit(
            "PickmansWhisper Error: expected one bhkNPCollisionObject; "
            f"found {len(np_ids)}"
        )
    np_i = np_ids[0]
    size = parsed["sizes"][np_i]
    if size < 14:
        raise SystemExit(
            f"PickmansWhisper Error: bhkNPCollisionObject block too small ({size})"
        )
    return np_i, parsed["starts"][np_i], size


def read_np_collision_disk(path: Path) -> dict:
    """Read Target/Flags/Data/BodyID from the unique NP block. Never writes."""
    parsed = parse_nif_header(path)
    if "bhkNPCollisionObject" not in parsed["types"]:
        return {}
    _, start, _ = _unique_np_block(parsed)
    blob = parsed["data"][start : start + 14]
    return {
        "target": int.from_bytes(blob[0:4], "little"),
        "flags": int.from_bytes(blob[4:6], "little"),
        "data_id": int.from_bytes(blob[6:10], "little"),
        "body_id": int.from_bytes(blob[10:14], "little"),
    }


def patch_np_collision_target(path: Path, target_name: str) -> None:
    """Set the unique bhkNPCollisionObject Target link to Scene Root (NiNode)."""
    parsed = parse_nif_header(path)
    host_ids = _nif_blocks_named(parsed, COLLISION_TARGET_BLOCK, target_name)
    if len(host_ids) != 1:
        raise SystemExit(
            f"PickmansWhisper Error: expected one {target_name!r} {COLLISION_TARGET_BLOCK}; "
            f"found {len(host_ids)}"
        )
    _, start, _ = _unique_np_block(parsed)
    blob = bytearray(parsed["data"])
    blob[start : start + 4] = int(host_ids[0]).to_bytes(4, "little")
    path.write_bytes(bytes(blob))


def patch_np_collision_flags(path: Path) -> None:
    """Write ACTIVE|SET_LOCAL|SYNC_ON_UPDATE into the unique NP Flags field."""
    parsed = parse_nif_header(path)
    _, start, _ = _unique_np_block(parsed)
    blob = bytearray(parsed["data"])
    blob[start + 4 : start + 6] = int(NP_COLLISION_FLAGS).to_bytes(2, "little")
    path.write_bytes(bytes(blob))


def patch_np_body_id(path: Path) -> None:
    """Write body index 0 so FO4 does not CreateInstance with NODEID_NONE."""
    parsed = parse_nif_header(path)
    _, start, _ = _unique_np_block(parsed)
    blob = bytearray(parsed["data"])
    blob[start + 10 : start + 14] = int(NP_BODY_INDEX).to_bytes(4, "little")
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
        verify_np_instance_fields(info)
        verify_motion_cinfo_stride(info)
        verify_body_motion_ids(info)
        verify_np_inertia(info)
        verify_collision_meta(info)
        verify_gore_cap_shader(info)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    targets = ", ".join(info.get("collision_targets") or []) or "<none>"
    print(
        f"wrote {NIF_PATH.name}: BSXFlags={info['bsx']} (Havok|Dynamic|Articulated), "
        f"np target={targets}, bodyID={info.get('np_body_id')}, flags={info.get('np_flags')}, "
        f"motionIds={info.get('np_motion_ids')}, invInertia={info.get('np_inv_inertia')}, "
        f"layers={info.get('layers')}, "
        f"np={info['np_count']} classic={info['classic_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
