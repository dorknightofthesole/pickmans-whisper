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
$PscAlias = "PickmansWhisperPlayerAliasScript.psc"

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

Write-Host "==> Look-fixation (C5 P1) contract test"
& python (Join-Path $Root "tools\test_look_fixation.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "test_look_fixation.py failed with exit code $LASTEXITCODE"
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

Write-Host "==> Rebuilding PickmansWhisper.esp (Knife Hunger SPEL)"
& python (Join-Path $Root "tools\build_hunger_spell_esp.py")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
  throw "build_hunger_spell_esp.py failed with exit code $LASTEXITCODE"
}

Write-Host "==> Compiling $Psc + $PscAlias"
Push-Location $Src
try {
  foreach ($script in @($Psc, $PscAlias)) {
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
$PexAlias = Join-Path $PexOut "PickmansWhisperPlayerAliasScript.pex"
if (-not (Test-Path $Pex)) { throw "compile produced no main .pex" }
if (-not (Test-Path $PexAlias)) { throw "compile produced no PlayerAlias .pex" }

Write-Host "==> Deploying to $Deploy"
@(
  "Scripts\Source\User",
  "MCM\Config\PickmansWhisper",
  "MCM\Settings",
  "PickmansWhisper\config",
  "docs"
) | ForEach-Object {
  New-Item -ItemType Directory -Force -Path (Join-Path $Deploy $_) | Out-Null
}

Copy-Item -Force $Pex (Join-Path $Deploy "Scripts\")
Copy-Item -Force $PexAlias (Join-Path $Deploy "Scripts\")
Copy-Item -Force (Join-Path $Src $Psc) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Src $PscAlias) (Join-Path $Deploy "Scripts\Source\User\")
Copy-Item -Force (Join-Path $Root "Data\MCM\Config\PickmansWhisper\config.json") (Join-Path $Deploy "MCM\Config\PickmansWhisper\")
Copy-Item -Force (Join-Path $Root "Data\MCM\Config\PickmansWhisper\settings.ini") (Join-Path $Deploy "MCM\Config\PickmansWhisper\")
Copy-Item -Force (Join-Path $Root "Data\MCM\Settings\PickmansWhisper.ini") (Join-Path $Deploy "MCM\Settings\")

Get-ChildItem (Join-Path $Root "Data\PickmansWhisper\config\*.txt") -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-Item -Force $_.FullName (Join-Path $Deploy "PickmansWhisper\config\")
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
