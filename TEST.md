# Smoke tests — Pickman's Whisper

## Build / deploy (automated)

```bash
# Git Bash
./tools/build-deploy-local.sh
```

```powershell
# PowerShell
.\tools\build-deploy-local.ps1
```

Expect Caprica `.pex`, ESP SPEL+QUST, MO2 deploy, `dist/PickmansWhisper-0.2.0.zip`.

## Slice A — bond / hunger / MCM

1. Enable `PickmansWhisper.esp` (F4SE). Toast: `Pickman's Whisper ready`.
2. Already own the blade or `player.additem 22595f 1` → intro whisper; Debug shows equipped / owned.
3. MCM Hunger: level drifts; push to addicted / satiate (debug) work.
4. Optional: enter Pickman Gallery → bond without blade.

## Slice B — knife kills

1. Bond + equip **Pickman's Blade**.
2. MCM Hunger → push hunger high (or wait for drip).
3. Kill a **non-essential human** raider/settler (not a named essential) with the blade.
4. Expect: praise toast; hunger **0**; sated yes; bond intensity / kills tick up on Hunger panel.
5. Kill with another weapon while blade unequipped → hunger should **not** clear.
6. Essential / robot / ghoul kills with blade → no satiation.

Papyrus log: `PickmansWhisper: knife kill #…`
