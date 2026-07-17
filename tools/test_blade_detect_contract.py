#!/usr/bin/env python3
"""Regression contract for Pickman's Blade detection (B27+).

Locks the Fallout4.esm FormIDs / CustomItem mod pair that live GoE scanning depends on,
and asserts the quest script still references those constants.

Usage:
  python tools/test_blade_detect_contract.py
  python tools/test_blade_detect_contract.py --esm "<path>/Fallout4.esm"

Exit 0 = pass. Requires Fallout4.esm (via --esm, FALLOUT4_ESM env, or .env).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"

# Contract — must match live detection in PickmansWhisperMainQuestScript.psc
FID_LVLI_TEMPLATE = 0x0022595F
FID_FLST_MODS = 0x00225960
FID_COMBAT_KNIFE = 0x000913CA
FID_OMOD_BLEED = 0x001E7C20
FID_OMOD_STEALTH = 0x00187A10
EDID_LVLI = b"CustomItem_DoNotPlaceDirectly_DN101PickmansBlade"
EDID_FLST = b"CustomItemMods_DN101PickmansBlade"
EDID_KNIFE = b"Knife"
EDID_BLEED = b"mod_Legendary_Weapon_Bleed"
EDID_STEALTH = b"mod_melee_Knife_SerratedStealth"
NAME_NEEDLE = "Pickman's Blade"


def find_esm(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    load_dotenv()
    env = __import__("os").environ.get("FALLOUT4_ESM")
    if env and Path(env).is_file():
        return Path(env)
    return None


def parse_psc_fids(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for name, val in re.findall(
        r"Int\s+(FID_\w+)\s*=\s*(0x[0-9A-Fa-f]+)", text
    ):
        out[name] = int(val, 16)
    return out


def get_record(data: bytes, fid: int) -> tuple[bytes, bytes, bytes] | None:
    """Return (tag, edid, record_body) for FormID or None."""
    target = fid.to_bytes(4, "little")
    for tag in (b"WEAP", b"OMOD", b"LVLI", b"FLST", b"KYWD"):
        start = 0
        while True:
            i = data.find(tag, start)
            if i < 0 or i + 16 > len(data):
                break
            if data[i + 12 : i + 16] == target:
                sz = int.from_bytes(data[i + 4 : i + 8], "little")
                body = data[i + 24 : i + 24 + sz]
                edid = b""
                j = body.find(b"EDID")
                if j >= 0 and j + 6 <= len(body):
                    esz = int.from_bytes(body[j + 4 : j + 6], "little")
                    edid = body[j + 6 : j + 6 + esz].split(b"\x00")[0]
                return tag, edid, body
            start = i + 4
    return None


def flst_members(body: bytes) -> list[int]:
    members: list[int] = []
    p = 0
    while p + 6 <= len(body):
        tag = body[p : p + 4]
        fsz = int.from_bytes(body[p + 4 : p + 6], "little")
        payload = body[p + 6 : p + 6 + fsz]
        if tag == b"LNAM" and len(payload) >= 4:
            members.append(int.from_bytes(payload[:4], "little"))
        p += 6 + fsz
    return members


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--esm", default=None, help="Path to Fallout4.esm")
    args = ap.parse_args()
    errors: list[str] = []

    if not PSC.is_file():
        print(f"FAIL: missing {PSC}")
        return 1

    text = PSC.read_text(encoding="utf-8", errors="replace")
    fids = parse_psc_fids(text)

    expected = {
        "FID_PICKMANS_BLADE": FID_LVLI_TEMPLATE,
        "FID_COMBAT_KNIFE": FID_COMBAT_KNIFE,
        "FID_OMOD_BLEED": FID_OMOD_BLEED,
        "FID_OMOD_STEALTH": FID_OMOD_STEALTH,
    }
    for key, want in expected.items():
        got = fids.get(key)
        if got != want:
            errors.append(f"PSC {key}: expected 0x{want:08X}, got {got!r}")

    if f'BLADE_NAME_NEEDLE = "{NAME_NEEDLE}"' not in text and f"BLADE_NAME_NEEDLE = '{NAME_NEEDLE}'" not in text:
        if NAME_NEEDLE not in text:
            errors.append(f"PSC missing name needle {NAME_NEEDLE!r}")

    for fn in (
        "FindEquippedPickmansBladeIndex",
        "InventorySlotIsPickmansBlade",
        "GetNthItemHasMod",
        "GetItemIndexesByName",
    ):
        if fn not in text:
            errors.append(f"PSC missing detection symbol {fn!r}")

    esm = find_esm(args.esm)
    if not esm:
        print("SKIP ESM checks: Fallout4.esm not found (set FALLOUT4_ESM in .env, env, or --esm)")
    else:
        print(f"ESM: {esm}")
        data = esm.read_bytes()

        checks = [
            (FID_LVLI_TEMPLATE, b"LVLI", EDID_LVLI),
            (FID_FLST_MODS, b"FLST", EDID_FLST),
            (FID_COMBAT_KNIFE, b"WEAP", EDID_KNIFE),
            (FID_OMOD_BLEED, b"OMOD", EDID_BLEED),
            (FID_OMOD_STEALTH, b"OMOD", EDID_STEALTH),
        ]
        for fid, tag, edid in checks:
            rec = get_record(data, fid)
            if not rec:
                errors.append(f"ESM 0x{fid:08X}: record not found")
                continue
            got_tag, got_edid, body = rec
            if got_tag != tag:
                errors.append(f"ESM 0x{fid:08X}: expected {tag.decode()}, got {got_tag.decode()}")
            if got_edid != edid:
                errors.append(
                    f"ESM 0x{fid:08X}: expected EDID {edid!r}, got {got_edid!r}"
                )
            if fid == FID_FLST_MODS:
                members = flst_members(body)
                for need in (FID_OMOD_BLEED, FID_OMOD_STEALTH):
                    if need not in members:
                        errors.append(
                            f"ESM FLST CustomItemMods missing 0x{need:08X} (have {[hex(m) for m in members]})"
                        )

        # Hard rule: template is NOT a weapon — GetEquippedWeapon must not be compared to it alone
        rec = get_record(data, FID_LVLI_TEMPLATE)
        if rec and rec[0] == b"WEAP":
            errors.append("0x22595F unexpectedly WEAP — detection assumptions broken")

    if errors:
        print("FAIL blade detect contract:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("PASS blade detect contract")
    print(f"  Knife WEAP 0x{FID_COMBAT_KNIFE:08X} + bleed 0x{FID_OMOD_BLEED:08X} + stealth 0x{FID_OMOD_STEALTH:08X}")
    print(f"  Name needle {NAME_NEEDLE!r}; LVLI template 0x{FID_LVLI_TEMPLATE:08X} is not the drawn form")
    return 0


if __name__ == "__main__":
    sys.exit(main())
