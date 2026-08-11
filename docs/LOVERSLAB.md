# LoversLab release draft — Pickman's Whisper

Paste-ready copy for the **Resource** page and a **support thread**. Edit placeholders (`[LINK]`, screenshots, Necromantic Resource URL) before posting.

Author / version (from FOMOD): **Oohtre** · **1.3.0**  
Repo: https://github.com/dorknightofthesole/pickmans-whisper

---

## Suggested Resource metadata

| Field | Suggestion |
| ----- | ---------- |
| **Title** | Pickman's Whisper |
| **Category** | Fallout 4 → Adult Mods (or closest FO4 adult/gameplay fit) |
| **Prefix / tags** | Fallout 4, Adult, Dark, Horror, Serial Killer, Slavery, AAF (optional), MCM, F4SE |
| **Short description** | Knife voice + serial hunger for Pickman's Blade. Mostly non-sexual; optional AAF "Take Her" for an enslaved NPC. Soft companion to Necromantic. |
| **Content warnings** | Graphic violence / serial murder fantasy; non-consensual slavery / force trade; optional AAF adult scene; corpse decay / cannibal hooks |

**Do not** post on Nexus — content policies usually block this theme.

Keep a **separate** MO2 folder and LoversLab page from Necromantic.

---

## Resource description (BBCode)

Copy everything below into the Resource description editor.

```bbcode
[CENTER][SIZE=6][B]Pickman's Whisper[/B][/SIZE]
[I]A voice that bonds to Pickman's Blade — then feeds a hunger only knife kills can sate.[/I]

[B]Version[/B] 1.3.0 · Author: Oohtre
[URL=https://github.com/dorknightofthesole/pickmans-whisper]GitHub[/URL]
[/CENTER]

[B]Content warnings[/B]
Serial killer / knife-murder fantasy · adult female victim targeting · force trade & slavery · optional AAF adult scene · corpse decay / cannibal hooks. Not a lighthearted companion mod.

[HR]

[SIZE=5][B]What this is[/B][/SIZE]

Fallout 4 companion mod for the [B]Pickman's Blade[/B] fantasy: a voice that starts warm and bonded, then escalates into staged [B]hunger[/B] that only clears when you kill an eligible adult woman [B]with the blade drawn[/B].

This mod is [B]not sexual by default[/B]. One narrow exception: Slavery [B]"Take Her"[/B] (needs AAF) — a two-actor scene only after she is already your slave. Stack with [B]Necromantic[/B] for corpse aftermath play; no hard master / no compile-time coupling.

[B]Suite arc[/B] (surface → commitment):
Occult Pact → [B]Pickman's Whisper[/B] → Necromantic

Soft load order when using all three. Separate mod folder / page from Necromantic.

[HR]

[SIZE=5][B]Features[/B][/SIZE]

[B]Bond, hunger, knife voice[/B]
[LIST]
[*]Bond when entering [B]Pickman Gallery[/B] and/or obtaining / equipping [B]Pickman's Blade[/B]
[*]Hunger meter (0–100); rises while bonded; Pip-Boy withdrawal stand-in (AGI/CHA)
[*]Valid blade kill → praise, hunger → 0, sated window
[*]Eligible kills: adult [B]female[/B] non-essential human, seen non-hostile while alive (men, children, teammates, hostiles-from-first-sight, robots/synths/ghouls skipped; see TargetOverrides for opt-in)
[*]Hunger-staged ambient whispers (editable line banks + optional audio maps)
[*]Look-fixation / Potential Victims: aim, name her in MCM, recognition + sleep lines
[*]MCM: How To Use, Hunger, Voice, Victims, Debug
[/LIST]

[B]Blade play[/B]
[LIST]
[*][B]Corpse sever[/B] — blade drawn, aim a dead adult woman, press [B]/[/B] for limb menu
[*][B]Beat before kill[/B] — unarmed struggle path on tracked victims (blade sheathed for clean activate)
[*][B]Bed gift[/B] — occasional sleep hallucination corpse near the bed
[*][B]Corpse decay[/B] — tracked knife-kill bodies stage through LooksMenu overlays; ripe-corpse eat urge + END buff when Cannibal applies
[*][B]Desperate rename[/B] — at peak hunger, nearby eligible NPCs get a knife-voice name suffix
[*]Soft [B]Necromantic[/B] intimacy hooks on named Potential Victim corpses (no Necromantic.esp master)
[/LIST]

[B]Force Trade & slavery[/B]
[LIST]
[*][B]][/B] toggles Force Trade / Enslave / Take Her choices ([B]off by default[/B] so beat/attack keep a clean activate)
[*]Choices are [B]hidden while Pickman's Blade is drawn[/B] (extra activate options block attack)
[*][B]Force Trade[/B] — open her inventory; first trade strips outfit-locked gear once
[*]Gates: living eligible target, [B]knife calm[/B] (low hunger), player Charisma ≥ config thresholds
[*]Inventory item names containing [B]slave[/B] (case-insensitive) → pacify on Trade close and auto-enslave
[*][B]Enslave[/B] — follow + cross-cell warp; [B]not[/B] a vanilla companion (still a Whisper victim you can kill)
[*][B]Take Her[/B] (optional AAF) — once enslaved, starts a two-actor scene; free via MCM Victims page
[*]One slave at a time
[/LIST]

[B]Follow tip:[/B] a collar / any "slave"-named item can [B]enslave[/B], but she usually will [B]not walk-follow[/B] until her [B]arms are bound[/B] (slave bindings or similar). Collar = yours; bindings = she marches.

[HR]

[SIZE=5][B]Requirements[/B][/SIZE]

[B]Required[/B]
[LIST]
[*]Fallout 4 + [URL=https://f4se.silverlock.org/]F4SE[/URL]
[*][URL=https://www.nexusmods.com/fallout4/mods/21497]Mod Configuration Menu[/URL] (MCM)
[*][URL=https://www.nexusmods.com/fallout4/mods/74160]Garden of Eden Papyrus Script Extender[/URL] (scans, inventory helpers, config load)
[*][URL=https://www.nexusmods.com/fallout4/mods/21483]LooksMenu[/URL] (corpse decay overlays)
[/LIST]

[B]Optional[/B]
[LIST]
[*][URL=https://www.nexusmods.com/fallout4/mods/31304]Advanced Animation Framework[/URL] (AAF.esm) + at least one 2-actor animation pack — [B]only[/B] for Slavery "Take Her"
[*]Slave collar / bindings from whatever slave-equipment mods you use (this mod only matches the substring [B]slave[/B] in item display names)
[*][B]Necromantic[/B] — recommended companion for corpse intimacy after the kill habit ([URL=REPLACE_WITH_NECROMANTIC_LL_OR_GITHUB]Necromantic[/URL]) — [I]not required[/I]
[/LIST]

[HR]

[SIZE=5][B]Install (MO2)[/B][/SIZE]

[LIST=1]
[*]Install [B]PickmansWhisper[/B] (FOMOD zip) into its [B]own[/B] mod folder named PickmansWhisper
[*]Enable [B]PickmansWhisper.esp[/B] after Fallout4.esm, F4SE, MCM, GoE, LooksMenu
[*]Soft suite order: Occult Pact → PickmansWhisper → Necromantic
[/LIST]

[HR]

[SIZE=5][B]Quick start[/B][/SIZE]

[LIST=1]
[*]Load a save — toast: [I]Pickman's Whisper ready[/I]
[*]Enter Pickman Gallery [B]or[/B] take the blade ([FONT=courier]player.additem 22595f 1[/FONT])
[*]Hear an intro whisper; hunger drifts upward while bonded
[*]Open MCM → Hunger / Voice / Victims / Debug
[*]For Force Trade / Enslave: sheath the blade, keep hunger calm, press [B]][/B], dress her in slave gear ([B]bindings[/B] if you want follow)
[/LIST]

Editable config lives under [FONT=courier]Data/PickmansWhisper/config/[/FONT] (notice line banks, audio maps, ModConfig.txt, TargetOverrides). Missing TargetOverrides = safe blocked defaults; copy from the .example file to opt in.

[HR]

[SIZE=5][B]Support[/B][/SIZE]

Bug reports, questions, and update notes: [URL=REPLACE_WITH_SUPPORT_THREAD]support thread[/URL].

Please include: FO4 + F4SE version, load order snippet (this mod + MCM/GoE/LooksMenu/AAF/Necromantic if used), MCM Debug status lines if relevant, and a short repro. Papyrus logging on helps a lot ([FONT=courier]bEnableLogging=1[/FONT], [FONT=courier]bEnableTrace=1[/FONT], [FONT=courier]bLoadDebugInformation=1[/FONT]).

[HR]

[SIZE=5][B]Permissions[/B][/SIZE]

[LIST]
[*]Personal use / private load orders: fine
[*]Do not re-upload elsewhere without asking
[*]Assets and line banks are editable for your own game; please don't republish the whole package as your own
[/LIST]

[I]Not affiliated with Bethesda. Fallout 4 © Bethesda Softworks.[/I]
```

---

## Support thread — opening post (BBCode)

Create a forum thread in the matching FO4 section. Title idea: **Pickman's Whisper — Support & Updates**.

```bbcode
[B]Pickman's Whisper — support & updates[/B]

Resource: [URL=REPLACE_WITH_RESOURCE_URL]Pickman's Whisper[/URL]
GitHub: [URL=https://github.com/dorknightofthesole/pickmans-whisper]dorknightofthesole/pickmans-whisper[/URL]

This thread is for bug reports, questions, and release notes. Download from the Resource page above.

[B]What belongs here[/B]
[LIST]
[*]Install / load-order issues
[*]Hunger / whisper / kill-satiation bugs
[*]Force Trade / Enslave / Take Her problems
[*]Soft suite stacking with Necromantic
[/LIST]

[B]Please include when reporting[/B]
[LIST]
[*]Mod version (FOMOD / MCM)
[*]FO4 + F4SE build
[*]Relevant load order (PickmansWhisper + MCM, GoE, LooksMenu; AAF / Necromantic if used)
[*]What you expected vs what happened
[*]MCM Debug / status lines if the feature has them
[*]Papyrus log excerpt if you can ([FONT=courier]Documents\My Games\Fallout4\Logs\Script\Papyrus.0.log[/FONT] — OneDrive Documents path if applicable)
[/LIST]

[B]Soft suite note[/B]
Pickman's Whisper is the knife / serial-hunger layer. [B]Necromantic[/B] is the recommended (optional) corpse-intimacy companion — separate download, separate MO2 folder, no esp master from this mod. Soft order: Occult Pact → Pickman's Whisper → Necromantic.

[B]Current version[/B]
1.3.0 — see Resource description for features and requirements.
```

---

## Soft suite blurb (short — for Necromantic page / cross-link)

Paste on Necromantic (or in comments) when you want a one-liner pointer:

```bbcode
[B]Suite companion:[/B] [URL=REPLACE_WITH_PICKMANS_WHISPER_RESOURCE]Pickman's Whisper[/URL] — Pickman's Blade voice + serial hunger (mostly non-sexual; optional AAF "Take Her" for an enslaved NPC). Soft-stack before Necromantic. Not required.
```

---

## Posting checklist

From `TODO.md` LoversLab release items:

- [ ] Create the **Resource** (primary download + description above)
- [ ] Attach the FOMOD zip; confirm folder name `PickmansWhisper` / `PickmansWhisper.esp`
- [ ] Create the **support thread**; link Resource ↔ thread both ways
- [ ] Soft suite note on Necromantic (companion, not required)
- [ ] Replace `REPLACE_WITH_*` URLs after both pages exist
- [ ] Add 2–4 screenshots (gallery bond toast, hunger MCM, whisper toast, optional slavery / Take Her if you want that visible)
- [ ] Skip Nexus
