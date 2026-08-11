# TODO

## Slice B (done)

- [x] Knife-kill detection + praise toasts + hunger satiation
- [x] Blade vs gun drawn gate (GoE instance / OMOD contract)

## Slice C

- [x] **C1** GoE living NPC scan + adult female / non-hostile filters
- [x] **C2** Nearby non-hostile female notice toasts + `OnNoticeSpoken` hook
- [x] **C3** Hunger-staged file whispers (`NoticeLines_*.txt` by hunger band; files-only)
- [x] **C4** Approach / ambient restore + always-on killscan arming (verified in-game)
- [x] **C5** Look-fixation POC (ambient unchanged) — verified in-game
  - [x] **P1** Aim edge (GoE) → FormID count (cap 32) + MCM `sFixation:Debug` (fixed: no fake crosshair native)
  - [x] **P2** Voice by count: 1 silent / 2 stage whisper / 3+ `RecognitionLines.txt`
  - [x] **P3+P4** Potential Victims (merged): MCM Victims + FormID↔name + SetDisplayName; optional VictimsHold alias
  - [x] **P5** Sleep recognition (`SleepRecognitionLines.txt` when 3rd+ look + sleeping)

## Slice D

- [x] **D0-POC** MCM Debug Play test whisper (EndIt) (`tools/test_audio_poc.py`)
- [x] **D0.5** Clone SNDRs for Desperate_Audio.txt stems + WhisperSndrIds.txt
- [x] **D1** Delivery mode + notice-hook audio maps (`tools/test_audio_d1.py`) — verify in-game

## Slice E

- [x] **E1** Named-victim kill toast + audio (`ModConfig.txt` keys; Potential Victims name) — toast shipped; audio key when `.xwm` ready
- [x] **E2** Soft Necromantic intimacy hook (`OnNecroSceneStart`/`End` on 0x800; named victim `akArgs[1]`; no ESP master)
- [x] **E3** `OnNecroSceneEnd` intimacy toast (shared speaker with toast param)
- [x] **E4** Random intimacy from `Intimacy_Start_Named.txt` / `Intimacy_End_Named.txt`
- [x] **E5** Intimacy audio maps (23+23 Necromantic Start/End `.xwm`) + same-index delivery

## Slice F

- [x] **F** Blade corpse sever (`/` + MSG limb menu + `Actor.Dismember`) — see docs/SLICE_F_CORPSE_SEVER.md (verified in-game)

## Slice G

- [x] **G1** Bed corpse hallucination (sleep spawn + look-away despawn) — see docs/BED_CORPSE_HALLUCINATION.md (`tools/test_bed_hallucination.py`); verify in-game

## Slice H — corpse decay (body + face) / consume

See docs/SLICE_H_CORPSE_DECAY.md · face art docs/Decay_Head_Guide.md (former Slice I merged here).

- [x] **P0.1** Wound lab (sticky corpse + DeathMarks tint/count)
- [x] **P0.2** Porcupine skin + SFT face lab steppers
- [x] **P1** Bed-gift DeathMarks overlays (verified in-game)
- [ ] **P2** Deliver working Corpse Decay stage change in MCM (Victims Set/Reset/Advance → visible body+face)
- [ ] **P3** Kill stamp + ModConfig `startHours` stage clock (coded — verify in-game)
- [ ] **P4** Peak-stage eat-urge toast (+ optional audio)
- [ ] **P5** Eat reward + clear from Potential Victims
- [ ] **P6** Face decal art finish (stages 1–4; stage 0 verified)

## Slice J — retire KillerScan + Alias refactor (later)

See docs/ROADMAP.md Slice J. Do not start until event-driven kill/notice path is confirmed in-game.

- [ ] **J1** Deprecate and remove the old KillerScan poller
- [ ] **J2** Refactor MainQuestScript — move more code into Alias scripts (e.g. MCM into its own Alias)

## Later

- [ ] **bedGiftWoundAlpha Main expose** — `tools/test_corpse_decay.py` assertion that Main must load/expose `bedGiftWoundAlpha` / `GetBedGiftWoundAlpha` is commented out. Review after ModConfigAlias move: confirm opacity is read from ModConfigAlias (or CorpseDecay) only, then either restore a correct contract or delete the dead Main-facing assert. Related: `test_bed_hallucination.py`, `test_decay_stage_modconfig.py`.
- [ ] **Prune unused Caprica stubs** — after the FO4/F4SE/GoE honesty audit, `tools/stubs/` still keeps every type Caprica may need (inheritance, param types, soft deps). Do a **compile-driven** orphan pass later: remove only stubs proven unnecessary (not a text-scan guess). Keep the live `test_stub_natives.py` source check; never reintroduce fake/Skyrim natives to silence Caprica.
- [ ] **K** Victim beat-before-kill (temp essential + fight back; unarmed exception) — was Slice Q / earlier J
- [ ] **L** Slow hunger stages (days) + peak-wait reward (attr bonuses until stage 2 — TBD)
- [ ] **M** Corpse hold / preserve sync with Necromantic
- [ ] **N** Lady Killer / Black Widow soft gates; Cannibal stretch
- [ ] **O** Witnesses / killer rumors
- [ ] **P** Infamy whispers
- [ ] **Q** Private cells + quests (Combat Zone, Culte des Ghouls, butcher shop, Pickman house)
- [ ] **U** AAF slave scene ("Take Her" activate choice, replaces Free) — see docs/ROADMAP.md Slice U / docs/SLICE_U_SLAVE_SCENE.md (implemented, awaiting in-game confirm)

## LoversLab release / visibility

- [ ] Create the **Resource** (primary download + description)
- [ ] Create a **support thread** — link the Resource, take bug reports and updates there
- [ ] Soft suite note pointing at Necromantic (companion, not required)

### Skip

- Nexus (content policies usually block this theme)

### Notes

- Tag clearly: serial killer hunger, Pickman's Blade, non-sexual companion to Necromantic
- Separate MO2 folder / page from Necromantic
