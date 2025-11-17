from kivy.properties import ListProperty
from kivy.uix.widget import Widget


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

        # 防御：长度不一致直接放弃这一帧
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
                # 完全不变时给一点假的跨度，避免全挤在中间
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
