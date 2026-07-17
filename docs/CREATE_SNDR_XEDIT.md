# Create a Sound Descriptor (SNDR) in xEdit — beginner walkthrough

This guide is for **Pickman's Whisper** Slice D. Goal: make **one** working Sound Descriptor that plays a converted whisper clip via Papyrus `Sound.Play`. Once that “golden” SNDR works in-game, we can clone it for the rest of the lines.

You do **not** need the Creation Kit for this path.

---

## What you are making

| Piece | Role |
|-------|------|
| Source clip | e.g. `Data/PickmansWhisper/whispers/EndIt.mp3` (authoring) |
| Runtime clip | e.g. `Data/Sound/PickmansWhisper/EndIt.xwm` (what the game plays) |
| SNDR record | Inside `PickmansWhisper.esp` — tells the game “this FormID plays that `.xwm`” |

Papyrus cannot play the `.mp3` by path. It plays the **SNDR form**.

Suggested first clip (Desperate map index 0): **`EndIt`**.

---

## Before you open xEdit

### 1. Install FO4Edit (xEdit for Fallout 4)

1. Download **FO4Edit** from Nexus: [FO4Edit (xEdit)](https://www.nexusmods.com/fallout4/mods/2737) — that **is** xEdit for Fallout 4 (same tool; FO4Edit / SSEEdit / TES5Edit are game-specific builds). You do **not** need a separate “xEdit” download.
2. Unzip it somewhere stable (e.g. `D:\Tools\FO4Edit\`).
3. You will run **`FO4Edit.exe`**.

### 2. Use Mod Organizer 2 (recommended)

If you use MO2 (this mod’s usual setup):

1. In MO2: **Tools → Executables → Add**.
2. Title: `FO4Edit`.
3. Binary: browse to `FO4Edit.exe`.
4. Start in: FO4Edit’s folder (or leave default).
5. Run FO4Edit **from MO2** with your usual profile active so it sees `PickmansWhisper` and Fallout4.esm the same way the game does.

If you run FO4Edit outside MO2, it only sees files under the real `Fallout 4\Data` folder — easy to edit the wrong copy of the esp.

### 3. Convert one MP3 → XWM

xEdit does **not** convert audio. Do this first.

1. Use **MultiXwm** (or any FO4-capable xwm converter you trust).
2. Convert `Data/PickmansWhisper/whispers/EndIt.mp3` → `EndIt.xwm`.
3. Create folder (under the mod, so MO2 deploys it):

   `Data/Sound/PickmansWhisper/`

4. Put the file here:

   `Data/Sound/PickmansWhisper/EndIt.xwm`

Keep the `.mp3` in `whispers/` for editing; the game will use the `.xwm` under `Sound\`.

**Path the SNDR will store** (no `Data\` prefix — FO4 style):

```text
Sound\PickmansWhisper\EndIt.xwm
```

---

## Open the plugins in FO4Edit

1. Start FO4Edit (via MO2 if you use it).
2. A checklist of plugins appears.
3. Click **OK** / leave defaults so masters load. Make sure these are checked:
   - `Fallout4.esm` (required)
   - `PickmansWhisper.esp` (your mod)
4. Wait until the background loader finishes (bottom status: something like “Background Loader: finished”).

Left pane = plugin tree. Right pane = record details.

---

## Easiest method: copy an existing SNDR, then edit it

Creating a blank SNDR from scratch is fiddly (categories, output models, flags). Safer for a first time: **copy a simple vanilla sound**, override it into our esp, then point it at `EndIt.xwm` and rename it.

### 4. Find a simple vanilla sound to copy

1. In the left tree, expand **`Fallout4.esm`**.
2. Expand **`Sound Descriptor`** (record type **SNDR**).
3. Click inside that list and press **Ctrl+F** (Find).
4. Search for something short and UI-like, for example:
   - `UIMenuOK`
   - or `UIPipBoy`
   - or any non-looping one-shot that looks simple in the right pane

You want a **Standard** one-shot sound (not a huge compound weapon set). If the right pane shows a clear **sound file path** and it plays conceptually as a short cue, you’re fine.

### 5. Copy as override into PickmansWhisper.esp

1. Right-click the SNDR you found in `Fallout4.esm`.
2. Choose **Copy as override into…**
3. In the plugin list, check **`PickmansWhisper.esp`** only → OK.
4. If asked about adding a master: `Fallout4.esm` should already be a master; accept defaults.

You should now see the same EditorID under:

`PickmansWhisper.esp` → `Sound Descriptor` → (that record)

Green / override coloring means “this esp overrides the vanilla form.” Next we turn it into **our** whisper form (new EditorID + our file), not a permanent override of the UI click sound.

### 6. Give it a Pickman's Whisper identity

With the override selected under **`PickmansWhisper.esp`**:

1. In the right pane, find **EDID - Editor ID**.
2. Double-click the value and change it to:

   ```text
   PW_Whisper_EndIt
   ```

3. Confirm / press Enter.

Naming rule for later clones: `PW_Whisper_<Stem>` where stem matches the map filename without extension (`EndIt.mp3` → `PW_Whisper_EndIt`).

### 7. Point it at your XWM

Still on that record under `PickmansWhisper.esp`:

1. Look through the right pane for the **sound file / path** field. In FO4Edit this often appears under a structure related to the sound definition (names vary slightly by xEdit version — look for a path ending in `.xwm` or `.wav`, or a “Sounds” / “ANAM” / file list entry).
2. Change that path to:

   ```text
   Sound\PickmansWhisper\EndIt.xwm
   ```

   Use **backslashes**. Do **not** prefix with `Data\`.

3. If there are multiple file entries, clear extras so only this one remains (one-shot whisper).

### 8. Keep category / output model from the template (for now)

Leave **Sound Category**, **Output Model**, attenuation, and flags as copied from the vanilla template for D0. We only need “it plays.” If volume is wrong later, we retune the golden template once, then clone.

Avoid setting **Loop** unless you want the whisper to loop forever.

### 9. Important: don’t leave it as a silent override of UI sounds

Because we used **Copy as override**, the FormID is still the **vanilla** FormID. That would replace the original UI sound for everyone using the esp — bad.

For the golden whisper we want a **new** record owned by our mod:

#### Option A — preferred in recent xEdit: deep copy / change FormID

1. Right-click your edited record under `PickmansWhisper.esp`.
2. Look for **Change FormID** or **Deep copy as override into…** / **Copy as new record into…** (wording varies by FO4Edit version).
3. Target: `PickmansWhisper.esp`.
4. When asked for a new FormID, let xEdit assign the next free ID in our plugin (or pick an unused `xx0008xx` in our range — our esp already uses low IDs around `0800`–`0805` for quest/spell; use something clearly free, e.g. start whisper SNDRs at **`00000810`** if offered a manual ID: full FormID becomes `01000810` with our load index, but xEdit usually shows the local object ID).

If you only see **Copy as new record into…**:

1. Use that into `PickmansWhisper.esp`.
2. Set EDID `PW_Whisper_EndIt` and path `Sound\PickmansWhisper\EndIt.xwm` on the **new** record.
3. **Remove** the temporary override of the vanilla UI SNDR from `PickmansWhisper.esp` (right-click that override → **Remove**), so we don’t ship a UI sound override.

#### Option B — if stuck: ask in Discord / leave a note

Ship only a **new** SNDR FormID under `PickmansWhisper.esp`. Never ship an override that replaces `UIMenuOK` (or similar) in the wild.

After this step you should have:

- One SNDR under **only** `PickmansWhisper.esp`
- EDID: `PW_Whisper_EndIt`
- File: `Sound\PickmansWhisper\EndIt.xwm`
- Its own FormID (not a vanilla FormID)

Write down the **FormID** shown in xEdit (e.g. `01000810` — the first byte changes with load order; the last six hex digits `000810` are what scripts often use with `GetFormFromFile`).

---

## Save and exit

1. Top menu: **File → Save** (or Ctrl+S).
2. Check `PickmansWhisper.esp` → OK.
3. Close FO4Edit.
4. If MO2 prompts about the esp changing, keep the mod’s copy as the source of truth in the git repo: copy the saved esp back into  
   `d:\GitHub\pickmans-whisper\Data\PickmansWhisper.esp`  
   if FO4Edit wrote through the MO2 overwrite/deploy path.

---

## Quick checklist

- [ ] `EndIt.xwm` exists at `Data/Sound/PickmansWhisper/EndIt.xwm` in the mod
- [ ] FO4Edit run via MO2 (if you use MO2)
- [ ] SNDR EDID `PW_Whisper_EndIt` in `PickmansWhisper.esp`
- [ ] Path `Sound\PickmansWhisper\EndIt.xwm`
- [ ] Record is a **new** FormID, not a permanent override of a vanilla UI sound
- [ ] FormID noted for Papyrus / Debug play button
- [ ] Esp saved back into the git `Data/` folder

---

## What happens next (not in this doc)

1. In-game / Debug: script calls `Sound.Play(PlayerRef)` on that form — confirm you hear it.
2. Build tooling can **clone** this golden SNDR (same fields, new FormID / EDID / path) for each row in `Desperate_Audio.txt`.
3. Delivery modes (toast + audio / audio only / toast only) wire up after playback is proven.

If the golden SNDR is silent in-game: confirm the `.xwm` path, that the file is actually deployed by MO2, and that you didn’t leave Loop/attenuation at extreme values. Try copying a different vanilla one-shot as the template and repeat from step 4.

---

## Glossary

| Term | Meaning |
|------|---------|
| **xEdit / FO4Edit** | Plugin record editor (esp/esm). FO4Edit = Fallout 4 version of xEdit. |
| **SNDR** | Sound Descriptor record — the form Papyrus `Sound` plays. |
| **EDID** | Editor ID — human name of the record (`PW_Whisper_EndIt`). |
| **FormID** | Hex ID the game/script uses to find the form. |
| **Override** | Your esp replaces a record from a master. Fine as a temporary copy source; bad if we ship overrides of UI sounds. |
| **Master** | A plugin this esp depends on (`Fallout4.esm`). |
