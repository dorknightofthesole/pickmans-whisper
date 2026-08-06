#!/usr/bin/env python3
"""ModConfigAlias on PickmansWhisperMain — ModConfig.txt host.

Locks:
  - Main ALST 5 ModConfigAlias UniqueActor=Player
  - ANAM 7 (past VoiceAlias ALST 6)
  - VMAD attaches PickmansWhisperModConfigScript on ALST 5
  - Main.ModConfigAlias Auto Const + VMAD Object bind to ALST 5
  - LoadModConfig body + parse helpers live on ModConfigScript
  - Main keeps thin LoadModConfig / DecayStagesReady façades
  - OnAliasInit calls LoadModConfig
  - Deploy compiles + ships ModConfigScript

Usage:
  python tools/test_modconfig_alias.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
MAIN_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
MOD_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperModConfigScript.psc"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"

FID_QUEST = 0x01000800
ALIAS_MOD_CONFIG_ID = 5
ALIAS_VOICE_ID = 6
ANAM_NEXT = ALIAS_VOICE_ID + 1


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


def find_vmad_object_prop(
    vmad: bytes, prop_name: str
) -> list[tuple[int, int]]:
    """Return list of (alias_id, form_id) for Object props named prop_name."""
    name_b = prop_name.encode("utf-8")
    out: list[tuple[int, int]] = []
    i = 0
    while True:
        j = vmad.find(name_b, i)
        if j < 0:
            break
        # wstring: u16 len + bytes — prop layout after name
        # We match exact wstring by checking preceding u16 length.
        if j >= 2:
            ln = struct.unpack_from("<H", vmad, j - 2)[0]
            if ln == len(name_b) and j + ln + 2 + 2 + 4 <= len(vmad):
                # type(1) status(1) pad(2) alias(2) form(4) — after name
                off = j + ln
                typ, status = vmad[off], vmad[off + 1]
                if typ == 1:
                    alias_id = struct.unpack_from("<h", vmad, off + 2 + 2)[0]
                    form_id = struct.unpack_from("<I", vmad, off + 2 + 2 + 2)[0]
                    out.append((alias_id, form_id))
        i = j + 1
    return out


def main() -> None:
    builder = BUILDER.read_text(encoding="utf-8", errors="replace")
    for needle, label in (
        ("ALIAS_MOD_CONFIG_ID = 5", "ModConfig ALST"),
        ('zstr("ModConfigAlias")', "ModConfig ALID"),
        ('"PickmansWhisperModConfigScript"', "alias script attach"),
    ):
        if needle not in builder:
            fail(f"builder missing {label}: {needle}")
    if "mod_config_prop" not in builder:
        fail("builder must VMAD-bind Main.ModConfigAlias (mod_config_prop)")
    ok("builder declares ModConfigAlias ALST 5 + VMAD script + Main Object bind")

    if not MOD_PSC.is_file():
        fail("PickmansWhisperModConfigScript.psc missing")
    mod = MOD_PSC.read_text(encoding="utf-8", errors="replace")
    if "Scriptname PickmansWhisperModConfigScript extends ReferenceAlias" not in mod:
        fail("ModConfigScript must extend ReferenceAlias")
    if "Event OnAliasInit()" not in mod or "LoadModConfig()" not in mod:
        fail("ModConfigScript must LoadModConfig on OnAliasInit")
    if "Function LoadModConfig()" not in mod:
        fail("ModConfigScript must own LoadModConfig")
    if "ClearPendingDecayStages" not in mod or "CommitPendingDecayStages" not in mod:
        fail("ModConfigScript must own pending→commit decay stage load")
    if "String Property RenamePromptFemaleNPC" not in mod:
        fail("ModConfigScript must expose RenamePromptFemaleNPC as Property")
    if "String Property BondIntroGreeting" not in mod:
        fail("ModConfigScript must expose BondIntroGreeting as Property")
    if "String Property HungerWithdrawalToast" not in mod:
        fail("ModConfigScript must expose HungerWithdrawalToast as Property")
    if 'key == "bondIntroGreeting"' not in mod:
        fail("LoadModConfig must parse bondIntroGreeting")
    if 'key == "hungerWithdrawalToast"' not in mod:
        fail("LoadModConfig must parse hungerWithdrawalToast")
    if "Int Property DECAY_STAGE_COUNT" not in mod:
        fail("ModConfigScript must expose DECAY_STAGE_COUNT as Property")
    ok("ModConfigScript: ReferenceAlias + OnAliasInit load + Properties")

    mod_txt = (ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    if "bondIntroGreeting=Something in the gallery leans closer... glad you came." not in mod_txt:
        fail("ModConfig.txt must ship bondIntroGreeting default")
    if "hungerWithdrawalToast=The quiet ends. The knife remembers." not in mod_txt:
        fail("ModConfig.txt must ship hungerWithdrawalToast default")
    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    if "Something in the gallery leans closer" in psc:
        fail("Main must not hard-code bond intro (ModConfig BondIntroGreeting is source of truth)")
    if "ModConfigAlias.BondIntroGreeting" not in psc:
        fail("StartBond must read ModConfigAlias.BondIntroGreeting")
    alias_psc = (
        ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
    ).read_text(encoding="utf-8", errors="replace")
    if 'StartBond("blade-equipped")' not in alias_psc:
        fail('PlayerAlias must StartBond("blade-equipped") on blade ready')
    if "StartBond(" in psc:
        # RewardKill must not own bond; equip path does.
        import re

        m = re.search(
            r"(?im)^Function RewardKill\b.*?\nEndFunction",
            psc,
            flags=re.S,
        )
        if m and "StartBond" in m.group(0):
            fail("RewardKill must not StartBond (PlayerAlias blade-equipped owns it)")
    ok(
        "bondIntroGreeting ships in ModConfig.txt; StartBond reads ModConfigAlias; "
        "equip path owns bond"
    )

    psc = MAIN_PSC.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperModConfigScript Property ModConfigAlias Auto Const" not in psc:
        fail("Main must declare ModConfigAlias Auto Const (ESP Object bind)")
    if "Function EnsureFeatureAliases" not in psc:
        fail("Main must keep EnsureFeatureAliases fail-loud check")
    if "Function LoadModConfig()" in psc:
        fail("Main must not own LoadModConfig (Alias OnAliasInit only)")
    if "String Function ConfigFieldTrim" in psc:
        fail("Main must not keep ConfigFieldTrim body (moved to ModConfigAlias)")
    if "ClearPendingDecayStages" in psc and "Function ClearPendingDecayStages" in psc:
        fail("Main must not keep ClearPendingDecayStages body")
    ok("MainQuestScript declares ModConfigAlias Auto Const")

    if not ESP.is_file():
        fail(f"ESP missing: {ESP}")
    data = ESP.read_bytes()
    qust = find_qust(data, FID_QUEST)
    if not qust:
        fail("PickmansWhisperMain QUST missing")
    fields = parse_fields(qust)
    aliases: list[tuple[int, str, int]] = []
    anam = None
    for st, sd in fields:
        if st == b"ANAM" and len(sd) >= 4:
            anam = struct.unpack_from("<I", sd, 0)[0]
        if st == b"ALST" and len(sd) >= 4:
            aid = struct.unpack_from("<I", sd, 0)[0]
            alid = ""
            fnam = 0
            # peek following fields until ALED — simplified: scan next few
            aliases.append((aid, "", 0))
    # proper ALID walk
    aliases = []
    i = 0
    while i < len(fields):
        st, sd = fields[i]
        if st == b"ALST" and len(sd) >= 4:
            aid = struct.unpack_from("<I", sd, 0)[0]
            alid = ""
            fnam = 0
            j = i + 1
            while j < len(fields) and fields[j][0] != b"ALED":
                if fields[j][0] == b"ALID":
                    alid = zfield(fields[j][1])
                elif fields[j][0] == b"FNAM" and len(fields[j][1]) >= 4:
                    fnam = struct.unpack_from("<I", fields[j][1], 0)[0]
                j += 1
            aliases.append((aid, alid, fnam))
            i = j
        else:
            i += 1

    mc = [a for a in aliases if a[1] == "ModConfigAlias"]
    if not mc or mc[0][0] != ALIAS_MOD_CONFIG_ID:
        fail(f"ModConfigAlias ALST must be {ALIAS_MOD_CONFIG_ID}, got {mc}")
    if anam != ANAM_NEXT:
        fail(f"Main ANAM must be {ANAM_NEXT}, got {anam}")
    ok(f"ESP ModConfigAlias ALST={ALIAS_MOD_CONFIG_ID}; ANAM={anam}")

    vmad = dict(fields).get(b"VMAD", b"")
    if not vmad or b"PickmansWhisperModConfigScript" not in vmad:
        fail("Main VMAD must attach PickmansWhisperModConfigScript")
    binds = find_vmad_object_prop(vmad, "ModConfigAlias")
    if not binds or binds[0] != (ALIAS_MOD_CONFIG_ID, FID_QUEST):
        fail(
            f"Main VMAD must Object-bind ModConfigAlias → ALST {ALIAS_MOD_CONFIG_ID}, "
            f"got {binds}"
        )
    ok(f"VMAD: ModConfigScript on ALST 5; Main.ModConfigAlias -> {ALIAS_MOD_CONFIG_ID}")

    deploy = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    if "PickmansWhisperModConfigScript.psc" not in deploy:
        fail("build-deploy-local.ps1 must Caprica-compile ModConfigScript")
    if "test_modconfig_alias.py" not in deploy:
        fail("build-deploy-local.ps1 must run test_modconfig_alias.py")
    ok("deploy gate compiles ModConfigScript + runs this contract")

    print("All ModConfigAlias contracts passed.")


if __name__ == "__main__":
    main()
