#!/usr/bin/env python3
"""Proximity cloak MGEF/SPEL chain retired — must not be in ESP / builder emit.

Usage:
  python tools/test_proximity_cloak.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
FID_PROXIMITY_HIT_MGEF = 0x01000870
FID_PROXIMITY_HIT_SPEL = 0x01000871
FID_PROXIMITY_CLOAK_MGEF = 0x01000872
FID_PROXIMITY_CLOAK_SPEL = 0x01000873
FID_PLAYER_QUEST = 0x01000805


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def find_record(data: bytes, typ: bytes, fid: int) -> bytes | None:
    i = 0
    while True:
        j = data.find(typ, i)
        if j < 0:
            return None
        if j + 24 <= len(data):
            rec_fid = struct.unpack_from("<I", data, j + 12)[0]
            data_size = struct.unpack_from("<I", data, j + 4)[0]
            if rec_fid == fid and j + 24 + data_size <= len(data):
                return data[j + 24 : j + 24 + data_size]
        i = j + 4


def main() -> None:
    builder = BUILDER.read_text(encoding="utf-8", errors="replace")
    if "def build_proximity_" in builder:
        fail("ESP builder must not define build_proximity_* payload helpers")
    if "PickmansCloakSpell" in builder:
        fail("ESP builder must not reference PickmansCloakSpell")
    if "PickmansWhisperProximityCloak" in builder or "PickmansWhisperProximityHit" in builder:
        fail("ESP builder must not emit proximity cloak/hit EDIDs")
    ok("ESP builder has no proximity cloak emit/bind helpers")

    data = ESP.read_bytes()
    for typ, fid, label in (
        (b"MGEF", FID_PROXIMITY_HIT_MGEF, "Hit MGEF"),
        (b"MGEF", FID_PROXIMITY_CLOAK_MGEF, "Cloak MGEF"),
        (b"SPEL", FID_PROXIMITY_HIT_SPEL, "Hit SPEL"),
        (b"SPEL", FID_PROXIMITY_CLOAK_SPEL, "Cloak SPEL"),
    ):
        if find_record(data, typ, fid):
            fail(f"ESP must not contain retired {label} 0x{fid:08X}")
    for edid in (
        b"PickmansWhisperProximityHitEffect\x00",
        b"PickmansWhisperProximityCloakEffect\x00",
        b"PickmansWhisperProximityHit\x00",
        b"PickmansWhisperProximityCloak\x00",
    ):
        if edid in data:
            fail(f"ESP must not contain cloak EDID {edid[:-1]!r}")
    ok("ESP has no proximity cloak MGEF/SPEL records")

    player_q = find_record(data, b"QUST", FID_PLAYER_QUEST)
    if not player_q:
        fail("PlayerCombat QUST missing")
    if b"PickmansCloakSpell" in player_q:
        fail("PlayerCombat VMAD must not bind PickmansCloakSpell")
    ok("PlayerCombat VMAD has no PickmansCloakSpell bind")

    effect_psc = (
        ROOT
        / "Data"
        / "Scripts"
        / "Source"
        / "User"
        / "PickmansWhisperProximityEffect.psc"
    )
    if effect_psc.is_file():
        fail("PickmansWhisperProximityEffect.psc must be deleted")
    alias = (
        ROOT
        / "Data"
        / "Scripts"
        / "Source"
        / "User"
        / "PickmansWhisperPlayerAliasScript.psc"
    ).read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperProximityEffect" in alias:
        fail("PlayerAlias must not reference PickmansWhisperProximityEffect")
    if "PickmansCloakSpell" in alias or "GrantProximityCloak" in alias:
        fail("PlayerAlias must not reference PickmansCloakSpell / GrantProximityCloak")
    ok("ProximityEffect.psc deleted; PlayerAlias cloak refs removed")

    print("All proximity cloak retirement contracts passed.")


if __name__ == "__main__":
    main()
