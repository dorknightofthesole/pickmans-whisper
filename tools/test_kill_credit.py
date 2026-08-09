#!/usr/bin/env python3
"""Kill credit — RegisterTarget arms OnDeath while living+blade; RewardKill
settles at death if the blade is still drawn. No BladeTagged hit-memory /
hit-dead / late-corpse credit (bleed-out far from the knife is intentional).

Locks:
  - RegisterTarget (living + blade): RegisterForRemoteEvent OnDeath + RegisterForHitEvent
  - Actor.OnDeath → RewardKill → ProcessKnifeKill (blade still equipped)
  - RewardKill skips bed/lab (KnifeKillCreditSuppressed / IsNonGameplayCorpse)
  - No BladeTagged / HandleBladeHit / HandleNPCDeath / ReconcileBladeTagged
  - TrackLivingNear: IsNonGameplayCorpse + IsValidTarget + HitArmed dedup for hit whisper
  - Fully removed legacy: KillWatchList, FriendlySeen, PendingKillVictim, CombatGrace, …

Usage:
  python tools/test_kill_credit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
ALIAS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
TARGET_SCAN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperTargetScanScript.psc"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Function|Bool Function|Int Function|String Function)\s+{name}\s*\(",
        text,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\r?\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
    return text[start : start + end_m.end()]


def extract_event(text: str, signature_pattern: str) -> str:
    m = re.search(signature_pattern, text)
    if not m:
        fail(f"missing event matching {signature_pattern!r}")
    start = m.start()
    end_m = re.search(r"\r?\nEndEvent\b", text[start:])
    if not end_m:
        fail(f"no EndEvent for {signature_pattern!r}")
    return text[start : start + end_m.end()]


def main() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")

    for gone in (
        "BladeTagged",
        "BladeTaggedCount",
        "BLADE_TAGGED_MAX",
        "WasBladeTagged",
        "MarkBladeTagged",
        "ForgetBladeTagged",
        "ReconcileBladeTagged",
        "EnsureBladeTaggedList",
        "HandleBladeHit",
        "HandleNPCDeath",
        "RejectKill",
        "ToastHumanKillDetected",
        "LastDeathToastId",
        "LastHandledKillId",
        "LastKnifeKillRealTime",
        "KNIFE_KILL_COOLDOWN",
    ):
        if gone in text:
            fail(f"{gone} must be fully removed (BladeTagged / hit-dead credit retired)")
    ok("BladeTagged stack + HandleBladeHit/HandleNPCDeath retired")

    reg = extract_function(text, "RegisterTarget")
    if 'RegisterForRemoteEvent(akTarget, "OnDeath")' not in reg:
        fail("RegisterTarget living+blade must RegisterForRemoteEvent OnDeath")
    if "RegisterForHitEvent(akTarget, PlayerRef)" not in reg:
        fail("RegisterTarget living+blade must RegisterForHitEvent")
    ok("RegisterTarget arms OnDeath + Hit while living with blade")

    on_death = extract_event(text, r"Event\s+Actor\.OnDeath\s*\(")
    if "RewardKill(akSender)" not in on_death:
        fail("Actor.OnDeath must RewardKill")
    ok("Actor.OnDeath -> RewardKill")

    reward = extract_function(text, "RewardKill")
    if "IsNonGameplayCorpse" not in reward or "KnifeKillCreditSuppressed" not in reward:
        fail("RewardKill must skip bed gift / wound lab corpses")
    if "IsPickmansBladeEquipped" not in reward:
        fail("RewardKill must require blade still equipped at death")
    if "ProcessKnifeKill(akSender)" not in reward:
        fail("RewardKill must ProcessKnifeKill when blade is drawn")
    if "IsValidTarget(" in reward:
        fail("RewardKill must not re-run IsValidTarget (sticky arm at RegisterTarget)")
    ok("RewardKill: blade-at-death + non-gameplay skip -> ProcessKnifeKill")

    on_hit = extract_event(text, r"Event\s+OnHit\s*\(")
    if "MaybeSpeakHitWhisper" not in on_hit:
        fail("OnHit must MaybeSpeakHitWhisper")
    if "ProcessKnifeKill" in on_hit or "RewardKill" in on_hit:
        fail("OnHit must not credit kills (RewardKill / OnDeath only)")
    ok("OnHit is hit-whisper only (no kill credit)")

    track = extract_function(text, "TrackLivingNear")
    if "IsNonGameplayCorpse" not in track:
        fail("TrackLivingNear must still honor IsNonGameplayCorpse")
    if "IsValidTarget(ak)" not in track:
        fail("TrackLivingNear must call IsValidTarget")
    if "RegisterForHitEvent(ak, PlayerRef)" not in track or "MarkHitArmed(ak)" not in track:
        fail("TrackLivingNear must proactively RegisterForHitEvent + MarkHitArmed")
    if "WasHitArmed(ak)" not in track:
        fail("TrackLivingNear must dedup via WasHitArmed")
    ok("TrackLivingNear: ambient hit-arm dedup for whisper path")

    if "Actor[] HitArmed" not in text:
        fail("HitArmed must be Actor[]")
    was_armed = extract_function(text, "WasHitArmed")
    if "HitArmed[i] == ak" not in was_armed:
        fail("WasHitArmed must compare actor refs directly")
    mark_armed = extract_function(text, "MarkHitArmed")
    if "WasHitArmed(ak)" not in mark_armed:
        fail("MarkHitArmed must dedup via WasHitArmed before adding")
    ok("HitArmed list: Actor[] refs, dedup add")

    for gone in (
        "KillWatchList", "KillWatchCount", "KILL_WATCH_MAX",
        "AliveSeenIds", "WasAliveSeen(", "NoteAliveSeen(", "EnsureAliveSeenList",
        "PendingKillVictim", "CombatGraceUntilRealTime", "OnPlayerCombatBegan",
        "WatchKillCandidate(", "TagBladeVictim(", "ClearKillWatchForWeaponSwap",
        "ArmCombatTarget", "HandlePotentialKnifeKill", "BladeTaggedIds",
        "ScanNearbyDeadForKnifeKills", "ScanNearbyLivingCandidates",
        "ReArmHitEventsOnWatched", "PollWatchedForDeath", "EnsureKillWatchList",
        "FriendlySeenIds", "FriendlySeenCount", "FRIENDLY_SEEN_MAX",
        "EnsureFriendlySeenList", "NoteFriendlySeen(", "WasFriendlySeen(",
    ):
        if gone in text:
            fail(f"{gone} must be fully removed, not left as dead code")
    ok("legacy KillWatch / FriendlySeen / CombatGrace machinery fully removed")

    alias_text = ALIAS.read_text(encoding="utf-8", errors="replace")
    if re.search(r"Event\s+OnCombatStateChanged\s*\(", alias_text):
        fail("PlayerAliasScript.OnCombatStateChanged must be removed")
    ok("PlayerAliasScript has no orphaned OnCombatStateChanged")

    ts = TARGET_SCAN.read_text(encoding="utf-8", errors="replace")
    if "ReconcileBladeTagged" in ts:
        fail("TargetScan must not CallFunctionNoWait ReconcileBladeTagged")
    ok("TargetScan does not host ReconcileBladeTagged")

    print("All kill-credit contracts passed.")


if __name__ == "__main__":
    main()
