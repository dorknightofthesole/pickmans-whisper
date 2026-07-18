# Slice F — blade corpse sever

Aim reticule at a dead adult female, wield **Pickman's Blade**, press **`/`** (DX scancode 53). Limb picker (`Message.Show`) → `Actor.Dismember(part, False, True, True)`.

## Notes

- Reticule selects the **corpse** only (GoE camera target). Limb under crosshair is not available in FO4 Papyrus.
- Gore: force dismember + bloody mess, **not** explode (severed piece stays visible).
- Skip in menu mode and while `NecroSceneActive`.
- MSG `PW_SeverLimbMenu` FormID `0x806` in `PickmansWhisper.esp`.

## Verify

1. Living aim + `/` → no sever.
2. Dead adult female + blade + `/` → menu → Head severs with gore.
3. Same limb again → already severed.
4. Blade not drawn → silent skip.
