# TargetScan vision (architecture note)

**Status:** vision / direction — recorded from product owner (2026-08-05).  
**Not a milestone checklist.** Do not treat this file as “ship TargetScan” or mark roadmap items Done from it alone.

## Why the Glowing One cloak is out

The proximity-cloak approach (Ability → Cloak MGEF → Hit SPEL/MGEF → `ProximityEffect` → `RegisterTarget`) will **not** work for this mod’s needs:

- Effect events effectively only showed up usefully around **enter then leave** of an NPC’s proximity — not a reliable “entered radius, stay tracked” bus.
- Even if enter fired cleanly, the model is a poor fit for **many NPCs at once**.

That chain (and `PickmansWhisperProximityEffect`) is retired. Do not reintroduce without explicit permission.

## Replacement: TargetScan (not old KillScan)

Nearby discovery moves to `PickmansWhisperTargetScanScript` — scanning for nearby NPCs (alive / dead / look, as authored there).

Unlike the old **KillScan** this replaces for discovery:

- **Minimal state — almost zero.** Not a heavy parallel tracker / snapshot empire on Main.
- Periodic scan + light local bookkeeping only as needed; prefer event registration (`OnDeath`, hits, etc.) over mirroring the world into big collections.

## Lighter MainQuestScript

Consequences of this direction:

- Main **no longer owns NPC tracking collections** (e.g. retired `TrackedNPCs` RefCollectionAlias path).
- **`OnDeath` registration is more reliable**, so the old missed-death backup path is unnecessary — the background settle queue / `KillReward` “was this death never rewarded?” thread is not part of the target architecture.

Main stays a thinner router: voice façades, kill credit when events fire, MCM/alias glue — not a proximity registry.

## Related retired pieces (context)

Already removed or being retired in line with this vision (see git / contracts; this doc does not drive further edits):

- Cloak SPEL/MGEF FormIDs `0x870`–`0x873`
- `PickmansWhisperProximityEffect`
- `KillRewardAlias` / pending-reward settle timer
- Main `TrackedNPCs` RefCollectionAlias mapping

## Agent note

If implementing further TargetScan / Main thinning work: wait for an explicit task. This file is **memory of intent**, not an instruction to refactor.