# Roadmap — Pickman's Whisper

Status source of truth for this repo. Suite framing: [DIRECTION.md](DIRECTION.md).


| Slice | Deliverable                                                                                    | Status                                                                                                                                               |
| ----- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A** | Trigger on house/knife; toast-only voice; hunger meter; MCM                                    | **Shipped (0.1.0)**                                                                                                                                  |
| **B** | Kill-with-knife praise + satiation rules                                                       | **Done**                                                                                                                                             |
| **C** | NPC scan + nearby comments + hunger-staged whispers + approach + look-fixation                 | **Done** — C1–C5 verified in-game                                                                                                                    |
| **D** | Audio bank playback (research + implement)                                                     | **Done** — D0–D1 Desperate audio; delivery modes verified                                                                                            |
| **E** | Named-victim kill voice + soft Necromantic intimacy hooks                                      | **Done** — E1–E5                                                                                                                                     |
| **F** | Blade corpse sever (`/` + limb menu + `Actor.Dismember`)                                       | **Done** — verified in-game ([SLICE_F_CORPSE_SEVER.md](SLICE_F_CORPSE_SEVER.md))                                                                     |
| **G** | Bed corpse hallucination (sleep spawn + look-away despawn)                                     | **G1 shipped** — verify in-game ([BED_CORPSE_HALLUCINATION.md](BED_CORPSE_HALLUCINATION.md))                                                         |
| **H** | Corpse decay (body + face) → eat urge → reward                                                 | **P1 done**; next **P2** MCM stage change — [SLICE_H_CORPSE_DECAY.md](SLICE_H_CORPSE_DECAY.md) · face art [Decay_Head_Guide.md](Decay_Head_Guide.md) |
| **I** | Desperate hunger: rename nearby NPCs (knife-voice suffix)                                      | **I1–I2 verified in-game** — [SLICE_I_DESPERATE_RENAME.md](SLICE_I_DESPERATE_RENAME.md)                                                              |
| **J** | Retire KillerScan + thin Main via Alias scripts (e.g. MCM Alias)                               | **J1 implemented** — awaiting in-game confirm                                                                                                        |
| **K** | Victim “beat before kill” — temp essential + fight back (unarmed exception)                    | Planned (was Slice Q / earlier J; code/comments may still say J or Q)                                                                                |
| **L** | Slow hunger stages (days) + Calm-state AGI/CHA reward                                          | **Done** — awaiting in-game confirm                                                                                                                  |
| **N** | Perk gates (Lady Killer hard-gates Bond); optional butcher cell / Cannibal hooks                | **Done** — awaiting in-game confirm                                                                                                                  |
| **O** | Witness support: flee/scream or attack; rumors of the "killer"                                 | Planned                                                                                                                                              |
| **P** | Infamy / serial-killer whispers                                                                | Planned                                                                                                                                              |
| **Q** | Private cells + quests (Combat Zone stage, Culte des Ghouls, butcher shop, Pickman house home) | Planned                                                                                                                                              |
| **R** | First blade acquire (inventory) — quest beat when the knife enters the player’s hands          | **R1/R2 done** — verified in-game; R3 (stop-carrying policy) open                                                                                    |
| **S** | Force Trade — activate-choice inventory + one-time strip + slave pacify                        | **Done** — verified in-game                                                                                                                          |
| **T** | Slavery — Enslave/Free follow + collar gate; killable (not vanilla companion)                  | **Implemented** — awaiting in-game confirm                                                                                                           |
| **V** | Stronger patience boon — "permanent" (temporal) SPECIAL raise + perk grant (e.g. Intimidation)  | Idea only — not scheduled                                                                                                                            |
| **W** | Execute — instant kill on a living victim (Decapitate / Smash Head In), new \\ hotkey           | **Done** — awaiting in-game confirm                                                                                                                  |




## Slice A — trigger, toast, hunger, MCM

- [x] Bond on blade acquire/equip. Hard rule: Bond means the player first acquired the blade — it can never start before that, structurally enforced inside `StartBond` itself via `PlayerHasBlade()` (not just by every caller happening to already gate on it), so a future caller (or the MCM debug force-bond button) can't accidentally start Bond with no blade ever owned. (Originally also triggered on `PickmanGallery01` enter alone — removed: confusing to see "bond active" on an old save standing in the Gallery before ever owning the blade.)
- [x] Gallery-entry welcome dialog decoupled from Bond entirely — `bondIntroGreeting`'s once-ever `Debug.MessageBox` now fires from `AnnounceGalleryIntro`, triggered by `RunBondPoll`'s `SeenGallery` latch on first Gallery entry, not from `StartBond`. The line is Gallery-flavored ("welcome to the room"), Bond is blade-flavored ("you found me") — the mechanics no longer need to share a trigger. `AnnounceBladeAcquire` (Slice R1) also switched from `Debug.Notification` to `Debug.MessageBox` for the same guaranteed-seen reasoning. MCM debug button renamed "Test: reset bond + gallery intro (debug)" — resets both `BondStarted` and `SeenGallery` so either can be retested independently.
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
- [x] **C4** — Approach / first-enter feel via ambient KillerScan path (dedicated 0.5s FindActors hammer rejected — silenced the quest). **Verified in-game** with always-on timer arming; auto MessageBoxes removed (MCM Scan nearby keeps its dialog).
- [x] **Killer Orchestrator (v1.3.0)** — sole `PickmansWhisperKillerScanScript` → TargetSnapshot → Voice sync + NoWait knife/cadence/Victims/CorpseDecay(H)/BedGift. Replaces WorldScan + multi-timer arming. Contract: `tools/test_killer_scan_bus.py`. Victims MCM decay Set/Reset overlay nudge parked → **H P2**.
- [x] **C5** — Look-fixation POC (**additive — no change to ambient C2/C3 whispers**). Cap 32 FormIDs, save-persisted arrays. **Verified in-game** (incl. sleep recognition).
  - [x] **P1** — Aim edge (GoE camera/activate — not fake `GetCurrentCrosshairRef`) → count + MCM Look fixation. Ambient KillerScan whispers; KillerScan re-arms before tick body (`tools/test_look_fixation.py`).
  - [x] **P2** — Voice by count: 1st silent / 2nd `RecognitionLines.txt` / 3rd+ hunger-stage notice (`tools/test_recognition_lines.py`). Ladder ends on sharper C3 lines.
  - [x] **P3+P4** — Potential Victims (merged): MCM Victims page ↔ FormID table + GoE2 `SetDisplayName` (world name) so `{name}` matches aim label; cap 32; lazy re-apply when seen; optional `VictimsHold` RefCollectionAlias (`tools/test_potential_victims.py`).
  - [x] **Manual rename (player-facing)** — Victims page "New name" + "Apply name" lets the player give ANY eligible target — including FO4's nameless generic NPCs (world label "Settler"/"Resident") — a real, permanent name. `ApplyVictimName` (`PickmansWhisperMainQuestScript.psc`) rejects generic/junk input (can't rename someone *to* "Settler"/"Resident"), then `GardenOfEden2.SetDisplayName` makes it her actual world/HUD name from then on, and it's what fills `{name}` in every subsequent whisper/toast/kill line. Same cap-32 FormID table as the rest of Potential Victims.
  - [x] **P5** — Sleep recognition: `SleepRecognitionLines.txt` when 2nd look and `GetSleepState() >= 3` (`tools/test_sleep_recognition.py`).



## Slice D — audio

- [x] **D0-POC** — MCM Debug **Play test whisper (EndIt)** → `Sound.Play` on `PW_Whisper_EndIt` (`0x807`).
- [x] **D0.5** — Esp build clones SNDR for every `Desperate_Audio.txt` `.xwm` stem (`PW_Whisper_<Stem>`, `WhisperSndrIds.txt`).
- [x] **D1** — Load `*_Audio.txt`, MCM `iVoiceDelivery` (Toast+Audio / Audio / Toast), same-index `PlayNoticeAudio` on notice path (`tools/test_audio_d1.py`). **Verified in-game.**

- Map keys are `.xwm` under `Data/Sound/PickmansWhisper/`. Blank Calm/Restless/Hungry/Starving maps until clips exist.
- Docs: [AUDIO.md](AUDIO.md), [CREATE_SNDR_XEDIT.md](CREATE_SNDR_XEDIT.md).
- Voice features require owning Pickman's Blade (`IsVoiceWeaponReady` → `PlayerHasBlade`); kills / butcher still require it drawn (`IsBladeEquipped`).



## Slice E — named kill voice + soft Necromantic intimacy

Special lines when the player has a personal stake (Potential Victims name) and soft suite hooks with Necromantic. **No** `Necromantic.esp` master; no AAF/sex code in this mod outside [Slice U](SLICE_U_SLAVE_SCENE.md) (Slavery scene).

- [x] **E1** — Named-victim kill voice: on a valid blade kill, if the victim has a player-assigned Potential Victim name (`GetVictimOverrideName`), speak a dedicated toast + audio from `ModConfig.txt` (text + optional SNDR stem keys) instead of the generic praise line. Later: optional randomized banks. *(toast shipped; uncomment* `namedKillAudio` *when* `.xwm` *exists)*
- [x] **E2** — Soft Necromantic intimacy hook: `GetFormFromFile(0x800)` + `RegisterForCustomEvent` `OnNecroSceneStart` / `OnNecroSceneEnd`; named Potential Victim corpse in `akArgs[1]`.
- [x] **E3** — `OnNecroSceneEnd` named-victim voice (shared speaker; mirrors start).
- [x] **E4** — Random intimacy toasts from files: `config/necromantic/Intimacy_Start_Named.txt` / `Intimacy_End_Named.txt` (no ModConfig single-line toast keys). Fail loud if bank missing when the event would speak.
- [x] **E5** — Parallel audio maps `Intimacy_Start_Audio.txt` / `Intimacy_End_Audio.txt` (23+23 relative `.xwm` under `Sound/PickmansWhisper/Necromantic/Start|End`); ESP SNDRs; same-index `iVoiceDelivery` like notice D1. Retire `namedIntimacyAudio`.

- Honor direction rules: not sexual here; soft complementarity only; blade-drawn voice gate still applies.



## Slice F — blade corpse sever

Working note: [SLICE_F_CORPSE_SEVER.md](SLICE_F_CORPSE_SEVER.md). **Done** (verified in-game).

- [x] Aim reticule at a dead adult female; wield **Pickman's Blade**; press `/` (`VK_OEM_2` = 191).
- [x] Limb picker via MSG `PW_SeverLimbMenu` (`0x806`) → `Actor.Dismember(part, False, True, False)` (force sever, no BloodyMess gib).
- [x] **Cut Off Tits** — slot-33 mutilated body ARMO + weighted MISC prop (Havok drop). Prop cut surface: vanilla `Materials\Gore\GoreHumanLeg.BGSM` (see [SLICE_F](SLICE_F_CORPSE_SEVER.md)). **Verified in-game** — falls, rests, loots, pushable. Build pipeline: [Severed_Part_Guide.md](Severed_Part_Guide.md).
- [x] Skip Necromantic scene latch. Hacksaw / other weapons later.
- [x] Contract: `tools/test_corpse_sever.py`.



## Slice G — bed corpse hallucination

Design + G1: [BED_CORPSE_HALLUCINATION.md](BED_CORPSE_HALLUCINATION.md). Contract: `tools/test_bed_hallucination.py`.

- [x] **G1** — SleepStart spawn `DiamondCityResidentF01NoodleMarket` (unnamed Resident); wake `SnapIntoInteraction` + `KillSilent` (ragdoll fallback); own `TIMER_BED_DESPAWN`; bond + blade + MCM + cooldown. Optional `ModConfig.txt` `bedGiftWakeToast`. Self-contained on `PickmansWhisperBedGiftScript` (no KillerScan).

- On sleep start: spawn disabled vanilla female Actor at bed (place+disable; no LooksMenu on sleep stack).
- On wake: player finds the corpse; pose via BedGift timer; no sync Wait on SleepStop.
- Despawn via BedGift oneshot timer after present.
- MCM Voice toggle + Debug force/clear; no custom corpse mesh.



## Slice H — corpse decay (body + face) / consume + victim places

Design: [SLICE_H_CORPSE_DECAY.md](SLICE_H_CORPSE_DECAY.md). Face art: [Decay_Head_Guide.md](Decay_Head_Guide.md). Soft with **N** (Cannibal). Corpse preserve left to an external mod. Cap aligns with Victims (32).

**Merged former face-only slice** (FaceGen-preserving slot-54 face decals) into this slice — body overlays + face ARMO share the same stage clock.

**Visual:** LooksMenu overlays + **ROF DeadOverlays** DeathMarks (`DecayWoundOverlays.txt`) + slot-54 face decal ARMO (`DecayFaceStages.txt`). `PlayImpactEffect` **retired**. Soft deps — no ROF/LooksMenu ESP master. SPID not required.

- [x] **P0.1** — MCM Debug wound lab (sticky corpse + template/tint/count apply). Verify in-game.
- [x] **P0.2** — Wound Lab: Porcupine Scars/SkinTexture stepper + apply/all (stacks with DeathMarks). Soft dep `porcOverlays.esl`. Face lab: Scripted Face Tints Damage/Boxer bruises (`DecayFaceOverlays.txt`, soft `SFT.esp`).
- [x] **P1** — Apply DeathMarks wound overlays on the bed-gift corpse (POC; no kill clock). Verify in-game.
- [x] **P2** — **Deliver working Corpse Decay stage change in MCM** (Set/Reset = kill clock; KillerScan sync applies overlays). Stage 0 body none; Pallor (1) tinted SkinTexture_16. Implemented — awaiting in-game confirm.
- [x] **P3** — Stamp kill game-time + ModConfig `startHours` thresholds (0 / 0.25 / 2 / 48 / 96); `SyncDecayForKnifeCorpse` via KillerScan → CorpseDecay `CallFunctionNoWait` (not on voice stack). SFT Boxer face stays lab-only; stage face ARMO rides the clock. Coded — verify in-game.
- [x] **P4** — At max stage (4), toast urging the player to eat her before she is too ripe. Cannibal-perk gated, ModConfig `eatRipeCorpseToast`, once-per-game-hour. Coded — awaiting in-game confirm.
- [x] **P5** — Reward eating the corpse at that peak stage and clear her from Potential Victims.
- [x] **P6** — Face decal art finish: photo-edit stage-0 DDS toward putrefaction; **one asset set per ModConfig stage 0–4** (stage 0 verified in-game). Hard no slot-32 FaceGen swap. ESP builder must preserve ARMO FormIDs. Guide: [Decay_Head_Guide.md](Decay_Head_Guide.md).

Victim **places** (last-known cell/label) remain a tangential foundation for unloaded refs / MCM — not required for P1–P5 visuals.

## Slice I — desperate hunger rename (knife voice)

Design: [SLICE_I_DESPERATE_RENAME.md](SLICE_I_DESPERATE_RENAME.md). Contract: `tools/test_desperate_rename.py`.

At notice stage **desperate** (hunger band 4), the knife voice rewrites how nearby women read — world name + `{name}` in notice toasts.

- [x] **I1** — KillerScan `ScanAlive` → GoE2 `SetDisplayName` append ModConfig `desperateNameSuffix` (e.g.  `Dumb Bitch`). Idempotent; strip when stage drops. Skip essential / notice-reject. Logic on `PickmansWhisperDesperateRenameScript`. **Verified in-game.**
- [x] **I2** — `GetActorDisplayName` / notice `{name}` show the suffixed label while desperate (toast matches mouseover). **Verified in-game** (world name confirmed).
- [ ] **I3** — Optional bank of suffixes / MCM toggle (later).

Honor direction: never rename **essential** story NPCs. Editable suffix in `ModConfig.txt` only (no hard-coded line bank mirror).

## Slice J — retire KillerScan + Alias refactor (later)

Architecture cleanup after the event-driven cloak / OnHit / OnDeath / KillReward path is solid. Do **not** start until that path is confirmed in-game. Supersedes the old “KillerScan → true event bus” Later item — the goal here is removal, not a prettier bus.  Eddie: It is a prettier bus though. This feature began with this query: "fallout 4 I want to build a cloak of fear aura mod" on July 28th. This is a substantial refactor of the project.

- [x] **J1 — Deprecate and remove KillerScan** — **J1 implemented** — awaiting in-game confirm. Retire `PickmansWhisperKillerScanScript` and the poll-driven TargetSnapshot / cadence fan-out once notice, fixation, decay sync, bed gift, and related listeners are driven by events (or thin dedicated hosts). Update contracts (`test_no_killer_scan.py`, arming docs) so they no longer require the scanner. Protect proven load/arm behavior until the replacement is verified — then delete, don’t leave a zombie poller.
- [x] **J2 — Thin MainQuestScript via Alias scripts** — Move more feature/MCM surface out of `PickmansWhisperMainQuestScript` onto quest Alias scripts (same pattern as ModConfigAlias, KillRewardAlias, PlayerAlias). Example: MCM CallFunction / panel refresh into its own Alias. Main stays a thin router; Caprica cast-through-Quest rule still applies. Follow [modular-feature-scripts](.cursor/rules/modular-feature-scripts.mdc).



## Slice K — victim beat-before-kill (temp essential)

Formerly roadmap **Slice Q** (and earlier **J**; scripts/tests may still say J / Q / J1–J5). Let the player **pretend to beat** a qualified woman before finishing her with the knife — she won’t die during the scuffle and ideally **fights back**. Soft with Victims (C5) and knife-kill rules (B).

- [x] **K1 — MCM Victims: mark essential** — On a Potential Victim (or aimed eligible NPC), toggle “can’t be killed” for the beat fantasy. Clear via K5 / MCM off / blade kill path.
- [x] **K2 — Auto on unarmed attack** — If the player attacks a **qualified** NPC **without a weapon armed** (fists / no drawn weapon), auto-enter the same temp-essential + fight-back state. **Exception:** Pickman's Blade need **not** be drawn for this path (blade still required later to sate / praise).
- [x] **K3 — Fight back** — Aggro / combat so she resists instead of crumpling; exit cleanly when essential is cleared so a later blade kill can work.
- [x] **K4 — Qualification** — Same spirit as notice/kill: adult **female**, human, **non-hostile** (at first contact); skip story essentials, children, teammates, non-humans. Never leave a shared `ActorBase` permanently essential (FO4 essential is base-level — design must be ref-safe / restore prior state).
- [x] **K5 — Clear essential on rearm** — When the player **rearms any weapon** (draws / equips a weapon again after the unarmed beat), mark her **unessential** (restore prior state) so she can be finished with the blade.

Honor direction: this is **player-opted / auto beat** essential on eligible targets only — not a loophole to immortalize story NPCs.

## Slice L — slow hunger + Calm-state reward

Stretch the hunger climb so each stage lasts **days** of game time (not a quick meter fill). Reward the player for being sated (Calm) instead of just neutral.

- [x] **Pace** — `GetHungerTimeGainPerHour`'s default/fallback (Papyrus fallback + `fTimeGain:Hunger` MCM slider default + both `settings.ini` copies) currently **1.0/hr** (was 5.0, then 0.5 — 0.5 turned out to drag too much per live feedback): ~25h per 25-point band (Calm/Restless), ~20h per 20-point band (Hungry/Starving) — roughly a day per stage; 0→100 ~4.2 game-days, calm→desperate (90) ~3.75 days. Bands are unequal width so a single rate can't make every stage exactly 24h; 1.0 is the closest clean round number. Still fully MCM-tunable (slider unchanged, 0–15 step 0.5). The delta-based climb math in `RunHungerTick` (already correct — scales with real elapsed game-time, handles sleep/fast-travel) was not touched; this is a default-value change only. Stage bands (25/50/70/90, the five C3 whisper stages) untouched — nothing depends on climb rate, only on `HungerLevel`'s current value.
- [x] **Calm-state reward, patience-gated** (the "peak wait" draft, realized) — `SyncCalmBonusSpell` grants a flat **+4 AGI / +4 CHA** (`ModValue`, no real Spell/MGEF, same mechanism as the existing hunger-addiction penalty) while `HungerLevel < 25.0` (Calm) **AND** `CalmBonusEligible`, cleared the instant either isn't true. Mirrors `SyncHungerAddictionSpell`'s exact level-based recompute-and-diff shape (no timer, no edge-detection) and `HungerSpecialPenaltyDepth`'s depth-capped-at-1 save-safety bookkeeping (`CalmBonusApplied`/`CalmBonusDepth`), wired into the same 5 call sites (`HandleGameResume`, `RunHungerTick` x2, `ApplyHungerDelta`, `SatiateHunger`) so it self-corrects on every hunger mutation and on load. Calm (`<25`) and Addicted (`>=` `fAddictedAt:Hunger`, MCM floor 25) can never overlap, so the penalty already clears itself the instant the bonus would apply — no extra "remove the penalty" step needed. Magnitude and threshold hardcoded (no MCM slider, matching the penalty's own hardcoded -1/-1); no dedicated repair-stack debug button (the existing "Test: satiate hunger (debug)" button already exercises the full apply path via `SatiateHunger`; `ShowHungerInfo` surfaces `CalmBonusApplied`/`CalmBonusEligible` and live patience-hours progress). Contract: `tools/test_hunger_pace_calm_bonus.py`.
  - **Patience gate:** the bonus is earned, not automatic — only granted if hunger was **continuously** at/above Desperate (`HungerLevel >= 90`) for at least **`CALM_BONUS_PATIENCE_HOURS` = 13 game-hours** immediately before the kill/satiation. `SyncDesperateTracking` (same recompute-and-diff shape, no edge-detection) stamps `DesperateEnteredGameTime` the moment Desperate is reached and clears it the moment hunger drops back below 90 before a kill consumes it — no cumulative credit across dips. `SatiateHunger` reads that timestamp into `CalmBonusEligible` *before* resetting `HungerLevel` to 0 (order matters — `SyncDesperateTracking` would otherwise clear the timestamp first). Satiation itself (hunger reset, sated window, `BondIntensity`, kill-crediting) stays entirely unconditional on hunger level or patience, exactly as before — only the bonus is gated.



## Slice N — perk / stretch

- [x] **Lady Killer hard-gates Bond** — `StartBond` requires `PlayerHasLadyKillerPerk()` (any of the 3 additive ranks, same shape as `PlayerHasCannibalPerk()`) in addition to the existing `PlayerHasBlade()` rule (Slice R). Without Lady Killer, owning/equipping the blade does nothing — hunger stays locked (`IsHungerUnlocked()` is a pure alias for `BondStarted`). The perk check is LIVE, not a one-time snapshot: `RunBondPoll` already re-calls `StartBond("trigger")` every ~4s real-time whenever `!BondStarted`, so acquiring Lady Killer later (even long after the blade) unlocks Bond on the very next poll tick — no new polling loop needed, `BondStarted` stays a true one-way latch. FormIDs (`LadyKiller01/02/03`) verified directly against `Fallout4.esm` PERK records, not guessed. MCM Hunger page distinguishes "locked (needs Lady Killer perk)" from the plain "locked (visit gallery or take the blade)" when only the perk is missing. Contract: `tools/test_lady_killer_bond_gate.py`.
- Not gated on Cannibal — considered and rejected as too restrictive. Cannibal already has its own, separate role: the eat-ripe-corpse Endurance bonus (Slice H P5, `ateRipeCorpseEndBuffAmount/MaxDelta/Hours` — currently +2 END per eat, capped at +4, decaying 2 game-hours after the last eat) relies on `PlayerHasCannibalPerk()` as *detection* logic (no vanilla "ate a corpse" event exists; the perk possession is what distinguishes a Cannibal heal from a Stimpak heal), not a Bond gate.
- Black Widow noted alongside Lady Killer in earlier drafts but not wired — same-gender-only concept doesn't apply the same way; left for a future decision if ever revisited.
- Occult Pact bridges documented only until that mod exists.
- Soft with **H**: Cannibal / blade-eat consume path that clears Victims (clear body + face decay visuals first).



## Slice O — witnesses

NPCs who witness a knife kill (or catch the player mid-crime) react instead of ignoring it.

- **Reaction on witness:** either
  - **Flee** — run in fear / scream / call for help, or
  - **Fight** — turn hostile and attack the player.
- Reuse existing GoE proximity / LOS scanning (kill-watch + `GetActorsDetecting`) to find who actually saw it; gate by distance/line-of-sight so unseen kills stay quiet.
- **O1 (sub) — rumors of the "killer":** witnesses spread talk; other NPCs later reference a killer at large (toast/among-settlers flavor). Foundation for reputation/bounty-style consequences.
- Room to expand later: bounties, faction/settlement reactions, escalating heat, witnesses that must be silenced.
- Honor `.cursor/rules/pickmans-whisper-direction.mdc`: never punish or trigger hostile reactions around essential/protected story NPCs in a way that breaks main quests.



## Slice P — infamy

Serial-killer reputation that builds as the player leaves a trail. Soft with **O** (witnesses / rumors) and **Q** (public performances). Honor direction: never urge or reward killing **essential** / protected story NPCs.

- [ ] **P1 — Infamy on non-essential kill (named worth more)** — When the player kills a **non-essential** NPC (blade kill path / same gates as Slice B where applicable), increase an infamy score (or stage). **Named** victims raise it **more** than unnamed; essentials / story-protected never raise infamy. Persist across saves; MCM Debug readout optional.
- [ ] **P2 — Infamy-staged whispers** — Line banks that escalate with infamy (new serial killer in the Commonwealth → references to past murders). Optional: world/rumor name that differs from a Potential Victim override so the player still recognizes “Cindy.”
- [ ] **P3 — Whisper cadence after murder** — Ambient / notice pressure ramps shortly after an infamy-raising kill (cooldown so it does not spam).



## Slice Q — private cells + quests (stage, cult, shop, home)

Large stretch: custom (or heavily edited) **private cells** and quests that turn the knife voice into a public/secret economy of murder. Soft with **N** (butcher / Cannibal) and **P** (infamy). Design before ESP sprawl — each pillar can ship as its own sub-slice.

- [ ] **Q1 — Combat Zone stage of horror** — Partner with **Tommy Lonegan** at the Combat Zone; offer “performances” where the player murders captured slaves before an audience. Transform the Combat Zone into a stage of horror (crowd reaction, payment, optional return gigs).
- [ ] **Q2 — Culte des Ghouls** — Secret society of elites who **pay to watch** the player commit murder; they are secret cannibals and want to **feast on the victim afterward**. Private salon / cellar cell; invitation / membership progression TBD.
- [ ] **Q3 — Butcher shop** — Player-openable butcher shop (cell + vendor / workbench loop). Soft-stack with Slice **N** Cannibal / butcher-shop stretch — decide whether Q3 *is* that stretch or a fuller shop quest.
- [ ] **Q4 — Pickman's house as player home** — Make **Pickman's Gallery / house** a proper player home (ownership, storage, bed, safe return). Likely the **priority** pillar of Q; may unlock before or alongside Q1–Q3.

Honor direction: no AAF/sex content here beyond the scoped [Slice U](SLICE_U_SLAVE_SCENE.md) slavery scene; never break essential/protected story NPCs; keep line banks editable; soft complementarity with Necromantic only (no hard master).

## Slice R — first blade acquire

Today `OnItemAdded` / `OnItemRemoved` on **MainQuestScript** only flip ownership / bond flags. Drawn-weapon detection stays on PlayerAlias; **inventory ownership belongs on Main** (quest-level “you have the knife” state), not the alias.

Design a real first-acquire beat when Pickman’s Blade first enters the player inventory.

- [x] **R1 — First acquire moment** — `MarkOwnedBlade` (hooked off `Actor.OnItemAdded`, plus `RunBondPoll`'s fallback detection net) fires `AnnounceBladeAcquire()` the one time `SeenBlade` flips True — a true one-time event. Message dialog (`Debug.MessageBox`, not a toast) + optional audio from ModConfig `bladeAcquireToast`/`bladeAcquireAudio` (editable banks). Unlike every other voice line, the dialog half is NOT gated on `IsVoiceWeaponReady` or `IsVoiceEnabled` — fires at acquire regardless of drawn state or the master voice toggle (only `iVoiceDelivery` mode applies); the audio half still requires blade-in-hand (shared `PlayWhisperXwmByFile` machinery). Distinct from Gallery enter (`SeenGallery`/`AnnounceGalleryIntro`) and from later re-equips (R2). Contract: `tools/test_blade_acquire.py`.
- [x] **R2 — Re-acquire vs first** — Already covered by the `SeenBlade` latch `MarkOwnedBlade` guards on — later adds (lost and found, console, stash) all route through the same function but the `!SeenBlade` branch (and therefore `AnnounceBladeAcquire`) only ever runs once per save. No separate quieter "knife returned" line added.
- [ ] **R3 — Stop carrying (open)** — Unclear what should happen if the player drops, stores, or otherwise stops carrying the blade: mute voice only, freeze hunger, full “quest paused,” keep ownership forever once claimed, etc. Decide before coding removal side effects beyond today’s `OwnedPickmansBlade` clear.

**R1/R2 confirmed in-game** (2026-08-10): first-acquire `MessageBox` fires correctly on genuine first blade acquire; `DebugResetBond` ("Test: reset bond + gallery intro (debug)") correctly clears both `BondStarted` and `SeenGallery` for retesting. R3 (stop-carrying policy) remains open — not part of what shipped here.

Honor direction: editable lines; no essential-NPC pressure; blade still gates kills / satiation when drawn.

## Slice S — Force Trade (victim inventory)

Activate-choice **Force Trade** on eligible living NPCs (perk beside Talk). Soft with beat-before-kill (**K**) and Potential Victims (**C5**). Contract: `tools/test_victim_trade.py`. Config: `ModConfig.txt` `victimTradeMinCha` (SSOT).

- [x] **S1 — Perk activate choice** — PERK `PW_VictimTradeActivate` Add Activate Choice labeled **Force Trade**; CTDA living only (`GetDead == 0`) so it does not steal Cannibal **Eat Corpse** on corpses. Fragment → Main `TryForceVictimTradeFromActivate`. Modular `PickmansWhisperVictimTradeScript` + perk script; not a hotkey.
- [x] **S2 — Gates** — Living; `IsValidTarget` with hostiles allowed for trade; calm hunger (`HungerLevel` below calm max); player CHA ≥ `victimTradeMinCha`. Fail loud via toast/trace when blocked.
- [x] **S3 — Inventory UI** — `OpenInventory(True)` (not `ShowBarterMenu` — empty panes on non-vendors).
- [x] **S4 — One-time strip per NPC** — First Force Trade: empty OTFT `SetOutfit` + `UnequipAll` so outfit-locked default gear is lootable; latch by FormID (cap 32). Later Force Trades skip strip so gear the player put on her stays equipped. Never strip on ContainerMenu close.
- [x] **S5 — Slave pacify on close** — After menu close, if inventory item name contains `slave` (case-insensitive): stop combat/alarm, clear attack-on-sight, raise relationship, evaluate package + toast; then `SyncSlaveryFromSlaveGear` (Slice **T**).

Honor direction: never urge/reward essential story kills; living-only activate so corpse eat stays available.

## Slice T — Slavery

Enslave a living eligible NPC who has slave gear so she **follows and teleports** with the player. Not a vanilla companion (`CurrentCompanionFaction`); remains a Whisper victim (notice / blade kill / beat-before-kill). Contract: `tools/test_slavery.py`. Config: `ModConfig.txt` `slaveryMinCha` (SSOT).

- [x] **T1 — Perk Enslave / Take Her** — PERK `PW_SlaveryActivate` living-only activate choices; fragment → Main → `PickmansWhisperSlaveryScript`. "Take Her" replaced the original "Free" label — see [Slice U](SLICE_U_SLAVE_SCENE.md); direct one-click free moved to an MCM button (`PickmansWhisperVictimsScript.MCMFreeAimedSlave`).
- [x] **T2 — Slave-gear gate** — Inventory item name contains `slave` (SSOT on Slavery script). Auto after Force Trade close; manual Enslave also requires calm hunger + CHA ≥ `slaveryMinCha`.
- [x] **T3 — Follow without companion faction** — `SetPlayerTeammate(True, False, False)`; latch `Slave` FormID; one at a time; never `SetEssential` here.
- [x] **T4 — Kill / whisper eligibility** — `IsValidTarget` allows our slave teammate; still rejects other teammates and `CurrentCompanionFaction`.
- [x] **T5 — Cell warp** — PlayerAlias `OnLocationChange` → `WarpSlaveToPlayerIfNeeded` (`MoveTo` if unloaded / far).

**Status: Implemented — awaiting in-game confirm.**

## Slice U — Slave Scene (AAF)

Deliberate, scoped exception to the "no AAF" direction rule (see [DIRECTION.md](DIRECTION.md)) — a real two-actor AAF scene between the player and an already-enslaved NPC, replacing the old "Free" activate choice. Reference implementation: `D:\GitHub\aaf-necromantic` (same author, same AAF Papyrus API) for the CTD-avoidance patterns this reuses. Contract: `tools/test_slave_scene.py`. Config: `ModConfig.txt` `aafSlaveSceneDurationSeconds` / `aafSlaveSceneIncludeTags` (SSOT — tag-based AAF position auto-select, no hand-curated position-ID list since installed AAF packs vary per user). Full design doc: [SLICE_U_SLAVE_SCENE.md](SLICE_U_SLAVE_SCENE.md).

- [x] **U1 — Perk label swap** — `PW_SlaveryActivate`'s "already a slave" choice relabeled **Take Her**; `PickmansWhisperSlaveryPerkScript.OnEntryRun` routes it to `TryStartSlaveSceneFromActivate` instead of `TryFreeSlaveFromActivate`.
- [x] **U2 — Two-actor AAF scene** — New `PickmansWhisperSlaveSceneScript`; `actors = new Actor[2]` (player + target, unlike Necromantic's solo `new Actor[1]`); `settings.position = ""` + `settings.includeTags` from ModConfig (tag-based auto-select).
- [x] **U3 — CTD-avoidance parity** — Interior-only by default (MCM `bAllowExteriorSlaveScene:Debug` override), `EnsureAAFStoppedForRestart` before every start, watchdog poll + hard max-duration timer (`OnSceneEnd` is flaky), careful event re-registration on `OnAAFReady`.
- [x] **U4 — MCM status / cancel / free** — Victims page status row (`sSlaveScene`) + "Free (no scene)" button (`MCMFreeAimedSlave`, direct one-click free now that the activate menu no longer has one); Debug page exterior-allow toggle + "Cancel slave scene" button.
- [x] **U5 — Docs reversal** — [DIRECTION.md](DIRECTION.md) / this file's "no AAF" rules scoped to name this one exception explicitly rather than left contradictory.

**Status: Implemented — awaiting in-game confirm (cannot verify actual AAF scene start/CTD behavior without a live AAF install + animation packs; static checks only confirm the code is wired correctly).**

## Slice V — stronger patience boon (idea only, not scheduled)

Draft idea, not designed or implemented — something to work on later, not part of the current Slice L patience boon (`SyncCalmBonusSpell`, +4 AGI/CHA, `CalmBonusEligible` gate).

- Instead of (or as a stronger tier above) the current temporary +4 AGI/CHA: a "permanent" SPECIAL point raise, plus grant a perk (Lady Killer/Black Widow-adjacent candidate: **Intimidation**, unverified — no FormID looked up yet).
- "Permanent" is in quotes deliberately — per the user, this should still be **temporal, like the current boon** (reversible/expiring), not a true forever change to the player's base SPECIAL. Exact meaning of "permanently raise a SPECIAL attr" while also being temporal needs to be resolved before design: candidates include raising the ActorValue base (not just a ModValue delta, unlike the current Calm bonus) for the duration, or simply a much longer/harder-to-lose expiry condition than "leaving Calm."
- Perk grant/removal would need the same idempotent apply/clear + save-safety bookkeeping shape already established for `HungerSpecialPenaltyDepth`/`CalmBonusDepth` (`Actor.AddPerk`/`RemovePerk`, not `ModValue` — different mechanism than the current SPECIAL bonus).
- Open questions: what earns this tier (longer patience threshold than 13h? multiple patience-boon kills in a row? something else)? Does it stack with or replace the existing +4 AGI/CHA boon? Which perk (Intimidation vs. something else)? Exact SPECIAL point(s) affected?

## Slice W — Execute (instant kill on a living victim)

Leverages the existing corpse-sever gore mechanism (Slice F) but applied to a still-LIVING, eligible victim instead of a corpse — an instant kill via **Decapitate** or **Smash Head In**. New hotkey (`\`), new script, new MSG menu — zero changes to the existing corpse-sever feature. Contract: `tools/test_execute_kill.py`.

- [x] **W1 — New isolated script** — `PickmansWhisperExecuteScript` (extends `Quest`, attached to Main's VMAD like every other feature script) owns all aim/menu/weapon-check/kill logic. Reaches `MainQuestScript`/`VictimsScript`/`CorpseDecayScript` only via the established `(Self as Quest) as X` sibling-cast pattern (`Main()`/`Victims()`/`CorpseDecay()` accessors) — no logic added to `MainQuestScript` beyond a 3-line `Execute()` cast, a thin `TryExecuteAimedVictim()` forwarder, and one small `IsNecroSceneActive()` getter (needed because `NecroSceneActive` is a plain script var, not cross-script-readable). No measurable performance concern: this is hotkey-driven (fires only on an actual keypress, not a per-frame/per-tick poll), and cross-script casts are the same mechanism dozens of existing feature scripts in this mod already use at far higher call frequency.
- [x] **W2 — Hotkey** — `\` (`KEY_EXECUTE = 220`, `VK_OEM_5`) registered on `PlayerAliasScript` (Quest key registration is unreliable — established convention), distinct from the existing `/` corpse-sever key (`KEY_BUTCHER = 191`) and `]` dialog toggle (`KEY_DIALOG_ACTIVATE = 221`), neither of which changed.
- [x] **W3 — Aim + menu** — Reuses `VictimsScript.ResolveVictimsAimActor()` (the existing general-purpose living-actor aim resolver — camera + activate-target + cache) rather than duplicating camera-resolution logic, plus a range check. New `PW_ExecuteMenu` MSG (built in `tools/build_hunger_spell_esp.py`, same field-order convention as the existing `PW_SeverLimbMenu`): **Sever Head** / **Smash Head In** / **Cancel**.
- [x] **W4 — Weapon gates, per-option** — **Decapitate** requires `Main.IsBladeEquipped()` (same gate as every other blade feature in this mod). **Smash Head In** requires one of 5 real, verified heavy-blunt-melee `WEAP` forms — BaseballBat/Sledgehammer/SuperSledge/PipeWrench/PoolCue — confirmed by scanning `Fallout4.esm`'s own `KWDA` (keyword) lists directly: FO4 has **no shared "blunt" keyword** across these (each only carries its own weapon-specific `ma_*` animation keyword plus the generic `WeaponTypeMelee1H/2H` handedness keyword, which is also shared by bladed weapons like Shishkebab) — a curated FormID list is the only honest option here, not invented keyword logic. The menu opens if *either* weapon type is equipped; the specific choice is validated (and rejected with a clear toast) against its specific weapon requirement at selection time.
- [x] **W5 — Eligibility** — Both paths hard-gate on `Main.IsValidTarget(ak, False)` — **non-hostile only** (ambush-style, matching most of this mod's other features, not a combat finisher) — the same essential/protected-NPC-safe check every other kill-adjacent feature in this mod relies on. Re-validated immediately before the kill (menu `Show()` blocks while open; target state could change).
- [x] **W5a — Bond gate** — `TryExecuteAimedVictim` (the entry point) requires `Main.IsHungerUnlocked()` (Bond) before even the weapon check, checked once (Bond is a one-way latch — cannot change value in the window between here and `TryDecapitate`/`TrySmashHeadIn`, so re-checking there would be redundant). Found and fixed as a real gap after initial ship: neither kill path originally checked Bond at all — Smash Head In needs no blade, and Decapitate only required the blade *equipped*, not bonded (Bond needs the blade **and** the Lady Killer perk together, Slice N) — so a fresh, never-bonded save could otherwise execute victims with nothing but a found baseball bat.
- [x] **W6 — Kill sequence** — `RegisterTarget(ak)` (defensive — guarantees `OnDeath` is hooked even if ambient `TargetScan` hasn't caught her yet) → `ak.KillSilent(player)` (passing the player as killer — this mod has already hit the "a killerless `KillSilent` can leave Protected actors alive" gotcha elsewhere and works around it this exact way) → `Dismember("Head1", False, True, abSmash)` (`abForceBloodyMess=False` for a clean Sever Head, `=True` for the gorier Smash Head In — the same flag this codebase already found gibs the head, previously deliberately avoided for corpses, now exactly the desired effect) → `CorpseDecay().QueueStripBodyDecayAfterDismember(ak)` for stump-visual consistency with the existing corpse-sever feature. **No new kill-crediting code** — `OnDeath` fires from any death cause, and since she's registered, the existing `RewardKill → ProcessKnifeKill` pipeline (hunger satiation, decay stamp, named-kill voice) picks it up automatically, exactly like a normal blade kill.

**Status: Implemented — awaiting in-game confirm.** The one thing that could not be verified from code alone: whether `Dismember` immediately after `KillSilent` looks right in the same frame, or needs a beat of delay for the ragdoll to settle first. Built to fail loud (trace + toast, `Is3DLoaded()` guard before the `Dismember` call) rather than silently no-op if this needs revisiting.

## Risks

- Audio without dialogue may need F4SE / custom sound forms.
- Essential NPC filters must never break main quests.
- Tone is extreme — keep lines in editable config files.
- Named-kill / Necromantic hooks (E): soft stub + CustomEvents; no `Necromantic.esp` master.
- Corpse sever (F): limb-under-reticule unavailable in Papyrus; MSG menu + `Dismember` must leave gore pieces (no force-explode / no BloodyMess gib).
- Bed hallucination (G): sleep timing, bed Z clipping, LOS false-triggers on wake camera (see Slice G doc).
- Corpse decay (H): unloaded Actor refs; MCM stage change vs KillerScan sync; eat must clear Victims without orphaning place data; slot-54 face ARMO + ESP/builder FormIDs; equip on ragdolls; strip on consume/despawn; preserve left to external mods.
- Desperate rename (I): GoE2 display names vs Potential Victims overrides; strip cleanly when hunger drops; never touch essentials.
- Retire KillerScan (J): don’t yank the poller until event-driven notice/decay/bed paths are proven; Main façades and contracts still assume KillerScan cadence today.
- Main Alias refactor (J): Caprica forbids `Self as SiblingScript` — cast through Quest; ESP VMAD must list every new Alias script.
- Victim beat (K): FO4 `SetEssential` is often **ActorBase**-scoped (shared templates); must restore prior essential/protected state on K5 rearm; unarmed hit detection without false positives; don’t block later blade kill / satiation; never sticky-essential story NPCs.
- Hunger pacing (L): long climbs must stay fun (not “forgot the mod is installed”); peak rewards must not soft-lock or break SPECIAL balance.
- Witnesses (O): reliable "who actually saw it" detection (LOS/distance) without false positives; forcing flee/hostile AI states cleanly; not aggroing essential/protected NPCs.
- Infamy (P): define “named” vs display-name / Potential Victim overrides for the higher weight; unnamed still awards a smaller bump; never award infamy for essentials; soft-stack with O rumors without double-counting every ambient toast.
- Private cells / quests (Q): Combat Zone / Tommy Lonegan vanilla quest conflicts; captive NPC sourcing without stealing essentials; Culte des Ghouls cell + payment loop; butcher shop vs N overlap. (Gallery no longer triggers Bond on its own — see R — so Pickman house ownership no longer needs to route around that.)
- First blade (R): one-shot first-acquire vs inventory churn / legendary instance FormIDs; Bond trigger no longer includes Gallery-enter-alone (removed — see Slice A); policy when they stop carrying still undecided.
- Force Trade (S): perk must stay living-only so it never replaces Eat Corpse; one-time strip latch is session-script state (cap 32) — oldest drops if many victims; slave pacify is name-substring heuristic (mod gear naming).
- Slavery (T): `SetPlayerTeammate` must stay excepted in `IsValidTarget` or kills/whispers break; never add `CurrentCompanionFaction`; warp is best-effort MoveTo (no Followers quest); one slave at a time; slave-gear name heuristic only.
- Slave scene (U): tag-based position selection depends entirely on what AAF packs the user has installed — must fail loud (toast + trace) if the configured tag resolves to nothing, never silently no-op; exteriors are CTD-prone for AAF scene starts (interior-only default); `OnSceneEnd`/`OnAnimationStart` are documented-flaky in the reference implementation, especially with the player as a scene participant — watchdog + max-duration timer are load-bearing, not just cleanup; never let this feature's `aeCombatState==0`-adjacent or essential-state code paths cross with Slice K's essential-actor protected-collapse race (see BeatBeforeKillScript's own top-of-file note).

