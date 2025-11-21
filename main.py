import os
import sys
import ctypes
from kivy.core.window import Window
from kivy.lang import Builder

from kivymd.app import MDApp


def get_screen_size():
    """
    优先用 Windows API 取物理屏幕分辨率；
    失败时退回 Kivy 的 Window.system_size。
    """
    try:
        user32 = ctypes.windll.user32
        # 当前主屏幕分辨率（已经考虑 DPI）
        sw = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        sh = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        if sw > 0 and sh > 0:
            return sw, sh
    except Exception:
        pass
    # 兜底：用 Kivy 的
    return Window.system_size


def get_titlebar_height() -> int:
    """
    估算窗口标题栏+边框高度，用于纵向补偿。
    """
    try:
        user32 = ctypes.windll.user32
        SM_CYCAPTION = 4  # 标题栏高度
        SM_CYFRAME = 33  # 框架高度（大概值，实际随 DPI 变化）
        caption = user32.GetSystemMetrics(SM_CYCAPTION)
        frame = user32.GetSystemMetrics(SM_CYFRAME)
        return caption + frame
    except Exception:
        return 32  # 兜底值


def center_window(width: int, height: int):
    """
    设置窗口大小并把窗口放在屏幕正中。
    """
    Window.size = (width, height)

    sw, sh = get_screen_size()
    title_h = get_titlebar_height()

    # 居中 + 纵向轻微下移，避免贴顶被挡
    Window.left = int((sw - width) / 2)
    Window.top = int((sh - height) / 2 - title_h / 2)


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

from kivymd.uix.appbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDButton, MDFabButton
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
        from kivymd.uix.divider import MDDivider  # KivyMD 2.x

        class MDSeparator(MDDivider):
            """Compat alias for removed MDSeparator."""

            pass


# ------------------------------------------------------------


# Legacy aliases for KivyMD 1.x names
class MDRaisedButton(MDButton):
    """Compat alias for migrated KivyMD 2.x API."""

    pass


class MDFloatingActionButton(MDFabButton):
    """Compat alias for migrated KivyMD 2.x API."""

    pass


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
        self.theme_cls.primary_palette = "#607d8b"

        Window.size = (1280, 720)

        kv_file = resource_path("kv/main.kv")
        return Builder.load_file(kv_file)

    def on_start(self):
        # center_window(1280, 720)
        Window.maximize()

    def change_screen(self, name: str):
        """Switch to a named screen if it exists."""
        if self.root and name in self.root.screen_names:
            self.root.current = name

    def go_home(self, *args):
        self.root.current = "home"


if __name__ == "__main__":
    FRPHMIDemo().run()
