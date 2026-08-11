# Slice U — Slave Scene (AAF)

A deliberate, scoped exception to the "no AAF" [DIRECTION.md](DIRECTION.md) rule: a real
two-actor AAF scene between the player and an already-enslaved NPC, reachable via the
"already a slave" branch of `PW_SlaveryActivate` — the activate-choice label there is
now **Take Her**, replacing the original **Free**. Direct one-click freeing moved to an
MCM button (`PickmansWhisperVictimsScript.MCMFreeAimedSlave`, Victims page) so removing
Free from the activate menu isn't a dead end.

## Why this exists, and why not through Necromantic

Necromantic is the suite's existing AAF module, but its scenes are single-actor by
design — the "corpse" in a Necromantic scene is a positioned prop the player aligns to
and animates near, never a real second AAF participant (see
`D:\GitHub\aaf-necromantic\Data\Scripts\Source\User\NecromanticMainQuestScript.psc`,
`Actor[] actors = new Actor[1]`). A genuine two-actor scene with a living, currently
enslaved NPC doesn't fit that architecture without a redesign of Necromantic itself, so
Slice U adds AAF directly to Pickman's Whisper instead — the one narrow, explicitly
documented exception to the "not sexual" direction.

## Reference implementation

`D:\GitHub\aaf-necromantic` is the ground truth for how this author's own prior work
drives the real AAF Papyrus API safely (`tools\stubs\AAF\AAF_API.psc` there — copied
verbatim into this repo at the same path). Key facts, all verified against that code
rather than assumed:

- AAF resolves at runtime: `Game.GetFormFromFile(0x00000F99, "AAF.esm") as AAF:AAF_API`
  (the API quest) and `Game.GetFormFromFile(0x0000915A, "AAF.esm") as Keyword`
  (`AAF_ActorBusy`, polled because `OnSceneInit`/`OnAnimationStart`/`OnSceneEnd` are
  documented-flaky, especially with the player as a participant). No ESP master, no VMAD
  property — same pattern as this mod's existing soft Necromantic hook (Slice E2).
- `StartScene(Actor[] actors, SceneSettings settings)` — Necromantic always passes a
  solo `new Actor[1]` (player only); Slice U is the first place in either mod that builds
  a real `new Actor[2]`.
- **Position selection: an exact id, cloned from Necromantic's own curated-list approach
  — not tag-based auto-select.** Tag-based selection (`settings.position = ""` +
  `settings.includeTags`) was tried first and abandoned: checking real installed 2-actor
  packs (Leito, Atomic Lust, rufGT's — 140 positions total) found only 12 tagged positions
  total, none tagged `Sex` (the original default), and even after relaxing the default to
  empty (no filter), `OnSceneInit` kept failing with `status=5` regardless of which tag was
  tried. Slice U now clones Necromantic's own `Positions.txt` approach 100%: it ships its
  own AAF data (`Data\AAF\PickmansWhisper_positionData.xml` /
  `PickmansWhisper_animationData.xml`), cloned from Necromantic's exact curated 7-position
  list but pairing **both** halves into genuine two-actor animations instead of
  Necromantic's solo M-only idle, using verified real F+M `idleForm` pairs from
  `rxl_bp70_animations.esp` (the same plugin Necromantic already depends on — checked
  directly against the installed "BP70s Fallout 4 Sex anims 2.8" pack's own
  `rxl_bp70_anims_animationData.xml`, not guessed). `settings.position` is set to an exact
  id read from `Data\PickmansWhisper\config\SlaveScenePositions.txt` (first non-comment
  line — unlike Necromantic's `Positions.txt`, there is **no in-game cycling** (no U/P
  keys) for this feature; edit the file and reopen MCM / reload the save to change it).
  `aafSlaveSceneIncludeTags` was removed from `ModConfig.txt`/`ModConfigScript.psc`
  entirely along with this pivot.
- CTD-avoidance patterns reused as-is (all hard-won from that mod's own production
  history, not reinvented here): interior-only by default (`CanStartSceneInCurrentCell`,
  MCM `bAllowExteriorSlaveScene:Debug` override), `EnsureAAFStoppedForRestart` before
  every `StartScene` (stop + `Wait(0.35)` if already busy), a watchdog timer polling
  `AAF_ActorBusy` every 0.5s, a hard `duration + 2.0` max-duration timer as an
  `OnSceneEnd`-is-flaky fallback, careful Unregister-then-Register of all 5
  `CustomEvent`s at load **and** again inside `OnAAFReady` (AAF re-fires that on its own
  re-init).
- **Not** reused: Necromantic's per-corpse player ghost/align logic
  (`ClearAlignGhost`/"Havok CTD vector" avoidance, `SavePlayerTransform`). That exists
  specifically because Necromantic's second "actor" is a static prop being positioned as
  furniture-adjacent. Both actors in a Slice U scene are real AAF participants — AAF's
  own `StartScene` positioning handles placement, so none of that machinery applies.

## Design

- `PickmansWhisperSlaveSceneScript` (new co-script on the Main quest) owns all AAF state:
  `LoadAAF`/`OnAAFReady` (event registration), `EnsureSlaveScenePositionBank`/
  `GetSlaveScenePositionId` (loads `SlaveScenePositions.txt` via the same manifest-free
  `VoiceAlias.LoadStageBankAt` loader every other bank in this mod uses; always returns
  index 0, no cycling state), `TryStartSlaveSceneFromActivate` (gameplay entry —
  re-validates `IsOurSlave`, blade sheathed, not already active, interior cell, ModConfig
  duration present, position bank non-empty), `StartSlaveScene` (builds the 2-actor array
  + `SceneSettings` with the exact `settings.position`), `EndSlaveScene`/
  `CancelSlaveScene` (idempotent teardown), the watchdog + max-duration `OnTimer`, and the
  5 AAF scene events.
- `PickmansWhisperSlaveryPerkScript.OnEntryRun` now trusts `auiEntryID` as the primary
  signal: `tools/build_hunger_spell_esp.py`'s `_activate_choice_entry` gives each entry a
  real, unique `EPFB` (Enslave=0, Take Her=1 — the earlier shared-`EPFB=0000` bug that made
  both entries indistinguishable was found and fixed; see Risks below).
  `IsOurSlave`-based routing is kept only as a fallback for an unrecognized `auiEntryID`.
- `PickmansWhisperMainQuestScript.RegisterFeatureScripts` calls `SlaveScene().LoadAAF()`
  on every `OnQuestInit`/load-game resume (AAF re-fires `OnAAFReady` on its own re-init,
  so this and the in-event re-registration are both intentional, not redundant).

## Phases

- [x] **U1 — Perk label swap** — `PW_SlaveryActivate`'s "already a slave" choice
  relabeled **Take Her**; `OnEntryRun` routes it to `TryStartSlaveSceneFromActivate`
  instead of `TryFreeSlaveFromActivate`.
- [x] **U2 — Two-actor AAF scene** — `new Actor[2]` (player + target); exact
  `settings.position` sourced from `SlaveScenePositions.txt`, pointing at this mod's own
  `Data\AAF\PickmansWhisper_positionData.xml`/`_animationData.xml` (cloned from
  Necromantic's curated 7-position list, paired instead of solo). Tag-based auto-select
  was tried first and abandoned — see "Position selection" above.
- [x] **U3 — CTD-avoidance parity** — Interior-only default + MCM override, restart-safe
  `EnsureAAFStoppedForRestart`, watchdog + max-duration timers, `OnAAFReady` re-bind.
- [x] **U4 — MCM status / cancel / free** — Victims page `sSlaveScene` status row +
  "Free (no scene)" button (`MCMFreeAimedSlave`); Debug page exterior-allow toggle +
  "Cancel slave scene" button.
- [x] **U5 — Docs reversal** — [DIRECTION.md](DIRECTION.md) / [ROADMAP.md](ROADMAP.md)
  scope the "no AAF" rule to name this one exception explicitly.

**Status: Implemented — awaiting in-game confirm of the exact-position pivot.** Static
checks (`tools/test_slave_scene.py`) only verify the code and AAF data are wired
correctly; the actual `StartScene` call against `rxl_bp70_animations.esp`'s real idle
forms and CTD-avoidance timing still need a real in-game session with AAF running to
confirm.

## Risks

- **Tag-based auto-select was tried first and did not work — this is why the design
  changed, not a hypothetical concern.** The original default tag (`Sex`) was an
  unverified guess and matched zero installed positions (checked Leito/Atomic
  Lust/rufGT's directly: 140 positions, 12 tagged, none `Sex`). Relaxing the default to
  empty (no filter) still produced `OnSceneInit status=5` on a brand-new, never-before-
  tested NPC, ruling out per-actor state as the cause. Exact-position selection (cloning
  Necromantic's own approach, pointing `settings.position` at this mod's own verified-real
  `rxl_bp70_animations.esp` idle forms) replaces tag matching entirely — there is no tag
  fallback path left to reason about.
- **`EnsureAAFStoppedForRestart`/`EndSlaveScene` must check both actors, not just the
  player.** Confirmed gap in both: they originally only checked `Game.GetPlayer()`'s
  `AAF_ActorBusy` keyword, never the target's — a stale busy flag left on the target from
  a prior aborted attempt (keywords on an actor reference are save-game state, so this can
  persist across reloads and even full game restarts) would never be noticed or cleared.
  Fixed via `IsActorAAFBusy`. Ruled out as the cause of the `status=5` failure specifically
  (confirmed via log: `playerBusy=False targetBusy=False` on a failing attempt after the
  fix), but was a real gap regardless.
- **Enslave/Take Her shared the same `EPFB`, so `auiEntryID` could never distinguish
  them — a real, confirmed bug, not a guess.** `tools/build_hunger_spell_esp.py`'s
  `_activate_choice_entry` hardcoded `EPFB=0000` for every entry. xEdit's own field
  schema (`wbDefinitionsFO4.pas`) names `EPFB` **"Perk Entry ID (unique)"** — it's what
  `OnEntryRun`'s `auiEntryID` actually reflects. With both entries sharing id 0, clicking
  either "Enslave" or "Take Her" always ran the same `IsOurSlave`-based branch, so once an
  NPC was already enslaved, clicking Enslave on her again started an AAF scene instead.
  Fixed: each entry now gets a real unique `EPFB` (Enslave=0, Take Her=1, verified
  byte-for-byte in the built ESP by `tools/test_slavery.py`), and `OnEntryRun` branches on
  `auiEntryID` primarily, keeping `IsOurSlave` only as a fallback for an unrecognized id.
- **Exteriors are CTD-prone for AAF scene starts** (same finding Necromantic's own
  testing produced) — interior-only is the safe default; the MCM override exists for
  debugging, not routine use.
- **`OnSceneEnd`/`OnAnimationStart` are documented-flaky**, especially with the player as
  a participant (not just an idle-solo scene) — the watchdog + max-duration timer are
  load-bearing here, not just a cleanup nicety.
- **Do not let this feature's logic cross Slice K's essential-actor protected-collapse
  race.** `PickmansWhisperBeatBeforeKillScript`'s own top-of-file note documents a
  confirmed-live bug where touching `SetEssential` inside `Actor.OnCombatStateChanged`'s
  `aeCombatState==0` branch raced an essential actor's protected-collapse moment.
  `HandleCombatEnd` (Slice K's own later addition, cosmetic beat-face overlays) proved a
  *non*-essential-mutating action in that same branch is safe; Slice U's AAF calls live
  entirely outside that event and never touch `SetEssential`, but any future change that
  makes them interact with combat-state handling should re-read that history first.

## Contract

`tools/test_slave_scene.py` — stub presence, 2-actor array (not Necromantic's solo
`new Actor[1]`), exact-position `settings.position` (no `includeTags` anywhere, no
hardcoded literal id), AAF data files (7 genuine two-actor positions cross-checked against
`SlaveScenePositions.txt`), ModConfig SSOT + fail-loud (duration only, no
`aafSlaveSceneIncludeTags`), CTD-avoidance function/event presence, perk/Main/Victims
wiring, MCM config, deploy gate (both `.ps1` and `.sh`, plus `package_mo2_zip.py` and
`fomod/ModuleConfig.xml` shipping `Data/AAF`), and that the direction docs no longer state
an unconditional "no AAF" rule.
