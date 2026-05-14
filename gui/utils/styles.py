"""
应用程序样式表
"""


class StyleSheet:
    """样式表管理"""

    MAIN_STYLE = """
    QMainWindow {
        background-color: #2b2b2b;
    }

    QMenuBar {
        background-color: #3c3c3c;
        color: #dcdcdc;
        border-bottom: 1px solid #555;
    }

    QMenuBar::item:selected {
        background-color: #505050;
    }

    QMenu {
        background-color: #3c3c3c;
        color: #dcdcdc;
        border: 1px solid #555;
    }

    QMenu::item:selected {
        background-color: #0078d4;
    }

    QToolBar {
        background-color: #3c3c3c;
        border-bottom: 1px solid #555;
        spacing: 4px;
        padding: 2px;
    }

    QStatusBar {
        background-color: #3c3c3c;
        color: #dcdcdc;
        border-top: 1px solid #555;
    }

    QGroupBox {
        font-weight: bold;
        color: #dcdcdc;
        border: 1px solid #555;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 16px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 8px;
        color: #4fc3f7;
    }

    QLabel {
        color: #dcdcdc;
    }

    QPushButton {
        background-color: #505050;
        color: #dcdcdc;
        border: 1px solid #666;
        border-radius: 3px;
        padding: 5px 12px;
        min-height: 24px;
    }

    QPushButton:hover {
        background-color: #606060;
        border-color: #0078d4;
    }

    QPushButton:pressed {
        background-color: #404040;
    }

    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background-color: #3c3c3c;
        color: #dcdcdc;
        border: 1px solid #555;
        border-radius: 3px;
        padding: 3px 5px;
        min-height: 20px;
    }

    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
        border-color: #0078d4;
    }

    QComboBox::drop-down {
        border: none;
        width: 20px;
    }

    QComboBox QAbstractItemView {
        background-color: #3c3c3c;
        color: #dcdcdc;
        selection-background-color: #0078d4;
    }

    QCheckBox {
        color: #dcdcdc;
        spacing: 8px;
    }

    QCheckBox::indicator {
        width: 16px;
        height: 16px;
    }

    QRadioButton {
        color: #dcdcdc;
        spacing: 8px;
    }

    QSlider::groove:horizontal {
        height: 6px;
        background: #3c3c3c;
        border-radius: 3px;
    }

    QSlider::handle:horizontal {
        width: 14px;
        height: 14px;
        background: #0078d4;
        border-radius: 7px;
        margin: -4px 0;
    }

    QSlider::sub-page:horizontal {
        background: #0078d4;
        border-radius: 3px;
    }

    QScrollArea {
        border: none;
    }

    QScrollBar:vertical {
        background: #2b2b2b;
        width: 10px;
    }

    QScrollBar::handle:vertical {
        background: #555;
        border-radius: 5px;
        min-height: 20px;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QSplitter::handle {
        background: #555;
    }

    QDockWidget {
        color: #dcdcdc;
        titlebar-close-icon: none;
    }

    QDockWidget::title {
        background-color: #3c3c3c;
        padding: 4px;
        border-bottom: 1px solid #555;
    }

    QListWidget {
        background-color: #3c3c3c;
        color: #dcdcdc;
        border: 1px solid #555;
        border-radius: 3px;
    }

    QListWidget::item:selected {
        background-color: #0078d4;
    }

    QListWidget::item:hover {
        background-color: #505050;
    }
    """

    @classmethod
    def get_style(cls) -> str:
        """获取样式表"""
        return cls.MAIN_STYLE

    @classmethod
    def get_dark_style(cls) -> str:
        """获取暗色主题样式"""
        return cls.MAIN_STYLE

    @classmethod
    def get_button_style(cls, color: str = "#0078d4") -> str:
        """获取按钮样式"""
        return f"""
        QPushButton {{
            background-color: {color};
            color: white;
            border: none;
            border-radius: 3px;
            padding: 5px 12px;
            min-height: 24px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {self._lighten_color(color)};
        }}
        QPushButton:pressed {{
            background-color: {self._darken_color(color)};
        }}
        """

    @staticmethod
    def _lighten_color(hex_color: str, factor: float = 0.2) -> str:
        """提亮颜色"""
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)

            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))

            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return hex_color

    @staticmethod
    def _darken_color(hex_color: str, factor: float = 0.2) -> str:
        """加深颜色"""
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)

            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))

            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return hex_color