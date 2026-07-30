#!/usr/bin/env python3
"""KillRewardAlias on PickmansWhisperMain — timer host + queue + due-time AVIF.

Locks:
  - Main ALST 2 KillRewardAlias UniqueActor=Player
  - Main ALST 4 PendingRewardTargets RefCollection (+ seed 3 / ALCS)
  - ANAM 6 (past ModConfigAlias ALST 5)
  - VMAD attaches PickmansWhisperKillRewardScript with:
      PendingRewardTargets → ALST 4
      PW_KillRewardCheckTime → AVIF 0x876
      PlayerAlias → PlayerCombat ALST 0
  - Main.KillRewardAlias Auto Const bound to Main ALST 2
  - TIMER_KILL_REWARD_CHECK = 22; RegisterKillRewardCheck StartTimer
  - Deploy compiles + ships KillRewardScript

Usage:
  python tools/test_kill_reward_alias.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
REWARD_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperKillRewardScript.psc"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"

FID_QUEST = 0x01000800
FID_PLAYER_QUEST = 0x01000805
FID_AV_KILL_REWARD_CHECK_TIME = 0x01000876
ALIAS_KILL_REWARD_ID = 2
ALIAS_PENDING_REWARD_SEED_ID = 3
ALIAS_PENDING_REWARD_ID = 4
ALIAS_MOD_CONFIG_ID = 5
ANAM_NEXT = ALIAS_MOD_CONFIG_ID + 1


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def parse_fields(body: bytes) -> list[tuple[bytes, bytes]]:
    out: list[tuple[bytes, bytes]] = []
    j = 0
    while j + 6 <= len(body):
        t = body[j : j + 4]
        sz = struct.unpack_from("<H", body, j + 4)[0]
        out.append((t, body[j + 6 : j + 6 + sz]))
        j += 6 + sz
    return out


def find_records(data: bytes, rtype: bytes) -> list[tuple[int, bytes]]:
    i = 0
    while i + 24 <= len(data):
        if data[i : i + 4] == b"TES4":
            i += 24 + struct.unpack_from("<I", data, i + 4)[0]
            break
        i += 1
    out: list[tuple[int, bytes]] = []
    while i + 24 <= len(data):
        tag = data[i : i + 4]
        if tag == b"GRUP":
            gsize = struct.unpack_from("<I", data, i + 4)[0]
            end = i + gsize
            j = i + 24
            while j + 24 <= end:
                if data[j : j + 4] == b"GRUP":
                    j += struct.unpack_from("<I", data, j + 4)[0]
                    continue
                rt = data[j : j + 4]
                size = struct.unpack_from("<I", data, j + 4)[0]
                fid = struct.unpack_from("<I", data, j + 12)[0]
                if rt == rtype:
                    out.append((fid, data[j + 24 : j + 24 + size]))
                j += 24 + size
            i = end
            continue
        i += 24 + struct.unpack_from("<I", data, i + 4)[0]
    return out


def find_qust(data: bytes, fid: int) -> bytes | None:
    for rfid, body in find_records(data, b"QUST"):
        if rfid == fid:
            return body
    return None


def zfield(blob: bytes) -> str:
    return blob.split(b"\x00", 1)[0].decode("latin1", "replace")


def parse_vmad_object_prop(vmad: bytes, name: str) -> tuple[int, int, int, int, int]:
    idx = vmad.find(name.encode("ascii"))
    if idx < 2:
        fail(f"VMAD missing property {name}")
    nlen = struct.unpack_from("<H", vmad, idx - 2)[0]
    if nlen != len(name):
        fail(f"{name} wstring length mismatch")
    off = idx + nlen
    ptype, pstat = vmad[off], vmad[off + 1]
    zero, alias_id, form_fid = struct.unpack_from("<hhI", vmad, off + 2)
    return ptype, pstat, zero, alias_id, form_fid


def main() -> None:
    builder = BUILDER.read_text(encoding="utf-8", errors="replace")
    for needle, label in [
        ("ALIAS_KILL_REWARD_ID = 2", "KillReward ALST"),
        ("ALIAS_PENDING_REWARD_SEED_ID = 3", "PendingReward seed"),
        ("ALIAS_PENDING_REWARD_ID = 4", "PendingReward collection"),
        ("FID_AV_KILL_REWARD_CHECK_TIME = 0x01000876", "check-time AVIF"),
        ("NEXT_OID = 0x00000877", "NEXT_OID"),
        ('zstr("KillRewardAlias")', "KillReward ALID"),
        ('zstr("PendingRewardTargets")', "PendingReward ALID"),
        ('zstr("PendingRewardTargetsSeed")', "PendingReward seed ALID"),
        ('"KillRewardAlias", ALIAS_KILL_REWARD_ID', "Main KillRewardAlias bind"),
        ('"PendingRewardTargets", ALIAS_PENDING_REWARD_ID', "KillReward queue bind"),
        ('"PW_KillRewardCheckTime", FID_AV_KILL_REWARD_CHECK_TIME', "check-time bind"),
        ('"PlayerAlias", 0, FID_PLAYER_QUEST', "KillReward PlayerAlias bind"),
        ("build_pending_reward_targets_alias_fields", "pending alias helper"),
    ]:
        if needle not in builder:
            fail(f"builder must declare {label}: {needle}")
    # KillReward alias script must bind PlayerAlias (not only MainQuestScript).
    if builder.count('"PlayerAlias", 0, FID_PLAYER_QUEST') < 2:
        fail("builder must VMAD-bind PlayerAlias on both Main and KillRewardScript")
    ok("builder declares KillReward alias + PendingRewardTargets + check-time AVIF + PlayerAlias")

    if not REWARD_PSC.is_file():
        fail("PickmansWhisperKillRewardScript.psc missing")
    reward = REWARD_PSC.read_text(encoding="utf-8", errors="replace")
    if "extends ReferenceAlias" not in reward:
        fail("KillRewardScript must extend ReferenceAlias")
    if "RefCollectionAlias Property PendingRewardTargets Auto Const" not in reward:
        fail("KillRewardScript must declare PendingRewardTargets Auto Const")
    if "ActorValue Property PW_KillRewardCheckTime Auto Const" not in reward:
        fail("KillRewardScript must declare PW_KillRewardCheckTime Auto Const")
    if "PickmansWhisperPlayerAliasScript Property PlayerAlias Auto Const" not in reward:
        fail("KillRewardScript must declare PlayerAlias Auto Const")
    if "PendingRewardTarget.AddRef" in reward:
        fail("KillRewardScript typo PendingRewardTarget (missing s) must be fixed")
    if "PendingRewardTargets.AddRef" not in reward:
        fail("RegisterKillRewardCheck must PendingRewardTargets.AddRef")
    if "TIMER_KILL_REWARD_CHECK = 22" not in reward:
        fail("KillRewardScript must use TIMER_KILL_REWARD_CHECK = 22")
    if "StartTimer(" not in reward or "TIMER_KILL_REWARD_CHECK" not in reward:
        fail("RegisterKillRewardCheck must StartTimer(TIMER_KILL_REWARD_CHECK)")
    if "Event OnTimer" not in reward:
        fail("KillRewardScript must declare OnTimer")
    if "main.RewardKill(targetActor)" not in reward:
        fail("KillReward OnTimer must call Main.RewardKill")
    if "CheckIfKillRewarded" in reward:
        fail("KillRewardScript must not call CheckIfKillRewarded (RewardKill owns that)")
    ok("KillRewardScript: queue + AV + PlayerAlias properties + timer 22 + AddRef")

    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperKillRewardScript Property KillRewardAlias Auto Const" not in psc:
        fail("Main must declare KillRewardAlias Auto Const")
    if "Function ClearCollection(RefCollectionAlias" not in psc:
        fail("Main must expose ClearCollection for KillReward OnAliasInit")
    ok("MainQuestScript declares KillRewardAlias + ClearCollection")
    # RegisterTarget / RewardKill / CheckIfKillRewarded body contracts:
    # tools/test_register_reward_path.py

    if not ESP.is_file():
        fail(f"missing ESP {ESP}")
    data = ESP.read_bytes()
    body = find_qust(data, FID_QUEST)
    if body is None:
        fail(f"ESP missing QUST 0x{FID_QUEST:08X}")
    fields = parse_fields(body)
    anam = None
    aliases: list[tuple[int, str, int]] = []
    trailers_after: dict[int, dict[str, int]] = {}
    cur_id = None
    cur_name = None
    cur_fnam = None
    last_closed_id: int | None = None
    for st, sd in fields:
        if st == b"ANAM" and len(sd) >= 4:
            anam = struct.unpack("<I", sd)[0]
        if st == b"ALST" and len(sd) >= 4:
            cur_id = struct.unpack("<I", sd)[0]
            cur_name = None
            cur_fnam = None
        elif st == b"ALID" and cur_id is not None:
            cur_name = sd.split(b"\x00", 1)[0].decode("latin1", "replace")
        elif st == b"FNAM" and cur_id is not None and len(sd) >= 4:
            cur_fnam = struct.unpack("<I", sd)[0]
        elif st == b"ALED" and cur_id is not None and cur_name is not None:
            aliases.append((cur_id, cur_name, cur_fnam if cur_fnam is not None else -1))
            last_closed_id = cur_id
            cur_id = None
        elif st == b"ALCS" and last_closed_id is not None and len(sd) >= 4:
            trailers_after.setdefault(last_closed_id, {})["ALCS"] = struct.unpack(
                "<I", sd
            )[0]
        elif st == b"ALMI" and last_closed_id is not None:
            trailers_after.setdefault(last_closed_id, {})["ALMI"] = (
                sd[0] if sd else -1
            )

    kr = [a for a in aliases if a[1] == "KillRewardAlias"]
    if not kr or kr[0][0] != ALIAS_KILL_REWARD_ID:
        fail(f"KillRewardAlias ALST must be {ALIAS_KILL_REWARD_ID}")
    pending = [a for a in aliases if a[1] == "PendingRewardTargets"]
    if not pending or pending[0][0] != ALIAS_PENDING_REWARD_ID:
        fail(f"PendingRewardTargets ALST must be {ALIAS_PENDING_REWARD_ID}")
    if pending[0][2] != 0x20:
        fail(f"PendingRewardTargets FNAM must be 0x20, got 0x{pending[0][2]:X}")
    seed = [a for a in aliases if a[1] == "PendingRewardTargetsSeed"]
    if not seed or seed[0][0] != ALIAS_PENDING_REWARD_SEED_ID:
        fail(f"PendingRewardTargetsSeed ALST must be {ALIAS_PENDING_REWARD_SEED_ID}")
    seed_trail = trailers_after.get(ALIAS_PENDING_REWARD_SEED_ID, {})
    if seed_trail.get("ALCS") != ALIAS_PENDING_REWARD_ID:
        fail("post-ALED ALCS after PendingReward seed must point at collection id 4")
    if "ALMI" not in seed_trail:
        fail("post-ALED ALMI missing after PendingRewardTargetsSeed")
    if anam != ANAM_NEXT:
        fail(f"Main ANAM must be {ANAM_NEXT} (past ModConfigAlias), got {anam}")
    ok(
        f"ESP KillRewardAlias ALST={ALIAS_KILL_REWARD_ID}; "
        f"PendingRewardTargets ALST={ALIAS_PENDING_REWARD_ID}; ANAM={anam}"
    )

    avifs = {fid: body for fid, body in find_records(data, b"AVIF")}
    av_body = avifs.get(FID_AV_KILL_REWARD_CHECK_TIME)
    if av_body is None:
        fail(f"ESP missing AVIF 0x{FID_AV_KILL_REWARD_CHECK_TIME:08X}")
    if zfield(dict(parse_fields(av_body)).get(b"EDID", b"")) != "PW_KillRewardCheckTime":
        fail("AVIF 0x876 EDID must be PW_KillRewardCheckTime")
    ok("ESP AVIF PW_KillRewardCheckTime @ 0x876")

    vmad = next((sd for st, sd in fields if st == b"VMAD"), None)
    if not vmad or b"PickmansWhisperKillRewardScript" not in vmad:
        fail("Main VMAD must attach PickmansWhisperKillRewardScript")

    ptype, pstat, pzero, palias_id, pquest_fid = parse_vmad_object_prop(
        vmad, "KillRewardAlias"
    )
    if ptype != 1 or pstat != 1 or pzero != 0 or palias_id != ALIAS_KILL_REWARD_ID:
        fail("Main KillRewardAlias property bind invalid")
    if pquest_fid != FID_QUEST:
        fail("KillRewardAlias must bind to Main quest")

    ptype, pstat, pzero, palias_id, pquest_fid = parse_vmad_object_prop(
        vmad, "PendingRewardTargets"
    )
    if ptype != 1 or pstat != 1 or pzero != 0 or palias_id != ALIAS_PENDING_REWARD_ID:
        fail(
            f"PendingRewardTargets must bind alias {ALIAS_PENDING_REWARD_ID}, "
            f"got type/status={ptype}/{pstat} zero={pzero} alias={palias_id}"
        )
    if pquest_fid != FID_QUEST:
        fail("PendingRewardTargets must bind to Main quest")

    ptype, pstat, pzero, palias_id, pquest_fid = parse_vmad_object_prop(
        vmad, "PW_KillRewardCheckTime"
    )
    if ptype != 1 or pstat != 1 or pzero != 0 or palias_id != -1:
        fail("PW_KillRewardCheckTime must be Form bind (alias=-1)")
    if pquest_fid != FID_AV_KILL_REWARD_CHECK_TIME:
        fail(
            f"PW_KillRewardCheckTime must be 0x{FID_AV_KILL_REWARD_CHECK_TIME:08X}, "
            f"got 0x{pquest_fid:08X}"
        )

    # PlayerAlias appears on Main and KillRewardScript — verify both bind PlayerCombat ALST 0.
    player_binds = 0
    search_from = 0
    while True:
        idx = vmad.find(b"PlayerAlias", search_from)
        if idx < 0:
            break
        nlen = struct.unpack_from("<H", vmad, idx - 2)[0]
        if nlen == len("PlayerAlias"):
            off = idx + nlen
            ptype, pstat = vmad[off], vmad[off + 1]
            pzero, palias_id, pquest_fid = struct.unpack_from("<hhI", vmad, off + 2)
            if (
                ptype == 1
                and pstat == 1
                and pzero == 0
                and palias_id == 0
                and pquest_fid == FID_PLAYER_QUEST
            ):
                player_binds += 1
        search_from = idx + len("PlayerAlias")
    if player_binds < 2:
        fail(
            f"VMAD must bind PlayerAlias→PlayerCombat ALST 0 on Main and KillReward "
            f"(found {player_binds})"
        )
    ok(
        "VMAD: KillRewardAlias + PendingRewardTargets + PW_KillRewardCheckTime + "
        "PlayerAlias (x2) bound"
    )

    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperKillRewardScript.psc" not in deploy:
        fail("build-deploy-local.ps1 must Caprica-compile KillRewardScript")
    if "test_kill_reward_alias.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_kill_reward_alias.py")
    ok("deploy gate compiles KillRewardScript + runs this contract")

    print("All KillRewardAlias contracts passed.")


if __name__ == "__main__":
    main()
