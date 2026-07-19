#!/usr/bin/env python3
"""Contracts for Slice E — named kill voice + soft Necromantic intimacy events.

Locks:
  - ModConfig namedKillToast ships; intimacy toast/audio keys retired (E4/E5 banks)
  - E4/E5: Intimacy_Start_Named / Intimacy_End_Named + parallel *_Audio.txt (23+23)
  - ProcessKnifeKill branches via MaybeSpeakNamedKillVoice before generic praise
  - Kill blade helpers still IsBladeEquipped / IsBladeKillWeaponReady (satiation untouched)
  - Soft Necromantic: GetFormFromFile(0x800) + RegisterForCustomEvent Start/End
  - MaybeSpeakNamedIntimacyEvent — iVoiceDelivery same-index like notice D1
  - Minimal stub only — no Necromantic.esp master in esp builder
  - PlayWhisperXwmByFile resolves subdir keys; voice paths gate IsVoiceWeaponReady
  - Builder emits Necromantic SNDRs; deploy copies Sound tree recursively
  - No namedIntimacyAudio on scene path

Usage:
  python tools/test_named_kill_voice.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MOD_CONFIG = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
NECRO = ROOT / "Data" / "PickmansWhisper" / "config" / "necromantic"
START_NAMED = NECRO / "Intimacy_Start_Named.txt"
END_NAMED = NECRO / "Intimacy_End_Named.txt"
START_AUDIO = NECRO / "Intimacy_Start_Audio.txt"
END_AUDIO = NECRO / "Intimacy_End_Audio.txt"
SOUND = ROOT / "Data" / "Sound" / "PickmansWhisper"
STUB = ROOT / "tools" / "stubs" / "NecromanticMainQuestScript.psc"
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"

EXPECTED_INTIMACY = 23


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:Function|Bool Function|Int Function|String Function)\s+{name}\s*\(",
        text,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", text[start:])
    if not end_m:
        fail(f"no EndFunction for {name}")
    return text[start : start + end_m.end()]


def parse_modconfig_active_keys(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip()
    return out


def parse_bank_lines(path: Path) -> list[str]:
    out: list[str] = []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def numeric_prefix_key(rel: str) -> tuple[int, str]:
    """Sort key from leading digits in the leaf filename."""
    leaf = Path(rel.replace("\\", "/")).name
    m = re.match(r"^(\d+)", leaf)
    if not m:
        fail(f"audio map entry missing numeric prefix: {rel}")
    return int(m.group(1)), leaf


def test_modconfig() -> None:
    if not MOD_CONFIG.is_file():
        fail(f"missing {MOD_CONFIG}")
    keys = parse_modconfig_active_keys(MOD_CONFIG)
    if "namedKillToast" not in keys or not keys["namedKillToast"]:
        fail("ModConfig must ship namedKillToast")
    if "{name}" not in keys["namedKillToast"]:
        fail("namedKillToast should support {name}")
    for retired in (
        "namedIntimacyToast",
        "namedIntimacyEndToast",
        "namedIntimacyAudio",
    ):
        if retired in keys:
            fail(f"{retired} retired — use Intimacy_*_Named / *_Audio banks (E5)")
    if "namedKillAudio" in keys:
        fail("namedKillAudio must stay commented until NamedKill.xwm ships")
    text = MOD_CONFIG.read_text(encoding="utf-8")
    if "Intimacy_Start_Named.txt" not in text or "Intimacy_End_Named.txt" not in text:
        fail("ModConfig should document E4/E5 named intimacy banks")
    if "Intimacy_Start_Audio.txt" not in text or "Intimacy_End_Audio.txt" not in text:
        fail("ModConfig should document E5 intimacy audio maps")
    if "Intimacy_Stop" in text:
        fail("ModConfig must use End naming (not Stop)")
    ok("ModConfig kill toast; intimacy retired to E4/E5 banks")


def test_intimacy_banks() -> None:
    for path in (START_NAMED, END_NAMED, START_AUDIO, END_AUDIO):
        if not path.is_file():
            fail(f"missing {path}")
    if (NECRO / "Intimacy_Stop_Named.txt").is_file():
        fail("Intimacy_Stop_Named.txt must be renamed to Intimacy_End_Named.txt")
    if (NECRO / "Intimacy_Stop_Audio.txt").is_file():
        fail("Intimacy_Stop_Audio.txt must be renamed to Intimacy_End_Audio.txt")

    start = parse_bank_lines(START_NAMED)
    end = parse_bank_lines(END_NAMED)
    start_audio = parse_bank_lines(START_AUDIO)
    end_audio = parse_bank_lines(END_AUDIO)

    if len(start) != EXPECTED_INTIMACY:
        fail(f"Intimacy_Start_Named.txt need {EXPECTED_INTIMACY} lines, got {len(start)}")
    if len(end) != EXPECTED_INTIMACY:
        fail(f"Intimacy_End_Named.txt need {EXPECTED_INTIMACY} lines, got {len(end)}")
    if len(start_audio) != EXPECTED_INTIMACY:
        fail(f"Intimacy_Start_Audio.txt need {EXPECTED_INTIMACY} lines, got {len(start_audio)}")
    if len(end_audio) != EXPECTED_INTIMACY:
        fail(f"Intimacy_End_Audio.txt need {EXPECTED_INTIMACY} lines, got {len(end_audio)}")

    if not any("{name}" in ln for ln in start):
        fail("Intimacy_Start_Named.txt should include {name} lines")
    if not any("{name}" in ln for ln in end):
        fail("Intimacy_End_Named.txt should include {name} lines")

    start_disk = sorted(
        (SOUND / "Necromantic" / "Start").glob("*.xwm"),
        key=lambda p: numeric_prefix_key(p.name),
    )
    end_disk = sorted(
        (SOUND / "Necromantic" / "End").glob("*.xwm"),
        key=lambda p: numeric_prefix_key(p.name),
    )
    if len(start_disk) != EXPECTED_INTIMACY:
        fail(f"Necromantic/Start need {EXPECTED_INTIMACY} xwm, got {len(start_disk)}")
    if len(end_disk) != EXPECTED_INTIMACY:
        fail(f"Necromantic/End need {EXPECTED_INTIMACY} xwm, got {len(end_disk)}")

    for i, rel in enumerate(start_audio):
        key = rel.replace("\\", "/")
        if not key.startswith("Necromantic/Start/"):
            fail(f"Start audio map must be under Necromantic/Start/: {rel}")
        if not (SOUND / Path(*key.split("/"))).is_file():
            fail(f"missing on-disk xwm for Start map: {rel}")
        if i > 0 and numeric_prefix_key(key) < numeric_prefix_key(start_audio[i - 1]):
            fail("Intimacy_Start_Audio.txt must be numeric-prefix sorted")

    for i, rel in enumerate(end_audio):
        key = rel.replace("\\", "/")
        if not key.startswith("Necromantic/End/"):
            fail(f"End audio map must be under Necromantic/End/: {rel}")
        if not (SOUND / Path(*key.split("/"))).is_file():
            fail(f"missing on-disk xwm for End map: {rel}")
        if i > 0 and numeric_prefix_key(key) < numeric_prefix_key(end_audio[i - 1]):
            fail("Intimacy_End_Audio.txt must be numeric-prefix sorted")

    # Maps must list actual filenames (incl. quirky names like 04LookAtHer / 01-ColdNow..)
    start_names = {p.name for p in start_disk}
    end_names = {p.name for p in end_disk}
    for rel in start_audio:
        leaf = Path(rel.replace("\\", "/")).name
        if leaf not in start_names:
            fail(f"Start audio map leaf not on disk: {leaf}")
    for rel in end_audio:
        leaf = Path(rel.replace("\\", "/")).name
        if leaf not in end_names:
            fail(f"End audio map leaf not on disk: {leaf}")

    ok(f"E5 banks 23/23 Named+Audio; on-disk xwm match")


def test_kill_branch(text: str) -> None:
    proc = extract_function(text, "ProcessKnifeKill")
    if "MaybeSpeakNamedKillVoice" not in proc:
        fail("ProcessKnifeKill must call MaybeSpeakNamedKillVoice")
    if "SatiateHunger" not in proc:
        fail("ProcessKnifeKill must still SatiateHunger")
    if "IsBladeEquipped" not in proc:
        fail("ProcessKnifeKill must keep IsBladeEquipped gate")
    named = extract_function(text, "MaybeSpeakNamedKillVoice")
    if "GetVictimOverrideName" not in named:
        fail("MaybeSpeakNamedKillVoice must use GetVictimOverrideName")
    if "NamedKillToast" not in named:
        fail("MaybeSpeakNamedKillVoice must require NamedKillToast")
    if "IsVoiceWeaponReady" not in named:
        fail("MaybeSpeakNamedKillVoice must gate IsVoiceWeaponReady")
    if "GetVoiceDeliveryMode" not in named:
        fail("MaybeSpeakNamedKillVoice must honor GetVoiceDeliveryMode")
    if "PlayWhisperXwmByFile" not in named:
        fail("MaybeSpeakNamedKillVoice must play via PlayWhisperXwmByFile when audio set")
    if "PickPraiseLine" not in proc or "ToastPraiseLine" not in proc:
        fail("ProcessKnifeKill must fall back to PickPraiseLine/ToastPraiseLine")
    ok("E1 kill voice branch; satiation + praise fallback intact")


def test_necro_soft(text: str) -> None:
    if not STUB.is_file():
        fail(f"missing stub {STUB}")
    stub = STUB.read_text(encoding="utf-8")
    if "CustomEvent OnNecroSceneStart" not in stub:
        fail("stub must declare CustomEvent OnNecroSceneStart")
    if "CustomEvent OnNecroSceneEnd" not in stub:
        fail("stub must declare CustomEvent OnNecroSceneEnd")
    if re.search(r"\bNative\b", stub):
        fail("Necromantic stub must not invent Native functions")
    reg = extract_function(text, "RegisterNecromanticSceneEvents")
    if "FID_NECROMANTIC_MAIN" not in reg and "0x00000800" not in reg:
        fail("RegisterNecromanticSceneEvents must GetFormFromFile Necromantic 0x800")
    if 'RegisterForCustomEvent(necro, "OnNecroSceneStart")' not in reg:
        fail("must RegisterForCustomEvent OnNecroSceneStart")
    if 'RegisterForCustomEvent(necro, "OnNecroSceneEnd")' not in reg:
        fail("must RegisterForCustomEvent OnNecroSceneEnd")
    if "RegisterNecromanticSceneEvents()" not in text:
        fail("must call RegisterNecromanticSceneEvents from init/load")
    if "Event NecromanticMainQuestScript.OnNecroSceneStart" not in text:
        fail("missing OnNecroSceneStart handler")
    if "Event NecromanticMainQuestScript.OnNecroSceneEnd" not in text:
        fail("missing OnNecroSceneEnd handler")
    if "MaybeSpeakNamedIntimacyVoice" in text:
        fail("MaybeSpeakNamedIntimacyVoice retired — use MaybeSpeakNamedIntimacyEvent (E5)")
    intimacy = extract_function(text, "MaybeSpeakNamedIntimacyEvent")
    if "GetVictimOverrideName" not in intimacy:
        fail("intimacy voice must filter named Potential Victims")
    if "GetVoiceDeliveryMode" not in intimacy:
        fail("MaybeSpeakNamedIntimacyEvent must honor GetVoiceDeliveryMode")
    if "IsVoiceWeaponReady" not in intimacy:
        fail("intimacy voice must gate IsVoiceWeaponReady")
    if "PickIntimacyNamedIndex" not in intimacy:
        fail("intimacy must PickIntimacyNamedIndex for toast modes")
    if "PickIntimacyAudioIndex" not in intimacy:
        fail("intimacy audio-only must PickIntimacyAudioIndex")
    if "PlayIntimacyAudioAt" not in intimacy:
        fail("intimacy must PlayIntimacyAudioAt for same-index / audio-only")
    if "NamedIntimacyAudio" in text:
        fail("PSC must not keep NamedIntimacyAudio (E5 banks)")
    if "NamedIntimacyToast" in text or "NamedIntimacyEndToast" in text:
        fail("PSC must not keep NamedIntimacyToast / NamedIntimacyEndToast vars (E4)")
    if "Intimacy_Stop" in text or "IntimacyStop" in text:
        fail("PSC must use End naming (not Stop)")
    builder = BUILDER.read_text(encoding="utf-8")
    if "Necromantic.esp" in builder:
        fail("esp builder must not master/reference Necromantic.esp")
    if "Intimacy_Start_Audio.txt" not in builder or "Intimacy_End_Audio.txt" not in builder:
        fail("builder must parse Intimacy Start/End audio maps")
    if "namedIntimacyAudio" in builder and "retired" not in builder.lower():
        # allow comment about retirement; reject active MOD_CONFIG_AUDIO_KEYS entry
        if re.search(r'MOD_CONFIG_AUDIO_KEYS\s*=\s*\([^)]*namedIntimacyAudio', builder):
            fail("builder must not emit namedIntimacyAudio from ModConfig")
    ok("E2 soft Necromantic + E5 same-index intimacy delivery")


def test_e5_load_pick(text: str) -> None:
    load_banks = extract_function(text, "LoadLineBanks")
    if "LoadIntimacyNamedLines()" not in load_banks:
        fail("LoadLineBanks must call LoadIntimacyNamedLines")
    load = extract_function(text, "LoadIntimacyNamedLines")
    for name in (
        "Intimacy_Start_Named.txt",
        "Intimacy_End_Named.txt",
        "Intimacy_Start_Audio.txt",
        "Intimacy_End_Audio.txt",
    ):
        if name not in load:
            fail(f"LoadIntimacyNamedLines must read {name}")
    if "ReportIntimacyAudioCountMismatch" not in load:
        fail("LoadIntimacyNamedLines must report toast/audio count mismatch")
    if "NecromanticConfigPath" not in load and "necromantic" not in load:
        fail("LoadIntimacyNamedLines must use necromantic config path")
    path_fn = extract_function(text, "NecromanticConfigPath")
    if "necromantic" not in path_fn:
        fail("NecromanticConfigPath must point at config/necromantic")
    for name in (
        "LoadStageBankAt",
        "PickIntimacyNamedIndex",
        "PickIntimacyAudioIndex",
        "PlayIntimacyAudioAt",
        "MaybeSpeakNamedIntimacyEvent",
    ):
        extract_function(text, name)
    named_pick = extract_function(text, "PickIntimacyNamedIndex")
    audio_pick = extract_function(text, "PickIntimacyAudioIndex")
    if "RandomInt" not in named_pick or "RandomInt" not in audio_pick:
        fail("intimacy picks must use Utility.RandomInt")
    if "LastIntimacyStartLine" not in named_pick or "LastIntimacyEndLine" not in named_pick:
        fail("intimacy named picks must no-immediate-repeat")
    load_cfg = extract_function(text, "LoadModConfig")
    if 'key == "namedIntimacyToast"' in load_cfg or 'key == "namedIntimacyEndToast"' in load_cfg:
        fail("LoadModConfig must not parse retired intimacy toast keys")
    if 'key == "namedIntimacyAudio"' in load_cfg:
        fail("LoadModConfig must not parse namedIntimacyAudio (E5)")
    if 'key == "namedKillToast"' not in load_cfg:
        fail("LoadModConfig must still parse namedKillToast")
    start_evt = text[
        text.find("Event NecromanticMainQuestScript.OnNecroSceneStart") : text.find(
            "Event NecromanticMainQuestScript.OnNecroSceneEnd"
        )
    ]
    end_evt = extract_function(text, "MaybeSpeakNamedIntimacyEvent")  # handlers call this
    if "MaybeSpeakNamedIntimacyEvent(corpse, True)" not in text:
        fail("OnNecroSceneStart must MaybeSpeakNamedIntimacyEvent(..., True)")
    if "MaybeSpeakNamedIntimacyEvent(corpse, False)" not in text:
        fail("OnNecroSceneEnd must MaybeSpeakNamedIntimacyEvent(..., False)")
    _ = start_evt  # keep unused quiet
    _ = end_evt
    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "necromantic" not in deploy:
        fail("build-deploy-local.ps1 must copy config/necromantic")
    if "Necromantic\\Start" not in deploy and "Necromantic/Start" not in deploy:
        fail("deploy must verify Necromantic Start xwm (recursive sound)")
    if "Get-ChildItem" not in deploy and "Copy-Item" not in deploy:
        fail("deploy must copy Sound tree")
    # Recursive copy: soundSrc + Recurse or Copy-Item -Recurse on Sound\PickmansWhisper
    if "Sound\\PickmansWhisper" not in deploy:
        fail("deploy must copy Sound\\PickmansWhisper")
    if "-Recurse" not in deploy and "Recurse" not in deploy:
        fail("deploy Sound copy must be recursive (E5 subdirs)")
    ok("E5 load/pick + deploy necromantic + recursive sound")


def test_play_subdir_and_sndr_cap(text: str) -> None:
    play = extract_function(text, "PlayWhisperXwmByFile")
    if "IsVoiceWeaponReady" not in play:
        fail("PlayWhisperXwmByFile must gate IsVoiceWeaponReady")
    if "Debug.Notification" not in play:
        fail("PlayWhisperXwmByFile must fail loud")
    if 'c == "/"' not in play and "lastSep" not in play:
        fail("PlayWhisperXwmByFile must split relative subdir keys")
    load_ids = extract_function(text, "LoadWhisperSndrIds")
    if "new String[128]" not in load_ids and "WHISPER_SNDR_MAX" not in text:
        fail("LoadWhisperSndrIds must support >=128 entries for intimacy SNDRs")
    if "WHISPER_SNDR_MAX" in text:
        if "WhisperSndrCount < WHISPER_SNDR_MAX" not in load_ids:
            fail("LoadWhisperSndrIds loop must use WHISPER_SNDR_MAX")
    notice = extract_function(text, "PlayNoticeAudio")
    if "PlayWhisperXwmByFile" not in notice:
        fail("PlayNoticeAudio must delegate to PlayWhisperXwmByFile")
    builder = BUILDER.read_text(encoding="utf-8")
    if "edid_stem_from_map_key" not in builder:
        fail("builder must sanitize relative-path EDIDs")
    if r"Sound\PickmansWhisper\{rel}" not in builder and "Sound\\PickmansWhisper\\" not in builder:
        fail("builder ANAM must use Sound\\PickmansWhisper\\<relative>")
    ok("PlayWhisperXwmByFile subdir + SNDR cap + builder relative ANAM")


def test_kill_helpers_untouched(text: str) -> None:
    blade = extract_function(text, "IsBladeEquipped")
    if "FindEquippedPickmansBladeIndex" not in blade:
        fail("IsBladeEquipped must remain GoE scan")
    kill = extract_function(text, "IsBladeKillWeaponReady")
    if not re.search(r"Return\s+IsBladeEquipped\s*\(\s*\)", kill):
        fail("IsBladeKillWeaponReady must still alias IsBladeEquipped")
    ok("kill blade helpers unchanged")


def main() -> None:
    if not PSC.is_file():
        fail(f"missing {PSC}")
    text = PSC.read_text(encoding="utf-8", errors="replace")
    test_modconfig()
    test_intimacy_banks()
    test_kill_branch(text)
    test_necro_soft(text)
    test_e5_load_pick(text)
    test_play_subdir_and_sndr_cap(text)
    test_kill_helpers_untouched(text)
    print("All named-kill / Necromantic E contracts passed.")


if __name__ == "__main__":
    main()
