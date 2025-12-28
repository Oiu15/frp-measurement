from dataclasses import dataclass
from typing import Any, Dict
from . import tag_map


@dataclass
class CommandAck:
    acked: bool
    done: bool
    err_code: int


def build_command(cmd_code: int, seq: int, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload or {}
    cmd = {
        tag_map.CMD_CODE: int(cmd_code),
        tag_map.CMD_SEQ: int(seq),
        tag_map.CMD_REQ: 1,
    }
    cmd.update(payload)
    return cmd


def interpret_ack(raw: Dict[str, Any], seq: int) -> CommandAck:
    ack_seq = int(raw.get(tag_map.CMD_ACK_SEQ, 0) or 0)
    done_seq = int(raw.get(tag_map.CMD_DONE_SEQ, 0) or 0)
    err = int(raw.get(tag_map.CMD_ERR_CODE, 0) or 0)
    return CommandAck(
        acked=ack_seq == seq,
        done=done_seq == seq and err == 0,
        err_code=err if done_seq == seq else 0,
    )

