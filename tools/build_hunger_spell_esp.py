# Rebuild PickmansWhisper.esp with:
#   QUST 0x01000800 PickmansWhisperMain (quest script only)
#   QUST 0x01000805 PickmansWhisperPlayerCombat (Player UniqueActor alias —
#     VMAD mirrors DialogueGenericPlayer: 0 quest scripts + alias script)
#   GLOB / MGEF / SPEL Knife Hunger
#   SNDR clones for every Desperate_Audio.txt .xwm stem (D0.5) starting at
#     0x01000807 — EDID PW_Whisper_<Stem>, path Sound\PickmansWhisper\<file>
#   Writes Data/PickmansWhisper/config/WhisperSndrIds.txt (filename=localFid)
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ESP_PATH = ROOT / "Data" / "PickmansWhisper.esp"
DESPERATE_AUDIO = ROOT / "Data" / "PickmansWhisper" / "config" / "Desperate_Audio.txt"
SOUND_DIR = ROOT / "Data" / "Sound" / "PickmansWhisper"
SNDR_IDS_PATH = ROOT / "Data" / "PickmansWhisper" / "config" / "WhisperSndrIds.txt"

FID_QUEST = 0x01000800
FID_SPEL = 0x01000801
FID_GLOB = 0x01000802
FID_MGEF_AGI = 0x01000803
FID_MGEF_CHA = 0x01000804
FID_PLAYER_QUEST = 0x01000805
FID_WHISPER_BASE = 0x01000807
# Whisper SNDRs use 0x807+; leave headroom past 12 Desperate stems.
NEXT_OID = 0x00000820

# Vanilla PeakValueMod alcohol-withdrawal MGEFs we clone DATA from
VANILLA_MGEF_AGI = 0x0010224F
VANILLA_MGEF_CHA = 0x00102251

# Golden Standard one-shot SNDR fields (matches verified EndIt hand FO4Edit)
SNDR_CNAM_STANDARD = 0x1EEF540A  # BGSStandardSoundDef
SNDR_GNAM_WPN_RELOADS = 0x00249D87  # AudioCategoryWPNreloads
SNDR_ONAM_MONO = 0x000EC523  # SOMMono00700


def find_esm() -> Path:
    load_dotenv()
    env = os.environ.get("FALLOUT4_ESM")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    raise SystemExit(
        "Fallout4.esm not found. Copy .env.example to .env and set FALLOUT4_ESM "
        "to the full path of your Fallout4.esm (or set it as an environment variable)."
    )


ESM = find_esm()


def u32(n: int) -> bytes:
    return struct.pack("<I", n)


def u16(n: int) -> bytes:
    return struct.pack("<H", n)


def field(tag: bytes, data: bytes) -> bytes:
    return tag + u16(len(data)) + data


def zstr(s: str) -> bytes:
    return s.encode("ascii") + b"\x00"


def wstring(s: str) -> bytes:
    raw = s.encode("ascii")
    return struct.pack("<H", len(raw)) + raw


def record(typ: bytes, fid: int, payload: bytes, flags: int = 0) -> bytes:
    return (
        typ
        + u32(len(payload))
        + u32(flags)
        + u32(fid)
        + u32(0)
        + u16(131)
        + u16(0)
        + payload
    )


def group(label: bytes, records: bytes) -> bytes:
    body = records
    size = 24 + len(body)
    return b"GRUP" + u32(size) + label + u32(0) + u32(0) + u32(0) + body


def parse_fields(payload: bytes):
    fields = []
    off = 0
    while off + 6 <= len(payload):
        st = payload[off : off + 4]
        if not all(32 <= c < 127 for c in st):
            break
        ss = struct.unpack_from("<H", payload, off + 4)[0]
        if off + 6 + ss > len(payload):
            break
        sd = payload[off + 6 : off + 6 + ss]
        fields.append((st, sd))
        off += 6 + ss
    return fields


def build_vmad_script(script_name: str, status: int = 0) -> bytes:
    data = struct.pack("<HHH", 6, 2, 1)
    data += wstring(script_name)
    data += struct.pack("<BH", status & 0xFF, 0)
    return data


def build_vmad_alias_only(alias_script: str, quest_fid: int, status: int = 2) -> bytes:
    """
    Match DialogueGenericPlayer:
      ver=6 ofmt=2 scriptCount=0
      fragVer=3 unk=0 fragCount=0   (no empty filename — FO4 DGP omits it)
      aliasCount=1
      object: aliasId=0, reserved=0, formID=quest
      nested: ver=6 ofmt=2 scriptCount=1 + alias script (status 2 like vanilla)
    """
    data = struct.pack("<HHH", 6, 2, 0)  # no quest scripts
    data += struct.pack("<BHH", 3, 0, 0)  # fragVer, unk, fragCount
    data += struct.pack("<H", 1)  # aliasCount
    data += struct.pack("<hh", 0, 0)  # aliasId, reserved
    data += u32(quest_fid & 0xFFFFFFFF)
    data += struct.pack("<HHH", 6, 2, 1)
    data += wstring(alias_script)
    data += struct.pack("<BH", status & 0xFF, 0)
    return data


def build_player_alias_fields() -> bytes:
    return b"".join(
        [
            field(b"ALST", u32(0)),
            field(b"ALID", zstr("PlayerAlias")),
            field(b"FNAM", u32(0)),
            field(b"ALUA", u32(0x00000007)),  # Player
            field(b"VTCK", u32(0)),
            field(b"ALED", b""),
        ]
    )


def build_main_quest_payload() -> bytes:
    body = b""
    body += field(b"EDID", zstr("PickmansWhisperMain"))
    body += field(b"VMAD", build_vmad_script("PickmansWhisperMainQuestScript"))
    body += field(b"FULL", zstr("PickmansWhisperMain"))
    body += field(b"DNAM", bytes.fromhex("11005C730000000000000000"))
    body += field(b"NEXT", b"")
    body += field(b"ANAM", u32(0))
    return body


def build_player_combat_quest_payload() -> bytes:
    body = b""
    body += field(b"EDID", zstr("PickmansWhisperPlayerCombat"))
    body += field(
        b"VMAD",
        build_vmad_alias_only(
            "PickmansWhisperPlayerAliasScript", FID_PLAYER_QUEST, status=2
        ),
    )
    body += field(b"FULL", zstr("PickmansWhisperPlayerCombat"))
    # Start Game Enabled (0x0001) + same priority packing as main
    body += field(b"DNAM", bytes.fromhex("11005C730000000000000000"))
    body += field(b"NEXT", b"")
    body += field(b"ANAM", u32(1))
    body += build_player_alias_fields()
    return body


def extract_esm_mgef_payload(fid: int) -> bytes:
    data = ESM.read_bytes()
    needle = struct.pack("<I", fid)
    idx = 0
    while True:
        i = data.find(needle, idx)
        if i < 0:
            break
        if i >= 12 and data[i - 12 : i - 8] == b"MGEF":
            p = i - 12
            size = struct.unpack_from("<I", data, p + 4)[0]
            return data[p + 24 : p + 24 + size]
        idx = i + 1
    raise SystemExit(f"MGEF 0x{fid:08X} not found in Fallout4.esm")


def build_mgef_value_mod(van_fid: int, edid: str, full: str) -> bytes:
    src = extract_esm_mgef_payload(van_fid)
    out = []
    for st, sd in parse_fields(src):
        if st == b"EDID":
            out.append(field(b"EDID", zstr(edid)))
        elif st == b"FULL":
            out.append(field(b"FULL", zstr(full)))
        elif st == b"DATA" and len(sd) >= 72:
            data = bytearray(sd)
            struct.pack_into("<I", data, 64, 0)
            out.append(field(b"DATA", bytes(data)))
        else:
            out.append(field(st, sd))
    return b"".join(out)


def build_glob_payload() -> bytes:
    return b"".join(
        [
            field(b"EDID", zstr("PickmansWhisperHungerActive")),
            field(b"FNAM", b"f"),
            field(b"FLTV", struct.pack("<f", 0.0)),
        ]
    )


def ctda_global_equals_one(glob_fid: int) -> bytes:
    b = bytearray(32)
    b[0] = 0
    b[1:4] = bytes.fromhex("a02d76")
    struct.pack_into("<f", b, 4, 1.0)
    struct.pack_into("<H", b, 8, 74)
    struct.pack_into("<I", b, 12, glob_fid)
    struct.pack_into("<I", b, 28, 0xFFFFFFFF)
    return bytes(b)


def build_spel_payload() -> bytes:
    spit = bytearray(36)
    struct.pack_into("<I", spit, 8, 4)
    ctda = ctda_global_equals_one(FID_GLOB)
    efit = struct.pack("<fII", 0.0, 0, 0)
    return b"".join(
        [
            field(b"EDID", zstr("PickmansWhisperKnifeHunger")),
            field(b"OBND", b"\x00" * 12),
            field(b"FULL", zstr("Knife Hunger")),
            field(b"DESC", zstr("Withdrawal from unused Pickman's Blade hunger.")),
            field(b"SPIT", bytes(spit)),
            field(b"EFID", u32(FID_MGEF_AGI)),
            field(b"EFIT", efit),
            field(b"CTDA", ctda),
            field(b"EFID", u32(FID_MGEF_CHA)),
            field(b"EFIT", efit),
            field(b"CTDA", ctda),
        ]
    )


def build_tes4(num_records: int, next_object_id: int) -> bytes:
    payload = b"".join(
        [
            field(b"HEDR", struct.pack("<fII", 1.0, num_records, next_object_id)),
            field(b"CNAM", zstr("PickmansWhisper")),
            field(b"MAST", zstr("Fallout4.esm")),
            field(b"DATA", struct.pack("<Q", 0)),
            field(b"INTV", u32(1)),
        ]
    )
    return record(b"TES4", 0, payload, flags=0)


def parse_audio_map(path: Path) -> list[str]:
    """Parse *_Audio.txt — same skip rules as notice banks (blank / #)."""
    if not path.is_file():
        raise SystemExit(f"Missing audio map: {path}")
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def stem_from_xwm(filename: str) -> str:
    name = filename.strip()
    if not name.lower().endswith(".xwm"):
        raise SystemExit(f"Audio map entry must be .xwm, got {filename!r}")
    return name[: -len(".xwm")]


def build_whisper_sndr_payload(stem: str, xwm_filename: str) -> bytes:
    """Standard one-shot SNDR cloned from golden EndIt field layout."""
    edid = f"PW_Whisper_{stem}"
    anam = rf"Sound\PickmansWhisper\{xwm_filename}"
    # BNAM: freqShift, freqVar, priority=128, dbVar, staticAtten*100 (12.78 → 1278)
    bnam = struct.pack("<bbBBH", 0, 0, 128, 0, 1278)
    return b"".join(
        [
            field(b"EDID", zstr(edid)),
            field(b"CNAM", u32(SNDR_CNAM_STANDARD)),
            field(b"GNAM", u32(SNDR_GNAM_WPN_RELOADS)),
            field(b"ANAM", zstr(anam)),
            field(b"ONAM", u32(SNDR_ONAM_MONO)),
            field(b"LNAM", u32(0)),  # Looping: None
            field(b"BNAM", bnam),
        ]
    )


def collect_sndr_records() -> list[bytes]:
    """Emit one SNDR per Desperate_Audio.txt row (FormID = BASE + index)."""
    files = parse_audio_map(DESPERATE_AUDIO)
    if len(files) < 1:
        raise SystemExit(f"{DESPERATE_AUDIO} has no usable .xwm rows")
    out: list[bytes] = []
    id_lines = [
        "# Generated by tools/build_hunger_spell_esp.py — do not hand-edit.",
        "# filename=.xwm key → local FormID decimal (low 24 bits) for GetFormFromFile.",
    ]
    for i, filename in enumerate(files):
        stem = stem_from_xwm(filename)
        xwm_path = SOUND_DIR / filename
        if not xwm_path.is_file():
            raise SystemExit(f"Missing xwm for SNDR clone: {xwm_path}")
        fid = FID_WHISPER_BASE + i
        local_fid = fid & 0xFFFFFF
        out.append(record(b"SNDR", fid, build_whisper_sndr_payload(stem, filename)))
        id_lines.append(f"{filename}={local_fid}")
        print(f"  SNDR 0x{fid:08X} PW_Whisper_{stem} -> Sound\\PickmansWhisper\\{filename}")
    SNDR_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNDR_IDS_PATH.write_text("\n".join(id_lines) + "\n", encoding="utf-8")
    print(f"  Wrote {SNDR_IDS_PATH} ({len(files)} entries)")
    return out


def main() -> None:
    ESP_PATH.parent.mkdir(parents=True, exist_ok=True)

    main_q = record(b"QUST", FID_QUEST, build_main_quest_payload())
    player_q = record(b"QUST", FID_PLAYER_QUEST, build_player_combat_quest_payload())
    spel_rec = record(b"SPEL", FID_SPEL, build_spel_payload())
    glob_rec = record(b"GLOB", FID_GLOB, build_glob_payload())
    mgef_agi = record(
        b"MGEF",
        FID_MGEF_AGI,
        build_mgef_value_mod(
            VANILLA_MGEF_AGI, "PickmansWhisperReduceAgility", "Knife Hunger (Agility)"
        ),
    )
    mgef_cha = record(
        b"MGEF",
        FID_MGEF_CHA,
        build_mgef_value_mod(
            VANILLA_MGEF_CHA, "PickmansWhisperReduceCharisma", "Knife Hunger (Charisma)"
        ),
    )
    sndr_recs = collect_sndr_records()
    sndr_blob = b"".join(sndr_recs)

    # 2x QUST + SPEL + GLOB + 2x MGEF + N SNDR
    num_records = 6 + len(sndr_recs)
    tes4 = build_tes4(num_records=num_records, next_object_id=NEXT_OID)
    out = (
        tes4
        + group(b"GLOB", glob_rec)
        + group(b"MGEF", mgef_agi + mgef_cha)
        + group(b"SPEL", spel_rec)
        + group(b"QUST", main_q + player_q)
        + group(b"SNDR", sndr_blob)
    )
    ESP_PATH.write_bytes(out)
    print(f"Wrote {ESP_PATH} ({len(out)} bytes)")
    print(f"  GLOB 0x{FID_GLOB:08X} PickmansWhisperHungerActive")
    print(f"  MGEF 0x{FID_MGEF_AGI:08X} / 0x{FID_MGEF_CHA:08X} ValueMod AGI/CHA")
    print(f"  SPEL 0x{FID_SPEL:08X} Knife Hunger Ability + CTDA")
    print(f"  QUST 0x{FID_QUEST:08X} PickmansWhisperMain")
    print(f"  QUST 0x{FID_PLAYER_QUEST:08X} PickmansWhisperPlayerCombat + PlayerAlias")
    print(f"  SNDR count={len(sndr_recs)} (Desperate_Audio.txt clones)")


if __name__ == "__main__":
    main()
