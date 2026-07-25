# Slice H — corpse decay (body + face) / consume + victim places

**Merged former Slice I** (FaceGen-preserving slot-54 face decals) into this slice. Face art guide: [Decay_Head_Guide.md](Decay_Head_Guide.md). Soft ties to **J** (preserve), **K** (Cannibal / butcher), **G** (bed gift POC), and **C5** Potential Victims.

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

- [x] **P0.1** — MCM Debug wound lab: sticky bed corpse (no auto-despawn), wound template menu, tint R/G/B/A sliders, apply count, Apply. Separate `PickmansWhisperDecayWoundLabScript` (fork of bed spawn; does not refactor BedGift).
- [x] **P0.2** — Wound Lab Porcupine skin: Scars + SkinTexture stepper + apply/all from `DecaySkinOverlays.txt` (soft `porcOverlays.esl`). Stacks with DeathMarks. Face lab uses Scripted Face Tints Damage/Boxer set (`DecayFaceOverlays.txt`, soft `SFT.esp`).
- [x] **P1** — Apply DeathMarks wound overlays on the bed-gift corpse (POC; no kill clock). Soft-fail loud if LooksMenu or DeadOverlays missing. Verified in-game.
- [ ] **P2** — **Deliver working Corpse Decay stage change in MCM** (Victims Set / Reset = kill clock only; KillerScan → `SyncOverlaysFromKillerScanSnapshot` applies). Stage 0 body `none`; Pallor (1) = tinted `SkinTexture_16`. Implemented — awaiting in-game confirm.
- [ ] **P3** — Stamp game-time on Pickman’s Blade kills; deepen overlays via ModConfig **startHours** thresholds + locked stage tint/skins/face ARMO; tracked victims without a stamp start at Freshly Deceased (coded — verify in-game).
- [ ] **P4** — At max stage (4 / Black Putrefaction), toast (and optional audio) urging the player to eat her before she is too ripe.
- [ ] **P5** — Reward eating the corpse at that peak stage and clear her from Potential Victims.
- [ ] **P6** — Face decal art finish (stages 1–4 toward putrefaction; stage 0 verified). Hard no slot-32 FaceGen swap. See [Decay_Head_Guide.md](Decay_Head_Guide.md).

Mark each phase Done only after in-game confirm.

## Locked stage tint + SkinTexture map (P3 clock)

**Single source:** `Data/PickmansWhisper/config/ModConfig.txt` keys `decayStage0`…`decayStage4`.

Format (semicolon fields — not comma; names have spaces):

```text
decayStageN=name;r;g;b;a;startHours;skins[+skin...];scars?
```

- `a` — LooksMenu opacity (0–1), fourth numeric after blue
- `startHours` — game-hours after credited blade kill when this stage begins (stay until next start; Black forever after)
- `skins` — one or more Porcupine SkinTexture ids joined with `+`, or `none` for **no body overlays** (default body)
- trailing `scars` — apply all `Scars_*` from `DecaySkinOverlays.txt` (not valid with `skins=none`)
- Face masks: `DecayFaceStages.txt` (`none` = strip PW face ARMO). Stages **0–1** are `none` (no mask); masks begin at stage **2** (Red).

| Stage | Name | R | G | B | A | Start (h) | Skins | Scars |
|------:|------|--:|--:|--:|--:|----------:|-------|:-----:|
| 0 | Freshly Deceased | 0.650 | 0.520 | 0.480 | 1.0 | 0 | `none` (default body) | — |
| 1 | Pallor Mortis | 0.300 | 0.750 | 0.720 | 1.0 | 0.25 (15 min) | `SkinTexture_16` dirt/tint only | — |
| 2 | Livor Mortis | 0.480 | 0.140 | 0.300 | 1.0 | 2 | `SkinTexture_16` dirt/tint only | — |
| 3 | Putrefaction | 0.380 | 0.820 | 0.480 | 1.0 | 48 (2 d) | `SkinTexture_16` dirt/tint only | — |
| 4 | Black Putrefaction | 0.149 | 0.118 | 0.102 | 1.0 | 240 (10 d) | `SkinTexture_16` dirt/tint only | — |

**Simplified body paint:** face ARMO first, then one dirt carrier + stage RGBA. Multi-skin / scars map retired (hung Papyrus before stage 4 finished).

**Intact limbs only (body overlays):** LooksMenu body skins glow at dismember UV edges (decay tint → green halo; CumOverlays → white). Body decay applies only when head + four limbs are attached (`IsCorpseLimbsIntact`). Missing limbs → clear PW body skins **and** CumOverlays templates from `CumOverlayIds.txt` (face ARMO still if head present). Butcher (`SeverCorpseLimb`) queues `StripBodyDecayOverlaysForDismember` after `Dismember`. PW does not apply cum — strip only (soft dep).

**MCM `bDecayVisuals:Victims` (default OFF):** when off, knife sync / Set stage still advance the murder clock and stage labels; knife/MCM `ApplyDecayStageOverlays` paint is skipped. **Bed gift** still paints DeathMarks + Black stage (vignette). Turn on for world-corpse decay visuals; load **Real HD Faces after** Pickman's Whisper if both are used.

**Kill path:** `ProcessKnifeKill` → `StampDecayKill` (FormID + kill game-time) → `SyncDecayForKnifeCorpse`. Killscan dead pass re-syncs when stage advances. Bed gift stays forced stage 4 (not in kill registry).

**Tracked victims:** if she is in the Potential Victims FormID table and dead with no decay stamp, KillerScan → `CallFunctionNoWait("SyncOverlaysFromKillerScanSnapshot")` stamps **Freshly Deceased** without LooksMenu on the voice stack, then applies stage overlays from the KillerScan `ScanDead` TargetSnapshot (no second `FindActors`). Backoff 30s on apply failure. Never inside `ProcessKnifeKill` / VoiceScan (LooksMenu `Utility.Wait` starved Notice + Recognition). MCM copy says `no decay clock (Name her, then Refresh)` only for untracked corpses.

**Killer Orchestrator (v1.3.0):** `PickmansWhisperKillerScanScript` is the sole neighborhood `FindActors` producer. Voice sync first; knife/cadence/Victims/CorpseDecay NoWait. **H P2:** Victims MCM Set/Reset moves the kill clock only; overlays apply via KillerScan → `SyncOverlaysFromKillerScanSnapshot` (no MCM ForceApply path).

Scripts must not bake a mirror of these RGBA/hours/skin lists. Missing/incomplete/unordered `startHours` fail loud. Wound Lab **Decay stage** stepper names must match ModConfig order; **Apply stage** reads ModConfig (reload via MCM Voice → Reload line banks). Wound Lab Tint A still tunes manual wound/skin/face Applies only.

## Locked face bruises (lab) — SFT Damage / Boxer

Wound Lab “apply all face” applies **all** SFT Damage Boxer headparts from `DecayFaceOverlays.txt`:

- Boxer - 12 Rounds
- Boxer - Broken Nose
- Boxer - Black Eye
- Boxer - Fat Lip

**Not on knife-kill sync in P3** — lab `Resurrect`/`ChangeHeadPart` is unsafe on world corpses (lab-only). Soft dep `SFT.esp`. Stage face **ARMO** (slot 54) rides the decay clock separately from these Boxer headparts.

## P0.2 in-game notes — Porcupine SkinTexture shortlist (lab browse)

Wound Lab look-test keepers (superset of the locked stage map above):

| Template | Notes |
|----------|--------|
| SkinTexture_01 | Really good |
| SkinTexture_03 | Keeper — **stage 4** (with 18) |
| SkinTexture_04 | Keeper |
| SkinTexture_07 | Keeper (lab) — not on locked 0–2 map anymore |
| SkinTexture_09 | Keeper |
| SkinTexture_13 | Keeper |
| SkinTexture_15 | Has veins — **stage 2** Livor (with 09) |
| SkinTexture_16 | Good **early** texture — **stage 1** Pallor (carrier for cyan/green tint `0.300;0.750;0.720`) |
| SkinTexture_17 | Late mottling — **stage 3** (with 16 carrier + 18) |
| SkinTexture_18 | Really good — **stages 3 and 4** (layered) |

Not listed above: leave out of gameplay shortlist for now (still in `DecaySkinOverlays.txt` for lab).

## Soft rules

- Do **not** decay essential/protected story NPCs (none should be victims anyway).
- Soft with **J**: preserved / Necromantic-held corpses pause or reset the decay clock (P3+).
- Cap stays **32** unless **J** raises hold limits.
