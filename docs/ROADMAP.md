# Roadmap — Pickman's Whisper

Status source of truth for this repo. Suite framing: [DIRECTION.md](DIRECTION.md).

| Slice | Deliverable | Status |
|-------|-------------|--------|
| **A** | Trigger on house/knife; toast-only voice; hunger meter; MCM | **Shipped (0.1.0)** |
| **B** | Kill-with-knife praise + satiation rules | **Done** |
| **C** | NPC scan + nearby comments + hunger-staged whispers + approach + look-fixation | **Done** — C1–C5 verified in-game |
| **D** | Audio bank playback (research + implement) | **Done** — D0–D1 Desperate audio; delivery modes verified |
| **E** | Named-victim kill voice + soft Necromantic intimacy hooks | **Done** — E1–E5 |
| **F** | Blade corpse sever (`/` + limb menu + `Actor.Dismember`) | **Done** — verified in-game ([SLICE_F_CORPSE_SEVER.md](SLICE_F_CORPSE_SEVER.md)) |
| **G** | Bed corpse hallucination (sleep spawn + look-away despawn) | **G1 shipped** — verify in-game ([BED_CORPSE_HALLUCINATION.md](BED_CORPSE_HALLUCINATION.md)) |
| **H** | Corpse decay / consume + victim places | Planned — design: [SLICE_H_CORPSE_DECAY.md](SLICE_H_CORPSE_DECAY.md) |
| **I** | Slow hunger stages (days) + peak-hunger wait rewards | Planned |
| **J** | Corpse preserve sync with Necromantic | Planned |
| **K** | Perk gates; optional butcher cell / Cannibal hooks | Planned |
| **L** | Witness support: flee/scream or attack; rumors of the "killer" | Planned |
| **M** | Infamy / serial-killer whispers | Planned |

## Slice A — trigger, toast, hunger, MCM

- [x] Bond on `PickmanGallery01` enter and/or blade acquire/equip.
- [x] Trust line bank + hunger band toasts.
- [x] Hunger 0–100 with AGI/CHA withdrawal stand-in (Necromantic craving pattern).
- [x] MCM: How To Use, Hunger, Voice, Debug.
- [x] Satiation UI copy present; full clear on knife kill reserved for B.

## Slice B — knife kills + satiation

**Status: Done** (verified: blade sates on non-hostile adult females; gun with blade in inventory does not). Regression: [TEST.md](../TEST.md) + `tools/test_blade_detect_contract.py` + MCM **Verify blade detect**.

- [x] Detect kills while weapon is Pickman's Blade (primary: nearby living→dead GoE scan; soft backups: `OnDeath` / hit-tag / combat target).
- [x] **Blade identity (B27):** GoE equipped-slot name / OMOD pair (`Knife` `0x913CA` + bleed `0x1E7C20` + stealth `0x187A10`). Do **not** trust `GetEquippedWeapon` name alone (reports Combat Knife) or LVLI `0x22595F` as the drawn WEAP.
- [x] Valid target: adult **female** non-**essential** human, seen **non-hostile** while alive (Protected settlers **do** count after you aggro them); skips men, hostiles-from-first-sight (raiders), children, teammates, ghoul/SM/synth/robot.
- [x] Only kills with **Pickman's Blade** drawn count; gun with blade only in inventory must **not** sate.

## Slice C — NPC scan + comments + fixation

- [x] **C1** — Periodic Garden of Eden living scan; default adult female non-essential (shared with B kill-watch / filters).
- [x] **C2** — Soft toast comments on nearby **non-hostile** adult women (`NoticeLines.txt`, `{name}` when known). Success path calls `OnNoticeSpoken` (C3 hook). Poll debug dialogs optional (MCM Debug).
- [x] **C3** — Hunger-staged whispers: five editable stage files (`NoticeLines_<Stage>.txt`) chosen by `HungerLevel` band — admiration → infatuation → jealousy → anger → kill-urge — with no-immediate-repeat selection. Files-only (no builtin fallback); GoE2 load + GoE string helpers; per-file MCM load status, load MessageBox, and stage dropdown / force toggle. **Verified in-game** (file load + notice toasts).
- [x] **C4** — Approach / first-enter feel via ambient killscan path (dedicated 0.5s FindActors hammer rejected — silenced the quest). **Verified in-game** with always-on timer arming; auto MessageBoxes removed (MCM Scan nearby keeps its dialog).
- [x] **C5** — Look-fixation POC (**additive — no change to ambient C2/C3 whispers**). Cap 32 FormIDs, save-persisted arrays. **Verified in-game** (incl. sleep recognition).
  - [x] **P1** — Aim edge (GoE camera/activate — not fake `GetCurrentCrosshairRef`) → count + MCM Look fixation. Ambient killscan whispers unchanged; killscan re-arms before tick body (`tools/test_look_fixation.py`).
  - [x] **P2** — Voice by count: 1st silent / 2nd hunger-stage notice line / 3rd+ `RecognitionLines.txt` (`tools/test_recognition_lines.py`).
  - [x] **P3+P4** — Potential Victims (merged): MCM Victims page ↔ FormID table + F4SE `SetDisplayName` (world name) so `{name}` matches aim label; cap 32; lazy re-apply when seen; optional `VictimsHold` RefCollectionAlias (`tools/test_potential_victims.py`).
  - [x] **P5** — Sleep recognition: `SleepRecognitionLines.txt` when 3rd+ look and `GetSleepState() >= 3` (`tools/test_sleep_recognition.py`).

## Slice D — audio

- [x] **D0-POC** — MCM Debug **Play test whisper (EndIt)** → `Sound.Play` on `PW_Whisper_EndIt` (`0x807`).
- [x] **D0.5** — Esp build clones SNDR for every `Desperate_Audio.txt` `.xwm` stem (`PW_Whisper_<Stem>`, `WhisperSndrIds.txt`).
- [x] **D1** — Load `*_Audio.txt`, MCM `iVoiceDelivery` (Toast+Audio / Audio / Toast), same-index `PlayNoticeAudio` on notice path (`tools/test_audio_d1.py`). **Verified in-game.**
- Map keys are **`.xwm`** under `Data/Sound/PickmansWhisper/`. Blank Calm/Restless/Hungry/Starving maps until clips exist.
- Docs: [AUDIO.md](AUDIO.md), [CREATE_SNDR_XEDIT.md](CREATE_SNDR_XEDIT.md).
- Voice features require drawn Pickman's Blade (`IsVoiceWeaponReady` → `IsBladeEquipped`).

## Slice E — named kill voice + soft Necromantic intimacy

Special lines when the player has a personal stake (Potential Victims name) and soft suite hooks with Necromantic. **No** `Necromantic.esp` master; no AAF/sex code in this mod.

- [x] **E1** — Named-victim kill voice: on a valid blade kill, if the victim has a player-assigned Potential Victim name (`GetVictimOverrideName`), speak a dedicated toast + audio from `ModConfig.txt` (text + optional SNDR stem keys) instead of the generic praise line. Later: optional randomized banks. *(toast shipped; uncomment `namedKillAudio` when `.xwm` exists)*
- [x] **E2** — Soft Necromantic intimacy hook: `GetFormFromFile(0x800)` + `RegisterForCustomEvent` `OnNecroSceneStart` / `OnNecroSceneEnd`; named Potential Victim corpse in `akArgs[1]`.
- [x] **E3** — `OnNecroSceneEnd` named-victim voice (shared speaker; mirrors start).
- [x] **E4** — Random intimacy toasts from files: `config/necromantic/Intimacy_Start_Named.txt` / `Intimacy_End_Named.txt` (no ModConfig single-line toast keys). Fail loud if bank missing when the event would speak.
- [x] **E5** — Parallel audio maps `Intimacy_Start_Audio.txt` / `Intimacy_End_Audio.txt` (23+23 relative `.xwm` under `Sound/PickmansWhisper/Necromantic/Start|End`); ESP SNDRs; same-index `iVoiceDelivery` like notice D1. Retire `namedIntimacyAudio`.
- Honor direction rules: not sexual here; soft complementarity only; blade-drawn voice gate still applies.

## Slice F — blade corpse sever

Working note: [SLICE_F_CORPSE_SEVER.md](SLICE_F_CORPSE_SEVER.md). **Done** (verified in-game).

- [x] Aim reticule at a dead adult female; wield **Pickman's Blade**; press **`/`** (`VK_OEM_2` = 191).
- [x] Limb picker via MSG `PW_SeverLimbMenu` (`0x806`) → `Actor.Dismember(part, False, True, False)` (force sever, no BloodyMess gib).
- [x] Skip Necromantic scene latch. Hacksaw / other weapons later.
- [x] Contract: `tools/test_corpse_sever.py`.

## Slice G — bed corpse hallucination

Design + G1: [BED_CORPSE_HALLUCINATION.md](BED_CORPSE_HALLUCINATION.md). Contract: `tools/test_bed_hallucination.py`.

- [x] **G1** — Pre-warm living `LCharRaiderFemale`; wake `SnapIntoInteraction` + `KillSilent` (ragdoll fallback); timed despawn; bond + MCM + cooldown. Optional `BedGiftLines.txt` wake toast.
- On sleep start: spawn disabled vanilla female Actor at bed, silent `Kill()`, place on/beside bed.
- On wake: player finds the corpse; no visible place→ragdoll if timed during sleep fade.
- Track presence via script ref; FO4 Direct LOS (not Skyrim `HasLOS`).
- Despawn on look-away so look-back finds an empty bed.
- MCM Voice toggle + Debug force/clear; no custom corpse mesh.

## Slice H — corpse decay / consume + victim places

Design: [SLICE_H_CORPSE_DECAY.md](SLICE_H_CORPSE_DECAY.md).

Bodies and Victims list should not be immortal. After enough game-days, corpses **decay** (static/gore swap or soft despawn). Optionally **incentivize eating** the corpse (Cannibal / blade action) so the player clears her deliberately — that path **removes her from Potential Victims**.

Tangential foundation: stamp each victim with a **last-known place** (cell + optional coords / MCM label) on name, kill, or butcher, so finding her again (and resolving unloaded refs for decay/eat) is tractable.

- Soft with J (preserve pauses decay) and K (Cannibal stretch).
- Cap stays aligned with Victims (32) unless J raises holds.

## Slice I — slow hunger + peak wait rewards

Stretch the hunger climb so each stage lasts **days** of game time (not a quick meter fill). Reward patience when the player waits until hunger is peaking before killing.

- **Pace:** climb from calm → desperate over at least ~3 game days; prefer ~1 week+ to reach 100% (tunable MCM / config). Stage bands stay the five C3 whisper stages; only the rise rate / thresholds stretch.
- **Peak reward (TBD — draft):** waiting until high hunger (e.g. starving/desperate) before a valid blade kill grants a temporary bonus — candidate: **attribute bonuses that last until hunger drops back to stage 2 (restless)** (or similar clear exit). Exact bonuses / magnitude undecided; design before implement.
- Do **not** break C3 stage file mapping or the verified killscan arming path while tuning rise rate.
- Soft-stack with Necromantic craving feel; no ESP master dependency.

## Slice J — corpse preserve

- `HeldCorpses[]` + soft claim token on knife-kill victims.
- Compatible with Necromantic holds; no ESP master dependency.
- Ephemeral bed-hallucination corpses (Slice G) are **not** long-term hold targets.
- Soft with **H**: preserved / claimed corpses pause or reset decay.

## Slice K — perk / stretch

- Soft-gate or enhance via Lady Killer / Black Widow.
- Optional Cannibal; stretch butcher-shop cell.
- Occult Pact bridges documented only until that mod exists.
- Soft with **H**: Cannibal / blade-eat consume path that clears Victims.

## Slice L — witnesses

NPCs who witness a knife kill (or catch the player mid-crime) react instead of ignoring it.

- **Reaction on witness:** either
  - **Flee** — run in fear / scream / call for help, or
  - **Fight** — turn hostile and attack the player.
- Reuse existing GoE proximity / LOS scanning (kill-watch + `GetActorsDetecting`) to find who actually saw it; gate by distance/line-of-sight so unseen kills stay quiet.
- **L1 (sub) — rumors of the "killer":** witnesses spread talk; other NPCs later reference a killer at large (toast/among-settlers flavor). Foundation for reputation/bounty-style consequences.
- Room to expand later: bounties, faction/settlement reactions, escalating heat, witnesses that must be silenced.
- Honor `.cursor/rules/pickmans-whisper-direction.mdc`: never punish or trigger hostile reactions around essential/protected story NPCs in a way that breaks main quests.

## Slice M — infamy

- Whispers about a new serial killer in the commonwealth
- References to past murders, could include the name of the victim that differs from the name the player gave them, but the player would realize it is "Cindy"
- Whispers could increase after a murder

## Risks

- Audio without dialogue may need F4SE / custom sound forms.
- Essential NPC filters must never break main quests.
- Tone is extreme — keep lines in editable config files.
- Named-kill / Necromantic hooks (E): soft stub + CustomEvents; no `Necromantic.esp` master.
- Corpse sever (F): limb-under-reticule unavailable in Papyrus; MSG menu + `Dismember` must leave gore pieces (no force-explode / no BloodyMess gib).
- Bed hallucination (G): sleep timing, bed Z clipping, LOS false-triggers on wake camera (see Slice G doc).
- Corpse decay / places (H): unloaded Actor refs; decay vs J preserve race; eat must clear Victims without orphaning place data; exterior place labels are fuzzy.
- Hunger pacing (I): long climbs must stay fun (not “forgot the mod is installed”); peak rewards must not soft-lock or break SPECIAL balance.
- Witnesses (L): reliable "who actually saw it" detection (LOS/distance) without false positives; forcing flee/hostile AI states cleanly; not aggroing essential/protected NPCs.
