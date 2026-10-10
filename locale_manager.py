import os
import json
from PySide6.QtCore import QObject, Signal

class LocaleManager(QObject):
    language_changed = Signal()

    def __init__(self, locales_dir="locales"):
        super().__init__()
        self.locales_dir = os.path.abspath(locales_dir)
        self.available_locales = {}  # {code: {"name": display_name, "data": dict}}
        self.current_locale_code = "ru"
        self.scan_locales()

    def scan_locales(self):
        """Сканирует папку locales на наличие JSON-файлов и считывает код и отображаемое имя из заголовка."""
        self.available_locales.clear()
        if not os.path.exists(self.locales_dir):
            os.makedirs(self.locales_dir, exist_ok=True)
            self._ensure_default_files()

        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.locales_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        lang_code = data.get("lang_code", os.path.splitext(filename)[0])
                        lang_name = data.get("lang_name", lang_code.upper())
                        self.available_locales[lang_code] = {
                            "name": lang_name,
                            "data": data,
                            "path": path
                        }
                except Exception as e:
                    print(f"Ошибка при чтении файла локализации {filename}: {e}")

        if not self.available_locales:
            self._ensure_default_files()
            self.scan_locales()

    def _ensure_default_files(self):
        ru_path = os.path.join(self.locales_dir, "ru.json")
        en_path = os.path.join(self.locales_dir, "en.json")
        if not os.path.exists(ru_path):
            ru_data = {
                "lang_code": "ru",
                "lang_name": "Русский",
                "logo_title": "F1 HUB CE",
                "home_prompt": "Нажмите Ctrl + M для подключения устройства",
                "connected": "● Подключено",
                "disconnected": "○ Отключено",
                "buttons_title": "Кнопки",
                "dpi_hz_title": "DPI и Частота",
                "dpi_label": "DPI:",
                "hz_label": "Частота:",
                "profiles_title": "Профили",
                "default_profile": "Профиль по умолчанию",
                "profile_prefix": "Профиль",
                "profile_renamed": "(изм.)",
                "btn_lmb": "ЛКМ",
                "btn_rmb": "ПКМ",
                "btn_mmb": "СКМ",
                "btn_forward": "Вперед",
                "btn_back": "Назад",
                "action_default": "По умолчанию",
                "action_1": "Действие 1",
                "action_2": "Действие 2",
                "eject_tooltip": "Отключить устройство",
                "settings_title": "Настройки",
                "language_label": "Язык интерфейса:",
                "theme_label": "Тема:",
                "theme_auto": "Авто (системная)",
                "theme_dark": "Тёмная",
                "theme_light": "Светлая",
                "temp_menu": "Временное меню",
                "sim_charging": "⚡ Имитация зарядки",
                "mouse_image_alt": "[ Изображение мыши ]"
            }
            with open(ru_path, "w", encoding="utf-8") as f:
                json.dump(ru_data, f, ensure_ascii=False, indent=2)

        if not os.path.exists(en_path):
            en_data = {
                "lang_code": "en",
                "lang_name": "English",
                "logo_title": "F1 HUB CE",
                "home_prompt": "Press Ctrl + M to connect device",
                "connected": "● Connected",
                "disconnected": "○ Disconnected",
                "buttons_title": "Buttons",
                "dpi_hz_title": "DPI & Polling Rate",
                "dpi_label": "DPI:",
                "hz_label": "Polling Rate:",
                "profiles_title": "Profiles",
                "default_profile": "Default Profile",
                "profile_prefix": "Profile",
                "profile_renamed": "(mod.)",
                "btn_lmb": "LMB",
                "btn_rmb": "RMB",
                "btn_mmb": "MMB",
                "btn_forward": "Forward",
                "btn_back": "Back",
                "action_default": "Default",
                "action_1": "Action 1",
                "action_2": "Action 2",
                "eject_tooltip": "Disconnect device",
                "settings_title": "Settings",
                "language_label": "Interface Language:",
                "theme_label": "Theme:",
                "theme_auto": "Auto (System)",
                "theme_dark": "Dark",
                "theme_light": "Light",
                "temp_menu": "Temporary menu",
                "sim_charging": "⚡ Simulate charging",
                "mouse_image_alt": "[ Mouse Image ]"
            }
            with open(en_path, "w", encoding="utf-8") as f:
                json.dump(en_data, f, ensure_ascii=False, indent=2)

    def set_language(self, lang_code):
        if lang_code in self.available_locales and self.current_locale_code != lang_code:
            self.current_locale_code = lang_code
            self.language_changed.emit()

    def tr(self, key, default=""):
        locale_info = self.available_locales.get(self.current_locale_code)
        if locale_info and "data" in locale_info:
            return locale_info["data"].get(key, default if default else key)
        return default if default else key
