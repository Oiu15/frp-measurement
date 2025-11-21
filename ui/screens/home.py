from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

from logic.models import global_state


class HomeScreen(MDScreen):
    def on_kv_post(self, base_widget):
        # kv 绑定完成后调用，这时 ids 已经可用
        self.update_labels(0)
        if not hasattr(self, "_home_ev"):
            self._home_ev = Clock.schedule_interval(self.update_labels, 0.2)

    def on_enter(self, *args):
        ids = self.ids

        # ResultCard dummy values
        if "length_card" in ids:
            ids.length_card.value = "1800.0"
            ids.length_card.unit = "mm"
        if "od_card" in ids:
            ids.od_card.value = "100.0"
            ids.od_card.unit = "mm"
        if "id_card" in ids:
            ids.id_card.value = "95.0"
            ids.id_card.unit = "mm"
        if "roundness_card" in ids:
            ids.roundness_card.value = "0.20"
            ids.roundness_card.unit = "mm"
        if "straightness_card" in ids:
            ids.straightness_card.value = "0.15"
            ids.straightness_card.unit = "mm/m"
        if "concentricity_card" in ids:
            ids.concentricity_card.value = "0.10"
            ids.concentricity_card.unit = "mm"

        # InfoItems dummy values
        if "system_state_item" in ids:
            ids.system_state_item.value = "Standby"
        if "measurement_state_item" in ids:
            ids.measurement_state_item.value = "Idle"
        if "runtime_item" in ids:
            ids.runtime_item.value = "00:05:00"
        if "current_recipe_item" in ids:
            ids.current_recipe_item.value = "Demo-01"
        if "part_count_item" in ids:
            ids.part_count_item.value = "12"
        if "ng_count_item" in ids:
            ids.ng_count_item.value = "1"

        # Step labels
        if "current_step_label" in ids:
            ids.current_step_label.text = "Current Step: Standby"
        if "next_step_label" in ids:
            ids.next_step_label.text = "Next Step: Start Measure"

        # State button initial text
        if "state_button_text" in ids:
            ids.state_button_text.text = "Start"

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

    def on_state_button_pressed(self):
        print(">>> state button pressed")

        # 获取按钮文字控件，而不是按钮本体
        lbl = self.ids.get("state_button_text")
        if not lbl:
            print("ERROR: state_button_text id not found")
            return

        current = (lbl.text or "").strip()

        if current == "Start":
            lbl.text = "Running"
        elif current == "Running":
            lbl.text = "Paused"
        else:
            lbl.text = "Start"

        print(f">>> state changed to: {lbl.text}")
