# Slice D audio

## Runtime model

| Role | Location |
|------|----------|
| Toast text | `config/NoticeLines_<Stage>.txt` |
| Audio map | `config/<Stage>_Audio.txt` — one **`.xwm`** filename per notice row |
| Clips | `Data/Sound/PickmansWhisper/*.xwm` |
| SNDR forms | `PickmansWhisper.esp` — EDID `PW_Whisper_<Stem>` |
| FormID table | `config/WhisperSndrIds.txt` (**generated** by esp build) |

Papyrus never plays `.mp3` by path. `Sound.Play` uses the SNDR FormID from `WhisperSndrIds.txt`.

## Esp build (D0.5)

`tools/build_hunger_spell_esp.py` reads `Desperate_Audio.txt` and emits one Standard SNDR per row:

- FormID `0x01000807 + index`
- Path `Sound\PickmansWhisper\<file>.xwm`
- Writes `WhisperSndrIds.txt` (`EndIt.xwm=2055`, …)

## Voice delivery (D1)

MCM Voice → **Voice delivery** (`iVoiceDelivery`, default Toast + Audio):

| Mode | Behavior |
|------|----------|
| 0 Toast + Audio | One `RandomInt` on notice bank → toast + `PlayNoticeAudio(stage, index)` |
| 1 Audio only | `RandomInt` on audio bank → play only |
| 2 Toast only | Notice toast only |

Missing xwm / SNDR / empty map → **error toast** (no silent substitute). Unfinished stages may have empty `*_Audio.txt` (count 0).

## Debug

- **Play test whisper (EndIt)** — always FormID `0x807`; MessageBox shows xwm exists + Play instance id.
- Force notice stage **5 Desperate** on Debug page to test Desperate clips.

## Deploy

`build-deploy-local` copies `Sound\PickmansWhisper\*.xwm` into the MO2 mod (required).
