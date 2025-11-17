import math
import random
import json
import os
import sys
from pathlib import Path

from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

from logic.models import global_state
from logic import measurement_flow as mf
from core import frp_core

from kivy.uix.widget import Widget
from kivy.properties import ListProperty, NumericProperty

from kivymd.uix.datatables import MDDataTable
from kivy.metrics import dp

import json
from pathlib import Path


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


class AutoMeasureScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 曲线 / 信号
        self._t = 0.0
        self._ods = []
        self._ids = []
        self._auto_ev = None

        # 步骤显示 & demo 状态机
        self._current_step = 1  # 1~7
        self._step_ev = None  # 刷新高亮
        self._step_demo_ev = None  # demo：每秒推进一步

    def _restart_demo(self):
        """重置 demo 状态机 + 曲线，每次进入 Auto 页都要调用"""

        # 先把旧定时器全部关掉，防止重复注册
        for ev_name in ("_auto_ev", "_step_ev", "_step_demo_ev"):
            ev = getattr(self, ev_name, None)
            if ev is not None:
                ev.cancel()
                setattr(self, ev_name, None)

        # 重置 C++ 核心 & 本地数据
        frp_core.reset()
        self._t = 0.0
        self._ods.clear()
        self._ids.clear()

        # 从第 1 步开始
        self._current_step = 1
        global_state.live.current_step = self._current_step

        # 曲线 / 数值定时刷新
        self._auto_ev = Clock.schedule_interval(self._demo_measure_loop, 0.05)

        # 步骤高亮轮询（0.2s 改一次颜色）
        self._step_ev = Clock.schedule_interval(self._update_step_indicator, 0.2)

        # demo 状态机：每 1 秒自动下一步
        self._step_demo_ev = Clock.schedule_interval(self._demo_step_advance, 1.0)

        # 立刻高亮一次
        self._update_step_indicator(0)

    def on_kv_post(self, base_widget):
        """第一次 kv 构建完毕时跑一次"""
        self._restart_demo()

    def on_pre_enter(self, *args):
        """每次切到 Auto 页时都从第 1 步重新开始"""
        self._restart_demo()

    # ---------- demo 状态机：1 秒一步 ----------

    def _demo_step_advance(self, dt):
        """
        demo 版：每秒把步骤 +1，到 7 时自动 compute 并跳转 Result
        """
        if self._current_step < 7:
            self._current_step += 1
            global_state.live.current_step = self._current_step
        else:
            # 已经在最后一步：执行一次计算并跳转
            self._finish_auto_sequence()
            # 取消自己的定时器
            if self._step_demo_ev is not None:
                self._step_demo_ev.cancel()
                self._step_demo_ev = None
            return False  # 不再重复调用

        return True

    # ---------- 状态机步骤高亮 ----------

    def _get_current_step_index(self) -> int:
        """
        现在先用 demo 的 self._current_step。
        以后接 PLC 状态机时，可以在这里改成从状态机读：
        比如：
            return int(global_state.live.current_step)
        """
        return int(self._current_step)

    def _update_step_indicator(self, dt):
        current = self._get_current_step_index()

        for i in range(1, 8):
            lbl = self.ids.get(f"step_lbl_{i}")
            if not lbl:
                continue

            if i == current:
                lbl.theme_text_color = "Custom"
                lbl.text_color = (1, 1, 0, 1)  # 黄色高亮
            else:
                lbl.theme_text_color = "Secondary"

    # ---------- 自动测量 + 曲线刷新 ----------

    def _demo_measure_loop(self, dt):
        """模拟旋转采样 + 调用 C++ 核心 + 刷新 UI + 曲线"""

        # 兜底：防止极端情况下属性没初始化
        if not hasattr(self, "_ods"):
            self._t = 0.0
            self._ods = []
            self._ids = []

        self._t += 5.0
        angle = self._t % 360

        # 模拟外径 / 内径的一个小波动
        od = 152.0 + 0.2 * math.sin(math.radians(angle)) + random.uniform(-0.02, 0.02)
        id_ = 76.0 + 0.05 * math.cos(math.radians(angle)) + random.uniform(-0.01, 0.01)

        # 写入全局实时状态
        global_state.live.outer_diameter = od
        global_state.live.inner_diameter = id_
        global_state.live.angle_deg = angle

        # 推给 C++ 核心
        frp_core.add_sample(angle, od, id_)

        # 数值显示
        ids = self.ids
        if "auto_outer_value" in ids:
            ids.auto_outer_value.text = f"{od:0.2f} mm"
        if "auto_inner_value" in ids:
            ids.auto_inner_value.text = f"{id_:0.2f} mm"
        if "auto_angle" in ids:
            ids.auto_angle.text = f"{angle:0.1f} °"

        # ---- 曲线数据更新（滚动窗口）----
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

    # ---------- 结束时统一收尾 ----------

    def _finish_auto_sequence(self):
        """最后一步：计算结果 + 跳转 Result + 收掉定时器（demo 版）"""
        res = frp_core.compute()
        result_screen = self.manager.get_screen("result")
        result_screen.show_result(res)
        self.manager.current = "result"

        # demo：算完后把定时器都停掉，避免后台还在跑
        if self._auto_ev is not None:
            self._auto_ev.cancel()
            self._auto_ev = None
        if self._step_ev is not None:
            self._step_ev.cancel()
            self._step_ev = None

    def on_leave(self, *args):
        """如果从 Auto 手动跳走，也顺便把 demo 定时器停掉"""
        for ev_name in ("_auto_ev", "_step_ev", "_step_demo_ev"):
            ev = getattr(self, ev_name, None)
            if ev is not None:
                ev.cancel()
                setattr(self, ev_name, None)


class ManualScreen(MDScreen):
    """Manual / Jog page for all 5 motors (2 slides + 3 rotary/extension axes).

    现在还是纯 UI / demo：
    之后你可以在 _apply_linear_jog / _apply_rotary_jog / home_* 里
    加上真正的 PLC 指令。
    """

    # 共享步距
    linear_step_mm = NumericProperty(0.5)
    rotary_step_deg = NumericProperty(5.0)

    def on_kv_post(self, base_widget):
        """kv 绑定完成后，从 global_state 初始化各个位置。"""
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
            ids.linear_step_slider.value = self.linear_step_mm

        if "rot_step_label" in ids:
            ids.rot_step_label.text = f"{self.rotary_step_deg:0.1f} °"
        if "rot_step_slider" in ids:
            ids.rot_step_slider.value = self.rotary_step_deg

    # ---------- 通用线性 Jog ----------

    def _apply_linear_jog(self, attr_name: str, direction: int):
        """按线性步距移动某个轴，direction = ±1。"""
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

        # TODO: 这里接 PLC 直线运动命令

    # ---------- 通用旋转 Jog ----------

    def _apply_rotary_jog(self, attr_name: str, direction: int):
        """按角度步距旋转某个轴，direction = ±1。"""
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

        # TODO: 这里接 PLC 旋转命令

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
        """内径测头缩回。"""
        self._apply_linear_jog("id_head_mm", -1)

    def jog_head_out(self):
        """内径测头伸出。"""
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


def app_base_dir() -> Path:
    """
    应用外部文件的基准目录：
    - 开发时：项目根目录（ui/ 的上一级）
    - 打包 onefile 后：exe 所在目录
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后的 exe
        return Path(sys.executable).resolve().parent
    else:
        # 当前文件在 ui/screens_md.py → 根目录是它的上上级
        return Path(__file__).resolve().parent.parent


CONFIG_DIR = app_base_dir() / "config"
CONFIG_PATH = CONFIG_DIR / "frp_hmi_config.json"

DEFAULT_CONFIG = {
    "plc_ip": "192.168.0.10",
    "plc_port": 502,
    "samples_per_rev": 180,
}


def load_config() -> dict:
    if CONFIG_PATH.is_file():
        try:
            return {
                **DEFAULT_CONFIG,
                **json.loads(CONFIG_PATH.read_text(encoding="utf-8")),
            }
        except Exception:
            # 解析失败时退回默认
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


class SettingsScreen(MDScreen):
    def on_kv_post(self, base_widget):
        """kv 绑定完成后，把配置读出来填进文本框"""
        cfg = load_config()
        ids = self.ids

        if "plc_ip_field" in ids:
            ids.plc_ip_field.text = cfg.get("plc_ip", "")
        if "plc_port_field" in ids:
            ids.plc_port_field.text = str(cfg.get("plc_port", "502"))
        if "samples_field" in ids:
            ids.samples_field.text = str(cfg.get("samples_per_rev", "180"))

    def on_apply_button(self):
        """点击“应用/保存”按钮时写回 JSON"""
        ids = self.ids
        cfg = load_config()

        if "plc_ip_field" in ids:
            cfg["plc_ip"] = ids.plc_ip_field.text.strip()

        if "plc_port_field" in ids:
            try:
                cfg["plc_port"] = int(ids.plc_port_field.text.strip())
            except Exception:
                pass

        if "samples_field" in ids:
            try:
                cfg["samples_per_rev"] = int(ids.samples_field.text.strip())
            except Exception:
                pass

        save_config(cfg)
        # 这里如果要同步到测量核心，可以在后面派发事件 / 调用接口


class ResultScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_table = None

    def on_kv_post(self, base_widget):
        """kv 绑定完成后，在装好的容器里创建 MDDataTable"""
        container = self.ids.get("result_table_container")
        if container and not self.data_table:
            self.data_table = MDDataTable(
                size_hint=(1, 1),
                use_pagination=False,
                check=False,
                column_data=[
                    ("Outer Ø Avg (mm)", dp(40)),
                    ("Inner Ø Avg (mm)", dp(40)),
                    ("Roundness OD (mm)", dp(40)),
                    ("Roundness ID (mm)", dp(40)),
                    ("Straightness (mm)", dp(40)),
                    ("Concentricity (mm)", dp(40)),
                    ("Length (m)", dp(40)),
                    ("OK?", dp(25)),
                ],
                row_data=[],
            )
            container.add_widget(self.data_table)

    def show_result(self, res):
        """
        把一次测量的结果塞成“单行报表”
        """
        # 先更新表格
        if self.data_table is None:
            # 防御：kv 还没走 on_kv_post 的极端情况
            self.on_kv_post(None)

        row = (
            f"{res.outer_diameter_avg:0.3f}",
            f"{res.inner_diameter_avg:0.3f}",
            f"{res.roundness_outer:0.3f}",
            f"{res.roundness_inner:0.3f}",
            f"{res.straightness:0.3f}",
            f"{res.concentricity:0.3f}",
            f"{res.length:0.3f}",
            "OK" if res.ok_flag else "NG",
        )

        if self.data_table:
            self.data_table.row_data = [row]

        # 如果你还想保留右侧/下方的单值标签，也可以在这里继续给 ids.*.text 赋值
        ids = self.ids
        if "res_ok_label" in ids:
            ids.res_ok_label.text = "OK" if res.ok_flag else "NG"


class AlarmScreen(MDScreen):
    pass


class LivePlotWidget(Widget):
    """简单工业风实时曲线控件：黑底 + 两条滚动线"""

    outer_points = ListProperty([])
    inner_points = ListProperty([])

    def update_data(
        self,
        od_list,
        id_list,
        y_min=150.0,
        y_max=154.0,
        inner_y_min=None,
        inner_y_max=None,
    ):
        """按时间顺序滚动显示，外径用 y_min/y_max，内径用自己的一套缩放"""

        if not self.width or not self.height or not od_list or not id_list:
            return

        # 防御：长度不一致直接放弃这帧
        if len(od_list) != len(id_list):
            return

        w, h = self.width, self.height
        x0, y0 = self.x, self.y
        n = len(od_list) - 1 if len(od_list) > 1 else 1

        # ---- 内径的纵轴范围：自动按当前窗口数据自适应缩放 ----
        if inner_y_min is None or inner_y_max is None:
            v_min = min(id_list)
            v_max = max(id_list)
            span = v_max - v_min
            if span == 0:
                # 完全不变时给一点假的跨度，避免全挤在中线
                span = 0.01
            # 给一点边界余量，避免贴边
            inner_y_min = v_min - 0.3 * span
            inner_y_max = v_max + 0.3 * span

        def to_points(values, vmin, vmax):
            pts = []
            for i, val in enumerate(values):
                # X：按索引线性铺满整个宽度
                x = x0 + (i / n) * w

                # Y：映射到高度的 10%~90%
                if vmax == vmin:
                    y_norm = 0.5
                else:
                    y_norm = (val - vmin) / (vmax - vmin)
                y_norm = max(0.0, min(1.0, y_norm))
                y = y0 + 0.1 * h + y_norm * 0.8 * h

                pts.extend([x, y])
            return pts

        # 外径：用 y_min / y_max（绝对值）
        self.outer_points = to_points(od_list, y_min, y_max)
        # 内径：用 inner_y_min / inner_y_max（局部自动缩放）
        self.inner_points = to_points(id_list, inner_y_min, inner_y_max)
