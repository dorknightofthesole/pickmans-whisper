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

## Later

- [ ] **G** Bed corpse hallucination — see docs/BED_CORPSE_HALLUCINATION.md
- [ ] **H** Corpse decay / consume + victim places — see docs/SLICE_H_CORPSE_DECAY.md
- [ ] **I** Slow hunger stages (days) + peak-wait reward (attr bonuses until stage 2 — TBD)
- [ ] Corpse hold sync with Necromantic (J)
- [ ] Lady Killer / Black Widow soft gates; Cannibal stretch (K)
- [ ] Witnesses / killer rumors (L)
- [ ] Infamy whispers (M)

## LoversLab release / visibility

- [ ] Create the **Resource** (primary download + description)
- [ ] Create a **support thread** — link the Resource, take bug reports and updates there
- [ ] Soft suite note pointing at Necromantic (companion, not required)

### Skip

- Nexus (content policies usually block this theme)

### Notes

- Tag clearly: serial killer hunger, Pickman's Blade, non-sexual companion to Necromantic
- Separate MO2 folder / page from Necromantic
