#!/usr/bin/env python3
"""Contracts for Slice E — named kill voice + soft Necromantic intimacy events.

Locks:
  - ModConfig namedKillToast / namedIntimacyToast keys ship; audio keys optional (#)
  - ProcessKnifeKill branches via MaybeSpeakNamedKillVoice before generic praise
  - Kill blade helpers still IsBladeEquipped / IsBladeKillWeaponReady (satiation untouched)
  - Soft Necromantic: GetFormFromFile(0x800) + RegisterForCustomEvent Start/End
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
STUB = ROOT / "tools" / "stubs" / "NecromanticMainQuestScript.psc"
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"


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


def test_modconfig() -> None:
    if not MOD_CONFIG.is_file():
        fail(f"missing {MOD_CONFIG}")
    keys = parse_modconfig_active_keys(MOD_CONFIG)
    if "namedKillToast" not in keys or not keys["namedKillToast"]:
        fail("ModConfig must ship namedKillToast")
    if "{name}" not in keys["namedKillToast"]:
        fail("namedKillToast should support {name}")
    if "namedIntimacyToast" not in keys or not keys["namedIntimacyToast"]:
        fail("ModConfig must ship namedIntimacyToast")
    # Audio keys must stay commented until xwm exists (no silent missing SNDR at build).
    if "namedKillAudio" in keys:
        fail("namedKillAudio must stay commented until NamedKill.xwm ships")
    if "namedIntimacyAudio" in keys:
        fail("namedIntimacyAudio must stay commented until NamedIntimacy.xwm ships")
    text = MOD_CONFIG.read_text(encoding="utf-8")
    if "namedKillAudio=" not in text or "namedIntimacyAudio=" not in text:
        fail("ModConfig should document namedKillAudio / namedIntimacyAudio (commented)")
    ok("ModConfig named toast keys; audio keys documented but inactive")


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
    # Fall back path still present
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
    if 'GetFormFromFile(FID_NECROMANTIC_MAIN, "Necromantic.esp")' not in reg and (
        "0x00000800" not in reg and "FID_NECROMANTIC_MAIN" not in reg
    ):
        fail("RegisterNecromanticSceneEvents must GetFormFromFile Necromantic 0x800")
    if 'RegisterForCustomEvent(necro, "OnNecroSceneStart")' not in reg:
        fail("must RegisterForCustomEvent OnNecroSceneStart")
    if 'RegisterForCustomEvent(necro, "OnNecroSceneEnd")' not in reg:
        fail("must RegisterForCustomEvent OnNecroSceneEnd")
    if "OnQuestInit" in text:
        # call sites
        if "RegisterNecromanticSceneEvents()" not in text:
            fail("must call RegisterNecromanticSceneEvents from init/load")
    if "Event NecromanticMainQuestScript.OnNecroSceneStart" not in text:
        fail("missing OnNecroSceneStart handler")
    if "Event NecromanticMainQuestScript.OnNecroSceneEnd" not in text:
        fail("missing OnNecroSceneEnd handler")
    intimacy = extract_function(text, "MaybeSpeakNamedIntimacyVoice")
    if "GetVictimOverrideName" not in intimacy:
        fail("intimacy voice must filter named Potential Victims")
    if "NamedIntimacyToast" not in intimacy:
        fail("intimacy voice must use NamedIntimacyToast")
    if "IsVoiceWeaponReady" not in intimacy:
        fail("intimacy voice must gate IsVoiceWeaponReady")
    builder = BUILDER.read_text(encoding="utf-8")
    if "Necromantic.esp" in builder:
        fail("esp builder must not master/reference Necromantic.esp")
    if "parse_modconfig_audio_files" not in builder:
        fail("builder should clone optional ModConfig audio stems")
    ok("E2 soft Necromantic CustomEvent contract + stub")


def test_load_modconfig(text: str) -> None:
    load = extract_function(text, "LoadModConfig")
    for key in (
        "namedKillToast",
        "namedKillAudio",
        "namedIntimacyToast",
        "namedIntimacyAudio",
    ):
        if f'key == "{key}"' not in load:
            fail(f"LoadModConfig must parse {key}")
    play = extract_function(text, "PlayWhisperXwmByFile")
    if "IsVoiceWeaponReady" not in play:
        fail("PlayWhisperXwmByFile must gate IsVoiceWeaponReady")
    if "Debug.Notification" not in play:
        fail("PlayWhisperXwmByFile must fail loud")
    notice = extract_function(text, "PlayNoticeAudio")
    if "PlayWhisperXwmByFile" not in notice:
        fail("PlayNoticeAudio must delegate to PlayWhisperXwmByFile")
    ok("LoadModConfig keys + shared PlayWhisperXwmByFile")


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
    test_kill_branch(text)
    test_necro_soft(text)
    test_load_modconfig(text)
    test_kill_helpers_untouched(text)
    print("All named-kill / Necromantic E contracts passed.")


if __name__ == "__main__":
    main()
