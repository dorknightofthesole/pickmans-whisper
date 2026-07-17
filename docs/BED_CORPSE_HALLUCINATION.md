# Bed corpse hallucination (design notes)

**Status:** Design capture only — not implemented. Intended as roadmap **Slice G** (see [ROADMAP.md](ROADMAP.md)). Turn this doc into an implementation plan when that slice starts.

**Fantasy beat:** After the knife bond is active, the player sleeps. While the screen is handling sleep (fade / menu), a corpse appears in or on the bed. On wake they see her. When they look away (and optionally look back), she is gone — a gift / hallucination / voice prank, not a permanent body.

Complements Necromantic later (same corpse *type*: real dead Actor) but this instance is ephemeral and should usually despawn before suite corpse-preserve logic claims it.

---

## Goals

1. Player wakes next to a usable-looking human corpse (adult female default, matching suite filters).
2. Player does **not** see a living NPC spawn and ragdoll-fall onto the bed.
3. Detect that the bed corpse is present (script-held ref).
4. Detect when she leaves the player's view / "frame," then despawn.
5. No custom corpse mesh / static clutter asset required.

## Non-goals

- Custom "pre-killed" corpse meshes or clutter props as the primary path (not real Actors; poor fit for later Necromantic targeting).
- Story / essential NPC bodies.
- Permanent bed trophies (that's closer to butcher cell / hold lists).
- AAF or sexual content.

---

## Asset approach (locked preference)

Usable FO4 corpses are almost always **dead Actors**, not separate corpse meshes.

| Option | Verdict |
|--------|---------|
| Static clutter "body" props | Reject for this feature — not Actor corpses |
| Custom corpse mesh in mod | Not needed |
| Vanilla Actor / leveled list → silent `Kill()` | **Preferred** |

Vanilla forms (soft-link `Fallout4.esm`, same idea as Necromantic Test Spawn): e.g. `LCharRaiderFemale`, scavenger / gunner female lists, etc. Curate a small whitelist later; default adult female non-essential.

**Still need one scripted `Kill()`** after `PlaceAtMe` so the engine treats her as dead. The issue to avoid is *seeing* that kill/ragdoll — solved by timing + disabled spawn (below), not by skipping `Kill()`.

---

## Sleep detection

Native FO4 (no F4SE required):

```papyrus
RegisterForPlayerSleep()

Event OnPlayerSleepStart(Float afSleepStartTime, Float afDesiredSleepEndTime, ObjectReference akBed)
EndEvent

Event OnPlayerSleepStop(Bool abInterrupted, ObjectReference akBed)
EndEvent
```

- `akBed` is the furniture used — primary placement anchor.
- Do **not** conflate with Wait (chairs); only sleep-in-bed unless we explicitly add wait later.
- Optional backup timing: `RegisterForMenuOpenCloseEvent("SleepWaitMenu")`.

### When to spawn (preferred)

```text
OnPlayerSleepStart
  → PlaceAtMe near akBed, InitiallyDisabled = True
  → Kill() while disabled / during sleep UI / fade
  → SetPosition / angle onto or beside bed
  → hold script ref (BedCorpse)
  → (optional) keep disabled until near wake

OnPlayerSleepStop (if not interrupted, or even if interrupted — policy TBD)
  → Enable if still disabled
  → optional toast from voice line bank
  → start LOS / look-away poll
```

**Why during sleep:** Screen is black / sleep menu covers the place→ragdoll. Player wakes up and she is already there.

Fallback if sleep-start timing is flaky: spawn in the first moments of wake while camera/controls settle — still better than broad-daylight Place+Kill.

---

## Placement

- Anchor: `akBed` from sleep events.
- Prefer **on / beside** the bed over a perfect tucked-in mattress pose (Z and furniture clipping are fiddly).
- Offset so she does not spawn inside the player.
- Hold a quest-scoped `Actor BedCorpse` ref until despawn so cell reset does not purge her mid-beat.
- Do **not** run Necromantic-style long-term `HoldCorpse` / claim token for this ephemeral instance (or strip on despawn). Slice F preserve is for knife-kill trophies, not hallucinations.

---

## Look-away / despawn

There is no true "is this pixel on screen?" API. Practical detection:

| Signal | Role |
|--------|------|
| `PlayerRef.HasLOS(BedCorpse)` | Primary "in view" |
| Facing angle + distance | Optional tighten so peripheral LOS does not count as "seen" |
| GoE camera helpers | Optional soft dep later |

### Recommended state machine

```text
Idle
  → (sleep spawn succeeds) → PresentHiddenOrEnabled
  → player gains LOS / considers "seen" → SeenOnce
  → lose LOS (grace timer) → LookedAway
  → despawn immediately  OR  wait for LOS regain then despawn
  → Gone (cooldown before another gift)
```

**Preferred player-facing read:** despawn **on look-away** so when they look back the bed is empty ("she was never there").

Alternate (if we want a jump-scare second look): keep until look-away **and** look-back, then despawn at the look-back moment.

### Grace timers (required)

- Wake camera cuts / fade-in can blip LOS — do not despawn in the first N seconds after `OnPlayerSleepStop`.
- Cell transitions / menus: pause the LOS poll while `Utility.IsInMenuMode()`.

### Despawn cleanup

- `Disable()` + `Delete()` (or equivalent safe cleanup).
- Clear `BedCorpse` ref; stop poll timer.
- Never leave a permanent accidental Actor in the cell.

---

## Gating / cadence (open, defaults suggested)

| Gate | Suggested default |
|------|-------------------|
| Bond required | Yes (`BondStarted`) |
| Hunger / intensity gate | Optional: only above hunger band or `BondIntensity` threshold |
| Cooldown | Several game-hours / sleeps between gifts |
| Interrupted sleep | Skip spawn or despawn without showing — TBD in plan |
| Settlement beds vs world beds | Allow both unless POC shows issues |
| MCM | Toggle feature; debug force-spawn / force-despawn |

---

## Voice / UX

- Optional toast on wake (trust / hunger bank, or new `BedGiftLines.txt`).
- Optional toast on despawn ("Look again...") — keep sparse so it feels uncanny, not spammy.
- Still toast-only until Slice D audio.

---

## Cross-slice dependencies

| Slice | Relationship |
|-------|----------------|
| **A** | Bond + toast infrastructure |
| **B+** | Stronger fantasy if hunger/intensity gates gifts |
| **C** | Same adult-female non-essential filter language; GoE optional for camera |
| **E** | Do **not** treat hallucination corpse as preserved trophy |
| **G** (ex-F) | Independent of perk / butcher stretch |

Necromantic: if player somehow starts a scene on this body before despawn, that is an edge case — prefer despawn-on-look-away fast enough that it is rare; do not add AAF code here.

---

## POC checklist (for the future plan)

1. `RegisterForPlayerSleep` fires start/stop with valid `akBed`.
2. Disabled PlaceAtMe + Kill during sleep → wake with corpse, no visible fall (eyeball test).
3. Bed Z/offset acceptable on vanilla common beds.
4. LOS SeenOnce → look-away → despawn; wake grace does not false-trigger.
5. Cooldown + interrupted sleep behavior signed off.
6. MCM smoke: force gift, force clear.

---

## Risks

- Ragdoll still visible if spawn runs after fade-in.
- Some bed furniture warps corpses through geometry.
- `HasLOS` ≠ camera frustum; may need facing cone.
- Essential/protected filters when picking spawn bases (never unique story NPCs).
- Player looting / dragging the body before despawn — decide: allow and then vanish, or ghost inventory, or shorten window.

---

## Open questions (resolve when planning Slice G)

1. Despawn on look-away only, or look-away + look-back?
2. Count as knife activity / hunger interaction, or pure vignette?
3. Can the player loot her before she vanishes?
4. One body per sleep max; refuse if another `BedCorpse` still alive in world?
5. Share spawn form list with Necromantic Test Spawn labels for suite consistency?

---

## References

- Necromantic `SpawnTestEnemy` — vanilla female leveled lists + `PlaceAtMe` + offset (combat path; we kill silently instead).
- FO4 `RegisterForPlayerSleep` / `OnPlayerSleepStart` / `OnPlayerSleepStop`.
- Suite filters: adult female, non-essential (DIRECTION / Slice C).
