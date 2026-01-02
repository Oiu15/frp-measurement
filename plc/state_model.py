from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CommandWindow:
    code: int = 0
    seq: int = 0
    req: int = 0
    ack_seq: int = 0
    done_seq: int = 0
    err_code: int = 0


@dataclass
class AxisStatus:
    pos: float = 0.0


@dataclass
class PlcState:
    connected: bool = False

    # items for eip test
    heartbeat: bool = False
    cycle_cnt: int = 0
    estop_active: bool = False
    en_req_local: bool = False
    jog_up_local: bool = False
    jog_dn_local: bool = False
    abs1_local: bool = False
    abs2_local: bool = False

    cmd: CommandWindow = field(default_factory=CommandWindow)
    sys_mode: str = "unknown"
    sys_state: str = "idle"
    axis0: AxisStatus = field(default_factory=AxisStatus)
    axis1: AxisStatus = field(default_factory=AxisStatus)
    alarm_code: int = 0
    comm_health: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, tags: Dict[str, Any], connected: bool = False):
        return cls(
            connected=connected,
            heartbeat=bool(tags.get("PLC_HEARTBEAT_1HZ", False)),
            cycle_cnt=int(tags.get("PLC_CYCLE_CNT", 0) or 0),
            estop_active=bool(tags.get("PLC_ESTOP_ACTIVE", False)),
            en_req_local=bool(tags.get("PLC_EN_REQ_LOCAL", False)),
            jog_up_local=bool(tags.get("PLC_JOG_UP_LOCAL", False)),
            jog_dn_local=bool(tags.get("PLC_JOG_DN_LOCAL", False)),
            abs1_local=bool(tags.get("PLC_ABS1_LOCAL", False)),
            abs2_local=bool(tags.get("PLC_ABS2_LOCAL", False)),
            cmd=CommandWindow(
                code=int(tags.get("HMI_CMD_CODE", 0) or 0),
                seq=int(tags.get("HMI_CMD_SEQ", 0) or 0),
                req=int(tags.get("HMI_CMD_REQ", 0) or 0),
                ack_seq=int(tags.get("HMI_CMD_ACK_SEQ", 0) or 0),
                done_seq=int(tags.get("HMI_CMD_DONE_SEQ", 0) or 0),
                err_code=int(tags.get("HMI_CMD_ERR_CODE", 0) or 0),
            ),
            sys_mode=str(tags.get("SYS_MODE", "unknown")),
            sys_state=str(tags.get("SYS_STATE", "idle")),
            axis0=AxisStatus(pos=float(tags.get("AXIS0_POS", 0.0) or 0.0)),
            axis1=AxisStatus(pos=float(tags.get("AXIS1_POS", 0.0) or 0.0)),
            alarm_code=int(tags.get("ALARM_CODE", 0) or 0),
            comm_health=int(tags.get("COMM_HEALTH", 0) or 0),
            raw=tags,
        )
