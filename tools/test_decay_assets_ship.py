#!/usr/bin/env python3
"""Decay asset trees must ship via deploy + FOMOD package.

Locks:
  - Data/Materials|Meshes|Textures/PickmansWhisper/Decay present with seed files
  - build-deploy-local.(ps1|sh) Sync/copy those trees (+ F4SE)
  - package_mo2_zip.py stages Materials/Meshes/Textures/F4SE
  - fomod/ModuleConfig.xml installs those folders

Usage:
  python tools/test_decay_assets_ship.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
PS1 = ROOT / "tools" / "build-deploy-local.ps1"
SH = ROOT / "tools" / "build-deploy-local.sh"
PACKAGE = ROOT / "tools" / "package_mo2_zip.py"
FOMOD = ROOT / "fomod" / "ModuleConfig.xml"

SEED = (
    DATA / "Materials" / "PickmansWhisper" / "Decay" / "Necro_Bruising01_d.bgsm",
    DATA / "Meshes" / "PickmansWhisper" / "Decay" / "NecroBaseFemaleHead.nif",
    DATA / "Textures" / "PickmansWhisper" / "Decay" / "Necro_Bruising01_d.DDS",
    DATA / "F4SE" / "Plugins" / "F4EE" / "Overlays" / "PickmansWhisper.esp" / "overlays.json",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> None:
    for path in SEED:
        if not path.is_file():
            fail(f"missing decay/F4SE asset: {path.relative_to(ROOT)}")
    decay_tex = DATA / "Textures" / "PickmansWhisper" / "Decay"
    bgsm_n = len(list((DATA / "Materials" / "PickmansWhisper" / "Decay").glob("*.bgsm")))
    dds_n = len({p.name.lower() for p in decay_tex.iterdir() if p.suffix.lower() == ".dds"})
    if bgsm_n < 12:
        fail(f"expected >=12 Decay .bgsm, found {bgsm_n}")
    if dds_n < 12:
        fail(f"expected >=12 Decay .DDS, found {dds_n}")
    ok(f"Data Decay assets present ({bgsm_n} bgsm, {dds_n} dds, head nif, overlays.json)")

    ps1 = PS1.read_text(encoding="utf-8", errors="replace")
    sh = SH.read_text(encoding="utf-8", errors="replace")
    pkg = PACKAGE.read_text(encoding="utf-8", errors="replace")
    fomod = FOMOD.read_text(encoding="utf-8", errors="replace")

    for name in ("Materials", "Meshes", "Textures", "F4SE"):
        if f'Sync-DataTree "{name}"' not in ps1:
            fail(f"build-deploy-local.ps1 must Sync-DataTree {name}")
        if f'sync_data_tree "{name}"' not in sh:
            fail(f"build-deploy-local.sh must sync_data_tree {name}")
        if f'ROOT / "Data" / "{name}"' not in pkg:
            fail(f"package_mo2_zip.py must stage Data/{name}")
        if f'source="{name}"' not in fomod:
            fail(f"ModuleConfig.xml must install folder {name}")

    if 'Sync-DataTree "PickmansWhisper"' not in ps1:
        fail("build-deploy-local.ps1 must Sync-DataTree PickmansWhisper (config+whispers)")
    if 'sync_data_tree "PickmansWhisper"' not in sh:
        fail("build-deploy-local.sh must sync_data_tree PickmansWhisper")
    if "NecroBaseFemaleHead.nif" not in ps1 or "NecroBaseFemaleHead.nif" not in pkg:
        fail("deploy/package must require NecroBaseFemaleHead.nif")
    if "test_decay_assets_ship.py" not in ps1:
        fail("build-deploy-local.ps1 must run test_decay_assets_ship.py")
    ok("deploy + package + FOMOD ship Materials/Meshes/Textures/F4SE")
    print("All decay-assets-ship contracts passed.")


if __name__ == "__main__":
    main()
