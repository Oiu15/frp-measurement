from enum import Enum, auto


class MeasureStep(Enum):
    IDLE = auto()
    ZERO_PROBE = auto()
    LOCATE_EDGE1 = auto()
    LOCATE_EDGE2 = auto()
    MOVE_TO_SECTION = auto()
    ROTATE_MEASURE = auto()
    NEXT_SECTION = auto()
    FINISHED = auto()
    ERROR = auto()


STEP_LABELS = {
    MeasureStep.IDLE: "Idle",
    MeasureStep.ZERO_PROBE: "Zero Probe",
    MeasureStep.LOCATE_EDGE1: "Locate Edge 1",
    MeasureStep.LOCATE_EDGE2: "Locate Edge 2",
    MeasureStep.MOVE_TO_SECTION: "Move To Section",
    MeasureStep.ROTATE_MEASURE: "Rotate & Acquire",
    MeasureStep.NEXT_SECTION: "Next Section",
    MeasureStep.FINISHED: "Finished",
    MeasureStep.ERROR: "Error",
}
