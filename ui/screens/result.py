from kivy.metrics import dp
from kivy.properties import ListProperty
from kivymd.app import MDApp
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
        app = MDApp.get_running_app()
        container = self.ids.get("result_table_container")
        if container and not self.data_table:
            self.data_table = MDDataTable(
                size_hint=(1, 1),
                use_pagination=False,
                check=False,
                column_data=[
                    (app._("result_col_outer_avg"), dp(40)),
                    (app._("result_col_inner_avg"), dp(40)),
                    (app._("result_col_roundness_od"), dp(40)),
                    (app._("result_col_roundness_id"), dp(40)),
                    (app._("result_col_straightness"), dp(40)),
                    (app._("result_col_concentricity"), dp(40)),
                    (app._("result_col_length"), dp(40)),
                    (app._("result_col_ok"), dp(25)),
                ],
                row_data=[],
            )
            container.add_widget(self.data_table)

    def show_result(self, res):
        """把一次测量的结果塞成“单行报表”"""
        if self.data_table is None:
            # 防御：kv 还没跑 on_kv_post 的极端情况
            self.on_kv_post(None)

        app = MDApp.get_running_app()
        row = (
            f"{res.outer_diameter_avg:0.3f}",
            f"{res.inner_diameter_avg:0.3f}",
            f"{res.roundness_outer:0.3f}",
            f"{res.roundness_inner:0.3f}",
            f"{res.straightness:0.3f}",
            f"{res.concentricity:0.3f}",
            f"{res.length:0.3f}",
            app._("common_ok") if res.ok_flag else app._("common_ng"),
        )

        if self.data_table:
            self.data_table.row_data = [row]

        ids = self.ids
        if "res_ok_label" in ids:
            ids.res_ok_label.text = app._("common_ok") if res.ok_flag else app._("common_ng")

    def refresh_language(self, *args):
        app = MDApp.get_running_app()
        if self.data_table:
            self.data_table.column_data = [
                (app._("result_col_outer_avg"), dp(40)),
                (app._("result_col_inner_avg"), dp(40)),
                (app._("result_col_roundness_od"), dp(40)),
                (app._("result_col_roundness_id"), dp(40)),
                (app._("result_col_straightness"), dp(40)),
                (app._("result_col_concentricity"), dp(40)),
                (app._("result_col_length"), dp(40)),
                (app._("result_col_ok"), dp(25)),
            ]
        ids = self.ids
        if "res_ok_label" in ids:
            text = ids.res_ok_label.text.upper() if ids.res_ok_label.text else ""
            if text in ("OK", app._("common_ok").upper()):
                ids.res_ok_label.text = app._("common_ok")
            elif text in ("NG", app._("common_ng").upper()):
                ids.res_ok_label.text = app._("common_ng")
