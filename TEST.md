# Smoke / regression tests — Pickman's Whisper

## Automated (CI / before deploy)

```powershell
python tools\test_blade_detect_contract.py
.\tools\build-deploy-local.ps1
```

`test_blade_detect_contract.py` locks the **B27 blade identity contract**:

| Constant | FormID | Must be |
|----------|--------|---------|
| Combat Knife base | `0x913CA` | WEAP `Knife` (what `GetEquippedWeapon` returns) |
| Bleed OMOD | `0x1E7C20` | `mod_Legendary_Weapon_Bleed` |
| Stealth OMOD | `0x187A10` | `mod_melee_Knife_SerratedStealth` |
| CustomItem mods list | `0x225960` | FLST containing **both** OMODs |
| Template | `0x22595F` | LVLI only — **never** treat as drawn WEAP |

Also asserts the quest script still calls GoE `GetItemIndexesByName` / `GetNthItemHasMod`.

Set `FALLOUT4_ESM` or pass `--esm` if the game is not in a default Steam path.

## Build / deploy

```powershell
.\tools\build-deploy-local.ps1
```

Expect Caprica `.pex`, ESP SPEL+QUST, MO2 deploy, `dist/PickmansWhisper-*.zip`. Script runs the blade contract test first.

## In-game — blade detect (no kill)

1. Quit FO4 fully; load with **B27-goe** (or later) PEX.
2. Equip **Pickman's Blade** (unequip/re-equip once after load if needed).
3. MCM → Debug → **Verify blade detect**.
4. Expect MessageBox: **PASS — Pickman's Blade DRAWN** and GoE name `Pickman's Blade` (base may still say Combat Knife).
5. Equip a **gun** (blade stays in inventory) → Verify again → **FAIL / not drawn**.
6. Equip a plain **Combat Knife** (if you have one) → must **not** PASS as Pickman's.

## Slice B — satiation regression (confirmed working matrix)

Bond + hunger active. Prefer MCM **Kill debug toasts** ON for the first pass.

| # | Weapon | Target | Expect |
|---|--------|--------|--------|
| 1 | Pickman's Blade drawn | Adult **female** settler (was non-hostile when first seen) | Praise + hunger sated |
| 2 | **Gun** drawn, blade **only in inventory** | Same class of target | **No** sate; Last kill ≈ `not blade` |
| 3 | Pickman's Blade | Adult **male** settler | No sate |
| 4 | Pickman's Blade | Hostile-from-first-sight (e.g. raider already mad) | No sate |
| 5 | Pickman's Blade | Essential / robot / ghoul | No sate |

**Do not ship weapon-detect changes** unless #1 and #2 still pass.

Papyrus log: `PickmansWhisper: knife kill #…` only on #1.

## Slice C2 — nearby notice comments

1. Bond + voice toasts ON. Build / Debug shows **`C2-scanDbg`** (or later).
2. Stand near settlers. MCM Debug → **Scan nearby NPCs (raw)**.
3. Expect MessageBox with `GoE living (unfiltered): N` **> 0** and named entries. Row **Nearby NPC scan** updates (`live=N det=M`).
4. If step 3 is zero, notice filters cannot work — fix detection first (same GoE path as kill scan / Necromantic witnesses use detecting).
5. Then Voice → **Test notice** for filtered female comments.

## Slice A — bond / hunger / MCM

1. Enable `PickmansWhisper.esp` (F4SE + GoE). Toast: `Pickman's Whisper ready` / build id.
2. Own the blade or `player.additem 22595f 1` → intro whisper.
3. MCM Hunger: level drifts; debug satiate works.
4. Optional: enter Pickman Gallery → bond without blade.
