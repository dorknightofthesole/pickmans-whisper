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
| One body | **Primary spawn**: SleepStart `TrySpawnBedCorpse` place+disable (no Pose/LooksMenu on sleep stack). Present poses on wake. |
| Overlay timer | BedGift one-shot `TIMER_BED_OVERLAYS` (does not reschedule from OnTimer). SleepStart / Present **arm** it via `KickBedOverlayOnesHot`. |
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
OnPlayerSleepStart
  → save BedAnchor
  → TrySpawnBedCorpse (PlaceAtMe + disable) when blade/bond/MCM/cooldown ok
  → KickBedOverlayOnesHot (no LooksMenu on sleep stack)

OnPlayerSleepStop
  → if BedCorpse: Enable → TIMER_BED_POSE (Is3DLoaded / Snap / settle) → KillSilent → strip
  → FinishBedPresentTail: ArmBedDespawnTimer + KickBedOverlayOnesHot + toast

TIMER_BED_DESPAWN (~4s)
  → ClearBedCorpse (hold/retry if overlay busy; watchdog force-clear)
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
