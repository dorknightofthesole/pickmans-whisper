# Bed corpse hallucination (Slice G)

**Status:** G1 implemented in PSC + MCM.

**Fantasy beat:** After the knife bond is active, the player sleeps. On wake they see a corpse gift / hallucination; after a few seconds she is gone.

Ephemeral vignette — `DiamondCityResidentF01NoodleMarket` (unnamed female Resident) via `PlaceAtMe`, then `SnapIntoInteraction` + `KillSilent` on the bed (ragdoll fallback if snap fails). Not Necromantic preserve / not permanent.

**Code layout:** Logic lives on `PickmansWhisperBedGiftScript` (attached to the same Main quest). `PickmansWhisperMainQuestScript` keeps thin façades (`HandlePlayerSleep*`, `MaybeWarmBedGiftBody`, MCM debug) so PlayerAlias / killscan / MCM keep calling Main.

---

## G1 locked decisions

| Topic | Choice |
|-------|--------|
| Despawn | KillerScan pulse count (`BED_DESPAWN_SCANS = 2`) after present |
| Beat | Pure vignette: `BondStarted` + MCM `bBedGift` + `ModConfig.txt` `bedGiftCooldownDays` (default `0.5` ≈ 12h; Debug **Bed gift every sleep** bypasses; default ON) |
| Hunger | No gate, no satiation (`KillSilent` credit suppressed; body never enters kill-watch) |
| One body | **Primary spawn**: killscan `MaybeWarmBedGiftBody` every tick while bonded. **SleepStart fallback** place+disable only (no Pose/LooksMenu on sleep stack). Present poses on wake. Despawn pulses sync on KillerScan. |
| Overlay timer | **Experiment:** BedGift one-shot `TIMER_BED_OVERLAYS` (does not reschedule). KillerScan / Present only **arm** it. Recurring timer remains KillerScan-only. |
| Spawn form | `Fallout4.esm` `DiamondCityResidentF01NoodleMarket` (`0x4DEC`, unnamed Resident; kill via `KillSilent(player)`) |
| Placement | Prefer `Enable` → wait `Is3DLoaded` → `SnapIntoInteraction(bed)` → `Utility.Wait(0.5)` → `KillSilent` → strip. Fallback if no 3D / snap fails: `KillSilent` + `SetPosition` + ragdoll (never call Snap without 3D). |
| Gear | `UnequipAll` + `RemoveAllItems` (before snap + after kill) |
| Sleep hook | **PlayerAlias** `RegisterForPlayerSleep` |
| Voice | Optional `ModConfig.txt` → `bedGiftWakeToast`; requires voice + blade |

Contract: `tools/test_bed_hallucination.py`. MCM Debug: **Force bed gift** / **Clear bed gift**.

Slice H: decay applies **before Enable** when possible — deferred timer after warm (parked/disabled), with SleepStart finishing any pending apply during the sleep fade. Wake only Enables an already Black Putrefaction body (Present sync-apply forbidden — stalls SleepStop / MCM Force). See [SLICE_H_CORPSE_DECAY.md](SLICE_H_CORPSE_DECAY.md).

**Note:** `SnapIntoInteraction` fails if the bed seat is occupied. On wake the player has usually left the furniture; if snap still fails, status shows ragdoll fallback.

---

## When to spawn (G1)

```text
While awake (killscan) — ONLY PlaceAtMe site
  → MaybeWarmBedGiftBody → PlaceAtMe DiamondCityResidentF01NoodleMarket (alive)
  → ghost + park disabled under player
  → ScheduleBedGiftDecayOverlays (BedOverlaysAtReal); KillerScan arms one-shot TIMER_BED_OVERLAYS

OnPlayerSleepStart
  → save BedAnchor; TrySpawn fallback if warm missed (place+disable only)
  → schedule overlays if still pending (no LooksMenu on sleep stack)

OnPlayerSleepStop
  → if BedCorpse: Enable → wait Is3DLoaded → SnapIntoInteraction → Wait → KillSilent → strip
  → clear BedOverlaysApplied → KickBedOverlayOnesHot (paint AFTER pose; oneshot OnTimer)
  → toast → despawn on 2nd KillerScan pulse
```

After deploy: quit FO4 to desktop so old suspended stacks (e.g. retired `BedDespawnAtReal`) die.

---

## Verify (in-game)

1. Bonded → walk ~10s → sleep → wake with corpse posed on bed (or ragdoll fallback).
2. On snap fail: always get toast `bed SnapIntoInteraction FAILED — ragdoll fallback` (not debug-gated).
3. On the **2nd KillerScan** deadline pulse after present, she despawns.
4. Debug force/clear work.
5. Wake toast only when blade drawn + voice on.
