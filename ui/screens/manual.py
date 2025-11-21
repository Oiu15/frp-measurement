from kivy.properties import NumericProperty
from kivymd.uix.screen import MDScreen

from logic.models import global_state


class ManualScreen(MDScreen):
    """Manual / Jog page for all 5 motors (2 slides + 3 rotary/extension axes).

    现在还是演示 UI。
    之后你可以在 _apply_linear_jog / _apply_rotary_jog / home_* 等
    加上真正的 PLC 指令。
    """

    # 共享步距
    linear_step_mm = NumericProperty(0.5)
    rotary_step_deg = NumericProperty(5.0)

    def on_kv_post(self, base_widget):
        """kv 绑定完成后，先把 global_state 初始化各个位置量"""
        live = global_state.live

        def init_attr(name, default):
            if not hasattr(live, name):
                setattr(live, name, default)
            return getattr(live, name)

        # 保证这些属性存在
        init_attr("od_slide_mm", 0.0)  # 外径滑台
        init_attr("id_slide_mm", 0.0)  # 内径滑台（共轨）
        init_attr("id_head_mm", 0.0)  # 内径测头伸缩
        init_attr("pipe_angle_deg", 0.0)  # 主旋转
        init_attr("aux_angle_deg", 0.0)  # 从旋转

        ids = self.ids
        # 位置显示
        if "od_pos_label" in ids:
            ids.od_pos_label.text = f"{live.od_slide_mm:0.1f} mm"
        if "id_pos_label" in ids:
            ids.id_pos_label.text = f"{live.id_slide_mm:0.1f} mm"
        if "head_pos_label" in ids:
            ids.head_pos_label.text = f"{live.id_head_mm:0.1f} mm"
        if "main_angle_label" in ids:
            ids.main_angle_label.text = f"{live.pipe_angle_deg:0.1f} °"
        if "aux_angle_label" in ids:
            ids.aux_angle_label.text = f"{live.aux_angle_deg:0.1f} °"

        # 步距显示 & slider
        if "linear_step_label" in ids:
            ids.linear_step_label.text = f"{self.linear_step_mm:0.1f} mm"
        if "linear_step_slider" in ids:
            ids.linear_step_slider.value = self.linear_step_mm * 10

        if "rot_step_label" in ids:
            ids.rot_step_label.text = f"{self.rotary_step_deg:0.1f} °"
        if "rot_step_slider" in ids:
            ids.rot_step_slider.value = self.rotary_step_deg

    # ---------- 通用线性 Jog ----------

    def _apply_linear_jog(self, attr_name: str, direction: int):
        """按线性步距移动某个轴，direction = ±1"""
        live = global_state.live
        step = float(self.linear_step_mm)

        pos = getattr(live, attr_name, 0.0)
        pos += direction * step
        setattr(live, attr_name, pos)

        ids = self.ids
        mapping = {
            "od_slide_mm": "od_pos_label",
            "id_slide_mm": "id_pos_label",
            "id_head_mm": "head_pos_label",
        }
        lbl_id = mapping.get(attr_name)
        if lbl_id and lbl_id in ids:
            ids[lbl_id].text = f"{pos:0.1f} mm"

        # TODO: 这里连 PLC 直线运动命令

    # ---------- 通用旋转 Jog ----------

    def _apply_rotary_jog(self, attr_name: str, direction: int):
        """按角度步距旋转某个轴，direction = ±1"""
        live = global_state.live
        step = float(self.rotary_step_deg)

        ang = getattr(live, attr_name, 0.0)
        ang += direction * step
        setattr(live, attr_name, ang)

        ids = self.ids
        mapping = {
            "pipe_angle_deg": "main_angle_label",
            "aux_angle_deg": "aux_angle_label",
        }
        lbl_id = mapping.get(attr_name)
        if lbl_id and lbl_id in ids:
            ids[lbl_id].text = f"{ang:0.1f} °"

        # TODO: 这里连 PLC 旋转命令

    # ---------- 线性轴按钮回调 ----------

    def jog_od_neg(self):
        self._apply_linear_jog("od_slide_mm", -1)

    def jog_od_pos(self):
        self._apply_linear_jog("od_slide_mm", +1)

    def jog_id_neg(self):
        self._apply_linear_jog("id_slide_mm", -1)

    def jog_id_pos(self):
        self._apply_linear_jog("id_slide_mm", +1)

    def jog_head_in(self):
        """内径测头缩回"""
        self._apply_linear_jog("id_head_mm", -1)

    def jog_head_out(self):
        """内径测头伸出"""
        self._apply_linear_jog("id_head_mm", +1)

    def home_od(self):
        live = global_state.live
        live.od_slide_mm = 0.0
        if "od_pos_label" in self.ids:
            self.ids.od_pos_label.text = "0.0 mm"
        # TODO: PLC Home 命令

    def home_id(self):
        live = global_state.live
        live.id_slide_mm = 0.0
        if "id_pos_label" in self.ids:
            self.ids.id_pos_label.text = "0.0 mm"

    def home_head(self):
        live = global_state.live
        live.id_head_mm = 0.0
        if "head_pos_label" in self.ids:
            self.ids.head_pos_label.text = "0.0 mm"

    # ---------- 旋转轴按钮回调 ----------

    def jog_main_ccw(self):
        self._apply_rotary_jog("pipe_angle_deg", -1)

    def jog_main_cw(self):
        self._apply_rotary_jog("pipe_angle_deg", +1)

    def jog_aux_ccw(self):
        self._apply_rotary_jog("aux_angle_deg", -1)

    def jog_aux_cw(self):
        self._apply_rotary_jog("aux_angle_deg", +1)

    def home_main_rot(self):
        live = global_state.live
        live.pipe_angle_deg = 0.0
        if "main_angle_label" in self.ids:
            self.ids.main_angle_label.text = "0.0 °"

    def home_aux_rot(self):
        live = global_state.live
        live.aux_angle_deg = 0.0
        if "aux_angle_label" in self.ids:
            self.ids.aux_angle_label.text = "0.0 °"

    # ---------- 步距 slider 回调 ----------

    def on_linear_step_slider(self, value):
        self.linear_step_mm = float(value)
        if "linear_step_label" in self.ids:
            self.ids.linear_step_label.text = f"{self.linear_step_mm:0.1f} mm"

    def on_rot_step_slider(self, value):
        self.rotary_step_deg = float(value)
        if "rot_step_label" in self.ids:
            self.ids.rot_step_label.text = f"{self.rotary_step_deg:0.1f} °"
