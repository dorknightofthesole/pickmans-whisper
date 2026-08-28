# Build Pickman's Whisper (Caprica), deploy into a local MO2 mod folder, and write
# dist/PickmansWhisper-<version>.zip (FOMOD) for Install Mod in MO2.
#
# Usage (PowerShell):
#   .\tools\build-deploy-local.ps1
#
# Optional env:
#   PICKMANS_WHISPER_ROOT   - repo root
#   PICKMANS_WHISPER_DEPLOY - MO2 mod folder (REQUIRED; set in .env or env)
#   CAPRICA                - path to Caprica.exe
#   FALLOUT4_ESM           - path to Fallout4.esm (for ESP MGEF clone; set in .env)
#
# Machine-specific paths are read from a git-ignored .env at repo root.
# Copy .env.example to .env and fill in your paths. Real env vars override .env.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load machine-specific settings from a git-ignored .env at repo root
# (KEY=VALUE lines). Real environment variables take precedence over .env.
function Import-DotEnv([string]$Path) {
  if (-not (Test-Path $Path)) { return }
  foreach ($line in Get-Content $Path) {
    $t = $line.Trim()
    if ($t -eq "" -or $t.StartsWith("#")) { continue }
    if ($t.StartsWith("export ")) { $t = $t.Substring(7).Trim() }
    $eq = $t.IndexOf("=")
    if ($eq -lt 1) { continue }
    $k = $t.Substring(0, $eq).Trim()
    $v = $t.Substring($eq + 1).Trim()
    if ($v.Length -ge 2 -and $v[0] -eq $v[-1] -and ($v[0] -eq '"' -or $v[0] -eq "'")) {
      $v = $v.Substring(1, $v.Length - 2)
    }
    if (-not [Environment]::GetEnvironmentVariable($k)) {
      Set-Item -Path ("Env:" + $k) -Value $v
    }
  }
}
Import-DotEnv (Join-Path (Resolve-Path (Join-Path $ScriptDir "..")).Path ".env")

$Root = if ($env:PICKMANS_WHISPER_ROOT) { $env:PICKMANS_WHISPER_ROOT } else { (Resolve-Path (Join-Path $ScriptDir "..")).Path }
$Deploy = if ($env:PICKMANS_WHISPER_DEPLOY) { $env:PICKMANS_WHISPER_DEPLOY } else { throw "PICKMANS_WHISPER_DEPLOY is not set. Copy .env.example to .env and set it to your MO2 mods\PickmansWhisper folder (or set the env var)." }
$Caprica = if ($env:CAPRICA) { $env:CAPRICA } else { Join-Path $Root "tools\Caprica\Caprica.exe" }
$Stubs = Join-Path $Root "tools\stubs"
$Src = Join-Path $Root "Data\Scripts\Source\User"
$PexOut = Join-Path $Root "Data\Scripts"
$Psc = "PickmansWhisperMainQuestScript.psc"
$PscBed = "PickmansWhisperBedGiftScript.psc"
$PscDecay = "PickmansWhisperCorpseDecayScript.psc"
$PscWoundLab = "PickmansWhisperDecayWoundLabScript.psc"
$PscVictims = "PickmansWhisperVictimsScript.psc"
$PscDesperateRename = "PickmansWhisperDesperateRenameScript.psc"
$PscAlias = "PickmansWhisperPlayerAliasScript.psc"
$PscBuffTracker = "PickmansWhisperBuffTrackerScript.psc"
$PscBeatBeforeKill = "PickmansWhisperBeatBeforeKillScript.psc"
$PscExecute = "PickmansWhisperExecuteScript.psc"
$PscKillReward = "PickmansWhisperKillRewardScript.psc"
$PscModConfig = "PickmansWhisperModConfigScript.psc"
$PscSlaveScene = "PickmansWhisperSlaveSceneScript.psc"
$PscSlaveryPerk = "PickmansWhisperSlaveryPerkScript.psc"
$PscSlavery = "PickmansWhisperSlaveryScript.psc"
$PscTargetScan = "PickmansWhisperTargetScanScript.psc"
$PscVictimTradePerk = "PickmansWhisperVictimTradePerkScript.psc"
$PscVictimTrade = "PickmansWhisperVictimTradeScript.psc"
$PscVoiceAlias = "PickmansWhisperVoiceAliasScript.psc"

Write-Host "==> Pickman's Whisper local build + deploy"
Write-Host "    ROOT=$Root"
Write-Host "    DEPLOY=$Deploy"

if (-not (Test-Path $Caprica)) { throw "Caprica not found at $Caprica" }
if (-not (Test-Path (Join-Path $Src $Psc))) { throw "missing $Src\$Psc" }
if (-not (Test-Path $Deploy)) {
  $parent = Split-Path -Parent $Deploy
  if (-not (Test-Path $parent)) {
    throw "deploy parent does not exist: $parent (set PICKMANS_WHISPER_DEPLOY to your MO2 mods folder path)"
  }
  Write-Host "==> Creating MO2 mod folder: $Deploy"
  New-Item -ItemType Directory -Force -Path $Deploy | Out-Null
}

Write-Host "==> Stub native honesty contract test"
& python (Join-Path $Root "tools\test_stub_natives.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_stub_natives.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Blade detect contract test"
& python (Join-Path $Root "tools\test_blade_detect_contract.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_blade_detect_contract.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Notice line / detection contract test"
& python (Join-Path $Root "tools\test_notice_lines.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_notice_lines.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Hunger SPECIAL penalty (no ModValue stack) contract test"
& python (Join-Path $Root "tools\test_hunger_special_penalty.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_hunger_special_penalty.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Look-fixation (C5 P1) contract test"
& python (Join-Path $Root "tools\test_look_fixation.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_look_fixation.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Recognition lines (C5 P2) contract test"
& python (Join-Path $Root "tools\test_recognition_lines.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_recognition_lines.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Potential Victims (C5 P3+P4) contract test"
& python (Join-Path $Root "tools\test_potential_victims.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_potential_victims.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Sleep recognition (C5 P5) contract test"
& python (Join-Path $Root "tools\test_sleep_recognition.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_sleep_recognition.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Audio D0-POC (Debug EndIt) contract test"
& python (Join-Path $Root "tools\test_audio_poc.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_audio_poc.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Audio D0.5/D1 (SNDR clones + delivery) contract test"
& python (Join-Path $Root "tools\test_audio_d1.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_audio_d1.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Voice blade gate contract test"
& python (Join-Path $Root "tools\test_voice_blade_gate.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_voice_blade_gate.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Kill-credit contract test"
& python (Join-Path $Root "tools\test_kill_credit.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_kill_credit.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Named kill / Necromantic E contract test"
& python (Join-Path $Root "tools\test_named_kill_voice.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_named_kill_voice.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Cut Off Tits prop Havok (BSX 194 Havok|Dynamic|Articulated; Scene Root target)"
& python (Join-Path $Root "tools\add_prop_tits_havok.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "add_prop_tits_havok.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Corpse sever (Slice F) contract test"
& python (Join-Path $Root "tools\test_corpse_sever.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_corpse_sever.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Bed hallucination (Slice G) contract test"
& python (Join-Path $Root "tools\test_bed_hallucination.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_bed_hallucination.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Desperate rename (Slice I) contract test"
& python (Join-Path $Root "tools\test_desperate_rename.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_desperate_rename.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Corpse decay (Slice H ROF/LooksMenu) contract test"
& python (Join-Path $Root "tools\test_corpse_decay.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_corpse_decay.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay wound lab (Slice H P0.1) contract test"
& python (Join-Path $Root "tools\test_decay_wound_lab.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_wound_lab.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay stage ModConfig parse contract test"
& python (Join-Path $Root "tools\test_decay_stage_modconfig.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_stage_modconfig.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay kill stamp (Slice H P2) contract test"
& python (Join-Path $Root "tools\test_decay_kill_p2.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_kill_p2.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay MCM kill-clock (reset/apply) contract test"
& python (Join-Path $Root "tools\test_decay_mcm_clock.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_mcm_clock.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay eat-ripe-toast (Slice H P4) contract test"
& python (Join-Path $Root "tools\test_decay_eat_ripe_toast.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_eat_ripe_toast.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay eaten-ripe-corpse (Slice H P5) contract test"
& python (Join-Path $Root "tools\test_decay_eaten_ripe_corpse.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_eaten_ripe_corpse.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Buff tracker (Slice H P5 bonus) contract test"
& python (Join-Path $Root "tools\test_buff_tracker.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_buff_tracker.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Beat before kill (Slice J1) contract test"
& python (Join-Path $Root "tools\test_beat_before_kill.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_beat_before_kill.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> KillerScan removal contract test (Slice J1 - must not exist)"
& python (Join-Path $Root "tools\test_no_killer_scan.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_no_killer_scan.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Voice debug Trace / MCM dump contract test"
& python (Join-Path $Root "tools\test_voice_debug_trace.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_voice_debug_trace.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay assets ship contract test"
& python (Join-Path $Root "tools\test_decay_assets_ship.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_assets_ship.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay face ARMA/ARMO ESP contract test"
& python (Join-Path $Root "tools\test_decay_face_armor_esp.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_face_armor_esp.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Proximity cloak (Phase 1) ESP contract test"
& python (Join-Path $Root "tools\test_proximity_cloak.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_proximity_cloak.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Decay face stage equip contract test"
& python (Join-Path $Root "tools\test_decay_face_stage_equip.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_decay_face_stage_equip.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> TargetOverrides filter contract test"
& python (Join-Path $Root "tools\test_target_overrides.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_target_overrides.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Env loader / no-hardcoded-path test"
& python (Join-Path $Root "tools\test_env_loader.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_env_loader.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> First blade acquire voice line (Slice R1) contract test"
& python (Join-Path $Root "tools\test_blade_acquire.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_blade_acquire.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Blade hit / kill-credit ActorValue (AVIF) contract test"
& python (Join-Path $Root "tools\test_blade_hit_av.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_blade_hit_av.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Wound Lab Captive Tattoos contract test"
& python (Join-Path $Root "tools\test_captive_tattoo_lab.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_captive_tattoo_lab.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Execute - instant kill (Slice W) contract test"
& python (Join-Path $Root "tools\test_execute_kill.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_execute_kill.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Hunger pace + Calm-state bonus (Slice L) contract test"
& python (Join-Path $Root "tools\test_hunger_pace_calm_bonus.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_hunger_pace_calm_bonus.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> KillRewardAlias retirement contract test"
& python (Join-Path $Root "tools\test_kill_reward_alias.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_kill_reward_alias.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Lady Killer perk Bond gate (Slice N) contract test"
& python (Join-Path $Root "tools\test_lady_killer_bond_gate.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_lady_killer_bond_gate.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> ModConfigAlias host contract test"
& python (Join-Path $Root "tools\test_modconfig_alias.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_modconfig_alias.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> RegisterTarget / OnHit / OnDeath / RewardKill contract test"
& python (Join-Path $Root "tools\test_register_reward_path.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_register_reward_path.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Slave Scene (Slice U AAF) contract test"
& python (Join-Path $Root "tools\test_slave_scene.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_slave_scene.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Slavery (enslave/follow/slave-gear) contract test"
& python (Join-Path $Root "tools\test_slavery.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_slavery.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> IsValidTarget hard-gate eligibility contract test"
& python (Join-Path $Root "tools\test_target_eligible.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_target_eligible.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> TargetScan VMAD form bind contract test"
& python (Join-Path $Root "tools\test_target_scan.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_target_scan.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> TrackedNPCs retirement contract test"
& python (Join-Path $Root "tools\test_tracked_npcs_alias.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_tracked_npcs_alias.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Trust / Hunger / Praise files contract test"
& python (Join-Path $Root "tools\test_trust_hunger_praise_files.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_trust_hunger_praise_files.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Force Trade (Talk activate menu) contract test"
& python (Join-Path $Root "tools\test_victim_trade.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_victim_trade.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> VoiceAlias host contract test"
& python (Join-Path $Root "tools\test_voice_alias.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_voice_alias.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Rebuilding PickmansWhisper.esp (Knife Hunger SPEL)"
& python (Join-Path $Root "tools\build_hunger_spell_esp.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "build_hunger_spell_esp.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Compiling $Psc + $PscBed + $PscDecay + $PscWoundLab + $PscVictims + $PscDesperateRename + $PscAlias + $PscBuffTracker + $PscBeatBeforeKill + $PscExecute + $PscKillReward + $PscModConfig + $PscSlaveScene + $PscSlaveryPerk + $PscSlavery + $PscTargetScan + $PscVictimTradePerk + $PscVictimTrade + $PscVoiceAlias"
Push-Location $Src
try {
  foreach ($script in @($Psc, $PscBed, $PscDecay, $PscWoundLab, $PscVictims, $PscDesperateRename, $PscAlias, $PscBuffTracker, $PscBeatBeforeKill, $PscExecute, $PscKillReward, $PscModConfig, $PscSlaveScene, $PscSlaveryPerk, $PscSlavery, $PscTargetScan, $PscVictimTradePerk, $PscVictimTrade, $PscVoiceAlias)) {
    if (-not (Test-Path $script)) { throw "missing $Src\$script" }
    Write-Host "    Caprica $script"
    & $Caprica $script -g fallout4 -i "$Stubs;$Src" -f (Join-Path $Stubs "Institute_Papyrus_Flags.flg") -o $PexOut
    if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
      throw "Caprica failed on $script with exit code $LASTEXITCODE"
    }
  }
} finally {
  Pop-Location
}

$Pex = Join-Path $PexOut "PickmansWhisperMainQuestScript.pex"
$PexBed = Join-Path $PexOut "PickmansWhisperBedGiftScript.pex"
$PexDecay = Join-Path $PexOut "PickmansWhisperCorpseDecayScript.pex"
$PexWoundLab = Join-Path $PexOut "PickmansWhisperDecayWoundLabScript.pex"
$PexVictims = Join-Path $PexOut "PickmansWhisperVictimsScript.pex"
$PexDesperateRename = Join-Path $PexOut "PickmansWhisperDesperateRenameScript.pex"
$PexAlias = Join-Path $PexOut "PickmansWhisperPlayerAliasScript.pex"
$PexBuffTracker = Join-Path $PexOut "PickmansWhisperBuffTrackerScript.pex"
$PexBeatBeforeKill = Join-Path $PexOut "PickmansWhisperBeatBeforeKillScript.pex"
$PexExecute = Join-Path $PexOut "PickmansWhisperExecuteScript.pex"
$PexKillReward = Join-Path $PexOut "PickmansWhisperKillRewardScript.pex"
$PexModConfig = Join-Path $PexOut "PickmansWhisperModConfigScript.pex"
$PexSlaveScene = Join-Path $PexOut "PickmansWhisperSlaveSceneScript.pex"
$PexSlaveryPerk = Join-Path $PexOut "PickmansWhisperSlaveryPerkScript.pex"
$PexSlavery = Join-Path $PexOut "PickmansWhisperSlaveryScript.pex"
$PexTargetScan = Join-Path $PexOut "PickmansWhisperTargetScanScript.pex"
$PexVictimTradePerk = Join-Path $PexOut "PickmansWhisperVictimTradePerkScript.pex"
$PexVictimTrade = Join-Path $PexOut "PickmansWhisperVictimTradeScript.pex"
$PexVoiceAlias = Join-Path $PexOut "PickmansWhisperVoiceAliasScript.pex"
if (-not (Test-Path $Pex)) { throw "compile produced no main .pex" }
if (-not (Test-Path $PexBed)) { throw "compile produced no BedGift .pex" }
if (-not (Test-Path $PexDecay)) { throw "compile produced no CorpseDecay .pex" }
if (-not (Test-Path $PexWoundLab)) { throw "compile produced no DecayWoundLab .pex" }
if (-not (Test-Path $PexVictims)) { throw "compile produced no Victims .pex" }
if (-not (Test-Path $PexDesperateRename)) { throw "compile produced no DesperateRename .pex" }
if (-not (Test-Path $PexAlias)) { throw "compile produced no PlayerAlias .pex" }
if (-not (Test-Path $PexBuffTracker)) { throw "compile produced no BuffTracker .pex" }
if (-not (Test-Path $PexBeatBeforeKill)) { throw "compile produced no BeatBeforeKill .pex" }
if (-not (Test-Path $PexExecute)) { throw "compile produced no Execute .pex" }
if (-not (Test-Path $PexKillReward)) { throw "compile produced no KillReward .pex" }
if (-not (Test-Path $PexModConfig)) { throw "compile produced no ModConfig .pex" }
if (-not (Test-Path $PexSlaveScene)) { throw "compile produced no SlaveScene .pex" }
if (-not (Test-Path $PexSlaveryPerk)) { throw "compile produced no SlaveryPerk .pex" }
if (-not (Test-Path $PexSlavery)) { throw "compile produced no Slavery .pex" }
if (-not (Test-Path $PexTargetScan)) { throw "compile produced no TargetScan .pex" }
if (-not (Test-Path $PexVictimTradePerk)) { throw "compile produced no VictimTradePerk .pex" }
if (-not (Test-Path $PexVictimTrade)) { throw "compile produced no VictimTrade .pex" }
if (-not (Test-Path $PexVoiceAlias)) { throw "compile produced no VoiceAlias .pex" }

Write-Host "==> Deploying to $Deploy"
@(
  "Scripts\Source\User",
  "MCM\Config\PickmansWhisper",
  "MCM\Settings",
  "PickmansWhisper",
  "Sound\PickmansWhisper",
  "Materials",
  "Meshes",
  "Textures",
  "F4SE",
  "docs"
) | ForEach-Object {
  New-Item -ItemType Directory -Force -Path (Join-Path $Deploy $_) | Out-Null
}

Copy-Item -Force $Pex (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexBed (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexDecay (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexWoundLab (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexVictims (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexDesperateRename (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexAlias (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexBuffTracker (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexBeatBeforeKill (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexExecute (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexKillReward (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexModConfig (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexSlaveScene (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexSlaveryPerk (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexSlavery (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexTargetScan (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexVictimTradePerk (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexVictimTrade (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexVoiceAlias (Join-Path $Deploy "Scripts\")
Copy-Item -Force (Join-Path $Src $Psc) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscBed) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscDecay) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscWoundLab) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscVictims) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscDesperateRename) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscAlias) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscBuffTracker) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscBeatBeforeKill) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscExecute) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscKillReward) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscModConfig) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscSlaveScene) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscSlaveryPerk) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscSlavery) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscTargetScan) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscVictimTradePerk) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscVictimTrade) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscVoiceAlias) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Root "Data\MCM\Config\PickmansWhisper\config.json") (Join-Path $Deploy "MCM\Config\PickmansWhisper\")
Copy-Item -Force (Join-Path $Root "Data\MCM\Config\PickmansWhisper\settings.ini") (Join-Path $Deploy "MCM\Config\PickmansWhisper\")
Copy-Item -Force (Join-Path $Root "Data\MCM\Settings\PickmansWhisper.ini") (Join-Path $Deploy "MCM\Settings\")

# Full mod data trees (config + whispers; decay Materials/Meshes/Textures; F4SE when present).
function Sync-DataTree([string]$Rel) {
  $srcTree = Join-Path $Root ("Data\" + $Rel)
  $dstTree = Join-Path $Deploy $Rel
  if (-not (Test-Path $srcTree)) {
    throw "Deploy source missing Data\$Rel"
  }
  New-Item -ItemType Directory -Force -Path $dstTree | Out-Null
  Copy-Item -Force -Recurse (Join-Path $srcTree "*") $dstTree
}
Sync-DataTree "PickmansWhisper"
Sync-DataTree "Materials"
Sync-DataTree "Meshes"
Sync-DataTree "Textures"
Sync-DataTree "F4SE"
Sync-DataTree "AAF"
$decayMesh = Join-Path $Deploy "Meshes\PickmansWhisper\Decay\NecroBaseFemaleHead.nif"
if (-not (Test-Path $decayMesh)) {
  throw "Deploy missing Meshes\PickmansWhisper\Decay\NecroBaseFemaleHead.nif"
}
$decayBgsm = Join-Path $Deploy "Materials\PickmansWhisper\Decay\Necro_Bruising01_d.bgsm"
if (-not (Test-Path $decayBgsm)) {
  throw "Deploy missing Materials\PickmansWhisper\Decay\*.bgsm"
}
$decayTex = Join-Path $Deploy "Textures\PickmansWhisper\Decay\Necro_Bruising01_d.DDS"
if (-not (Test-Path $decayTex)) {
  throw "Deploy missing Textures\PickmansWhisper\Decay\*.DDS"
}

# Recursive — Desperate top-level .xwm plus E5 Necromantic\Start|End clips.
$soundSrc = Join-Path $Root "Data\Sound\PickmansWhisper"
$soundDeploy = Join-Path $Deploy "Sound\PickmansWhisper"
if (Test-Path $soundSrc) {
  New-Item -ItemType Directory -Force -Path $soundDeploy | Out-Null
  Copy-Item -Force -Recurse (Join-Path $soundSrc "*") $soundDeploy
}
$endItDeployed = Join-Path $Deploy "Sound\PickmansWhisper\EndIt.xwm"
if (-not (Test-Path $endItDeployed)) {
  throw "Deploy missing Sound\PickmansWhisper\EndIt.xwm (D0-POC audio). Source should be Data\Sound\PickmansWhisper\EndIt.xwm"
}
$necroStartClip = Join-Path $Deploy "Sound\PickmansWhisper\Necromantic\Start\01-LooksPeaceful.xwm"
if (-not (Test-Path $necroStartClip)) {
  throw "Deploy missing Necromantic Start xwm (E5). Expected Sound\PickmansWhisper\Necromantic\Start\01-LooksPeaceful.xwm"
}

$Esp = Join-Path $Root "Data\PickmansWhisper.esp"
if (-not (Test-Path $Esp)) { $Esp = Join-Path $Root "PickmansWhisper.esp" }
if (-not (Test-Path $Esp)) { throw "PickmansWhisper.esp missing at Data/PickmansWhisper.esp" }

$espSrcLen = (Get-Item $Esp).Length
# Quest-only plugin is ~272 bytes; Knife Hunger SPEL bumps this well above 400.
$EspMinBytes = 400
if ($espSrcLen -lt $EspMinBytes) {
  throw "source PickmansWhisper.esp is only $espSrcLen bytes (need >= $EspMinBytes with Knife Hunger SPEL) - rebuild failed?"
}
Write-Host "    source ESP: $espSrcLen bytes"

$destEsp = Join-Path $Deploy "PickmansWhisper.esp"
$alt = Join-Path $Deploy "PickmansWhisper.esp.new"
$copied = $false
for ($attempt = 1; $attempt -le 5; $attempt++) {
  try {
    if (Test-Path $destEsp) {
      Remove-Item -Force $destEsp -ErrorAction Stop
    }
    Copy-Item -Force $Esp $destEsp -ErrorAction Stop
    $len = (Get-Item $destEsp).Length
    Write-Host "    ESP deployed ($len bytes)"
    if ($len -ne $espSrcLen) {
      throw "deployed ESP size $len != source $espSrcLen (stale or partial copy)"
    }
    if (Test-Path $alt) { Remove-Item -Force $alt -ErrorAction SilentlyContinue }
    $copied = $true
    break
  } catch {
    Write-Warning ("ESP deploy attempt $attempt failed: " + $_.Exception.Message)
    Start-Sleep -Milliseconds 400
  }
}
if (-not $copied) {
  Copy-Item -Force $Esp $alt -ErrorAction SilentlyContinue
  Write-Host "    Manual: Copy-Item -Force `"$alt`" `"$destEsp`""
  throw "FAILED: could not replace PickmansWhisper.esp (FO4/MO2 lock?). Wrote PickmansWhisper.esp.new if possible. Quit both, re-run this script. Deployed ESP must be $espSrcLen bytes."
}

# Hard verify: size match + SPEL PickmansWhisperKnifeHunger (0x01000801) present
Write-Host "==> Verifying deployed PickmansWhisper.esp"
$verifyScript = Join-Path $Root "tools\verify_pickmans_whisper_esp.py"
$verify = & python $verifyScript $destEsp $espSrcLen
if ($LASTEXITCODE -ne 0) {
  throw "ESP verify failed (exit $LASTEXITCODE): $verify. Do not launch FO4 until PickmansWhisper.esp deploys cleanly."
}
Write-Host "    $verify"

Get-ChildItem (Join-Path $Root "docs\*.md") -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-Item -Force $_.FullName (Join-Path $Deploy "docs\")
}

$configDeployed = Join-Path $Deploy "MCM\Config\PickmansWhisper\config.json"
# MO2 meta.ini: gameName must be Fallout4 (no space) or MO2 warns "for a different game"
$metaDeploy = Join-Path $Deploy "meta.ini"
if (-not (Test-Path $metaDeploy)) {
  Copy-Item -Force (Join-Path $Root "meta.ini") $metaDeploy
} else {
  $metaLines = Get-Content $metaDeploy
  $metaLines = $metaLines | ForEach-Object { if ($_ -match '^gameName=') { "gameName=Fallout4" } else { $_ } }
  $metaLines | Set-Content -Path $metaDeploy -Encoding ASCII
}

Write-Host "==> Packaging FOMOD zip for MO2"
& python (Join-Path $Root "tools\package_mo2_zip.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "package_mo2_zip.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Done."
Write-Host ("    MCM config: " + (Get-Item $configDeployed).LastWriteTime)
Write-Host "    Restart FO4 (quit to desktop) so MCM reloads config.json - in-game MCM often caches page layout."
Write-Host "    MO2 install zip: dist\PickmansWhisper-<version>.zip"
