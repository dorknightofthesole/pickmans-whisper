# Severed body part (butcher prop) — recreate guide

How a butcher-menu body part goes from Blender to a prop that **falls, rests, loots, and can be shoved**. Written from the Cut Off Tits build; every step below is something that actually bit us.

Cross-ref: [SLICE_F_CORPSE_SEVER.md](SLICE_F_CORPSE_SEVER.md) (slice notes + Havok field table) · [Decay_Head_Guide.md](Decay_Head_Guide.md) (slot-54 face art).

## A severed part is two assets, not one

| Half | What it is | Cut Off Tits example |
| --- | --- | --- |
| Corpse-side | A **slot-33 ARMO** worn by the corpse, whose mesh has the part removed | `Meshes\PickmansWhisper\Characters\FemaleBody_Mutilated_Tits.nif` → ARMA `0x0100087C` / ARMO `0x0100087D` |
| World-side | A **weighted MISC** `PlaceAtMe`'d beside her, with Havok collision | `Meshes\PickmansWhisper\Props\FemaleBody_Prop_Tits.nif` → MISC `0x0100087E` |

Only the world-side half needs Havok. Parts that FO4 already has a gore bone for should use `Actor.Dismember` instead — this pipeline exists because there is no breast gore bone.

---

## Step 1: Blender — two shapes and a hull

The prop NIF needs exactly three things.

1. **Root node named `Scene Root`.** The patcher hangs `bhkNPCollisionObject` on it by name (`COLLISION_TARGET_NAME`), and `PlaceAtMe` uses it as the motion root.
2. **A flesh shape and a cut-cap shape**, as separate shapes so they can carry different materials. Cut Off Tits uses `SeveredTits001:5` (flesh) and `SeveredTitsBack002` (the cut surface).
   - The cap shape name is a **contract**: `GORE_CAP_SHAPE` in `tools/add_prop_tits_havok.py` matches it exactly or as a `Name:0` prefix. Rename the shape in Blender and the build fails loudly with `missing cut cap shape`.
   - Cap the hole. An open mesh reads as a hollow shell from behind.
3. **A convex-hull collision body**, exported by PyNifly. The Python tooling **never** generates hull geometry — Blender is the only source of hull verts, and the patcher is explicitly tested to not bake them.
   - **Fit the hull to the visible mesh.** Ours does not (mesh spans x `[-26.7, 10.2]` centred at `-8.2`; hull spans about `[-10.5, 10.5]` centred at `0`), so the shovable volume sits offset from what's drawn. Check this before calling a part done.
   - Set the body **mass** here. This is Havok mass (stored as `1/mass` in the packfile), separate from the MISC inventory weight in Step 4 — they both happen to be `3` today.

---

## Step 2: Materials

- **Flesh:** the same skin the body uses — vanilla `basehumanFemaleskin.bgsm` / `FemaleBody_d.dds`.
- **Cut cap:** vanilla **`Materials\Gore\GoreHumanLeg.BGSM`** (`GORE_CAP_BGSM`).

Blender re-export tends to put skin on *both* shapes, so `restore_gore_cap_material` rewrites the cap's shader name back to the gore BGSM on every build. You do not have to fix it by hand, but do not fight it either.

A MISC lying on the ground has no actor tint, so the patcher also forces the cap shader to **Default** (not Skin Tint), clears **FACEGEN_RGB_TINT**, and sets **DOUBLE_SIDED**. A facegen-tinted skin shader on a dropped mesh renders as nothing.

---

## Step 3: The Havok packfile — what the exporter gets wrong

This is the part that cost us the most time. PyNifly writes a `bhkPhysicsSystem` that **looks** complete in Blender and in NifSkope, but is missing three things the engine needs. All three are patched automatically by `tools/add_prop_tits_havok.py`; none of them are fixable in Blender or NifSkope (NifSkope shows the packfile as an opaque blob on FO4).

Ground truth for all of it: vanilla `Meshes\Actors\Supermutant\CharacterAssets\GoreSuperMutantArmL.nif`, which falls and can be pushed.

| Field | Exporter writes | Vanilla | Symptom if unfixed |
| --- | --- | --- | --- |
| `hknpBodyCinfo.m_motionId` (+0x0C) | `0x7FFFFFFF` (its default) | a real index | **The whole bug.** A body with no motion is Havok's definition of static: it collides and loots, but never falls and cannot be shoved. |
| `sizeof(hknpMotionCinfo)` | `0x40` | `0x70` | The array is 0x30 short per element, so `m_orientation` (+0x40) is read out of the bodyCinfo array that follows and comes back as a **NaN quaternion**. |
| `m_inverseInertiaLocal` (+0x20) | `0`, or direct `I` | `1/I` | Havok stores **inverse** inertia here (its neighbour at +0x04 is `1/mass`). Zero means infinite inertia; direct `I` was ~2400x too small. Either way the part will not tumble. |

The patcher also writes `bodyID 0` into the 14-byte `bhkNPCollisionObject` (PyNifly leaves `NODEID_NONE`, which FO4 uses as a body-array index and access-violates on), sets collision layer **Clutter**, and writes `BSXFlags = 194` **last**, because `nif.save()` overwrites it with gore-pattern `74`.

To re-derive any of this against a vanilla reference:

```powershell
python tools/compare_prop_havok.py "C:\path\to\SomeVanillaGore.nif"
```

It dumps blocks, `BSXFlags`, the NP block, node/mesh bounds, and the decoded packfile for the reference and for our prop side by side.

### Why the inertia constant is 2/3

`INV_INERTIA_BOX_FACTOR` is not a fudge. Using the correct `0x70` stride, `stored × boxInertia` comes out to exactly `2/3` on all nine axes across the three vanilla gore bodies — a constant that only holds if the field is inverse inertia. If a future reference disagrees, re-measure rather than nudging the number.

---

## Step 4: ESP records

`tools/build_hunger_spell_esp.py` emits these; the CK is not used.

**MISC (the dropped prop)** — `build_cut_off_tits_misc_payload`:

- `EDID` `PickmansWhisper_PropCutOffTits`
- `OBND` — AABB taken from the prop's verts in game units, padded by 1
- `FULL` — the loot name the player reads
- `MODL` — mesh path relative to `Meshes\`
- `MODT` — minimal texture-hash stub
- `DATA` — inventory value and **weight**. Weight is what makes it a carryable, droppable object; it is not the Havok mass.

**ARMA + ARMO (the corpse-side body)** — biped **slot 33**, `MOD3` pointing at the mutilated body NIF, ARMO's `MODL` pointing at the ARMA.

Keep FormIDs stable once anything has spawned in a save. The retired debug MISC `0x87F` is still in the ESP for exactly that reason.

---

## Step 5: Papyrus — how it gets dropped

`PickmansWhisperCorpseDecayScript.DropHavokMiscBeside` is the only correct spawn order, and each line is load-bearing:

```papyrus
; Initially disabled: MoveTo on a live 3D MISC keyframes it, and kicks never take.
ObjectReference placed = akCorpse.PlaceAtMe(misc, 1, False, True)
placed.MoveTo(akCorpse, offsetX, offsetY, offsetZ, False)
placed.Enable(False)
; ... wait for Is3DLoaded (guarded, up to ~2s) ...
GardenOfEden.InitHavok(placed)
placed.SetMotionType(placed.Motion_Dynamic, True)
placed.ApplyHavokImpulse(0.0, 0.0, -1.0, 8.0)
```

- **Spawn disabled, then `MoveTo`, then `Enable`.** Moving a MISC that already has 3D keyframes it in Havok — it will hang in the air no matter how correct the NIF is.
- **Wait for `Is3DLoaded`.** `InitHavok` in the same frame as `Enable` silently no-ops. The wait is safe here because this is the butcher-menu path, not a hot event stack.
- **The small downward impulse** is what wakes the body so it settles instead of hovering until something touches it.

The caller (`ApplyMutilatedBodyOnCorpse`) equips the ARMO first, confirms it landed with `GetItemCount`, and only then spawns the prop — so a failed body swap never leaves a floating part with an intact corpse.

---

## Step 6: Build, deploy, verify

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build-deploy-local.ps1
```

The gate runs `add_prop_tits_havok.py` and then `test_corpse_sever.py` before it syncs anything. **Do not run the patcher by hand** — it edits the NIF in place, and the gate is what guarantees the patched file is the one that ships.

Two deploy traps we already hit:

- `Copy-Item -Recurse -Force` does not reliably overwrite an existing NIF at the destination, so `Sync-Tree` copies file by file. The gate then hash-compares the source and deployed prop NIF and throws on mismatch. If you ever see a fix "do nothing" in-game, check that hash first.
- `build-deploy-local.ps1` must stay pure ASCII. It has no BOM, so Windows PowerShell 5.1 reads an em dash as cp1252 and a smart quote terminates the string early.

In-game check, in order:

1. The part **falls** and rests on the floor, not mid-air.
2. You can **shove it** by walking into it.
3. It is **lootable** and the name matches `FULL`.
4. The cut surface **renders** (gore material, not invisible).
5. The corpse shows the mutilated body, not a default one.

---

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Floats, loots fine, cannot be pushed | Static body — `m_motionId` left on `0x7FFFFFFF`, or the prop was `MoveTo`'d while enabled |
| Falls but never tumbles / rotates like a brick | Inverse inertia is zero or was written as direct `I` |
| Part vanishes or teleports oddly | NaN in the motion — short `hknpMotionCinfo` array, non-unit orientation |
| CTD on spawn (Buffout names the MISC) | `bhkNPCollisionObject` bodyID left as `NODEID_NONE` |
| Cut surface invisible | Cap shader is Skin Tint / FACEGEN_RGB_TINT, or the cap lost `GoreHumanLeg.BGSM` |
| Sits inside the floor or shoves from the wrong spot | Hull does not match the visible mesh (Step 1) |
| Change had no effect at all | Deployed NIF hash differs from source, or the game was not restarted |

---

## Adding a second severed part

The tooling is currently **single-part**. A new part means widening these, not copy-pasting a second script:

- `add_prop_tits_havok.py`: `NIF_PATH` and `GORE_CAP_SHAPE` are single values today.
- `build_hunger_spell_esp.py`: `FID_*` and `*_MESH_REL` constants, plus a payload builder per record.
- `PickmansWhisperCorpseDecayScript`: a `Resolve*Misc()` + spawn offsets per part, and a butcher-menu entry.
- `test_corpse_sever.py`: extend the existing contracts rather than adding a parallel test file.

Prefer driving the list from one table so the NIF, the MISC, and the menu entry cannot drift apart.
