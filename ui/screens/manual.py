from kivy.properties import NumericProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from logic.models import global_state
from main import plc_service

CMD_GREEN_BUTTON = 1
CMD_AXIS0_MOVE = 100


class ManualScreen(MDScreen):
    """Manual / Jog page for all 5 motors (2 slides + 3 rotary/extension axes).

    ���ڻ�����ʾ UI��֮��������� _apply_linear_jog / _apply_rotary_jog / home_* ��
    ���������� PLC ָ�
    """

    # �������
    linear_step_mm = NumericProperty(0.5)
    rotary_step_deg = NumericProperty(5.0)

    def on_kv_post(self, base_widget):
        """kv ����ɺ��Ȱ� global_state ��ʼ������λ����"""
        live = global_state.live

        def init_attr(name, default):
            if not hasattr(live, name):
                setattr(live, name, default)
            return getattr(live, name)

        # ��֤��Щ���Դ���
        init_attr("od_slide_mm", 0.0)  # �⾶��̨
        init_attr("id_slide_mm", 0.0)  # �ھ���̨�����죩
        init_attr("id_head_mm", 0.0)  # �ھ���ͷ����
        init_attr("pipe_angle_deg", 0.0)  # ����ת
        init_attr("aux_angle_deg", 0.0)  # ����ת
        ids = self.ids
        # λ����ʾ
        if "od_pos_label" in ids:
            unit = MDApp.get_running_app()._("common_unit_mm")
            ids.od_pos_label.text = f"{live.od_slide_mm:0.1f} {unit}"
        if "id_pos_label" in ids:
            unit = MDApp.get_running_app()._("common_unit_mm")
            ids.id_pos_label.text = f"{live.id_slide_mm:0.1f} {unit}"
        if "head_pos_label" in ids:
            unit = MDApp.get_running_app()._("common_unit_mm")
            ids.head_pos_label.text = f"{live.id_head_mm:0.1f} {unit}"
        if "main_angle_label" in ids:
            unit = MDApp.get_running_app()._("common_unit_deg")
            ids.main_angle_label.text = f"{live.pipe_angle_deg:0.1f} {unit}"
        if "aux_angle_label" in ids:
            unit = MDApp.get_running_app()._("common_unit_deg")
            ids.aux_angle_label.text = f"{live.aux_angle_deg:0.1f} {unit}"

        # ������ʾ & slider
        if "linear_step_label" in ids:
            unit = MDApp.get_running_app()._("common_unit_mm")
            ids.linear_step_label.text = f"{self.linear_step_mm:0.1f} {unit}"
        if "linear_step_slider" in ids:
            ids.linear_step_slider.value = self.linear_step_mm * 10

        if "rot_step_label" in ids:
            unit = MDApp.get_running_app()._("common_unit_deg")
            ids.rot_step_label.text = f"{self.rotary_step_deg:0.1f} {unit}"
        if "rot_step_slider" in ids:
            ids.rot_step_slider.value = self.rotary_step_deg

    # ---------- ͨ������ Jog ----------

    def _apply_linear_jog(self, attr_name: str, direction: int):
        """�����Բ����ƶ�ĳ���ᣬdirection = ��1"""
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
            unit = MDApp.get_running_app()._("common_unit_mm")
            ids[lbl_id].text = f"{pos:0.1f} {unit}"

        # TODO: ����� PLC ֱ���˶�����

    # ---------- ͨ����ת Jog ----------

    def _apply_rotary_jog(self, attr_name: str, direction: int):
        """���ǶȲ�����תĳ���ᣬdirection = ��1"""
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
            unit = MDApp.get_running_app()._("common_unit_deg")
            ids[lbl_id].text = f"{ang:0.1f} {unit}"

        # TODO: ����� PLC ��ת����

    # ---------- �����ᰴť�ص� ----------

    def jog_od_neg(self):
        self._apply_linear_jog("od_slide_mm", -1)

    def jog_od_pos(self):
        self._apply_linear_jog("od_slide_mm", +1)

    def jog_id_neg(self):
        self._apply_linear_jog("id_slide_mm", -1)

    def jog_id_pos(self):
        self._apply_linear_jog("id_slide_mm", +1)

    def jog_head_in(self):
        """�ھ���ͷ����"""
        self._apply_linear_jog("id_head_mm", -1)

    def jog_head_out(self):
        """�ھ���ͷ���"""
        self._apply_linear_jog("id_head_mm", +1)

    def home_od(self):
        live = global_state.live
        live.od_slide_mm = 0.0
        if "od_pos_label" in self.ids:
            unit = MDApp.get_running_app()._("common_unit_mm")
            self.ids.od_pos_label.text = f"0.0 {unit}"
        # TODO: PLC Home ����

    def home_id(self):
        live = global_state.live
        live.id_slide_mm = 0.0
        if "id_pos_label" in self.ids:
            unit = MDApp.get_running_app()._("common_unit_mm")
            self.ids.id_pos_label.text = f"0.0 {unit}"

    def home_head(self):
        live = global_state.live
        live.id_head_mm = 0.0
        if "head_pos_label" in self.ids:
            unit = MDApp.get_running_app()._("common_unit_mm")
            self.ids.head_pos_label.text = f"0.0 {unit}"

    # ---------- ��ת�ᰴť�ص� ----------

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
            unit = MDApp.get_running_app()._("common_unit_deg")
            self.ids.main_angle_label.text = f"0.0 {unit}"

    def home_aux_rot(self):
        live = global_state.live
        live.aux_angle_deg = 0.0
        if "aux_angle_label" in self.ids:
            unit = MDApp.get_running_app()._("common_unit_deg")
            self.ids.aux_angle_label.text = f"0.0 {unit}"

    # ---------- ���� slider �ص� ----------

    def on_linear_step_slider(self, value):
        self.linear_step_mm = float(value)
        if "linear_step_label" in self.ids:
            unit = MDApp.get_running_app()._("common_unit_mm")
            self.ids.linear_step_label.text = f"{self.linear_step_mm:0.1f} {unit}"

    def on_rot_step_slider(self, value):
        self.rotary_step_deg = float(value)
        if "rot_step_label" in self.ids:
            unit = MDApp.get_running_app()._("common_unit_deg")
            self.ids.rot_step_label.text = f"{self.rotary_step_deg:0.1f} {unit}"

    # ---------- PLC ����ʾ������������ ----------

    def send_green_button(self):
        """ʾ����ģ���̰�ť���"""
        if plc_service:
            plc_service.enqueue_command(CMD_GREEN_BUTTON)

    def send_axis0_move(self, target_pos: float):
        """ʾ������0 ��λ���payload ��Ŀ��λ�� tag"""
        if plc_service:
            plc_service.enqueue_command(CMD_AXIS0_MOVE, payload={"AXIS0_TARGET": float(target_pos)})

