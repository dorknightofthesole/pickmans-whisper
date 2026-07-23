#!/usr/bin/env python3
"""Contracts for Slice H P2 ModConfig decayStage0..4 parse + hour thresholds.

Proves the shipped ModConfig strings parse to name/RGBA/startHours/skins/scars the
same way Papyrus SplitByChar + ParseDecayStageValue do, and that stage resolve
from elapsed hours matches ResolveDecayStageFromElapsedHours.

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
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"

# Locked start-hour thresholds (game hours after kill).
SHIPPED_START_HOURS = (0.0, 0.25, 2.0, 48.0, 240.0)


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
    """Mirror ParseDecayStageValue: name;r;g;b;a;startHours;skins[+…];scars?"""
    fields = split_by_char(val, ";")
    if len(fields) < 7:
        raise ValueError(f"need name;r;g;b;a;startHours;skins — got {len(fields)} fields: {val!r}")
    name = fields[0]
    skins = fields[6]
    if not name or not skins:
        raise ValueError(f"empty name or skins: {val!r}")
    start_h = float(fields[5])
    if start_h < 0.0:
        raise ValueError(f"startHours must be >= 0: {val!r}")
    scars = len(fields) >= 8 and fields[7] == "scars"
    if skins == "none":
        if scars:
            raise ValueError(f"skins=none cannot use scars: {val!r}")
        skin_list: list[str] = []
    else:
        skin_list = [p for p in split_by_char(skins, "+") if p]
    return {
        "name": name,
        "r": float(fields[1]),
        "g": float(fields[2]),
        "b": float(fields[3]),
        "a": float(fields[4]),
        "start_hours": start_h,
        "skins": skin_list,
        "skins_raw": skins,
        "scars": scars,
    }


def resolve_decay_stage(elapsed_hours: float, starts: list[float] | tuple[float, ...]) -> int:
    """Mirror ResolveDecayStageFromElapsedHours — highest i with elapsed >= starts[i]."""
    elapsed = max(0.0, float(elapsed_hours))
    stage = 0
    for i, start in enumerate(starts):
        if elapsed >= start:
            stage = i
    return stage


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
        0: ("Freshly Deceased", 0.650, 0.520, 0.480, 1.0, 0.0, [], False),
        1: ("Pallor Mortis", 0.300, 0.750, 0.720, 1.0, 0.25, [], False),
        2: ("Livor Mortis", 0.480, 0.140, 0.300, 1.0, 2.0, ["SkinTexture_15", "SkinTexture_09"], False),
        3: (
            "Putrefaction",
            0.369,
            0.451,
            0.318,
            1.0,
            48.0,
            ["SkinTexture_17", "SkinTexture_18"],
            True,
        ),
        4: (
            "Black Putrefaction",
            0.149,
            0.118,
            0.102,
            1.0,
            240.0,
            ["SkinTexture_03", "SkinTexture_18"],
            True,
        ),
    }
    for idx, (name, r, g, b, a, start_h, skins, scars) in expected.items():
        got = stages[idx]
        if got["name"] != name:
            fail(f"stage {idx} name: {got['name']!r} != {name!r}")
        for label, want, have in (
            ("r", r, got["r"]),
            ("g", g, got["g"]),
            ("b", b, got["b"]),
            ("a", a, got["a"]),
            ("start_hours", start_h, got["start_hours"]),
        ):
            if abs(want - have) > 1e-6:
                fail(f"stage {idx} {label}: {have} != {want}")
        if got["skins"] != skins:
            fail(f"stage {idx} skins: {got['skins']} != {skins}")
        if got["scars"] != scars:
            fail(f"stage {idx} scars: {got['scars']} != {scars}")
    if stages[0]["skins_raw"] != "none" or stages[1]["skins_raw"] != "none":
        fail("stages 0–1 must use skins=none (no body change)")
    if stages[2]["skins"] != ["SkinTexture_15", "SkinTexture_09"]:
        fail("stage 2 Livor must use SkinTexture_15+SkinTexture_09 (visible vs Pallor none)")
    starts = [stages[i]["start_hours"] for i in range(5)]
    if starts != list(SHIPPED_START_HOURS):
        fail(f"startHours {starts} != locked {list(SHIPPED_START_HOURS)}")
    for i in range(1, 5):
        if starts[i] < starts[i - 1]:
            fail(f"startHours not nondecreasing at {i}: {starts}")
    ok("parse shipped ModConfig decayStage0..4 (name/RGBA/startHours/skins/scars)")


def test_resolve_decay_stage() -> None:
    starts = SHIPPED_START_HOURS
    cases = (
        (0.0, 0),
        (0.24, 0),
        (0.25, 1),
        (1.9, 1),
        (2.0, 2),
        (47.9, 2),  # gap before Putrefaction stays Livor
        (48.0, 3),
        (239.9, 3),
        (240.0, 4),
        (9999.0, 4),  # Black forever
    )
    for elapsed, want in cases:
        got = resolve_decay_stage(elapsed, starts)
        if got != want:
            fail(f"resolve({elapsed}) = {got}, want {want}")
    ok("resolve_decay_stage thresholds (gaps keep prior; Black forever)")


def test_parse_edge_cases() -> None:
    p = parse_decay_stage_value(
        "  Freshly Deceased ; 0.650 ; 0.520 ; 0.480 ; 1.0 ; 0 ; none "
    )
    if (
        p["name"] != "Freshly Deceased"
        or p["a"] != 1.0
        or p["start_hours"] != 0.0
        or p["skins"] != []
        or p["skins_raw"] != "none"
    ):
        fail(f"skins=none parse failed: {p}")
    p2 = parse_decay_stage_value(
        "Putrefaction;0.369;0.451;0.318;0.75;48;SkinTexture_17+SkinTexture_18;scars"
    )
    if (
        p2["a"] != 0.75
        or p2["start_hours"] != 48.0
        or p2["skins"] != ["SkinTexture_17", "SkinTexture_18"]
        or not p2["scars"]
    ):
        fail(f"alpha+hours+scars+layers parse failed: {p2}")
    try:
        parse_decay_stage_value("Freshly Deceased;0.650;0.520;0.480;1.0;SkinTexture_07")
        fail("old 6-field (no startHours) line must fail")
    except ValueError:
        pass
    try:
        parse_decay_stage_value("Freshly Deceased;0.650;0.520;0.480;1.0;0;none;scars")
        fail("skins=none + scars must fail")
    except ValueError:
        pass
    ok("parse edge cases (none body, startHours, +skins, scars; reject missing hours)")


def test_papyrus_wiring() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    parse = extract_function(main, "ParseDecayStageValue")
    if "n < 7" not in parse and "n<7" not in parse.replace(" ", ""):
        fail("ParseDecayStageValue must require >= 7 fields (name;r;g;b;a;startHours;skins)")
    if "fields[5]" not in parse or "fields[6]" not in parse:
        fail("ParseDecayStageValue must read startHours=fields[5] skins=fields[6]")
    if 'skins == "none"' not in parse and "skins == \"none\"" not in parse:
        fail("ParseDecayStageValue must accept skins=none")
    if "DecayStageStartHours" not in parse:
        fail("ParseDecayStageValue must store DecayStageStartHours")
    fill = extract_function(main, "FillDecayStageSkins")
    if 'raw == "none"' not in fill:
        fail("FillDecayStageSkins must treat skins=none as empty body bank")
    if "GetDecayStageStartHours" not in main:
        fail("Main must expose GetDecayStageStartHours")
    if "ResolveDecayStageFromElapsedHours" not in main:
        fail("Main must ResolveDecayStageFromElapsedHours")
    if "DecayStageHoursOrdered" not in main:
        fail("Main must DecayStageHoursOrdered for load gate")
    lab = LAB.read_text(encoding="utf-8", errors="replace")
    apply = extract_function(lab, "DebugApplyDecayStageLab")
    if "ApplyDecayStageOverlays" not in apply:
        fail("DebugApplyDecayStageLab must ApplyDecayStageOverlays (shared bed/lab path)")
    decay = DECAY.read_text(encoding="utf-8", errors="replace")
    stage_apply = extract_function(decay, "ApplyDecayStageOverlays")
    if "body default (skins=none)" not in stage_apply:
        fail("ApplyDecayStageOverlays must clear body and succeed when skins=none")
    if "ClearSkinBankOverlays" not in stage_apply:
        fail("ApplyDecayStageOverlays must ClearSkinBankOverlays before apply/none")
    bed_apply = extract_function(decay, "ApplyBedGiftDecayOverlays")
    if "ApplyDecayStageOverlays" not in bed_apply:
        fail("ApplyBedGiftDecayOverlays must call ApplyDecayStageOverlays")
    if "GetBedGiftWoundAlpha" not in bed_apply:
        fail("ApplyBedGiftDecayOverlays must use bedGiftWoundAlpha for wound opacity")
    ok("Papyrus parse + startHours + shared stage apply")


def main() -> int:
    if not MOD_CONFIG.is_file():
        fail(f"missing {MOD_CONFIG}")
    test_parse_shipped_modconfig()
    test_resolve_decay_stage()
    test_parse_edge_cases()
    test_papyrus_wiring()
    print("All decay-stage ModConfig parse contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
