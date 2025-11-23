import json
from pathlib import Path
from typing import Any, Dict, Optional


class I18N:
    """Simple JSON-based translator with fallback support."""

    def __init__(self, locales_dir: str, default_lang: str = "en_US", fallback_lang: Optional[str] = None):
        self.locales_dir = Path(locales_dir)
        self.default_lang = default_lang
        self.fallback_lang = fallback_lang or default_lang
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_lang = default_lang
        self._ensure_loaded(self.default_lang)

    def _load_file(self, lang: str) -> Dict[str, str]:
        path = self.locales_dir / f"{lang}.json"
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _ensure_loaded(self, lang: str):
        if lang not in self.translations:
            self.translations[lang] = self._load_file(lang)

    def set_lang(self, lang: str):
        """Switch current language; missing language falls back to default."""
        self.current_lang = lang
        self._ensure_loaded(lang)

    def translate(self, key: str, **kwargs: Any) -> str:
        """Return translated text; fall back to fallback/default key name."""
        self._ensure_loaded(self.current_lang)
        text = self.translations.get(self.current_lang, {}).get(key)
        if text is None and self.fallback_lang:
            self._ensure_loaded(self.fallback_lang)
            text = self.translations.get(self.fallback_lang, {}).get(key)
        if text is None:
            text = key
        try:
            return text.format(**kwargs) if kwargs else text
        except Exception:
            return text


__all__ = ["I18N"]
