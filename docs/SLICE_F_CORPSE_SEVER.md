# Slice F — butcher menu (blade corpse sever)

Aim reticule at a dead adult female, wield **Pickman's Blade**, press **`/`** (`VK_OEM_2` = 191). **Butcher menu** (`Message.Show`) → `Actor.Dismember(part, False, True, False)` for Head / arms / legs. **Cut Off Tits** swaps the corpse onto a slot-33 mutilated-body ARMO and `PlaceAtMe`s the cut-off **MISC** beside her (not a Dismember bone).

## Notes

- Key: `RegisterForKey` + `OnKeyDown` on **PlayerAlias**. F4SE uses **Windows VK** codes (Necromantic `N=78`), not DirectX DIK — DIK `53` never fires for `/`.
- Aim: last-activate → camera → faced nearest dead female (Necromantic `FindActors` dead+female+closest) → last butcher.
- MESG must match working FO4 menus (`EDID/DESC/FULL/INAM/DNAM/ITXT` — **no TNAM**).
- Gore: force dismember, **no** ForceBloodyMess (True gibs/explodes heads), **no** force-explode.
- Skip while `NecroSceneActive`. Blade-not-drawn / bad aim toast (not silent).
- MSG `PW_SeverLimbMenu` FormID `0x806` in `PickmansWhisper.esp`.
- **Cut Off Tits** (implemented — awaiting in-game confirm): ARMA/ARMO `0x87C`/`0x87D` + weighted MISC `0x87E` (Havok drop). Debug SM-arm MISC `0x87F` remains in the ESP (FormID stability) but is **not** spawned.

### Cut Off Tits assets

- Body: `Data/Meshes/PickmansWhisper/Characters/FemaleBody_Mutilated_Tits.nif` — Fusion Girl Reduced + vanilla `basehumanFemaleskin.bgsm` / `FemaleBody_d.dds`.
- Prop: `Data/Meshes/PickmansWhisper/Props/FemaleBody_Prop_Tits.nif` — same skin on the flesh; cut surface uses vanilla **`Materials\Gore\GoreHumanLeg.BGSM`**. Re-export must keep that gore material. Collision (hull) is **Blender/PyNifly-baked**. `python tools/add_prop_tits_havok.py` writes **BSXFlags = 194**, points `bhkNPCollisionObject` Target at **Scene Root**, patches **bodyID 0** + **SYNC_ON_UPDATE**, writes Havok **Clutter** layer (PyNifly's BodyCInfo layer 255 is not pushable junk), and clears **FACEGEN_RGB_TINT** / sets **DOUBLE_SIDED** on the GoreHumanLeg cap (facegen tint on a MISC gore material does not render). It verifies layer **Clutter or Prop** and material **Flesh** when those fields are readable — it does not write hull bytes.
- Unused debug MISC: `PickmansWhisper_DebugGoreSuperMutantArmL` (`0x87F`) — kept in the ESP so FormIDs stay put. Not spawned.

## Verify

1. Living aim + `/` → toast, no sever.
2. Dead adult female + blade + `/` → butcher menu → Head **severs** (does not explode).
3. Same limb again → already severed.
4. Blade not drawn → toast "draw Pickman's Blade for the butcher menu".
