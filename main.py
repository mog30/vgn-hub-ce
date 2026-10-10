import os
import sys

os.environ["QSG_RHI_BACKEND"] = "vulkan"
os.environ["OS_CHROMIUM_FLAGS"] = "--logging-level=3"

from PySide6.QtCore import Qt, QSize, Slot, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QKeySequence, QShortcut, QFontDatabase, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                             QSlider, QListWidget, QComboBox, QButtonGroup,
                             QInputDialog, QMessageBox)

from locale_manager import LocaleManager
from theme_manager import ThemeManager, THEMES
from mouse_logic import MouseLogic, KEY_BINDINGS_MAP
from media_manager import MediaManager
from ui_widgets import HoldableButton, SettingsMenu

BASE_WIDTH = 860
BASE_HEIGHT = 520

KEY_BINDING_OPTIONS = [
    "ЛКМ", "ПКМ", "СКМ", "Вперед", "Назад",
    "DPI цикл", "DPI+", "DPI-", "Ничего", "Custom"
]


class SmoothSlider(QSlider):
    """Слайдер с плавной анимацией перемещения ползунка."""
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.anim = QPropertyAnimation(self, b"value")
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.setDuration(180)

    def setValueSmooth(self, value: int):
        self.anim.stop()
        self.anim.setStartValue(self.value())
        self.anim.setEndValue(value)
        self.anim.start()


class F1HubCEApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.base_dir, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)

        self.locale_mgr = LocaleManager(os.path.join(self.base_dir, "locales"))
        self.theme_mgr = ThemeManager(self.assets_dir)
        self.mouse_logic = MouseLogic()
        self.media_mgr = MediaManager(self.base_dir, self.assets_dir)

        self.load_custom_font()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(BASE_WIDTH, BASE_HEIGHT)
        self.setMinimumSize(540, 340)

        self.drag_position = None
        self._transition_generation = 0

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.root_container = QWidget(self.central_widget)
        self.root_container.setObjectName("rootContainer")

        self.root_container_layout = QVBoxLayout(self.root_container)
        self.root_container_layout.setContentsMargins(0, 0, 0, 0)
        self.root_container_layout.setSpacing(0)

        self.root_layout.addWidget(self.root_container)

        self.setup_topbar()

        self.stacked_widget = QStackedWidget(self.root_container)
        self.root_container_layout.addWidget(self.stacked_widget)

        self.setup_home_page()
        self.setup_video_page()
        self.setup_dashboard_page()

        self.stacked_widget.setCurrentIndex(0)

        self.theme_mgr.theme_changed.connect(self.on_theme_changed)
        self.locale_mgr.language_changed.connect(self.update_translations)

        # Сигналы логики устройства
        self.mouse_logic.connection_changed.connect(self.update_connection_visibility)
        self.mouse_logic.battery_changed.connect(self.update_dashboard_status)
        self.mouse_logic.dpi_changed.connect(self.update_dashboard_status)
        self.mouse_logic.hz_changed.connect(self.update_dashboard_status)
        self.mouse_logic.profiles_changed.connect(self.refresh_profiles_list)
        self.mouse_logic.keybindings_changed.connect(self.update_keybindings_ui)
        self.mouse_logic.apply_status_changed.connect(self.on_apply_status_finished)

        self.shortcut_skip = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_skip.activated.connect(self.go_to_dashboard)

        self.apply_style()
        self.update_connection_visibility()
        self.update_translations()

        # Фоновая проверка подключения мыши
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1500)
        self.poll_timer.timeout.connect(self.check_device_status)
        self.poll_timer.start()

        # Если мышь уже подключена при запуске — ждем 1 сек и запускаем анимацию
        if self.mouse_logic.is_connected:
            QTimer.singleShot(1000, self.trigger_connection_animation)

    def load_custom_font(self):
        font_path = os.path.join(self.assets_dir, "HarmonyOS_SansSC_Medium.ttf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            self.custom_font_name = font_families[0] if font_families else "Sans-Serif"
        else:
            self.custom_font_name = "Sans-Serif"

    def setup_topbar(self):
        self.topbar = QWidget(self.root_container)
        self.topbar.setFixedHeight(45)

        layout = QHBoxLayout(self.topbar)
        layout.setContentsMargins(15, 5, 10, 5)
        layout.setSpacing(10)

        self.logo_label = QLabel(self.topbar)
        self.logo_label.setTextFormat(Qt.RichText)
        self.logo_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.logo_label)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        self.tabs_container = QWidget(self.topbar)
        tabs_layout = QHBoxLayout(self.tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(6)

        for i in range(1, 4):
            btn = QPushButton(str(i))
            btn.setFixedSize(26, 26)
            btn.setCheckable(True)
            if i == 1:
                btn.setChecked(True)
            self.tabs_group.addButton(btn, i)
            tabs_layout.addWidget(btn)

        layout.addWidget(self.tabs_container)
        layout.addStretch(1)

        self.center_container = QWidget(self.topbar)
        center_h_layout = QHBoxLayout(self.center_container)
        center_h_layout.setContentsMargins(0, 0, 0, 0)
        center_h_layout.setSpacing(12)

        self.mouse_title = QLabel(self.mouse_logic.device_name, self.center_container)
        self.mouse_title.setStyleSheet("font-size: 13px; font-weight: bold;")

        self.usb_icon_label = QLabel(self.center_container)
        self.mouse_status = QLabel(self.center_container)

        self.battery_widget = QWidget(self.center_container)

        bat_info_layout = QHBoxLayout(self.battery_widget)
        bat_info_layout.setContentsMargins(0, 0, 0, 0)
        bat_info_layout.setSpacing(2)

        self.battery_icon_label = QLabel()
        self.battery_charge_indicator = QLabel()
        self.battery_charge_indicator.setFixedSize(14, 14)
        self.battery_charge_indicator.setAlignment(Qt.AlignCenter)

        self.battery_label = QLabel()
        self.battery_label.setFixedSize(38, 20)
        self.battery_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.battery_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        bat_info_layout.addWidget(self.battery_icon_label)
        bat_info_layout.addWidget(self.battery_charge_indicator)
        bat_info_layout.addWidget(self.battery_label)

        center_h_layout.addWidget(self.mouse_title)
        center_h_layout.addWidget(self.usb_icon_label)
        center_h_layout.addWidget(self.mouse_status)
        center_h_layout.addWidget(self.battery_widget)

        layout.addWidget(self.center_container)
        self.connected_widgets = [self.tabs_container, self.center_container]

        layout.addStretch(1)

        self.btn_theme = HoldableButton()
        self.btn_theme.clicked.connect(self.on_theme_btn_click)
        self.btn_theme.held.connect(self.on_theme_btn_hold)

        self.btn_settings = QPushButton()
        self.btn_settings.clicked.connect(self.show_settings_menu)

        self.btn_minimize = QPushButton()
        self.btn_close = QPushButton()

        for btn in [self.btn_theme, self.btn_settings, self.btn_minimize, self.btn_close]:
            btn.setFixedSize(28, 28)
            btn.setIconSize(QSize(16, 16))
            layout.addWidget(btn)

        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_close.clicked.connect(self.close)

        self.root_container_layout.addWidget(self.topbar)

    def setup_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        self.home_usb_icon_label = QLabel(page)
        self.home_usb_icon_label.setAlignment(Qt.AlignCenter)

        self.home_label = QLabel(page)
        self.home_label.setAlignment(Qt.AlignCenter)
        self.home_label.setStyleSheet("font-size: 16px; font-weight: 500;")

        layout.addWidget(self.home_usb_icon_label)
        layout.addWidget(self.home_label)
        self.stacked_widget.addWidget(page)

    def setup_video_page(self):
        page = QWidget()
        page.setObjectName("videoPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        web_view = self.media_mgr.create_web_view(page)
        self.media_mgr.bridge.video_ended.connect(self.go_to_dashboard)

        layout.addWidget(web_view)
        self.stacked_widget.addWidget(page)

    def setup_dashboard_page(self):
        self.dashboard_page = QWidget()

        main_dash_layout = QHBoxLayout(self.dashboard_page)
        main_dash_layout.setContentsMargins(10, 10, 10, 10)
        main_dash_layout.setSpacing(10)

        # Левая колонка
        self.left_column = QWidget()
        self.left_column.setFixedWidth(230)
        left_layout = QVBoxLayout(self.left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 1. Назначение кнопок
        self.buttons_card = QWidget()
        self.buttons_card.setObjectName("card")
        buttons_layout = QVBoxLayout(self.buttons_card)
        buttons_layout.setSpacing(6)

        buttons_header = QHBoxLayout()
        self.buttons_icon_label = QLabel()
        self.buttons_title = QLabel(self.buttons_card)
        self.buttons_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        buttons_header.addWidget(self.buttons_icon_label)
        buttons_header.addWidget(self.buttons_title)
        buttons_header.addStretch()
        buttons_layout.addLayout(buttons_header)

        self.btn_rows = []
        self.combo_boxes = []
        self.btn_keys = [
            ("btn_1", "btn_lmb"),
            ("btn_2", "btn_rmb"),
            ("btn_3", "btn_mmb"),
            ("btn_4", "btn_back"),
            ("btn_5", "btn_forward")
        ]

        for btn_id, locale_key in self.btn_keys:
            row_layout = QHBoxLayout()
            lbl = QLabel(self.buttons_card)
            lbl.setStyleSheet("font-size: 11px;")
            combo = QComboBox(self.buttons_card)
            combo.setFixedHeight(26)
            combo.setCursor(Qt.PointingHandCursor)
            combo.addItems(KEY_BINDING_OPTIONS)

            combo.currentTextChanged.connect(
                lambda text, b_id=btn_id: self.mouse_logic.set_key_binding(b_id, text)
            )

            row_layout.addWidget(lbl)
            row_layout.addWidget(combo)
            buttons_layout.addLayout(row_layout)
            self.btn_rows.append((lbl, locale_key, combo, btn_id))
            self.combo_boxes.append(combo)

        left_layout.addWidget(self.buttons_card)

        # 2. DPI и Hz
        self.dpi_hz_card = QWidget()
        self.dpi_hz_card.setObjectName("card")
        dpi_hz_layout = QVBoxLayout(self.dpi_hz_card)
        dpi_hz_layout.setSpacing(8)

        dpi_hz_header = QHBoxLayout()
        self.dpi_hz_icon_label = QLabel()
        self.dpi_hz_title = QLabel(self.dpi_hz_card)
        self.dpi_hz_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        dpi_hz_header.addWidget(self.dpi_hz_icon_label)
        dpi_hz_header.addWidget(self.dpi_hz_title)
        dpi_hz_header.addStretch()
        dpi_hz_layout.addLayout(dpi_hz_header)

        dpi_sub_layout = QHBoxLayout()
        current_dpi = self.mouse_logic.dpi_values[self.mouse_logic.dpi_index]
        self.dpi_val = QLabel(str(current_dpi), self.dpi_hz_card)
        self.dpi_val.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.lbl_dpi_tag = QLabel(self.dpi_hz_card)
        dpi_sub_layout.addWidget(self.lbl_dpi_tag)
        dpi_sub_layout.addWidget(self.dpi_val)
        dpi_sub_layout.addStretch()
        dpi_hz_layout.addLayout(dpi_sub_layout)

        self.dpi_slider = SmoothSlider(Qt.Horizontal, self.dpi_hz_card)
        self.dpi_slider.setRange(0, len(self.mouse_logic.dpi_values) - 1)
        self.dpi_slider.setValue(self.mouse_logic.dpi_index)
        self.dpi_slider.setCursor(Qt.PointingHandCursor)
        self.dpi_slider.setTracking(True)
        self.dpi_slider.valueChanged.connect(self.mouse_logic.set_dpi_index)
        dpi_hz_layout.addWidget(self.dpi_slider)

        hz_sub_layout = QHBoxLayout()
        current_hz = self.mouse_logic.hz_values[self.mouse_logic.hz_index]
        self.hz_val = QLabel(f"{current_hz} Hz", self.dpi_hz_card)
        self.hz_val.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.lbl_hz_tag = QLabel(self.dpi_hz_card)
        hz_sub_layout.addWidget(self.lbl_hz_tag)
        hz_sub_layout.addWidget(self.hz_val)
        hz_sub_layout.addStretch()
        dpi_hz_layout.addLayout(hz_sub_layout)

        self.hz_slider = SmoothSlider(Qt.Horizontal, self.dpi_hz_card)
        self.hz_slider.setRange(0, len(self.mouse_logic.hz_values) - 1)
        self.hz_slider.setValue(self.mouse_logic.hz_index)
        self.hz_slider.setCursor(Qt.PointingHandCursor)
        self.hz_slider.setTracking(True)
        self.hz_slider.valueChanged.connect(self.mouse_logic.set_hz_index)
        dpi_hz_layout.addWidget(self.hz_slider)

        left_layout.addWidget(self.dpi_hz_card)

        # 3. Кнопка «Применить настройки»
        self.btn_apply = QPushButton(self.left_column)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self.on_apply_clicked)
        left_layout.addWidget(self.btn_apply)

        left_layout.addStretch()

        # Центральная колонка
        self.center_column = QWidget()
        center_layout = QVBoxLayout(self.center_column)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.mouse_image_label = QLabel(self.center_column)
        self.mouse_image_label.setAlignment(Qt.AlignCenter)

        center_layout.addWidget(self.mouse_image_label)

        # Правая колонка
        self.right_column = QWidget()
        self.right_column.setFixedWidth(230)
        right_layout = QVBoxLayout(self.right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.profiles_card = QWidget()
        self.profiles_card.setObjectName("card")
        prof_layout = QVBoxLayout(self.profiles_card)
        prof_layout.setContentsMargins(10, 10, 10, 10)

        prof_header = QHBoxLayout()
        self.profiles_icon_label = QLabel()
        self.profiles_title = QLabel(self.profiles_card)
        self.profiles_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        prof_header.addWidget(self.profiles_icon_label)
        prof_header.addWidget(self.profiles_title)
        prof_header.addStretch()
        prof_layout.addLayout(prof_header)

        self.profiles_list = QListWidget(self.profiles_card)
        self.profiles_list.currentRowChanged.connect(self.on_profile_selected)
        prof_layout.addWidget(self.profiles_list, stretch=1)

        prof_buttons_layout = QHBoxLayout()
        prof_buttons_layout.setContentsMargins(0, 0, 0, 0)
        prof_buttons_layout.setSpacing(6)

        self.btn_add_profile = QPushButton()
        self.btn_rename_profile = QPushButton()
        self.btn_delete_profile = QPushButton()

        for btn in [self.btn_add_profile, self.btn_rename_profile, self.btn_delete_profile]:
            btn.setFixedSize(32, 32)
            btn.setIconSize(QSize(16, 16))
            btn.setCursor(Qt.PointingHandCursor)
            prof_buttons_layout.addWidget(btn)

        prof_buttons_layout.addStretch()

        self.btn_add_profile.clicked.connect(self.on_add_profile_dialog)
        self.btn_rename_profile.clicked.connect(self.on_rename_profile_dialog)
        self.btn_delete_profile.clicked.connect(self.on_delete_profile_dialog)

        prof_layout.addLayout(prof_buttons_layout)
        right_layout.addWidget(self.profiles_card)

        main_dash_layout.addWidget(self.left_column)
        main_dash_layout.addWidget(self.center_column, stretch=1)
        main_dash_layout.addWidget(self.right_column)

        self.stacked_widget.addWidget(self.dashboard_page)
        self.refresh_profiles_list()
        self.update_mouse_image()

    def check_device_status(self):
        """Периодическая проверка наличия устройства."""
        was_connected = self.mouse_logic.is_connected
        is_connected = self.mouse_logic.check_connection()

        if not was_connected and is_connected:
            self.trigger_connection_animation()
        elif was_connected and not is_connected:
            self.stacked_widget.setCurrentIndex(0)

    def update_mouse_image(self):
        target_w = self.width() if self.width() > 100 else BASE_WIDTH
        target_h = self.height() if self.height() > 100 else BASE_HEIGHT
        pixmap = self.media_mgr.load_scaled_mouse_pixmap(target_w, target_h)
        if pixmap:
            self.mouse_image_label.setPixmap(pixmap)
        else:
            self.mouse_image_label.setText(self.locale_mgr.tr("mouse_image_alt", "[ Изображение мыши ]"))
            self.mouse_image_label.setStyleSheet("color: #555; font-size: 16px;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_mouse_image()

    def refresh_profiles_list(self):
        self.profiles_list.blockSignals(True)
        self.profiles_list.clear()
        for prof in self.mouse_logic.profiles:
            self.profiles_list.addItem(prof)
        self.profiles_list.setCurrentRow(self.mouse_logic.current_profile_index)
        self.profiles_list.blockSignals(False)

    def on_profile_selected(self, row: int):
        if 0 <= row < len(self.mouse_logic.profiles):
            self.mouse_logic.select_profile_by_index(row)

    def on_add_profile_dialog(self):
        name, ok = QInputDialog.getText(self, self.locale_mgr.tr("new_profile", "Новый профиль"), "Введите имя профиля:")
        if ok and name.strip():
            self.mouse_logic.add_profile(name.strip())

    def on_rename_profile_dialog(self):
        row = self.profiles_list.currentRow()
        if 0 <= row < len(self.mouse_logic.profiles):
            old_name = self.mouse_logic.profiles[row]
            new_name, ok = QInputDialog.getText(self, self.locale_mgr.tr("rename_profile", "Переименование профиля"), "Новое имя:", text=old_name)
            if ok and new_name.strip() and new_name.strip() != old_name:
                self.mouse_logic.rename_profile(row, new_name.strip())

    def on_delete_profile_dialog(self):
        row = self.profiles_list.currentRow()
        if 0 <= row < len(self.mouse_logic.profiles):
            if len(self.mouse_logic.profiles) <= 1:
                QMessageBox.warning(self, "Ошибка", "Нельзя удалить единственный профиль!")
                return
            old_name = self.mouse_logic.profiles[row]
            reply = QMessageBox.question(self, "Удаление", f"Удалить профиль '{old_name}'?")
            if reply == QMessageBox.Yes:
                self.mouse_logic.delete_profile(row)

    def on_apply_clicked(self):
        self.btn_apply.setText(self.locale_mgr.tr("applying", "Сохранение..."))
        self.btn_apply.setEnabled(False)
        self.mouse_logic.apply_current_settings()

    def on_apply_status_finished(self, success: bool):
        self.btn_apply.setEnabled(True)
        self.btn_apply.setText(self.locale_mgr.tr("btn_apply", "Применить настройки"))
        if success:
            QMessageBox.information(self, "Успех", "Настройки успешно сохранены в устройство!")
        else:
            QMessageBox.warning(self, "Внимание", "Не удалось записать настройки в мышь (устройство не подключено). Изменения сохранены в файл профиля.")

    def update_keybindings_ui(self):
        for lbl, locale_key, combo, btn_id in self.btn_rows:
            action_name = self.mouse_logic.key_bindings.get(btn_id, "Custom")
            combo.blockSignals(True)
            idx = combo.findText(action_name)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText("Custom")
            combo.blockSignals(False)

    def update_translations(self):
        tr = self.locale_mgr.tr
        self.logo_label.setText(f'{tr("logo_title", "F1 HUB CE")} <span style="color: #ff6600;">•</span>')
        self.home_label.setText(tr("connect_device", "Подключите устройство"))

        self.buttons_title.setText(tr("buttons_title", "Кнопки"))
        self.dpi_hz_title.setText(tr("dpi_hz_title", "DPI и Частота"))
        self.lbl_dpi_tag.setText(tr("dpi_label", "DPI:"))
        self.lbl_hz_tag.setText(tr("hz_label", "Частота:"))
        self.profiles_title.setText(tr("profiles_title", "Профили"))
        self.btn_apply.setText(tr("btn_apply", "Применить настройки"))

        for lbl, locale_key, combo, btn_id in self.btn_rows:
            lbl.setText(tr(locale_key, locale_key))

        self.refresh_profiles_list()
        self.update_dashboard_status()

    def update_dashboard_status(self):
        effective_theme = self.theme_mgr.get_effective_theme()
        color = THEMES[effective_theme]["icon_color"]
        tr = self.locale_mgr.tr

        # Выводим настоящее название устройства
        self.mouse_title.setText(self.mouse_logic.device_name)

        # Вывод иконки usb_off на главной странице с учетом цвета темы
        self.home_usb_icon_label.setPixmap(
            self.theme_mgr.get_tinted_icon("usb_off", color, QSize(64, 64)).pixmap(64, 64)
        )

        usb_icon = "usb" if self.mouse_logic.is_connected else "usb_off"
        self.usb_icon_label.setPixmap(self.theme_mgr.get_tinted_icon(usb_icon, color, QSize(16, 16)).pixmap(16, 16))

        if self.mouse_logic.is_connected:
            self.mouse_status.setText(tr("connected", "● Подключено"))
            self.mouse_status.setStyleSheet("font-size: 11px; color: #00e676;")
        else:
            self.mouse_status.setText(tr("disconnected", "○ Отключено"))
            self.mouse_status.setStyleSheet("font-size: 11px; color: #ff5252;")

        # Реальный процент заряда и статус зарядки
        bat_icon = self.mouse_logic.get_battery_icon_name()
        self.battery_icon_label.setPixmap(self.theme_mgr.get_tinted_icon(bat_icon, color, QSize(18, 18)).pixmap(18, 18))
        self.battery_label.setText(f"{self.mouse_logic.battery_level}%")

        if self.mouse_logic.is_charging:
            self.battery_charge_indicator.setPixmap(self.theme_mgr.get_tinted_icon("battery_charging", "#ffeb3b", QSize(14, 14)).pixmap(14, 14))
        else:
            transparent_pixmap = QPixmap(14, 14)
            transparent_pixmap.fill(Qt.transparent)
            self.battery_charge_indicator.setPixmap(transparent_pixmap)

        self.buttons_icon_label.setPixmap(self.theme_mgr.get_tinted_icon("buttons", color, QSize(18, 18)).pixmap(18, 18))
        self.dpi_hz_icon_label.setPixmap(self.theme_mgr.get_tinted_icon("speed", color, QSize(18, 18)).pixmap(18, 18))
        self.profiles_icon_label.setPixmap(self.theme_mgr.get_tinted_icon("profiles", color, QSize(18, 18)).pixmap(18, 18))

        self.btn_add_profile.setIcon(self.theme_mgr.get_tinted_icon("add", color))
        self.btn_rename_profile.setIcon(self.theme_mgr.get_tinted_icon("rename", color))
        self.btn_delete_profile.setIcon(self.theme_mgr.get_tinted_icon("delete", color))

        current_dpi = self.mouse_logic.dpi_values[self.mouse_logic.dpi_index] if self.mouse_logic.dpi_index < len(self.mouse_logic.dpi_values) else 800
        current_hz = self.mouse_logic.hz_values[self.mouse_logic.hz_index] if self.mouse_logic.hz_index < len(self.mouse_logic.hz_values) else 1000
        self.dpi_val.setText(str(current_dpi))
        self.hz_val.setText(f"{current_hz} Hz")

        self.dpi_slider.blockSignals(True)
        self.dpi_slider.setRange(0, max(0, len(self.mouse_logic.dpi_values) - 1))
        self.dpi_slider.setValueSmooth(self.mouse_logic.dpi_index)
        self.dpi_slider.blockSignals(False)

        self.hz_slider.blockSignals(True)
        self.hz_slider.setRange(0, max(0, len(self.mouse_logic.hz_values) - 1))
        self.hz_slider.setValueSmooth(self.mouse_logic.hz_index)
        self.hz_slider.blockSignals(False)

        self.update_keybindings_ui()

    def update_topbar_icons(self):
        effective_theme = self.theme_mgr.get_effective_theme()
        color = THEMES[effective_theme]["icon_color"]

        mode = self.theme_mgr.theme_mode
        theme_icon = "light_mode_auto" if mode == "auto" else ("dark_mode" if mode == "dark" else "light_mode")

        self.btn_theme.setIcon(self.theme_mgr.get_tinted_icon(theme_icon, color))
        self.btn_settings.setIcon(self.theme_mgr.get_tinted_icon("settings", color))
        self.btn_minimize.setIcon(self.theme_mgr.get_tinted_icon("minimize", color))
        self.btn_close.setIcon(self.theme_mgr.get_tinted_icon("close", color))

    def update_connection_visibility(self):
        visible = self.mouse_logic.is_connected
        for widget in self.connected_widgets:
            widget.setVisible(visible)

    def apply_style(self):
        effective_theme = self.theme_mgr.get_effective_theme()
        theme_colors = THEMES[effective_theme]

        stylesheet = self.theme_mgr.get_stylesheet(self.custom_font_name)

        primary = theme_colors.get('primary', '#ff6600')
        primary_hover = theme_colors.get('primary_hover', '#ff8533')
        primary_pressed = theme_colors.get('primary_pressed', '#cc5200')

        btn_apply_style = f"""
            QPushButton {{
                background-color: {primary};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {primary_hover};
            }}
            QPushButton:pressed {{
                background-color: {primary_pressed};
            }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #888888;
            }}
        """
        self.setStyleSheet(stylesheet)
        self.btn_apply.setStyleSheet(btn_apply_style)

        self.update_topbar_icons()
        self.update_dashboard_status()

    def on_theme_changed(self):
        self.apply_style()

    def on_theme_btn_click(self):
        current = self.theme_mgr.get_effective_theme()
        next_theme = "light" if current == "dark" else "dark"
        self.theme_mgr.set_theme_mode(next_theme)

    def on_theme_btn_hold(self):
        self.theme_mgr.set_theme_mode("auto")

    def show_settings_menu(self):
        menu = SettingsMenu(self, self.locale_mgr, self.theme_mgr)
        pos = self.btn_settings.mapToGlobal(QPoint(0, self.btn_settings.height() + 4))

        theme = THEMES[self.theme_mgr.get_effective_theme()]
        menu.setStyleSheet(f"""
            QMenu {{ background: transparent; border: none; }}
            QWidget#settings_container {{
                background-color: {theme['card_bg']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
            }}
        """)
        menu.exec(pos)

    def trigger_connection_animation(self):
        self._transition_generation += 1
        generation = self._transition_generation

        self.stacked_widget.setCurrentIndex(1)
        self.media_mgr.play_forward()

        QTimer.singleShot(12000, lambda: self._connection_timeout(generation))

    def _connection_timeout(self, generation):
        if generation == self._transition_generation and self.stacked_widget.currentIndex() == 1:
            self.go_to_dashboard()

    @Slot()
    def go_to_dashboard(self):
        QTimer.singleShot(0, self._perform_switch_to_dashboard)

    def _perform_switch_to_dashboard(self):
        self.update_dashboard_status()
        self.stacked_widget.setCurrentIndex(2)
        self.animate_dashboard_in()

    def animate_dashboard_in(self):
        widgets = [self.left_column, self.center_column, self.right_column]
        for index, widget in enumerate(widgets):
            final = widget.pos()
            dx = (-22 if index == 0 else (22 if index == 2 else 0))
            start_pos = final + QPoint(dx, 12)
            widget.move(start_pos)
            anim = QPropertyAnimation(widget, b"pos", self)
            anim.setStartValue(start_pos)
            anim.setEndValue(final)
            anim.setDuration(460 + index * 55)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() <= 45:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = F1HubCEApp()
    window.show()
    sys.exit(app.exec())
