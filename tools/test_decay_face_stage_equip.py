#!/usr/bin/env python3
"""Slice I — stage→face ARMO map + corpse EquipItem path.

Locks:
  - DecayFaceStages.txt 0=Base 1=Gray 2=Red 3=Green 4=Black
  - CorpseDecay loads DecayFaceArmorIds.txt + DecayFaceStages.txt
  - ApplyDecayStageOverlays equips via ApplyDecayFaceArmorForStage
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
    0: "Base",
    1: "Gray",
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
    ok("DecayFaceStages.txt 0=Base 1=Gray 2=Red 3=Green 4=Black")

    if not IDS.is_file():
        fail("DecayFaceArmorIds.txt missing — rebuild ESP")
    id_text = IDS.read_text(encoding="utf-8")
    for label in EXPECTED.values():
        if not re.search(rf"(?m)^{re.escape(label)}=\d+,\d+\s*$", id_text):
            fail(f"DecayFaceArmorIds.txt missing ARMO for label {label}")
    ok("DecayFaceArmorIds.txt covers all stage labels")

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
    if "FACE_ARMOR_IDS_FILE" not in ensure or "FACE_STAGE_FILE" not in ensure:
        fail("EnsureDecayFaceArmorBanks must load FACE_ARMOR_IDS_FILE + FACE_STAGE_FILE")
    if "GetLinesFromFile(FACE_ARMOR_IDS_FILE" not in ensure:
        fail("EnsureDecayFaceArmorBanks must GetLinesFromFile armor ids")
    if "GetLinesFromFile(FACE_STAGE_FILE" not in ensure:
        fail("EnsureDecayFaceArmorBanks must GetLinesFromFile stage map")
    if "Debug.Notification" not in ensure or "Debug.Trace" not in ensure:
        fail("EnsureDecayFaceArmorBanks must fail loud")

    apply_face = extract_function(decay, "ApplyDecayFaceArmorForStage")
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
            fail("ApplyDecayFaceArmorForStage must not Return False on IsEquipped=0 alone")
    if "GetFormFromFile" not in apply_face:
        fail("ApplyDecayFaceArmorForStage must GetFormFromFile ARMO")

    stage_fn = extract_function(decay, "ApplyDecayStageOverlays")
    if "If !ApplyDecayFaceArmorForStage(akCorpse, aiStage)" not in stage_fn:
        fail("ApplyDecayStageOverlays must abort when ApplyDecayFaceArmorForStage fails")
    ok("CorpseDecay stage->face ARMO equip path")

    ps1 = PS1.read_text(encoding="utf-8", errors="replace")
    if "test_decay_face_stage_equip.py" not in ps1:
        fail("build-deploy-local.ps1 must run test_decay_face_stage_equip.py")
    sh = SH.read_text(encoding="utf-8", errors="replace")
    if "test_decay_face_stage_equip.py" not in sh:
        fail("build-deploy-local.sh must run test_decay_face_stage_equip.py")
    ok("deploy gate includes face-stage equip contract")
    print("All decay-face-stage-equip contracts passed.")


if __name__ == "__main__":
    main()
