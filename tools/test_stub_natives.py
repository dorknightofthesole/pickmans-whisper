#!/usr/bin/env python3
"""Forbid known fake / Skyrim-only Native stubs in tools/stubs.

Caps the no-fake-native-stubs rule: Caprica only sees stubs, so wishful Natives
compile green and die in-game. This list is burn history + audited landmines.

When FO4 / GoE / LooksMenu sources are present on this machine, also verify that
every Native declared under tools/stubs exists on the real script (inheritance
aware for FO4 Base/F4SE).

Usage:
  python tools/test_stub_natives.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "tools" / "stubs"
USER_SCRIPTS = ROOT / "Data" / "Scripts" / "Source" / "User"
EXTRACTED_OVERLAYS = ROOT / "tools" / "_extracted_looksmenu" / "scripts" / "Source" / "User" / "Overlays.psc"


def _env_path(key: str) -> Path | None:
    raw = os.environ.get(key, "").strip()
    return Path(raw) if raw else None

# (relative stub file, regex that must NOT match a Native declaration / call)
FORBIDDEN = [
    (
        "Quest.psc",
        r"Bool\s+Function\s+IsRunning\s*\(\s*\)\s*\n\s*Return",
        "Quest.IsRunning dummy body (must be Native)",
    ),
    (
        "Game.psc",
        r"Function\s+GetCurrentCrosshairRef\s*\(",
        "Game.GetCurrentCrosshairRef (Skyrim SKSE / optional extender, not base FO4)",
    ),
    (
        "Game.psc",
        r"Function\s+EnablePlayerControls\s*\(",
        "Game.EnablePlayerControls (Skyrim; not FO4 Game.psc)",
    ),
    (
        "Game.psc",
        r"Function\s+DisablePlayerControls\s*\(",
        "Game.DisablePlayerControls (Skyrim; not FO4 Game.psc)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForUpdate\s*\(",
        "ScriptObject.RegisterForUpdate (removed in FO4; use StartTimer)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForSingleUpdate\s*\(",
        "ScriptObject.RegisterForSingleUpdate (removed in FO4; use StartTimer)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+UnregisterForUpdate\s*\(",
        "ScriptObject.UnregisterForUpdate (removed in FO4)",
    ),
    (
        "ScriptObject.psc",
        r"Event\s+OnUpdate\s*\(",
        "ScriptObject.OnUpdate (removed in FO4; use OnTimer)",
    ),
    (
        "Math.psc",
        r"Function\s+NumberOfSetBits\s*\(",
        "Math.NumberOfSetBits (not in FO4 Math.psc)",
    ),
    (
        "Input.psc",
        r"Function\s+IsKeyPressed\s*\(",
        "Input.IsKeyPressed (Skyrim SKSE; FO4 uses RegisterForKey + OnKeyDown)",
    ),
    (
        "Actor.psc",
        r"Function\s+HasLOS\s*\(",
        "Actor.HasLOS (Skyrim; FO4 uses HasDetectionLOS / RegisterForDirectLOS*)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForLOS\s*\(",
        "ScriptObject.RegisterForLOS (not FO4; use RegisterForDirectLOSGain/Lost)",
    ),
    (
        "Quest.psc",
        r"Function\s+RegisterForRemoteEvent\s*\(",
        "Quest.RegisterForRemoteEvent shadow (lives on ScriptObject with ScriptEventName)",
    ),
    (
        "Quest.psc",
        r"Function\s+RegisterForKey\s*\(",
        "Quest.RegisterForKey shadow (lives on ScriptObject)",
    ),
    (
        "Quest.psc",
        r"Function\s+StartTimer\s*\(",
        "Quest.StartTimer shadow (lives on ScriptObject)",
    ),
    (
        "ActorBase.psc",
        r"Function\s+GetName\s*\(\s*\)\s*Native",
        "ActorBase.GetName Native (real API is F4SE Form.GetName)",
    ),
    (
        "ReferenceAlias.psc",
        r"Actor\s+Function\s+GetActorReference\s*\(\s*\)\s*Native",
        "ReferenceAlias.GetActorReference as Native (real FO4 is a non-native cast wrapper)",
    ),
]

# Real FO4 APIs Slice G needs — must stay Native in stubs.
REQUIRED_NATIVES = [
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForPlayerSleep\s*\(\s*\)\s*Native",
        "RegisterForPlayerSleep",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+StartTimer\s*\(",
        "StartTimer",
    ),
    (
        "ScriptObject.psc",
        r"Bool\s+Function\s+RegisterForRemoteEvent\s*\(\s*ScriptObject",
        "RegisterForRemoteEvent(ScriptObject, ScriptEventName)",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForDirectLOSGain\s*\(",
        "RegisterForDirectLOSGain",
    ),
    (
        "ScriptObject.psc",
        r"Function\s+RegisterForDirectLOSLost\s*\(",
        "RegisterForDirectLOSLost",
    ),
    (
        "Actor.psc",
        r"Bool\s+Function\s+HasDetectionLOS\s*\(",
        "HasDetectionLOS",
    ),
    (
        "Actor.psc",
        r"Function\s+KillSilent\s*\(",
        "KillSilent",
    ),
    (
        "Actor.psc",
        r"Bool\s+Function\s+SnapIntoInteraction\s*\(",
        "SnapIntoInteraction",
    ),
    (
        "ObjectReference.psc",
        r"Bool\s+Function\s+PlayImpactEffect\s*\(",
        "PlayImpactEffect",
    ),
    (
        "ObjectReference.psc",
        r"Float\s+Function\s+GetValue\s*\(",
        "ObjectReference.GetValue",
    ),
    (
        "Game.psc",
        r"Function\s+FadeOutGame\s*\(\s*Bool\s+\w+\s*,\s*Bool\s+\w+\s*,\s*Float\s+\w+\s*,\s*Float\s+\w+",
        "FadeOutGame(abFadingOut, abBlackFade, afSecsBeforeFade, afFadeDuration, ...)",
    ),
    (
        "Overlays.psc",
        r"Function\s+AddEntry\s*\(\s*Actor\s+akActor\s*,\s*bool\s+isFemale\s*,\s*int\s+priority\s*,\s*string\s+template\s*\)\s*global",
        "Overlays.AddEntry",
    ),
    (
        "Overlays.psc",
        r"Function\s+Update\s*\(\s*Actor\s+akActor\s*\)\s*global\s+native",
        "Overlays.Update",
    ),
    (
        "GardenOfEden2.psc",
        r"Bool\s+Function\s+SetDisplayName\s*\(\s*ObjectReference",
        "GardenOfEden2.SetDisplayName",
    ),
]

# Fake APIs that must never appear as Native stubs.
FORBIDDEN_FAKE_NATIVES = [
    (
        "Actor.psc",
        r"Function\s+SetSilent\s*\(",
        "Actor.SetSilent (not FO4 — Skyrim folklore / wishful API)",
    ),
    (
        "ObjectReference.psc",
        r"Function\s+SetDisplayName\s*\(\s*String",
        "ObjectReference.SetDisplayName(String,...) (SKSE shape — use GardenOfEden2.SetDisplayName)",
    ),
]

# Entire stub files that must not exist (Skyrim-only / wishful packages).
FORBIDDEN_STUB_FILES = [
    ("StringUtil.psc", "FO4/F4SE has no StringUtil — use GardenOfEden.StrFind/SubStr/ReplaceStr"),
]

# Calls in our scripts that must never appear (even if stub is gone).
FORBIDDEN_CALLS = [
    (r"Game\.GetCurrentCrosshairRef\s*\(\s*\)", "Game.GetCurrentCrosshairRef()"),
    (r"\bRegisterForUpdate\s*\(", "RegisterForUpdate("),
    (r"\bRegisterForSingleUpdate\s*\(", "RegisterForSingleUpdate("),
    (r"\bUnregisterForUpdate\s*\(", "UnregisterForUpdate("),
    (r"Math\.NumberOfSetBits\s*\(", "Math.NumberOfSetBits("),
    (r"Input\.IsKeyPressed\s*\(", "Input.IsKeyPressed("),
    (r"\bSetSilent\s*\(", "SetSilent("),
    (r"StringUtil\.", "StringUtil.* (Skyrim-only — use GoE string natives)"),
    (r"Game\.EnablePlayerControls\s*\(", "Game.EnablePlayerControls("),
    (r"Game\.DisablePlayerControls\s*\(", "Game.DisablePlayerControls("),
    # Member SetDisplayName is SKSE-shaped; GoE2.SetDisplayName(ref, name) is the FO4 path.
    (
        r"(?<!GardenOfEden2\.)\bSetDisplayName\s*\(\s*[^,\)]+\s*,",
        "Actor/ObjectReference.SetDisplayName(member) — use GardenOfEden2.SetDisplayName",
    ),
]

NATIVE_RE = re.compile(
    r"(?im)^\s*(?:[A-Za-z0-9_\[\]\s]+?\s+)?"
    r"Function\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*"
    r"(?:Native\s+Global|Global\s+Native|native\s+global|global\s+native|Native|native)\b",
)

EXTENDS_RE = re.compile(
    r"(?im)^\s*ScriptName\s+(\S+)\s+(?:extends\s+(\S+))?",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def strip_comments(text: str) -> str:
    text = re.sub(r";.*?$", "", text, flags=re.M)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text


def native_names(text: str) -> set[str]:
    # Join Papyrus line-continuations so multi-line signatures stay one line.
    # Do NOT use DOTALL on args — that previously swallowed later Function decls.
    cleaned = strip_comments(text)
    cleaned = re.sub(r"\\\s*\n", " ", cleaned)
    return {m.group(1) for m in NATIVE_RE.finditer(cleaned)}


def resolve_fo4_script(fo4_source: Path, name: str) -> Path | None:
    """Prefer F4SE-merged Source root, then Base/."""
    if not fo4_source.is_dir():
        return None
    root = fo4_source / name
    if root.is_file():
        return root
    base = fo4_source / "Base" / name
    if base.is_file():
        return base
    user = fo4_source / "User" / name
    if user.is_file():
        return user
    return None


def inheritance_native_universe(
    script_path: Path,
    fo4_source: Path,
    cache: dict[str, set[str]],
) -> set[str]:
    key = str(script_path.resolve())
    if key in cache:
        return cache[key]
    text = script_path.read_text(encoding="utf-8", errors="replace")
    names = native_names(text)
    m = EXTENDS_RE.search(text)
    parent = m.group(2) if m else None
    if parent:
        parent_name = parent.split(":")[-1] + ".psc"
        # ScriptObject has no file parent beyond itself.
        if parent_name.lower() != script_path.name.lower():
            parent_path = resolve_fo4_script(fo4_source, parent_name)
            if parent_path:
                names |= inheritance_native_universe(parent_path, fo4_source, cache)
    cache[key] = names
    return names


def verify_against_real_sources() -> None:
    """When install sources exist, every stub Native must exist on the real script."""
    fo4_source = _env_path("FO4_SCRIPTS_SOURCE")
    goe_source = _env_path("GOE_SCRIPTS_SOURCE")
    mcm_source = _env_path("MCM_SCRIPT_SOURCE")
    sft_source = _env_path("SFT_API_SOURCE")
    overlays_real_env = _env_path("LOOKSMENU_OVERLAYS_PSC")

    if not fo4_source or not fo4_source.is_dir():
        print("SKIP: set FO4_SCRIPTS_SOURCE in .env for live FO4/F4SE stub verify")
        return

    cache: dict[str, set[str]] = {}
    soft_deps = {
        "NecromanticMainQuestScript.psc",  # events-only soft stub
        "SFT\\SFT_API.psc",
        "SFT/SFT_API.psc",
        "Overlays.psc",  # LooksMenu — checked separately
        "MCM.psc",
        "GardenOfEden.psc",
        "GardenOfEden2.psc",
        "GardenOfEden3.psc",
        "F4SE.psc",
    }

    for stub_path in sorted(STUBS.rglob("*.psc")):
        rel = stub_path.relative_to(STUBS).as_posix()
        rel_win = str(stub_path.relative_to(STUBS))
        if rel in soft_deps or rel_win in soft_deps:
            continue
        stub_natives = native_names(stub_path.read_text(encoding="utf-8", errors="replace"))
        if not stub_natives:
            continue
        real = resolve_fo4_script(fo4_source, stub_path.name)
        if not real:
            fail(f"{rel}: stub declares natives but no FO4 source found for {stub_path.name}")
        universe = inheritance_native_universe(real, fo4_source, cache)
        # Papyrus names are case-insensitive (FO4 Math uses sin/cos; stubs may use Sin/Cos).
        universe_ci = {n.casefold() for n in universe}
        fake = sorted(n for n in stub_natives if n.casefold() not in universe_ci)
        if fake:
            fail(f"{rel}: Native(s) not in FO4/F4SE (+parents) {real}: {fake}")
        print(f"OK: {rel} natives subset of {real.name} (+parents)")

    # GoE / MCM / F4SE / SFT — exact script match for declared natives / functions.
    pairs: list[tuple[Path, Path | None, str]] = [
        (
            STUBS / "GardenOfEden.psc",
            (goe_source / "GardenOfEden.psc") if goe_source else None,
            "GOE_SCRIPTS_SOURCE",
        ),
        (
            STUBS / "GardenOfEden2.psc",
            (goe_source / "GardenOfEden2.psc") if goe_source else None,
            "GOE_SCRIPTS_SOURCE",
        ),
        (
            STUBS / "GardenOfEden3.psc",
            (goe_source / "GardenOfEden3.psc") if goe_source else None,
            "GOE_SCRIPTS_SOURCE",
        ),
        (STUBS / "F4SE.psc", fo4_source / "F4SE.psc", "FO4_SCRIPTS_SOURCE"),
        (STUBS / "MCM.psc", mcm_source, "MCM_SCRIPT_SOURCE"),
    ]
    for stub_path, real_path, env_key in pairs:
        if not stub_path.is_file():
            fail(f"missing stub {stub_path.name}")
        if real_path is None or not real_path.is_file():
            print(f"SKIP: set {env_key} in .env to verify {stub_path.name}")
            continue
        sn = native_names(stub_path.read_text(encoding="utf-8", errors="replace"))
        rn = native_names(real_path.read_text(encoding="utf-8", errors="replace"))
        rn_ci = {n.casefold() for n in rn}
        fake = sorted(n for n in sn if n.casefold() not in rn_ci)
        if fake:
            fail(f"{stub_path.name}: Native(s) not in real {real_path}: {fake}")
        print(f"OK: {stub_path.name} natives subset of installed source")

    if sft_source and sft_source.is_file():
        stub_text = (STUBS / "SFT" / "SFT_API.psc").read_text(encoding="utf-8", errors="replace")
        real_text = sft_source.read_text(encoding="utf-8", errors="replace")
        stub_fns = set(re.findall(r"(?im)^\s*(?:[A-Za-z0-9_\[\]\s]+?\s+)?Function\s+(\w+)\s*\(", stub_text))
        real_fns = set(re.findall(r"(?im)^\s*(?:[A-Za-z0-9_\[\]\s]+?\s+)?Function\s+(\w+)\s*\(", real_text))
        fake = sorted(stub_fns - real_fns)
        if fake:
            fail(f"SFT_API.psc: function(s) not in real SFT API: {fake}")
        print("OK: SFT_API.psc functions subset of installed SFT")
    else:
        print("SKIP: set SFT_API_SOURCE in .env to verify SFT_API.psc")

    overlays_stub = STUBS / "Overlays.psc"
    overlays_real = None
    if overlays_real_env and overlays_real_env.is_file():
        overlays_real = overlays_real_env
    elif EXTRACTED_OVERLAYS.is_file():
        overlays_real = EXTRACTED_OVERLAYS
    if overlays_real:
        sn = native_names(overlays_stub.read_text(encoding="utf-8", errors="replace"))
        rn = native_names(overlays_real.read_text(encoding="utf-8", errors="replace"))
        fake = sorted(n for n in sn if n.casefold() not in {x.casefold() for x in rn})
        if fake:
            fail(f"Overlays.psc: Native(s) not in LooksMenu source: {fake}")
        print("OK: Overlays.psc natives subset of LooksMenu source")
    else:
        print("SKIP: set LOOKSMENU_OVERLAYS_PSC in .env (or extract Overlays.psc) to verify")


def main() -> None:
    load_dotenv()
    if not STUBS.is_dir():
        fail(f"missing stubs dir {STUBS}")

    for rel, why in FORBIDDEN_STUB_FILES:
        if (STUBS / rel).is_file():
            fail(f"forbidden stub file {rel}: {why}")
        print(f"OK: no forbidden stub file {rel}")

    for rel, pattern, why in FORBIDDEN + FORBIDDEN_FAKE_NATIVES:
        path = STUBS / rel
        if not path.is_file():
            # Input.psc must not exist with IsKeyPressed; absence is fine.
            if rel == "Input.psc":
                continue
            fail(f"missing stub {rel}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(pattern, text):
            fail(f"{rel}: forbidden Native/event — {why}")
        print(f"OK: {rel} clean of {why.split('(')[0].strip()}")

    # Input.psc must not be introduced as a Skyrim key-poll stub
    input_psc = STUBS / "Input.psc"
    if input_psc.is_file():
        text = input_psc.read_text(encoding="utf-8", errors="replace")
        if re.search(r"Function\s+IsKeyPressed\s*\(", text):
            fail("Input.psc: forbidden IsKeyPressed Native")

    for rel, pattern, label in REQUIRED_NATIVES:
        path = STUBS / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        if not re.search(pattern, text):
            fail(f"{rel}: missing required Native {label}")
        print(f"OK: {rel} declares {label}")

    for psc in sorted(USER_SCRIPTS.glob("*.psc")):
        text = psc.read_text(encoding="utf-8", errors="replace")
        for pattern, label in FORBIDDEN_CALLS:
            if re.search(pattern, text):
                fail(f"{psc.name}: forbidden call {label}")
        if re.search(r"\bHasLOS\s*\(", text):
            fail(f"{psc.name}: forbidden Skyrim HasLOS (use HasDetectionLOS / DirectLOS)")
        if re.search(r"\bRegisterForLOS\s*\(", text):
            fail(f"{psc.name}: forbidden RegisterForLOS (use RegisterForDirectLOSGain/Lost)")
    print("OK: user scripts have no forbidden Skyrim/fake native calls")

    verify_against_real_sources()
    print("All stub-native contracts passed.")


if __name__ == "__main__":
    main()
