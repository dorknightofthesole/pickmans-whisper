#!/usr/bin/env python3
"""RegisterTarget / OnHit / OnDeath / RewardKill (KillRewardScript retired).

Locks (Papyrus source contracts — mirrors current event-driven kill credit path):

Main register/reward path:
  - RegisterTarget(akTarget) / UnRegisterTarget(akTarget) — no akCaster; hit filter is PlayerRef
  - Live+blade+untracked → OnDeath + HitEvent(PlayerRef)
  - RewardKill: cleanup, hit+blade gates, ProcessKnifeKill
  - RewardKill must NOT StartBond (bond is equip-driven)
  - OnHit stamps hit AV only (no hit re-arm — sticky flag)
  - PlayerAlias StartBond(\"blade-equipped\")

Usage:
  python tools/test_register_reward_path.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
ALIAS_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def fn_body(src: str, name: str) -> str:
    m = re.search(
        rf"(?im)^(?:(?:Bool |Float |Int |String )?Function|function|Event)"
        rf" (?:Actor\.)?{re.escape(name)}\b",
        src,
    )
    if not m:
        fail(f"missing {name}")
    start = m.start()
    end_fn = src.find("\nEndFunction", start)
    end_ev = src.find("\nEndEvent", start)
    ends = [e for e in (end_fn, end_ev) if e >= 0]
    if not ends:
        fail(f"unclosed {name}")
    return src[start : min(ends)]


def test_main_register_reward_path() -> None:
    if not MAIN_PSC.is_file():
        fail("MainQuestScript missing")
    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")

    reg = fn_body(psc, "RegisterTarget")
    if not re.search(r"(?im)^Function RegisterTarget\(Actor akTarget\)", psc):
        fail("RegisterTarget must be RegisterTarget(Actor akTarget) — no akCaster")
    if "RegisterForRemoteEvent(akTarget, \"OnDeath\")" not in reg:
        fail("RegisterTarget live path must RegisterForRemoteEvent OnDeath")
    if "RegisterForHitEvent(akTarget, PlayerRef)" not in reg:
        fail("RegisterTarget live path must RegisterForHitEvent(akTarget, PlayerRef)")
    if "RegisterForHitEvent(akTarget, akCaster)" in reg:
        fail("RegisterTarget must not use akCaster hit filter (signature dropped akCaster)")
    if "RegisterKillRewardCheck" in reg and not all(
        line.strip().startswith(";")
        for line in reg.splitlines()
        if "RegisterKillRewardCheck" in line
    ):
        fail("RegisterTarget must not call RegisterKillRewardCheck (KillReward retired)")
    if "SetValue(PW_Credit_For_PickmansBlade_Kill, 1.0)" in reg:
        fail("RegisterTarget must not stamp credit AV (skips ProcessKnifeKill)")
    # Inverted If VoiceAlias used to Trace "not initialized" on the success path.
    m_voice = re.search(
        r"(?is)If\s+VoiceAlias\s*\n\s*VoiceAlias\.HandleWhisperVoice\(akTarget\)\s*\n"
        r"\s*Else\s*\n.*?VoiceAlias unbound",
        reg,
    )
    if not m_voice:
        fail(
            "RegisterTarget live path must HandleWhisperVoice when VoiceAlias is set; "
            "error Trace only in Else (must not fire on success)"
        )

    un = fn_body(psc, "UnRegisterTarget")
    if not re.search(r"(?im)^function UnRegisterTarget\(Actor akTarget\)", psc):
        fail("UnRegisterTarget must be UnRegisterTarget(Actor akTarget) — no akCaster")
    if "UnregisterForRemoteEvent(akTarget, \"OnDeath\")" not in un:
        fail("UnRegisterTarget must UnregisterForRemoteEvent OnDeath")
    if "UnregisterForHitEvent(akTarget, PlayerRef)" not in un:
        fail("UnRegisterTarget must UnregisterForHitEvent(akTarget, PlayerRef)")
    if "UnregisterForHitEvent(akTarget, akCaster)" in un:
        fail("UnRegisterTarget must not use akCaster hit filter (signature dropped akCaster)")

    if "RegisterForRemoteEvent(akTarget, \"OnDeath\")" not in reg:
        fail("RegisterTarget must RegisterForRemoteEvent OnDeath")

    onhit = fn_body(psc, "OnHit")
    if "RegisterForHitEvent" in onhit:
        fail("OnHit must not re-arm RegisterForHitEvent (sticky hit AV)")

    ondeath = fn_body(psc, "OnDeath")
    if "RewardKill(akSender)" not in ondeath:
        fail("OnDeath must call RewardKill")

    rew = fn_body(psc, "RewardKill")
    if "UnregisterForRemoteEvent(akSender, \"OnDeath\")" not in rew:
        fail("RewardKill must UnregisterForRemoteEvent OnDeath")
    if "UnregisterForAllHitEvents(akSender)" not in rew:
        fail("RewardKill must UnregisterForAllHitEvents")
    if "IsPickmansBladeEquipped" not in rew:
        fail("RewardKill must gate on blade equipped")
    if "ProcessKnifeKill(akSender)" not in rew:
        fail("RewardKill must ProcessKnifeKill when eligible")
    if "StartBond" in rew:
        fail("RewardKill must not StartBond (equip path owns bond)")

    ok("Main RegisterTarget / OnHit / OnDeath / RewardKill")


def test_start_bond_equip_path() -> None:
    if not ALIAS_PSC.is_file():
        fail("PlayerAliasScript missing")
    alias = ALIAS_PSC.read_text(encoding="utf-8", errors="replace")
    ready = fn_body(alias, "CheckAndHandleBladeReady")
    if 'StartBond("blade-equipped")' not in ready:
        fail('PlayerAlias CheckAndHandleBladeReady must StartBond("blade-equipped")')

    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    rew = fn_body(psc, "RewardKill")
    if "StartBond" in rew:
        fail("RewardKill must not StartBond")
    bond = fn_body(psc, "StartBond")
    if "ModConfigAlias.BondIntroGreeting" not in bond:
        fail("StartBond must still read ModConfigAlias.BondIntroGreeting")
    ok('StartBond: equip path blade-equipped; not from RewardKill')


def test_deploy_gate() -> None:
    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "test_register_reward_path.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_register_reward_path.py")
    ok("deploy gate runs test_register_reward_path.py")


def main() -> None:
    test_main_register_reward_path()
    test_start_bond_equip_path()
    test_deploy_gate()
    print("All register/reward path contracts passed.")


if __name__ == "__main__":
    main()
