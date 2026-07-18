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

## Later

- [ ] Audio bank research / playback (D)
- [ ] **E** Slow hunger stages (days) + peak-wait reward (attr bonuses until stage 2 — TBD)
- [ ] Corpse hold sync with Necromantic (F)
- [ ] Bed corpse hallucination (G) — see docs/BED_CORPSE_HALLUCINATION.md
- [ ] Lady Killer / Black Widow soft gates; Cannibal stretch (H)
- [ ] Witnesses / killer rumors (I)

## LoversLab release / visibility

- [ ] Create the **Resource** (primary download + description)
- [ ] Create a **support thread** — link the Resource, take bug reports and updates there
- [ ] Soft suite note pointing at Necromantic (companion, not required)

### Skip

- Nexus (content policies usually block this theme)

### Notes

- Tag clearly: serial killer hunger, Pickman's Blade, non-sexual companion to Necromantic
- Separate MO2 folder / page from Necromantic
