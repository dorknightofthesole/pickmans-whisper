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

## Step 1: Blender — two shapes and a collision box

The prop NIF needs exactly three things.

1. **Root node named `Scene Root`.** The patcher hangs `bhkNPCollisionObject` on it by name (`COLLISION_TARGET_NAME`), and `PlaceAtMe` uses it as the motion root.
2. **A flesh shape and a cut-cap shape**, as separate shapes so they can carry different materials. Cut Off Tits uses `SeveredTits001:5` (flesh) and `SeveredTitsBack002` (the cut surface).
   - The cap shape name is a **contract**: `GORE_CAP_SHAPE` in `tools/add_prop_tits_havok.py` matches it exactly or as a `Name:0` prefix. Rename the shape in Blender and the build fails loudly with `missing cut cap shape`.
   - Cap the hole. An open mesh reads as a hollow shell from behind.
3. **A third object: a box wrapping the part.** This is the collision body, and it is a separate mesh alongside the two visible shapes — add a Cube, scale it around the part, and put the physics on **the cube**. The visible meshes get no rigid body and no custom properties. PyNifly exports the cube as a convex polytope. The Python tooling **never** generates collision geometry; Blender is the only source of those verts, and the patcher is explicitly tested to not bake them.
   - Ours is exactly that: **8 verts, 12 faces**, convex radius `0.01`, **21.08 × 10.43 × 12.29** game units.
   - A box is not the only option — any convex mesh exports identically, and a tighter shape settles more believably. If you use a real hull instead, mind the **255-vertex** ceiling (`ConvexPolytopeShape: at most 255 vertices (u8 FVI)` — an assert, so it fails loudly).
   - **Check the box against both visible shapes.** Ours wraps the cut cap well (cap x `[-10.3, 9.9]` vs box x `[-10.5, 10.5]`) but not the flesh, which runs out to x `-26.7` — centre `-8.2` against the box's `0`. Roughly the far half of what's drawn has no collision under it. Worth fixing before calling a part done.
   - Set the body **mass** on the box. This is Havok mass (stored as `1/mass` in the packfile), separate from the MISC inventory weight in Step 4 — they both happen to be `3` today.

### Wiring the box so PyNifly exports FO4 physics

Four things route the box into the FO4 `bhkNPCollisionObject` + `bhkPhysicsSystem` path. Miss any one and the export is silently wrong in a different way. Custom properties go on the **box** object (Object Properties ▸ Custom Properties).

| What | Where | If you skip it |
| --- | --- | --- |
| `pynRigidBody` = `bhkPhysicsSystem` | custom prop on the box | You get Skyrim-style `bhkCollisionObject` / `bhkRigidBody` instead, and the patcher aborts with no NP collision |
| `pynCollisionShapeType` = `polytope` | custom prop on the box | Export drops to its legacy path, which packs verts and faces with **no physics block at all** — no mass, no damping, no motion arrays |
| **Rigid Body, type Active** | `Object ▸ Rigid Body ▸ Add Active`, on the box | `is_dynamic` goes false and the motion + inertia arrays are written with **count 0**. There is no motion for the patcher to repair, so the part is static however correct everything else is |
| A link from the node that hosts it | a **`COPY_TRANSFORMS` constraint** on that node's object, targeting the box (PyNifly calls it `bhkCollisionConstraint`), **or** custom prop `pynCollisionTarget` = the box's object name | The exporter never finds the box and writes no collision at all |

Three things about that constraint, because it is the least obvious part of the setup:

- **`COPY_TRANSFORMS` is the only constraint type PyNifly reads.** Blender's own **Rigid Body Constraint** is never looked at on export — it does nothing for the NIF.
- **It decides where the collision lands.** PyNifly attaches the collision to whichever object carries the link. Our tree is `Scene Root` → `SeveredTits001` → the two `BSTriShape`s, and the export puts the collision below the root, which is why `patch_np_collision_target` moves it back onto `Scene Root` (step 2 of the patch order). You do not have to get this right in Blender, but do not be surprised when NifSkope shows it on the wrong node.
- **Every `COPY_TRANSFORMS` with a target exports as another collision.** The exporter loops over all of them, so a leftover constraint from unrelated rigging quietly doubles the collision. Ours ends up with exactly one NP block; if `np_count` comes back above 1, look here first.

Blender's native rigid-body fields are the ones that do survive export: **Mass** (written as `1/mass`), Friction, Restitution, and both Damping values. With **Margin** enabled its Collision Margin becomes the Havok convex radius; otherwise `collision_radius` from the FO4 Physics panel is used. Ours came through as `0.01`.

Two more properties of the box mesh:

- **Verts are baked in world space.** The box's own location, rotation, and scale are exactly what the collision volume becomes, and it does not need to be parented to the visible mesh — so the fit problem above is fixed by scaling and moving the box in the viewport, nothing more.
- The object's **name is free**. On the FO4 path PyNifly dispatches on the `pynCollisionShapeType` tag, not on a `bhkConvexVerticesShape*` name prefix like the Skyrim path. Ours arrives in the packfile as `Polytope_standalone_0x1c0`, a name the decoder invents.

### The FO4 Physics panel is mostly a trap

Object Properties also gains a **FO4 Physics** group (`inertia`, `gravity_factor`, `max_lin_vel`, `max_ang_vel`, `material_hex`, `collision_radius`) and a **Collision Object** group (`flags`). Gravity factor, the velocity caps, and the material bytes are honoured. The `flags` string is parsed and exported too, so `ACTIVE|SET_LOCAL|SYNC_ON_UPDATE` can be typed there — though the patcher forces `137` regardless.

**Do not try to fix the physics with the `inertia` field.** It defaults to `(0,0,0)`, and the exporter writes whatever you type straight into `m_inverseInertiaLocal` — a field that holds `1/I`, not `I`. A correct inertia tensor entered there lands ~2400x too small while looking deliberately authored. Leave it at zero and let the patcher compute `1/I` from the collision box (Step 3).

### What no amount of Blender fiddling can fix

The three defects in Step 3 are baked into the exporter's byte templates, which is why the patcher has to exist. In the PyNifly addon:

- **bodyID** — `nif/collision.py`: the non-compound NP export calls `add_collision()` with no `body_id`, so it keeps `NODEID_NONE`. Only the compound path plumbs `pynCollisionBodyID` through.
- **motion stride** — `pyn/bhk_autopack.py`: `_DYN_INERTIA_TEMPLATE` is `0x40` bytes behind `assert len(...) == 0x40`. The engine wants `0x70`.
- **motion id** — same file: `_BODY_CINFO` carries `0x7FFFFFFF` at `+0x0C`, under the comment *"one static body at identity transform."*

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

### What the patcher writes, in order

`apply_bsx_and_retarget` runs all of this against the exported NIF. Order matters where noted.

1. Via PyNifly: `BSXFlags = 194`, collision host retarget, `restore_gore_cap_material`, `patch_gore_cap_shader` — then `nif.save()`.
2. `patch_np_collision_target` — `bhkNPCollisionObject` Target → `Scene Root`.
3. `patch_np_collision_flags` — `ACTIVE|SET_LOCAL|SYNC_ON_UPDATE` (137). Gore pieces use `SYNC_ON_UPDATE` alone; world clutter needs `ACTIVE`.
4. `patch_np_body_id` — bodyID `0`.
5. `patch_motion_cinfo_stride` — grow the motion array. **Must run before anything reads offsets inside it.**
6. `patch_body_motion_id` — link each body to its motion.
7. `patch_np_clutter_layer` — collision layer Clutter.
8. `patch_np_inertia_from_hull` — inverse inertia from the collision box AABB (the code calls the collision shape the "hull" throughout; ours happens to be a box).
9. `patch_gore_cap_shader_type` — cap shader → Default.
10. `patch_bsx_loot_flags` — **last**, because `nif.save()` rewrites BSX to gore-pattern `74`.

Everything from 2 down is raw byte surgery on the saved file: PyNifly routes `setBlock` on `bhkNPCollisionObject` to the physics-system setter, where it fails. For the same reason `read_bsx_disk_flags` reads BSX back from the bytes on disk — PyNifly's in-memory `bsx.flags` happily reported `194` while the file on disk held `74`.

### How the motion array is grown

Expanding an array inside a Havok packfile in place would mean shifting every fixup offset after it. Instead the array is **re-emitted at the end of the `__data__` section**, so nothing that already exists has to move. What does change:

- the `__data__` section header offsets (`+0x18`…`+0x2C`: local/global/virtual fixups, exports, imports, end) shift by the added bytes;
- that array's own local fixup is repointed at the new offset;
- **both** NIF length fields — the `bhkPhysicsSystem` block's `u32` byte count *and* its entry in the NIF block-size table. Leaving the second one stale makes every block after it unreadable.

Each element keeps its original bytes and gains a real `m_orientation`, copied from its body (identity if the body's is degenerate). The old bytes stay behind as unreferenced padding. Appends must stay 16-byte aligned; the patcher throws rather than break that.

### What the gate enforces

These run in `test_corpse_sever.py` against the built NIF, so a re-export cannot quietly put the part back to static:

| Verifier | Rejects |
| --- | --- |
| `verify_motion_cinfo_stride` | a short motion array; any non-unit motion orientation |
| `verify_body_motion_ids` | the invalid motion-id sentinel; ids with no matching motion |
| `verify_np_inertia` | missing, all-zero, or direct `I` where `1/I` belongs |
| `verify_np_instance_fields` | `NODEID_NONE` bodyID; wrong NP collision flags |
| `verify_bsx_flags`, `verify_collision_target` | BSX ≠ 194; collision not on `Scene Root` |
| `verify_collision_meta`, `verify_gore_cap_shader` | non-Clutter layer, non-Flesh material, missing cap shape, cap still Skin Tint / FACEGEN, cap not double-sided |

`verify_np_inertia` recomputes the expected `1/I` from the collision box and compares, so it is a law check rather than a pinned constant. There is also a pure-Python test that feeds each defect to its verifier and asserts it is rejected — that one runs even if the NIF is absent.

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
| Sits inside the floor or shoves from the wrong spot | Collision box does not match the visible mesh (Step 1) |
| Change had no effect at all | Deployed NIF hash differs from source, or the game was not restarted |

---

## Adding a second severed part

The tooling is currently **single-part**. A new part means widening these, not copy-pasting a second script:

- `add_prop_tits_havok.py`: `NIF_PATH` and `GORE_CAP_SHAPE` are single values today.
- `build_hunger_spell_esp.py`: `FID_*` and `*_MESH_REL` constants, plus a payload builder per record.
- `PickmansWhisperCorpseDecayScript`: a `Resolve*Misc()` + spawn offsets per part, and a butcher-menu entry.
- `test_corpse_sever.py`: extend the existing contracts rather than adding a parallel test file.

Prefer driving the list from one table so the NIF, the MISC, and the menu entry cannot drift apart.
