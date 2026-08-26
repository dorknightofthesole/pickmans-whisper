#!/usr/bin/env python3
"""Diagnose FemaleBody_Mutilated_Tits.nif's skin transform / weights against the
known-good reference body (nif/Meshes/Actors/Character/CharacterAssets/FemaleBody.nif).

Reads only — makes no changes. Uses the same standalone PyNifly-load trick as
tools/add_prop_tits_havok.py (no bpy import needed).
"""
from __future__ import annotations

import sys
import types
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUTILATED_NIF = ROOT / "Data" / "Meshes" / "PickmansWhisper" / "Characters" / "FemaleBody_Mutilated_Tits.nif"
REFERENCE_NIF = ROOT / "nif" / "Meshes" / "Actors" / "Character" / "CharacterAssets" / "FemaleBody.nif"
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


def load_pynifly():
    pkg = types.ModuleType("io_scene_nifly")
    pkg.__path__ = [str(PYNIFLY_ADDON)]
    pkg.__package__ = "io_scene_nifly"
    sys.modules["io_scene_nifly"] = pkg
    pyn = types.ModuleType("io_scene_nifly.pyn")
    pyn.__path__ = [str(PYNIFLY_ADDON / "pyn")]
    pyn.__package__ = "io_scene_nifly.pyn"
    sys.modules["io_scene_nifly.pyn"] = pyn
    from io_scene_nifly.pyn.pynifly import NifFile
    return NifFile


def fmt_xform(xf) -> str:
    t = xf.translation
    sc = xf.scale
    rot = xf.rotation
    return f"translation={tuple(round(c, 4) for c in t)} scale={round(sc, 6)} rot_row0={tuple(round(c, 4) for c in rot[0])}"


def describe(nif_path: Path, NifFile) -> None:
    print(f"=== {nif_path} ===")
    if not nif_path.is_file():
        print("  MISSING FILE")
        return
    nif = NifFile(str(nif_path))
    for shape in nif.shapes:
        print(f"shape: {shape.name}")
        try:
            print(f"  global_transform:   {fmt_xform(shape.global_transform)}")
        except Exception as e:
            print(f"  global_transform: ERROR {e}")
        try:
            has_g2s = shape.has_global_to_skin
            g2s = shape.global_to_skin
            print(f"  has_global_to_skin: {has_g2s}")
            print(f"  global_to_skin:     {fmt_xform(g2s)}")
        except Exception as e:
            print(f"  global_to_skin: ERROR {e}")

        try:
            names = shape.unique_bone_names
            print(f"  unique bone count:  {len(names)}")
        except Exception as e:
            print(f"  bone_names: ERROR {e}")
            names = []

        try:
            weights = shape.bone_weights  # {bone_name: [(vertex, weight), ...]}
            per_vertex_total = defaultdict(float)
            per_vertex_count = defaultdict(int)
            for bone_name, pairs in weights.items():
                for v, w in pairs:
                    per_vertex_total[v] += w
                    if w > 1e-6:
                        per_vertex_count[v] += 1
            n_verts = len(shape.verts) if hasattr(shape, "verts") else max(per_vertex_total, default=-1) + 1
            zero_weight = [v for v in range(n_verts) if per_vertex_total.get(v, 0.0) < 1e-6]
            over4 = [v for v, c in per_vertex_count.items() if c > 4]
            bad_sum = [v for v in range(n_verts) if per_vertex_total.get(v, 0.0) > 1e-6 and abs(per_vertex_total[v] - 1.0) > 0.02]
            print(f"  vertex count:       {n_verts}")
            print(f"  zero-weight verts:  {len(zero_weight)} (first 10: {zero_weight[:10]})")
            print(f"  >4-influence verts: {len(over4)} (first 10: {over4[:10]})")
            print(f"  weight-sum != 1.0:  {len(bad_sum)} (first 10 with sums: {[(v, round(per_vertex_total[v], 3)) for v in bad_sum[:10]]})")
        except Exception as e:
            print(f"  bone_weights: ERROR {e}")
        print()


def main() -> int:
    if not PYNIFLY_ADDON.is_dir():
        print(f"missing PyNifly addon at {PYNIFLY_ADDON}", file=sys.stderr)
        return 1
    NifFile = load_pynifly()
    describe(REFERENCE_NIF, NifFile)
    describe(MUTILATED_NIF, NifFile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
