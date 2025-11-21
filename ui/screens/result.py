from kivy.metrics import dp
from kivy.properties import ListProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

try:
    from kivymd.uix.datatables import MDDataTable  # KivyMD 1.x
except ImportError:
    class MDDataTable(MDBoxLayout):  # Minimal fallback for KivyMD 2.x
        column_data = ListProperty()
        row_data = ListProperty()

        def __init__(self, column_data=None, row_data=None, **kwargs):
            kwargs.pop("use_pagination", None)
            kwargs.pop("check", None)
            super().__init__(orientation="vertical", spacing=dp(4), padding=dp(4), **kwargs)
            self.header = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(32), spacing=dp(4))
            self.body = MDBoxLayout(orientation="vertical", spacing=dp(2))
            self.add_widget(self.header)
            self.add_widget(self.body)
            self.column_data = column_data or []
            self.row_data = row_data or []
            self._build_header()
            self._build_rows()

        def _build_header(self):
            self.header.clear_widgets()
            for title, width in self.column_data:
                self.header.add_widget(
                    MDLabel(
                        text=title,
                        size_hint_x=None,
                        width=width,
                        halign="center",
                        theme_text_color="Secondary",
                        bold=True,
                    )
                )

        def _build_rows(self):
            self.body.clear_widgets()
            for row in self.row_data:
                row_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(4))
                for (title, width), cell in zip(self.column_data, row):
                    row_layout.add_widget(
                        MDLabel(
                            text=str(cell),
                            size_hint_x=None,
                            width=width,
                            halign="center",
                            theme_text_color="Primary",
                        )
                    )
                self.body.add_widget(row_layout)

        def on_column_data(self, *args):
            self._build_header()
            self._build_rows()

        def on_row_data(self, *args):
            self._build_rows()


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
            # 防御：kv 还没跑 on_kv_post 的极端情况
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

        # 如果你还想保留右下方的单值标签，也可以在这里继续给 ids.*.text 赋值
        ids = self.ids
        if "res_ok_label" in ids:
            ids.res_ok_label.text = "OK" if res.ok_flag else "NG"
