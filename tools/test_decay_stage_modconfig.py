#!/usr/bin/env python3
"""Contracts for Slice H P2 ModConfig decayStage0..4 parse.

Proves the shipped ModConfig strings parse to name/RGBA/skins/scars the same way
Papyrus SplitByChar + ParseDecayStageValue do (semicolon fields; + layered skins).

Usage:
  python tools/test_decay_stage_modconfig.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_CONFIG = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
LAB = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperDecayWoundLabScript.psc"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(src: str, name: str) -> str:
    m = re.search(rf"(?:Bool |Float |Int |String )?Function {re.escape(name)}\(", src)
    if not m:
        fail(f"missing Function {name}")
    start = m.start()
    end = src.find("\nEndFunction", start)
    if end < 0:
        fail(f"unclosed Function {name}")
    return src[start : end + len("\nEndFunction")]


def split_by_char(s: str, sep: str) -> list[str]:
    """Mirror Papyrus SplitByChar (single-char sep, trim fields)."""
    if len(sep) != 1:
        fail("split_by_char sep must be one char")
    if s is None:
        return []
    out: list[str] = []
    start = 0
    length = len(s)
    i = 0
    while i <= length:
        at_end = i == length
        is_sep = (not at_end) and s[i] == sep
        if at_end or is_sep:
            out.append(s[start:i].strip())
            start = i + 1
        i += 1
    return out


def parse_decay_stage_value(val: str) -> dict:
    """Mirror ParseDecayStageValue: name;r;g;b;a;skins[+…];scars?"""
    fields = split_by_char(val, ";")
    if len(fields) < 6:
        raise ValueError(f"need name;r;g;b;a;skins — got {len(fields)} fields: {val!r}")
    name = fields[0]
    skins = fields[5]
    if not name or not skins:
        raise ValueError(f"empty name or skins: {val!r}")
    scars = len(fields) >= 7 and fields[6] == "scars"
    skin_list = [p for p in split_by_char(skins, "+") if p]
    return {
        "name": name,
        "r": float(fields[1]),
        "g": float(fields[2]),
        "b": float(fields[3]),
        "a": float(fields[4]),
        "skins": skin_list,
        "skins_raw": skins,
        "scars": scars,
    }


def load_modconfig_decay_stages() -> dict[int, dict]:
    text = MOD_CONFIG.read_text(encoding="utf-8")
    stages: dict[int, dict] = {}
    for line in text.splitlines():
        t = line.strip()
        if not t or t.startswith("#") or "=" not in t:
            continue
        key, val = t.split("=", 1)
        key = key.strip()
        m = re.fullmatch(r"decayStage([0-4])", key)
        if not m:
            continue
        idx = int(m.group(1))
        stages[idx] = parse_decay_stage_value(val.strip())
    return stages


def test_parse_shipped_modconfig() -> None:
    stages = load_modconfig_decay_stages()
    if set(stages.keys()) != {0, 1, 2, 3, 4}:
        fail(f"expected decayStage0..4, got {sorted(stages.keys())}")

    expected = {
        0: ("Freshly Deceased", 0.650, 0.520, 0.480, 1.0, ["SkinTexture_07"], False),
        1: ("Pallor Mortis", 0.350, 0.680, 0.650, 1.0, ["SkinTexture_07"], False),
        2: ("Livor Mortis", 0.400, 0.176, 0.267, 1.0, ["SkinTexture_07"], False),
        3: (
            "Putrefaction",
            0.369,
            0.451,
            0.318,
            1.0,
            ["SkinTexture_17", "SkinTexture_18"],
            True,
        ),
        4: (
            "Black Putrefaction",
            0.149,
            0.118,
            0.102,
            1.0,
            ["SkinTexture_03", "SkinTexture_18"],
            True,
        ),
    }
    for idx, (name, r, g, b, a, skins, scars) in expected.items():
        got = stages[idx]
        if got["name"] != name:
            fail(f"stage {idx} name: {got['name']!r} != {name!r}")
        for label, want, have in (
            ("r", r, got["r"]),
            ("g", g, got["g"]),
            ("b", b, got["b"]),
            ("a", a, got["a"]),
        ):
            if abs(want - have) > 1e-6:
                fail(f"stage {idx} {label}: {have} != {want}")
        if got["skins"] != skins:
            fail(f"stage {idx} skins: {got['skins']} != {skins}")
        if got["scars"] != scars:
            fail(f"stage {idx} scars: {got['scars']} != {scars}")
    ok("parse shipped ModConfig decayStage0..4 (name/RGBA/skins/scars)")


def test_parse_edge_cases() -> None:
    # Spaces around fields / layered skins.
    p = parse_decay_stage_value(
        "  Freshly Deceased ; 0.650 ; 0.520 ; 0.480 ; 1.0 ; SkinTexture_07 "
    )
    if p["name"] != "Freshly Deceased" or p["a"] != 1.0 or p["skins"] != ["SkinTexture_07"]:
        fail(f"trim/spaces parse failed: {p}")
    p2 = parse_decay_stage_value(
        "Putrefaction;0.369;0.451;0.318;0.75;SkinTexture_17+SkinTexture_18;scars"
    )
    if p2["a"] != 0.75 or p2["skins"] != ["SkinTexture_17", "SkinTexture_18"] or not p2["scars"]:
        fail(f"alpha+scars+layers parse failed: {p2}")
    try:
        parse_decay_stage_value("Freshly Deceased;0.650;0.520;0.480;SkinTexture_07")
        fail("old 5-field (no alpha) line must fail")
    except ValueError:
        pass
    ok("parse edge cases (trim, alpha, +skins, scars; reject missing alpha)")


def test_papyrus_wiring() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    parse = extract_function(main, "ParseDecayStageValue")
    if "n < 6" not in parse and "n<6" not in parse.replace(" ", ""):
        fail("ParseDecayStageValue must require >= 6 fields (name;r;g;b;a;skins)")
    if "fields[4]" not in parse or "fields[5]" not in parse:
        fail("ParseDecayStageValue must read a=fields[4] skins=fields[5]")
    if "DecayStageTintA" not in parse:
        fail("ParseDecayStageValue must store DecayStageTintA")
    if "GetDecayStageTintA" not in main:
        fail("Main must expose GetDecayStageTintA")
    lab = LAB.read_text(encoding="utf-8", errors="replace")
    apply = extract_function(lab, "DebugApplyDecayStageLab")
    if "GetDecayStageTintA" not in apply:
        fail("DebugApplyDecayStageLab must read GetDecayStageTintA from ModConfig")
    if "ApplyDecayStageOverlays" not in apply:
        fail("DebugApplyDecayStageLab must ApplyDecayStageOverlays (shared bed/lab path)")
    if "tintA = 1.0" in apply or "tintA=1.0" in apply.replace(" ", ""):
        fail("DebugApplyDecayStageLab must not hardcode tintA = 1.0")
    decay = (ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc").read_text(
        encoding="utf-8", errors="replace"
    )
    bed_apply = extract_function(decay, "ApplyBedGiftDecayOverlays")
    if "BED_GIFT_DECAY_STAGE" not in bed_apply and "ApplyDecayStageOverlays" not in bed_apply:
        fail("ApplyBedGiftDecayOverlays must apply a ModConfig decay stage")
    if "ApplyDecayStageOverlays" not in bed_apply:
        fail("ApplyBedGiftDecayOverlays must call ApplyDecayStageOverlays")
    if "GetBedGiftWoundAlpha" not in bed_apply:
        fail("ApplyBedGiftDecayOverlays must use bedGiftWoundAlpha for wound opacity")
    ok("Papyrus parse + Apply stage use ModConfig alpha; bed gift shares stage apply")


def main() -> int:
    if not MOD_CONFIG.is_file():
        fail(f"missing {MOD_CONFIG}")
    test_parse_shipped_modconfig()
    test_parse_edge_cases()
    test_papyrus_wiring()
    print("All decay-stage ModConfig parse contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
