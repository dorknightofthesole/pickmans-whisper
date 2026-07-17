# Pickman's Whisper

Fallout 4 companion mod: a voice that bonds with the wielder of **Pickman's Blade**, then feeds a serial **hunger** that is only sated by knife kills (Slice B+). **Not sexual** — stack with [Necromantic](https://github.com/dorknightofthesole/aaf-necromantic) for corpse aftermath play.

Suite arc (surface → commitment): **Occult Pact** → **Pickman's Whisper** → **Necromantic**. Soft load order when using all three; no compile-time coupling between mods.

## Slice A (shipped)

- Trigger when entering **Pickman Gallery** interior and/or obtaining / equipping **Pickman's Blade**
- Toast-only voice (builtin trust lines)
- Knife hunger meter (0–100) with Pip-Boy withdrawal stand-in
- MCM: How To Use, Hunger, Voice, Debug

## Slice B (current)

- Kill a non-essential human with **Pickman's Blade** equipped → praise toast, hunger → 0, sated window
- Essential / protected / children / non-humans ignored
- Builtin praise lines + MCM praise test

Fixation scans, audio VO, corpse hold sync, bed hallucination, and perk gates are later slices (see [docs/ROADMAP.md](docs/ROADMAP.md)).

## Requirements

- Fallout 4 + [F4SE](https://f4se.silverlock.org/)
- [Mod Configuration Menu](https://www.nexusmods.com/fallout4/mods/21497) (MCM)

Optional (the five `NoticeLines_*.txt` hunger-stage whisper banks are read from disk and editable; without it, builtin notice lines are used):

- Garden of Eden Papyrus Script Extender (GoE2 file APIs)

No AAF / BP70. Necromantic is a recommended companion, not a hard dependency.

## Install (MO2)

1. Install **PickmansWhisper** (FOMOD zip or deploy script) so `Data\` contents sit in a mod folder named `PickmansWhisper`.
2. Enable `PickmansWhisper.esp` after `Fallout4.esm`.
3. Soft suite order: Occult Pact → **PickmansWhisper** → Necromantic.

## Quick start

1. Load a save — toast: `Pickman's Whisper ready`.
2. Enter Pickman Gallery **or** take the blade (`player.additem 22595f 1`).
3. Hear an intro whisper; hunger begins drifting upward while the bond is active.
4. Open MCM → **Hunger** / **Voice** / **Debug** for status and tests.

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

Override deploy path with `PICKMANS_WHISPER_DEPLOY` if needed. The script rebuilds `PickmansWhisper.esp` (Knife Hunger forms), compiles the quest script, copies MCM/config assets, and verifies the ESP.

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
