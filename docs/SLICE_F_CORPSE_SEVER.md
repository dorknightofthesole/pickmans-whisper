# Slice F — butcher menu (blade corpse sever)

Aim reticule at a dead adult female, wield **Pickman's Blade**, press **`/`** (`VK_OEM_2` = 191). **Butcher menu** (`Message.Show`) → `Actor.Dismember(part, False, True, False)` for Head / arms / legs. **Cut Off Tits** swaps the corpse onto a slot-33 mutilated-body ARMO and `PlaceAtMe`s the cut-off **MISC** beside her (not a Dismember bone).

## Notes

- Key: `RegisterForKey` + `OnKeyDown` on **PlayerAlias**. F4SE uses **Windows VK** codes (Necromantic `N=78`), not DirectX DIK — DIK `53` never fires for `/`.
- Aim: last-activate → camera → faced nearest dead female (Necromantic `FindActors` dead+female+closest) → last butcher.
- MESG must match working FO4 menus (`EDID/DESC/FULL/INAM/DNAM/ITXT` — **no TNAM**).
- Gore: force dismember, **no** ForceBloodyMess (True gibs/explodes heads), **no** force-explode.
- Skip while `NecroSceneActive`. Blade-not-drawn / bad aim toast (not silent).
- MSG `PW_SeverLimbMenu` FormID `0x806` in `PickmansWhisper.esp`.
- **Cut Off Tits** (**verified in-game** — falls, rests, loots, pushable): ARMA/ARMO `0x87C`/`0x87D` + weighted MISC `0x87E` (Havok drop). Debug SM-arm MISC `0x87F` remains in the ESP (FormID stability) but is **not** spawned.

### Cut Off Tits assets

Step-by-step pipeline for building a severed part (Blender → materials → Havok → ESP → spawn → verify): [Severed_Part_Guide.md](Severed_Part_Guide.md).

- Body: `Data/Meshes/PickmansWhisper/Characters/FemaleBody_Mutilated_Tits.nif` — Fusion Girl Reduced + vanilla `basehumanFemaleskin.bgsm` / `FemaleBody_d.dds`.
- Prop: `Data/Meshes/PickmansWhisper/Props/FemaleBody_Prop_Tits.nif` — same skin on the flesh; cut surface uses vanilla **`Materials\Gore\GoreHumanLeg.BGSM`**. Re-export must keep that gore material. Collision (hull) is **Blender/PyNifly-baked**. `python tools/add_prop_tits_havok.py` writes **BSXFlags = 194**, points `bhkNPCollisionObject` Target at **Scene Root**, patches **bodyID 0** + **ACTIVE|SET_LOCAL|SYNC_ON_UPDATE**, writes Havok **Clutter** layer (PyNifly's BodyCInfo layer 255 is not pushable junk), applies the three **static-body** fixes below, and clears **FACEGEN_RGB_TINT** / sets **DOUBLE_SIDED** on the GoreHumanLeg cap (facegen tint on a MISC gore material does not render). It verifies **on-disk** BSX 194 (PyNifly `nif.save()` writes gore 74) plus layer **Clutter or Prop** and material **Flesh** when those fields are readable — it does not write hull bytes. Spawn: `PlaceAtMe` initially disabled, `MoveTo`, `Enable`, then `InitHavok` (MoveTo on a live MISC keyframes it).
- Unused debug MISC: `PickmansWhisper_DebugGoreSuperMutantArmL` (`0x87F`) — kept in the ESP so FormIDs stay put. Not spawned.

### Why the prop was static (Havok packfile)

Reference for all three: vanilla `Meshes/Actors/Supermutant/CharacterAssets/GoreSuperMutantArmL.nif`, which falls and can be pushed. `python tools/compare_prop_havok.py [reference.nif]` re-runs the side-by-side diff.

| Field | PyNifly wrote | Vanilla | Effect |
| --- | --- | --- | --- |
| `hknpBodyCinfo.m_motionId` (+0x0C) | `0x7FFFFFFF` (default) | `0`/`1`/`2` | No motion = **static**: collides and loots, never falls or pushes |
| `sizeof(hknpMotionCinfo)` | `0x40` | `0x70` | `m_orientation` (+0x40) read out of the following bodyCinfo array = **NaN quaternion** |
| `m_inverseInertiaLocal` (+0x20) | box `I` (and `0` before that) | `1/I` | ~2400x too much inertia; `0` is infinite inertia |

Havok stores **inverse** inertia here — the sibling field at +0x04 is `1/mass`. Measured against all three vanilla gore bodies, `stored * boxInertia == 2/3` on every axis, hence `INV_INERTIA_BOX_FACTOR`.

The motion array is re-emitted at the end of the `__data__` section rather than expanded in place, so no existing fixup offset moves — only the `__data__` section header offsets, the array's own local fixup, and the two NIF length fields change.

Still divergent from vanilla and **untested**, in case physics is ever wrong again: `BSXFlags` 194 vs 74, NP flags 137 vs 128, `hknpBodyCinfo.m_flags` (+0x14) `1` vs `0x8013`.

### Blender-side follow-up

The collision hull does not match the visible mesh: mesh `SeveredTits001:5` spans x `[-26.7, 10.2]` centred at `-8.2`, the hull spans roughly `[-10.5, 10.5]` centred at `0`. It will settle and be pushable, but the pushable volume sits offset from what is drawn. Re-fit the hull around the actual mesh in Blender before calling the prop done.

## Verify

1. Living aim + `/` → toast, no sever.
2. Dead adult female + blade + `/` → butcher menu → Head **severs** (does not explode).
3. Same limb again → already severed.
4. Blade not drawn → toast "draw Pickman's Blade for the butcher menu".
