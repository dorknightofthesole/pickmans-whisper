#!/usr/bin/env python3
"""Regenerate the Wound Lab "Captive Tattoos" chunk banks from the Captive Tattoos
mod's own LooksMenu overlay catalog (SlaveTattoos.esp/overlays.json).

Why chunked at all: Fallout 4's Papyrus VM caps dynamic arrays (`new Type[N]`) at
128 elements. The catalog has 1,025 overlay ids, so it cannot live in one bank
array like DecayWoundOverlays.txt/DecaySkinOverlays.txt do. Instead this splits
the catalog by its own "(Category)" tag (parsed out of each entry's "name", e.g.
"CapTats (Front Belly) BBC Whore" -> category "Front Belly"), one bank file +
one MCM stepper per category, capped well under the 128 ceiling per chunk.

Output (all under Data/PickmansWhisper/config/tattoos/):
  - CaptiveTattoo_<Slug>[_<Letter>].txt   — one overlay id per line (Papyrus bank
    format: '#'-prefixed comments and blank lines skipped by ParseRawIntoBank,
    same as DecayWoundOverlays.txt/DecaySkinOverlays.txt).
  - _manifest.json — dev-tool-only index consumed by later generation steps
    (Papyrus field/dispatch table, config.json stepper options). NOT read by
    Papyrus or shipped — matches source .txt bank ordering exactly, which is
    what actually matters (MCM stepper index -> bank[index] must line up).

Usage:
  python tools/build_captive_tattoo_bank.py
  (reads CAPTIVE_TATTOOS_OVERLAYS_JSON from .env / real env; see .env.example)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "Data" / "PickmansWhisper" / "config" / "tattoos"
MANIFEST_PATH = OUT_DIR / "_manifest.json"

# Headroom under Papyrus's 128-element dynamic-array ceiling — chunks split at
# this size, not 128, so a handful of catalog updates don't tip a chunk over.
MAX_CHUNK = 110
# Categories with fewer entries than this get folded into one "Misc" chunk
# instead of getting their own single-digit-item stepper.
MIN_CHUNK = 10

NAME_CATEGORY_RE = re.compile(r"^CapTats\s*\((.*?)\)")


def find_overlays_json() -> Path:
    import os

    load_dotenv()
    env = os.environ.get("CAPTIVE_TATTOOS_OVERLAYS_JSON")
    if not env:
        raise SystemExit(
            "CAPTIVE_TATTOOS_OVERLAYS_JSON not set. Copy .env.example to .env and "
            "point it at Captive Tattoos' F4SE/Plugins/F4EE/Overlays/SlaveTattoos.esp/"
            "overlays.json (see .env.example for the exact key)."
        )
    p = Path(env)
    if not p.is_file():
        raise SystemExit(f"CAPTIVE_TATTOOS_OVERLAYS_JSON not a file: {p}")
    return p


def slugify(category: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "", category)
    if not slug:
        slug = "Misc"
    return slug


def extract_category(name: str) -> str:
    m = NAME_CATEGORY_RE.match(name.strip())
    if not m:
        return "Misc"
    cat = re.sub(r"\s+", " ", m.group(1)).strip()
    return cat if cat else "Misc"


def load_catalog(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise SystemExit(f"unexpected overlays.json shape (want a list): {path}")
    out = []
    for entry in data:
        oid = entry.get("id")
        name = entry.get("name", "")
        if not oid:
            continue
        out.append({"id": oid, "name": name, "category": extract_category(name)})
    return out


def group_into_chunks(entries: list[dict]) -> list[dict]:
    """Group by category; merge tiny categories into Misc; split oversized ones.
    Returns ordered chunk dicts: {label, slug, entries: [{id, name}, ...]}."""
    by_cat: dict[str, list[dict]] = {}
    for e in entries:
        by_cat.setdefault(e["category"], []).append({"id": e["id"], "name": e["name"]})

    misc: list[dict] = list(by_cat.pop("Misc", []))
    real: dict[str, list[dict]] = {}
    for cat, items in by_cat.items():
        if len(items) < MIN_CHUNK:
            misc.extend(items)
        else:
            real[cat] = items

    chunks: list[dict] = []
    for cat in sorted(real.keys()):
        items = real[cat]
        if len(items) <= MAX_CHUNK:
            chunks.append({"label": cat, "slug": slugify(cat), "entries": items})
        else:
            n_parts = -(-len(items) // MAX_CHUNK)  # ceil div
            size = -(-len(items) // n_parts)  # even-ish split
            for i in range(n_parts):
                part = items[i * size : (i + 1) * size]
                if not part:
                    continue
                letter = chr(ord("A") + i)
                chunks.append(
                    {
                        "label": f"{cat} {letter}",
                        "slug": f"{slugify(cat)}_{letter}",
                        "entries": part,
                    }
                )

    if misc:
        # Misc can itself exceed MAX_CHUNK once every stray small category is
        # dumped in — split the same way as an oversized real category.
        if len(misc) <= MAX_CHUNK:
            chunks.append({"label": "Misc", "slug": "Misc", "entries": misc})
        else:
            n_parts = -(-len(misc) // MAX_CHUNK)
            size = -(-len(misc) // n_parts)
            for i in range(n_parts):
                part = misc[i * size : (i + 1) * size]
                if not part:
                    continue
                letter = chr(ord("A") + i)
                chunks.append({"label": f"Misc {letter}", "slug": f"Misc_{letter}", "entries": part})

    return chunks


def write_chunk_file(chunk: dict, index: int) -> str:
    filename = f"CaptiveTattoo_{chunk['slug']}.txt"
    lines = [
        f"# Captive Tattoos chunk {index} — {chunk['label']} ({len(chunk['entries'])} ids).",
        "# Auto-generated by tools/build_captive_tattoo_bank.py — do not hand-edit;",
        "# re-run the generator against overlays.json instead. Order matches the",
        f"# iTattooItem_{chunk['slug']}:WoundLab stepper in config.json exactly.",
    ]
    lines.extend(e["id"] for e in chunk["entries"])
    (OUT_DIR / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return filename


def main() -> None:
    src = find_overlays_json()
    entries = load_catalog(src)
    print(f"loaded {len(entries)} overlay entries from {src}")

    chunks = group_into_chunks(entries)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    total = 0
    for i, chunk in enumerate(chunks):
        if len(chunk["entries"]) > 128:
            raise SystemExit(f"chunk {chunk['label']} has {len(chunk['entries'])} > 128 — split logic bug")
        filename = write_chunk_file(chunk, i)
        total += len(chunk["entries"])
        manifest.append(
            {
                "index": i,
                "file": filename,
                "label": chunk["label"],
                "slug": chunk["slug"],
                "count": len(chunk["entries"]),
                "names": [e["name"] for e in chunk["entries"]],
            }
        )
        print(f"  [{i:2d}] {filename:40s} {chunk['label']:24s} {len(chunk['entries']):4d} ids")

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(chunks)} chunk files, {total} ids total (source had {len(entries)})")
    print(f"manifest: {MANIFEST_PATH}")
    if total != len(entries):
        raise SystemExit(f"id count mismatch: chunks have {total}, source has {len(entries)}")


if __name__ == "__main__":
    main()
