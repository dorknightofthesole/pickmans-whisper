#!/usr/bin/env python3
"""Add FO4 dynamic Havok collision to FemaleBody_Prop_Tits.nif.

STAT/MSTT/MISC PlaceAtMe will not fall without a bhkNPCollisionObject + BSX Havok
flag. Re-run this if the visual mesh is re-exported from Blender.

Requires the installed PyNifly addon (NiflyDLL.dll).
"""
from __future__ import annotations

import sys
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

# Game units → Havok space (PyNifly FO4 scale).
HAVOK_SCALE = 69.99125
# Inventory-ish mass for a dynamic convex body. Not a contract pin.
PROP_MASS = 3.0
BSX_HAVOK_DYNAMIC = 2 | 64  # HAVOC | DYNAMIC


def _aabb_box(mn, mx):
    x0, y0, z0 = mn
    x1, y1, z1 = mx
    verts = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    # CCW when viewed from outside.
    faces = [
        [0, 2, 1],
        [0, 3, 2],
        [4, 5, 6],
        [4, 6, 7],
        [0, 1, 5],
        [0, 5, 4],
        [2, 3, 7],
        [2, 7, 6],
        [0, 4, 7],
        [0, 7, 3],
        [1, 2, 6],
        [1, 6, 5],
    ]
    return verts, faces


def main() -> int:
    if not NIF_PATH.is_file():
        print(f"missing {NIF_PATH}", file=sys.stderr)
        return 1
    if not PYNIFLY_ADDON.is_dir():
        print(f"missing PyNifly addon at {PYNIFLY_ADDON}", file=sys.stderr)
        return 1

    # Load pynifly without importing io_scene_nifly/__init__.py (that needs bpy).
    import types

    pkg = types.ModuleType("io_scene_nifly")
    pkg.__path__ = [str(PYNIFLY_ADDON)]
    pkg.__package__ = "io_scene_nifly"
    sys.modules["io_scene_nifly"] = pkg
    pyn = types.ModuleType("io_scene_nifly.pyn")
    pyn.__path__ = [str(PYNIFLY_ADDON / "pyn")]
    pyn.__package__ = "io_scene_nifly.pyn"
    sys.modules["io_scene_nifly.pyn"] = pyn

    from io_scene_nifly.pyn.pynifly import NifFile, bhkPhysicsSystem, BSXFlags
    from io_scene_nifly.pyn.nifdefs import PynBufferTypes
    from io_scene_nifly.pyn.bhk_autounpack import CollisionShape, PhysicsProps
    from io_scene_nifly.pyn.bhk_autopack import compute_density

    nif = NifFile(str(NIF_PATH))
    root = nif.root
    if root.collision_object is not None:
        print("collision already present — leaving nif unchanged")
        return 0

    world = []
    for shape in nif.shapes:
        xf = shape.global_transform
        rot = xf.rotation
        sc = xf.scale
        t = xf.translation
        for v in shape.verts:
            x, y, z = v
            rx = rot[0][0] * x + rot[0][1] * y + rot[0][2] * z
            ry = rot[1][0] * x + rot[1][1] * y + rot[1][2] * z
            rz = rot[2][0] * x + rot[2][1] * y + rot[2][2] * z
            world.append((rx * sc + t[0], ry * sc + t[1], rz * sc + t[2]))

    if not world:
        print("nif has no mesh verts", file=sys.stderr)
        return 1

    mn = [min(v[i] for v in world) for i in range(3)]
    mx = [max(v[i] for v in world) for i in range(3)]
    print(f"game AABB {mn} .. {mx}")

    havok_mn = [c / HAVOK_SCALE for c in mn]
    havok_mx = [c / HAVOK_SCALE for c in mx]
    verts, faces = _aabb_box(havok_mn, havok_mx)

    physics = PhysicsProps(is_dynamic=True, mass=PROP_MASS, gravity_factor=1.0)
    physics.density = compute_density(PROP_MASS, verts, faces, 0.0, "polytope")

    if root.get_extra_data(blockname="BSXFlags") is None:
        BSXFlags.New(nif, name="BSX", flags=BSX_HAVOK_DYNAMIC, parent=root)

    # bodyID 0 = first (only) body in the physics system — unset crashes FO4.
    coll = root.add_collision(
        None,
        flags=128,
        collision_type=PynBufferTypes.bhkNPCollisionObjectBufType,
        body_id=0,
    )
    shape = CollisionShape(
        shape_type="polytope",
        name="PropTitsHull",
        transform=None,
        verts=verts,
        faces=faces,
        convex_radius=0.0,
        children=[],
        physics=physics,
    )
    ps = bhkPhysicsSystem.New(nif, shapes=[shape], parent=coll)
    coll.properties.dataID = ps.id
    coll.properties.bodyID = 0

    nif.save()
    print(f"wrote dynamic Havok collision -> {NIF_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
