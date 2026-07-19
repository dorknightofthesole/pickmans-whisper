# Rebuild PickmansWhisper.esp with:
#   QUST 0x01000800 PickmansWhisperMain (MainQuest + BedGift scripts)
#   QUST 0x01000805 PickmansWhisperPlayerCombat (Player UniqueActor alias —
#     VMAD mirrors DialogueGenericPlayer: 0 quest scripts + alias script)
#   GLOB / MGEF / SPEL Knife Hunger
#   SNDR clones for Desperate_Audio.txt + E5 Intimacy_*_Audio.txt starting at
#     0x01000807 — EDID PW_Whisper_<SanitizedStem>, path Sound\PickmansWhisper\<rel>
#   Writes Data/PickmansWhisper/config/WhisperSndrIds.txt (mapKey=localFid)
import os
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ESP_PATH = ROOT / "Data" / "PickmansWhisper.esp"
DESPERATE_AUDIO = ROOT / "Data" / "PickmansWhisper" / "config" / "Desperate_Audio.txt"
INTIMACY_START_AUDIO = (
    ROOT / "Data" / "PickmansWhisper" / "config" / "necromantic" / "Intimacy_Start_Audio.txt"
)
INTIMACY_END_AUDIO = (
    ROOT / "Data" / "PickmansWhisper" / "config" / "necromantic" / "Intimacy_End_Audio.txt"
)
MOD_CONFIG = ROOT / "Data" / "PickmansWhisper" / "config" / "ModConfig.txt"
SOUND_DIR = ROOT / "Data" / "Sound" / "PickmansWhisper"
SNDR_IDS_PATH = ROOT / "Data" / "PickmansWhisper" / "config" / "WhisperSndrIds.txt"
# namedIntimacyAudio retired (E5 banks). namedKillAudio still optional.
MOD_CONFIG_AUDIO_KEYS = ("namedKillAudio",)

FID_QUEST = 0x01000800
FID_SPEL = 0x01000801
FID_GLOB = 0x01000802
FID_MGEF_AGI = 0x01000803
FID_MGEF_CHA = 0x01000804
FID_PLAYER_QUEST = 0x01000805
FID_SEVER_MSG = 0x01000806  # PW_SeverLimbMenu (Slice F)
FID_WHISPER_BASE = 0x01000807
# Whisper SNDRs: ~12 Desperate + ~46 Necromantic intimacy; leave headroom.
NEXT_OID = 0x00000850

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


def build_vmad_scripts(script_names: list[str], status: int = 0) -> bytes:
    """FO4 quest VMAD with one or more scripts attached (no properties)."""
    if not script_names:
        raise ValueError("script_names must be non-empty")
    data = struct.pack("<HHH", 6, 2, len(script_names))
    for script_name in script_names:
        data += wstring(script_name)
        data += struct.pack("<BH", status & 0xFF, 0)
    return data


def build_vmad_script(script_name: str, status: int = 0) -> bytes:
    return build_vmad_scripts([script_name], status=status)


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
    body += field(
        b"VMAD",
        build_vmad_scripts(
            [
                "PickmansWhisperMainQuestScript",
                "PickmansWhisperBedGiftScript",
            ]
        ),
    )
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
    # utf-8-sig strips a leading BOM so "# comment" is not treated as a map key.
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def normalize_audio_map_key(filename: str) -> str:
    """Map line as stored in *_Audio.txt / WhisperSndrIds (forward slashes)."""
    name = filename.strip().replace("\\", "/")
    if not name.lower().endswith(".xwm"):
        raise SystemExit(f"Audio map entry must be .xwm, got {filename!r}")
    return name


def stem_from_xwm(filename: str) -> str:
    name = normalize_audio_map_key(filename)
    return name[: -len(".xwm")]


def edid_stem_from_map_key(filename: str) -> str:
    """EDID-safe stem: path seps / hyphens / dots → underscore."""
    stem = stem_from_xwm(filename)
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", stem)
    safe = re.sub(r"_+", "_", safe).strip("_")
    if not safe:
        raise SystemExit(f"Audio map entry yields empty EDID stem: {filename!r}")
    return safe


def build_whisper_sndr_payload(edid_stem: str, map_key: str) -> bytes:
    """Standard one-shot SNDR cloned from golden EndIt field layout."""
    edid = f"PW_Whisper_{edid_stem}"
    rel = map_key.replace("/", "\\")
    anam = rf"Sound\PickmansWhisper\{rel}"
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


def parse_modconfig_audio_files() -> list[str]:
    """Optional namedKillAudio .xwm keys from ModConfig.txt."""
    if not MOD_CONFIG.is_file():
        return []
    out: list[str] = []
    for raw in MOD_CONFIG.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if key not in MOD_CONFIG_AUDIO_KEYS or not val:
            continue
        key_norm = normalize_audio_map_key(val)
        if key_norm not in out:
            out.append(key_norm)
    return out


def build_sever_limb_menu_payload() -> bytes:
    """MESG message-box with limb buttons. DNAM bit0 = Message Box.

    Field order matches working FO4 mod menus (AFT/CAM/etc): EDID DESC FULL
    INAM DNAM ITXT… — do NOT emit TNAM (vanilla/mod boxes that work omit it).
    """
    buttons = (
        "Head",
        "Left Arm",
        "Right Arm",
        "Left Leg",
        "Right Leg",
        "Cancel",
    )
    parts = [
        field(b"EDID", zstr("PW_SeverLimbMenu")),
        field(b"DESC", zstr("Butcher which part?")),
        field(b"FULL", zstr("Pickmans Whisper - Butcher")),
        field(b"INAM", u32(0)),
        field(b"DNAM", u32(0x00000001)),  # Message Box
    ]
    for label in buttons:
        parts.append(field(b"ITXT", zstr(label)))
    return b"".join(parts)


def collect_sndr_records() -> list[bytes]:
    """Emit SNDRs for Desperate + E5 intimacy maps + optional ModConfig namedKillAudio."""
    files: list[str] = []
    seen: set[str] = set()

    def add_map(path: Path) -> None:
        for raw in parse_audio_map(path):
            key = normalize_audio_map_key(raw)
            if key in seen:
                continue
            xwm_path = SOUND_DIR / Path(*key.split("/"))
            if not xwm_path.is_file():
                raise SystemExit(f"Missing xwm for SNDR clone: {xwm_path}")
            files.append(key)
            seen.add(key)

    add_map(DESPERATE_AUDIO)
    if len(files) < 1:
        raise SystemExit(f"{DESPERATE_AUDIO} has no usable .xwm rows")
    add_map(INTIMACY_START_AUDIO)
    add_map(INTIMACY_END_AUDIO)
    for extra in parse_modconfig_audio_files():
        if extra in seen:
            continue
        xwm_path = SOUND_DIR / Path(*extra.split("/"))
        if not xwm_path.is_file():
            raise SystemExit(
                f"ModConfig audio key set but missing xwm for SNDR clone: {xwm_path}"
            )
        files.append(extra)
        seen.add(extra)

    out: list[bytes] = []
    id_lines = [
        "# Generated by tools/build_hunger_spell_esp.py — do not hand-edit.",
        "# mapKey=.xwm (relative under Sound/PickmansWhisper) → local FormID decimal.",
    ]
    for i, map_key in enumerate(files):
        edid_stem = edid_stem_from_map_key(map_key)
        xwm_path = SOUND_DIR / Path(*map_key.split("/"))
        if not xwm_path.is_file():
            raise SystemExit(f"Missing xwm for SNDR clone: {xwm_path}")
        fid = FID_WHISPER_BASE + i
        local_fid = fid & 0xFFFFFF
        out.append(record(b"SNDR", fid, build_whisper_sndr_payload(edid_stem, map_key)))
        id_lines.append(f"{map_key}={local_fid}")
        print(
            f"  SNDR 0x{fid:08X} PW_Whisper_{edid_stem} -> Sound\\PickmansWhisper\\{map_key.replace('/', chr(92))}"
        )
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
    msg_rec = record(b"MESG", FID_SEVER_MSG, build_sever_limb_menu_payload())
    sndr_recs = collect_sndr_records()
    sndr_blob = b"".join(sndr_recs)

    # 2x QUST + SPEL + GLOB + 2x MGEF + MESG + N SNDR
    num_records = 7 + len(sndr_recs)
    tes4 = build_tes4(num_records=num_records, next_object_id=NEXT_OID)
    out = (
        tes4
        + group(b"GLOB", glob_rec)
        + group(b"MGEF", mgef_agi + mgef_cha)
        + group(b"SPEL", spel_rec)
        + group(b"MESG", msg_rec)
        + group(b"QUST", main_q + player_q)
        + group(b"SNDR", sndr_blob)
    )
    ESP_PATH.write_bytes(out)
    print(f"Wrote {ESP_PATH} ({len(out)} bytes)")
    print(f"  GLOB 0x{FID_GLOB:08X} PickmansWhisperHungerActive")
    print(f"  MGEF 0x{FID_MGEF_AGI:08X} / 0x{FID_MGEF_CHA:08X} ValueMod AGI/CHA")
    print(f"  SPEL 0x{FID_SPEL:08X} Knife Hunger Ability + CTDA")
    print(f"  MESG 0x{FID_SEVER_MSG:08X} PW_SeverLimbMenu")
    print(f"  QUST 0x{FID_QUEST:08X} PickmansWhisperMain")
    print(f"  QUST 0x{FID_PLAYER_QUEST:08X} PickmansWhisperPlayerCombat + PlayerAlias")
    print(f"  SNDR count={len(sndr_recs)} (Desperate + Intimacy Start/End maps)")


if __name__ == "__main__":
    main()
