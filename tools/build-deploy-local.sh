#!/usr/bin/env bash
# Build Pickman's Whisper (Caprica), deploy into a local MO2 mod folder, and write
# dist/PickmansWhisper-<version>.zip (FOMOD) for Install Mod in MO2.
#
# Usage (Git Bash / WSL / macOS* with Caprica.exe via wine not covered):
#   ./tools/build-deploy-local.sh
#
# Machine-specific paths are read from a git-ignored .env at repo root.
# Copy .env.example to .env and fill in your paths. Real env vars override .env.
# Settings:
#   PICKMANS_WHISPER_ROOT   — repo root (default: parent of tools/)
#   PICKMANS_WHISPER_DEPLOY - MO2 mod folder (REQUIRED; set in .env or env)
#   CAPRICA                — path to Caprica.exe
#   FALLOUT4_ESM           — path to Fallout4.esm (for ESP MGEF clone; set in .env)
#
# * Caprica is a Windows binary; this script expects it runnable under your shell.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load machine-specific settings from a git-ignored .env at repo root
# (KEY=VALUE lines). Real environment variables take precedence over .env.
load_dotenv() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"   # ltrim
    [[ -z "$line" || "$line" == \#* ]] && continue
    line="${line#export }"
    [[ "$line" != *=* ]] && continue
    local key="${line%%=*}" val="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"       # rtrim key
    val="${val#"${val%%[![:space:]]*}"}"       # ltrim val
    # strip one layer of surrounding quotes
    val="${val%\"}"; val="${val#\"}"
    val="${val%\'}"; val="${val#\'}"
    [[ -z "$key" ]] && continue
    [[ -z "${!key:-}" ]] && export "$key=$val"
  done < "$f"
}
load_dotenv "$SCRIPT_DIR/../.env"

ROOT="$(cd "${PICKMANS_WHISPER_ROOT:-$SCRIPT_DIR/..}" && pwd)"

# Git Bash on Windows: prefer /d/... style; also accept Windows paths in env.
DEPLOY="${PICKMANS_WHISPER_DEPLOY:-}"
if [[ -z "$DEPLOY" ]]; then
  echo "ERROR: PICKMANS_WHISPER_DEPLOY is not set." >&2
  echo "       Copy .env.example to .env and set it to your MO2 mods/PickmansWhisper folder." >&2
  exit 1
fi
CAPRICA="${CAPRICA:-$ROOT/tools/Caprica/Caprica.exe}"
STUBS="$ROOT/tools/stubs"
SRC="$ROOT/Data/Scripts/Source/User"
PEX_OUT="$ROOT/Data/Scripts"
PSC="PickmansWhisperMainQuestScript.psc"
PSC_BED="PickmansWhisperBedGiftScript.psc"
PSC_DECAY="PickmansWhisperCorpseDecayScript.psc"
PSC_WOUND_LAB="PickmansWhisperDecayWoundLabScript.psc"
PSC_WORLD_SCAN="PickmansWhisperWorldScanScript.psc"
PSC_VOICE_SCAN="PickmansWhisperVoiceScanScript.psc"
PSC_ALIAS="PickmansWhisperPlayerAliasScript.psc"

to_win_path() {
  local p="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$p"
  else
    # WSL
    if command -v wslpath >/dev/null 2>&1 && [[ "$p" == /mnt/* ]]; then
      wslpath -w "$p"
    else
      echo "$p" | sed -e 's|^/d/|D:/|' -e 's|^/c/|C:/|' -e 's|/|\\|g'
    fi
  fi
}

echo "==> Pickman's Whisper local build + deploy"
echo "    ROOT=$ROOT"
echo "    DEPLOY=$DEPLOY"

if [[ ! -f "$CAPRICA" ]]; then
  echo "ERROR: Caprica not found at $CAPRICA" >&2
  exit 1
fi
if [[ ! -f "$SRC/$PSC" ]]; then
  echo "ERROR: missing $SRC/$PSC" >&2
  exit 1
fi
if [[ ! -d "$DEPLOY" ]]; then
  parent="$(dirname "$DEPLOY")"
  if [[ ! -d "$parent" ]]; then
    echo "ERROR: deploy parent does not exist: $parent" >&2
    echo "       Set PICKMANS_WHISPER_DEPLOY to your MO2 mods folder path." >&2
    exit 1
  fi
  echo "==> Creating MO2 mod folder: $DEPLOY"
  mkdir -p "$DEPLOY"
fi

CAPRICA_WIN="$(to_win_path "$CAPRICA")"
STUBS_WIN="$(to_win_path "$STUBS")"
SRC_WIN="$(to_win_path "$SRC")"
OUT_WIN="$(to_win_path "$PEX_OUT")"
FLAGS_WIN="$(to_win_path "$STUBS/Institute_Papyrus_Flags.flg")"

echo "==> Stub native honesty contract test"
python "$ROOT/tools/test_stub_natives.py" || exit 1

echo "==> Blade detect contract test"
python "$ROOT/tools/test_blade_detect_contract.py" || exit 1

echo "==> Notice line / detection contract test"
python "$ROOT/tools/test_notice_lines.py" || exit 1

echo "==> Look-fixation (C5 P1) contract test"
python "$ROOT/tools/test_look_fixation.py" || exit 1
python "$ROOT/tools/test_recognition_lines.py" || exit 1
python "$ROOT/tools/test_potential_victims.py" || exit 1
python "$ROOT/tools/test_sleep_recognition.py" || exit 1
python "$ROOT/tools/test_audio_poc.py" || exit 1
python "$ROOT/tools/test_audio_d1.py" || exit 1
python "$ROOT/tools/test_voice_blade_gate.py" || exit 1

echo "==> TargetOverrides filter contract test"
python "$ROOT/tools/test_target_overrides.py" || exit 1

echo "==> Env loader / no-hardcoded-path test"
python "$ROOT/tools/test_env_loader.py" || exit 1

echo "==> Corpse decay (Slice H ROF/LooksMenu) contract test"
python "$ROOT/tools/test_corpse_decay.py" || exit 1

echo "==> Decay wound lab (Slice H P0.1) contract test"
python "$ROOT/tools/test_decay_wound_lab.py" || exit 1

echo "==> Decay stage ModConfig parse contract test"
python "$ROOT/tools/test_decay_stage_modconfig.py" || exit 1

echo "==> Decay kill stamp (Slice H P2) contract test"
python "$ROOT/tools/test_decay_kill_p2.py" || exit 1

echo "==> WorldScan event bus contract test"
python "$ROOT/tools/test_world_scan_bus.py" || exit 1

echo "==> Voice debug Trace / MCM dump contract test"
python "$ROOT/tools/test_voice_debug_trace.py" || exit 1

echo "==> Rebuilding PickmansWhisper.esp (Knife Hunger SPEL)"
python "$ROOT/tools/build_hunger_spell_esp.py"

echo "==> Compiling $PSC + $PSC_BED + $PSC_DECAY + $PSC_WOUND_LAB + $PSC_WORLD_SCAN + $PSC_VOICE_SCAN + $PSC_ALIAS"
(
  cd "$SRC"
  for script in "$PSC" "$PSC_BED" "$PSC_DECAY" "$PSC_WOUND_LAB" "$PSC_WORLD_SCAN" "$PSC_VOICE_SCAN" "$PSC_ALIAS"; do
    if [[ ! -f "$script" ]]; then
      echo "ERROR: missing $SRC/$script" >&2
      exit 1
    fi
    echo "    Caprica $script"
    # Caprica wants Windows paths when run as .exe from Git Bash
    "$CAPRICA" "$script" \
      -g fallout4 \
      -i "${STUBS_WIN};${SRC_WIN}" \
      -f "$FLAGS_WIN" \
      -o "$OUT_WIN"
  done
)

if [[ ! -f "$PEX_OUT/PickmansWhisperMainQuestScript.pex" ]]; then
  echo "ERROR: compile produced no main .pex" >&2
  exit 1
fi
if [[ ! -f "$PEX_OUT/PickmansWhisperBedGiftScript.pex" ]]; then
  echo "ERROR: compile produced no BedGift .pex" >&2
  exit 1
fi
if [[ ! -f "$PEX_OUT/PickmansWhisperCorpseDecayScript.pex" ]]; then
  echo "ERROR: compile produced no CorpseDecay .pex" >&2
  exit 1
fi
if [[ ! -f "$PEX_OUT/PickmansWhisperDecayWoundLabScript.pex" ]]; then
  echo "ERROR: compile produced no DecayWoundLab .pex" >&2
  exit 1
fi
if [[ ! -f "$PEX_OUT/PickmansWhisperWorldScanScript.pex" ]]; then
  echo "ERROR: compile produced no WorldScan .pex" >&2
  exit 1
fi
if [[ ! -f "$PEX_OUT/PickmansWhisperVoiceScanScript.pex" ]]; then
  echo "ERROR: compile produced no VoiceScan .pex" >&2
  exit 1
fi
if [[ ! -f "$PEX_OUT/PickmansWhisperPlayerAliasScript.pex" ]]; then
  echo "ERROR: compile produced no PlayerAlias .pex" >&2
  exit 1
fi

echo "==> Deploying to $DEPLOY"
mkdir -p \
  "$DEPLOY/Scripts/Source/User" \
  "$DEPLOY/MCM/Config/PickmansWhisper" \
  "$DEPLOY/MCM/Settings" \
  "$DEPLOY/PickmansWhisper/config" \
  "$DEPLOY/Sound/PickmansWhisper" \
  "$DEPLOY/docs"

cp -f "$PEX_OUT/PickmansWhisperMainQuestScript.pex" "$DEPLOY/Scripts/"
cp -f "$PEX_OUT/PickmansWhisperBedGiftScript.pex" "$DEPLOY/Scripts/"
cp -f "$PEX_OUT/PickmansWhisperCorpseDecayScript.pex" "$DEPLOY/Scripts/"
cp -f "$PEX_OUT/PickmansWhisperDecayWoundLabScript.pex" "$DEPLOY/Scripts/"
cp -f "$PEX_OUT/PickmansWhisperWorldScanScript.pex" "$DEPLOY/Scripts/"
cp -f "$PEX_OUT/PickmansWhisperVoiceScanScript.pex" "$DEPLOY/Scripts/"
cp -f "$PEX_OUT/PickmansWhisperPlayerAliasScript.pex" "$DEPLOY/Scripts/"
cp -f "$SRC/PickmansWhisperMainQuestScript.psc" "$DEPLOY/Scripts/Source/User/"
cp -f "$SRC/PickmansWhisperBedGiftScript.psc" "$DEPLOY/Scripts/Source/User/"
cp -f "$SRC/PickmansWhisperCorpseDecayScript.psc" "$DEPLOY/Scripts/Source/User/"
cp -f "$SRC/PickmansWhisperDecayWoundLabScript.psc" "$DEPLOY/Scripts/Source/User/"
cp -f "$SRC/PickmansWhisperWorldScanScript.psc" "$DEPLOY/Scripts/Source/User/"
cp -f "$SRC/PickmansWhisperVoiceScanScript.psc" "$DEPLOY/Scripts/Source/User/"
cp -f "$SRC/PickmansWhisperPlayerAliasScript.psc" "$DEPLOY/Scripts/Source/User/"
cp -f "$ROOT/Data/MCM/Config/PickmansWhisper/config.json" "$DEPLOY/MCM/Config/PickmansWhisper/"
cp -f "$ROOT/Data/MCM/Config/PickmansWhisper/settings.ini" "$DEPLOY/MCM/Config/PickmansWhisper/"
cp -f "$ROOT/Data/MCM/Settings/PickmansWhisper.ini" "$DEPLOY/MCM/Settings/"
cp -f "$ROOT/Data/PickmansWhisper/config/"*.txt "$DEPLOY/PickmansWhisper/config/" 2>/dev/null || true
mkdir -p "$DEPLOY/PickmansWhisper/config/necromantic"
cp -f "$ROOT/Data/PickmansWhisper/config/necromantic/"*.txt "$DEPLOY/PickmansWhisper/config/necromantic/" 2>/dev/null || true
cp -f "$ROOT/Data/Sound/PickmansWhisper/"*.xwm "$DEPLOY/Sound/PickmansWhisper/" 2>/dev/null || true
if [[ ! -f "$DEPLOY/Sound/PickmansWhisper/EndIt.xwm" ]]; then
  echo "ERROR: Deploy missing Sound/PickmansWhisper/EndIt.xwm (D0-POC audio)" >&2
  exit 1
fi

ESP_SRC=""
if [[ -f "$ROOT/Data/PickmansWhisper.esp" ]]; then
  ESP_SRC="$ROOT/Data/PickmansWhisper.esp"
elif [[ -f "$ROOT/PickmansWhisper.esp" ]]; then
  ESP_SRC="$ROOT/PickmansWhisper.esp"
else
  echo "ERROR: PickmansWhisper.esp missing" >&2
  exit 1
fi

ESP_SRC_LEN=$(wc -c < "$ESP_SRC" | tr -d ' ')
ESP_MIN=400
if (( ESP_SRC_LEN < ESP_MIN )); then
  echo "ERROR: source PickmansWhisper.esp is only ${ESP_SRC_LEN} bytes (need >= ${ESP_MIN} with Knife Hunger SPEL)" >&2
  exit 1
fi
echo "    source ESP: ${ESP_SRC_LEN} bytes"

DEST_ESP="$DEPLOY/PickmansWhisper.esp"
ALT_ESP="$DEPLOY/PickmansWhisper.esp.new"
copied=0
for attempt in 1 2 3 4 5; do
  if rm -f "$DEST_ESP" 2>/dev/null && cp -f "$ESP_SRC" "$DEST_ESP" 2>/dev/null; then
    DEST_LEN=$(wc -c < "$DEST_ESP" | tr -d ' ')
    echo "    ESP deployed (${DEST_LEN} bytes)"
    if [[ "$DEST_LEN" -eq "$ESP_SRC_LEN" ]]; then
      rm -f "$ALT_ESP" 2>/dev/null || true
      copied=1
      break
    fi
    echo "WARN: deployed size ${DEST_LEN} != source ${ESP_SRC_LEN}" >&2
  else
    echo "WARN: ESP deploy attempt ${attempt} failed (lock?)" >&2
    sleep 0.4
  fi
done

if [[ "$copied" -ne 1 ]]; then
  cp -f "$ESP_SRC" "$ALT_ESP" 2>/dev/null || true
  echo "    Manual: cp -f \"$ALT_ESP\" \"$DEST_ESP\"" >&2
  echo "ERROR: could not replace PickmansWhisper.esp (FO4/MO2 lock?). Deployed ESP must be ${ESP_SRC_LEN} bytes." >&2
  exit 1
fi

echo "==> Verifying deployed PickmansWhisper.esp"
python "$ROOT/tools/verify_pickmans_whisper_esp.py" "$DEST_ESP" "$ESP_SRC_LEN"

cp -f "$ROOT/docs/"*.md "$DEPLOY/docs/" 2>/dev/null || true

echo "==> Packaging FOMOD zip for MO2"
python "$ROOT/tools/package_mo2_zip.py"

echo "==> Done. In MO2, ensure the mod folder is enabled, then restart FO4 (or at least reload scripts / load a save)."
echo "    Tip: MO2 mod folder should be named PickmansWhisper."
echo "    MO2 install zip: dist/PickmansWhisper-<version>.zip"
