# Slice F — butcher menu (blade corpse sever)

Aim reticule at a dead adult female, wield **Pickman's Blade**, press **`/`** (`VK_OEM_2` = 191). **Butcher menu** (`Message.Show`) → `Actor.Dismember(part, False, True, False)`.

## Notes

- Key: `RegisterForKey` + `OnKeyDown` on **PlayerAlias**. F4SE uses **Windows VK** codes (Necromantic `N=78`), not DirectX DIK — DIK `53` never fires for `/`.
- Aim: last-activate → camera → faced nearest dead female (Necromantic `FindActors` dead+female+closest) → last butcher.
- MESG must match working FO4 menus (`EDID/DESC/FULL/INAM/DNAM/ITXT` — **no TNAM**).
- Gore: force dismember, **no** ForceBloodyMess (True gibs/explodes heads), **no** force-explode.
- Skip while `NecroSceneActive`. Blade-not-drawn / bad aim toast (not silent).
- MSG `PW_SeverLimbMenu` FormID `0x806` in `PickmansWhisper.esp`.

## Verify

1. Living aim + `/` → toast, no sever.
2. Dead adult female + blade + `/` → butcher menu → Head **severs** (does not explode).
3. Same limb again → already severed.
4. Blade not drawn → toast "draw Pickman's Blade for the butcher menu".
