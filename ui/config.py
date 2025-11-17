import json
import sys
from pathlib import Path


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
        # 当前文件在 ui/ 下，根目录是它的上一级
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
