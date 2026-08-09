#!/usr/bin/env python3
"""Contracts for Slice H P5 — reward/toast when the player actually eats a max-stage corpse.

Detection design: no vanilla FO4 script registers an animation event for the Cannibal
eat action, so we listen for PerkCannibalHeal's RestoreHealthGeneric MGEF on the player
alias, latch PendingEatRipeReward, then claim it from HandleCorpseDecay →
MaybeRewardEatenRipeCorpse(akCorpse) on the TargetScan corpse (no KillerScan ScanDead).

Registration lives on PickmansWhisperPlayerAliasScript (ReferenceAlias filled with the
player). Quest-level RegisterForMagicEffectApplyEvent was confirmed dead live.

Locks:
  - ModConfig ateRipeCorpseToast ships with {name} support
  - LoadModConfig parses + resets ateRipeCorpseToast
  - tools/stubs/ScriptObject.psc declares RegisterForMagicEffectApplyEvent + OnMagicEffectApply
  - MainQuestScript.GetRestoreHealthGenericEffect + PlayerAlias Auto Const
  - PlayerAliasScript.RegisterMagicEffectDetect + OnMagicEffectApply → HandlePlayerMagicEffectApply
  - HandlePlayerMagicEffectApply → NotePendingEatRipeReward (not immediate reward)
  - HandleCorpseDecay at max stage → MaybeRewardEatenRipeCorpse(akCorpse)
  - MaybeRewardEatenRipeCorpse(Actor): pending latch, Cannibal perk, butcher range,
    tracked + max-stage on that actor; no KillerScan / FindActors
  - ToastAteRipeCorpse: {name} -> "She" fallback when unnamed
  - ApplyEatRipeCorpseBonus → BuffTrackerScript.ApplyEatRipeCorpseEndBuff
  - FID_MGEF_RESTORE_HEALTH_GENERIC verified against Fallout4.esm
  - SyncMagicEffectSniffer delegates to alias.SyncMagicEffectSniff

Usage:
  python tools/test_decay_eaten_ripe_corpse.py
  python tools/test_decay_eaten_ripe_corpse.py --esm "<path>/Fallout4.esm"
"""
from __future__ import annotations

import argparse
import re
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"
MODCFG = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
ALIAS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
MOD_CONFIG = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
STUB_SCRIPTOBJECT = ROOT / "tools" / "stubs" / "ScriptObject.psc"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
MCM_CONFIG = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
MCM_SETTINGS = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
SETTINGS_LEGACY = ROOT / "Data" / "MCM" / "Settings" / "PickmansWhisper.ini"

FID_MGEF_RESTORE_HEALTH_GENERIC = 0x00023735
EDID_RESTORE_HEALTH_GENERIC = b"RestoreHealthGeneric"


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


def extract_event(text: str, signature_start: str) -> str:
    idx = text.find(signature_start)
    if idx < 0:
        fail(f"missing event {signature_start!r}")
    end_m = re.search(r"\nEndEvent\b", text[idx:])
    if not end_m:
        fail(f"no EndEvent for {signature_start!r}")
    return text[idx : idx + end_m.end()]


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
    if "ateRipeCorpseToast" not in keys or not keys["ateRipeCorpseToast"]:
        fail("ModConfig must ship ateRipeCorpseToast")
    if "{name}" not in keys["ateRipeCorpseToast"]:
        fail("ateRipeCorpseToast should support {name}")
    ok("ModConfig ateRipeCorpseToast ships with {name}")


def test_stub() -> None:
    stub = STUB_SCRIPTOBJECT.read_text(encoding="utf-8", errors="replace")
    if not re.search(
        r"Function\s+RegisterForMagicEffectApplyEvent\s*\(\s*ScriptObject\s+\w+\s*,\s*ScriptObject\s+\w+\s*=\s*None\s*,\s*Form\s+\w+\s*=\s*None\s*,\s*Bool\s+\w+\s*=\s*True\s*\)\s*Native",
        stub,
    ):
        fail("tools/stubs/ScriptObject.psc must declare RegisterForMagicEffectApplyEvent matching the real signature")
    if "Event OnMagicEffectApply(ObjectReference akTarget, ObjectReference akCaster, MagicEffect akEffect)" not in stub:
        fail("tools/stubs/ScriptObject.psc must declare the base OnMagicEffectApply event")
    ok("ScriptObject stub declares RegisterForMagicEffectApplyEvent + OnMagicEffectApply")


def test_main_wiring() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")

    if "FID_MGEF_RESTORE_HEALTH_GENERIC = 0x00023735" not in text:
        fail("FID_MGEF_RESTORE_HEALTH_GENERIC must be 0x00023735 (Fallout4.esm RestoreHealthGeneric)")

    resolve = extract_function(text, "ResolveVanillaForms")
    if "RestoreHealthGenericEffect" not in resolve or "FID_MGEF_RESTORE_HEALTH_GENERIC" not in resolve:
        fail("ResolveVanillaForms must lazy-load RestoreHealthGenericEffect")

    getter = extract_function(text, "GetRestoreHealthGenericEffect")
    if "ResolveVanillaForms()" not in getter or "Return RestoreHealthGenericEffect" not in getter:
        fail("GetRestoreHealthGenericEffect must ResolveVanillaForms then return the field (alias-callable getter)")

    if "PickmansWhisperPlayerAliasScript Property PlayerAlias Auto Const" not in text:
        fail("Main must declare PlayerAlias Auto Const (CK/VMAD bind to PlayerCombat)")
    if "Function PlayerAlias()" in text:
        fail("PlayerAlias() GetFormFromFile facade retired — use Auto Const property")
    if "Return pq.GetAlias(0)" in text:
        fail("retired PlayerAlias facade must not GetAlias(0) via PlayerCombat")

    if "RegisterEatCorpseDetection" in text or "Event Actor.OnMagicEffectApply" in text:
        fail("Quest-level RegisterForMagicEffectApplyEvent detection must be fully removed (confirmed dead live; moved to PlayerAliasScript)")

    for anchor in ("OnQuestInit", "HandleGameResume"):
        body = extract_event(text, f"Event {anchor}()") if anchor == "OnQuestInit" else extract_function(text, anchor)
        if "RegisterForMagicEffectApplyEvent" in body:
            fail(f"{anchor} must not register magic-effect-apply directly (moved to PlayerAliasScript)")

    handler = extract_function(text, "HandlePlayerMagicEffectApply")
    if "akEffect != RestoreHealthGenericEffect" not in handler:
        fail("HandlePlayerMagicEffectApply must re-verify akEffect before dispatching")
    if "NotePendingEatRipeReward()" not in handler:
        fail("HandlePlayerMagicEffectApply must call NotePendingEatRipeReward (latch for HandleCorpseDecay)")
    if "MaybeRewardEatenRipeCorpse(" in handler:
        fail("HandlePlayerMagicEffectApply must not call MaybeRewardEatenRipeCorpse directly (no Actor yet)")
    if "DebugSniffMagicEffects" not in handler:
        fail("HandlePlayerMagicEffectApply must Trace every effect while the P5 discovery sniffer is on")

    sniffer = extract_function(text, "SyncMagicEffectSniffer")
    if 'MCM.GetModSettingBool(MOD_NAME, "bSniffMagicEffects:Debug")' not in sniffer:
        fail("SyncMagicEffectSniffer must read bSniffMagicEffects:Debug")
    if "PlayerAlias.SyncMagicEffectSniff(want)" not in sniffer:
        fail("SyncMagicEffectSniffer must call PlayerAlias.SyncMagicEffectSniff (Auto Const property)")
    if "!PlayerAlias" not in sniffer:
        fail("SyncMagicEffectSniffer must guard unbound PlayerAlias property")

    if 'id == "bSniffMagicEffects:Debug"' not in extract_function(text, "OnMCMSettingChange"):
        fail("OnMCMSettingChange must dispatch bSniffMagicEffects:Debug to SyncMagicEffectSniffer")

    facade = extract_function(text, "NotePendingEatRipeReward")
    if "CorpseDecay()" not in facade:
        fail("Main NotePendingEatRipeReward must facade via CorpseDecay()")
    decay_txt = DECAY.read_text(encoding="utf-8", errors="replace")
    note = extract_function(decay_txt, "NotePendingEatRipeReward")
    if "PendingEatRipeReward = True" not in note:
        fail("NotePendingEatRipeReward must set PendingEatRipeReward = True")
    if "eaten-ripe-corpse pending" not in note:
        fail("NotePendingEatRipeReward must Trace pending latch (no silent set)")

    handle = extract_function(decay_txt, "HandleCorpseDecay")
    if "MaybeRewardEatenRipeCorpse(akCorpse)" not in handle:
        fail("HandleCorpseDecay must call MaybeRewardEatenRipeCorpse(akCorpse) at max stage")
    if "KillerScan" in handle or "ScanDead" in handle:
        fail("HandleCorpseDecay must not use KillerScan / ScanDead for P5 reward")

    reward = extract_function(decay_txt, "MaybeRewardEatenRipeCorpse")
    if "Actor akCorpse" not in reward[:120]:
        fail("MaybeRewardEatenRipeCorpse must take Actor akCorpse")
    if "!PendingEatRipeReward" not in reward:
        fail("MaybeRewardEatenRipeCorpse must early-return when PendingEatRipeReward is False")
    if "PlayerHasCannibalPerk()" not in reward:
        fail("MaybeRewardEatenRipeCorpse must gate on PlayerHasCannibalPerk (RestoreHealthGeneric is not cannibal-exclusive)")
    if "KillerScan" in reward or "ScanDead" in reward:
        fail("MaybeRewardEatenRipeCorpse must not use KillerScan / ScanDead (Actor param from HandleCorpseDecay)")
    if "FindActors" in reward:
        fail("MaybeRewardEatenRipeCorpse must not FindActors")
    if "butcherR" not in reward and "BUTCHER_CORPSE_RADIUS" not in reward:
        fail("MaybeRewardEatenRipeCorpse must cap butcher range (500)")
    if "GetDistance(akCorpse)" not in reward:
        fail("MaybeRewardEatenRipeCorpse must GetDistance(akCorpse) for butcher range")
    if "FindDecayKillSlot(formId)" not in reward:
        fail("MaybeRewardEatenRipeCorpse must require the corpse be tracked")
    stage_check_idx = reward.find(
        "ResolveDecayStageForKill(formId) != (DECAY_STAGE_COUNT - 1)"
    )
    if stage_check_idx < 0:
        fail("MaybeRewardEatenRipeCorpse must require the corpse be at max decay stage (DECAY_STAGE_COUNT - 1)")
    if "ToastAteRipeCorpse(akCorpse)" not in reward or "ApplyEatRipeCorpseBonus(akCorpse)" not in reward:
        fail("MaybeRewardEatenRipeCorpse must call both ToastAteRipeCorpse and ApplyEatRipeCorpseBonus on akCorpse")
    stage_if_block = reward[stage_check_idx : reward.find("EndIf", stage_check_idx)]
    if "Return" not in stage_if_block:
        fail("MaybeRewardEatenRipeCorpse's max-decay-stage check must Return (not just Trace) on mismatch")
    toast_idx = reward.find("ToastAteRipeCorpse(akCorpse)")
    bonus_idx = reward.find("ApplyEatRipeCorpseBonus(akCorpse)")
    if toast_idx < stage_check_idx or bonus_idx < stage_check_idx:
        fail("ToastAteRipeCorpse/ApplyEatRipeCorpseBonus must be called AFTER the max-decay-stage gate, not before")
    if "PendingEatRipeReward = False" not in reward:
        fail("MaybeRewardEatenRipeCorpse must clear PendingEatRipeReward on success / cannibal fail")
    for needle in (
        "eaten-ripe-corpse skip | no Cannibal perk",
        "eaten-ripe-corpse skip | no corpse",
        "eaten-ripe-corpse skip | corpse out of butcher range",
        "eaten-ripe-corpse skip | corpse untracked",
        "eaten-ripe-corpse skip | corpse not max stage",
    ):
        if needle not in reward:
            fail(f"MaybeRewardEatenRipeCorpse must Trace {needle!r} (no silent skip)")

    toast = extract_function(decay_txt, "ToastAteRipeCorpse")
    if "GetVictimOverrideName" not in toast:
        fail("ToastAteRipeCorpse must resolve the victim's override name")
    if '= "She"' not in toast:
        fail('ToastAteRipeCorpse must fall back to "She" (capitalized) when unnamed')
    if "ApplyNamePlaceholder" not in toast:
        fail("ToastAteRipeCorpse must ApplyNamePlaceholder for {name} substitution")
    if "Debug.Notification" not in toast:
        fail("ToastAteRipeCorpse must Debug.Notification the toast")
    for needle in (
        "eaten-ripe-corpse skip | no ateRipeCorpseToast",
        "eaten-ripe-corpse skip | empty line after placeholder",
    ):
        if needle not in toast:
            fail(f"ToastAteRipeCorpse must Trace {needle!r} (no silent skip)")

    bonus = extract_function(decay_txt, "ApplyEatRipeCorpseBonus")
    if "BuffTracker()" not in bonus or "ApplyEatRipeCorpseEndBuff()" not in bonus:
        fail("ApplyEatRipeCorpseBonus must delegate to BuffTracker().ApplyEatRipeCorpseEndBuff")

    modcfg = MODCFG.read_text(encoding="utf-8", errors="replace")
    load_cfg = extract_function(modcfg, "LoadModConfig")
    if 'key == "ateRipeCorpseToast"' not in load_cfg:
        fail("LoadModConfig must parse ateRipeCorpseToast")
    if "AteRipeCorpseToast = \"\"" not in load_cfg:
        fail("LoadModConfig must reset AteRipeCorpseToast at the top like the other ModConfig strings")

    ok("MainQuestScript P5 detection/reward wiring + Trace coverage")


def test_player_alias_wiring() -> None:
    if not ALIAS.is_file():
        fail(f"missing {ALIAS}")
    text = ALIAS.read_text(encoding="utf-8", errors="replace")

    reg = extract_function(text, "RegisterMagicEffectDetect")
    if "main.GetRestoreHealthGenericEffect()" not in reg:
        fail("RegisterMagicEffectDetect must resolve the effect via MainQuestScript.GetRestoreHealthGenericEffect")
    if "RegisterForMagicEffectApplyEvent(Self, None, effect, True)" not in reg:
        fail("RegisterMagicEffectDetect must RegisterForMagicEffectApplyEvent(Self, ...) filtered to the effect")
    if "Debug.Trace" not in reg:
        fail("RegisterMagicEffectDetect must Trace on success too (silent registration was undiagnosable last time)")

    for anchor_event in ("OnAliasInit", "OnPlayerLoadGame"):
        body = extract_event(text, f"Event {anchor_event}()")
        if "RegisterMagicEffectDetect()" not in body:
            fail(f"{anchor_event} must call RegisterMagicEffectDetect (new-game + save-load)")

    # The exact signature the compiler demands — confirmed via a real Caprica error
    # ("doesn't match the signature in the parent class 'ScriptObject'") when a
    # shortened 2-param community-snippet form was tried first.
    handler = extract_event(
        text,
        "Event OnMagicEffectApply(ObjectReference akTarget, ObjectReference akCaster, MagicEffect akEffect)",
    )
    if "main.HandlePlayerMagicEffectApply(akEffect)" not in handler:
        fail("PlayerAliasScript.OnMagicEffectApply must forward to MainQuestScript.HandlePlayerMagicEffectApply")
    if "Event OnMagicEffectApply(ObjectReference akCaster, MagicEffect akEffect)" in text:
        fail("PlayerAliasScript must not use the shortened 2-param OnMagicEffectApply override (Caprica rejects it)")

    sniff = extract_function(text, "SyncMagicEffectSniff")
    if "RegisterForMagicEffectApplyEvent(Self)" not in sniff:
        fail("SyncMagicEffectSniff must register an unfiltered catch-all on Self when turned on")
    if "UnregisterForAllMagicEffectApplyEvents(Self)" not in sniff:
        fail("SyncMagicEffectSniff must unregister on Self when turned off")
    if "RegisterMagicEffectDetect()" not in sniff.split("UnregisterForAllMagicEffectApplyEvents", 1)[1]:
        fail("SyncMagicEffectSniff must re-arm the real filtered registration after unregister-all wipes it")

    ok("PlayerAliasScript P5 detection registration + 3-param local event + sniffer wiring")


def test_debug_sniffer_mcm() -> None:
    cfg = MCM_CONFIG.read_text(encoding="utf-8", errors="replace")
    if '"id": "bSniffMagicEffects:Debug"' not in cfg:
        fail("config.json Debug page must have bSniffMagicEffects:Debug switcher")
    if '"sourceType": "ModSettingBool"' not in cfg[cfg.find('"id": "bSniffMagicEffects:Debug"') :][:600]:
        fail("bSniffMagicEffects:Debug must be a ModSettingBool switcher")
    for settings_path in (MCM_SETTINGS, SETTINGS_LEGACY):
        settings = settings_path.read_text(encoding="utf-8", errors="replace")
        if "[Debug]" not in settings or "bSniffMagicEffects=" not in settings.split("[Debug]", 1)[1]:
            fail(f"{settings_path.name} must default bSniffMagicEffects=0 under [Debug]")
    ok("MCM Debug page + settings.ini ship bSniffMagicEffects sniffer toggle")


def test_deploy_gate() -> None:
    text = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "test_decay_eaten_ripe_corpse.py" not in text:
        fail("build-deploy-local.ps1 must run test_decay_eaten_ripe_corpse.py")
    ok("deploy gate includes decay eaten-ripe-corpse contract")


def find_esm(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    load_dotenv()
    import os

    env = os.environ.get("FALLOUT4_ESM")
    if env and Path(env).is_file():
        return Path(env)
    return None


def get_record_edid_zlib(data: bytes, sig: bytes, fid: int) -> bytes | None:
    target = fid.to_bytes(4, "little")
    start = 0
    while True:
        i = data.find(sig, start)
        if i < 0 or i + 24 > len(data):
            return None
        if data[i + 12 : i + 16] != target:
            start = i + 4
            continue
        size = int.from_bytes(data[i + 4 : i + 8], "little")
        flags = int.from_bytes(data[i + 8 : i + 12], "little")
        payload = data[i + 24 : i + 24 + size]
        if flags & 0x00040000:
            try:
                payload = zlib.decompress(payload[4:])
            except Exception:
                return None
        k = payload.find(b"EDID")
        if k < 0 or k + 6 > len(payload):
            return None
        esz = int.from_bytes(payload[k + 4 : k + 6], "little")
        return payload[k + 6 : k + 6 + esz].split(b"\x00", 1)[0]


def test_esm(esm: Path | None) -> None:
    if not esm:
        print("SKIP ESM checks: Fallout4.esm not found (set FALLOUT4_ESM in .env, env, or --esm)")
        return
    data = esm.read_bytes()
    got = get_record_edid_zlib(data, b"MGEF", FID_MGEF_RESTORE_HEALTH_GENERIC)
    if got != EDID_RESTORE_HEALTH_GENERIC:
        fail(f"FID 0x{FID_MGEF_RESTORE_HEALTH_GENERIC:06X} EDID {got!r} != {EDID_RESTORE_HEALTH_GENERIC!r}")
    ok("RestoreHealthGeneric MGEF FormID verified against Fallout4.esm")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--esm", default=None, help="Path to Fallout4.esm")
    args = ap.parse_args()

    if not MAIN.is_file():
        fail("missing MainQuestScript PSC")
    test_modconfig()
    test_stub()
    test_main_wiring()
    test_player_alias_wiring()
    test_debug_sniffer_mcm()
    test_deploy_gate()
    test_esm(find_esm(args.esm))
    print("All decay eaten-ripe-corpse (Slice H P5) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
