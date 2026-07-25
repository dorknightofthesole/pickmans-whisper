# Slice I — Desperate hunger rename

At notice stage **desperate** (`GetNoticeStage() == 4`), Pickman's Whisper appends a knife-voice insult to nearby eligible NPCs so the HUD name and notice `{name}` push the player toward violence.

## Behavior

| When | What |
| --- | --- |
| Desperate | For each KillerScan `ScanAlive` actor that passes notice eligibility (`ExplainNoticeReject` ignore-cooldown), `GardenOfEden2.SetDisplayName(base + suffix)`. |
| Not desperate | Strip the known suffix from nearby display names (restore readable label). |
| Idempotent | Never double-append; suffix from `ModConfig.txt` only. |

## Config (single source)

```
desperateNameSuffix= Dumb Bitch
```

Leading space is intentional (reads as `Name Dumb Bitch`). Empty / missing → feature idle (Trace once; no hard-coded fallback string).

## Scripts

- `PickmansWhisperDesperateRenameScript` on Main quest — owns apply/strip.
- KillerScan `DispatchListeners` → `CallFunctionNoWait("SyncFromKillerScanSnapshot")` (additive; does not touch arming).
- Main `GetActorDisplayName` → `MaybeSuffixDisplayName` so toast `{name}` matches mouseover while desperate.

## Filters

Same spirit as notice/kill: adult female humans, no essential/story, no children/teammates/non-humans. Never rename essentials.

## Status

I1/I2 implemented — **awaiting in-game confirm**. Do not mark Done until verified.
