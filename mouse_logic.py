import os
import json
import glob
import hid
from PySide6.QtCore import QObject, Signal

# Константы фрейминга CompX
COMPX_PACKET_LENGTH = 64
COMPX_HEADER_LENGTH = 6
COMPX_STATUS_REQUEST = 0x00

# Таблица байтовых значений для частоты опроса
POLLING_RATE_MAP = {
    125: 0x08,
    250: 0x04,
    500: 0x02,
    1000: 0x01
}
REV_POLLING_RATE_MAP = {v: k for k, v in POLLING_RATE_MAP.items()}

# Таблица LOD
LOD_MAP = {1: 0x01, 2: 0x02}
REV_LOD_MAP = {0x01: 1, 0x02: 2}

# Варианты назначения кнопок
KEY_BINDINGS_MAP = {
    "Ничего": 0x00,
    "ЛКМ": 0x01,
    "ПКМ": 0x02,
    "СКМ": 0x04,
    "Вперед": 0x08,
    "Назад": 0x10,
    "DPI цикл": 0x20,
    "DPI+": 0x21,
    "DPI-": 0x22
}
REV_KEY_BINDINGS_MAP = {v: k for k, v in KEY_BINDINGS_MAP.items()}


class CompXProtocol:
    """Низкоуровневый модуль работы с контроллерами CompX (Areson VGN F1: 25a7:fa7c)."""
    def __init__(self, vid=0x25A7, pid=0xFA7C):
        self.vid = vid
        self.pid = pid
        self.device = None
        self.product_name = "VGN Dragonfly F1"

    def connect(self) -> bool:
        if self.device:
            return True
        try:
            devs = hid.enumerate(self.vid, self.pid)
            if not devs:
                self.device = None
                return False

            selected_path = None
            for d in devs:
                if d.get('interface_number', -1) == 1 or d.get('usage_page', 0) >= 0xFF00:
                    selected_path = d['path']
                    prod = d.get('product_string') or "VGN F1"
                    mfg = d.get('manufacturer_string') or "Areson"
                    self.product_name = f"{mfg} {prod}" if mfg not in prod else prod
                    break

            if not selected_path:
                selected_path = devs[0]['path']
                prod = devs[0].get('product_string') or "VGN F1"
                mfg = devs[0].get('manufacturer_string') or "Areson"
                self.product_name = f"{mfg} {prod}" if mfg not in prod else prod

            self.device = hid.device()
            self.device.open_path(selected_path)
            self.device.set_nonblocking(0)
            return True
        except Exception:
            self.device = None
            return False

    def close(self):
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

    def encode_request(self, target: int, page: int, command: int, args: list) -> bytearray:
        packet = bytearray(COMPX_PACKET_LENGTH)
        packet[0] = COMPX_STATUS_REQUEST
        packet[2] = target
        packet[3] = len(args)
        packet[4] = page
        packet[5] = command
        for i, val in enumerate(args):
            if COMPX_HEADER_LENGTH + i < COMPX_PACKET_LENGTH:
                packet[COMPX_HEADER_LENGTH + i] = val
        return packet

    def send_command(self, target: int, page: int, command: int, args: list) -> bool:
        if not self.device and not self.connect():
            return False
        pkt = self.encode_request(target, page, command, args)
        try:
            self.device.write(pkt)
            return True
        except Exception as e:
            print(f"[CompX] Ошибка отправки: {e}")
            self.close()
            return False

    def query_command(self, target: int, page: int, command: int, args: list = None, timeout_ms=500) -> list:
        if args is None:
            args = []
        if not self.device and not self.connect():
            return []

        pkt = self.encode_request(target, page, command, args)
        try:
            self.device.write(pkt)
            response = self.device.read(COMPX_PACKET_LENGTH, timeout_ms)
            return list(response)
        except Exception as e:
            print(f"[CompX] Ошибка чтения из устройства: {e}")
            self.close()
            return []


class ProfileManager:
    """Система управления отдельными файлами профилей в папке profiles/."""
    def __init__(self, profiles_dir="profiles"):
        self.profiles_dir = profiles_dir
        self.ensure_dir()
        self.active_profile_name = "Основной"
        self.active_data = self.get_default_profile()
        self.load_active_or_first()

    def ensure_dir(self):
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir, exist_ok=True)

    def get_default_profile(self):
        return {
            "dpi_stages": [400, 800, 1600, 3200],
            "current_dpi_index": 1,
            "polling_rate": 1000,
            "lod": 1,
            "key_bindings": {
                "btn_1": "ЛКМ",
                "btn_2": "ПКМ",
                "btn_3": "СКМ",
                "btn_4": "Назад",
                "btn_5": "Вперед"
            }
        }

    def _get_path(self, name: str) -> str:
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        if not safe_name:
            safe_name = "Profile"
        return os.path.join(self.profiles_dir, f"{safe_name}.json")

    def list_profiles(self) -> list:
        self.ensure_dir()
        files = glob.glob(os.path.join(self.profiles_dir, "*.json"))
        names = [os.path.splitext(os.path.basename(f))[0] for f in files]
        return names if names else ["Основной"]

    def load_active_or_first(self):
        profiles = self.list_profiles()
        if self.active_profile_name not in profiles:
            self.active_profile_name = profiles[0]
        self.load_profile(self.active_profile_name)

    def load_profile(self, name: str) -> dict:
        filepath = self._get_path(name)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self.active_data = json.load(f)
                    self.active_profile_name = name
                    return self.active_data
            except Exception as e:
                print(f"[ProfileManager] Ошибка чтения {filepath}: {e}")

        self.active_data = self.get_default_profile()
        self.active_profile_name = name
        self.save_current_profile()
        return self.active_data

    def save_current_profile(self):
        self.ensure_dir()
        filepath = self._get_path(self.active_profile_name)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.active_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ProfileManager] Ошибка сохранения {filepath}: {e}")

    def create_profile(self, name: str):
        filepath = self._get_path(name)
        if not os.path.exists(filepath):
            new_data = self.get_default_profile()
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"[ProfileManager] Ошибка создания {filepath}: {e}")
        self.active_profile_name = name
        self.active_data = self.load_profile(name)

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        old_path = self._get_path(old_name)
        new_path = self._get_path(new_name)
        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                os.rename(old_path, new_path)
                if self.active_profile_name == old_name:
                    self.active_profile_name = new_name
                return True
            except Exception as e:
                print(f"[ProfileManager] Ошибка переименования: {e}")
                return False
        return False

    def delete_profile(self, name: str):
        path = self._get_path(name)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"[ProfileManager] Ошибка удаления: {e}")
        profiles = self.list_profiles()
        self.active_profile_name = profiles[0] if profiles else "Основной"
        self.load_profile(self.active_profile_name)


class MouseLogic(QObject):
    """Главный модуль логики взаимодействия UI, файлов и контроллера."""
    connection_changed = Signal()
    battery_changed = Signal()
    dpi_changed = Signal()
    hz_changed = Signal()
    profiles_changed = Signal()
    keybindings_changed = Signal()
    apply_status_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.protocol = CompXProtocol(vid=0x25A7, pid=0xFA7C)
        self.profile_mgr = ProfileManager()

        self.is_connected = False
        self.battery_level = 100
        self.is_charging = False
        self.device_name = "VGN Dragonfly F1"

        self.dpi_values = [400, 800, 1600, 3200]
        self.dpi_index = 1
        self.hz_values = [125, 250, 500, 1000]
        self.hz_index = 3
        self.key_bindings = {}

        self.sync_from_active_profile()
        self.check_connection()

    def sync_from_active_profile(self):
        pdata = self.profile_mgr.active_data
        self.dpi_values = pdata.get("dpi_stages", [400, 800, 1600, 3200])
        self.dpi_index = pdata.get("current_dpi_index", 1)

        rate = pdata.get("polling_rate", 1000)
        self.hz_index = self.hz_values.index(rate) if rate in self.hz_values else 3

        self.key_bindings = pdata.get("key_bindings", {
            "btn_1": "ЛКМ", "btn_2": "ПКМ", "btn_3": "СКМ",
            "btn_4": "Назад", "btn_5": "Вперед"
        })

    def check_connection(self) -> bool:
        """Проверка подключения и обновление данных."""
        was_connected = self.is_connected
        connected = self.protocol.connect()

        if connected:
            if self.protocol.product_name:
                self.device_name = self.protocol.product_name
            if not was_connected:
                self.read_hardware_state()
            else:
                self.read_battery_state()
        else:
            if was_connected:
                self.set_connected(False)

        return self.is_connected

    def read_battery_state(self):
        """Чтение реального заряда и состояния зарядки."""
        if not self.is_connected:
            return
        res = self.protocol.query_command(target=0x00, page=0x01, command=0x03)
        if len(res) >= 7:
            bat_val = res[6]
            charging = bool(res[7]) if len(res) > 7 else False
            if 0 <= bat_val <= 100:
                self.set_battery(bat_val, charging)

    def read_hardware_state(self):
        if not self.protocol.connect():
            self.set_connected(False)
            return

        self.set_connected(True)
        if self.protocol.product_name:
            self.device_name = self.protocol.product_name

        self.read_battery_state()

        # 1. Запрос DPI
        res_dpi = self.protocol.query_command(target=0x00, page=0x01, command=0x01)
        if len(res_dpi) >= 10:
            active_idx = res_dpi[6]
            stages = []
            for i in range(4):
                offset = 7 + (i * 4)
                if offset + 3 < len(res_dpi):
                    x_val = (res_dpi[offset] << 8) | res_dpi[offset + 1]
                    stages.append(x_val)
            if stages:
                self.dpi_values = stages
                self.dpi_index = min(active_idx, len(stages) - 1)
                self.profile_mgr.active_data["dpi_stages"] = self.dpi_values
                self.profile_mgr.active_data["current_dpi_index"] = self.dpi_index

        # 2. Запрос Частоты Опроса
        res_hz = self.protocol.query_command(target=0x00, page=0x01, command=0x02)
        if len(res_hz) >= 7:
            rate_code = res_hz[6]
            if rate_code in REV_POLLING_RATE_MAP:
                rate_val = REV_POLLING_RATE_MAP[rate_code]
                if rate_val in self.hz_values:
                    self.hz_index = self.hz_values.index(rate_val)
                    self.profile_mgr.active_data["polling_rate"] = rate_val

        # 3. Запрос Назначения Кнопок
        res_keys = self.protocol.query_command(target=0x00, page=0x02, command=0x01)
        if len(res_keys) >= 11:
            for btn_idx in range(1, 6):
                byte_val = res_keys[5 + btn_idx]
                btn_key = f"btn_{btn_idx}"
                action_name = REV_KEY_BINDINGS_MAP.get(byte_val, "Custom")
                self.key_bindings[btn_key] = action_name

            self.profile_mgr.active_data["key_bindings"] = self.key_bindings

        self.profile_mgr.save_current_profile()

        self.dpi_changed.emit()
        self.hz_changed.emit()
        self.keybindings_changed.emit()

    def apply_current_settings(self) -> bool:
        """Запись настроек в устройство."""
        success = True

        # 1. DPI
        curr_idx = self.dpi_index
        dpi_val = self.dpi_values[curr_idx] if curr_idx < len(self.dpi_values) else 800
        x_hi, x_lo = (dpi_val >> 8) & 0xFF, dpi_val & 0xFF
        if not self.protocol.send_command(0x00, 0x01, 0x01, [curr_idx, x_hi, x_lo, x_hi, x_lo]):
            success = False

        # 2. Polling Rate
        rate = self.hz_values[self.hz_index]
        rate_byte = POLLING_RATE_MAP.get(rate, 0x01)
        if not self.protocol.send_command(0x00, 0x01, 0x02, [rate_byte]):
            success = False

        # 3. Keybindings
        key_args = []
        for btn_idx in range(1, 6):
            btn_key = f"btn_{btn_idx}"
            action_name = self.key_bindings.get(btn_key, "Custom")
            byte_val = KEY_BINDINGS_MAP.get(action_name, 0x00)
            key_args.append(byte_val)

        if not self.protocol.send_command(0x00, 0x02, 0x01, key_args):
            success = False

        # Сохранение в профиль
        self.profile_mgr.active_data["current_dpi_index"] = self.dpi_index
        self.profile_mgr.active_data["dpi_stages"] = self.dpi_values
        self.profile_mgr.active_data["polling_rate"] = rate
        self.profile_mgr.active_data["key_bindings"] = self.key_bindings
        self.profile_mgr.save_current_profile()

        self.apply_status_changed.emit(success)
        return success

    def set_dpi_index(self, index: int):
        if 0 <= index < len(self.dpi_values):
            self.dpi_index = index
            self.dpi_changed.emit()

    def set_dpi_value(self, index: int, value: int):
        if 0 <= index < len(self.dpi_values):
            self.dpi_values[index] = value
            self.dpi_changed.emit()

    def set_hz_index(self, index: int):
        if 0 <= index < len(self.hz_values):
            self.hz_index = index
            self.hz_changed.emit()

    def set_key_binding(self, btn_id: str, action_name: str):
        self.key_bindings[btn_id] = action_name
        self.keybindings_changed.emit()

    @property
    def profiles(self) -> list:
        return self.profile_mgr.list_profiles()

    @property
    def current_profile_index(self) -> int:
        profiles = self.profiles
        name = self.profile_mgr.active_profile_name
        return profiles.index(name) if name in profiles else 0

    def select_profile_by_index(self, index: int):
        profiles = self.profiles
        if 0 <= index < len(profiles):
            name = profiles[index]
            self.profile_mgr.load_profile(name)
            self.sync_from_active_profile()
            self.dpi_changed.emit()
            self.hz_changed.emit()
            self.keybindings_changed.emit()

    def add_profile(self, name: str):
        self.profile_mgr.create_profile(name)
        self.sync_from_active_profile()
        self.profiles_changed.emit()
        self.dpi_changed.emit()
        self.hz_changed.emit()
        self.keybindings_changed.emit()

    def rename_profile(self, idx: int, new_name: str):
        profiles = self.profiles
        if 0 <= idx < len(profiles):
            old_name = profiles[idx]
            if self.profile_mgr.rename_profile(old_name, new_name):
                self.profiles_changed.emit()

    def delete_profile(self, idx: int):
        profiles = self.profiles
        if len(profiles) > 1 and 0 <= idx < len(profiles):
            del_name = profiles[idx]
            self.profile_mgr.delete_profile(del_name)
            self.sync_from_active_profile()
            self.profiles_changed.emit()
            self.dpi_changed.emit()
            self.hz_changed.emit()
            self.keybindings_changed.emit()

    def set_connected(self, state: bool):
        if self.is_connected != state:
            self.is_connected = state
            self.connection_changed.emit()

    def set_battery(self, level: int, charging: bool = False):
        self.battery_level = max(0, min(100, level))
        self.is_charging = charging
        self.battery_changed.emit()

    def get_battery_icon_name(self) -> str:
        if self.battery_level > 80:
            return "battery_full"
        elif self.battery_level > 40:
            return "battery_high"
        elif self.battery_level > 15:
            return "battery_low"
        return "battery_alert"
