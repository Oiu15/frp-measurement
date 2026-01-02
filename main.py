import os
import sys
import ctypes
from pathlib import Path
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.core.text import LabelBase
from kivy.resources import resource_add_path

from kivymd.app import MDApp

from plc.service import PlcService

plc_service: PlcService | None = None


def get_screen_size():
    """
    Prefer Windows API to get physical screen resolution; fallback to Kivy's Window.system_size.
    """
    try:
        user32 = ctypes.windll.user32
        # Primary screen resolution (DPI-aware)
        sw = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        sh = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        if sw > 0 and sh > 0:
            return sw, sh
    except Exception:
        pass
    # Fallback: use Kivy
    return Window.system_size


def get_titlebar_height() -> int:
    """
    Estimate window title bar + frame height for vertical compensation.
    """
    try:
        user32 = ctypes.windll.user32
        SM_CYCAPTION = 4  # Title bar height
        SM_CYFRAME = 33  # Approx frame height; varies with DPI
        caption = user32.GetSystemMetrics(SM_CYCAPTION)
        frame = user32.GetSystemMetrics(SM_CYFRAME)
        return caption + frame
    except Exception:
        return 32  # Fallback


def center_window(width: int, height: int):
    """
    Set window size and center it on the screen.
    """
    Window.size = (width, height)

    sw, sh = get_screen_size()
    title_h = get_titlebar_height()

    # Center + small downward offset to avoid top clipping
    Window.left = int((sw - width) / 2)
    Window.top = int((sh - height) / 2 - title_h / 2)


def resource_path(rel_path: str) -> str:
    """
    Resolve resource path for bundled exe or source tree.
    Dev: return path under source directory.
    Onefile: return path under sys._MEIPASS.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS  # PyInstaller onefile unpack dir
    else:
        base_path = os.path.dirname(__file__)

    rel_path = rel_path.replace("/", os.sep)
    return os.path.join(base_path, rel_path)


def register_fonts():
    """Register bundled Chinese fonts."""
    fonts_dir = resource_path("assets/fonts")
    resource_add_path(fonts_dir)
    LabelBase.register(
        name="MSYH",
        fn_regular="msyh.ttc",
        fn_bold="msyhbd.ttc",
        # Kivy does not have a dedicated light slot; map light to italic for compatibility.
        fn_italic="msyhl.ttc",
    )


def app_base_dir() -> str:
    """
    Base dir for external files:
    - Dev: repo root (main.py directory)
    - Bundled: exe directory
    For long-lived editable files like config.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)


# ---- KivyMD imports ----
from kivymd.icon_definitions import md_icons
from kivymd.font_definitions import theme_font_styles
from kivy.metrics import sp
from kivymd.uix.appbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDButton, MDFabButton
from kivymd.uix.slider import MDSlider
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dropdownitem import MDDropDownItem
from kivymd.uix.menu import MDDropdownMenu
from i18n import I18N
from ui.config import load_config, save_config

from kivymd.uix.divider import MDDivider

from plc.service import get_plc_service


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
    EipTestScreen,
)


class FRPHMIDemo(MDApp):
    lang = StringProperty("zh_CN")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        register_fonts()
        self.config_data = load_config()
        self.lang = self.config_data.get("lang", "zh_CN")
        locales_dir = resource_path("locales")
        self.i18n = I18N(locales_dir, default_lang=self.lang, fallback_lang="zh_CN")
        self._drawer_menu = None

        self.plc_service = get_plc_service(self.config_data)
        global plc_service

        plc_service = self.plc_service

    def build(self):
        # Dark theme + blue gray
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "#607d8b"

        fonts_dir = Path(__file__).parent / "assets" / "fonts"
        resource_add_path(str(fonts_dir))

        LabelBase.register(
            name="msyh",
            fn_regular=str(fonts_dir / "msyh.ttc"),
            fn_bold=str(fonts_dir / "msyhbd.ttc"),
        )

        for style in theme_font_styles:
            if style == "Icon":
                continue  # Icons use their own font

            for role in theme_font_styles[style]:
                theme_font_styles[style][role]["font-name"] = "MSYH"

        Window.size = (1280, 720)

        kv_file = resource_path("kv/main.kv")
        return Builder.load_file(kv_file)

    def on_start(self):
        # center_window(1280, 720)
        Window.maximize()
        try:
            if self.plc_service:
                self.plc_service.start()
        except Exception:
            # Do not break UI if PLC startup fails
            pass

    def on_stop(self):
        if self.plc_service:
            self.plc_service.stop()
        return super().on_stop()

    def change_screen(self, name: str):
        """Switch to a named screen if it exists."""
        if self.root and name in self.root.screen_names:
            self.root.current = name

    def go_home(self, *args):
        self.root.current = "home"

    def _(self, key: str, **kwargs):
        return self.i18n.translate(key, **kwargs)

    def toggle_language(self):
        """Toggle between zh_CN and en_US, then refresh UI text."""
        new_lang = "en_US" if self.lang == "zh_CN" else "zh_CN"
        self.lang = new_lang
        self.i18n.set_lang(new_lang)
        self.config_data["lang"] = new_lang
        save_config(self.config_data)

        if self.root:
            for screen_name in self.root.screen_names:
                screen = self.root.get_screen(screen_name)
                refresh_texts = getattr(screen, "refresh_texts", None)
                refresh_lang = getattr(screen, "refresh_language", None)
                if callable(refresh_texts):
                    refresh_texts()
                elif callable(refresh_lang):
                    refresh_lang()

    def open_drawer(self, caller):
        """Open top-left dropdown navigation menu."""
        if self._drawer_menu is None:
            items = [
                {
                    "text": self._("home_title") if hasattr(self, "_") else "Home",
                    "on_release": lambda: self._nav_to("home"),
                },
                {"text": "Manual", "on_release": lambda: self._nav_to("manual")},
                {"text": "Settings", "on_release": lambda: self._nav_to("settings")},
                {"text": "EIP Test", "on_release": lambda: self._nav_to("eip_test")},
                {"text": "Auto", "on_release": lambda: self._nav_to("auto")},
                {"text": "Alarm", "on_release": lambda: self._nav_to("alarm")},
            ]
            self._drawer_menu = MDDropdownMenu(
                caller=caller,
                items=items,
                position="auto",
                width_mult=4,
            )
        else:
            self._drawer_menu.caller = caller
        self._drawer_menu.open()

    def _nav_to(self, screen_name: str):
        """Navigate to a screen and close the drawer."""
        if self._drawer_menu:
            self._drawer_menu.dismiss()
        self.change_screen(screen_name)


if __name__ == "__main__":
    FRPHMIDemo().run()
