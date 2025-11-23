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

        # Step labels（旧的 Current/Next Step）
        if "current_step_label" in ids:
            ids.current_step_label.text = "Current Step: Standby"
        if "next_step_label" in ids:
            ids.next_step_label.text = "Next Step: Start Measure"

        # State button initial text（如果还在用的话）
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

    def update_status_panel(self, status: dict):
        ids = self.ids.status_info_card.ids

        # System
        ids.system_state_value.text = status.get("system_state", "Unknown")
        ids.system_mode_value.text = status.get("mode", "Auto")
        ids.system_runtime_value.text = status.get("runtime", "00:00:00")
        ids.system_recipe_value.text = status.get("recipe", "-")
        ids.system_last_result_value.text = status.get("last_result", "-")

        # Measurement
        ids.meas_state_value.text = status.get("meas_state", "Idle")
        ids.meas_step_value.text = status.get("meas_step", "-")
        ids.meas_last_time_value.text = status.get("last_time", "00:00")
        ids.meas_avg_time_value.text = status.get("avg_time", "00:00")
        ids.meas_part_count_value.text = str(status.get("part_count", 0))
        ids.meas_ng_count_value.text = str(status.get("ng_count", 0))
        ids.meas_last_ng_reason_value.text = status.get("last_ng_reason", "-")

        # Communication（收集 offline 项，构造单行文本）
        offline = status.get("offline_links", [])
        if not offline:
            ids.comm_status_value.text = "All links online"
            ids.comm_status_value.text_color = self.theme_cls.primary_color
        else:
            ids.comm_status_value.text = "Offline: " + ", ".join(offline)
            ids.comm_status_value.text_color = (1, 0.3, 0.3, 1)

    # —— 新增：右下角 Action 卡片的按钮逻辑 ——
    def on_action_button(self):
        """Home 界面右下角圆形按钮被点击时调用。"""
        card = self.ids.home_action_card
        ring = card.ids.action_ring
        btn = card.ids.action_btn
        label = card.ids.action_label

        # 简单 demo 状态机：Play / Pause
        if btn.icon == "play":
            btn.icon = "pause"
            label.text = "Moving ID Slide..."
            ring.total_steps = 8
            ring.current_step = 1  # 从第 1 格开始点亮
        elif btn.icon == "pause":
            btn.icon = "play"
            label.text = "Paused - Moving ID Slide"
            # 暂停时不动 current_step；真实项目里可挂起测量流程
