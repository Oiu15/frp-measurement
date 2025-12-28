from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

from ui.config import load_config, save_config


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
        """点击“应用/ 保存”按钮时写回 JSON，并触发 PLC 重新连接"""
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
        app = MDApp.get_running_app()
        svc = getattr(app, "plc_service", None)
        if svc:
            svc.reconfigure(ip=cfg.get("plc_ip", "192.168.0.10"), slot=0, timeout=1.0)
        # 这里如需同步到测量核心，可在后面派发事件 / 调用接口
