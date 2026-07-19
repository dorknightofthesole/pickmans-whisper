# Slice D audio

## Runtime model

| Role | Location |
|------|----------|
| Toast text | `config/NoticeLines_<Stage>.txt` |
| Audio map | `config/<Stage>_Audio.txt` — one **`.xwm`** filename per notice row |
| Clips | `Data/Sound/PickmansWhisper/` (top-level + `Necromantic/Start|End/`) |
| SNDR forms | `PickmansWhisper.esp` — EDID `PW_Whisper_<Stem>` |
| FormID table | `config/WhisperSndrIds.txt` (**generated** by esp build) |

Papyrus never plays `.mp3` by path. `Sound.Play` uses the SNDR FormID from `WhisperSndrIds.txt`.

## Esp build (D0.5 + E5)

`tools/build_hunger_spell_esp.py` reads `Desperate_Audio.txt` plus `config/necromantic/Intimacy_Start_Audio.txt` / `Intimacy_End_Audio.txt` and emits one Standard SNDR per row:

- FormID starts at `0x01000807` (Desperate) then intimacy maps
- ANAM `Sound\PickmansWhisper\<relative>` (subdir maps use backslashes)
- EDID sanitized from relative path (`PW_Whisper_Necromantic_Start_01_LooksPeaceful`)
- Writes `WhisperSndrIds.txt` — keys are **exact map lines** (`EndIt.xwm=…`, `Necromantic/Start/01-LooksPeaceful.xwm=…`)

## Voice delivery (D1)

MCM Voice → **Voice delivery** (`iVoiceDelivery`, default Toast + Audio):

| Mode | Behavior |
|------|----------|
| 0 Toast + Audio | One `RandomInt` on notice bank → toast + `PlayNoticeAudio(stage, index)` |
| 1 Audio only | `RandomInt` on audio bank → play only |
| 2 Toast only | Notice toast only |

Missing xwm / SNDR / empty map → **error toast** (no silent substitute). Unfinished stages may have empty `*_Audio.txt` (count 0).

## E5 — Necromantic intimacy audio

Same delivery table as D1, on `OnNecroSceneStart` / `OnNecroSceneEnd` for named Potential Victims:

| Toast bank | Audio map | Clips |
|------------|-----------|-------|
| `Intimacy_Start_Named.txt` | `Intimacy_Start_Audio.txt` | `Sound/PickmansWhisper/Necromantic/Start/` |
| `Intimacy_End_Named.txt` | `Intimacy_End_Audio.txt` | `Sound/PickmansWhisper/Necromantic/End/` |

Counts must match (23). `PlayWhisperXwmByFile` resolves relative keys under `Sound\PickmansWhisper\`.

## Debug

- **Play test whisper (EndIt)** — always FormID `0x807`; MessageBox shows xwm exists + Play instance id.
- Force notice stage **5 Desperate** on Debug page to test Desperate clips.

## Deploy

`build-deploy-local` recursively copies `Sound\PickmansWhisper\` into the MO2 mod (Desperate top-level + Necromantic subdirs).
