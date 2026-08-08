# Bed corpse hallucination (Slice G)

**Status:** G1 implemented in PSC + MCM.

**Fantasy beat:** After the knife bond is active, the player sleeps. On wake they see a corpse gift / hallucination; after a few seconds she is gone.

Ephemeral vignette — `DiamondCityResidentF01NoodleMarket` (unnamed female Resident) via `PlaceAtMe`, then `SnapIntoInteraction` + `KillSilent` on the bed (ragdoll fallback if snap fails). Not Necromantic preserve / not permanent.

**Code layout:** Self-contained on `PickmansWhisperBedGiftScript` (sleep events + own timers). Main keeps only shared callbacks (`OnBedGiftStatus`, kill-credit suppress, `IsNonGameplayCorpse`). PlayerAlias re-arms sleep via `GetBedGift()`. **No KillerScan coupling.**

---

## G1 locked decisions

| Topic | Choice |
|-------|--------|
| Despawn | BedGift oneshot `TIMER_BED_DESPAWN` (`BED_DESPAWN_SECONDS = 4.0`) after present |
| Beat | Pure vignette: `BondStarted` + blade equipped + MCM `bBedGift` + `ModConfig.txt` `bedGiftCooldownDays` (default `0.5` ≈ 12h; Debug **Bed gift every sleep** bypasses; default ON) |
| Hunger | No gate, no satiation (`KillSilent` credit suppressed; body never enters kill-watch) |
| One body | **EXPERIMENT**: SleepStart `TrySpawnBedCorpse` then `PresentBedCorpseOnWake` (posed before wake). SleepStop = interrupt cleanup only. Snap may fail while player occupies bed → ragdoll. |
| Overlay timer | BedGift one-shot `TIMER_BED_OVERLAYS` (does not reschedule from OnTimer). Spawn / Present **arm** it via `KickBedOverlayOnesHot`. |
| Spawn form | `Fallout4.esm` `DiamondCityResidentF01NoodleMarket` (`0x4DEC`, unnamed Resident; kill via `KillSilent(player)`) |
| Placement | Prefer `Enable` → wait `Is3DLoaded` → `SnapIntoInteraction(bed)` → settle → `KillSilent` → strip. Fallback if no 3D / snap fails: `KillSilent` + `SetPosition` + ragdoll (never call Snap without 3D). |
| Gear | `UnequipAll` + `RemoveAllItems` (before snap + after kill) |
| Sleep hook | **BedGift** `RegisterForPlayerSleep` (Alias re-arms via `GetBedGift()` every load) |
| Voice | Optional `ModConfig.txt` → `bedGiftWakeToast`; requires voice + blade |

Contract: `tools/test_bed_hallucination.py`. MCM Debug: **Force bed gift** / **Clear bed gift**.

Slice H: decay prefers apply while disabled — SleepStart arms `TIMER_BED_OVERLAYS` after PlaceAtMe. Present sync-apply forbidden (stalls SleepStop / MCM Force). See [SLICE_H_CORPSE_DECAY.md](SLICE_H_CORPSE_DECAY.md).

**Note:** `SnapIntoInteraction` fails if the bed seat is occupied. On wake the player has usually left the furniture; if snap still fails, status shows ragdoll fallback.

---

## When to spawn (G1)

```text
OnPlayerSleepStart (desired sleep >= 3h)
  → clear stale BedCorpse
  → TrySpawnBedCorpse (PlaceAtMe + disable)
  → PresentBedCorpseOnWake (Enable → TIMER_BED_POSE snap/kill → despawn arm + toast)
  → goal: already posed when player wakes (snap may fail if bed occupied)

OnPlayerSleepStop
  → interrupt → ClearBedCorpse; else ignore (already presented)

TIMER_BED_DESPAWN (~4s after Present)
  → ClearBedCorpse
```

After deploy: quit FO4 to desktop so old suspended stacks die.

---

## Verify (in-game)

1. Bonded + blade drawn → sleep → wake with corpse posed on bed (or ragdoll fallback).
2. On snap fail: always get toast `bed SnapIntoInteraction FAILED — ragdoll fallback` (not debug-gated).
3. After ~`BED_DESPAWN_SECONDS`, she despawns.
4. Debug force/clear work.
5. Wake toast only when blade drawn + voice on.
6. No blade drawn → SleepStart skips spawn (status visible).
