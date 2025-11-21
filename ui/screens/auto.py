import math
import random

from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

from core import frp_core
from logic.models import global_state


class AutoMeasureScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # demo data + timers
        self._t = 0.0
        self._ods = []
        self._ids = []
        self._auto_ev = None

        # step highlighting
        self._current_step = 1  # 1~7
        self._step_ev = None
        self._step_demo_ev = None

    def _restart_demo(self):
        """Reset demo state and timers."""
        # cancel previous timers
        for ev_name in ("_auto_ev", "_step_ev", "_step_demo_ev"):
            ev = getattr(self, ev_name, None)
            if ev is not None:
                ev.cancel()
                setattr(self, ev_name, None)

        # reset core + local data
        frp_core.reset()
        self._t = 0.0
        self._ods.clear()
        self._ids.clear()

        # start from step 1
        self._current_step = 1
        global_state.live.current_step = self._current_step

        # start timers
        self._auto_ev = Clock.schedule_interval(self._demo_measure_loop, 0.05)
        self._step_ev = Clock.schedule_interval(self._update_step_indicator, 0.2)
        self._step_demo_ev = Clock.schedule_interval(self._demo_step_advance, 1.0)
        self._update_step_indicator(0)

    def start_auto(self, *args):
        """Called by UI (e.g., Start button) to begin the auto demo."""
        self._restart_demo()

    # ---------- demo state machine ----------

    def _demo_step_advance(self, dt):
        """Advance fake steps each second; jump to Result on finish."""
        if self._current_step < 7:
            self._current_step += 1
            global_state.live.current_step = self._current_step
        else:
            self._finish_auto_sequence()
            if self._step_demo_ev is not None:
                self._step_demo_ev.cancel()
                self._step_demo_ev = None
            return False
        return True

    # ---------- step highlight ----------

    def _get_current_step_index(self) -> int:
        return int(self._current_step)

    def _update_step_indicator(self, dt):
        current = self._get_current_step_index()

        for i in range(1, 8):
            lbl = self.ids.get(f"step_lbl_{i}")
            if not lbl:
                continue

            if i == current:
                lbl.theme_text_color = "Custom"
                lbl.text_color = (1, 1, 0, 1)  # yellow highlight
            else:
                lbl.theme_text_color = "Secondary"

    # ---------- auto measurement + plot ----------

    def _demo_measure_loop(self, dt):
        """Simulate rotation sampling + feed core + update UI/plot."""
        self._t += 5.0
        angle = self._t % 360

        od = 152.0 + 0.2 * math.sin(math.radians(angle)) + random.uniform(-0.02, 0.02)
        id_ = 76.0 + 0.05 * math.cos(math.radians(angle)) + random.uniform(-0.01, 0.01)

        global_state.live.outer_diameter = od
        global_state.live.inner_diameter = id_
        global_state.live.angle_deg = angle

        frp_core.add_sample(angle, od, id_)

        ids = self.ids
        if "auto_outer_value" in ids:
            ids.auto_outer_value.text = f"{od:0.2f} mm"
        if "auto_inner_value" in ids:
            ids.auto_inner_value.text = f"{id_:0.2f} mm"
        if "auto_angle" in ids:
            ids.auto_angle.text = f"{angle:0.1f} °"

        self._ods.append(od)
        self._ids.append(id_)

        max_points = 200
        if len(self._ods) > max_points:
            self._ods.pop(0)
            self._ids.pop(0)

        plot = ids.get("live_plot")
        if plot:
            plot.update_data(
                self._ods,
                self._ids,
                y_min=151.5,
                y_max=152.5,
                inner_y_min=75.8,
                inner_y_max=76.2,
            )

    # ---------- finish ----------

    def _finish_auto_sequence(self):
        """Compute once, show Result, stop timers (demo)."""
        res = frp_core.compute()
        result_screen = self.manager.get_screen("result")
        result_screen.show_result(res)
        self.manager.current = "result"

        if self._auto_ev is not None:
            self._auto_ev.cancel()
            self._auto_ev = None
        if self._step_ev is not None:
            self._step_ev.cancel()
            self._step_ev = None

    def on_leave(self, *args):
        """Stop demo timers when leaving Auto."""
        for ev_name in ("_auto_ev", "_step_ev", "_step_demo_ev"):
            ev = getattr(self, ev_name, None)
            if ev is not None:
                ev.cancel()
                setattr(self, ev_name, None)
