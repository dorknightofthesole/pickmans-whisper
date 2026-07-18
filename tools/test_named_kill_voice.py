#!/usr/bin/env python3
"""Contracts for Slice E — named kill voice + soft Necromantic intimacy events.

Locks:
  - ModConfig namedKillToast ships; intimacy toast keys retired (E4 banks)
  - E4: Intimacy_Start_Named.txt / Intimacy_Stop_Named.txt load + random pick
  - ProcessKnifeKill branches via MaybeSpeakNamedKillVoice before generic praise
  - Kill blade helpers still IsBladeEquipped / IsBladeKillWeaponReady (satiation untouched)
  - Soft Necromantic: GetFormFromFile(0x800) + RegisterForCustomEvent Start/End
  - MaybeSpeakNamedIntimacyVoice(partner, toastTemplate, audioFile) — Start/End pass picks
  - Minimal stub only — no Necromantic.esp master in esp builder
  - PlayWhisperXwmByFile fails loud; voice paths gate IsVoiceWeaponReady

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
STOP_NAMED = NECRO / "Intimacy_Stop_Named.txt"
STUB = ROOT / "tools" / "stubs" / "NecromanticMainQuestScript.psc"
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"


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
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def test_modconfig() -> None:
    if not MOD_CONFIG.is_file():
        fail(f"missing {MOD_CONFIG}")
    keys = parse_modconfig_active_keys(MOD_CONFIG)
    if "namedKillToast" not in keys or not keys["namedKillToast"]:
        fail("ModConfig must ship namedKillToast")
    if "{name}" not in keys["namedKillToast"]:
        fail("namedKillToast should support {name}")
    # E4: single-line intimacy toasts retired
    if "namedIntimacyToast" in keys:
        fail("namedIntimacyToast retired — use Intimacy_Start_Named.txt (E4)")
    if "namedIntimacyEndToast" in keys:
        fail("namedIntimacyEndToast retired — use Intimacy_Stop_Named.txt (E4)")
    if "namedKillAudio" in keys:
        fail("namedKillAudio must stay commented until NamedKill.xwm ships")
    if "namedIntimacyAudio" in keys:
        fail("namedIntimacyAudio must stay commented until NamedIntimacy.xwm ships")
    text = MOD_CONFIG.read_text(encoding="utf-8")
    if "Intimacy_Start_Named.txt" not in text or "Intimacy_Stop_Named.txt" not in text:
        fail("ModConfig should document E4 named intimacy banks")
    ok("ModConfig kill toast; intimacy toasts retired to E4 banks")


def test_intimacy_banks() -> None:
    if not START_NAMED.is_file():
        fail(f"missing {START_NAMED}")
    if not STOP_NAMED.is_file():
        fail(f"missing {STOP_NAMED}")
    start = parse_bank_lines(START_NAMED)
    stop = parse_bank_lines(STOP_NAMED)
    if len(start) < 2:
        fail(f"Intimacy_Start_Named.txt need >= 2 lines, got {len(start)}")
    if len(stop) < 2:
        fail(f"Intimacy_Stop_Named.txt need >= 2 lines, got {len(stop)}")
    if not any("{name}" in ln for ln in start):
        fail("Intimacy_Start_Named.txt should include {name} lines")
    if not any("{name}" in ln for ln in stop):
        fail("Intimacy_Stop_Named.txt should include {name} lines")
    ok(f"E4 banks present (start={len(start)} stop={len(stop)})")


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
    intimacy = extract_function(text, "MaybeSpeakNamedIntimacyVoice")
    if "GetVictimOverrideName" not in intimacy:
        fail("intimacy voice must filter named Potential Victims")
    if "toastTemplate" not in intimacy:
        fail("MaybeSpeakNamedIntimacyVoice must take toastTemplate param")
    if "IsVoiceWeaponReady" not in intimacy:
        fail("intimacy voice must gate IsVoiceWeaponReady")
    if "PickIntimacyStartNamedLine" not in text:
        fail("OnNecroSceneStart must PickIntimacyStartNamedLine")
    if "PickIntimacyStopNamedLine" not in text:
        fail("OnNecroSceneEnd must PickIntimacyStopNamedLine")
    if "NamedIntimacyToast" in text or "NamedIntimacyEndToast" in text:
        fail("PSC must not keep NamedIntimacyToast / NamedIntimacyEndToast vars (E4)")
    builder = BUILDER.read_text(encoding="utf-8")
    if "Necromantic.esp" in builder:
        fail("esp builder must not master/reference Necromantic.esp")
    if "parse_modconfig_audio_files" not in builder:
        fail("builder should clone optional ModConfig audio stems")
    ok("E2 soft Necromantic CustomEvent + E4 bank picks")


def test_e4_load_pick(text: str) -> None:
    load_banks = extract_function(text, "LoadLineBanks")
    if "LoadIntimacyNamedLines()" not in load_banks:
        fail("LoadLineBanks must call LoadIntimacyNamedLines")
    load = extract_function(text, "LoadIntimacyNamedLines")
    if "Intimacy_Start_Named.txt" not in load or "Intimacy_Stop_Named.txt" not in load:
        fail("LoadIntimacyNamedLines must read both Named banks")
    if "NecromanticConfigPath" not in load and "necromantic" not in load:
        fail("LoadIntimacyNamedLines must use necromantic config path")
    path_fn = extract_function(text, "NecromanticConfigPath")
    if "necromantic" not in path_fn:
        fail("NecromanticConfigPath must point at config/necromantic")
    for name in (
        "LoadStageBankAt",
        "PickIntimacyStartNamedLine",
        "PickIntimacyStopNamedLine",
    ):
        extract_function(text, name)
    start_pick = extract_function(text, "PickIntimacyStartNamedLine")
    stop_pick = extract_function(text, "PickIntimacyStopNamedLine")
    if "RandomInt" not in start_pick or "RandomInt" not in stop_pick:
        fail("intimacy picks must use Utility.RandomInt")
    if "LastIntimacyStartLine" not in start_pick or "LastIntimacyStopLine" not in stop_pick:
        fail("intimacy picks must no-immediate-repeat")
    load_cfg = extract_function(text, "LoadModConfig")
    if 'key == "namedIntimacyToast"' in load_cfg or 'key == "namedIntimacyEndToast"' in load_cfg:
        fail("LoadModConfig must not parse retired intimacy toast keys")
    if 'key == "namedKillToast"' not in load_cfg:
        fail("LoadModConfig must still parse namedKillToast")
    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "necromantic" not in deploy:
        fail("build-deploy-local.ps1 must copy config/necromantic")
    ok("E4 load/pick + deploy necromantic folder")


def test_load_audio_helpers(text: str) -> None:
    play = extract_function(text, "PlayWhisperXwmByFile")
    if "IsVoiceWeaponReady" not in play:
        fail("PlayWhisperXwmByFile must gate IsVoiceWeaponReady")
    if "Debug.Notification" not in play:
        fail("PlayWhisperXwmByFile must fail loud")
    notice = extract_function(text, "PlayNoticeAudio")
    if "PlayWhisperXwmByFile" not in notice:
        fail("PlayNoticeAudio must delegate to PlayWhisperXwmByFile")
    ok("shared PlayWhisperXwmByFile intact")


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
    test_e4_load_pick(text)
    test_load_audio_helpers(text)
    test_kill_helpers_untouched(text)
    print("All named-kill / Necromantic E contracts passed.")


if __name__ == "__main__":
    main()
