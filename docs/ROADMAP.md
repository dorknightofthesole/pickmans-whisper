# Roadmap — Pickman's Whisper

Status source of truth for this repo. Suite framing: [DIRECTION.md](DIRECTION.md).

| Slice | Deliverable | Status |
|-------|-------------|--------|
| **A** | Trigger on house/knife; toast-only voice; hunger meter; MCM | **Shipped (0.1.0)** |
| **B** | Kill-with-knife praise + satiation rules | **Shipped (0.2.0)** |
| **C** | NPC scan + fixation mentions + tone tiers | Planned |
| **D** | Audio bank playback (research + implement) | Planned |
| **E** | Corpse preserve sync with Necromantic | Planned |
| **F** | Bed corpse hallucination (sleep spawn + look-away despawn) | Planned — design: [BED_CORPSE_HALLUCINATION.md](BED_CORPSE_HALLUCINATION.md) |
| **G** | Perk gates; optional butcher cell / Cannibal hooks | Planned |

## Slice A — trigger, toast, hunger, MCM

- Bond on `PickmanGallery01` enter and/or blade acquire/equip.
- Trust line bank + hunger band toasts.
- Hunger 0–100 with AGI/CHA withdrawal stand-in (Necromantic craving pattern).
- MCM: How To Use, Hunger, Voice, Debug.
- Satiation UI copy present; full clear on knife kill reserved for B.

## Slice B — knife kills + satiation

- Detect kills while weapon is Pickman's Blade (primary: nearby living→dead GoE scan; soft backups: `OnDeath` / hit-tag / combat target).
- Valid target: adult **female** non-**essential** human, seen **non-hostile** while alive (Protected settlers **do** count after you aggro them); skips men, hostiles-from-first-sight (raiders), children, teammates, ghoul/SM/synth/robot.
- Only kills with **Pickman's Blade** equipped count (brief post-swing sheath window only); other weapons do not sate.

## Slice C — NPC scan + fixation

- Periodic Garden of Eden scan; default adult female non-essential.
- Fixation list + tone tiers from bond / knife-days.
- Lines: crush → jealousy → remove → kill urge.

## Slice D — audio

- Research: `Sound.Play` / SNDR / F4SE file helpers / GoE hooks.
- Non-blocking one-shots; toast fallback always available.

## Slice E — corpse preserve

- `HeldCorpses[]` + soft claim token on knife-kill victims.
- Compatible with Necromantic holds; no ESP master dependency.
- Ephemeral bed-hallucination corpses (Slice F) are **not** long-term hold targets.

## Slice F — bed corpse hallucination

Design notes (for a later implementation plan): [BED_CORPSE_HALLUCINATION.md](BED_CORPSE_HALLUCINATION.md).

- On sleep start: spawn disabled vanilla female Actor at bed, silent `Kill()`, place on/beside bed.
- On wake: player finds the corpse; no visible place→ragdoll if timed during sleep fade.
- Track presence via script ref; `HasLOS` (+ optional facing) for in-view.
- Despawn on look-away (preferred) so look-back finds an empty bed.
- Bond / hunger / cooldown gates; MCM toggle + debug; no custom corpse mesh.

## Slice G — perk / stretch

- Soft-gate or enhance via Lady Killer / Black Widow.
- Optional Cannibal; stretch butcher-shop cell.
- Occult Pact bridges documented only until that mod exists.

## Risks

- Audio without dialogue may need F4SE / custom sound forms.
- Essential NPC filters must never break main quests.
- Tone is extreme — keep lines in editable config files.
- Bed hallucination: sleep timing, bed Z clipping, LOS false-triggers on wake camera (see Slice F doc).
