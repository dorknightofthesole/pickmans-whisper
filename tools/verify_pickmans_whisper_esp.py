# Verify PickmansWhisper.esp size + Knife Hunger SPEL (0x01000801).
# Usage: python verify_pickmans_whisper_esp.py <esp-path> [expected-bytes]
import struct
import sys

SPEL_FID = 0x01000801
QUEST_FID = 0x01000800
PLAYER_COMBAT_FID = 0x01000805
SEVER_MSG_FID = 0x01000806
ESP_MIN_BYTES = 400


def find_record(data: bytes, want_type: bytes, want_fid: int) -> bool:
    off = 0
    while off + 24 <= len(data):
        typ = data[off : off + 4]
        size = struct.unpack_from("<I", data, off + 4)[0]
        if typ == b"GRUP":
            end = off + size
            coff = off + 24
            while coff + 24 <= end:
                ct = data[coff : coff + 4]
                cs = struct.unpack_from("<I", data, coff + 4)[0]
                cid = struct.unpack_from("<I", data, coff + 12)[0]
                if ct == want_type and cid == want_fid:
                    return True
                coff += 24 + cs
            off = end
        else:
            off += 24 + size
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: verify_pickmans_whisper_esp.py <esp-path> [expected-bytes]",
            file=sys.stderr,
        )
        return 1
    path = sys.argv[1]
    data = open(path, "rb").read()
    if len(data) < ESP_MIN_BYTES:
        print(f"FAIL size={len(data)} (need >= {ESP_MIN_BYTES})")
        return 2
    if len(sys.argv) >= 3:
        expect = int(sys.argv[2])
        if len(data) != expect:
            print(f"FAIL size={len(data)} expected={expect}")
            return 2
    if not find_record(data, b"SPEL", SPEL_FID):
        print(f"FAIL SPEL 0x{SPEL_FID:08X} Knife Hunger missing")
        return 3
    if not find_record(data, b"QUST", QUEST_FID):
        print(f"FAIL QUST 0x{QUEST_FID:08X} PickmansWhisperMain missing")
        return 4
    if not find_record(data, b"QUST", PLAYER_COMBAT_FID):
        print(f"FAIL QUST 0x{PLAYER_COMBAT_FID:08X} PlayerCombat missing")
        return 5
    if b"ALUA" not in data or b"PlayerAlias\x00" not in data:
        print("FAIL PlayerAlias / ALUA missing")
        return 6
    if b"PickmansWhisperPlayerAliasScript" not in data:
        print("FAIL PlayerAlias script name missing from VMAD")
        return 7
    if b"PickmansWhisperMainQuestScript" not in data:
        print("FAIL Main quest script name missing from VMAD")
        return 7
    if b"PickmansWhisperBedGiftScript" not in data:
        print("FAIL BedGift script name missing from Main quest VMAD")
        return 7
    if b"PickmansWhisperCorpseDecayScript" not in data:
        print("FAIL CorpseDecay script name missing from Main quest VMAD")
        return 7
    if b"PickmansWhisperPlayerCombat\x00" not in data:
        print("FAIL PlayerCombat EDID missing")
        return 8
    if not find_record(data, b"MESG", SEVER_MSG_FID):
        print(f"FAIL MESG 0x{SEVER_MSG_FID:08X} PW_SeverLimbMenu missing")
        return 9
    if b"PW_SeverLimbMenu\x00" not in data:
        print("FAIL PW_SeverLimbMenu EDID missing")
        return 10
    print(f"OK size={len(data)} SPEL+Main+BedGift+CorpseDecay+PlayerCombat+PlayerAlias+SeverMSG present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
