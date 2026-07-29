#!/usr/bin/env python3
"""Proximity cloak — exact Glowing One chain contracts.

Ability SPEL (crGlowingOneCloak clone) → Cloak MGEF (RadiationCloak clone, arch=35,
NO VMAD, Assoc=hit SPEL, Area=15) → Hit SPEL (RadiationHazardToken clone) → Hit MGEF
(Script + PickmansWhisperProximityEffect VMAD; no radiation).

Locks:
  - FormIDs 0x870–0x873 + NEXT_OID 0x874
  - Vanilla sources: Ability 0xDB3AD, Cloak 0xDB3AE, Token 0xDF451, Hazard 0x9252A
  - Cloak Assoc Item == Hit SPEL; Cloak has no VMAD; Hit has proximity script
  - Cloak Area=15; Ability EFIT Area=40
  - Alias GetFormFromFile uses LOCAL id 0x00000873
  - Deploy compiles PickmansWhisperProximityEffect.psc (not CloakHost)

Usage:
  python tools/test_proximity_cloak.py
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_hunger_spell_esp.py"
ESP = ROOT / "Data" / "PickmansWhisper.esp"
STUB = ROOT / "tools" / "stubs" / "ActiveMagicEffect.psc"
EFFECT_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperProximityEffect.psc"
ALIAS_PSC = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperPlayerAliasScript.psc"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"

FID_PROXIMITY_HIT_MGEF = 0x01000870
FID_PROXIMITY_HIT_SPEL = 0x01000871
FID_PROXIMITY_CLOAK_MGEF = 0x01000872
FID_PROXIMITY_CLOAK_SPEL = 0x01000873
PROXIMITY_CLOAK_AREA = 15
PROXIMITY_ABILITY_EFIT_AREA = 40


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def parse_esp_records(data: bytes) -> list[tuple[str, int, bytes]]:
    i = 0
    while i + 24 <= len(data):
        if data[i : i + 4] == b"TES4":
            size = struct.unpack_from("<I", data, i + 4)[0]
            i += 24 + size
            break
        i += 1
    out: list[tuple[str, int, bytes]] = []
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
                rtype = data[j : j + 4].decode("ascii", "replace")
                size = struct.unpack_from("<I", data, j + 4)[0]
                formid = struct.unpack_from("<I", data, j + 12)[0]
                body = data[j + 24 : j + 24 + size]
                out.append((rtype, formid, body))
                j += 24 + size
            i = end
            continue
        rtype = tag.decode("ascii", "replace")
        size = struct.unpack_from("<I", data, i + 4)[0]
        formid = struct.unpack_from("<I", data, i + 12)[0]
        body = data[i + 24 : i + 24 + size]
        out.append((rtype, formid, body))
        i += 24 + size
    return out


def fields_last(body: bytes) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    j = 0
    while j + 6 <= len(body):
        t = body[j : j + 4].decode("ascii", "replace")
        sz = struct.unpack_from("<H", body, j + 4)[0]
        out[t] = body[j + 6 : j + 6 + sz]
        j += 6 + sz
    return out


def fields_all(body: bytes) -> list[tuple[str, bytes]]:
    out: list[tuple[str, bytes]] = []
    j = 0
    while j + 6 <= len(body):
        t = body[j : j + 4].decode("ascii", "replace")
        sz = struct.unpack_from("<H", body, j + 4)[0]
        out.append((t, body[j + 6 : j + 6 + sz]))
        j += 6 + sz
    return out


def zfield(blob: bytes) -> str:
    return blob.split(b"\x00", 1)[0].decode("latin1", "replace")


def main() -> None:
    builder_text = BUILDER.read_text(encoding="utf-8", errors="replace")
    for needle, label in [
        ("FID_PROXIMITY_HIT_MGEF = 0x01000870", "HIT_MGEF"),
        ("FID_PROXIMITY_HIT_SPEL = 0x01000871", "HIT_SPEL"),
        ("FID_PROXIMITY_CLOAK_MGEF = 0x01000872", "CLOAK_MGEF"),
        ("FID_PROXIMITY_CLOAK_SPEL = 0x01000873", "CLOAK_SPEL"),
        ("NEXT_OID = 0x00000874", "NEXT_OID"),
        ("VANILLA_CLOAK_ABILITY_SPEL_SOURCE = 0x000DB3AD", "ability source"),
        ("VANILLA_CLOAK_MGEF_SOURCE = 0x000DB3AE", "cloak source"),
        ("VANILLA_CLOAK_HIT_SPEL_SOURCE = 0x000DF451", "hit spel source"),
        ("VANILLA_CLOAK_HIT_MGEF_SOURCE = 0x0009252A", "hit mgef source"),
        ("PROXIMITY_CLOAK_AREA = 15", "cloak area"),
        ("PROXIMITY_ABILITY_EFIT_AREA = 40", "ability efit area"),
    ]:
        if needle not in builder_text:
            fail(f"build_hunger_spell_esp.py must declare {label}: {needle}")
    if "PickmansWhisperProximityCloakHost" in builder_text:
        fail("builder must not reference PickmansWhisperProximityCloakHost (Cloak has no VMAD)")
    if "0x00247A40" in builder_text or "DetectLife" in builder_text:
        fail("builder must not still clone DetectLife cloak sources")
    ok("builder reserves Glowing One clone FormIDs 0x870-0x873, NEXT_OID=0x874")

    if not STUB.is_file():
        fail("tools/stubs/ActiveMagicEffect.psc missing")
    stub_text = STUB.read_text(encoding="utf-8", errors="replace")
    if "extends ScriptObject Native Hidden" not in stub_text:
        fail("ActiveMagicEffect stub must match real FO4 source: extends ScriptObject Native Hidden")
    if "Event OnEffectStart(Actor akTarget, Actor akCaster)" not in stub_text:
        fail("ActiveMagicEffect stub must declare OnEffectStart(Actor akTarget, Actor akCaster)")
    if "Event OnEffectFinish(Actor akTarget, Actor akCaster)" not in stub_text:
        fail("ActiveMagicEffect stub must declare OnEffectFinish(Actor akTarget, Actor akCaster)")
    if "Native" in re.sub(r"^Scriptname.*$", "", stub_text, flags=re.MULTILINE):
        fail("ActiveMagicEffect stub must declare zero Native functions (events only)")
    ok("ActiveMagicEffect stub matches real FO4 source signature, events-only")

    if not EFFECT_PSC.is_file():
        fail("PickmansWhisperProximityEffect.psc missing")
    effect_text = EFFECT_PSC.read_text(encoding="utf-8", errors="replace")
    if "extends ActiveMagicEffect" not in effect_text:
        fail("PickmansWhisperProximityEffect must extend ActiveMagicEffect")
    if "Event OnEffectStart(Actor akTarget, Actor akCaster)" not in effect_text:
        fail("PickmansWhisperProximityEffect must implement OnEffectStart")
    if "Event OnEffectFinish(Actor akTarget, Actor akCaster)" not in effect_text:
        fail("PickmansWhisperProximityEffect must implement OnEffectFinish")
    if "akTarget == akCaster" not in effect_text:
        fail("PickmansWhisperProximityEffect must guard against the caster reporting on itself")
    if "hit MGEF" not in effect_text.lower() and "ProximityHitEffect" not in effect_text:
        fail("PickmansWhisperProximityEffect docstring must describe the hit MGEF / Cloak chain")
    if "RegisterTarget" not in effect_text:
        fail("PickmansWhisperProximityEffect must forward enter to Main.RegisterTarget")
    if "PickmansWhisperMainQuestScript Property Main Auto Const" not in effect_text:
        fail("ProximityEffect must declare Main Auto Const (bound from hit MGEF VMAD)")
    if re.search(r"Game\.GetFormFromFile\s*\(", effect_text):
        fail("ProximityEffect must not GetFormFromFile Main each pulse — use Auto Const Main")
    if "Function GetMain()" in effect_text:
        fail("ProximityEffect GetMain() retired — use Auto Const Main property")
    ok("PickmansWhisperProximityEffect: Main Auto Const + RegisterTarget + self-guard")

    host_psc = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperProximityCloakHost.psc"
    if host_psc.is_file():
        fail("PickmansWhisperProximityCloakHost.psc must be removed (Cloak MGEF has no script)")
    ok("ProximityCloakHost removed (matches RadiationCloak: no cloak VMAD)")

    alias_text = ALIAS_PSC.read_text(encoding="utf-8", errors="replace")
    if "Weapon Property CombatKnifeBase Auto Const" not in alias_text:
        fail("PlayerAliasScript must declare Weapon Property CombatKnifeBase Auto Const")
    if "Keyword Property PickmanModKeyword Auto Const" not in alias_text:
        fail("PlayerAliasScript must declare Keyword Property PickmanModKeyword Auto Const")
    if "Spell Property PickmansCloakSpell Auto Const" not in alias_text:
        fail("PlayerAliasScript must declare Spell Property PickmansCloakSpell Auto Const")
    if "ObjectMod Property mod_CombatKnife_Blade_Stealth" in alias_text:
        fail("PlayerAliasScript must not declare mod_CombatKnife_Blade_Stealth (retired)")
    if "ObjectMod Property mod_Legendary_Weapon_Bleed" in alias_text:
        fail("PlayerAliasScript must not declare mod_Legendary_Weapon_Bleed (retired)")
    if "Weapon Property TargetWeapon" in alias_text:
        fail("PlayerAliasScript must not declare TargetWeapon (retired)")
    if "FID_COMBAT_KNIFE = 0x000913CA" not in builder_text:
        fail("builder must declare FID_COMBAT_KNIFE = 0x000913CA")
    if "FID_PICKMAN_MOD_KEYWORD = 0x0013AD45" not in builder_text:
        fail("builder must declare FID_PICKMAN_MOD_KEYWORD = dn_HasMeleeMod_SerratedStealth")
    for needle in (
        '"CombatKnifeBase", FID_COMBAT_KNIFE',
        '"PickmanModKeyword", FID_PICKMAN_MOD_KEYWORD',
        '"PickmansCloakSpell", FID_PROXIMITY_CLOAK_SPEL',
    ):
        if needle not in builder_text:
            fail(f"PlayerCombat alias VMAD must bind {needle}")
    if "mod_CombatKnife_Blade_Stealth" in builder_text or "mod_Legendary_Weapon_Bleed" in builder_text:
        fail("builder must not bind retired OMOD properties")
    if "TargetWeapon" in builder_text:
        fail("builder must not bind TargetWeapon")
    ok("PlayerAliasScript CombatKnifeBase + PickmanModKeyword + PickmansCloakSpell binds")

    if "Function GrantProximityCloak()" not in alias_text:
        fail("PlayerAliasScript must declare GrantProximityCloak()")
    grant_body_m = re.search(r"Function GrantProximityCloak\(\).*?EndFunction", alias_text, re.DOTALL)
    if not grant_body_m:
        fail("could not extract GrantProximityCloak body")
    grant_body = grant_body_m.group(0)
    if "GrantProximityCloak enter" not in grant_body:
        fail("GrantProximityCloak must Trace on enter (Notifications alone never hit Papyrus.0.log)")
    if "GetFormFromFile" not in grant_body:
        fail("GrantProximityCloak must GetFormFromFile the cloak Ability")
    if "AddSpell(cloak, False)" not in grant_body:
        fail("GrantProximityCloak must AddSpell silently (abVerbose=False)")
    if "RemoveSpell(cloak)" not in grant_body:
        fail("GrantProximityCloak must RemoveSpell+AddSpell when already owned (refresh Constant Effect)")
    if "had=" not in grant_body and "re-applied" not in grant_body:
        fail("GrantProximityCloak must Trace had/re-apply outcome (silent path hid Constant Effect failures)")
    if "Bool hadSpell = p.HasSpell(cloak)" not in grant_body:
        fail("GrantProximityCloak must detect prior HasSpell before RemoveSpell+AddSpell refresh")
    if "FID_PROXIMITY_CLOAK_SPELL = 0x00000873" not in alias_text:
        fail("PlayerAliasScript must use local GetFormFromFile id 0x00000873 (not 0x01……)")
    if re.search(r"FID_PROXIMITY_CLOAK_SPELL\s*=\s*0x01000873", alias_text):
        fail("PlayerAliasScript must not assign plugin-prefixed FormID to FID_PROXIMITY_CLOAK_SPELL")
    on_alias_init_m = re.search(r"Event OnAliasInit\(\).*?EndEvent", alias_text, re.DOTALL)
    on_load_m = re.search(r"Event OnPlayerLoadGame\(\).*?EndEvent", alias_text, re.DOTALL)
    if not on_alias_init_m:
        fail("OnAliasInit missing")
    if not on_load_m:
        fail("OnPlayerLoadGame missing")
    # Direct Grant on init/load may be commented while aura is gated on TargetWeapon
    # equip; RegisterMagicEffectDetect (below) must still Grant for save-stack bypass.
    magic_reg_m = re.search(
        r"Function RegisterMagicEffectDetect\(\).*?EndFunction", alias_text, re.DOTALL
    )
    if not magic_reg_m or "GrantProximityCloak()" not in magic_reg_m.group(0):
        fail(
            "RegisterMagicEffectDetect must call GrantProximityCloak — "
            "stale OnPlayerLoadGame save-stacks call this but never Grant themselves"
        )
    ok("PlayerAliasScript grants cloak via RegisterMagicEffectDetect (save-stack bypass)")

    if not ESP.is_file():
        fail(f"missing built ESP: {ESP} (run tools/build_hunger_spell_esp.py first)")
    records = parse_esp_records(ESP.read_bytes())
    by_id = {(rtype, fid): body for rtype, fid, body in records}

    player_combat = by_id.get(("QUST", 0x01000805))
    if player_combat is None:
        fail("built ESP missing PickmansWhisperPlayerCombat 0x01000805")
    pc_vmad = fields_last(player_combat).get("VMAD", b"")
    expected_binds = (
        (b"CombatKnifeBase", 0x000913CA),
        (b"PickmanModKeyword", 0x0013AD45),
        (b"PickmansCloakSpell", 0x01000873),
    )
    for prop_name, want_fid in expected_binds:
        if prop_name not in pc_vmad:
            fail(f"PlayerCombat alias VMAD must contain {prop_name.decode()}")
        idx = pc_vmad.find(prop_name)
        nlen = struct.unpack_from("<H", pc_vmad, idx - 2)[0]
        if nlen != len(prop_name):
            fail(f"{prop_name.decode()} wstring length mismatch")
        off = idx + nlen
        ptype, pstat = pc_vmad[off], pc_vmad[off + 1]
        zero, alias_id, fid = struct.unpack_from("<hhI", pc_vmad, off + 2)
        if ptype != 1 or pstat != 1:
            fail(f"{prop_name.decode()} type/status must be 1/1, got {ptype}/{pstat}")
        if zero != 0 or alias_id != -1:
            fail(f"{prop_name.decode()} must be form bind (alias=-1)")
        if fid != want_fid:
            fail(f"{prop_name.decode()} must bind 0x{want_fid:08X}, got 0x{fid:08X}")
    for retired in (b"TargetWeapon", b"mod_CombatKnife_Blade_Stealth", b"mod_Legendary_Weapon_Bleed"):
        if retired in pc_vmad:
            fail(f"PlayerCombat VMAD must not contain {retired.decode()}")
    ok("PlayerCombat VMAD CombatKnifeBase + PickmanModKeyword + PickmansCloakSpell bound")

    hit_mgef = by_id.get(("MGEF", FID_PROXIMITY_HIT_MGEF))
    if hit_mgef is None:
        fail(f"built ESP missing Hit MGEF 0x{FID_PROXIMITY_HIT_MGEF:08X}")
    hmf = fields_last(hit_mgef)
    if zfield(hmf.get("EDID", b"")) != "PickmansWhisperProximityHitEffect":
        fail("hit MGEF EDID mismatch")
    if "VMAD" not in hmf or b"PickmansWhisperProximityEffect" not in hmf["VMAD"]:
        fail("hit MGEF VMAD must attach PickmansWhisperProximityEffect")
    vmad = hmf["VMAD"]
    if b"Main" not in vmad:
        fail("hit MGEF VMAD must bind property Main")
    # Object form property: name Main + type1/status1 + 0 + alias-1 + quest fid
    main_idx = vmad.find(b"Main")
    if main_idx < 2:
        fail("hit MGEF VMAD Main property offset invalid")
    main_nlen = struct.unpack_from("<H", vmad, main_idx - 2)[0]
    if main_nlen != len("Main"):
        fail("hit MGEF VMAD Main wstring length mismatch")
    poff = main_idx + main_nlen
    ptype, pstat = vmad[poff], vmad[poff + 1]
    zero, alias_id, quest_fid = struct.unpack_from("<hhI", vmad, poff + 2)
    if ptype != 1 or pstat != 1:
        fail(f"Main property type/status must be 1/1, got {ptype}/{pstat}")
    if zero != 0 or alias_id != -1:
        fail(f"Main property must be form bind (alias=-1), got zero={zero} alias={alias_id}")
    if quest_fid != 0x01000800:
        fail(f"Main property must point at PickmansWhisperMain 0x01000800, got 0x{quest_fid:08X}")
    hdata = hmf.get("DATA", b"")
    if len(hdata) < 88:
        fail(f"hit MGEF DATA too short ({len(hdata)})")
    if struct.unpack_from("<I", hdata, 64)[0] != 1:
        fail("hit MGEF Archetype must be 1 (Script)")
    if struct.unpack_from("<i", hdata, 68)[0] != 0:
        fail("hit MGEF Primary AV must be 0 (no Radiation)")
    if struct.unpack_from("<i", hdata, 16)[0] != 0:
        fail("hit MGEF Resist AV must be 0 (no Radiation resist)")
    if struct.unpack_from("<I", hdata, 80)[0] != 0 or struct.unpack_from("<I", hdata, 84)[0] != 3:
        fail("hit MGEF must be Constant Effect (0) / Target Actor (3)")
    ok(f"Hit MGEF 0x{FID_PROXIMITY_HIT_MGEF:08X}: Script + Constant/TargetActor + VMAD Main->0x800")

    cloak_mgef = by_id.get(("MGEF", FID_PROXIMITY_CLOAK_MGEF))
    if cloak_mgef is None:
        fail(f"built ESP missing Cloak MGEF 0x{FID_PROXIMITY_CLOAK_MGEF:08X}")
    cmf = fields_last(cloak_mgef)
    if zfield(cmf.get("EDID", b"")) != "PickmansWhisperProximityCloakEffect":
        fail("cloak MGEF EDID mismatch")
    if "VMAD" in cmf:
        fail("Cloak MGEF must have NO VMAD (RadiationCloak has none; script is on hit MGEF)")
    cdata = cmf.get("DATA", b"")
    if len(cdata) < 88:
        fail(f"cloak MGEF DATA too short ({len(cdata)})")
    arch = struct.unpack_from("<I", cdata, 64)[0]
    assoc = struct.unpack_from("<I", cdata, 8)[0]
    area = struct.unpack_from("<I", cdata, 44)[0]
    cast_t = struct.unpack_from("<I", cdata, 80)[0]
    deliv = struct.unpack_from("<I", cdata, 84)[0]
    if arch != 35:
        fail(f"cloak MGEF Archetype must be 35 (Cloak), got {arch}")
    if assoc != FID_PROXIMITY_HIT_SPEL:
        fail(f"cloak MGEF Assoc Item must be Hit SPEL 0x{FID_PROXIMITY_HIT_SPEL:08X}, got 0x{assoc:08X}")
    if area != PROXIMITY_CLOAK_AREA:
        fail(f"cloak MGEF Area must be {PROXIMITY_CLOAK_AREA}, got {area}")
    if cast_t != 0 or deliv != 0:
        fail(f"cloak MGEF must be Constant Effect / Self (cast={cast_t} deliv={deliv})")
    ok(f"Cloak MGEF 0x{FID_PROXIMITY_CLOAK_MGEF:08X}: arch=35 Assoc=HitSPEL Area={area} no VMAD")

    hit_spel = by_id.get(("SPEL", FID_PROXIMITY_HIT_SPEL))
    if hit_spel is None:
        fail(f"built ESP missing Hit SPEL 0x{FID_PROXIMITY_HIT_SPEL:08X}")
    hsf = fields_last(hit_spel)
    if zfield(hsf.get("EDID", b"")) != "PickmansWhisperProximityHit":
        fail("hit SPEL EDID mismatch")
    spit = hsf.get("SPIT", b"")
    if len(spit) < 24:
        fail(f"hit SPEL SPIT too short ({len(spit)})")
    if struct.unpack_from("<I", spit, 8)[0] != 0:
        fail("hit SPEL Type must be 0 (Spell) like RadiationHazardToken")
    if struct.unpack_from("<I", spit, 16)[0] != 0:
        fail("hit SPEL CastType must be 0 (Constant Effect)")
    if struct.unpack_from("<I", spit, 20)[0] != 3:
        fail("hit SPEL TargetType must be 3 (Target Actor)")
    efids = [sd for t, sd in fields_all(hit_spel) if t == "EFID"]
    efits = [sd for t, sd in fields_all(hit_spel) if t == "EFIT"]
    if len(efids) != 1:
        fail(f"hit SPEL must have exactly one EFID, got {len(efids)}")
    if len(efids[0]) < 4 or struct.unpack_from("<I", efids[0], 0)[0] != FID_PROXIMITY_HIT_MGEF:
        fail("hit SPEL EFID must point at Hit MGEF")
    if len(efits) != 1:
        fail(f"hit SPEL must have exactly one EFIT, got {len(efits)}")
    mag0, area0, dur0 = struct.unpack_from("<fII", efits[0], 0)
    if (area0, dur0) != (0, 1):
        fail(f"hit SPEL EFIT must be area/dur 0/1, got {(area0, dur0)}")
    if abs(mag0 - 5.0) > 0.01:
        fail(f"hit SPEL EFIT mag must be 5.0, got {mag0}")
    ok(f"Hit SPEL 0x{FID_PROXIMITY_HIT_SPEL:08X}: Constant/TargetActor + EFID->Hit MGEF EFIT 5/0/1")

    cloak_spel = by_id.get(("SPEL", FID_PROXIMITY_CLOAK_SPEL))
    if cloak_spel is None:
        fail(f"built ESP missing Cloak Ability SPEL 0x{FID_PROXIMITY_CLOAK_SPEL:08X}")
    csf = fields_last(cloak_spel)
    if zfield(csf.get("EDID", b"")) != "PickmansWhisperProximityCloak":
        fail("cloak SPEL EDID mismatch")
    spit = csf.get("SPIT", b"")
    if len(spit) < 24:
        fail(f"cloak SPEL SPIT too short ({len(spit)})")
    if struct.unpack_from("<I", spit, 8)[0] != 4:
        fail("cloak SPEL Type must be 4 (Ability)")
    if struct.unpack_from("<I", spit, 16)[0] != 0:
        fail("cloak SPEL CastType must be 0 (Constant Effect)")
    if struct.unpack_from("<I", spit, 20)[0] != 0:
        fail("cloak SPEL TargetType must be 0 (Self)")
    cef = csf.get("EFID", b"")
    if len(cef) < 4 or struct.unpack_from("<I", cef, 0)[0] != FID_PROXIMITY_CLOAK_MGEF:
        fail("cloak Ability SPEL EFID must point at Cloak MGEF")
    efit = csf.get("EFIT", b"")
    if len(efit) < 12:
        fail("cloak Ability EFIT missing")
    mag, efit_area, dur = struct.unpack_from("<fII", efit, 0)
    if efit_area != PROXIMITY_ABILITY_EFIT_AREA:
        fail(f"cloak Ability EFIT Area must be {PROXIMITY_ABILITY_EFIT_AREA}, got {efit_area}")
    if dur != 0:
        fail(f"cloak Ability EFIT Duration must be 0, got {dur}")
    if abs(mag - 10.0) > 0.01:
        fail(f"cloak Ability EFIT Magnitude must be 10.0 (crGlowingOneCloak), got {mag}")
    ok(f"Cloak Ability SPEL 0x{FID_PROXIMITY_CLOAK_SPEL:08X}: Ability/Self mag=10 area=40 -> Cloak MGEF")

    for deploy_path in (DEPLOY_PS1, DEPLOY_SH):
        deploy_text = deploy_path.read_text(encoding="utf-8", errors="replace")
        if "PickmansWhisperProximityEffect.psc" not in deploy_text:
            fail(f"{deploy_path.name} does not compile/deploy PickmansWhisperProximityEffect.psc")
        if "PickmansWhisperProximityCloakHost" in deploy_text:
            fail(f"{deploy_path.name} must not compile/deploy ProximityCloakHost")
    ok("deploy gate compiles + ships hit ActiveMagicEffect only")

    print("All proximity-cloak (Glowing One clone) contracts passed.")


if __name__ == "__main__":
    main()
