#!/usr/bin/env python3
"""Set BSXFlags + collision target on FemaleBody_Prop_Tits.nif.

Does not generate bhkNPCollisionObject, convex-hull verts, or packfile bytes.
Blender is the only source of hull geometry.

This script:
  1. Parses the NIF (collision must already exist from Blender/PyNifly)
  2. Writes BSXFlags = Havok | Dynamic | Articulated (194) — vanilla Baseball/TinCan
  3. Points bhkNPCollisionObject Target at Scene Root (PlaceAtMe motion root)
  4. Writes bodyID 0 and SYNC_ON_UPDATE flags (PyNifly leaves bodyID as NODEID_NONE,
     which FO4 uses as a body-array index and crashes)
  5. Verifies collision layer is Clutter or Prop, and material is Flesh, when those fields are readable
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
# bhkCOFlags.SYNC_ON_UPDATE — vanilla FO4 NP (GoreSuperMutantArmL pieces).
NP_COLLISION_FLAGS = 128
# Cut cap — SSOT path (docs/SLICE_F_CORPSE_SEVER.md). Blender re-export can drop it.
GORE_CAP_BGSM = r"Materials\Gore\GoreHumanLeg.BGSM"
GORE_CAP_SHAPE = "SeveredTitsBack002"

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

    disk = read_np_collision_disk(path)
    gore = _inspect_gore_cap(nif)
    info = {
        "bsx": int(bsx.flags) if bsx is not None else None,
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
            f"SYNC_ON_UPDATE ({NP_COLLISION_FLAGS}); found {flags}"
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


def _iter_np_body_layer_pack_offsets(packfile: bytes) -> list[int]:
    """Offsets of BodyCInfo collision-layer bytes inside a Havok packfile."""
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
    fixups = parse_local_fixups(packfile, data_hdr)
    objects = parse_virtual_fixups(packfile, data_hdr, hdrs["__classnames__"].abs_start)
    offsets = []
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
            offsets.append(body_abs + 0x10)
    return offsets


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
    """Write BSXFlags 194, hang collision on Scene Root, patch NP Target/body/flags/layer.

    PyNifly setBlock on bhkNPCollisionObject is routed to the physics-system
    setter and fails, so the 14-byte NP block and BodyCInfo layer byte are
    patched in the file after save. Hull verts are not rewritten.
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
    patch_bsx_loot_flags(path)
    patch_np_collision_target(path, COLLISION_TARGET_NAME)
    patch_np_collision_flags(path)
    patch_np_body_id(path)
    patch_np_clutter_layer(path)
    patch_gore_cap_shader_type(path)


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
    """Write SYNC_ON_UPDATE into the unique bhkNPCollisionObject Flags field."""
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
        verify_collision_meta(info)
        verify_gore_cap_shader(info)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    targets = ", ".join(info.get("collision_targets") or []) or "<none>"
    print(
        f"wrote {NIF_PATH.name}: BSXFlags={info['bsx']} (Havok|Dynamic|Articulated), "
        f"np target={targets}, bodyID={info.get('np_body_id')}, flags={info.get('np_flags')}, "
        f"layers={info.get('layers')}, np={info['np_count']} classic={info['classic_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
