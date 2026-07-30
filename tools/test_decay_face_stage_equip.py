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


def parse_positive_int_mirror(s: str) -> int:
    """Mirror Main.ParsePositiveInt — digits prefix; trailing junk ignored."""
    if not s:
        return -1
    n = 0
    got = False
    for c in s:
        if c.isdigit():
            got = True
            n = n * 10 + int(c)
        elif got:
            return n
        else:
            return -1
    return n if got else -1


def config_label_key_mirror(s: str) -> str:
    """Mirror CorpseDecay.ConfigLabelKey — letters only, lower."""
    return "".join(c.lower() for c in s if c.isalpha())


def main() -> None:
    if parse_positive_int_mirror("2135\r") != 2135:
        fail("ParsePositiveInt mirror must accept trailing CR (CRLF face ids)")
    if parse_positive_int_mirror("2137") != 2137:
        fail("ParsePositiveInt mirror clean int")
    if config_label_key_mirror("Green\r") != "green":
        fail("ConfigLabelKey mirror must drop CR on Green")
    if config_label_key_mirror("none") != "none":
        fail("ConfigLabelKey mirror must keep none")
    ok("CRLF-safe face id / label parse mirrors")

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
    if "ConfigTrim" not in ensure or "ConfigLowerAscii" not in ensure:
        fail("EnsureDecayFaceArmorBanks must ConfigTrim + ConfigLowerAscii (not TrimString/GetWords)")
    if "m.TrimString" in ensure:
        fail("EnsureDecayFaceArmorBanks must not TrimString face id lines (GetWords mangles key=value)")
    if "FaceArmorLabelsDebugList" not in ensure:
        fail("EnsureDecayFaceArmorBanks must Trace loaded labels")
    if "ConfigLabelKey" not in decay:
        fail("CorpseDecay must ConfigLabelKey (letters-only — drops CRLF \\r on face labels)")
    label_key = extract_function(decay, "ConfigLabelKey")
    if 'c == "A"' not in label_key or 'c == "a"' not in label_key:
        fail("ConfigLabelKey must accept upper and lower letters only")
    lower = extract_function(decay, "ConfigLowerAscii")
    if "ConfigLabelKey" not in lower:
        fail("ConfigLowerAscii must route through ConfigLabelKey")
    reload_map = extract_function(decay, "ReloadDecayFaceStageMap")
    if 'label == "none"' not in reload_map:
        fail("ReloadDecayFaceStageMap must accept face label none")
    if "GetLinesFromFile(FACE_STAGE_FILE" not in reload_map:
        fail("ReloadDecayFaceStageMap must GetLinesFromFile stage map")
    if "nextFids" not in reload_map:
        fail("ReloadDecayFaceStageMap must build temp nextFids then commit (no live wipe race)")
    if "ConfigTrim" not in reload_map or "ConfigLowerAscii" not in reload_map:
        fail("ReloadDecayFaceStageMap must ConfigTrim + ConfigLowerAscii labels")
    if "m.TrimString" in reload_map:
        fail("ReloadDecayFaceStageMap must not TrimString stage lines")
    if "known=[" not in reload_map:
        fail("ReloadDecayFaceStageMap UNKNOWN label must dump known= labels")
    find_label = extract_function(decay, "FindFaceArmorLabelIndex")
    if "ConfigLowerAscii" not in find_label:
        fail("FindFaceArmorLabelIndex must case-fold labels")
    if "InvalidateDecayFaceArmorBanks" not in decay:
        fail("CorpseDecay must InvalidateDecayFaceArmorBanks for ModConfig hot-reload")
    modcfg = (
        ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
    ).read_text(encoding="utf-8", errors="replace")
    load_mod = extract_function(modcfg, "LoadModConfig")
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
    if "QueueUpdate(True" not in apply_face:
        fail("ApplyDecayFaceArmorForStage must QueueUpdate after EquipItem (corpse inventory-only bug)")
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
    if "face FAILED" not in stage_apply and "face failed after body" not in stage_apply:
        fail("ApplyDecayStageOverlays must keep body success when face ARMO fails (tint must stamp)")
    if "Return False" in stage_apply:
        # Face-only failure must not Return False after bodyOk
        face_fail_blocks_body = re.search(
            r"If !ApplyDecayFaceArmorForStage\([^\)]*\)\s*\n\s*Return False",
            stage_apply,
        )
        if face_fail_blocks_body:
            fail("ApplyDecayStageOverlays must not Return False solely on face failure after body apply")
    ok("ApplyDecayStageOverlays wires face stage equip")

    for path in (PS1, SH):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "test_decay_face_stage_equip.py" not in text:
            fail(f"{path.name} must run test_decay_face_stage_equip.py")
    ok("deploy gate includes face stage equip contract")

    print("All decay face stage equip contracts passed.")


if __name__ == "__main__":
    main()
