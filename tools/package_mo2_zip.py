#!/usr/bin/env python3
"""Stage a FOMOD layout and write dist/PickmansWhisper-<version>.zip for MO2 install."""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
STAGING = DIST / "staging"
FOMOD_DST = STAGING / "fomod"


def read_version() -> str:
    info = ROOT / "fomod" / "info.xml"
    if info.is_file():
        try:
            ver = ET.parse(info).getroot().findtext("Version")
            if ver and ver.strip():
                return ver.strip()
        except ET.ParseError:
            pass
    meta = ROOT / "meta.ini"
    if meta.is_file():
        m = re.search(r"(?m)^version=(.+)$", meta.read_text(encoding="utf-8", errors="ignore"))
        if m:
            return m.group(1).strip()
    return "0.1.0"


def copy_tree_contents(src: Path, dst: Path) -> None:
    if not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise SystemExit(f"ERROR: missing {label}: {path}")


def require_file_or_dir(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"ERROR: missing staged {label}: {path}")


def stage() -> None:
    """Stage mod files at zip root (beside fomod/), never with destination=\"\".

    MO2 fails with \"invalid map<K, T> key\" when FOMOD uses an empty destination.
    """
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    FOMOD_DST.mkdir(parents=True)

    esp = ROOT / "Data" / "PickmansWhisper.esp"
    if not esp.is_file():
        esp = ROOT / "PickmansWhisper.esp"
    require_file(esp, "PickmansWhisper.esp")
    if esp.stat().st_size < 400:
        raise SystemExit(
            f"ERROR: PickmansWhisper.esp is only {esp.stat().st_size} bytes "
            "(need >= 400 with Knife Hunger SPEL)"
        )
    shutil.copy2(esp, STAGING / "PickmansWhisper.esp")

    (STAGING / "Scripts" / "Source" / "User").mkdir(parents=True)
    for script_stem in (
        "PickmansWhisperMainQuestScript",
        "PickmansWhisperBedGiftScript",
        "PickmansWhisperPlayerAliasScript",
    ):
        pex = ROOT / "Data" / "Scripts" / f"{script_stem}.pex"
        require_file(pex, f"compiled {script_stem}.pex")
        shutil.copy2(pex, STAGING / "Scripts" / f"{script_stem}.pex")
        psc = ROOT / "Data" / "Scripts" / "Source" / "User" / f"{script_stem}.psc"
        require_file(psc, f"{script_stem}.psc")
        shutil.copy2(psc, STAGING / "Scripts" / "Source" / "User" / f"{script_stem}.psc")

    copy_tree_contents(ROOT / "Data" / "MCM", STAGING / "MCM")
    copy_tree_contents(ROOT / "Data" / "PickmansWhisper", STAGING / "PickmansWhisper")
    copy_tree_contents(ROOT / "Data" / "Sound", STAGING / "Sound")
    require_file(
        STAGING / "Sound" / "PickmansWhisper" / "EndIt.xwm",
        "Sound/PickmansWhisper/EndIt.xwm",
    )

    docs = ROOT / "docs"
    if docs.is_dir():
        copy_tree_contents(docs, STAGING / "docs")

    for name in ("README.md", "meta.ini"):
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, STAGING / name)

    require_file(ROOT / "fomod" / "info.xml", "fomod/info.xml")
    require_file(ROOT / "fomod" / "ModuleConfig.xml", "fomod/ModuleConfig.xml")
    shutil.copy2(ROOT / "fomod" / "info.xml", FOMOD_DST / "info.xml")
    shutil.copy2(ROOT / "fomod" / "ModuleConfig.xml", FOMOD_DST / "ModuleConfig.xml")

    # Every FOMOD <file>/<folder source> must exist; empty destination="" breaks MO2.
    for src_name in (
        "PickmansWhisper.esp",
        "Scripts",
        "MCM",
        "PickmansWhisper",
        "Sound",
        "docs",
        "README.md",
        "meta.ini",
    ):
        require_file_or_dir(STAGING / src_name, src_name)


def write_zip(version: str) -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"PickmansWhisper-{version}.zip"
    if out.exists():
        out.unlink()

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(STAGING).as_posix())
    return out


def main() -> None:
    version = read_version()
    print(f"==> Packaging FOMOD zip (v{version})")
    stage()
    out = write_zip(version)
    print(f"    Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
