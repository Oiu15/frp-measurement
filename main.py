import os
import sys

from kivy.core.window import Window
from kivy.lang import Builder

from kivymd.app import MDApp


def resource_path(rel_path: str) -> str:
    """
    读取打包进 exe 的资源文件（kv 等）。
    开发环境：返回源码目录下的路径。
    onefile：返回 sys._MEIPASS 下的路径。
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS  # PyInstaller onefile 解压目录
    else:
        base_path = os.path.dirname(__file__)

    rel_path = rel_path.replace("/", os.sep)
    return os.path.join(base_path, rel_path)


def app_base_dir() -> str:
    """
    应用“外部文件”的基准目录：
    - 开发时：main_md.py 所在目录
    - 打包后：exe 所在目录
    用来放 config 这类要长期保存、可修改的文件。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)


# ---- KivyMD 控件导入 ----
from kivymd.icon_definitions import md_icons

from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.slider import MDSlider
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dropdownitem import MDDropDownItem
from kivymd.uix.menu import MDDropdownMenu

# MDSeparator 兼容处理
try:
    from kivymd.uix.separator import MDSeparator  # 新版本
except ImportError:
    try:
        from kivymd.uix.list import MDSeparator  # 旧版本
    except ImportError:
        MDSeparator = None  # 只是为了不报错，实际不在 Python 里用到
# ------------------------------------------------------------

from ui.screens import (
    HomeScreen,
    AutoMeasureScreen,
    ManualScreen,
    SettingsScreen,
    ResultScreen,
    AlarmScreen,
)


class FRPHMIDemo(MDApp):
    def build(self):
        # 深色主题 + 蓝灰
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.primary_hue = "700"

        Window.size = (1280, 720)

        kv_file = resource_path("kv/main.kv")
        return Builder.load_file(kv_file)

    def go_home(self, *args):
        self.root.current = "home"


if __name__ == "__main__":
    FRPHMIDemo().run()
