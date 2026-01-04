# eip_tag_rw.py
# 依赖: pip install pycomm3
# 用途: 对信捷 XDH EtherNet/IP 显式标签(0x4C/0x4D)进行读写（Tag 方案落地）
import struct
import time
from pycomm3 import CIPDriver

PLC_IP = "192.168.6.6"  # 你的 PLC IP

# 这些名字要和 PLC “全局变量表”里的名称完全一致（区分大小写）
CMD_TAG = "CMD_WORD"  # 绑定 D100，网络状态=公开
ST_TAGS = ["PLC_CYCLE_CNT", "PLC_HEARTBEAT_1HZ", "PLC_STATE"]

# Rockwell/通用CIP里常见：Symbol Object
SYMBOL_CLASS = 0x6B
SYMBOL_INSTANCE = 0x01


def _symbol_segment(tag: str) -> bytes:
    """
    ANSI Extended Symbol Segment (0x91)
    格式: 0x91, len, ascii_bytes, pad(0x00 if len is odd)
    """
    b = tag.encode("ascii")  # 手册也说明标签暂不支持中文
    if len(b) > 64:
        raise ValueError("Tag name too long (>64 bytes)")
    seg = bytes([0x91, len(b)]) + b
    if len(b) % 2 == 1:
        seg += b"\x00"
    return seg


def read_tag(plc: CIPDriver, tag: str, elements: int = 1):
    """
    Service 0x4C: Read Tag
    Request data: UINT16 elements
    Response data: UINT16 type_code + payload
    """
    resp = plc.generic_message(
        service=0x4C,
        class_code=SYMBOL_CLASS,
        instance=SYMBOL_INSTANCE,
        # 关键：把 Tag 名作为附加路径段（符号段）
        request_path=_symbol_segment(tag),
        request_data=struct.pack("<H", elements),
        connected=False,  # 显式读写建议走 Unconnected 更稳
        unconnected_send=True,
    )
    if resp is None or resp.error:
        raise RuntimeError(f"ReadTag failed: {getattr(resp, 'error', resp)}")

    data = resp.value
    if not isinstance(data, (bytes, bytearray)):
        raise RuntimeError(f"Unexpected response type: {type(data)} {data!r}")
    if len(data) < 2:
        raise RuntimeError(f"ReadTag response too short: {data.hex()}")

    type_code = struct.unpack_from("<H", data, 0)[0]
    payload = data[2:]
    return type_code, payload, data


def write_tag(
    plc: CIPDriver, tag: str, type_code: int, raw_payload: bytes, elements: int = 1
):
    """
    Service 0x4D: Write Tag
    Request data: UINT16 type_code + UINT16 elements + payload
    """
    req = struct.pack("<HH", type_code, elements) + raw_payload
    resp = plc.generic_message(
        service=0x4D,
        class_code=SYMBOL_CLASS,
        instance=SYMBOL_INSTANCE,
        request_path=_symbol_segment(tag),
        request_data=req,
        connected=False,
        unconnected_send=True,
    )
    if resp is None or resp.error:
        raise RuntimeError(f"WriteTag failed: {getattr(resp, 'error', resp)}")
    return True


def u16_from_payload(payload: bytes) -> int:
    if len(payload) < 2:
        raise ValueError(f"payload too short for UINT16: {payload.hex()}")
    return struct.unpack_from("<H", payload, 0)[0]


def u16_to_payload(v: int) -> bytes:
    return struct.pack("<H", v & 0xFFFF)


def main():
    with CIPDriver(PLC_IP) as plc:
        # 1) 先读 CMD_WORD，拿 type_code
        tc, pl, raw = read_tag(plc, CMD_TAG, 1)
        print(f"[READ] {CMD_TAG}: type_code=0x{tc:04X}, raw={raw.hex()}")
        cur = u16_from_payload(pl)
        print(f"       value={cur} (0x{cur:04X})")

        # 2) 写入 bit0=1（脉冲/保持由你PLC逻辑决定）
        cmd_word = 0x0001
        write_tag(plc, CMD_TAG, tc, u16_to_payload(cmd_word), 1)
        print(f"[WRITE] {CMD_TAG} <= 0x{cmd_word:04X}")

        time.sleep(0.2)

        # 3) 读回确认
        tc2, pl2, raw2 = read_tag(plc, CMD_TAG, 1)
        v2 = u16_from_payload(pl2)
        print(
            f"[READBACK] {CMD_TAG}: type_code=0x{tc2:04X}, raw={raw2.hex()}, value={v2} (0x{v2:04X})"
        )

        # 4) 读状态
        for t in ST_TAGS:
            tct, plt, rawt = read_tag(plc, t, 1)
            vv = u16_from_payload(plt)
            print(
                f"[READ] {t}: type_code=0x{tct:04X}, value={vv} (0x{vv:04X}), raw={rawt.hex()}"
            )


if __name__ == "__main__":
    main()
