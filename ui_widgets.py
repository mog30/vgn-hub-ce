from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QPushButton, QWidget, QMenu, QWidgetAction,
                             QVBoxLayout, QHBoxLayout, QLabel, QComboBox)

class HoldableButton(QPushButton):
    held = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._timer.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._timer.isActive():
                self._timer.stop()
            else:
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def _on_timeout(self):
        self.held.emit()

class ClickableWidget(QWidget):
    clicked = Signal(object)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(event.globalPosition().toPoint())
        super().mousePressEvent(event)

class SettingsMenu(QMenu):
    def __init__(self, parent, locale_manager, theme_manager):
        super().__init__(parent)
        self.locale_manager = locale_manager
        self.theme_manager = theme_manager

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.container = QWidget()
        self.container.setObjectName("settings_container")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(10)

        self.title_label = QLabel(self.locale_manager.tr("settings_title", "Настройки"))
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.layout.addWidget(self.title_label)

        # Выбор языка
        lang_layout = QHBoxLayout()
        self.lbl_lang = QLabel(self.locale_manager.tr("language_label", "Язык интерфейса:"))
        self.lbl_lang.setStyleSheet("font-size: 11px;")
        self.combo_lang = QComboBox()
        self.combo_lang.setFixedHeight(28)
        self.combo_lang.setCursor(Qt.PointingHandCursor)

        self.populate_languages()
        self.combo_lang.currentIndexChanged.connect(self._on_language_changed)

        lang_layout.addWidget(self.lbl_lang)
        lang_layout.addWidget(self.combo_lang)
        self.layout.addLayout(lang_layout)

        # Выбор темы
        theme_layout = QHBoxLayout()
        self.lbl_theme = QLabel(self.locale_manager.tr("theme_label", "Тема:"))
        self.lbl_theme.setStyleSheet("font-size: 11px;")
        self.combo_theme = QComboBox()
        self.combo_theme.setFixedHeight(28)
        self.combo_theme.setCursor(Qt.PointingHandCursor)

        self.populate_themes()
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)

        theme_layout.addWidget(self.lbl_theme)
        theme_layout.addWidget(self.combo_theme)
        self.layout.addLayout(theme_layout)

        action = QWidgetAction(self)
        action.setDefaultWidget(self.container)
        self.addAction(action)

        self.locale_manager.language_changed.connect(self.update_translations)

    def populate_languages(self):
        self.combo_lang.blockSignals(True)
        self.combo_lang.clear()
        self.locale_manager.scan_locales()

        for code, info in self.locale_manager.available_locales.items():
            self.combo_lang.addItem(info["name"], code)

        idx = self.combo_lang.findData(self.locale_manager.current_locale_code)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.blockSignals(False)

    def populate_themes(self):
        self.combo_theme.blockSignals(True)
        self.combo_theme.clear()
        self.combo_theme.addItem(self.locale_manager.tr("theme_auto", "Авто (системная)"), "auto")
        self.combo_theme.addItem(self.locale_manager.tr("theme_dark", "Тёмная"), "dark")
        self.combo_theme.addItem(self.locale_manager.tr("theme_light", "Светлая"), "light")

        idx = self.combo_theme.findData(self.theme_manager.theme_mode)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)
        self.combo_theme.blockSignals(False)

    def _on_language_changed(self, index):
        code = self.combo_lang.itemData(index)
        if code:
            self.locale_manager.set_language(code)

    def _on_theme_changed(self, index):
        mode = self.combo_theme.itemData(index)
        if mode:
            self.theme_manager.set_theme_mode(mode)

    def update_translations(self):
        self.title_label.setText(self.locale_manager.tr("settings_title", "Настройки"))
        self.lbl_lang.setText(self.locale_manager.tr("language_label", "Язык интерфейса:"))
        self.lbl_theme.setText(self.locale_manager.tr("theme_label", "Тема:"))
        self.populate_themes()
