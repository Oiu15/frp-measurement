import math
import random

from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

from core import frp_core
from logic.models import global_state


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
        demo 版：每秒把步骤 +1，到 7 时自动 compute 并跳到 Result
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
        以后接 PLC 状态机时，可以在这里改成从状态机读，比如：
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
