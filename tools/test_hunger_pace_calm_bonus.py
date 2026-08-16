"""Contract: Slice L — slow hunger pacing default + Calm-state AGI/CHA bonus.

Pacing: GetHungerTimeGainPerHour's no-MCM fallback and the fTimeGain:Hunger MCM/settings.ini
defaults must all agree on 1.0/hr (~1 day per stage; was 0.5, then 5.0 originally) — the
delta-based RunHungerTick math itself is untouched, this is purely a default-value change.
Bands are unequal width (25/25/20/20 points) so a single rate can't make every stage exactly
24h; 1.0 is the closest clean round number (~25h for Calm/Restless, ~20h for Hungry/Starving).

Calm bonus: SyncCalmBonusSpell mirrors SyncHungerAddictionSpell's exact shape (level-based
recompute-and-diff, ModValue against a live save, depth-capped-at-1 bookkeeping) rather than
a timer — +4.0 AGI/CHA while HungerLevel < 25.0 (Calm) AND CalmBonusEligible, cleared the
moment either isn't true. Wired into the same call sites SyncHungerAddictionSpell already
runs from.

Patience gate (follow-up): the bonus is no longer unconditional on any kill — it's earned
only by a kill/satiation that follows >= CALM_BONUS_PATIENCE_HOURS (13h) of CONTINUOUS
Desperate (HungerLevel >= 90) hunger beforehand. SyncDesperateTracking stamps/clears
DesperateEnteredGameTime live (same recompute-and-diff shape, no edge-detection); dipping
below 90 before satiating resets the clock (no cumulative credit). SatiateHunger reads the
timestamp BEFORE resetting HungerLevel to compute CalmBonusEligible, and satiation itself
(HungerLevel -> 0, sated window, BondIntensity, etc.) remains entirely unconditional
regardless of hunger level or patience — only the bonus is gated.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
SETTINGS_A = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
SETTINGS_B = ROOT / "Data" / "MCM" / "Settings" / "PickmansWhisper.ini"


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


def test_pace_default() -> None:
    psc = PSC.read_text(encoding="utf-8", errors="replace")
    gain = extract_function(psc, "GetHungerTimeGainPerHour")
    if "Float v = 1.0" not in gain:
        fail("GetHungerTimeGainPerHour's no-MCM fallback must default to 1.0 (~1 day/stage; was 0.5, then 5.0)")

    mcm = MCM_CONFIG.read_text(encoding="utf-8", errors="replace")
    if '"id": "fTimeGain:Hunger"' not in mcm:
        fail("config.json missing fTimeGain:Hunger slider")
    idx = mcm.find('"id": "fTimeGain:Hunger"')
    window = mcm[idx : idx + 400]
    if "Default 1.0" not in window:
        fail("fTimeGain:Hunger help text must state the new 1.0 default")

    for path in (SETTINGS_A, SETTINGS_B):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "fTimeGain=1.0" not in text:
            fail(f"{path} must default fTimeGain=1.0")
    ok("hunger pace default 1.0/hr (~1 day per stage) — Papyrus fallback, MCM help text, both settings.ini copies agree")


def test_calm_bonus_properties() -> None:
    psc = PSC.read_text(encoding="utf-8", errors="replace")
    if "Bool Property CalmBonusApplied" not in psc:
        fail("Main must declare CalmBonusApplied property")
    if "Int Property CalmBonusDepth" not in psc:
        fail("Main must declare CalmBonusDepth property (depth-capped bookkeeping, mirrors HungerSpecialPenaltyDepth)")
    ok("CalmBonusApplied/CalmBonusDepth properties declared")


def test_reconcile_apply_clear() -> None:
    psc = PSC.read_text(encoding="utf-8", errors="replace")

    reconcile = extract_function(psc, "ReconcileCalmBonusFlags")
    if "CalmBonusDepth > 1" not in reconcile:
        fail("ReconcileCalmBonusFlags must cap depth at 1")
    if "CalmBonusDepth = 1" not in reconcile:
        fail("ReconcileCalmBonusFlags must reconcile depth from a stale True flag")

    apply_fn = extract_function(psc, "ApplyCalmBonus")
    if "CalmBonusDepth" not in apply_fn or "CalmBonusApplied" not in apply_fn:
        fail("ApplyCalmBonus must honor CalmBonusApplied/CalmBonusDepth")
    if "already applied" not in apply_fn:
        fail("ApplyCalmBonus must skip + Trace when already applied (idempotent, no double ModValue)")
    if apply_fn.count("ModValue") < 2:
        fail("ApplyCalmBonus must ModValue AGI and CHA")
    if "ModValue(avAgi, 4.0)" not in apply_fn or "ModValue(avCha, 4.0)" not in apply_fn:
        fail("ApplyCalmBonus must ModValue exactly +4.0 on AGI and CHA")
    if "CalmBonusDepth = 1" not in apply_fn or "CalmBonusApplied = True" not in apply_fn:
        fail("ApplyCalmBonus must set depth=1 and applied=True after a real apply")

    clear_fn = extract_function(psc, "ClearCalmBonus")
    if "While i < n" not in clear_fn:
        fail("ClearCalmBonus must restore ModValue for depth n (loop, not a flat single call)")
    if "ModValue(avAgi, -4.0)" not in clear_fn or "ModValue(avCha, -4.0)" not in clear_fn:
        fail("ClearCalmBonus must ModValue exactly -4.0 on AGI and CHA")
    if "CalmBonusDepth = 0" not in clear_fn or "CalmBonusApplied = False" not in clear_fn:
        fail("ClearCalmBonus must zero depth and clear applied flag")

    ok("ApplyCalmBonus/ClearCalmBonus: idempotent +4.0/-4.0 AGI+CHA, depth-bookkept")


def test_sync_gate() -> None:
    psc = PSC.read_text(encoding="utf-8", errors="replace")
    sync = extract_function(psc, "SyncCalmBonusSpell")
    if "ReconcileCalmBonusFlags" not in sync:
        fail("SyncCalmBonusSpell must ReconcileCalmBonusFlags before diffing")
    if "IsHungerUnlocked()" not in sync:
        fail("SyncCalmBonusSpell must gate on IsHungerUnlocked() (no bonus before Bond)")
    if "HungerLevel < 25.0" not in sync:
        fail("SyncCalmBonusSpell must gate on HungerLevel < 25.0 (Calm band, same threshold as GetHungerBandLabel/GetNoticeStage)")
    if "CalmBonusEligible" not in sync:
        fail("SyncCalmBonusSpell must gate on CalmBonusEligible (earned via patience, not automatic on every kill)")
    if "ApplyCalmBonus()" not in sync:
        fail("SyncCalmBonusSpell must call ApplyCalmBonus() when entering Calm")
    if "ClearCalmBonus()" not in sync:
        fail("SyncCalmBonusSpell must call ClearCalmBonus() when leaving Calm")
    if "CalmBonusEligible = False" not in sync:
        fail("SyncCalmBonusSpell must reset CalmBonusEligible when clearing — a future satiation must re-earn it")
    ok("SyncCalmBonusSpell: Calm-band gate (<25.0) AND CalmBonusEligible, Bond-gated, apply/clear diffed")


def test_desperate_tracking() -> None:
    psc = PSC.read_text(encoding="utf-8", errors="replace")

    if "Float DesperateEnteredGameTime" not in psc:
        fail("Main must declare DesperateEnteredGameTime (game-time stamp of continuous Desperate entry)")
    if "Float CALM_BONUS_PATIENCE_HOURS = 13.0" not in psc:
        fail("Main must declare CALM_BONUS_PATIENCE_HOURS = 13.0")

    track = extract_function(psc, "SyncDesperateTracking")
    if "HungerLevel >= 90.0" not in track:
        fail("SyncDesperateTracking must gate on HungerLevel >= 90.0 (Desperate)")
    if "DesperateEnteredGameTime = Utility.GetCurrentGameTime()" not in track:
        fail("SyncDesperateTracking must stamp entry time when first reaching Desperate")
    if "DesperateEnteredGameTime = 0.0" not in track:
        fail("SyncDesperateTracking must clear the stamp when dropping back below 90 (continuous only, no cumulative credit)")

    satiate = extract_function(psc, "SatiateHunger")
    if "CalmBonusEligible = DesperateEnteredGameTime > 0.0" not in satiate:
        fail("SatiateHunger must compute CalmBonusEligible from DesperateEnteredGameTime before HungerLevel resets")
    if "CALM_BONUS_PATIENCE_HOURS" not in satiate:
        fail("SatiateHunger's eligibility check must reference CALM_BONUS_PATIENCE_HOURS")
    # Eligibility must be computed BEFORE HungerLevel is wiped (order matters: reading
    # DesperateEnteredGameTime after the reset would still work since it's a separate var,
    # but the eligibility line must precede SyncDesperateTracking, which would otherwise
    # have already cleared DesperateEnteredGameTime for the *next* cycle first).
    idx_eligible = satiate.find("CalmBonusEligible =")
    idx_hunger_reset = satiate.find("HungerLevel = 0.0")
    idx_sync_desperate = satiate.find("SyncDesperateTracking()")
    if idx_eligible < 0 or idx_hunger_reset < 0 or idx_sync_desperate < 0:
        fail("SatiateHunger missing expected eligibility/reset/sync lines")
    if not (idx_eligible < idx_hunger_reset < idx_sync_desperate):
        fail("SatiateHunger must compute CalmBonusEligible, then reset HungerLevel, then SyncDesperateTracking — in that order")

    ok("SyncDesperateTracking: continuous Desperate stamp/clear; SatiateHunger reads it into CalmBonusEligible before resetting")


def test_wired_into_same_call_sites_as_penalty() -> None:
    psc = PSC.read_text(encoding="utf-8", errors="replace")

    resume = extract_function(psc, "HandleGameResume")
    if "SyncHungerAddictionSpell()" not in resume or "SyncCalmBonusSpell()" not in resume:
        fail("HandleGameResume must call both SyncHungerAddictionSpell() and SyncCalmBonusSpell()")
    if "SyncDesperateTracking()" not in resume:
        fail("HandleGameResume must call SyncDesperateTracking()")

    tick = extract_function(psc, "RunHungerTick")
    if tick.count("SyncCalmBonusSpell()") < 2:
        fail("RunHungerTick must call SyncCalmBonusSpell() on both the unlocked-early-return path and the normal end-of-tick path (same as SyncHungerAddictionSpell)")
    if tick.count("SyncDesperateTracking()") < 2:
        fail("RunHungerTick must call SyncDesperateTracking() on both paths too")

    delta = extract_function(psc, "ApplyHungerDelta")
    if "SyncHungerAddictionSpell()" not in delta or "SyncCalmBonusSpell()" not in delta:
        fail("ApplyHungerDelta must call both SyncHungerAddictionSpell() and SyncCalmBonusSpell()")
    if "SyncDesperateTracking()" not in delta:
        fail("ApplyHungerDelta must call SyncDesperateTracking() — this is the only path that ever raises HungerLevel into Desperate")

    satiate = extract_function(psc, "SatiateHunger")
    if "SyncHungerAddictionSpell()" not in satiate or "SyncCalmBonusSpell()" not in satiate:
        fail("SatiateHunger must call both SyncHungerAddictionSpell() and SyncCalmBonusSpell() — this is the kill-triggered instant drop into Calm")
    if "SyncDesperateTracking()" not in satiate:
        fail("SatiateHunger must call SyncDesperateTracking() (after reading eligibility, to reset the clock for the next cycle)")

    ok("SyncCalmBonusSpell + SyncDesperateTracking wired into every SyncHungerAddictionSpell call site (HandleGameResume, RunHungerTick x2, ApplyHungerDelta, SatiateHunger)")


def test_hunger_info_shows_calm_flag() -> None:
    psc = PSC.read_text(encoding="utf-8", errors="replace")
    info = extract_function(psc, "ShowHungerInfo")
    if "CalmBonusApplied" not in info:
        fail("ShowHungerInfo must surface the Calm bonus flag (mirrors the existing Withdrawal flag line) — "
             "no new debug button needed since DebugSatiateHunger already exercises the full apply path via SatiateHunger")
    ok("ShowHungerInfo surfaces Calm bonus flag alongside the existing Withdrawal flag")


def test_mcm_desperate_patience_row() -> None:
    mcm = MCM_CONFIG.read_text(encoding="utf-8", errors="replace")
    if '"id": "sDesperatePatience:Hunger"' not in mcm:
        fail("config.json Hunger page must expose an sDesperatePatience:Hunger status row")

    for path in (SETTINGS_A, SETTINGS_B):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "sDesperatePatience=" not in text:
            fail(f"{path} must default sDesperatePatience=")

    psc = PSC.read_text(encoding="utf-8", errors="replace")
    panel = extract_function(psc, "RefreshHungerPanel")
    if 'MCM.SetModSettingString(MOD_NAME, "sDesperatePatience:Hunger"' not in panel:
        fail("RefreshHungerPanel must write sDesperatePatience:Hunger")
    if "CALM_BONUS_PATIENCE_HOURS" not in panel:
        fail("RefreshHungerPanel's sDesperatePatience display must reference CALM_BONUS_PATIENCE_HOURS")
    ok("MCM Hunger page shows live sDesperatePatience (hours at/above Desperate, vs. CALM_BONUS_PATIENCE_HOURS)")


def main() -> int:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    test_pace_default()
    test_calm_bonus_properties()
    test_reconcile_apply_clear()
    test_sync_gate()
    test_desperate_tracking()
    test_wired_into_same_call_sites_as_penalty()
    test_hunger_info_shows_calm_flag()
    test_mcm_desperate_patience_row()
    print("All Slice L (hunger pace + Calm bonus) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
