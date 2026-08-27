#!/usr/bin/env python3
"""Contracts for Wound Lab's Captive Tattoos section (SlaveTattoos.esp catalog).

Why chunked: the catalog has 1,025 overlay ids; Fallout 4's Papyrus VM caps
dynamic arrays (`new Type[N]`) at 128 elements, so tools/build_captive_tattoo_bank.py
splits it by the mod's own overlay category into <=128-id chunk banks. Apply always
targets whatever's in the crosshair (GardenOfEden3.GetCameraTargetReference via
TargetScanScript.GetLookingAt), never the sticky lab corpse the other Wound Lab
buttons use.

Multi-select, not single-select: the first version gated resolution through one
"category" menu + the matching chunk's item stepper — but MCM has no way to
redefine a stepper's option list at runtime, so all 20 item steppers are always
visible, and it's natural for a player to just move the one they're looking at
without also touching the category menu to match. That silently applied whatever
chunk the category menu happened to be sitting on (reported symptom: "only
applying the first stepper, hand, and ignoring the others"). Fixed by dropping
the category selector entirely: every item stepper defaults to option 0 = "(none)"
(skip), and Apply walks all 20, applying every one that isn't left at (none) —
any number at once, tracked per-chunk by UID (LastTattooUids[]) so a later Apply
replaces only what this panel itself applied.

Locks:
  - manifest.json chunk order/count matches every CaptiveTattoo_*.txt bank exactly
    (index -> file -> id count), and no chunk exceeds 128
  - ParseRawIntoBank derives its cap from bank.Length, not a hardcoded constant
  - DecayWoundLabScript: one (Bank/Count/Loaded) triplet + EnsureTattooChunk +
    TattooChunkBank/TattooChunkCount/TattooItemSettingId dispatcher per chunk;
    DebugApplyTattooLabOverlay resolves target via TargetScan().GetLookingAt()
    (not LabCorpse), loops all 20 chunks (no category gate), skips option 0
  - CorpseDecayScript: SoftTattooDepsReady gates on SlaveTattoos.esp (not
    porcOverlays.esl); BeginTattooApply/ApplyOneTattooChunk/FinishTattooApply
    track (LastTattooTarget, LastTattooUids[]) per chunk, only touching overlays
    this script itself applied to the same target
  - MainQuestScript forwards DebugApplyTattooLabOverlay to the lab script
  - config.json: no iTattooCategory selector; each iTattooItem_<Slug>:WoundLab
    stepper starts with "(none)" then that chunk's names in order
  - settings.ini (both copies) default every item key, no leftover category key
  - deploy scripts recursively ship Data/PickmansWhisper/config (chunk banks
    included) and run this test

Usage:
  python tools/test_captive_tattoo_lab.py
  (optional live check: set CAPTIVE_TATTOOS_OVERLAYS_JSON in .env to verify
  chunk ids are a subset of the real Captive Tattoos catalog)
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperDecayWoundLabScript.psc"
DECAY = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperCorpseDecayScript.psc"
MAIN = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperMainQuestScript.psc"
VOICE_ALIAS = ROOT / "Data" / "Scripts" / "Source" / "User" / "PickmansWhisperVoiceAliasScript.psc"
TATTOO_DIR = ROOT / "Data" / "PickmansWhisper" / "config" / "tattoos"
MANIFEST = TATTOO_DIR / "_manifest.json"
MCM = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "config.json"
SETTINGS_A = ROOT / "Data" / "MCM" / "Config" / "PickmansWhisper" / "settings.ini"
SETTINGS_B = ROOT / "Data" / "MCM" / "Settings" / "PickmansWhisper.ini"
DEPLOY_PS1 = ROOT / "tools" / "build-deploy-local.ps1"
DEPLOY_SH = ROOT / "tools" / "build-deploy-local.sh"
BUILDER = ROOT / "tools" / "build_captive_tattoo_bank.py"

MAX_CHUNK = 128


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def load_manifest() -> list[dict]:
    if not MANIFEST.is_file():
        fail(f"missing {MANIFEST} — run tools/build_captive_tattoo_bank.py")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def bank_ids(path: Path) -> list[str]:
    if not path.is_file():
        fail(f"missing chunk bank {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def test_manifest_matches_chunk_files() -> None:
    manifest = load_manifest()
    if len(manifest) < 2:
        fail("manifest has too few chunks — did the generator run?")
    total = 0
    for i, c in enumerate(manifest):
        if c["index"] != i:
            fail(f"manifest out of order at position {i}: index={c['index']}")
        if c["count"] > MAX_CHUNK:
            fail(f"chunk {c['label']} has {c['count']} ids > {MAX_CHUNK} Papyrus array cap")
        ids = bank_ids(TATTOO_DIR / c["file"])
        if len(ids) != c["count"]:
            fail(f"{c['file']}: manifest says {c['count']} ids, file has {len(ids)}")
        if len(c["names"]) != c["count"]:
            fail(f"manifest names/count mismatch for chunk {c['label']}")
        total += c["count"]
    ok(f"manifest matches {len(manifest)} chunk files, {total} ids total, all <= {MAX_CHUNK}")


def test_parse_raw_into_bank_uses_length() -> None:
    text = VOICE_ALIAS.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Int Function ParseRawIntoBank\(String\[\] raw, String\[\] bank\)(.*?)EndFunction", text, re.S)
    if not m:
        fail("ParseRawIntoBank not found")
    body = m.group(1)
    if "n < 64" in body:
        fail("ParseRawIntoBank must not hardcode a 64-element cap (breaks >64-id chunk banks)")
    if "n < bank.Length" not in body:
        fail("ParseRawIntoBank must cap on bank.Length so callers control capacity via allocation size")
    ok("ParseRawIntoBank caps on bank.Length, not a hardcoded constant")


def test_decay_wound_lab_script() -> None:
    manifest = load_manifest()
    text = LAB.read_text(encoding="utf-8", errors="replace")

    if "TATTOO_CONFIG_PATH" not in text:
        fail("DecayWoundLabScript must declare TATTOO_CONFIG_PATH (tattoos\\ subfolder)")

    for c in manifest:
        i = c["index"]
        for needle in (f"Tattoo{i}Bank", f"Tattoo{i}Count", f"Tattoo{i}Loaded", c["file"]):
            if needle not in text:
                fail(f"DecayWoundLabScript missing '{needle}' for chunk {i} ({c['label']})")
        if f'"iTattooItem_{c["slug"]}:WoundLab"' not in text:
            fail(f"TattooItemSettingId missing iTattooItem_{c['slug']}:WoundLab for chunk {i}")

    for fn in ("EnsureTattooChunk", "TattooChunkBank", "TattooChunkCount", "TattooItemSettingId", "DebugApplyTattooLabOverlay"):
        if f"Function {fn}(" not in text:
            fail(f"DecayWoundLabScript missing {fn}")

    apply_m = re.search(r"Function DebugApplyTattooLabOverlay\(\)(.*?)EndFunction", text, re.S)
    if not apply_m:
        fail("could not extract DebugApplyTattooLabOverlay body")
    apply_body = apply_m.group(1)
    if "TargetScan()" not in apply_body or "GetLookingAt()" not in apply_body:
        fail("DebugApplyTattooLabOverlay must resolve target via TargetScan().GetLookingAt() (camera target)")
    if re.search(r"[Tt]arget\s*=\s*LabCorpse\b", apply_body):
        fail("DebugApplyTattooLabOverlay must NOT fall back to the sticky LabCorpse field — always camera target per spec")
    if "iTattooCategory:WoundLab" in apply_body:
        fail("DebugApplyTattooLabOverlay must NOT gate resolution through a single category selector — every "
             "iTattooItem_* stepper must be checked independently (this was the multi-select bug: only the "
             "chunk the category menu happened to point at was ever applied)")
    if "StripLabCorpse(target)" not in apply_body:
        fail("DebugApplyTattooLabOverlay must StripLabCorpse(target) before applying — body-slot overlays render under worn clothing, same as every other Wound Lab apply")
    for fn in ("BeginTattooApply(", "ApplyOneTattooChunk(", "FinishTattooApply("):
        if fn not in apply_body:
            fail(f"DebugApplyTattooLabOverlay must call decay.{fn}...) as part of the multi-select apply pass")
    if "TattooItemSettingId(chunkIdx)" not in apply_body:
        fail("DebugApplyTattooLabOverlay must read every chunk's own item stepper by index, not just one")
    if "rawIdx > 0" not in apply_body and "rawIdx>0" not in apply_body:
        fail("DebugApplyTattooLabOverlay must skip chunks left at option 0 = (none)")
    if "chunkIdx < 20" not in apply_body:
        fail("DebugApplyTattooLabOverlay must loop over all 20 chunks, not stop early")

    ok(f"DecayWoundLabScript: {len(manifest)} chunk triplets + dispatcher + multi-select camera-target apply + clothing strip")


def test_corpse_decay_script() -> None:
    text = DECAY.read_text(encoding="utf-8", errors="replace")
    if 'PLUGIN_TATTOOS = "SlaveTattoos.esp"' not in text:
        fail("CorpseDecayScript must declare PLUGIN_TATTOOS = SlaveTattoos.esp")

    soft_m = re.search(r"Bool Function SoftTattooDepsReady\(\)(.*?)EndFunction", text, re.S)
    if not soft_m:
        fail("missing SoftTattooDepsReady")
    if "PLUGIN_PORC_OVERLAYS" in soft_m.group(1) or "PLUGIN_SFT" in soft_m.group(1):
        fail("SoftTattooDepsReady must gate on PLUGIN_TATTOOS only, not another bank's soft dep")
    if "PLUGIN_TATTOOS" not in soft_m.group(1):
        fail("SoftTattooDepsReady must check PLUGIN_TATTOOS")

    begin_m = re.search(r"Bool Function BeginTattooApply\(Actor akCorpse\)(.*?)EndFunction", text, re.S)
    if not begin_m:
        fail("missing Bool Function BeginTattooApply(Actor akCorpse)")
    begin_body = begin_m.group(1)
    if "SoftTattooDepsReady()" not in begin_body:
        fail("BeginTattooApply must gate on SoftTattooDepsReady()")
    if "LastTattooTarget" not in begin_body or "LastTattooUids" not in begin_body:
        fail("BeginTattooApply must track (LastTattooTarget, LastTattooUids[]) for multi-select replace")
    if "Overlays.Remove(" not in begin_body:
        fail("BeginTattooApply must remove whatever this script applied last time (same target only)")

    apply_one_m = re.search(r"Function ApplyOneTattooChunk\(Actor akCorpse, Int chunkIdx, String templateId\)(.*?)EndFunction", text, re.S)
    if not apply_one_m:
        fail("missing ApplyOneTattooChunk(Actor akCorpse, Int chunkIdx, String templateId)")
    one_body = apply_one_m.group(1)
    if "AddTintedOverlay(" not in one_body:
        fail("ApplyOneTattooChunk must add the overlay via AddTintedOverlay")
    if "TATTOO_PRIORITY" not in one_body:
        fail("ApplyOneTattooChunk must use TATTOO_PRIORITY")
    if "LastTattooUids[chunkIdx]" not in one_body:
        fail("ApplyOneTattooChunk must record the new overlay's UID at LastTattooUids[chunkIdx]")

    finish_m = re.search(r"Function FinishTattooApply\(Actor akCorpse, Int appliedCount\)(.*?)EndFunction", text, re.S)
    if not finish_m:
        fail("missing FinishTattooApply(Actor akCorpse, Int appliedCount)")
    finish_body = finish_m.group(1)
    if finish_body.count("Overlays.Update(") < 2:
        fail(
            "FinishTattooApply must call Overlays.Update twice (immediately, then again after a "
            "short Wait outside menu mode) — a single Update has been caught reporting success "
            "with nothing visually rendered, same reason ApplyTintedTemplateN does it"
        )
    if "Utility.Wait(" not in finish_body or "IsInMenuMode()" not in finish_body:
        fail("FinishTattooApply must Utility.Wait + re-Update outside menu mode, matching ApplyTintedTemplateN")

    if "Actor LastTattooTarget" not in text or "Int[] LastTattooUids" not in text:
        fail("CorpseDecayScript must declare LastTattooTarget/LastTattooUids[] fields")

    ok("CorpseDecayScript: SoftTattooDepsReady + multi-select Begin/ApplyOne/Finish tattoo apply")


def test_main_quest_forwarder() -> None:
    text = MAIN.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Function DebugApplyTattooLabOverlay\(\)(.*?)EndFunction", text, re.S)
    if not m:
        fail("MainQuestScript missing DebugApplyTattooLabOverlay forwarder")
    if "lab.DebugApplyTattooLabOverlay()" not in m.group(1):
        fail("MainQuestScript forwarder must call lab.DebugApplyTattooLabOverlay()")
    ok("MainQuestScript forwards DebugApplyTattooLabOverlay to the lab script")


def test_mcm_config() -> None:
    manifest = load_manifest()
    data = json.loads(MCM.read_text(encoding="utf-8"))
    wound_lab = next((p for p in data["pages"] if p.get("pageDisplayName") == "Wound Lab"), None)
    if not wound_lab:
        fail("config.json missing Wound Lab page")
    by_id = {e["id"]: e for e in wound_lab["content"] if "id" in e}

    if "iTattooCategory:WoundLab" in by_id:
        fail(
            "config.json must NOT have a category selector — the Item steppers are the selection "
            "themselves (multi-select); a category gate reproduces the 'only applies the first "
            "stepper' bug"
        )

    for c in manifest:
        sid = f"iTattooItem_{c['slug']}:WoundLab"
        el = by_id.get(sid)
        if not el:
            fail(f"config.json missing stepper {sid}")
        opts = el.get("valueOptions", {}).get("options", [])
        expected = ["(none)"] + c["names"]
        if opts != expected:
            fail(f"{sid}: options don't start with (none) followed by chunk {c['label']}'s names in order")

    apply_btn = next(
        (e for e in wound_lab["content"] if e.get("action", {}).get("function") == "DebugApplyTattooLabOverlay"),
        None,
    )
    if not apply_btn:
        fail("config.json missing Apply tattoo button (CallFunction DebugApplyTattooLabOverlay)")
    if apply_btn["action"].get("scriptName") != "PickmansWhisperMainQuestScript":
        fail("Apply tattoo button must CallFunction on PickmansWhisperMainQuestScript")

    ok(f"config.json: no category gate, {len(manifest)} item steppers default to (none) and match chunk banks + Apply button wired")


def test_settings_defaults() -> None:
    manifest = load_manifest()
    for path in (SETTINGS_A, SETTINGS_B):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "iTattooCategory=" in text:
            fail(f"{path} still defaults a removed iTattooCategory= key")
        for c in manifest:
            key = f"iTattooItem_{c['slug']}="
            if key not in text:
                fail(f"{path} missing default {key}")
    ok("settings.ini (both copies) default every tattoo MCM key")


def test_deploy_wiring() -> None:
    ps1 = DEPLOY_PS1.read_text(encoding="utf-8", errors="replace")
    sh = DEPLOY_SH.read_text(encoding="utf-8", errors="replace")
    if "test_captive_tattoo_lab.py" not in ps1 or "test_captive_tattoo_lab.py" not in sh:
        fail("deploy scripts must run test_captive_tattoo_lab.py")
    # .ps1 ships config\tattoos\ via a recursive folder sync function
    # (Sync-DataTree "PickmansWhisper" copies Data\PickmansWhisper\* recursively, which
    # includes config\ as a subfolder) rather than a literal path reference to config
    # itself — that literal form is only how build-deploy-local.sh happens to do it.
    if 'Sync-DataTree "PickmansWhisper"' not in ps1:
        fail('build-deploy-local.ps1 must Sync-DataTree "PickmansWhisper" (recursively ships config incl. tattoo chunk banks)')
    if "Data/PickmansWhisper/config" not in sh:
        fail("build-deploy-local.sh must recursively deploy Data/PickmansWhisper/config (ships tattoo chunk banks)")
    ok("deploy scripts ship the config folder recursively and run this test")


def test_live_catalog_subset() -> None:
    load_dotenv()
    env = os.environ.get("CAPTIVE_TATTOOS_OVERLAYS_JSON", "").strip()
    if not env:
        print("SKIP: set CAPTIVE_TATTOOS_OVERLAYS_JSON in .env to verify chunk ids against the live catalog")
        return
    src = Path(env)
    if not src.is_file():
        fail(f"CAPTIVE_TATTOOS_OVERLAYS_JSON not a file: {src}")
    known = {o["id"] for o in json.loads(src.read_text(encoding="utf-8-sig"))}
    manifest = load_manifest()
    missing_total = 0
    for c in manifest:
        ids = bank_ids(TATTOO_DIR / c["file"])
        missing = [i for i in ids if i not in known]
        missing_total += len(missing)
        if missing:
            fail(f"{c['file']}: {len(missing)} ids not in live catalog (e.g. {missing[:3]})")
    ok(f"all chunk ids ({sum(c['count'] for c in manifest)}) subset of live Captive Tattoos catalog")


def main() -> None:
    if not BUILDER.is_file():
        fail("missing tools/build_captive_tattoo_bank.py")
    test_manifest_matches_chunk_files()
    test_parse_raw_into_bank_uses_length()
    test_decay_wound_lab_script()
    test_corpse_decay_script()
    test_main_quest_forwarder()
    test_mcm_config()
    test_settings_defaults()
    test_deploy_wiring()
    test_live_catalog_subset()
    print("ALL OK")


if __name__ == "__main__":
    main()
