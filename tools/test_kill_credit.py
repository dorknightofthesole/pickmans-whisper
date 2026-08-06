#!/usr/bin/env python3
"""Kill-credit detection rewrite — replaces the old KillWatchList/AliveSeenIds/
BladeTaggedIds/PendingKillVictim/CombatGrace stack (four overlapping ambient
tracking lists + two independent "combat began" triggers on two different
scripts) with one path: a confirmed player+blade hit registers Actor.OnDeath
and adds the victim to a single BladeTagged list; the credit decision is made
live, once, at OnDeath (killer==player, IsBladeEquipped() now, IsValidTarget,
cooldown) instead of asking whether some ambient scan happened to notice the
victim beforehand.

This followed a live debugging session that found, in order: a dead-code arm
function (OnPlayerCombatBegan had zero callers), a one-shot grace window that
couldn't survive a real stealth approach, a non-refreshing grace window, a
silent dead-end race in WatchKillCandidate's own IsDead() re-check, a
permanent RegisterForRemoteEvent/RegisterForHitEvent leak (Unregister* was
never called anywhere in the file), and two more functions (ScanNearby-
DeadForKnifeKills, ReArmHitEventsOnWatched) that turned out to already be
dead code with zero callers. All of that collapses to: HandleBladeHit tags on
a confirmed hit, HandleNPCDeath decides credit and cleans up, ReconcileBlade-
Tagged is a safety-valve sweep for actors tagged but never killed.

A structural gap surfaced after THAT rewrite deployed: a whole play session
produced zero "blade-tagged" traces — HandleBladeHit never ran for any kill.
RegisterForHitEvent was only ever called reactively, inside HandleBladeHit
itself, to re-arm AFTER a hit already landed; nothing anywhere proactively
armed hit detection for a fresh, never-hit actor, so Actor.OnHit structurally
could not fire for a target's first strike — exactly the mod's core "sneak up
and stab an unaware target" case. Fixed by having TrackLivingNear (the
ambient sighting sweep that already runs for every nearby actor every
KillerScan tick) also call RegisterForHitEvent.

Two follow-up cleanups after that fix: (1) the arm call was gated on
IsBladeEquipped(), which is not load-bearing — HandleBladeHit and
HandleNPCDeath both independently re-check blade state live regardless — and
being gated that way didn't even reduce call volume, since TrackLivingNear
runs for every nearby actor every tick no matter the player's weapon anyway.
Replaced with a real dedup (WasHitArmed/MarkHitArmed) so each actor is armed
once, not re-registered every tick for as long as they stay nearby. (2)
HandleNPCDeath's six sequential rejection gates each repeated the same
"set reason, maybe toast, always trace" pattern inline; collapsed through a
shared RejectKill(reason) helper.

Locks:
  - HandleBladeHit: dead-at-hit-time routes directly to HandleNPCDeath; a
    live, not-yet-tagged victim registers OnDeath + marks tagged (deduped);
    NoteFriendlySeen is stamped on a confirmed non-hostile hit (closes the
    "ambient scan never saw them" gap for a genuine blade hit); hit-watching
    re-arms unconditionally so a multi-hit fight keeps working
  - HandleNPCDeath: cleans up (ForgetBladeTagged) unconditionally up front,
    before the credit decision; gate is killer==player + IsBladeEquipped +
    IsValidTarget + cooldown only — no tagged/seenAlive/combatGrace terms
  - Actor.OnDeath settle is RewardKill (event-driven TrackedNPCs path); legacy
    HandleNPCDeath remains for HandleBladeHit / KillerScan-era callers
  - MarkBladeTagged / WasBladeTagged / ForgetBladeTagged operate on a single
    Actor[] BladeTagged list; ForgetBladeTagged calls UnregisterForRemoteEvent
    (the old code never did, anywhere in the file — permanent leak)
  - ReconcileBladeTagged evicts (+ unregisters) tagged actors who wandered
    out of range or were never cleaned up any other way
  - ProcessKnifeCreditFromKillerScan still feeds TrackLivingNear (still
    needed for WasFriendlySeen / IsValidTarget) and calls ReconcileBladeTagged
  - TrackLivingNear no longer touches any kill-watch list — ambient sighting
    only, still honors IsNonGameplayCorpse + IsValidTarget (hard gate) — AND
    proactively arms hit detection (WasHitArmed/MarkHitArmed dedup, not
    IsBladeEquipped-gated) so Actor.OnHit can fire for a fresh target's
    first strike without re-registering the same actor every tick
  - HandleNPCDeath's rejection gates all route through RejectKill(reason)
  - Fully removed: KillWatchList/KillWatchCount/KILL_WATCH_MAX,
    AliveSeenIds/WasAliveSeen/NoteAliveSeen, PendingKillVictim,
    CombatGraceUntilRealTime, OnPlayerCombatBegan, WatchKillCandidate,
    TagBladeVictim, ClearKillWatchForWeaponSwap, ArmCombatTarget, and the
    already-dead ScanNearbyDeadForKnifeKills / ScanNearbyLivingCandidates /
    ReArmHitEventsOnWatched / PollWatchedForDeath
  - PlayerAliasScript's OnCombatStateChanged handler removed (existed only
    to feed the now-deleted ArmCombatTarget/PendingKillVictim)

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

    # --- HandleBladeHit ---
    hit = extract_function(text, "HandleBladeHit")
    if "HandleNPCDeath(victim, PlayerRef, \"hit-dead\")" not in hit:
        fail("HandleBladeHit must route an already-dead victim directly to HandleNPCDeath")
    if "MarkBladeTagged(victim)" not in hit or 'RegisterForRemoteEvent(victim, "OnDeath")' not in hit:
        fail("HandleBladeHit must register OnDeath + MarkBladeTagged on a confirmed live blade hit")
    if "NoteFriendlySeen(victim)" not in hit:
        fail("HandleBladeHit must stamp NoteFriendlySeen on a confirmed non-hostile hit (closes the ambient-scan-never-saw-them gap)")
    if "RegisterForHitEvent(victim, PlayerRef)" not in hit:
        fail("HandleBladeHit must re-arm hit-watching so a multi-hit fight keeps working")
    ok("HandleBladeHit: dead-at-hit direct credit, live-hit tag+register, friendly-seen stamp, hit re-arm")

    # --- RejectKill helper ---
    reject = extract_function(text, "RejectKill")
    if "LastKillIgnoreReason" in reject:
        fail("RejectKill must not set LastKillIgnoreReason (deleted Autovar)")
    if "ToastDebug(" not in reject or "Debug.Trace(" not in reject:
        fail("RejectKill must toast (conditionally) and always trace")
    ok("RejectKill: shared toast/trace helper (no Autovar)")

    # --- HandleNPCDeath ---
    death = extract_function(text, "HandleNPCDeath")
    if "ForgetBladeTagged(victim)" not in death:
        fail("HandleNPCDeath must clean up (ForgetBladeTagged) unconditionally")
    forget_idx = death.find("ForgetBladeTagged(victim)")
    dedup_idx = death.find("vid == LastHandledKillId")
    if forget_idx < 0 or dedup_idx < 0 or forget_idx > dedup_idx:
        fail("HandleNPCDeath must clean up BEFORE the dedup/credit checks, not scattered across every return path")
    for banned in ("tagged", "seenAlive", "combatGrace", "CombatGraceUntilRealTime", "WasAliveSeen", "IsInKillWatchList", "PendingKillVictim"):
        if banned in death:
            fail(f"HandleNPCDeath must not reference {banned} — credit gate is killer==player + IsBladeEquipped + IsValidTarget + cooldown only")
    if "akKiller != PlayerRef" not in death:
        fail("HandleNPCDeath must reject a non-player killer")
    if "IsBladeEquipped()" not in death:
        fail("HandleNPCDeath must require IsBladeEquipped() live")
    if "IsValidTarget(victim)" not in death:
        fail("HandleNPCDeath must gate on IsValidTarget(victim)")
    if "WasFriendlySeen(victim)" not in death:
        fail("HandleNPCDeath must compose knife feature WasFriendlySeen after hard gate")
    if "ProcessKnifeKill(victim)" not in death:
        fail("HandleNPCDeath must call ProcessKnifeKill on a valid credited kill")
    reject_calls = death.count("RejectKill(")
    if reject_calls < 5:
        fail(f"HandleNPCDeath's rejection gates must route through RejectKill (found {reject_calls} calls, expected at least 5)")
    if 'ToastDebug("PW debug: kill ignored' in death or 'Debug.Trace("PickmansWhisper: kill ignored' in death:
        fail("HandleNPCDeath must not inline the reason/toast/trace pattern — that's what RejectKill collapses")
    ok("HandleNPCDeath: upfront cleanup, simplified live gate via RejectKill, no ambient-list terms")

    # --- Tagged-list helpers ---
    if "Actor[] BladeTagged" not in text:
        fail("BladeTagged must be Actor[] (not Int[] FormIDs) so ReconcileBladeTagged can check distance/dead state directly")
    was_tagged = extract_function(text, "WasBladeTagged")
    if "BladeTagged[i] == ak" not in was_tagged:
        fail("WasBladeTagged must compare actor refs directly")
    mark = extract_function(text, "MarkBladeTagged")
    if "WasBladeTagged(ak)" not in mark:
        fail("MarkBladeTagged must dedup via WasBladeTagged before adding")
    forget = extract_function(text, "ForgetBladeTagged")
    if 'UnregisterForRemoteEvent(ak, "OnDeath")' not in forget:
        fail("ForgetBladeTagged must call UnregisterForRemoteEvent — the old code registered liberally but never unregistered anywhere in this file")
    reconcile = extract_function(text, "ReconcileBladeTagged")
    if "ForgetBladeTagged(ak)" not in reconcile:
        fail("ReconcileBladeTagged must clean up via ForgetBladeTagged")
    if "IsDead()" not in reconcile or "KILL_WATCH_RADIUS" not in reconcile:
        fail("ReconcileBladeTagged must evict actors who died some other way or wandered out of range")
    ok("BladeTagged list: Actor[] refs, dedup add, paired unregister+remove, range/dead reconcile sweep")

    # --- ProcessKnifeCreditFromKillerScan still feeds TrackLivingNear + reconcile ---
    ambient = extract_function(text, "ProcessKnifeCreditFromKillerScan")
    if "TrackLivingNear(" not in ambient:
        fail("ProcessKnifeCreditFromKillerScan must still feed TrackLivingNear (WasFriendlySeen / IsValidTarget still need ambient sighting)")
    if "ReconcileBladeTagged()" not in ambient:
        fail("ProcessKnifeCreditFromKillerScan must call ReconcileBladeTagged")
    if "HandlePotentialKnifeKill" in ambient or "KillWatchList" in ambient:
        fail("ProcessKnifeCreditFromKillerScan must not still poll a KillWatchList dead-scan — OnDeath is the credit path now")
    ok("ProcessKnifeCreditFromKillerScan: ambient sighting kept, dead-scan polling removed, reconcile wired in")

    # --- TrackLivingNear no longer touches kill-watch bookkeeping ---
    track = extract_function(text, "TrackLivingNear")
    if "IsNonGameplayCorpse" not in track:
        fail("TrackLivingNear must still honor IsNonGameplayCorpse")
    if "IsValidTarget(ak)" not in track:
        fail("TrackLivingNear must call IsValidTarget (hard gate; includes child override)")
    if "NoteFriendlySeen" not in track:
        fail("TrackLivingNear must still stamp NoteFriendlySeen")
    if "KillWatchList" in track or "KILL_WATCH_MAX" in track:
        fail("TrackLivingNear must not touch KillWatchList — ambient sighting only now")
    if "RegisterForHitEvent(ak, PlayerRef)" not in track or "MarkHitArmed(ak)" not in track:
        fail(
            "TrackLivingNear must proactively RegisterForHitEvent + MarkHitArmed — confirmed "
            "live that without this, Actor.OnHit never fires for a fresh target's first strike "
            "(RegisterForHitEvent is otherwise only called reactively inside HandleBladeHit, "
            "AFTER a hit already landed, so nothing ever arms it for the first swing) — a "
            "whole play session produced zero blade-tagged traces as a result"
        )
    if "WasHitArmed(ak)" not in track:
        fail("TrackLivingNear must dedup via WasHitArmed — without it, every nearby actor gets RegisterForHitEvent re-called every KillerScan tick for as long as they stay nearby")
    if re.search(r"If\s+IsBladeEquipped\(\)\s*\r?\n\s*RegisterForHitEvent", track):
        fail("TrackLivingNear must not gate hit-arming on IsBladeEquipped() — not load-bearing (HandleBladeHit/HandleNPCDeath both re-check blade state live) and doesn't reduce call volume since TrackLivingNear itself runs regardless of weapon; WasHitArmed dedup is what actually keeps this cheap")
    ok("TrackLivingNear: ambient sighting + hit-arm dedup (not blade-gated), kill-watch bookkeeping removed")

    # --- HitArmed dedup list ---
    if "Actor[] HitArmed" not in text:
        fail("HitArmed must be Actor[]")
    was_armed = extract_function(text, "WasHitArmed")
    if "HitArmed[i] == ak" not in was_armed:
        fail("WasHitArmed must compare actor refs directly")
    mark_armed = extract_function(text, "MarkHitArmed")
    if "WasHitArmed(ak)" not in mark_armed:
        fail("MarkHitArmed must dedup via WasHitArmed before adding")
    ok("HitArmed list: Actor[] refs, dedup add (no unregister needed — a lingering HitEvent registration is inert, not a leak)")

    # --- Confirm the old machinery is actually gone, not just unused ---
    for gone in (
        "KillWatchList", "KillWatchCount", "KILL_WATCH_MAX",
        "AliveSeenIds", "WasAliveSeen(", "NoteAliveSeen(", "EnsureAliveSeenList",
        "PendingKillVictim", "CombatGraceUntilRealTime", "OnPlayerCombatBegan",
        "WatchKillCandidate(", "TagBladeVictim(", "ClearKillWatchForWeaponSwap",
        "ArmCombatTarget", "HandlePotentialKnifeKill", "BladeTaggedIds",
        "ScanNearbyDeadForKnifeKills", "ScanNearbyLivingCandidates",
        "ReArmHitEventsOnWatched", "PollWatchedForDeath", "EnsureKillWatchList",
    ):
        if gone in text:
            fail(f"{gone} must be fully removed, not left as dead code")
    ok("old KillWatchList/AliveSeenIds/BladeTaggedIds/PendingKillVictim/CombatGrace machinery fully removed")

    # --- PlayerAliasScript's now-pointless combat handler removed ---
    alias_text = ALIAS.read_text(encoding="utf-8", errors="replace")
    if re.search(r"Event\s+OnCombatStateChanged\s*\(", alias_text):
        fail("PlayerAliasScript.OnCombatStateChanged must be removed — it existed only to feed the deleted ArmCombatTarget/PendingKillVictim")
    ok("PlayerAliasScript's orphaned OnCombatStateChanged handler removed")

    print("All kill-credit contracts passed.")


if __name__ == "__main__":
    main()
