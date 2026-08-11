# Direction — Pickman's Whisper

Companion to **Necromantic** in a three-mod suite that shares tone, addiction/hunger loops, and (later) corpse-preservation patterns. Each mod ships alone; soft-stack when combined.

## Suite progression

1. **Occult Pact** — invitation, ritual, “is it real?”
2. **Pickman's Whisper** (this mod) — the knife, the voice, serial hunger
3. **Necromantic** — corpse intimacy after the killing habit

On the surface, Occult Pact and Pickman's Whisper are **not sexual by default**. Necromantic remains the primary sexual module (AAF); one narrow exception exists in Pickman's Whisper — Slice U's "Take Her" activate choice, a two-actor AAF scene only reachable once an NPC is already the player's slave (see Product hard rules below). Necromantic is single-actor by design (its "corpse" is a positioned prop, never a real second AAF participant) and couldn't do a living two-actor scene without a redesign of its own, so Slice U lives here directly rather than routed through it. Shared tech (toasts, craving meters, corpse hold lists / tokens) stays complementary — **no compile-time coupling**. Soft load order: Occult Pact → Pickman's Whisper → Necromantic.

## Fantasy

- Trigger: enter **Pickman's house** (gallery interior) and/or obtain **Pickman's Blade**.
- Voice begins **innocent**: trust-building, warmth, bonding with the wielder.
- After knife kills (Slice B+): praise and hunger satiation.
- Later: fixation on nearby non-essential NPCs (default adult female); tone escalates over knife-use bond, not calendar alone.
- Hunger / addiction shared concept with Necromantic — different satiation (knife kill vs corpse scene).
- Soft ties later: Lady Killer / Black Widow, Cannibal, optional butcher cell.
- Later vignette: wake to a bed corpse that vanishes when you look away (see [BED_CORPSE_HALLUCINATION.md](BED_CORPSE_HALLUCINATION.md) / Slice G).

## Nearby NPC discovery (architecture)

TargetScan replaces the Glowing One proximity-cloak bus and thins Main’s NPC tracking. Vision only — see [TARGET_SCAN_VISION.md](TARGET_SCAN_VISION.md).

## Product hard rules

- **AAF is limited to one feature**: the Slavery "Take Her" activate choice ([Slice U](SLICE_U_SLAVE_SCENE.md)) starts a real two-actor AAF scene, gated on `IsOurSlave` (only reachable once she's already enslaved). No other AAF/sexual content, and no TopicInfo dialogue scenes for the voice. Do not add AAF calls anywhere else without revisiting this rule.
- Essential / protected NPC filters are strict once kill tracking lands (Slice B).
- Lines are data-driven (`.txt`); extreme tone allowed; keep content editable.
- Do not master `Necromantic.esp`. Duplicate minimal helpers until a shared lib exists.
- Prefer toast/MessageBox first; custom audio later without blocking combat/exploration.

## Vanilla anchors

| Asset | FormID | Notes |
|-------|--------|--------|
| Pickman's Blade | `0x0022595F` | `Fallout4.esm` |
| Pickman Gallery interior | `0x000379C5` | EditorID `PickmanGallery01` |

## Locked policy defaults

- Hunger unlocks on first bond (gallery **or** blade), not after N kills.
- Satiation (B+): only kills **with** Pickman's Blade fully clear hunger.
- Corpse hold (E): duplicate Necromantic pattern; both mods may hold the same body when stacked.
