# Slice F — butcher menu (blade corpse sever)

Aim reticule at a dead adult female, wield **Pickman's Blade**, press **`/`** (`VK_OEM_2` = 191). **Butcher menu** (`Message.Show`) → `Actor.Dismember(part, False, True, False)` for Head / arms / legs. **Cut Off Tits** swaps the corpse onto a slot-33 mutilated-body ARMO and `PlaceAtMe`s the cut-off **MISC** beside her (not a Dismember bone).

## Notes

- Key: `RegisterForKey` + `OnKeyDown` on **PlayerAlias**. F4SE uses **Windows VK** codes (Necromantic `N=78`), not DirectX DIK — DIK `53` never fires for `/`.
- Aim: last-activate → camera → faced nearest dead female (Necromantic `FindActors` dead+female+closest) → last butcher.
- MESG must match working FO4 menus (`EDID/DESC/FULL/INAM/DNAM/ITXT` — **no TNAM**).
- Gore: force dismember, **no** ForceBloodyMess (True gibs/explodes heads), **no** force-explode.
- Skip while `NecroSceneActive`. Blade-not-drawn / bad aim toast (not silent).
- MSG `PW_SeverLimbMenu` FormID `0x806` in `PickmansWhisper.esp`.
- **Cut Off Tits** (implemented — awaiting in-game confirm): ARMA/ARMO `0x87C`/`0x87D` + weighted MISC `0x87E` (Havok drop). Sanity spawn: MISC `0x87F` uses vanilla `Actors\Supermutant\CharacterAssets\GoreSuperMutantArmL.nif` on the opposite side (same PlaceAtMe / MoveTo / InitHavok / Dynamic / impulse path) so Havok on the tits prop can be compared in-game.

### Cut Off Tits assets

- Body: `Data/Meshes/PickmansWhisper/Characters/FemaleBody_Mutilated_Tits.nif` — Fusion Girl Reduced + vanilla `basehumanFemaleskin.bgsm` / `FemaleBody_d.dds`.
- Prop: `Data/Meshes/PickmansWhisper/Props/FemaleBody_Prop_Tits.nif` — same skin on the flesh; cut surface uses vanilla **`Materials\Gore\GoreHumanLeg.BGSM`**. Re-export must keep that gore material. Collision (hull + layer/material) is **Blender/PyNifly-baked**. `python tools/add_prop_tits_havok.py` writes **BSXFlags = 74** (Havok | Complex | Dynamic) and points `bhkNPCollisionObject` Target at **FusionGirlReduced** (not Scene Root). It verifies layer **Clutter or Prop** and material **Flesh** when those fields are readable — it does not write hull bytes.
- Havok sanity MISC: `PickmansWhisper_DebugGoreSuperMutantArmL` (`0x87F`) — vanilla Super Mutant left-arm gore mesh (BA2 path; not copied into this repo). Spawned opposite the tits prop on Cut Off Tits.

## Verify

1. Living aim + `/` → toast, no sever.
2. Dead adult female + blade + `/` → butcher menu → Head **severs** (does not explode).
3. Same limb again → already severed.
4. Blade not drawn → toast "draw Pickman's Blade for the butcher menu".
