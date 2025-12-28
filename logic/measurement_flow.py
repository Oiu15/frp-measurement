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


STEP_LABEL_KEYS = {
    MeasureStep.IDLE: "flow_step_idle",
    MeasureStep.ZERO_PROBE: "flow_step_zero_probe",
    MeasureStep.LOCATE_EDGE1: "flow_step_locate_edge1",
    MeasureStep.LOCATE_EDGE2: "flow_step_locate_edge2",
    MeasureStep.MOVE_TO_SECTION: "flow_step_move_to_section",
    MeasureStep.ROTATE_MEASURE: "flow_step_rotate_measure",
    MeasureStep.NEXT_SECTION: "flow_step_next_section",
    MeasureStep.FINISHED: "flow_step_finished",
    MeasureStep.ERROR: "flow_step_error",
}


def get_step_label(step):
    """Translate step to localized label if app is available."""
    try:
        from kivymd.app import MDApp

        app = MDApp.get_running_app()
        key = STEP_LABEL_KEYS.get(step, "flow_step_idle")
        return app._(key)
    except Exception:
        return STEP_LABEL_KEYS.get(step, "flow_step_idle")

