# Central tag names; adjust to match PLC program.
CMD_CODE = "HMI_CMD_CODE"
CMD_SEQ = "HMI_CMD_SEQ"
CMD_REQ = "HMI_CMD_REQ"
CMD_ACK_SEQ = "HMI_CMD_ACK_SEQ"
CMD_DONE_SEQ = "HMI_CMD_DONE_SEQ"
CMD_ERR_CODE = "HMI_CMD_ERR_CODE"

SYS_MODE = "SYS_MODE"
SYS_STATE = "SYS_STATE"
AXIS0_POS = "AXIS0_POS"
AXIS1_POS = "AXIS1_POS"
ALARM_CODE = "ALARM_CODE"
COMM_HEALTH = "COMM_HEALTH"


def command_tags():
    return [CMD_CODE, CMD_SEQ, CMD_REQ, CMD_ACK_SEQ, CMD_DONE_SEQ, CMD_ERR_CODE]


def status_tags():
    return [
        SYS_MODE,
        SYS_STATE,
        AXIS0_POS,
        AXIS1_POS,
        ALARM_CODE,
        COMM_HEALTH,
    ]

