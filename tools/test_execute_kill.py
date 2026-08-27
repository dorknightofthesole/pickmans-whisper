#!/usr/bin/env python3
"""Contract: Slice W — instant kill (Decapitate / Smash Head In) on a living victim.

Fully isolated new script (PickmansWhisperExecuteScript), a new hotkey (\\, VK_OEM_5=220,
distinct from the existing / corpse-sever key and ] dialog toggle), and a new MSG menu
(PW_ExecuteMenu). Zero changes to the existing corpse-sever feature (Slice F): different
hotkey, different menu, different Dismember call site, SeverCorpseLimb untouched.

Locks:
  - New script exists, extends Quest, attached to Main's VMAD script list
  - Requires Bond (Main.IsHungerUnlocked()), checked once in TryExecuteAimedVictim (the
    entry point) — without it, a never-bonded save could execute victims with a bare heavy
    blunt weapon and no Pickman's Blade at all (Smash Head In needs no blade; Decapitate
    only needs the blade equipped, not bonded — Bond needs blade + Lady Killer together)
  - Decapitate requires Main.IsBladeEquipped(); Smash Head In requires one of 5 verified
    Fallout4.esm heavy-blunt-melee WEAP forms (curated list, not a keyword check — FO4 has
    no shared "blunt" keyword across these, confirmed by direct ESM inspection)
  - Both paths hard-gate on Main.IsValidTarget(ak, False) — non-hostile only, same
    essential/protected-NPC-safe check every other feature in this mod relies on
  - Kill sequence: RegisterTarget (defensive) -> KillSilent(player) -> Dismember — no new
    kill-crediting code, reuses the existing OnDeath -> RewardKill -> ProcessKnifeKill pipeline
  - Hotkey lives on PlayerAliasScript (Quest key registration is unreliable — established
    convention), not on the new script or Main
  - ESP builder: new PW_ExecuteMenu MESG record, script attached to Main VMAD, NEXT_OID bumped
  - Existing corpse-sever feature (SeverCorpseLimb, PW_SeverLimbMenu, / key) completely untouched

Usage:
  python tools/test_execute_kill.py [--esm PATH]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTE_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperExecuteScript.psc"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
ALIAS_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"
PACKAGE = ROOT / "tools" / "package_mo2_zip.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

FID_HEAVY_BLUNT = {
    0x0008E736: b"BaseballBat",
    0x000E7AB9: b"Sledgehammer",
    0x000FF964: b"SuperSledge",
    0x000D83BF: b"PipeWrench",
    0x000FA3E8: b"PoolCue",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def extract_function(src: str, name: str) -> str:
    m = re.search(
        rf"(?:^\s*(?:Bool|Int|Float|String|Actor)?\s*)?Function\s+{re.escape(name)}\s*\(",
        src,
        re.M,
    )
    if not m:
        fail(f"missing function {name}")
    start = m.start()
    end_m = re.search(r"\nEndFunction\b", src[start:])
    if not end_m:
        fail(f"unclosed function {name}")
    return src[start : start + end_m.end()]


def strip_comment_lines(fn: str) -> str:
    return "\n".join(ln for ln in fn.splitlines() if not ln.strip().startswith(";"))


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
    if not esm or not esm.is_file():
        print("SKIP ESM checks: Fallout4.esm not found (set FALLOUT4_ESM in .env, env, or --esm)")
        return
    data = esm.read_bytes()
    for fid, edid in FID_HEAVY_BLUNT.items():
        got = get_record_edid_zlib(data, b"WEAP", fid)
        if got != edid:
            fail(f"FID 0x{fid:06X} EDID {got!r} != {edid!r}")
    ok("BaseballBat/Sledgehammer/SuperSledge/PipeWrench/PoolCue FormIDs verified against Fallout4.esm WEAP records")


def test_script_exists_and_isolated() -> None:
    if not EXECUTE_PSC.is_file():
        fail(f"missing {EXECUTE_PSC}")
    text = EXECUTE_PSC.read_text(encoding="utf-8", errors="replace")
    if "Scriptname PickmansWhisperExecuteScript extends Quest" not in text:
        fail("PickmansWhisperExecuteScript must extend Quest")
    ok("PickmansWhisperExecuteScript.psc exists, extends Quest")


def test_bond_gate(text: str) -> None:
    entry = extract_function(text, "TryExecuteAimedVictim")
    entry_code_only = strip_comment_lines(entry)
    if "IsHungerUnlocked()" not in entry_code_only:
        fail("TryExecuteAimedVictim must gate on Main.IsHungerUnlocked() (outside comments) — "
             "without it, Smash Head In needs no blade at all and could execute victims on a "
             "never-bonded save; Decapitate only needs the blade equipped, not bonded")
    # Bond check must come before the weapon-equipped check, so a not-yet-bonded player with
    # a bat already equipped gets an accurate "bond first" message, not a confusing
    # "draw a weapon" one.
    idx_bond = entry_code_only.find("IsHungerUnlocked()")
    idx_weapon = entry_code_only.find("IsHeavyBluntMeleeEquipped()")
    if idx_weapon < 0 or idx_bond < 0 or idx_bond > idx_weapon:
        fail("TryExecuteAimedVictim must check IsHungerUnlocked() before the blade-or-blunt-weapon check")
    ok("TryExecuteAimedVictim gates on Main.IsHungerUnlocked() (Bond) before the weapon check")


def test_weapon_formids(text: str) -> None:
    for fid in FID_HEAVY_BLUNT:
        needle = f"0x{fid:08X}"
        if needle not in text:
            fail(f"ExecuteScript must declare a FID const for {needle}")
    fn = extract_function(text, "IsHeavyBluntMeleeEquipped")
    if "GetEquippedWeapon()" not in fn:
        fail("IsHeavyBluntMeleeEquipped must check Actor.GetEquippedWeapon()")
    if fn.count("WeapBaseballBat") < 1 or fn.count("WeapSledgehammer") < 1 or fn.count("WeapSuperSledge") < 1 or fn.count("WeapPipeWrench") < 1 or fn.count("WeapPoolCue") < 1:
        fail("IsHeavyBluntMeleeEquipped must check the equipped weapon against all 5 curated heavy-blunt forms")
    ok("IsHeavyBluntMeleeEquipped checks GetEquippedWeapon() against all 5 curated, verified WEAP forms")


def test_eligibility_gate(text: str) -> None:
    elig = extract_function(text, "IsExecuteEligible")
    if "IsValidTarget(ak, False)" not in elig:
        fail("IsExecuteEligible must gate on Main.IsValidTarget(ak, False) — non-hostile only")
    if "ak.IsDead()" not in elig:
        fail("IsExecuteEligible must reject already-dead targets")

    decap = extract_function(text, "TryDecapitate")
    if "IsBladeEquipped()" not in decap:
        fail("TryDecapitate must require Main.IsBladeEquipped()")
    if "IsExecuteEligible(ak)" not in decap:
        fail("TryDecapitate must re-validate IsExecuteEligible before killing")

    smash = extract_function(text, "TrySmashHeadIn")
    if "IsHeavyBluntMeleeEquipped()" not in smash:
        fail("TrySmashHeadIn must require IsHeavyBluntMeleeEquipped()")
    if "IsExecuteEligible(ak)" not in smash:
        fail("TrySmashHeadIn must re-validate IsExecuteEligible before killing")
    ok("TryDecapitate requires blade; TrySmashHeadIn requires heavy blunt melee; both re-validate IsValidTarget(ak, False)")


def test_kill_sequence(text: str) -> None:
    kill = extract_function(text, "ExecuteKill")
    order = [kill.find(needle) for needle in ("RegisterTarget(ak)", "KillSilent(player)", 'Dismember("Head1"')]
    if any(i < 0 for i in order):
        fail("ExecuteKill must call RegisterTarget, KillSilent(player), and Dismember(\"Head1\", ...)")
    if not (order[0] < order[1] < order[2]):
        fail("ExecuteKill must call RegisterTarget, then KillSilent(player), then Dismember — in that order")
    if "KillSilent(player)" not in kill:
        fail("ExecuteKill must pass the player as killer to KillSilent (Protected actors can survive a killerless KillSilent — established gotcha elsewhere in this mod)")
    if "Dismember(\"Head1\", abSmash, True, abSmash)" not in kill:
        fail("ExecuteKill must call Dismember with abForceExplode=abSmash, abForceDismember=True, abForceBloodyMess=abSmash "
             "(abForceExplode=False regardless of abSmash was the original bug: Smash Head In looked identical to a clean "
             "Decapitate in-game because only abForceBloodyMess varied — abForceExplode is the flag that actually gibs)")
    if "ProcessKnifeKill" in kill or "SatiateHunger" in kill or "RewardKill" in kill:
        fail("ExecuteKill must NOT call reward-crediting functions directly — it relies entirely on the existing OnDeath pipeline via RegisterTarget")
    if "QueueStripBodyDecayAfterDismember" not in kill:
        fail("ExecuteKill should queue the same post-dismember decay-overlay strip corpse-sever already does, for visual consistency")
    ok("ExecuteKill: RegisterTarget -> KillSilent(player) -> Dismember(\"Head1\", abSmash, True, abSmash), no direct reward-crediting calls")


def test_no_impact_on_corpse_sever() -> None:
    main_text = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    sever = extract_function(main_text, "SeverCorpseLimb")
    if "abSmash" in sever or "ExecuteScript" in sever or "Execute()" in sever:
        fail("SeverCorpseLimb (existing Slice F corpse-sever) must be completely untouched by Slice W")
    trysever = extract_function(main_text, "TrySeverAimedCorpse")
    if "Execute" in trysever:
        fail("TrySeverAimedCorpse (existing / hotkey handler) must be completely untouched by Slice W")
    ok("Existing corpse-sever feature (SeverCorpseLimb, TrySeverAimedCorpse) untouched")


def test_main_facade(text: str) -> None:
    if "PickmansWhisperExecuteScript Function Execute()" not in text:
        fail("MainQuestScript must declare an Execute() cross-cast helper")
    facade = extract_function(text, "TryExecuteAimedVictim")
    if "Execute()" not in facade or "ex.TryExecuteAimedVictim()" not in facade:
        fail("MainQuestScript.TryExecuteAimedVictim must forward to Execute().TryExecuteAimedVictim()")
    if "Function IsNecroSceneActive(" not in text:
        fail("MainQuestScript must expose IsNecroSceneActive() (NecroSceneActive is a plain var, not cross-script accessible)")
    necro_getter = extract_function(text, "IsNecroSceneActive")
    if "Return NecroSceneActive" not in necro_getter:
        fail("IsNecroSceneActive must return the NecroSceneActive var")
    ok("MainQuestScript: Execute() cast, TryExecuteAimedVictim forwarder, IsNecroSceneActive getter")


def test_hotkey(text: str) -> None:
    if "Int KEY_EXECUTE = 220" not in text:
        fail("PlayerAliasScript must declare KEY_EXECUTE = 220 (VK_OEM_5, backslash)")
    for other_key, val in (("KEY_BUTCHER", "191"), ("KEY_DIALOG_ACTIVATE", "221")):
        if f"Int {other_key} = {val}" not in text:
            fail(f"{other_key} must remain unchanged at {val} — Slice W must not touch existing hotkeys")
    reg = extract_function(text, "RegisterExecuteKey")
    if "RegisterForKey(KEY_EXECUTE)" not in reg:
        fail("RegisterExecuteKey must RegisterForKey(KEY_EXECUTE)")
    if "RegisterExecuteKey()" not in text.split("Event OnKeyDown")[0]:
        fail("RegisterExecuteKey() must be called from OnAliasInit/OnPlayerLoadGame (before OnKeyDown in the file)")
    keydown = extract_function(text, "OnKeyDown") if "Function OnKeyDown" in text else None
    if keydown is None:
        m = re.search(r"Event OnKeyDown\(Int keyCode\)(.*?)EndEvent", text, re.S)
        if not m:
            fail("missing OnKeyDown event")
        keydown = m.group(0)
    if "keyCode == KEY_EXECUTE" not in keydown:
        fail("OnKeyDown must branch on KEY_EXECUTE")
    if "TryExecuteAimedVictim()" not in keydown:
        fail("OnKeyDown's KEY_EXECUTE branch must call main.TryExecuteAimedVictim()")
    ok("PlayerAliasScript: KEY_EXECUTE=220 registered + dispatched, existing KEY_BUTCHER/KEY_DIALOG_ACTIVATE untouched")


def test_esp_builder() -> None:
    text = BUILDER.read_text(encoding="utf-8", errors="replace")
    if '"PickmansWhisperExecuteScript"' not in text:
        fail("ESP builder must attach PickmansWhisperExecuteScript to the Main quest VMAD")
    if "FID_EXECUTE_MSG = 0x0100087B" not in text:
        fail("ESP builder must declare FID_EXECUTE_MSG = 0x0100087B")
    if "NEXT_OID = 0x00000880" not in text:
        fail("ESP builder NEXT_OID must be bumped past gore SM arm L MISC")
    if "def build_execute_menu_payload" not in text:
        fail("ESP builder must declare build_execute_menu_payload()")
    menu_fn_m = re.search(r"def build_execute_menu_payload.*?return b\"\"\.join\(parts\)", text, re.S)
    if not menu_fn_m:
        fail("could not extract build_execute_menu_payload body")
    menu_fn = menu_fn_m.group(0)
    for label in ("Sever Head", "Smash Head In", "Cancel"):
        if label not in menu_fn:
            fail(f"PW_ExecuteMenu must have a {label!r} button")
    if "msg_execute" not in text:
        fail("ESP builder must construct and emit the msg_execute MESG record")
    ok("ESP builder: PickmansWhisperExecuteScript attached, PW_ExecuteMenu (3 buttons) built and emitted, NEXT_OID bumped")


def test_deploy_wiring() -> None:
    ps1 = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    sh = DEPLOY_SH.read_text(encoding="utf-8", errors="replace")
    pkg = PACKAGE.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperExecuteScript.psc" not in ps1:
        fail("build-deploy-local.ps1 must compile PickmansWhisperExecuteScript.psc")
    if "test_execute_kill.py" not in ps1:
        fail("build-deploy-local.ps1 must run test_execute_kill.py")
    if "PickmansWhisperExecuteScript.psc" not in sh:
        fail("build-deploy-local.sh must compile PickmansWhisperExecuteScript.psc")
    if "test_execute_kill.py" not in sh:
        fail("build-deploy-local.sh must run test_execute_kill.py")
    if "PickmansWhisperExecuteScript" not in pkg:
        fail("package_mo2_zip.py must include PickmansWhisperExecuteScript")
    ok("deploy (.ps1 + .sh) and package gate include ExecuteScript + run this test")


def main() -> int:
    for path in (EXECUTE_PSC, MAIN_PSC, ALIAS_PSC, BUILDER, DEPLOY_PS1, DEPLOY_SH, PACKAGE):
        if not path.is_file():
            fail(f"missing {path}")
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--esm", default=None)
    args, _ = ap.parse_known_args()
    esm_path = args.esm or os.environ.get("FALLOUT4_ESM")
    test_esm(Path(esm_path) if esm_path else None)

    test_script_exists_and_isolated()
    execute_text = EXECUTE_PSC.read_text(encoding="utf-8", errors="replace")
    test_bond_gate(execute_text)
    test_weapon_formids(execute_text)
    test_eligibility_gate(execute_text)
    test_kill_sequence(execute_text)
    test_no_impact_on_corpse_sever()
    main_text = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    test_main_facade(main_text)
    alias_text = ALIAS_PSC.read_text(encoding="utf-8", errors="replace")
    test_hotkey(alias_text)
    test_esp_builder()
    test_deploy_wiring()
    print("All execute-kill (Slice W) contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
