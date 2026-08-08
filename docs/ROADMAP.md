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
| **J** | Retire KillerScan + thin Main via Alias scripts (e.g. MCM Alias)                               | Planned — later                                                                                                                                      |
| **K** | Victim “beat before kill” — temp essential + fight back (unarmed exception)                    | Planned (was Slice Q / earlier J; code/comments may still say J or Q)                                                                                |
| **L** | Slow hunger stages (days) + peak-hunger wait rewards                                           | Planned                                                                                                                                              |
| **M** | Corpse preserve sync with Necromantic                                                          | Planned                                                                                                                                              |
| **N** | Perk gates; optional butcher cell / Cannibal hooks                                             | Planned                                                                                                                                              |
| **O** | Witness support: flee/scream or attack; rumors of the "killer"                                 | Planned                                                                                                                                              |
| **P** | Infamy / serial-killer whispers                                                                | Planned                                                                                                                                              |
| **Q** | Private cells + quests (Combat Zone stage, Culte des Ghouls, butcher shop, Pickman house home) | Planned                                                                                                                                              |




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
- [x] **C4** — Approach / first-enter feel via ambient KillerScan path (dedicated 0.5s FindActors hammer rejected — silenced the quest). **Verified in-game** with always-on timer arming; auto MessageBoxes removed (MCM Scan nearby keeps its dialog).
- [x] **Killer Orchestrator (v1.3.0)** — sole `PickmansWhisperKillerScanScript` → TargetSnapshot → Voice sync + NoWait knife/cadence/Victims/CorpseDecay(H)/BedGift. Replaces WorldScan + multi-timer arming. Contract: `tools/test_killer_scan_bus.py`. Victims MCM decay Set/Reset overlay nudge parked → **H P2**.
- [x] **C5** — Look-fixation POC (**additive — no change to ambient C2/C3 whispers**). Cap 32 FormIDs, save-persisted arrays. **Verified in-game** (incl. sleep recognition).
  - [x] **P1** — Aim edge (GoE camera/activate — not fake `GetCurrentCrosshairRef`) → count + MCM Look fixation. Ambient KillerScan whispers; KillerScan re-arms before tick body (`tools/test_look_fixation.py`).
  - [x] **P2** — Voice by count: 1st silent / 2nd `RecognitionLines.txt` / 3rd+ hunger-stage notice (`tools/test_recognition_lines.py`). Ladder ends on sharper C3 lines.
  - [x] **P3+P4** — Potential Victims (merged): MCM Victims page ↔ FormID table + GoE2 `SetDisplayName` (world name) so `{name}` matches aim label; cap 32; lazy re-apply when seen; optional `VictimsHold` RefCollectionAlias (`tools/test_potential_victims.py`).
  - [x] **P5** — Sleep recognition: `SleepRecognitionLines.txt` when 2nd look and `GetSleepState() >= 3` (`tools/test_sleep_recognition.py`).



## Slice D — audio

- [x] **D0-POC** — MCM Debug **Play test whisper (EndIt)** → `Sound.Play` on `PW_Whisper_EndIt` (`0x807`).
- [x] **D0.5** — Esp build clones SNDR for every `Desperate_Audio.txt` `.xwm` stem (`PW_Whisper_<Stem>`, `WhisperSndrIds.txt`).
- [x] **D1** — Load `*_Audio.txt`, MCM `iVoiceDelivery` (Toast+Audio / Audio / Toast), same-index `PlayNoticeAudio` on notice path (`tools/test_audio_d1.py`). **Verified in-game.**

- Map keys are `.xwm` under `Data/Sound/PickmansWhisper/`. Blank Calm/Restless/Hungry/Starving maps until clips exist.
- Docs: [AUDIO.md](AUDIO.md), [CREATE_SNDR_XEDIT.md](CREATE_SNDR_XEDIT.md).
- Voice features require owning Pickman's Blade (`IsVoiceWeaponReady` → `PlayerHasBlade`); kills / butcher still require it drawn (`IsBladeEquipped`).



## Slice E — named kill voice + soft Necromantic intimacy

Special lines when the player has a personal stake (Potential Victims name) and soft suite hooks with Necromantic. **No** `Necromantic.esp` master; no AAF/sex code in this mod.

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

Design: [SLICE_H_CORPSE_DECAY.md](SLICE_H_CORPSE_DECAY.md). Face art: [Decay_Head_Guide.md](Decay_Head_Guide.md). Soft with **M** (preserve) and **N** (Cannibal). Cap aligns with Victims (32).

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

- [ ] **J1 — Deprecate and remove KillerScan** — Retire `PickmansWhisperKillerScanScript` and the poll-driven TargetSnapshot / cadence fan-out once notice, fixation, decay sync, bed gift, and related listeners are driven by events (or thin dedicated hosts). Update contracts (`test_killer_scan_bus.py`, arming docs) so they no longer require the scanner. Protect proven load/arm behavior until the replacement is verified — then delete, don’t leave a zombie poller.
- [ ] **J2 — Thin MainQuestScript via Alias scripts** — Move more feature/MCM surface out of `PickmansWhisperMainQuestScript` onto quest Alias scripts (same pattern as ModConfigAlias, KillRewardAlias, PlayerAlias). Example: MCM CallFunction / panel refresh into its own Alias. Main stays a thin router; Caprica cast-through-Quest rule still applies. Follow [modular-feature-scripts](.cursor/rules/modular-feature-scripts.mdc).
- [ ] J3 **— Deprecate Bond —** Remove all MCM and code references to bond.



## Slice K — victim beat-before-kill (temp essential)

Formerly roadmap **Slice Q** (and earlier **J**; scripts/tests may still say J / Q / J1–J5). Let the player **pretend to beat** a qualified woman before finishing her with the knife — she won’t die during the scuffle and ideally **fights back**. Soft with Victims (C5) and knife-kill rules (B).

- [ ] **K1 — MCM Victims: mark essential** — On a Potential Victim (or aimed eligible NPC), toggle “can’t be killed” for the beat fantasy. Clear via K5 / MCM off / blade kill path.
- [ ] **K2 — Auto on unarmed attack** — If the player attacks a **qualified** NPC **without a weapon armed** (fists / no drawn weapon), auto-enter the same temp-essential + fight-back state. **Exception:** Pickman's Blade need **not** be drawn for this path (blade still required later to sate / praise).
- [ ] **K3 — Fight back** — Aggro / combat so she resists instead of crumpling; exit cleanly when essential is cleared so a later blade kill can work.
- [ ] **K4 — Qualification** — Same spirit as notice/kill: adult **female**, human, **non-hostile** (at first contact); skip story essentials, children, teammates, non-humans. Never leave a shared `ActorBase` permanently essential (FO4 essential is base-level — design must be ref-safe / restore prior state).
- [ ] **K5 — Clear essential on rearm** — When the player **rearms any weapon** (draws / equips a weapon again after the unarmed beat), mark her **unessential** (restore prior state) so she can be finished with the blade.

Honor direction: this is **player-opted / auto beat** essential on eligible targets only — not a loophole to immortalize story NPCs.

## Slice L — slow hunger + peak wait rewards

Stretch the hunger climb so each stage lasts **days** of game time (not a quick meter fill). Reward patience when the player waits until hunger is peaking before killing.

- **Pace:** climb from calm → desperate over at least ~3 game days; prefer ~1 week+ to reach 100% (tunable MCM / config). Stage bands stay the five C3 whisper stages; only the rise rate / thresholds stretch.
- **Peak reward (TBD — draft):** waiting until high hunger (e.g. starving/desperate) before a valid blade kill grants a temporary bonus — candidate: **attribute bonuses that last until hunger drops back to stage 2 (restless)** (or similar clear exit). Exact bonuses / magnitude undecided; design before implement.
- Do **not** break C3 stage file mapping while tuning rise rate; prefer finishing **Slice J** (KillScanner gone) before relying on scan-tied hunger ticks.
- Soft-stack with Necromantic craving feel; no ESP master dependency.



## Slice M — corpse preserve

- `HeldCorpses[]` + soft claim token on knife-kill victims.
- Compatible with Necromantic holds; no ESP master dependency.
- Ephemeral bed-hallucination corpses (Slice G) are **not** long-term hold targets.
- Soft with **H**: preserved / claimed corpses pause or reset decay (body + face stage).



## Slice N — perk / stretch

- Soft-gate or enhance via Lady Killer / Black Widow.
- Optional Cannibal; stretch butcher-shop cell.
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

- Whispers about a new serial killer in the commonwealth
- References to past murders, could include the name of the victim that differs from the name the player gave them, but the player would realize it is "Cindy"
- Whispers could increase after a murder



## Slice Q — private cells + quests (stage, cult, shop, home)

Large stretch: custom (or heavily edited) **private cells** and quests that turn the knife voice into a public/secret economy of murder. Soft with **N** (butcher / Cannibal), **M** (preserve), **P** (infamy). Design before ESP sprawl — each pillar can ship as its own sub-slice.

- [ ] **Q1 — Combat Zone stage of horror** — Partner with **Tommy Lonegan** at the Combat Zone; offer “performances” where the player murders captured slaves before an audience. Transform the Combat Zone into a stage of horror (crowd reaction, payment, optional return gigs).
- [ ] **Q2 — Culte des Ghouls** — Secret society of elites who **pay to watch** the player commit murder; they are secret cannibals and want to **feast on the victim afterward**. Private salon / cellar cell; invitation / membership progression TBD.
- [ ] **Q3 — Butcher shop** — Player-openable butcher shop (cell + vendor / workbench loop). Soft-stack with Slice **N** Cannibal / butcher-shop stretch — decide whether Q3 *is* that stretch or a fuller shop quest.
- [ ] **Q4 — Pickman's house as player home** — Make **Pickman's Gallery / house** a proper player home (ownership, storage, bed, safe return). Likely the **priority** pillar of Q; may unlock before or alongside Q1–Q3.

Honor direction: no AAF/sex content here; never break essential/protected story NPCs; keep line banks editable; soft complementarity with Necromantic only (no hard master).

## Risks

- Audio without dialogue may need F4SE / custom sound forms.
- Essential NPC filters must never break main quests.
- Tone is extreme — keep lines in editable config files.
- Named-kill / Necromantic hooks (E): soft stub + CustomEvents; no `Necromantic.esp` master.
- Corpse sever (F): limb-under-reticule unavailable in Papyrus; MSG menu + `Dismember` must leave gore pieces (no force-explode / no BloodyMess gib).
- Bed hallucination (G): sleep timing, bed Z clipping, LOS false-triggers on wake camera (see Slice G doc).
- Corpse decay (H): unloaded Actor refs; MCM stage change vs KillerScan sync; decay vs M preserve race; eat must clear Victims without orphaning place data; slot-54 face ARMO + ESP/builder FormIDs; equip on ragdolls; strip on consume/despawn.
- Desperate rename (I): GoE2 display names vs Potential Victims overrides; strip cleanly when hunger drops; never touch essentials.
- Retire KillerScan (J): don’t yank the poller until event-driven notice/decay/bed paths are proven; Main façades and contracts still assume KillerScan cadence today.
- Main Alias refactor (J): Caprica forbids `Self as SiblingScript` — cast through Quest; ESP VMAD must list every new Alias script.
- Victim beat (K): FO4 `SetEssential` is often **ActorBase**-scoped (shared templates); must restore prior essential/protected state on K5 rearm; unarmed hit detection without false positives; don’t block later blade kill / satiation; never sticky-essential story NPCs.
- Hunger pacing (L): long climbs must stay fun (not “forgot the mod is installed”); peak rewards must not soft-lock or break SPECIAL balance.
- Witnesses (O): reliable "who actually saw it" detection (LOS/distance) without false positives; forcing flee/hostile AI states cleanly; not aggroing essential/protected NPCs.
- Private cells / quests (Q): Combat Zone / Tommy Lonegan vanilla quest conflicts; captive NPC sourcing without stealing essentials; Culte des Ghouls cell + payment loop; butcher shop vs N overlap; Pickman house ownership without breaking Gallery bond trigger.
