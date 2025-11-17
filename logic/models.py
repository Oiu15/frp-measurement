from dataclasses import dataclass, field


@dataclass
class LiveData:
    outer_diameter: float = 0.0
    inner_diameter: float = 0.0
    angle_deg: float = 0.0
    slide_pos_mm: float = 0.0
    status_text: str = "READY"


@dataclass
class SystemState:
    live: LiveData = field(default_factory=LiveData)
    current_step: str = "Idle"
    servo_x_on: bool = False
    servo_y_on: bool = False
    servo_r_on: bool = False
    alarm: bool = False


global_state = SystemState()
