import os
from PySide6.QtCore import QObject, Signal, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QGuiApplication
from PySide6.QtSvg import QSvgRenderer

THEMES = {
    "dark": {
        "bg": "#0b0c0e",
        "card_bg": "rgba(20, 22, 28, 245)",
        "card_bg2": "rgba(12, 14, 18, 245)",
        "input_bg": "rgba(8, 10, 14, 230)",
        "accent": "#ff7a18",
        "accent_soft": "rgba(255, 122, 24, 55)",
        "text": "#e1e1e6",
        "subtext": "#80828d",
        "topbar_btn": "#1f2128",
        "topbar_btn_hover": "#2e323d",
        "border": "#3d4251",
        "active_border": "#ffffff",
        "slider_groove": "#2a1f18",
        "slider_handle": "#ffffff",
        "slider_accent": "#ff7a18",  # Оранжевый акцент
        "icon_color": "#e1e1e6"
    },
    "light": {
        "bg": "#f0f2f5",
        "card_bg": "rgba(250, 251, 253, 245)",
        "card_bg2": "rgba(235, 238, 243, 245)",
        "input_bg": "rgba(226, 229, 234, 230)",
        "accent": "#ff6600",
        "accent_soft": "rgba(255, 102, 0, 35)",
        "text": "#1a1a1e",
        "subtext": "#6c707e",
        "topbar_btn": "#e2e5ea",
        "topbar_btn_hover": "#d1d5db",
        "border": "#b0b4be",
        "active_border": "#1a1a1e",
        "slider_groove": "#f0d8c8",
        "slider_handle": "#ffffff",
        "slider_accent": "#ff6600",  # Оранжевый акцент
        "icon_color": "#1a1a1e"
    }
}

class ThemeManager(QObject):
    theme_changed = Signal()

    def __init__(self, assets_dir):
        super().__init__()
        self.assets_dir = assets_dir
        self.theme_mode = "auto"
        self._ensure_theme_assets()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_system_theme_changed)

    def _ensure_theme_assets(self):
        light_arrow = os.path.join(self.assets_dir, "arrow_drop_down_light.svg")
        if not os.path.exists(light_arrow):
            svg = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">\n  <path fill="#1a1a1e" d="M7 10l5 5 5-5z"/>\n</svg>\n'
            try:
                with open(light_arrow, "w", encoding="utf-8") as f:
                    f.write(svg)
            except OSError:
                pass

    def get_effective_theme(self):
        if self.theme_mode == "auto":
            scheme = QGuiApplication.styleHints().colorScheme()
            return "dark" if scheme == Qt.ColorScheme.Dark else "light"
        return self.theme_mode

    def set_theme_mode(self, mode):
        if self.theme_mode != mode:
            self.theme_mode = mode
            self.theme_changed.emit()

    def _on_system_theme_changed(self):
        if self.theme_mode == "auto":
            self.theme_changed.emit()

    def get_tinted_icon(self, icon_name, color_hex, size=QSize(16, 16)):
        icon_path = os.path.join(self.assets_dir, f"{icon_name}.svg")
        if not os.path.exists(icon_path):
            return QIcon()

        renderer = QSvgRenderer(icon_path)
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color_hex))
        painter.end()

        return QIcon(pixmap)

    def get_stylesheet(self, font_family="Sans-Serif"):
        effective_theme = self.get_effective_theme()
        t = THEMES[effective_theme]
        arrow_name = "arrow_drop_down_light.svg" if effective_theme == "light" else "arrow_drop_down.svg"
        arrow_svg_path = os.path.join(self.assets_dir, arrow_name).replace(os.sep, "/")

        return f"""
            * {{
                font-family: '{font_family}', sans-serif;
            }}

            QMainWindow {{
                background: transparent;
            }}

            QWidget#rootContainer {{
                background-color: {t['bg']};
                border: 1px solid {t['border']};
                border-radius: 16px;
            }}

            /* Тултипы в цвете активной темы */
            QToolTip {{
                background-color: {t['card_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}

            QWidget#videoPage {{
                background: transparent;
            }}

            QWidget {{
                color: {t['text']};
            }}

            QWidget#card {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {t['card_bg']},
                    stop:1 {t['card_bg2']}
                );
                border: 1px solid {t['border']};
                border-radius: 14px;
                padding: 10px;
            }}

            QWidget#card:hover {{
                border-color: {t['active_border']};
            }}

            QPushButton {{
                background-color: {t['topbar_btn']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                color: {t['text']};
                padding: 2px;
            }}

            QPushButton:hover {{
                background-color: {t['topbar_btn_hover']};
                border-color: {t['active_border']};
            }}

            QPushButton:pressed {{
                background-color: {t['active_border']};
                color: {t['bg']};
            }}

            QPushButton:checked {{
                background-color: {t['topbar_btn_hover']};
                border: 1px solid {t['active_border']};
            }}

            QListWidget {{
                background-color: {t['input_bg']};
                border: 1px solid {t['border']};
                border-radius: 9px;
                padding: 4px;
            }}

            QListWidget::item {{
                border-radius: 7px;
                padding: 7px;
            }}

            QListWidget::item:hover {{
                background: {t['topbar_btn_hover']};
            }}

            QListWidget::item:selected {{
                background: {t['accent_soft']};
                color: {t['text']};
            }}

            QComboBox {{
                background-color: {t['input_bg']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 4px 8px;
                color: {t['text']};
            }}

            QComboBox:hover {{
                border-color: {t['accent']};
                background-color: {t['topbar_btn_hover']};
            }}

            QComboBox:focus {{
                border: 1px solid {t['accent']};
                background-color: {t['input_bg']};
            }}

            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background: transparent;
            }}

            QComboBox::down-arrow {{
                image: url({arrow_svg_path});
                width: 16px;
                height: 16px;
            }}

            QComboBox QAbstractItemView {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                selection-background-color: {t['topbar_btn_hover']};
                selection-color: {t['text']};
                outline: none;
            }}

            /* Слайдер с оранжевым акцентом */
            QSlider {{
                background: transparent;
                min-height: 22px;
            }}

            QSlider::groove:horizontal {{
                height: 6px;
                background: {t['slider_groove']};
                border: 1px solid {t['accent_soft']};
                border-radius: 3px;
            }}

            QSlider::sub-page:horizontal {{
                background: {t['slider_accent']};
                border-radius: 3px;
            }}

            QSlider::add-page:horizontal {{
                background: {t['input_bg']};
                border-radius: 3px;
            }}

            QSlider::handle:horizontal {{
                background: {t['slider_handle']};
                border: 2px solid {t['slider_accent']};
                width: 15px;
                height: 15px;
                margin: -5px 0;
                border-radius: 8px;
            }}

            QSlider::handle:horizontal:hover {{
                background: {t['slider_accent']};
                border-color: {t['text']};
            }}

            QSlider::handle:horizontal:pressed {{
                background: {t['text']};
                border-color: {t['slider_accent']};
            }}

            QLabel {{
                background: transparent;
            }}
        """
