# Rebuild PickmansWhisper.esp with:
#   QUST 0x01000800 PickmansWhisperMain (MainQuest + BedGift + CorpseDecay + DecayWoundLab + TargetScan)
#   QUST 0x01000805 PickmansWhisperPlayerCombat (Player UniqueActor alias —
#     VMAD mirrors DialogueGenericPlayer: 0 quest scripts + alias script)
#   GLOB / MGEF / SPEL Knife Hunger
#   Proximity cloak MGEF/SPEL chain @ 0x870–0x873 retired (FormID gap kept).
#   Writes WhisperSndrIds.txt + DecayFaceArmorIds.txt
from __future__ import annotations

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
# Whisper SNDRs: ~12 Desperate + ~46 Necromantic intimacy (ends ~0x840).
# Slice I face-decal armor (slot 54): variants from NecroBaseFemaleHead*.nif
#   Base + NecroBaseFemaleHead_<Color>.nif — ARMA/ARMO pairs @ 0x850+ (2 ids each)
FID_DECAY_FACE_BASE = 0x01000850
# Keep FormID headroom for more color NIFs without reshuffling SNDR/others.
DECAY_FACE_VARIANT_RESERVE = 16
FID_HUMAN_RACE = 0x00013746  # Fallout4.esm HumanRace
# BOD2 bit 24 = biped 54 [Unnamed] — FaceGen-safe decal slot (not 32).
BOD2_SLOT_54 = struct.pack("<I", 0x01000000)
DECAY_FACE_MESH_DIR = ROOT / "Data" / "Meshes" / "PickmansWhisper" / "Decay"
DECAY_FACE_MESH_PREFIX = "NecroBaseFemaleHead"
DECAY_FACE_MESH_REL = "PickmansWhisper\\Decay\\NecroBaseFemaleHead.nif"
DECAY_FACE_MESH_STAGE = DECAY_FACE_MESH_DIR / f"{DECAY_FACE_MESH_PREFIX}.nif"
DECAY_FACE_ARMOR_IDS_PATH = (
    ROOT / "Data" / "PickmansWhisper" / "config" / "DecayFaceArmorIds.txt"
)
# Proximity cloak FormIDs retired (records no longer emitted). Gap kept so AVIFs stay @ 0x874+.
# FID_PROXIMITY_HIT_MGEF = 0x01000870
# FID_PROXIMITY_HIT_SPEL = 0x01000871
# FID_PROXIMITY_CLOAK_MGEF = 0x01000872
# FID_PROXIMITY_CLOAK_SPEL = 0x01000873
# Blade hit / kill-credit ActorValues (Variable AVIF; Main Auto Const binds).
# EDIDs match Papyrus property names (including HitWih typo — keep in sync).
FID_AV_HIT_WITH_BLADE = 0x01000874  # PW_HitWihPickmansBlade
FID_AV_CREDIT_BLADE_KILL = 0x01000875  # PW_Credit_For_PickmansBlade_Kill
FID_AV_KILL_REWARD_CHECK_TIME = 0x01000876  # PW_KillRewardCheckTime
FID_AV_TARGET_TRACKER_EXPIRATION = 0x01000877  # PW_TargetTrackerExpiration
FID_PERK_VICTIM_TRADE = 0x01000878  # PW_VictimTradeActivate (Talk + Force Trade)
FID_OTFT_EMPTY = 0x01000879  # PW_EmptyOutfit — strip default outfits for Force Trade
# NEXT_OID is the local object counter (no plugin byte); record FormIDs use 0x01…….
NEXT_OID = 0x0000087A  # == (FID_OTFT_EMPTY & 0xFFFFFF) + 1
# Variable AVIF flags/type — mirror Fallout4.esm WorkshopSnapStacks / HC_* vars.
AVIF_FLAG_VARIABLE_DEFAULT0 = 0x00040000
AVIF_TYPE_VARIABLE = 8

# Pickman's Blade detection forms (Fallout4.esm) — PlayerAlias Auto Const binds.
# LVLI 0x0022595F is the custom-item template (DoNotPlaceDirectly), not a Weapon.
FID_COMBAT_KNIFE = 0x000913CA  # WEAP Knife
# Injected by mod_melee_Knife_SerratedStealth (on Pickman's Blade) — WornHasKeyword sees this.
FID_PICKMAN_MOD_KEYWORD = 0x0013AD45  # KYWD dn_HasMeleeMod_SerratedStealth

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


def build_vmad_object_alias_property(
    prop_name: str, alias_id: int, quest_fid: int, prop_status: int = 1
) -> bytes:
    """FO4 VMAD Object property bound to a quest alias (ofmt=2 layout).

    Vanilla encodes: type=1, status, int16 0, int16 aliasId, formid quest.
    Verified against RECheckpointQuestScript.DefenderCollection / RefCollectionToManage.
    """
    data = wstring(prop_name)
    data += struct.pack("<BB", 1, prop_status & 0xFF)  # Object, status
    data += struct.pack("<hhI", 0, alias_id, quest_fid & 0xFFFFFFFF)
    return data


def build_vmad_object_form_property(
    prop_name: str, form_fid: int, prop_status: int = 1
) -> bytes:
    """FO4 VMAD Object property bound to a Form (alias id = -1)."""
    data = wstring(prop_name)
    data += struct.pack("<BB", 1, prop_status & 0xFF)
    data += struct.pack("<hhI", 0, -1, form_fid & 0xFFFFFFFF)
    return data


def build_vmad_scripts(
    script_names: list[str],
    status: int = 0,
    script_properties: dict[str, list[bytes]] | None = None,
    alias_scripts: list[tuple[int, int, str, list[bytes]]] | None = None,
) -> bytes:
    """FO4 quest VMAD with one or more scripts attached.

    script_properties: optional map of script name -> list of property blobs
    (each from build_vmad_object_alias_property, etc.).

    alias_scripts: optional list of (alias_id, quest_fid, script_name, props)
    attached to quest aliases. When present, appends FO4 quest fragment trailer
    (fragVer=3, fragCount=0) + aliasCount + nested alias VMAD (status 2).
    """
    if not script_names:
        raise ValueError("script_names must be non-empty")
    props = script_properties or {}
    data = struct.pack("<HHH", 6, 2, len(script_names))
    for script_name in script_names:
        data += wstring(script_name)
        prop_list = props.get(script_name) or []
        data += struct.pack("<BH", status & 0xFF, len(prop_list))
        for prop in prop_list:
            data += prop
    if alias_scripts:
        # Match build_vmad_alias_only / DialogueGenericPlayer fragment header.
        data += struct.pack("<BHH", 3, 0, 0)  # fragVer, unk, fragCount
        data += struct.pack("<H", len(alias_scripts))
        for alias_id, quest_fid, alias_script, alias_props in alias_scripts:
            # ofmt=2 Object union: int16 unk=0, int16 aliasId, formid quest
            # (same layout as build_vmad_object_alias_property). Packing (aliasId, 0)
            # swapped fields so ALST 2/5/6 scripts bound to the wrong target — Papyrus:
            # "Unable to bind …KillRewardScript to Active effect 0 on PickmansWhisperMain".
            # ALST 0 (PlayerCombat) worked only because both layouts are (0, 0).
            data += struct.pack("<hhI", 0, alias_id, quest_fid & 0xFFFFFFFF)
            data += struct.pack("<HHH", 6, 2, 1)
            data += wstring(alias_script)
            data += struct.pack("<BH", 2, len(alias_props))
            for prop in alias_props:
                data += prop
    return data


def build_vmad_script(
    script_name: str,
    status: int = 0,
    properties: list[bytes] | None = None,
) -> bytes:
    props = {script_name: properties} if properties else None
    return build_vmad_scripts([script_name], status=status, script_properties=props)



def build_variable_avif_payload(edid: str, full: str) -> bytes:
    """Minimal FO4 Variable ActorValue (script SetValue/GetValue tag).

    Layout matches vanilla Variable AVIFs (EDID/DESC/NAM0/AVFL/NAM1). FULL is
    optional in the ESM but kept for FO4Edit readability.
    """
    return b"".join(
        [
            field(b"EDID", zstr(edid)),
            field(b"FULL", zstr(full)),
            field(b"DESC", zstr("")),
            field(b"NAM0", struct.pack("<f", 0.0)),
            field(b"AVFL", u32(AVIF_FLAG_VARIABLE_DEFAULT0)),
            field(b"NAM1", u32(AVIF_TYPE_VARIABLE)),
        ]
    )

# Alias IDs on PickmansWhisperMain.
# ALST 0–1 were TrackedNPCs (retired). ALST 2–4 were KillRewardAlias / PendingReward (retired).
# ModConfig.txt host (Unique Actor = Player) — PickmansWhisperModConfigScript.
ALIAS_MOD_CONFIG_ID = 5
# Voice host (Unique Actor = Player) — PickmansWhisperVoiceAliasScript.
ALIAS_VOICE_ID = 6


def build_vmad_alias_only(
    alias_script: str,
    quest_fid: int,
    status: int = 2,
    properties: list[bytes] | None = None,
) -> bytes:
    """
    Match DialogueGenericPlayer:
      ver=6 ofmt=2 scriptCount=0
      fragVer=3 unk=0 fragCount=0   (no empty filename — FO4 DGP omits it)
      aliasCount=1
      object: aliasId=0, reserved=0, formID=quest
      nested: ver=6 ofmt=2 scriptCount=1 + alias script (status 2 like vanilla)
            optional Object properties (form binds use aliasId=-1)
    """
    props = properties or []
    data = struct.pack("<HHH", 6, 2, 0)  # no quest scripts
    data += struct.pack("<BHH", 3, 0, 0)  # fragVer, unk, fragCount
    data += struct.pack("<H", 1)  # aliasCount
    # ofmt=2 Object: unk=0, aliasId=0, quest formid (same as build_vmad_scripts aliases)
    data += struct.pack("<hhI", 0, 0, quest_fid & 0xFFFFFFFF)
    data += struct.pack("<HHH", 6, 2, 1)
    data += wstring(alias_script)
    data += struct.pack("<BH", status & 0xFF, len(props))
    for prop in props:
        data += prop
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


def build_mod_config_alias_fields() -> bytes:
    """UniqueActor=Player ReferenceAlias hosting PickmansWhisperModConfigScript."""
    return b"".join(
        [
            field(b"ALST", u32(ALIAS_MOD_CONFIG_ID)),
            field(b"ALID", zstr("ModConfigAlias")),
            field(b"FNAM", u32(0)),
            field(b"ALUA", u32(0x00000007)),  # Player
            field(b"VTCK", u32(0)),
            field(b"ALED", b""),
        ]
    )


def build_voice_alias_fields() -> bytes:
    """UniqueActor=Player ReferenceAlias hosting PickmansWhisperVoiceAliasScript."""
    return b"".join(
        [
            field(b"ALST", u32(ALIAS_VOICE_ID)),
            field(b"ALID", zstr("VoiceAlias")),
            field(b"FNAM", u32(0)),
            field(b"ALUA", u32(0x00000007)),  # Player
            field(b"VTCK", u32(0)),
            field(b"ALED", b""),
        ]
    )


def build_main_quest_payload() -> bytes:
    main_scripts = [
        "PickmansWhisperMainQuestScript",
        "PickmansWhisperBedGiftScript",
        "PickmansWhisperCorpseDecayScript",
        "PickmansWhisperDecayWoundLabScript",
        "PickmansWhisperVictimsScript",
        "PickmansWhisperDesperateRenameScript",
        "PickmansWhisperBuffTrackerScript",
        "PickmansWhisperBeatBeforeKillScript",
        "PickmansWhisperTargetScanScript",
        "PickmansWhisperVictimTradeScript",
    ]
    trade_perk_prop = build_vmad_object_form_property(
        "TradeActivatePerk", FID_PERK_VICTIM_TRADE
    )
    trade_outfit_prop = build_vmad_object_form_property(
        "EmptyOutfit", FID_OTFT_EMPTY
    )
    # CK-style: Main.PlayerAlias → PickmansWhisperPlayerCombat ALST 0 (script host).
    player_alias_prop = build_vmad_object_alias_property(
        "PlayerAlias", 0, FID_PLAYER_QUEST
    )
    hit_av_prop = build_vmad_object_form_property(
        "PW_HitWihPickmansBlade", FID_AV_HIT_WITH_BLADE
    )
    credit_av_prop = build_vmad_object_form_property(
        "PW_Credit_For_PickmansBlade_Kill", FID_AV_CREDIT_BLADE_KILL
    )
    mod_config_prop = build_vmad_object_alias_property(
        "ModConfigAlias", ALIAS_MOD_CONFIG_ID, FID_QUEST
    )
    voice_alias_prop = build_vmad_object_alias_property(
        "VoiceAlias", ALIAS_VOICE_ID, FID_QUEST
    )
    target_scan_main_prop = build_vmad_object_form_property(
        "MainQuest", FID_QUEST
    )
    target_tracker_expiration_prop = build_vmad_object_form_property(
        "PW_TargetTrackerExpiration", FID_AV_TARGET_TRACKER_EXPIRATION
    )
    body = b""
    body += field(b"EDID", zstr("PickmansWhisperMain"))
    body += field(
        b"VMAD",
        build_vmad_scripts(
            main_scripts,
            script_properties={
                "PickmansWhisperMainQuestScript": [
                    player_alias_prop,
                    hit_av_prop,
                    credit_av_prop,
                    target_tracker_expiration_prop,
                    mod_config_prop,
                    voice_alias_prop,
                ],
                "PickmansWhisperBeatBeforeKillScript": [
                    player_alias_prop,
                ],
                "PickmansWhisperTargetScanScript": [
                    target_scan_main_prop,
                ],
                "PickmansWhisperVictimTradeScript": [
                    trade_perk_prop,
                    trade_outfit_prop,
                ],
            },
            alias_scripts=[
                (
                    ALIAS_MOD_CONFIG_ID,
                    FID_QUEST,
                    "PickmansWhisperModConfigScript",
                    [],
                ),
                (
                    ALIAS_VOICE_ID,
                    FID_QUEST,
                    "PickmansWhisperVoiceAliasScript",
                    [],
                ),
            ],
        ),
    )
    body += field(b"FULL", zstr("PickmansWhisperMain"))
    body += field(b"DNAM", bytes.fromhex("11005C730000000000000000"))
    body += field(b"NEXT", b"")
    # ANAM = next available alias id (highest ALST + 1).
    body += field(b"ANAM", u32(ALIAS_VOICE_ID + 1))
    body += build_mod_config_alias_fields()
    body += build_voice_alias_fields()
    return body


def build_player_combat_quest_payload() -> bytes:
    body = b""
    body += field(b"EDID", zstr("PickmansWhisperPlayerCombat"))
    body += field(
        b"VMAD",
        build_vmad_alias_only(
            "PickmansWhisperPlayerAliasScript",
            FID_PLAYER_QUEST,
            status=2,
            properties=[
                build_vmad_object_form_property("CombatKnifeBase", FID_COMBAT_KNIFE),
                build_vmad_object_form_property(
                    "PickmanModKeyword", FID_PICKMAN_MOD_KEYWORD
                ),
            ],
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


def discover_decay_face_variants() -> list[tuple[str, str]]:
    """Return [(label, mesh_rel), ...] from on-disk NecroBaseFemaleHead*.nif.

    - NecroBaseFemaleHead.nif → label Base (always first when present)
    - NecroBaseFemaleHead_<Color>.nif → label Color (sorted, e.g. Black/Gray/Green)

    Labels become EDID/FULL tokens so ``help DecayFace 4`` / ``help Green 4`` work.
    """
    out: list[tuple[str, str]] = []
    base = DECAY_FACE_MESH_DIR / f"{DECAY_FACE_MESH_PREFIX}.nif"
    if base.is_file():
        out.append(("Base", f"PickmansWhisper\\Decay\\{base.name}"))
    suffix_re = re.compile(rf"^{re.escape(DECAY_FACE_MESH_PREFIX)}_([A-Za-z][A-Za-z0-9]*)\.nif$")
    colored: list[tuple[str, str]] = []
    if DECAY_FACE_MESH_DIR.is_dir():
        for nif in sorted(DECAY_FACE_MESH_DIR.glob(f"{DECAY_FACE_MESH_PREFIX}_*.nif")):
            m = suffix_re.match(nif.name)
            if not m:
                continue
            label = m.group(1)
            colored.append((label, f"PickmansWhisper\\Decay\\{nif.name}"))
    colored.sort(key=lambda t: t[0].lower())
    out.extend(colored)
    return out


def build_decay_face_arma_payload(label: str, mesh_rel: str) -> bytes:
    """ARMA — female model only, biped 54, HumanRace (Slice I guide)."""
    edid = f"PickmansWhisper_DecayFace_{label}_ARMA"
    # MO3T: CK dump from working stage-0 record (20 bytes).
    mo3t = b"\x04\x00\x00\x00" + (b"\x00" * 16)
    return b"".join(
        [
            field(b"EDID", zstr(edid)),
            field(b"BOD2", BOD2_SLOT_54),
            field(b"RNAM", u32(FID_HUMAN_RACE)),
            field(b"DNAM", b"\x00" * 12),
            field(b"MOD3", zstr(mesh_rel)),
            field(b"MO3T", mo3t),
        ]
    )


def build_decay_face_armo_payload(label: str, arma_fid: int) -> bytes:
    """ARMO — links ARMA via MODL FormID; biped 54. FULL includes color for Help."""
    edid = f"PickmansWhisper_DecayFace_{label}_ARMO"
    full = f"PW DecayFace {label}"
    return b"".join(
        [
            field(b"EDID", zstr(edid)),
            field(b"OBND", b"\x00" * 12),
            field(b"FULL", zstr(full)),
            field(b"BOD2", BOD2_SLOT_54),
            field(b"RNAM", u32(FID_HUMAN_RACE)),
            field(b"DESC", zstr("")),
            field(b"INDX", b"\x00\x00"),
            field(b"MODL", u32(arma_fid)),
            field(b"DATA", b"\x00" * 12),
            field(b"FNAM", b"\x00" * 8),
        ]
    )


def collect_decay_face_armor_records() -> tuple[list[bytes], list[bytes]]:
    """Emit ARMA/ARMO for each NecroBaseFemaleHead*.nif on disk (Base required)."""
    variants = discover_decay_face_variants()
    if not variants or variants[0][0] != "Base":
        raise SystemExit(
            f"Missing decay face NIF (need Base): {DECAY_FACE_MESH_STAGE}"
        )
    if len(variants) > DECAY_FACE_VARIANT_RESERVE:
        raise SystemExit(
            f"Too many decay-face NIFs ({len(variants)}); raise "
            f"DECAY_FACE_VARIANT_RESERVE (now {DECAY_FACE_VARIANT_RESERVE})"
        )
    armas: list[bytes] = []
    armos: list[bytes] = []
    id_lines = [
        "# Generated by tools/build_hunger_spell_esp.py — do not hand-edit.",
        "# label=armaLocalFid,armoLocalFid (plugin local FormIDs, decimal)",
        "# Biped 54 face decals — see docs/Decay_Head_Guide.md",
        "# Console: help DecayFace 4  (or help Green 4, help Black 4, …)",
    ]
    for i, (label, mesh_rel) in enumerate(variants):
        arma_fid = FID_DECAY_FACE_BASE + 2 * i
        armo_fid = FID_DECAY_FACE_BASE + 2 * i + 1
        armas.append(
            record(b"ARMA", arma_fid, build_decay_face_arma_payload(label, mesh_rel))
        )
        armos.append(
            record(b"ARMO", armo_fid, build_decay_face_armo_payload(label, arma_fid))
        )
        id_lines.append(
            f"{label}={arma_fid & 0xFFFFFF},{armo_fid & 0xFFFFFF}"
        )
        print(
            f"  ARMA 0x{arma_fid:08X} / ARMO 0x{armo_fid:08X} "
            f"DecayFace {label} -> Meshes\\{mesh_rel}"
        )
    DECAY_FACE_ARMOR_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Force LF — Windows Path.write_text() defaults to CRLF, and trailing \\r broke
    # ParsePositiveInt for every face ARMO id except a lucky last line.
    with DECAY_FACE_ARMOR_IDS_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(id_lines) + "\n")
    print(f"  Wrote {DECAY_FACE_ARMOR_IDS_PATH} ({len(armas)} variant(s))")
    return armas, armos


def build_empty_outfit_payload() -> bytes:
    """OTFT with zero items — clears ActorBase default outfit for Force Trade strip."""
    return b"".join(
        [
            field(b"EDID", zstr("PW_EmptyOutfit")),
            field(b"INAM", b""),  # no armor pieces
        ]
    )


def build_victim_trade_perk_payload() -> bytes:
    """PERK Activate / Add Activate Choice labeled Force Trade (beside Talk).

    Mirrors Fallout4.esm activate-choice layout (e.g. Cannibal / HC_FillWaterBottle):
    PRKE type=EntryPoint, DATA entry=0x0E func=0x09 tabs=2, EPFT=4 text, EPF3=0
    (additional choice, not Replace Default). Target GetDead==0 so we do not steal
    Cannibal Eat Corpse's secondary activate slot on corpses. VMAD → MainQuest.
    """
    perk_vmad = build_vmad_scripts(
        ["PickmansWhisperVictimTradePerkScript"],
        script_properties={
            "PickmansWhisperVictimTradePerkScript": [
                build_vmad_object_form_property("MainQuest", FID_QUEST),
            ],
        },
    )
    # Vanilla GetDead == 0 (func 0x2E) — from WastelandWhisperer / Intimidation PERKs.
    ctda_get_dead_eq_0 = bytes.fromhex(
        "00c0c967000000002e00000000000000000000000000000000000000ffffffff"
    )
    parts = [
        field(b"EDID", zstr("PW_VictimTradeActivate")),
        field(b"VMAD", perk_vmad),
        field(b"FULL", zstr("Pickman's Whisper Trade")),
        # Trait=0, level=0, ranks=1, playable=1, hidden=0
        field(b"DATA", bytes.fromhex("0000010100")),
        # Entry Point rank0 priority0
        field(b"PRKE", bytes.fromhex("020000")),
        # Activate (0x0E) / Add Activate Choice (0x09) / 2 condition tabs
        field(b"DATA", bytes.fromhex("0e0902")),
        field(b"PRKC", bytes.fromhex("00")),  # Perk Owner tab (empty)
        field(b"PRKC", bytes.fromhex("01")),  # Target tab
        field(b"CTDA", ctda_get_dead_eq_0),  # living only — leave corpses to Cannibal
        field(b"EPFT", bytes.fromhex("04")),  # Activate text
        field(b"EPFB", bytes.fromhex("0000")),
        field(b"EPF2", zstr("Force Trade")),
        field(b"EPF3", bytes.fromhex("0000")),  # not Replace Default / not Run Immediately
        field(b"PRKF", b""),
    ]
    return b"".join(parts)


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
    perk_trade = record(
        b"PERK", FID_PERK_VICTIM_TRADE, build_victim_trade_perk_payload()
    )
    otft_empty = record(b"OTFT", FID_OTFT_EMPTY, build_empty_outfit_payload())
    avif_hit = record(
        b"AVIF",
        FID_AV_HIT_WITH_BLADE,
        build_variable_avif_payload(
            "PW_HitWihPickmansBlade", "Hit With Pickman's Blade"
        ),
    )
    avif_credit = record(
        b"AVIF",
        FID_AV_CREDIT_BLADE_KILL,
        build_variable_avif_payload(
            "PW_Credit_For_PickmansBlade_Kill", "Credit For Pickman's Blade Kill"
        ),
    )
    avif_reward_check = record(
        b"AVIF",
        FID_AV_KILL_REWARD_CHECK_TIME,
        build_variable_avif_payload(
            "PW_KillRewardCheckTime", "Kill Reward Check Time"
        ),
    )
    avif_tracker_expiration = record(
        b"AVIF",
        FID_AV_TARGET_TRACKER_EXPIRATION,
        build_variable_avif_payload(
            "PW_TargetTrackerExpiration", "Target Tracker Expiration"
        ),
    )
    sndr_recs = collect_sndr_records()
    sndr_blob = b"".join(sndr_recs)
    arma_recs, armo_recs = collect_decay_face_armor_records()
    arma_blob = b"".join(arma_recs)
    armo_blob = b"".join(armo_recs)

    # 2x QUST + SPEL + GLOB + 2x MGEF hunger + MESG + PERK + OTFT + 4 AVIF + N SNDR + N ARMA + N ARMO
    # (proximity cloak MGEF/SPEL chain retired)
    num_records = 13 + len(sndr_recs) + len(arma_recs) + len(armo_recs)
    tes4 = build_tes4(num_records=num_records, next_object_id=NEXT_OID)
    out = (
        tes4
        + group(b"GLOB", glob_rec)
        + group(
            b"AVIF",
            avif_hit + avif_credit + avif_reward_check + avif_tracker_expiration,
        )
        + group(b"MGEF", mgef_agi + mgef_cha)
        + group(b"SPEL", spel_rec)
        + group(b"MESG", msg_rec)
        + group(b"PERK", perk_trade)
        + group(b"OTFT", otft_empty)
        + group(b"ARMA", arma_blob)
        + group(b"ARMO", armo_blob)
        + group(b"QUST", main_q + player_q)
        + group(b"SNDR", sndr_blob)
    )
    ESP_PATH.write_bytes(out)
    print(f"Wrote {ESP_PATH} ({len(out)} bytes)")
    print(f"  GLOB 0x{FID_GLOB:08X} PickmansWhisperHungerActive")
    print(f"  MGEF 0x{FID_MGEF_AGI:08X} / 0x{FID_MGEF_CHA:08X} ValueMod AGI/CHA")
    print(f"  SPEL 0x{FID_SPEL:08X} Knife Hunger Ability + CTDA")
    print(f"  MESG 0x{FID_SEVER_MSG:08X} PW_SeverLimbMenu")
    print(f"  PERK 0x{FID_PERK_VICTIM_TRADE:08X} PW_VictimTradeActivate (Force Trade, living)")
    print(f"  OTFT 0x{FID_OTFT_EMPTY:08X} PW_EmptyOutfit")
    print("  Proximity cloak MGEF/SPEL chain retired (0x870-0x873 gap)")
    print(
        f"  AVIF 0x{FID_AV_HIT_WITH_BLADE:08X} PW_HitWihPickmansBlade / "
        f"0x{FID_AV_CREDIT_BLADE_KILL:08X} PW_Credit_For_PickmansBlade_Kill / "
        f"0x{FID_AV_KILL_REWARD_CHECK_TIME:08X} PW_KillRewardCheckTime / "
        f"0x{FID_AV_TARGET_TRACKER_EXPIRATION:08X} PW_TargetTrackerExpiration"
    )
    print(f"  ARMA/ARMO decay face variants={len(arma_recs)} (biped 54)")
    print(
        f"  QUST 0x{FID_QUEST:08X} PickmansWhisperMain + VoiceAlias ALST {ALIAS_VOICE_ID} "
        f"(TrackedNPCs alias retired)"
    )
    print(f"  QUST 0x{FID_PLAYER_QUEST:08X} PickmansWhisperPlayerCombat + PlayerAlias")
    print(f"  SNDR count={len(sndr_recs)} (Desperate + Intimacy Start/End maps)")


if __name__ == "__main__":
    main()
