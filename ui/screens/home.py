from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

from logic.models import global_state


class HomeScreen(MDScreen):
    def on_kv_post(self, base_widget):
        # kv 绑定完成后调用，这时 ids 一定已经就绪
        print("HomeScreen ids after kv:", list(self.ids.keys()))
        # 这里先刷新一次
        self.update_labels(0)
        # 如需实时刷新，可开启定时器
        if not hasattr(self, "_home_ev"):
            self._home_ev = Clock.schedule_interval(self.update_labels, 0.2)

    def update_labels(self, dt):
        ids = self.ids

        status_label = ids.get("status_label")
        outer_value = ids.get("outer_value")
        inner_value = ids.get("inner_value")
        angle_value = ids.get("angle_value")
        slide_value = ids.get("slide_value")

        if status_label:
            status_label.text = global_state.live.status_text

        if outer_value:
            outer_value.text = f"{global_state.live.outer_diameter:0.2f} mm"

        if inner_value:
            inner_value.text = f"{global_state.live.inner_diameter:0.2f} mm"

        if angle_value:
            angle_value.text = f"{global_state.live.angle_deg:0.1f} °"

        if slide_value:
            slide_value.text = f"{global_state.live.slide_pos_mm:0.1f} mm"

    def on_start_button(self):
        self.manager.current = "auto"
