# ui/widgets/segmentedring.py
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty
from kivy.graphics import Color, Line


class SegmentedRing(Widget):
    """分段式进度环：total_steps 个小格，current_step 表示点亮到第几格。"""

    total_steps = NumericProperty(8)  # 小格数量
    current_step = NumericProperty(0)  # 当前步（0 = 全部未点亮）
    gap_angle = NumericProperty(6)  # 每个格之间的“空隙”角度（单位：度）
    line_width = NumericProperty(12)  # 环的粗细（像素）

    active_color = ListProperty([0.2, 0.9, 0.4, 1])  # 已完成
    current_color = ListProperty([0.4, 1.0, 0.7, 1])  # 正在进行
    inactive_color = ListProperty([0.3, 0.3, 0.3, 1])  # 未开始

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            pos=self._update_canvas,
            size=self._update_canvas,
            total_steps=self._update_canvas,
            current_step=self._update_canvas,
            gap_angle=self._update_canvas,
            line_width=self._update_canvas,
        )

    def _update_canvas(self, *args):
        self.canvas.clear()
        if self.total_steps <= 0:
            return

        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        radius = min(self.width, self.height) / 2.0 - self.line_width

        step_angle = 360.0 / float(self.total_steps)
        arc_angle = max(0.0, step_angle - self.gap_angle)

        with self.canvas:
            for i in range(self.total_steps):
                start = i * step_angle + self.gap_angle / 2.0
                end = start + arc_angle

                # 选择颜色
                if i < self.current_step:
                    Color(*self.active_color)
                elif i == self.current_step:
                    Color(*self.current_color)
                else:
                    Color(*self.inactive_color)

                Line(
                    circle=(cx, cy, radius, start, end),
                    width=self.line_width,
                    cap="round",
                )

