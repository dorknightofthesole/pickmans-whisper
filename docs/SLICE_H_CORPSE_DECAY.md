# Slice H — corpse decay / consume + victim places

Later slice. Design only until G / I+ priorities settle. Soft ties to **J** (preserve), **K** (Cannibal / butcher), and **C5** Potential Victims.

## Goals

1. **Decay** — named / held knife victims do not stay fresh forever.
2. **Consume incentive** — optional player action that clears the body *and* drops her from the Victims list.
3. **Places** — remember where each victim was last known so the player can find her again.

## Decay (options — pick one primary, others stretch)

| Approach | Idea | Notes |
|----------|------|--------|
| **A. Asset swap** | After N game days, disable/delete the Actor corpse and place a static / ash pile / gore prop | Cleaner long-term clutter; needs a shipped mesh FormID (vanilla or small ESP add) |
| **B. Gore-down** | Progressive `Dismember` / disable 3D / sink; end state unrecognizable gore | Reuses Slice F APIs; may look uneven across races |
| **C. Soft despawn** | After N days, delete ref if player is far / no LOS; toast optional | Simplest; less “story” unless paired with places |

**Default lean:** A or C for reliability; B only if F gore already feels good on that body.

- Clock: game-days since kill (or since last Necromantic scene / preserve refresh — TBD with J).
- MCM: enable + days threshold.
- Do **not** decay essential/protected story NPCs (none should be victims anyway).
- Soft with J: preserved / Necromantic-held corpses pause or reset the decay clock.

## Consume incentive (eat)

Incentivize the player to **eat** the corpse (Cannibal perk soft-gate and/or blade-drawn action) so the body is gone on purpose.

- On success: remove Actor ref (or leave minimal gore), **remove FormID from Potential Victims** (and any place stamp), optional hunger/voice reward toast.
- Complements K Cannibal stretch; no AAF / sex code.
- Fail loud if Cannibal required but missing (or offer a Pickman’s-only eat path with clearer cost).

## Victim places (tangential but foundational)

Associate each Potential Victim FormID with a **last-known location** so decay / preserve / eat / “find her again” have somewhere to point.

**Stamp when:**

- Named via MCM Victims
- Valid blade kill
- Butcher menu used on her corpse
- Optional: first fixation / recognition look

**Store (save-backed, parallel to `VictimIds` / `VictimNames`):**

- Cell EditorID or FormID (interior preferred)
- Optional world position (X/Y/Z) for exteriors
- Optional short label for MCM (“Sanctuary hills”, “Pickman Gallery”)

**Use:**

- MCM Victims line: name + place summary
- Later: toast “she’s still in {place}” when hunger is high
- Decay / consume resolve the Actor via hold alias + place hint if the ref was unloaded

Cap stays **32** unless J raises hold limits.

## Out of scope for H1

- Full butcher-shop cell (K)
- Infamy / witness rumors (L / M)
- Custom decay meshes beyond one vanilla prop if A is chosen

## Verify (when implemented)

1. Kill → place stamped; MCM shows location.
2. After configured days → decay path fires once; no double-delete.
3. Eat / consume → corpse gone + Victims slot cleared.
4. Preserve / Necromantic hold (J) does not fight decay without an explicit rule.
