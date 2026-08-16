#!/usr/bin/env python3
"""Contracts for Slice R1 — first blade acquire voice line.

Once-per-save moment: the first time Pickman's Blade enters the player's inventory,
deliver a dedicated Message dialog/audio via ModConfig bladeAcquireToast/bladeAcquireAudio.
Debug.MessageBox (not Debug.Notification) so it's guaranteed seen, same reasoning as
StartBond/AnnounceGalleryIntro's bond-intro dialog. Deliberately NOT gated on
IsVoiceWeaponReady or IsVoiceEnabled like every other voice line in this mod — confirmed
live (Papyrus.0.log) that gating on IsVoiceEnabled made the (then-toast) delivery fire
with zero visible output and no trace, since SeenBlade is already latched True by the
time this runs (no later retry possible). Only iVoiceDelivery mode still applies. Hooked
off Main's existing Actor.OnItemAdded -> MarkOwnedBlade,
guarded by the existing SeenBlade latch so re-acquires/re-equips (R2) never replay it.
RunBondPoll's own independent SeenBlade set-site (a fallback detection net) is routed
through MarkOwnedBlade too, so the line fires from whichever path notices first, not
just OnItemAdded.

Locks:
  - ModConfig.txt ships bladeAcquireToast (default non-empty); bladeAcquireAudio ships
    commented out (no .xwm shipped yet, same convention as namedKillAudio)
  - ModConfigScript: BladeAcquireToast/BladeAcquireAudio properties, parse, commit,
    status-string entry
  - MainQuestScript: AnnounceBladeAcquire (no IsVoiceEnabled/IsVoiceWeaponReady gate;
    GetVoiceDeliveryMode + PlayWhisperXwmByFile), called from MarkOwnedBlade's
    !SeenBlade branch (single source of truth for the once-ever event)
  - RunBondPoll no longer raw-sets SeenBlade — routes through MarkOwnedBlade
  - ESP builder: bladeAcquireAudio in MOD_CONFIG_AUDIO_KEYS so an eventual .xwm gets a
    SNDR + WhisperSndrIds stem, same mechanism as namedKillAudio

Usage:
  python tools/test_blade_acquire.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MODCFG_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
MODCFG_TXT = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(text: str, name: str) -> str:
    m = re.search(
        rf"(?:^\s*(?:Bool|Int|Float|String|Actor)?\s*)?Function\s+{re.escape(name)}\s*\(",
        text,
        re.M,
    )
    if not m:
        fail(f"missing Function {name}")
    start = m.start()
    end = text.find("\nEndFunction", start)
    if end < 0:
        fail(f"unclosed Function {name}")
    return text[start : end + len("\nEndFunction")]


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


def test_modconfig_txt() -> None:
    keys = parse_modconfig_active_keys(MODCFG_TXT)
    if "bladeAcquireToast" not in keys or not keys["bladeAcquireToast"]:
        fail("ModConfig.txt must ship a non-empty bladeAcquireToast")
    if "{name}" in keys["bladeAcquireToast"]:
        fail("bladeAcquireToast must NOT use {name} — this is a player-acquire moment, not an NPC line")
    if "bladeAcquireAudio" in keys:
        fail("bladeAcquireAudio must stay commented until a real .xwm ships (matches namedKillAudio convention)")
    text = MODCFG_TXT.read_text(encoding="utf-8", errors="replace")
    if "bladeAcquireAudio" not in text:
        fail("ModConfig.txt should document bladeAcquireAudio even while commented out")
    ok("ModConfig.txt ships bladeAcquireToast; bladeAcquireAudio commented (no xwm yet)")


def test_modconfig_script() -> None:
    psc = MODCFG_PSC.read_text(encoding="utf-8", errors="replace")
    if "BladeAcquireToast" not in psc or "BladeAcquireAudio" not in psc:
        fail("ModConfigScript must declare BladeAcquireToast/BladeAcquireAudio properties")
    if 'key == "bladeAcquireToast"' not in psc or 'key == "bladeAcquireAudio"' not in psc:
        fail("ModConfigScript must parse both bladeAcquire keys")
    if "BladeAcquireToast = nextBladeAcquireToast" not in psc:
        fail("ModConfigScript must commit nextBladeAcquireToast -> BladeAcquireToast")
    if "BladeAcquireAudio = nextBladeAcquireAudio" not in psc:
        fail("ModConfigScript must commit nextBladeAcquireAudio -> BladeAcquireAudio")
    if 'status += "bladeAcquire "' not in psc:
        fail("ModConfigScript LoadModConfig status string must report bladeAcquire when BladeAcquireToast is set")
    ok("ModConfigScript: BladeAcquireToast/Audio SSOT, parse, commit, status")


def strip_comment_lines(fn: str) -> str:
    return "\n".join(
        ln for ln in fn.splitlines() if not ln.strip().startswith(";")
    )


def test_announce_function(text: str) -> None:
    fn = extract_function(text, "AnnounceBladeAcquire")
    code_only = strip_comment_lines(fn)
    if "ModConfigAlias.BladeAcquireToast" not in fn:
        fail("AnnounceBladeAcquire must require ModConfigAlias.BladeAcquireToast")
    if "IsVoiceEnabled" in code_only:
        fail("AnnounceBladeAcquire must NOT gate on IsVoiceEnabled (outside comments) — confirmed "
             "live this made the toast fire with zero visible output and no trace, and SeenBlade is "
             "already latched True by the time this runs so a swallowed toast here would never get a retry")
    if "IsVoiceWeaponReady" in code_only:
        fail("AnnounceBladeAcquire must NOT gate on IsVoiceWeaponReady (outside comments) — this "
             "is the acquire moment itself (may happen while sheathed), and SeenBlade is already "
             "latched True by the time this runs so a swallowed toast here would never get a retry")
    if "GetVoiceDeliveryMode" not in fn:
        fail("AnnounceBladeAcquire must honor VoiceAlias.GetVoiceDeliveryMode()")
    if code_only.count("Debug.MessageBox(line)") < 3:
        fail("AnnounceBladeAcquire must deliver via Debug.MessageBox(line) on all 3 paths (VoiceAlias-"
             "unbound fallback, normal delivery, audio-missing fallback) — guaranteed-seen dialog, "
             "not a toast that can be missed) — NOT VoiceAlias.ShowVoiceToast, which internally "
             "hard-gates on IsVoiceWeaponReady, and not Debug.Notification, which can be missed "
             "entirely with no later retry")
    if "Debug.Notification(" in code_only:
        fail("AnnounceBladeAcquire must not use Debug.Notification anywhere — every delivery path "
             "(VoiceAlias-unbound fallback, normal delivery, audio-missing fallback) must use "
             "Debug.MessageBox for this once-ever, no-retry event")
    if "PlayWhisperXwmByFile" not in fn:
        fail("AnnounceBladeAcquire must deliver audio via VoiceAlias.PlayWhisperXwmByFile when BladeAcquireAudio is set")
    if "BladeAcquireAudio" not in fn:
        fail("AnnounceBladeAcquire must reference ModConfigAlias.BladeAcquireAudio")
    ok("AnnounceBladeAcquire: ModConfig SSOT, no IsVoiceEnabled/IsVoiceWeaponReady gate, MessageBox+audio delivery")


def test_mark_owned_blade_calls_announce(text: str) -> None:
    fn = extract_function(text, "MarkOwnedBlade")
    if "SeenBlade" not in fn:
        fail("MarkOwnedBlade must still guard on SeenBlade")
    # AnnounceBladeAcquire must be called inside the !SeenBlade branch, not unconditionally
    # (unconditional would replay the line on every later re-add/re-equip — R2's job to prevent).
    m = re.search(r"If\s+!SeenBlade(.*?)EndIf", fn, re.S)
    if not m:
        fail("MarkOwnedBlade must have an If !SeenBlade ... EndIf branch")
    guarded_body = m.group(1)
    if "AnnounceBladeAcquire()" not in guarded_body:
        fail("MarkOwnedBlade must call AnnounceBladeAcquire() inside the !SeenBlade branch (once-ever, not on every call)")
    ok("MarkOwnedBlade calls AnnounceBladeAcquire() only inside the once-ever !SeenBlade branch")


def test_run_bond_poll_routes_through_mark_owned_blade(text: str) -> None:
    fn = extract_function(text, "RunBondPoll")
    if "SeenBlade = True" in fn:
        fail("RunBondPoll must NOT raw-set SeenBlade directly — that bypasses AnnounceBladeAcquire "
             "if this poll notices the blade before OnItemAdded does. Route through MarkOwnedBlade instead.")
    if 'MarkOwnedBlade("poll-detect")' not in fn and "MarkOwnedBlade(" not in fn:
        fail("RunBondPoll must call MarkOwnedBlade(...) when hasBlade && !SeenBlade")
    ok("RunBondPoll routes its hasBlade&&!SeenBlade fallback net through MarkOwnedBlade")


def test_builder_audio_key() -> None:
    text = BUILDER.read_text(encoding="utf-8", errors="replace")
    if "bladeAcquireAudio" not in text:
        fail("build_hunger_spell_esp.py must know about bladeAcquireAudio")
    m = re.search(r"MOD_CONFIG_AUDIO_KEYS\s*=\s*\(([^)]*)\)", text)
    if not m:
        fail("build_hunger_spell_esp.py missing MOD_CONFIG_AUDIO_KEYS tuple")
    if "bladeAcquireAudio" not in m.group(1):
        fail("MOD_CONFIG_AUDIO_KEYS must include bladeAcquireAudio so an eventual .xwm gets a SNDR clone")
    if "namedKillAudio" not in m.group(1):
        fail("MOD_CONFIG_AUDIO_KEYS must still include namedKillAudio")
    ok("ESP builder MOD_CONFIG_AUDIO_KEYS includes bladeAcquireAudio alongside namedKillAudio")


def test_deploy_wiring() -> None:
    ps1 = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    sh = DEPLOY_SH.read_text(encoding="utf-8", errors="replace")
    if "test_blade_acquire.py" not in ps1:
        fail("build-deploy-local.ps1 must run test_blade_acquire.py")
    if "test_blade_acquire.py" not in sh:
        fail("build-deploy-local.sh must run test_blade_acquire.py")
    ok("deploy (.ps1 + .sh) run this test")


def main() -> int:
    for path in (MAIN, MODCFG_PSC, MODCFG_TXT, BUILDER, DEPLOY_PS1, DEPLOY_SH):
        if not path.is_file():
            fail(f"missing {path}")
    text = MAIN.read_text(encoding="utf-8", errors="replace")
    test_modconfig_txt()
    test_modconfig_script()
    test_announce_function(text)
    test_mark_owned_blade_calls_announce(text)
    test_run_bond_poll_routes_through_mark_owned_blade(text)
    test_builder_audio_key()
    test_deploy_wiring()
    print("All blade acquire (Slice R1) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
