# Decay face decals (Slice I) — recreate guide

**Status:** Stage 0 (“decently deceased”) face-decal ARMO works in-game while **keeping FaceGen** (real face identity). Stages 1–4 = recolor DDS in a photo editor toward black putrefaction; ship one NIF/BGSM set (or tinted texture set) per ModConfig decay stage.

**Hard no:** FaceGen Head **slot 32** full-head swap (identical BaseFemaleHead on every corpse).

**Working biped:** **54 - [Unnamed]** on both ARMA and ARMO.

**This mod’s paths (examples):**

- Mesh: `Meshes\PickmansWhisper\Decay\NecroBaseFemaleHead.nif`
- Materials: `Materials\PickmansWhisper\Decay\Necro_*_d.bgsm`
- Textures: `Textures\PickmansWhisper\Decay\Necro_*_d.DDS`

Script equip / stage swap comes later; art pipeline is author-owned. Do **not** rely on a chemistry crafting recipe for gameplay — CK recipe below is optional for manual testing only.

Cross-ref: [ROADMAP.md](ROADMAP.md) Slice I · [SLICE_H_CORPSE_DECAY.md](SLICE_H_CORPSE_DECAY.md) stage clock.

---

## Step 1: Material Creation (.BGSM)

Always start here so your asset paths are locked in before you touch any 3D models.

1. Open the Fallout 4 Material Editor.
2. **Textures** tab: Link your `_d.dds` and `_n.dds` relative paths (e.g. `textures\PickmansWhisper\Decay\Necro_Bruising01_d.DDS`).
3. **General** tab:
   - **Alpha Blend Mode:** Standard.
   - **Decal:** CHECK (depth-bias so the mesh sits flat on skin).
   - **Alpha Test:** UNCHECK (smooth transparency gradients).
   - **Alpha Test Ref:** Leave at 0.

For later stages: duplicate the stage-0 DDS set, recolor in a photo editor (bruise → green/gray → black putrefaction), point each stage’s BGSMs at those files. Keep the same NIF layering unless a stage needs different coverage.

---

## Step 2: NIF Configuration (NifSkope)

Prepare the 3D geometry to cleanly receive your material files.

1. Open your mesh in NifSkope.
2. Right-click the shape node → **Block > Convert > Bethesda > BSTriShape**.
3. Expand the **BSTriShape** → select **BSLightingShaderProperty**.
4. In Block Details, set **Name** to the relative material path (e.g. `materials\PickmansWhisper\Decay\Necro_Bruising01_d.bgsm`).
5. Right-click the **BSTriShape** → **Node > Attach Property > NiAlphaProperty**. Set **Flags** to exactly **4844**.
6. On **BSLightingShaderProperty**:
   - **Shader Flags 1:** Check **Specular**, **Decal**, and **ZBuffer_Test** only. Uncheck **Skinned**, **Face**, **Cast_Shadows**, and **Own_Emit**.
   - **Shader Flags 2:** **SLSF2_ZBuffer_Write** must be UNCHECKED.
7. Stacking multiple non-overlapping decals: **duplicate shapes** (one material per shape), order bottom→top with **Block > Move Up / Move Down**. One shape cannot wear twelve BGSMs at once.

---

## Step 3: Outfit Studio sanity & segment check

1. **Visual check:** Use Outfit Studio inflation tool to raise any decals that are being clipped by the corpses face.

---

## Step 4: Creation Kit (ARMA + ARMO)

### Armor Addon (ARMA)

1. Items → ArmorAddon → New.
2. Unique ID (e.g. `PickmansWhisper_DecayFace_Green_ARMA`), Race **HumanRace**.
3. Biped Model → Female (and Male if needed) → select your `.nif`.
4. Biped Object: **54 - [Unnamed]** only (not 32 FaceGen Head).
5. OK.

### Armor (ARMO)

1. Items → Armor → New.
2. Unique ID (e.g. `PickmansWhisper_DecayFace_Stage0_ARMO`), Name for debug (e.g. “Decayed Face 0”).
3. Biped Object: same **54 - [Unnamed]**.
4. Models → New → pick the ARMA above.
5. OK → File → Save plugin.

Repeat ARMA/ARMO (or shared mesh + stage materials) for stages **1–4** after textures are recolored. Keep FormIDs stable once scripts start equipping by stage.

### Optional: crafting recipe (manual test only)

Constructible Object → chemistry workbench is fine for *you* to spawn/equip while art-testing. Ship path for Pickman’s Whisper is script `EquipItem` on knife-tracked corpses — no player craft UI required.

---

## Stage plan (art)

| ModConfig stage | Look (author) | Notes |
| --- | --- | --- |
| 0 | Decently deceased (current) | Working reference NIF + DDS/BGSM |
| 1–3 | Worsening bruise / discolor | Recolor DDS; same mesh layering if possible |
| 4 | Black putrefaction | Darkest set |

After each stage’s assets land under `Data\`, deploy copies them via `Sync-DataTree` (Materials / Meshes / Textures).

**ESP:** `tools/build_hunger_spell_esp.py` emits ARMA/ARMO (biped **54**) for every head NIF it finds:

- Base: `Meshes\PickmansWhisper\Decay\NecroBaseFemaleHead.nif`
- Color variants: `NecroBaseFemaleHead_<Color>.nif` (e.g. `_Green`, `_Gray`, `_Black`)

EDIDs / FULL include the color so console Help works, e.g. `help DecayFace 4` or `help Green 4`:

- ARMO EDID: `PickmansWhisper_DecayFace_Green_ARMO`
- FULL: `PW DecayFace Green`

FormIDs are written to `Data/PickmansWhisper/config/DecayFaceArmorIds.txt` (`label=armaLocalFid,armoLocalFid`). Drop a new `_Color.nif` and redeploy to get another pair.

**Stage map (script equip):** [`DecayFaceStages.txt`](../Data/PickmansWhisper/config/DecayFaceStages.txt) — `0=Base`, `1=Gray`, `2=Red`, `3=Green`, `4=Black`. `CorpseDecayScript.ApplyDecayStageOverlays` strips prior PW face ARMOs and `EquipItem`s the stage piece (`abPreventRemoval=false` so it stays playable/removable).

---

Reference for slot-54 face-decal patterns: [signature-sl.fr manual](https://signature-sl.fr/manual).
