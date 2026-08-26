# Pickman's Whisper

Fallout 4 companion mod: a voice that bonds with the wielder of **Pickman's Blade**, then feeds a serial **hunger** that is only sated by knife kills. **Not sexual by default** — one narrow exception (Slice U: an AAF scene with an already-enslaved NPC) — stack with [Necromantic](https://github.com/dorknightofthesole/aaf-necromantic) for corpse aftermath play.

Suite arc (surface → commitment): **Occult Pact** → **Pickman's Whisper** → **Necromantic**. Soft load order when using all three; no compile-time coupling between mods.

Slice status and planned work: [docs/ROADMAP.md](docs/ROADMAP.md). Product rules: [docs/DIRECTION.md](docs/DIRECTION.md).

## Core features

### Bond, hunger, knife voice

- Bond when entering **Pickman Gallery** and/or obtaining / equipping **Pickman's Blade**
- Hunger meter (0–100); rises while bonded; Pip-Boy withdrawal stand-in (AGI/CHA)
- Kill an eligible adult woman with **Pickman's Blade drawn** → praise, hunger → 0, sated window
- Eligible kills: adult **female** non-essential human, seen non-hostile while alive; men, children, teammates, hostiles-from-first-sight, robots/synths/ghouls skipped (see `TargetOverrides.txt` for opt-in exceptions)
- Hunger-staged ambient whispers (editable `NoticeLines_*.txt` + optional `*_Audio.txt`)
- Look-fixation / Potential Victims: aim at her, name her in MCM, recognition + sleep lines
- MCM: How To Use, Hunger, Voice, Victims, Debug

### Blade play

- **Corpse sever** — blade drawn, aim a dead adult woman, press `/` for the limb menu (including **Cut Off Tits**)
- **Beat before kill** — unarmed struggle path on tracked victims (blade sheathed for clean activate)
- **Bed gift** — occasional sleep hallucination corpse near the bed
- **Corpse decay** — tracked knife-kill bodies stage through LooksMenu overlays; ripe-corpse eat urge + END buff when Cannibal applies
- **Desperate rename** — at peak hunger, nearby eligible NPCs get a knife-voice name suffix
- Soft **Necromantic** intimacy hooks on named Potential Victim corpses (no `Necromantic.esp` master)

### Force Trade & slavery

Activate choices appear in the NPC Talk / multi-activate menu when enabled.

- **`]` toggles** Force Trade / Enslave / Take Her choices (**off by default** so beat/attack keep a clean activate)
- Choices are **hidden while Pickman's Blade is drawn** (extra activate options block attack)
- **Force Trade** — open her inventory (`OpenInventory`); first trade strips outfit-locked gear once; later trades keep gear you dressed her in
- Gates: living eligible target, **knife calm** (low hunger), player Charisma ≥ `victimTradeMinCha` / `slaveryMinCha` in `ModConfig.txt`
- Inventory item names containing **`slave`** (case-insensitive) → pacify on Trade close and **auto-enslave**
- **Enslave** — follow + cross-cell warp; **not** a vanilla companion (still a Whisper victim you can kill)
- **Take Her** ([Slice U](docs/SLICE_U_SLAVE_SCENE.md), needs AAF) — once she's already enslaved, this choice replaces the old direct "Free" with a two-actor AAF scene instead. Direct freeing (no scene) moved to an MCM button on the Victims page.
- One slave at a time

**Follow tip (in-game):** a collar / any `"slave"`-named item is enough to **enslave**, but she usually **will not walk-follow** until her **arms are bound** (slave bindings or similar gear). The bindings put her in a restrained AI/idle state; without them, teammate + pathing often leave her rooted even after the “she follows” toast. Collar = yours; bindings = she marches.

## Requirements

- Fallout 4 + [F4SE](https://f4se.silverlock.org/)
- [Mod Configuration Menu](https://www.nexusmods.com/fallout4/mods/21497) (MCM)
- [Garden of Eden Papyrus Script Extender](https://www.nexusmods.com/fallout4/mods/74160) (scans, inventory helpers, config file load)
- [LooksMenu](https://www.nexusmods.com/fallout4/mods/21483) (corpse decay overlays)
- Optional: [Advanced Animation Framework](https://www.nexusmods.com/fallout4/mods/31304) (`AAF.esm`) + at least one animation pack tagged for 2-actor scenes — only needed for the Slavery "Take Her" activate choice (Slice U); everything else in this mod works without it

Optional config under `Data/PickmansWhisper/config/` (editable; reload via MCM Voice or reopen MCM / reload save):

- Five `NoticeLines_*.txt` hunger-stage whisper banks + matching `*_Audio.txt` maps
- `TargetOverrides.txt` — opt-in filter flags. Missing file = all blocked (safe defaults). Copy from `TargetOverrides.example.txt` to enable (e.g. `AllowRobots=1`)
- `ModConfig.txt` — CHA gates, bed gift, decay stages, toast strings, etc.

Slave gear (collar / bindings) comes from whatever slave-equipment mods you use; this mod only looks for the substring **`slave`** in item display names.

One AAF feature (Slavery "Take Her" scene, [Slice U](docs/SLICE_U_SLAVE_SCENE.md) — needs AAF.esm, gated on the target already being enslaved); no BP70. Necromantic is a recommended companion, not a hard dependency.

## Install (MO2)

1. Install **PickmansWhisper** (FOMOD zip or deploy script) so `Data\` contents sit in a mod folder named `PickmansWhisper`.
2. Enable `PickmansWhisper.esp` after `Fallout4.esm` (and after F4SE / MCM / GoE / LooksMenu).
3. Soft suite order: Occult Pact → **PickmansWhisper** → Necromantic.

## Quick start

1. Load a save — toast: `Pickman's Whisper ready`.
2. Enter Pickman Gallery **or** take the blade (`player.additem 22595f 1`).
3. Hear an intro whisper; hunger begins drifting upward while the bond is active.
4. Open MCM → **Hunger** / **Voice** / **Victims** / **Debug** for status and tests.
5. For Force Trade / Enslave: sheath the blade, keep hunger calm, press **`]`** to show Talk choices, dress her in slave gear (**bindings** if you want her to follow).

## Build (developers)

Compile with Caprica (under `tools/Caprica/`) and deploy into your MO2 mod folder:

```bash
# Git Bash
./tools/build-deploy-local.sh
```

```powershell
# PowerShell
.\tools\build-deploy-local.ps1
```

Override deploy path with `PICKMANS_WHISPER_DEPLOY` if needed. The script rebuilds `PickmansWhisper.esp`, compiles scripts, copies MCM/config assets, runs contract tests, and verifies the ESP.

Rebuild ESP alone:

```text
python tools/build_hunger_spell_esp.py
```

Quest-only bootstrap (no hunger SPEL):

```text
python tools/build_esp.py
```

## Direction

Product rules and slice status: [docs/DIRECTION.md](docs/DIRECTION.md), [docs/ROADMAP.md](docs/ROADMAP.md).
