# Slice H — corpse decay / consume + victim places

Soft ties to **J** (preserve), **K** (Cannibal / butcher), **G** (bed gift POC), and **C5** Potential Victims.

## Visual path status

**Retired:** vanilla `PlayImpactEffect` + IPDS blood/bruise sprays — face-only / too faint.

**Active (P1 locked visual):** LooksMenu tinted `Overlays.Add` using **ROF DeadOverlays** DeathMarks templates (`INVB_OverlayFramework_DeadOverlays.esp`). Soft deps — no ESP master on ROF or LooksMenu. Tint RGB/A lightens the dark materials (not `AddEntry`’s zero tint).

- Template id list: `Data/PickmansWhisper/config/DecayWoundOverlays.txt` (single source; Female_* only for P1)
- Bed gift: `TIMER_BED_OVERLAYS` after warm (disabled/parked) applies DeathMarks + `ApplyDecayStageOverlays` stage 4; SleepStart finishes pending apply before wake Enable. Present only fallback-schedules if still unset — never sync-apply (stalls SleepStop / MCM Force)
- Logic: `PickmansWhisperCorpseDecayScript` on Main; bed gift calls on present
- MCM Debug: **Force corpse decay overlays** (same bed-gift path)
- MCM **Wound Lab** page (P0.1/P0.2): sticky spawn/clear + DeathMarks wound stepper + Porcupine Scars/SkinTexture steppers (template + optional template 2 with `(none)` skip) + **SFT face** steppers (Boxer bruises) + shared tint/count for overlays (`PickmansWhisperDecayWoundLabScript`). **Tint preset** menu writes R/G/B (P1 pale / death decay green / body decay red / ashen gray). Each Apply clears **only its bank** so wounds, skin, and face stack; skin/face 1+2 layer after one clear.
- Skin bank: `Data/PickmansWhisper/config/DecaySkinOverlays.txt` (soft dep `porcOverlays.esl`)
- Face bank: `Data/PickmansWhisper/config/DecayFaceOverlays.txt` — SFT Damage FULL names (`Boxer - …`). Soft dep **`SFT.esp`** (headpart records only; no ESP master). LooksMenu body overlays cannot paint FaceGen. Apply path mirrors SFT: `GardenOfEden2.GetHeadPartsByFullName` → `ChangeHeadPart`, with brief `Resurrect` + `QueueUpdate(facegen)` on dead lab corpses (ChangeHeadPart is weak on frozen PlaceAtMe bodies). Sex filter via `SFT_Damage` / `SFT_Damage_M` FormLists.
- Contract: `tools/test_corpse_decay.py`, `tools/test_decay_wound_lab.py`
- Stub: `tools/stubs/Overlays.psc` (copied from LooksMenu — do not invent APIs)

**Not required:** SPID / RobCo / ROF ambient faction distribution — PW applies overlays itself.

## Goals (unchanged)

1. **Decay** — knife victims do not stay visually “fresh” forever.
2. **Consume incentive** — at peak stage, urge then reward eating so the player clears her deliberately — that path **removes her from Potential Victims**.
3. **Places** (tangential) — last-known location for find-again / unloaded refs; not required for the visual POC.

## Phases

- [ ] **P0.1** — MCM Debug wound lab: sticky bed corpse (no auto-despawn), wound template menu, tint R/G/B/A sliders, apply count, Apply. Separate `PickmansWhisperDecayWoundLabScript` (fork of bed spawn; does not refactor BedGift).
- [ ] **P0.2** — Wound Lab Porcupine skin: Scars + SkinTexture stepper + apply/all from `DecaySkinOverlays.txt` (soft `porcOverlays.esl`). Stacks with DeathMarks. Face lab uses Scripted Face Tints Damage/Boxer set (`DecayFaceOverlays.txt`, soft `SFT.esp`).
- [ ] **P1** — Apply DeathMarks wound overlays on the bed-gift corpse (POC; no kill clock). Soft-fail loud if LooksMenu or DeadOverlays missing.
- [ ] **P2** — Stamp game-time on Pickman’s Blade kills and deepen overlays at day thresholds through the **locked stage tint ramp** below (stages 0–4).
- [ ] **P3** — At max stage (4 / Black Putrefaction), toast (and optional audio) urging the player to eat her before she is too ripe.
- [ ] **P4** — Reward eating the corpse at that peak stage and clear her from Potential Victims.

Mark each phase Done only after in-game confirm.

## Locked stage tint + SkinTexture map (P2)

**Single source:** `Data/PickmansWhisper/config/ModConfig.txt` keys `decayStage0`…`decayStage4`.

Format (semicolon fields — not comma; names have spaces):

```text
decayStageN=name;r;g;b;a;skins[+skin...];scars?
```

- `a` — LooksMenu opacity (0–1), fourth numeric after blue
- `skins` — one or more Porcupine SkinTexture ids joined with `+`
- trailing `scars` — apply all `Scars_*` from `DecaySkinOverlays.txt`

| Stage | Name | R | G | B | A | Skins | Scars |
|------:|------|--:|--:|--:|--:|-------|:-----:|
| 0 | Freshly Deceased | 0.650 | 0.520 | 0.480 | 1.0 | `SkinTexture_07` | — |
| 1 | Pallor Mortis | 0.350 | 0.680 | 0.650 | 1.0 | `SkinTexture_07` | — |
| 2 | Livor Mortis | 0.400 | 0.176 | 0.267 | 1.0 | `SkinTexture_07` | — |
| 3 | Putrefaction | 0.369 | 0.451 | 0.318 | 1.0 | `17`+`18` | all |
| 4 | Black Putrefaction | 0.149 | 0.118 | 0.102 | 1.0 | `03`+`18` | all |

Scripts must not bake a mirror of these RGBA/skin lists. Missing/incomplete keys fail loud. Wound Lab **Decay stage** stepper names must match ModConfig order; **Apply stage** reads ModConfig (reload via MCM Voice → Reload line banks). Wound Lab Tint A still tunes manual wound/skin/face Applies only.

## Locked face bruises (P2) — SFT Damage / Boxer

On each staged corpse (and Wound Lab “apply all face”), apply **all** SFT Damage Boxer headparts from `DecayFaceOverlays.txt`:

- Boxer - 12 Rounds
- Boxer - Broken Nose
- Boxer - Black Eye
- Boxer - Fat Lip

**Tint parity with body:** ideal = same stage RGB as body overlays / SkinTexture tint. **Constraint:** SFT Boxer HDPTs use baked materials, not LooksMenu `Overlays` tint channels — body tint may not transfer 1:1. Plan: try to match visually (material/tint hooks if any exist); if impossible, document loud and keep body stage tint on overlays only. Soft dep `SFT.esp`.

## P0.2 in-game notes — Porcupine SkinTexture shortlist (lab browse)

Wound Lab look-test keepers (superset of the locked stage map above):

| Template | Notes |
|----------|--------|
| SkinTexture_01 | Really good |
| SkinTexture_03 | Keeper — **stage 4** (with 18) |
| SkinTexture_04 | Keeper |
| SkinTexture_07 | Keeper — **stages 0–2** |
| SkinTexture_09 | Keeper |
| SkinTexture_13 | Keeper |
| SkinTexture_15 | Has veins — use **earlier** in decay ramp |
| SkinTexture_16 | Good **early** texture |
| SkinTexture_17 | Good **late** texture — **stage 3** (with 18) |
| SkinTexture_18 | Really good — **stages 3 and 4** (layered) |

Not listed above: leave out of gameplay shortlist for now (still in `DecaySkinOverlays.txt` for lab).

## Soft rules

- Do **not** decay essential/protected story NPCs (none should be victims anyway).
- Soft with J: preserved / Necromantic-held corpses pause or reset the decay clock (P2+).
- Cap stays **32** unless J raises hold limits.
