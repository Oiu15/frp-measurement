from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from logic.models import global_state
from main import plc_service


class HomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._home_ev = None
        self._plc_ev = None
        self._lang_bound = False
        self._last_status = {}

    def on_kv_post(self, base_widget):
        # kv 绑定完成后调用，这时 ids 已经可用
        self.update_labels(0)
        if self._home_ev is None:
            self._home_ev = Clock.schedule_interval(self.update_labels, 0.2)
        if self._plc_ev is None:
            self._plc_ev = Clock.schedule_interval(self._poll_plc_state, 0.2)
        app = MDApp.get_running_app()
        if not self._lang_bound:
            app.bind(lang=lambda *args: self.refresh_language())
            self._lang_bound = True
        self.refresh_language()

    def on_enter(self, *args):
        ids = self.ids
        app = MDApp.get_running_app()

        # ResultCard dummy values（仅存在时才赋值）
        if "length_card" in ids:
            ids.length_card.value = "1800.0"
            ids.length_card.unit = app._("common_unit_mm")
        if "od_card" in ids:
            ids.od_card.value = "100.0"
            ids.od_card.unit = app._("common_unit_mm")
        if "id_card" in ids:
            ids.id_card.value = "95.0"
            ids.id_card.unit = app._("common_unit_mm")
        if "roundness_card" in ids:
            ids.roundness_card.value = "0.20"
            ids.roundness_card.unit = app._("common_unit_mm")
        if "straightness_card" in ids:
            ids.straightness_card.value = "0.15"
            ids.straightness_card.unit = app._("common_unit_mm_per_m")
        if "concentricity_card" in ids:
            ids.concentricity_card.value = "0.10"
            ids.concentricity_card.unit = app._("common_unit_mm")

        # InfoItems dummy values
        if "system_state_item" in ids:
            ids.system_state_item.value = app._("home_step_standby")
        if "measurement_state_item" in ids:
            ids.measurement_state_item.value = app._("status_idle")
        if "runtime_item" in ids:
            ids.runtime_item.value = "00:05:00"
        if "current_recipe_item" in ids:
            ids.current_recipe_item.value = "Demo-01"
        if "part_count_item" in ids:
            ids.part_count_item.value = "12"
        if "ng_count_item" in ids:
            ids.ng_count_item.value = "1"

        self.refresh_language()

    def update_labels(self, dt):
        ids = self.ids
        app = MDApp.get_running_app()

        status_label = ids.get("status_label")
        outer_value = ids.get("outer_value")
        inner_value = ids.get("inner_value")
        angle_value = ids.get("angle_value")
        slide_value = ids.get("slide_value")
        unit_mm = app._("common_unit_mm")
        unit_deg = app._("common_unit_deg")

        if status_label:
            code = (global_state.live.status_text or "").lower()
            status_label.text = app._(f"status_{code}")

        if outer_value:
            outer_value.text = f"{global_state.live.outer_diameter:0.2f} {unit_mm}"

        if inner_value:
            inner_value.text = f"{global_state.live.inner_diameter:0.2f} {unit_mm}"

        if angle_value:
            angle_value.text = f"{global_state.live.angle_deg:0.1f} {unit_deg}"

        if slide_value:
            slide_value.text = f"{global_state.live.slide_pos_mm:0.1f} {unit_mm}"

    def update_status_panel(self, status: dict):
        app = MDApp.get_running_app()
        status_card = self.ids.get("status_info_card")
        if not status_card:
            return
        ids = status_card.ids
        self._last_status = status

        # System
        ids.system_state_value.text = status.get("system_state", app._("status_unknown"))
        ids.system_mode_value.text = status.get("mode", app._("status_mode_auto"))
        ids.system_runtime_value.text = status.get("runtime", "00:00:00")
        ids.system_recipe_value.text = status.get("recipe", app._("status_dash"))
        ids.system_last_result_value.text = status.get("last_result", app._("status_dash"))

        # Measurement
        ids.meas_state_value.text = status.get("meas_state", app._("status_idle"))
        ids.meas_step_value.text = status.get("meas_step", app._("status_dash"))
        ids.meas_last_time_value.text = status.get("last_time", "00:00")
        ids.meas_avg_time_value.text = status.get("avg_time", "00:00")
        ids.meas_part_count_value.text = str(status.get("part_count", 0))
        ids.meas_ng_count_value.text = str(status.get("ng_count", 0))
        ids.meas_last_ng_reason_value.text = status.get("last_ng_reason", app._("status_dash"))

        # Communication（收?offline 项，构单行文本）
        offline = status.get("offline_links", [])
        if not offline:
            ids.comm_status_value.text = app._("status_all_online")
            primary = getattr(app.theme_cls, "primary_color", None) or getattr(app.theme_cls, "primaryColor", None)
            ids.comm_status_value.text_color = primary
        else:
            ids.comm_status_value.text = app._("status_offline_prefix", links=", ".join(offline))
            ids.comm_status_value.text_color = (1, 0.3, 0.3, 1)

    # —— 新增：右下角 Action 卡片的按钮逻辑 ——
    def on_action_button(self):
        """Home 界面右下角圆形按钮被点击时调用"""
        card = self.ids.home_action_card
        ring = card.ids.action_ring
        btn = card.ids.action_btn
        label = card.ids.action_label
        app = MDApp.get_running_app()

        # 简?demo 状态机：Play / Pause
        if btn.icon == "play":
            btn.icon = "pause"
            label.text = app._("home_action_moving_id")
            ring.total_steps = 8
            ring.current_step = 1  # 从第 1 格开始点亮
        elif btn.icon == "pause":
            btn.icon = "play"
            label.text = app._("home_action_paused_id")
            # 暂停时不清 current_step；真实项目里可挂起测量流程

    def refresh_language(self, *args):
        """Re-apply translated text for labels set via Python."""
        app = MDApp.get_running_app()
        ids = self.ids
        if "current_step_label" in ids:
            ids.current_step_label.text = app._("home_current_step_fmt", step=app._("home_step_standby"))
        if "next_step_label" in ids:
            ids.next_step_label.text = app._("home_next_step_fmt", step=app._("home_step_start"))
        if "state_button_text" in ids:
            ids.state_button_text.text = app._("home_state_button_start")
        # 更新 status 信息的默认值
        if hasattr(self, "update_status_panel"):
            self.update_status_panel(getattr(self, "_last_status", {}))

    def refresh_texts(self, *args):
        """Refresh dynamic texts when language changes."""
        self.update_labels(0)
        self.refresh_language()

    def _poll_plc_state(self, dt):
        """Pull latest PLC snapshot on UI thread without blocking."""
        if not plc_service:
            return
        state = plc_service.get_latest_state()
        ids = self.ids
        if "measurement_state_item" in ids:
            ids.measurement_state_item.value = "online" if state.connected else "offline"
        if "system_state_item" in ids:
            ids.system_state_item.value = state.sys_state
