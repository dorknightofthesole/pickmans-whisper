# Rebuild PickmansWhisper.esp with:
#   QUST 0x01000800 PickmansWhisperMain (quest script only)
#   QUST 0x01000805 PickmansWhisperPlayerCombat (Player UniqueActor alias —
#     VMAD mirrors DialogueGenericPlayer: 0 quest scripts + alias script)
#   GLOB / MGEF / SPEL Knife Hunger
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP_PATH = ROOT / "Data" / "PickmansWhisper.esp"

FID_QUEST = 0x01000800
FID_SPEL = 0x01000801
FID_GLOB = 0x01000802
FID_MGEF_AGI = 0x01000803
FID_MGEF_CHA = 0x01000804
FID_PLAYER_QUEST = 0x01000805
NEXT_OID = 0x00000806

# Vanilla PeakValueMod alcohol-withdrawal MGEFs we clone DATA from
VANILLA_MGEF_AGI = 0x0010224F
VANILLA_MGEF_CHA = 0x00102251


def find_esm() -> Path:
    env = os.environ.get("FALLOUT4_ESM")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    candidates = [
        Path(r"D:\SteamLibrary\steamapps\common\Fallout 4\Data\Fallout4.esm"),
        Path(r"C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Data\Fallout4.esm"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise SystemExit(
        "Fallout4.esm not found - set FALLOUT4_ESM to the full path of Fallout4.esm"
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

    # 2x QUST + SPEL + GLOB + 2x MGEF
    tes4 = build_tes4(num_records=6, next_object_id=NEXT_OID)
    out = (
        tes4
        + group(b"GLOB", glob_rec)
        + group(b"MGEF", mgef_agi + mgef_cha)
        + group(b"SPEL", spel_rec)
        + group(b"QUST", main_q + player_q)
    )
    ESP_PATH.write_bytes(out)
    print(f"Wrote {ESP_PATH} ({len(out)} bytes)")
    print(f"  GLOB 0x{FID_GLOB:08X} PickmansWhisperHungerActive")
    print(f"  MGEF 0x{FID_MGEF_AGI:08X} / 0x{FID_MGEF_CHA:08X} ValueMod AGI/CHA")
    print(f"  SPEL 0x{FID_SPEL:08X} Knife Hunger Ability + CTDA")
    print(f"  QUST 0x{FID_QUEST:08X} PickmansWhisperMain")
    print(f"  QUST 0x{FID_PLAYER_QUEST:08X} PickmansWhisperPlayerCombat + PlayerAlias")


if __name__ == "__main__":
    main()
