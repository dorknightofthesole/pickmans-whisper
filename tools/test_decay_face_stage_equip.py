#!/usr/bin/env python3
"""Slice I — stage→face ARMO map + corpse EquipItem path.

Locks:
  - DecayFaceStages.txt 0=none 1=none 2=Red 3=Green 4=Black
  - CorpseDecay loads DecayFaceArmorIds.txt + DecayFaceStages.txt
  - ApplyDecayStageOverlays equips via ApplyDecayFaceArmorForStage
  - none stages strip face masks (no ARMO)
  - EquipItem(abPreventRemoval=false) — playable / removable
  - Actor.psc declares real EquipItem Native
  - Deploy gate runs this contract

Usage:
  python tools/test_decay_face_stage_equip.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"
STAGES = ROOT / "Data" / "PickmansWhisper" / "config" / "DecayFaceStages.txt"
IDS = ROOT / "Data" / "PickmansWhisper" / "config" / "DecayFaceArmorIds.txt"
ACTOR = ROOT / "tools" / "stubs" / "Actor.psc"
PS1 = ROOT / "tools" / "build-deploy-local.ps1"
SH = ROOT / "tools" / "build-deploy-local.sh"

EXPECTED = {
    0: "none",
    1: "none",
    2: "Red",
    3: "Green",
    4: "Black",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?ms)^((?:Bool|Int|Float|String|Form|Actor|Armor|Function)\s+)?Function\s+{re.escape(name)}\b.*?^EndFunction",
        text,
    )
    if not m:
        fail(f"missing Function {name}")
    return m.group(0)


def main() -> None:
    if not STAGES.is_file():
        fail(f"missing {STAGES.relative_to(ROOT)}")
    stage_map: dict[int, str] = {}
    for line in STAGES.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^(\d+)=([A-Za-z][A-Za-z0-9]*)$", s)
        if not m:
            fail(f"bad DecayFaceStages.txt row: {line!r}")
        stage_map[int(m.group(1))] = m.group(2)
    if stage_map != EXPECTED:
        fail(f"DecayFaceStages.txt map wrong:\n  got={stage_map}\n  want={EXPECTED}")
    ok("DecayFaceStages.txt 0=none 1=none 2=Red 3=Green 4=Black")

    if not IDS.is_file():
        fail("DecayFaceArmorIds.txt missing — rebuild ESP")
    id_text = IDS.read_text(encoding="utf-8")
    for label in EXPECTED.values():
        if label == "none":
            continue
        if not re.search(rf"(?m)^{re.escape(label)}=\d+,\d+\s*$", id_text):
            fail(f"DecayFaceArmorIds.txt missing ARMO for label {label}")
    ok("DecayFaceArmorIds.txt covers masked stage labels")

    actor = ACTOR.read_text(encoding="utf-8", errors="replace")
    if "Function EquipItem(Form akItem, Bool abPreventRemoval = False, Bool abSilent = False) Native" not in actor:
        fail("Actor.psc must declare real FO4 EquipItem Native")
    ok("Actor.psc EquipItem Native present")

    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    for needle in (
        'FACE_STAGE_FILE = "DecayFaceStages.txt"',
        'FACE_ARMOR_IDS_FILE = "DecayFaceArmorIds.txt"',
        "EnsureDecayFaceArmorBanks",
        "ApplyDecayFaceArmorForStage",
        "StripDecayFaceArmors",
        "EquipItem(armor, False, True)",
        "AddItem(armor, 1, True)",
    ):
        if needle not in decay:
            fail(f"CorpseDecay missing {needle!r}")

    ensure = extract_function(decay, "EnsureDecayFaceArmorBanks")
    if "FACE_ARMOR_IDS_FILE" not in ensure:
        fail("EnsureDecayFaceArmorBanks must load FACE_ARMOR_IDS_FILE")
    if "GetLinesFromFile(FACE_ARMOR_IDS_FILE" not in ensure:
        fail("EnsureDecayFaceArmorBanks must GetLinesFromFile armor ids")
    if "FaceStageMapReady" not in ensure:
        fail("EnsureDecayFaceArmorBanks must cache when FaceStageMapReady (no per-apply reload race)")
    if "ReloadDecayFaceStageMap" not in ensure:
        fail("EnsureDecayFaceArmorBanks must ReloadDecayFaceStageMap when cache cold")
    if "Debug.Notification" not in ensure or "Debug.Trace" not in ensure:
        fail("EnsureDecayFaceArmorBanks must fail loud")
    reload_map = extract_function(decay, "ReloadDecayFaceStageMap")
    if 'label == "none"' not in reload_map:
        fail("ReloadDecayFaceStageMap must accept face label none")
    if "GetLinesFromFile(FACE_STAGE_FILE" not in reload_map:
        fail("ReloadDecayFaceStageMap must GetLinesFromFile stage map")
    if "nextFids" not in reload_map:
        fail("ReloadDecayFaceStageMap must build temp nextFids then commit (no live wipe race)")
    if "InvalidateDecayFaceArmorBanks" not in decay:
        fail("CorpseDecay must InvalidateDecayFaceArmorBanks for ModConfig hot-reload")
    main = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    load_mod = extract_function(main, "LoadModConfig")
    if "InvalidateDecayFaceArmorBanks" not in load_mod:
        fail("LoadModConfig must InvalidateDecayFaceArmorBanks after reload")

    strip = extract_function(decay, "StripDecayFaceArmors")
    if "UnequipItem" not in strip or "RemoveItem" not in strip:
        fail("StripDecayFaceArmors must UnequipItem + RemoveItem all DecayFace ARMOs")
    if "EnsureDecayFaceArmorBanks" not in strip:
        fail("StripDecayFaceArmors must EnsureDecayFaceArmorBanks when bank empty")

    apply_face = extract_function(decay, "ApplyDecayFaceArmorForStage")
    if "StripDecayFaceArmors" not in apply_face:
        fail("ApplyDecayFaceArmorForStage must StripDecayFaceArmors for none / before equip")
    if "face cleanup" not in apply_face and "stripped" not in apply_face.lower():
        fail("ApplyDecayFaceArmorForStage none must cleanup/strip DecayFace masks")
    if "EquipItem(armor, False, True)" not in apply_face:
        fail("ApplyDecayFaceArmorForStage must EquipItem(..., False, True) — removable")
    if "EquipItem(armor, True" in apply_face:
        fail("face ARMO must stay playable/removable (no abPreventRemoval=true)")
    if "GetItemCount(armor)" not in apply_face:
        fail("ApplyDecayFaceArmorForStage must GetItemCount (dead IsEquipped is unreliable)")
    if "Return False" in apply_face and "IsEquipped(armor)" in apply_face:
        # Must not abort stage solely because IsEquipped is false on corpses.
        if re.search(
            r"If !akCorpse\.IsEquipped\(armor\).*Return False",
            apply_face,
            re.S,
        ):
            fail("ApplyDecayFaceArmorForStage must not Return False solely on !IsEquipped")
    ok("ApplyDecayFaceArmorForStage none + removable EquipItem")

    stage_apply = extract_function(decay, "ApplyDecayStageOverlays")
    if "ApplyDecayFaceArmorForStage" not in stage_apply:
        fail("ApplyDecayStageOverlays must ApplyDecayFaceArmorForStage")
    ok("ApplyDecayStageOverlays wires face stage equip")

    for path in (PS1, SH):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "test_decay_face_stage_equip.py" not in text:
            fail(f"{path.name} must run test_decay_face_stage_equip.py")
    ok("deploy gate includes face stage equip contract")

    print("All decay face stage equip contracts passed.")


if __name__ == "__main__":
    main()
