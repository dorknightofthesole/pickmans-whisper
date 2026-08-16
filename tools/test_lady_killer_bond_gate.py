#!/usr/bin/env python3
"""Contract: Slice N — Bond requires the Lady Killer perk, in addition to the blade.

Bond means the player has BOTH Pickman's Blade (Slice R rule) AND the Lady Killer perk
(Slice N). StartBond is still the single choke point (RunBondPoll, MarkOwnedBlade,
PlayerAlias's blade-equipped path, the MCM debug force-bond button all funnel through it).
The Lady Killer half is a LIVE check, not a one-time snapshot at blade-acquire time:
RunBondPoll already re-calls StartBond("trigger") every ~4s real-time whenever
!BondStarted, so acquiring Lady Killer later (even long after the blade) unlocks Bond on
the next poll tick with no new polling infrastructure. BondStarted itself stays a true
one-way latch, unchanged.

FormIDs (LadyKiller01/02/03) verified directly against Fallout4.esm PERK records — not
guessed — same mechanism as the existing Cannibal01/02/03 verification
(tools/test_decay_eat_ripe_toast.py).

Usage:
  python tools/test_lady_killer_bond_gate.py [--esm PATH]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

FID_LADYKILLER = {
    0x00019AA3: b"LadyKiller01",
    0x00065E33: b"LadyKiller02",
    0x00065E34: b"LadyKiller03",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(src: str, name: str) -> str:
    m = re.search(
        rf"(?:^\s*(?:Bool|Int|Float|String)?\s*)?Function\s+{re.escape(name)}\s*\(",
        src,
        re.M,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", src[start:])
    if not end_m:
        fail(f"unclosed function {name}")
    return src[start : start + end_m.end()]


def strip_comment_lines(fn: str) -> str:
    return "\n".join(ln for ln in fn.splitlines() if not ln.strip().startswith(";"))


def get_record_edid_zlib(data: bytes, sig: bytes, fid: int) -> bytes | None:
    target = fid.to_bytes(4, "little")
    start = 0
    while True:
        i = data.find(sig, start)
        if i < 0 or i + 24 > len(data):
            return None
        if data[i + 12 : i + 16] != target:
            start = i + 4
            continue
        size = int.from_bytes(data[i + 4 : i + 8], "little")
        flags = int.from_bytes(data[i + 8 : i + 12], "little")
        payload = data[i + 24 : i + 24 + size]
        if flags & 0x00040000:
            try:
                payload = zlib.decompress(payload[4:])
            except Exception:
                return None
        k = payload.find(b"EDID")
        if k < 0 or k + 6 > len(payload):
            return None
        esz = int.from_bytes(payload[k + 4 : k + 6], "little")
        return payload[k + 6 : k + 6 + esz].split(b"\x00", 1)[0]


def test_esm(esm: Path | None) -> None:
    if not esm or not esm.is_file():
        print("SKIP ESM checks: Fallout4.esm not found (set FALLOUT4_ESM in .env, env, or --esm)")
        return
    data = esm.read_bytes()
    for fid, edid in FID_LADYKILLER.items():
        got = get_record_edid_zlib(data, b"PERK", fid)
        if got != edid:
            fail(f"FID 0x{fid:06X} EDID {got!r} != {edid!r}")
    ok("LadyKiller01/02/03 FormIDs verified against Fallout4.esm PERK records")


def test_formid_constants(text: str) -> None:
    for fid, edid in FID_LADYKILLER.items():
        needle = f"0x{fid:08X} ; {edid.decode()}"
        if needle not in text:
            fail(f"MainQuestScript must declare a FID const for {edid.decode()} = {needle!r}")
    ok("FID_PERK_LADYKILLER_1/2/3 constants declared with EDID comments")


def test_resolve_and_check_function(text: str) -> None:
    resolve = extract_function(text, "ResolveVanillaForms")
    for var in ("LadyKillerPerk1", "LadyKillerPerk2", "LadyKillerPerk3"):
        if var not in resolve:
            fail(f"ResolveVanillaForms must resolve {var}")

    check = extract_function(text, "PlayerHasLadyKillerPerk")
    if check.count("HasPerk") < 3:
        fail("PlayerHasLadyKillerPerk must check all 3 ranks (additive PERK records, same as PlayerHasCannibalPerk)")
    ok("PlayerHasLadyKillerPerk resolves + checks all 3 ranks")


def test_start_bond_gate(text: str) -> None:
    bond = extract_function(text, "StartBond")
    bond_code_only = strip_comment_lines(bond)
    if "PlayerHasBlade()" not in bond_code_only:
        fail("StartBond must still gate on PlayerHasBlade() (Slice R rule, unchanged)")
    if "PlayerHasLadyKillerPerk()" not in bond_code_only:
        fail("StartBond must gate on PlayerHasLadyKillerPerk() (Slice N rule)")
    # Order matters for the Trace-reason semantics but not for correctness; just confirm
    # both guards run before BondStarted = True.
    idx_blade = bond_code_only.find("PlayerHasBlade()")
    idx_perk = bond_code_only.find("PlayerHasLadyKillerPerk()")
    idx_started = bond_code_only.find("BondStarted = True")
    if idx_started < 0 or idx_started < idx_blade or idx_started < idx_perk:
        fail("StartBond must check both PlayerHasBlade() and PlayerHasLadyKillerPerk() before BondStarted = True")
    ok("StartBond gates on PlayerHasBlade() AND PlayerHasLadyKillerPerk() before latching")


def test_debug_force_bond_reports_accurately(text: str) -> None:
    force = extract_function(text, "DebugForceBond")
    if "PlayerHasLadyKillerPerk()" not in force:
        fail("DebugForceBond must check PlayerHasLadyKillerPerk() itself and report an accurate "
             "blocked message — otherwise it always claims 'Bond forced' even when StartBond silently refused")
    ok("DebugForceBond reports an accurate Lady-Killer-missing message")


def test_mcm_status_text(text: str) -> None:
    panel = extract_function(text, "RefreshHungerPanel")
    if "PlayerHasLadyKillerPerk()" not in panel:
        fail("RefreshHungerPanel must distinguish 'blade but no Lady Killer' from 'no blade yet' in the locked status text")
    if "needs Lady Killer perk" not in panel:
        fail("RefreshHungerPanel must surface a 'needs Lady Killer perk' status string")
    ok("RefreshHungerPanel surfaces a distinct locked-status message when the perk is the only thing missing")


def test_run_bond_poll_covers_late_acquire(text: str) -> None:
    poll = extract_function(text, "RunBondPoll")
    poll_code_only = strip_comment_lines(poll)
    if "StartBond(" not in poll_code_only:
        fail("RunBondPoll must keep re-calling StartBond every poll (this is what makes late Lady Killer acquisition unlock Bond without new polling infrastructure)")
    ok("RunBondPoll keeps re-attempting StartBond every tick — late Lady Killer acquire unlocks Bond on the next poll")


def main() -> int:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")

    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--esm", default=None)
    args, _ = ap.parse_known_args()
    esm_path = args.esm or os.environ.get("FALLOUT4_ESM")
    test_esm(Path(esm_path) if esm_path else None)

    test_formid_constants(text)
    test_resolve_and_check_function(text)
    test_start_bond_gate(text)
    test_debug_force_bond_reports_accurately(text)
    test_mcm_status_text(text)
    test_run_bond_poll_covers_late_acquire(text)
    print("All Lady Killer bond-gate (Slice N) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
