# Bed corpse hallucination (Slice G)

**Status:** G1 implemented in PSC + MCM.

**Fantasy beat:** After the knife bond is active, the player sleeps. On wake they see a corpse gift / hallucination; after a few seconds she is gone.

Ephemeral vignette — `LCharRaiderFemale` Actor via `PlaceAtMe`, then `SnapIntoInteraction` + `KillSilent` on the bed (ragdoll fallback if snap fails). Not Necromantic preserve / not permanent.

**Code layout:** Logic lives on `PickmansWhisperBedGiftScript` (attached to the same Main quest). `PickmansWhisperMainQuestScript` keeps thin façades (`HandlePlayerSleep*`, `MaybeWarmBedGiftBody`, MCM debug) so PlayerAlias / killscan / MCM keep calling Main.

---

## G1 locked decisions

| Topic | Choice |
|-------|--------|
| Despawn | Real-time timer (~6s after present) |
| Beat | Pure vignette: `BondStarted` + MCM `bBedGift` + ~12h cooldown (Debug **Bed gift every sleep** bypasses; default ON) |
| Hunger | No gate, no satiation |
| One body | **Single gameplay spawn**: killscan `MaybeWarmBedGiftBody` only. SleepStart saves bed; SleepStop Present or skip. No retries. |
| Spawn form | `Fallout4.esm` `LCharRaiderFemale` (`0xD39F5`) |
| Placement | Prefer `SnapIntoInteraction(bed)` → `Utility.Wait(0.5)` → `KillSilent` → strip. Fallback: `KillSilent` + `SetPosition` + ragdoll. |
| Gear | `UnequipAll` + `RemoveAllItems` (before snap + after kill) |
| Sleep hook | **PlayerAlias** `RegisterForPlayerSleep` |
| Voice | Optional `BedGiftLines.txt` wake toast; requires voice + blade |

Contract: `tools/test_bed_hallucination.py`. MCM Debug: **Force bed gift** / **Clear bed gift**.

**Note:** `SnapIntoInteraction` fails if the bed seat is occupied. On wake the player has usually left the furniture; if snap still fails, status shows ragdoll fallback.

---

## When to spawn (G1)

```text
While awake (killscan) — ONLY PlaceAtMe site
  → MaybeWarmBedGiftBody → PlaceAtMe LCharRaiderFemale (alive)
  → ghost + park disabled under player

OnPlayerSleepStart
  → save BedAnchor only (never PlaceAtMe)

OnPlayerSleepStop
  → if BedCorpse alive: Enable → SnapIntoInteraction → Wait → KillSilent → strip
  → else: skip (no retry)
  → toast → ~6s despawn
```

---

## Verify (in-game)

1. Bonded → walk ~10s → sleep → wake with corpse posed on bed (or ragdoll fallback).
2. On snap fail: always get toast `bed SnapIntoInteraction FAILED — ragdoll fallback` (not debug-gated).
3. ~6s later she despawns.
4. Debug force/clear work.
5. Wake toast only when blade drawn + voice on.
