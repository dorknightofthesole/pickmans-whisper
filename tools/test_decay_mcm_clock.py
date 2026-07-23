#!/usr/bin/env python3
"""Contracts for Victims MCM decay kill-clock test harness.

Reset → murder time = now, stage selector → 0.
Apply → killTime = now − (ModConfig startHours[stage] / 24).

Pure math mirrors ForceDecayKillClockToStage + ResolveDecayStageFromElapsedHours.
Papyrus/MCM wiring asserts Reset + Apply stay clock-only (WorldScan applies overlays).

Usage:
  python tools/test_decay_mcm_clock.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
VICTIMS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVictimsScript.psc"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
MOD_CONFIG = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"

# Keep in sync with ModConfig decayStage0..4 startHours (and test_decay_stage_modconfig).
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


def kill_game_time_for_stage(now_days: float, start_hours: float) -> float:
    """Mirror ForceDecayKillClockToStage: killTime = now - (elapsedH / 24).

    elapsedH is startHours, plus a 0.001h pad when startHours > 0 so Float
    round-trip still satisfies elapsed >= startHours.
    """
    elapsed_h = float(start_hours)
    if elapsed_h > 0.0:
        elapsed_h += 0.001
    return now_days - (elapsed_h / 24.0)


def elapsed_hours_since_kill(now_days: float, kill_days: float) -> float:
    return (now_days - kill_days) * 24.0


def resolve_decay_stage(elapsed_hours: float, starts: tuple[float, ...] | list[float]) -> int:
    """Mirror ResolveDecayStageFromElapsedHours."""
    elapsed = max(0.0, float(elapsed_hours))
    stage = 0
    for i, start in enumerate(starts):
        if elapsed >= start:
            stage = i
    return stage


def load_modconfig_start_hours() -> list[float]:
    text = MOD_CONFIG.read_text(encoding="utf-8")
    starts: dict[int, float] = {}
    for line in text.splitlines():
        t = line.strip()
        if not t or t.startswith("#") or "=" not in t:
            continue
        key, val = t.split("=", 1)
        m = re.fullmatch(r"decayStage([0-4])", key.strip())
        if not m:
            continue
        fields = [f.strip() for f in val.split(";")]
        if len(fields) < 7:
            fail(f"{key} needs startHours at field[5]: {val!r}")
        starts[int(m.group(1))] = float(fields[5])
    if set(starts.keys()) != {0, 1, 2, 3, 4}:
        fail(f"expected decayStage0..4 startHours, got {sorted(starts)}")
    return [starts[i] for i in range(5)]


def test_reset_is_now_then_apply_subtracts_start_hours() -> None:
    """User flow: reset → now (stage 0); pick stage N → subtract startHours[N]."""
    starts = load_modconfig_start_hours()
    if starts != list(SHIPPED_START_HOURS):
        fail(f"ModConfig startHours {starts} != locked {list(SHIPPED_START_HOURS)}")

    now = 1000.5  # arbitrary game-days

    # 1–2. Reset: murder time = now → elapsed 0 → stage 0 regardless of prior stage.
    kill_after_reset = now
    elapsed_reset = elapsed_hours_since_kill(now, kill_after_reset)
    if abs(elapsed_reset) > 1e-9:
        fail(f"reset elapsed must be 0, got {elapsed_reset}")
    if resolve_decay_stage(elapsed_reset, starts) != 0:
        fail("reset must resolve to stage 0")

    # 3. Apply: from "now", subtract hours needed to reach selected stage.
    for stage, start_h in enumerate(starts):
        kill = kill_game_time_for_stage(now, start_h)
        elapsed = elapsed_hours_since_kill(now, kill)
        want_elapsed = start_h if start_h <= 0.0 else start_h + 0.001
        if abs(elapsed - want_elapsed) > 1e-9:
            fail(f"stage {stage}: elapsed {elapsed} != {want_elapsed} (startHours={start_h})")
        if elapsed + 1e-12 < start_h:
            fail(f"stage {stage}: elapsed {elapsed} below threshold {start_h}")
        got = resolve_decay_stage(elapsed, starts)
        if got != stage:
            fail(f"stage {stage}: resolve({elapsed}) == {got}, want {stage}")

    # Selecting a later stage after reset must not depend on prior LastStage.
    for prior in (0, 1, 2, 3, 4):
        for target in range(5):
            kill = kill_game_time_for_stage(now, starts[target])
            got = resolve_decay_stage(elapsed_hours_since_kill(now, kill), starts)
            if got != target:
                fail(f"from prior={prior} apply target={target} resolved {got}")

    ok("reset=now (stage 0); apply subtracts startHours -> correct stage")


def test_force_clock_uses_exact_start_hours() -> None:
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    force = extract_function(main, "ForceDecayKillClockToStage")
    if "GetDecayStageStartHours" not in force:
        fail("ForceDecayKillClockToStage must read GetDecayStageStartHours")
    if "elapsedH / 24.0" not in force and "needH / 24.0" not in force:
        fail("ForceDecayKillClockToStage must set killTime = now - (hours / 24)")
    if "needH + 0.001" not in force:
        fail("ForceDecayKillClockToStage must pad startHours>0 by 0.001h for Float safety")
    # Mid-point / +1.0 black padding fights the "subtract startHours" MCM model.
    # (Do not search bare "mid =" — it false-matches inside "formId ==".)
    if "* 0.5" in force or "nextH" in force or "(needH + nextH)" in force:
        fail("ForceDecayKillClockToStage must not mid-point between stages")
    if "needH + 1.0" in force:
        fail("ForceDecayKillClockToStage must not pad Black past startHours")
    ok("ForceDecayKillClockToStage = startHours backdate (+0.001h pad)")


def test_mcm_reset_and_apply_wiring() -> None:
    victims = VICTIMS.read_text(encoding="utf-8", errors="replace")
    main = MAIN.read_text(encoding="utf-8", errors="replace")
    cfg = MCM_CONFIG.read_text(encoding="utf-8")

    reset_body = extract_function(victims, "ResetAimedDecayKillClock")
    for needle in (
        "StampDecayKill",
        'iVictimDecayStage:Victims", 0',
        "NoteForcedDecayClockForTest",
        "ResolveVictimsAimActor",
    ):
        if needle not in reset_body:
            fail(f"ResetAimedDecayKillClock must use {needle}")
    if "ApplyDecayStageOverlays" in reset_body:
        fail("ResetAimedDecayKillClock must NOT ApplyDecayStageOverlays")

    mcm_reset = extract_function(victims, "MCMResetAimedDecayKillClock")
    if "ResetAimedDecayKillClock" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must call ResetAimedDecayKillClock")
    if 'iVictimDecayStage:Victims", 0' not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must force stage selector to 0")
    if "StartTimer" not in mcm_reset or "TIMER_DECAY_ADVANCE" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must StartTimer to nudge WorldScan after MCM closes")
    if "ApplyDecayStageOverlays" in mcm_reset:
        fail("MCMResetAimedDecayKillClock must NOT ApplyDecayStageOverlays")

    prep = extract_function(victims, "PrepAimedDecayStage")
    if "ForceDecayKillClockToStage" not in prep:
        fail("PrepAimedDecayStage must ForceDecayKillClockToStage (subtract startHours)")
    if "ApplyDecayStageOverlays" in prep:
        fail("PrepAimedDecayStage must NOT ApplyDecayStageOverlays")

    mcm_apply = extract_function(victims, "MCMApplyAimedDecayStage")
    if "iVictimDecayStage:Victims" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must read selected stage")
    if "PrepAimedDecayStage" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must PrepAimedDecayStage")
    if "McmDecayButtonBusy" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must guard re-entrant MCM CallFunction spam")
    if "WriteDecayStageStatusToMcmForActor(aimed, False)" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must write status without SyncVictimDecayStageStepper")
    if "SetModSettingInt(MOD_NAME, \"iVictimDecayStage:Victims\", stage)" not in mcm_apply:
        fail("MCMApplyAimedDecayStage must latch chosen stage so spam cannot re-read 0")

    mcm_reset = extract_function(victims, "MCMResetAimedDecayKillClock")
    if "McmDecayButtonBusy" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must guard re-entrant MCM CallFunction spam")
    if "WriteDecayStageStatusToMcmForActor(aimed, False)" not in mcm_reset:
        fail("MCMResetAimedDecayKillClock must write status without SyncVictimDecayStageStepper")

    write_status = extract_function(main, "WriteDecayStageStatusToMcmForActor")
    if "abSyncStepper" not in write_status:
        fail("WriteDecayStageStatusToMcmForActor must accept abSyncStepper")

    if "Victims()" not in extract_function(main, "MCMResetAimedDecayKillClock"):
        fail("Main MCMResetAimedDecayKillClock must façade via Victims()")

    if '"function": "MCMResetAimedDecayKillClock"' not in cfg:
        fail("config.json must wire Reset decay stage -> MCMResetAimedDecayKillClock")
    if '"text": "Reset decay stage"' not in cfg:
        fail("config.json missing Reset decay stage button label")
    if '"text": "Set decay stage"' not in cfg:
        fail("config.json missing Set decay stage button label")
    if '"scriptName": "PickmansWhisperVictimsScript"' not in cfg:
        fail("config.json Victims CallFunctions must target PickmansWhisperVictimsScript")
    # Reset button must use VictimsScript (same multi-script quest pattern).
    reset_idx = cfg.find('"function": "MCMResetAimedDecayKillClock"')
    if reset_idx < 0:
        fail("missing MCMResetAimedDecayKillClock in config.json")
    window = cfg[max(0, reset_idx - 400) : reset_idx + 200]
    if '"scriptName": "PickmansWhisperVictimsScript"' not in window:
        fail("MCMResetAimedDecayKillClock action must set scriptName PickmansWhisperVictimsScript")
    apply_idx = cfg.find('"function": "MCMApplyAimedDecayStage"')
    if apply_idx < 0 or apply_idx >= reset_idx:
        fail("Set decay stage button must appear above Reset decay stage")

    ok("MCM reset/apply wiring (clock-only; selector -> 0 on reset)")


def main() -> int:
    if not MAIN.is_file() or not VICTIMS.is_file():
        fail("missing Main or Victims PSC")
    test_reset_is_now_then_apply_subtracts_start_hours()
    test_force_clock_uses_exact_start_hours()
    test_mcm_reset_and_apply_wiring()
    print("All decay MCM clock contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
