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
    if "KnifeKillCreditSuppressed = False" not in un:
        fail(
            "UnRegisterTarget must clear KnifeKillCreditSuppressed "
            "(sticky True from Bed Gift KillSilent must not mute real kills forever)"
        )
    if "UnregisterForHitEvent(akTarget, akCaster)" in un:
        fail("UnRegisterTarget must not use akCaster hit filter (signature dropped akCaster)")

    if "RegisterForRemoteEvent(akTarget, \"OnDeath\")" not in reg:
        fail("RegisterTarget must RegisterForRemoteEvent OnDeath")

    onhit = fn_body(psc, "OnHit")
    if "RegisterForHitEvent" in onhit:
        fail("OnHit must not re-arm RegisterForHitEvent (sticky hit AV)")
    if "MaybeSpeakHitWhisper" not in onhit:
        fail("OnHit must VoiceAlias.MaybeSpeakHitWhisper (ModConfig hitWhisper)")
    if "Finish what you started" in onhit:
        fail("OnHit must not hard-code hit toast (ModConfig HitWhisper is source of truth)")

    voice_psc = (
        ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
    )
    if not voice_psc.is_file():
        fail("VoiceAliasScript missing")
    voice = voice_psc.read_text(encoding="utf-8", errors="replace")
    hit = fn_body(voice, "MaybeSpeakHitWhisper")
    if "ModConfigAlias.HitWhisper" not in hit:
        fail("MaybeSpeakHitWhisper must read ModConfigAlias.HitWhisper")
    if "ShowVoiceToast" not in hit:
        fail("MaybeSpeakHitWhisper must ShowVoiceToast (toast now; audio later)")

    reg = fn_body(psc, "RegisterTarget")
    if "MaybeSpeakNeedsBeatingWhisper" in reg:
        fail("RegisterTarget must not call MaybeSpeakNeedsBeatingWhisper (moved to BeatBeforeKill)")
    if "IsReadyToGiveBeating" in reg:
        fail("RegisterTarget must not gate IsReadyToGiveBeating for needs-beating (BeatBeforeKill owns it)")
    if "needs a good beating" in reg:
        fail("RegisterTarget must not hard-code beating toast (ModConfig NeedsBeatingWhisper)")
    beat_psc = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperBeatBeforeKillScript.psc"
    if not beat_psc.is_file():
        fail("BeatBeforeKillScript missing")
    handle_beat = fn_body(beat_psc.read_text(encoding="utf-8", errors="replace"), "HandleBeatBeforeKill")
    if "MaybeSpeakNeedsBeatingWhisper" not in handle_beat:
        fail("HandleBeatBeforeKill must VoiceAlias.MaybeSpeakNeedsBeatingWhisper when unarmed")
    if "IsReadyToGiveBeating" not in handle_beat:
        fail("HandleBeatBeforeKill must gate on IsReadyToGiveBeating before needs-beating whisper")
    beat = fn_body(voice, "MaybeSpeakNeedsBeatingWhisper")
    if "ModConfigAlias.NeedsBeatingWhisper" not in beat:
        fail("MaybeSpeakNeedsBeatingWhisper must read ModConfigAlias.NeedsBeatingWhisper")
    if "FormatLineWithActorName" not in beat:
        fail("MaybeSpeakNeedsBeatingWhisper must Main.FormatLineWithActorName for {name}")
    if "NoticeNameForLine" in beat:
        fail("MaybeSpeakNeedsBeatingWhisper must not NoticeNameForLine — use FormatLineWithActorName(..., False)")
    if "ShowVoiceToast" in beat:
        fail("MaybeSpeakNeedsBeatingWhisper must not ShowVoiceToast (blade gate; knife is away)")
    if "FormatVoiceToast" not in beat or "Debug.Notification" not in beat:
        fail("MaybeSpeakNeedsBeatingWhisper must Notification(FormatVoiceToast(...))")
    if "Function FormatLineWithActorName(" not in psc:
        fail("Main must expose FormatLineWithActorName (SSOT actor+template)")
    if "Function ApplyNamePlaceholder(String line, String npcName)" not in psc:
        fail("Main must own ApplyNamePlaceholder SSOT")

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
    if "IsValidTarget" in rew:
        fail("RewardKill must not re-check IsValidTarget (OnDeath settle; eligibility was at arm time)")
    if "StartBond" in rew:
        fail("RewardKill must not StartBond (equip path owns bond)")

    ok("Main RegisterTarget / OnHit / OnDeath / RewardKill")


def test_start_bond_equip_path() -> None:
    if not ALIAS_PSC.is_file():
        fail("PlayerAliasScript missing")
    alias = ALIAS_PSC.read_text(encoding="utf-8", errors="replace")
    if "Bool Property IsReadyToGiveBeating" not in alias:
        fail("PlayerAlias must expose IsReadyToGiveBeating Property")
    ready = fn_body(alias, "CheckAndHandleBladeReady")
    if 'StartBond("blade-equipped")' not in ready:
        fail('PlayerAlias CheckAndHandleBladeReady must StartBond("blade-equipped")')
    if "GetEquippedWeapon()" not in ready:
        fail("CheckAndHandleBladeReady must treat !GetEquippedWeapon as unarmed → IsReadyToGiveBeating")
    if "IsReadyToGiveBeating = True" not in ready:
        fail("CheckAndHandleBladeReady unarmed path must set IsReadyToGiveBeating = True")
    if "IsReadyToGiveBeating = False" not in ready:
        fail("CheckAndHandleBladeReady must clear IsReadyToGiveBeating when armed")

    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    rew = fn_body(psc, "RewardKill")
    if "StartBond" in rew:
        fail("RewardKill must not StartBond")
    bond = fn_body(psc, "StartBond")
    if "ModConfigAlias.BondIntroGreeting" in bond:
        fail("StartBond must NOT read ModConfigAlias.BondIntroGreeting — that line moved to "
             "AnnounceGalleryIntro (Gallery entry), decoupled from Bond/blade entirely")
    if "Debug.MessageBox" in bond:
        fail("StartBond must NOT call Debug.MessageBox directly — the once-ever intro dialog "
             "moved to AnnounceGalleryIntro, triggered on Gallery entry (SeenGallery), not on Bond start")
    if "ArmRuntimeLoops" in bond:
        fail("StartBond must not ArmRuntimeLoops (load/init arms scanners)")
    if "LastHungerPollGameTime" in bond or "LastKnifeActivityGameTime" in bond:
        fail("StartBond is bond latch only — no hunger/activity stamps")

    gallery_intro = fn_body(psc, "AnnounceGalleryIntro")
    gallery_intro_code_only = "\n".join(
        ln for ln in gallery_intro.splitlines() if not ln.strip().startswith(";")
    )
    if "ModConfigAlias.BondIntroGreeting" not in gallery_intro:
        fail("AnnounceGalleryIntro must read ModConfigAlias.BondIntroGreeting")
    if "Debug.MessageBox(line)" not in gallery_intro_code_only:
        fail("AnnounceGalleryIntro's once-ever Gallery welcome must use Debug.MessageBox (guaranteed-seen dialog, not a toast that can be missed)")
    if "ToastVoice(line)" in gallery_intro_code_only:
        fail("AnnounceGalleryIntro must not deliver the line via ToastVoice — that gates on IsVoiceWeaponReady/IsInMenuMode, either of which could permanently eat the only chance this once-ever line gets")
    if "IsVoiceEnabled" in gallery_intro_code_only:
        fail("AnnounceGalleryIntro's Debug.MessageBox(line) call must NOT be gated on IsVoiceEnabled (outside comments) — "
             "confirmed live this exact gate made the blade-acquire dialog fire with zero visible output; "
             "the Gallery intro must not repeat that mistake since SeenGallery has no later retry either")

    # Rule: Bond means the player first acquired the blade — must never start without it,
    # enforced once inside StartBond itself (not just trusted at every call site).
    m = re.search(r"If\s+BondStarted\s*\n\s*Return\s*\n\s*EndIf\s*\n(.*?)BondStarted\s*=\s*True", bond, re.S)
    if not m:
        fail("StartBond must check !PlayerHasBlade() after the BondStarted guard and before setting BondStarted = True")
    guard_gap = m.group(1)
    if "PlayerHasBlade()" not in guard_gap:
        fail("StartBond must guard on !PlayerHasBlade() before BondStarted = True — bond can never start before the blade is acquired")

    force = fn_body(psc, "DebugForceBond")
    if "PlayerHasBlade()" not in force:
        fail("DebugForceBond must check PlayerHasBlade() itself and report an accurate blocked message — "
             "otherwise it always claims 'Bond forced' even when StartBond silently refused")

    poll = fn_body(psc, "RunBondPoll")
    poll_code_only = "\n".join(
        ln for ln in poll.splitlines() if not ln.strip().startswith(";")
    )
    if "inGallery || hasBlade" in poll_code_only or "(inGallery ||" in poll_code_only:
        fail("RunBondPoll must not trigger StartBond on Gallery entry alone (outside comments) — "
             "bond now requires real blade ownership/equip (hasBlade || equipped); confirmed live "
             "that Gallery-alone triggering an old save's 'bond active' toast before the blade was "
             "ever owned read as a bug")
    if "hasBlade || equipped" not in poll_code_only:
        fail("RunBondPoll must trigger StartBond on (hasBlade || equipped)")
    if "AnnounceGalleryIntro()" not in poll_code_only:
        fail("RunBondPoll must call AnnounceGalleryIntro() inside its SeenGallery-latch branch")
    if "LastKnifeActivityGameTime" in psc:
        fail("LastKnifeActivityGameTime retired (was write-only)")
    if "Function NoteKnifeActivity" in psc:
        fail("NoteKnifeActivity retired with LastKnifeActivityGameTime")
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
