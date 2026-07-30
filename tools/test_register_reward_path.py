#!/usr/bin/env python3
"""RegisterTarget / OnHit / OnDeath / RewardKill / CheckIfKillRewarded + KillRewardScript.

Locks (Papyrus source contracts — mirrors current event-driven kill credit path):

KillRewardScript:
  - RegisterKillRewardCheck stamps PW_KillRewardCheckTime, AddRef, StartTimer(22)
  - OnTimer due entries call Main.RewardKill then RemoveRef
  - Re-arms while queue non-empty; clears IsCounterRunning when empty
  - Does not gate OnTimer with CheckIfKillRewarded (RewardKill owns that)

Main 519–718:
  - Live+blade+untracked → OnDeath + HitEvent + TrackedNPCs.AddRef
  - Dead+blade+hit AV+no credit → RegisterKillRewardCheck (no credit stamp)
  - CheckIfKillRewarded: TrackedNPCs.Find → GetAt → credit AV == 1.0
  - RewardKill: CheckIfKillRewarded, cleanup, hit+blade gates, ProcessKnifeKill, stamp credit
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
REWARD_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillRewardScript.psc"
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


def check_if_kill_rewarded_mirror(
    tracked: list[int], credit_by_id: dict[int, float], target_id: int
) -> bool:
    """Pure mirror of CheckIfKillRewarded: must be in TrackedNPCs, then credit AV."""
    if target_id not in tracked:
        return False
    return credit_by_id.get(target_id, 0.0) == 1.0


def test_check_if_kill_rewarded_mirror() -> None:
    tracked = [10, 20]
    credit = {10: 0.0, 20: 1.0, 30: 1.0}
    if check_if_kill_rewarded_mirror(tracked, credit, 20) is not True:
        fail("mirror: tracked + credit 1.0 → True")
    if check_if_kill_rewarded_mirror(tracked, credit, 10) is not False:
        fail("mirror: tracked + credit 0.0 → False")
    if check_if_kill_rewarded_mirror(tracked, credit, 30) is not False:
        fail("mirror: credit 1.0 but not in TrackedNPCs → False")
    if check_if_kill_rewarded_mirror(tracked, credit, 99) is not False:
        fail("mirror: unknown id → False")
    ok("CheckIfKillRewarded pure mirror (TrackedNPCs then credit AV)")


def test_kill_reward_script() -> None:
    if not REWARD_PSC.is_file():
        fail("PickmansWhisperKillRewardScript.psc missing")
    reward = REWARD_PSC.read_text(encoding="utf-8", errors="replace")

    if "extends ReferenceAlias" not in reward:
        fail("KillRewardScript must extend ReferenceAlias")
    if "RefCollectionAlias Property PendingRewardTargets Auto Const" not in reward:
        fail("KillRewardScript must declare PendingRewardTargets")
    if "ActorValue Property PW_KillRewardCheckTime Auto Const" not in reward:
        fail("KillRewardScript must declare PW_KillRewardCheckTime")
    if "TIMER_KILL_REWARD_CHECK = 22" not in reward:
        fail("KillRewardScript must use timer id 22")
    if "KILL_REWARD_CHECK_SECONDS = 5.0" not in reward:
        fail("KillRewardScript must poll every 5.0s")

    reg = fn_body(reward, "RegisterKillRewardCheck")
    if "SetValue(PW_KillRewardCheckTime" not in reg:
        fail("RegisterKillRewardCheck must stamp PW_KillRewardCheckTime due time")
    if "GetCurrentRealTime()" not in reg or "secondsTillCheck" not in reg:
        fail("RegisterKillRewardCheck due time must be now + secondsTillCheck")
    if "PendingRewardTargets.Find(akTarget) < 0" not in reg:
        fail("RegisterKillRewardCheck must AddRef only when not already queued")
    if "PendingRewardTargets.AddRef(akTarget)" not in reg:
        fail("RegisterKillRewardCheck must PendingRewardTargets.AddRef")
    if "If !IsCounterRunning" not in reg:
        fail("RegisterKillRewardCheck must StartTimer only when counter idle")
    if "StartTimer(KILL_REWARD_CHECK_SECONDS, TIMER_KILL_REWARD_CHECK)" not in reg:
        fail("RegisterKillRewardCheck must StartTimer(5.0, 22)")

    ont = fn_body(reward, "OnTimer")
    if "aiTimerID != TIMER_KILL_REWARD_CHECK" not in ont:
        fail("OnTimer must ignore non-kill-reward timer ids")
    if "main.RewardKill(targetActor)" not in ont:
        fail("OnTimer due entry must call Main.RewardKill")
    if "PendingRewardTargets.RemoveRef(kRef)" not in ont:
        fail("OnTimer must RemoveRef after settle attempt")
    if "CheckIfKillRewarded" in ont:
        fail("OnTimer must not call CheckIfKillRewarded (RewardKill owns that)")
    if "|| PlayerAlias.IsPickmansBladeEquipped" in ont:
        fail("OnTimer must not OR blade-equipped into RewardKill")
    if "PendingRewardTargets.GetCount() > 0" not in ont:
        fail("OnTimer must re-arm while queue non-empty")
    if "IsCounterRunning = False" not in ont:
        fail("OnTimer must clear IsCounterRunning when queue empty")

    init = fn_body(reward, "OnAliasInit")
    if "ClearCollection(PendingRewardTargets)" not in init:
        fail("OnAliasInit must ClearCollection(PendingRewardTargets)")
    if "IsCounterRunning = False" not in init:
        fail("OnAliasInit must reset IsCounterRunning")

    ok("KillRewardScript: register queue + OnTimer -> RewardKill + re-arm")


def test_main_register_reward_path() -> None:
    if not MAIN_PSC.is_file():
        fail("MainQuestScript missing")
    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")

    reg = fn_body(psc, "RegisterTarget")
    if "RegisterForRemoteEvent(akTarget, \"OnDeath\")" not in reg:
        fail("RegisterTarget live path must RegisterForRemoteEvent OnDeath")
    if "RegisterForHitEvent(akTarget, akCaster)" not in reg:
        fail("RegisterTarget live path must RegisterForHitEvent")
    if "TrackedNPCs.AddRef(akTarget)" not in reg:
        fail("RegisterTarget live path must TrackedNPCs.AddRef")
    if "RegisterKillRewardCheck(akTarget, 20)" not in reg:
        fail("RegisterTarget dead path must RegisterKillRewardCheck(..., 20)")
    if "SetValue(PW_Credit_For_PickmansBlade_Kill, 1.0)" in reg:
        fail("RegisterTarget must not stamp credit AV (skips ProcessKnifeKill)")
    if "PW_HitWihPickmansBlade" not in reg or "PW_Credit_For_PickmansBlade_Kill" not in reg:
        fail("RegisterTarget dead path must gate on hit AV + credit AV")

    un = fn_body(psc, "UnRegisterTarget")
    if "UnregisterForRemoteEvent(akTarget, \"OnDeath\")" not in un:
        fail("UnRegisterTarget must UnregisterForRemoteEvent OnDeath")
    if "UnregisterForHitEvent(akTarget, akCaster)" not in un:
        fail("UnRegisterTarget must UnregisterForHitEvent")
    if "TrackedNPCs.RemoveRef(akTarget)" not in un:
        fail("UnRegisterTarget must TrackedNPCs.RemoveRef")

    onhit = fn_body(psc, "OnHit")
    if "SetValue(PW_HitWihPickmansBlade, 1.0)" not in onhit:
        fail("OnHit must stamp PW_HitWihPickmansBlade when blade equipped")
    if "RegisterForHitEvent" in onhit:
        fail("OnHit must not re-arm RegisterForHitEvent (sticky hit AV)")

    ondeath = fn_body(psc, "OnDeath")
    if "RewardKill(akSender)" not in ondeath:
        fail("OnDeath must call RewardKill")

    chk = fn_body(psc, "CheckIfKillRewarded")
    if "TrackedNPCs.Find(akTarget)" not in chk:
        fail("CheckIfKillRewarded must Find on TrackedNPCs")
    if "TrackedNPCs.GetAt(targetRefIdx)" not in chk:
        fail("CheckIfKillRewarded must GetAt tracked instance before reading AV")
    if "GetValue(PW_Credit_For_PickmansBlade_Kill) == 1.0" not in chk:
        fail("CheckIfKillRewarded must read credit AV == 1.0 on tracked instance")

    rew = fn_body(psc, "RewardKill")
    if "CheckIfKillRewarded(akSender)" not in rew:
        fail("RewardKill must call CheckIfKillRewarded")
    if "UnregisterForRemoteEvent(akSender, \"OnDeath\")" not in rew:
        fail("RewardKill must UnregisterForRemoteEvent OnDeath")
    if "UnregisterForAllHitEvents(akSender)" not in rew:
        fail("RewardKill must UnregisterForAllHitEvents")
    if "TrackedNPCs.RemoveRef(akSender)" not in rew:
        fail("RewardKill must TrackedNPCs.RemoveRef")
    if "PW_HitWihPickmansBlade" not in rew:
        fail("RewardKill must gate on hit AV")
    if "IsPickmansBladeEquipped" not in rew:
        fail("RewardKill must gate on blade equipped")
    if "ProcessKnifeKill(akSender)" not in rew:
        fail("RewardKill must ProcessKnifeKill when eligible")
    if "SetValue(PW_Credit_For_PickmansBlade_Kill, 1.0)" not in rew:
        fail("RewardKill must stamp credit after ProcessKnifeKill")
    if "StartBond" in rew:
        fail("RewardKill must not StartBond (equip path owns bond)")

    ok("Main RegisterTarget / OnHit / OnDeath / CheckIfKillRewarded / RewardKill")


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
    test_check_if_kill_rewarded_mirror()
    test_kill_reward_script()
    test_main_register_reward_path()
    test_start_bond_equip_path()
    test_deploy_gate()
    print("All register/reward path contracts passed.")


if __name__ == "__main__":
    main()
