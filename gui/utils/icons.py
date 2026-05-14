"""
图标管理
"""

from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, QSize


class IconManager:
    """图标管理器"""

    _icons = {}
    _icon_size = 24

    @classmethod
    def get_icon(cls, name: str, size: int = None) -> QIcon:
        """
        获取图标

        Args:
            name: 图标名称
            size: 图标大小

        Returns:
            QIcon对象
        """
        if size is None:
            size = cls._icon_size

        cache_key = f"{name}_{size}"
        if cache_key in cls._icons:
            return cls._icons[cache_key]

        # 创建图标
        icon = cls._create_icon(name, size)
        cls._icons[cache_key] = icon
        return icon

    @classmethod
    def _create_icon(cls, name: str, size: int) -> QIcon:
        """创建图标"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 根据名称绘制不同图标
        if name == "open":
            cls._draw_folder_icon(painter, size)
        elif name == "save":
            cls._draw_save_icon(painter, size)
        elif name == "calculate":
            cls._draw_calculate_icon(painter, size)
        elif name == "zoom_in":
            cls._draw_zoom_in_icon(painter, size)
        elif name == "zoom_out":
            cls._draw_zoom_out_icon(painter, size)
        elif name == "fit":
            cls._draw_fit_icon(painter, size)
        elif name == "screenshot":
            cls._draw_camera_icon(painter, size)
        elif name == "reset_view":
            cls._draw_reset_view_icon(painter, size)
        elif name == "app":
            cls._draw_app_icon(painter, size)
        else:
            cls._draw_default_icon(painter, size)

        painter.end()

        return QIcon(pixmap)

    @staticmethod
    def _draw_folder_icon(painter: QPainter, size: int):
        """绘制文件夹图标"""
        margin = size * 0.2
        painter.setPen(QPen(QColor(100, 180, 255), 1.5))
        painter.setBrush(QColor(100, 180, 255, 180))

        # 文件夹主体
        painter.drawRect(int(margin), int(size * 0.35),
                         int(size - margin * 2), int(size * 0.5))

        # 文件夹标签
        points = [
            (margin + 2, size * 0.35),
            (margin + 2, size * 0.25),
            (size * 0.4, size * 0.25),
            (size * 0.5, size * 0.35),
        ]

    @staticmethod
    def _draw_save_icon(painter: QPainter, size: int):
        """绘制保存图标"""
        margin = size * 0.2
        painter.setPen(QPen(QColor(100, 200, 150), 1.5))
        painter.setBrush(QColor(100, 200, 150, 180))

        # 磁盘形状
        painter.drawRect(int(margin), int(margin),
                         int(size - margin * 2), int(size - margin * 2))

        # 磁盘细节
        painter.setPen(QPen(QColor(80, 160, 120), 1))
        painter.drawLine(int(size * 0.35), int(margin + 2),
                         int(size * 0.35), int(size * 0.45))

    @staticmethod
    def _draw_calculate_icon(painter: QPainter, size: int):
        """绘制计算图标"""
        margin = size * 0.2
        painter.setPen(QPen(QColor(255, 180, 50), 2))
        painter.setBrush(Qt.NoBrush)

        # 公式符号
        font = QFont()
        font.setPixelSize(int(size * 0.5))
        painter.setFont(font)
        painter.drawText(int(margin), int(margin),
                         int(size - margin * 2), int(size - margin * 2),
                         Qt.AlignCenter, "f(x)")

    @staticmethod
    def _draw_zoom_in_icon(painter: QPainter, size: int):
        """绘制放大图标"""
        center = size * 0.35
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(Qt.NoBrush)

        # 放大镜
        painter.drawEllipse(int(center - size * 0.15), int(center - size * 0.15),
                            int(size * 0.3), int(size * 0.3))

        # 手柄
        painter.drawLine(int(center + size * 0.15), int(center + size * 0.15),
                         int(size * 0.75), int(size * 0.75))

        # +号
        painter.drawLine(int(size * 0.35), int(size * 0.7),
                         int(size * 0.35), int(size * 0.9))
        painter.drawLine(int(size * 0.25), int(size * 0.8),
                         int(size * 0.45), int(size * 0.8))

    @staticmethod
    def _draw_zoom_out_icon(painter: QPainter, size: int):
        """绘制缩小图标"""
        center = size * 0.35
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(Qt.NoBrush)

        # 放大镜
        painter.drawEllipse(int(center - size * 0.15), int(center - size * 0.15),
                            int(size * 0.3), int(size * 0.3))

        # 手柄
        painter.drawLine(int(center + size * 0.15), int(center + size * 0.15),
                         int(size * 0.75), int(size * 0.75))

        # -号
        painter.drawLine(int(size * 0.25), int(size * 0.8),
                         int(size * 0.45), int(size * 0.8))

    @staticmethod
    def _draw_fit_icon(painter: QPainter, size: int):
        """绘制适应图标"""
        margin = size * 0.15
        painter.setPen(QPen(QColor(200, 200, 200), 1.5))
        painter.setBrush(Qt.NoBrush)

        # 四个角的箭头
        arrow_size = size * 0.15
        painter.drawLine(int(margin), int(margin + arrow_size),
                         int(margin), int(margin))
        painter.drawLine(int(margin), int(margin),
                         int(margin + arrow_size), int(margin))

        painter.drawLine(int(size - margin), int(margin + arrow_size),
                         int(size - margin), int(margin))
        painter.drawLine(int(size - margin), int(margin),
                         int(size - margin - arrow_size), int(margin))

        painter.drawLine(int(margin), int(size - margin - arrow_size),
                         int(margin), int(size - margin))
        painter.drawLine(int(margin), int(size - margin),
                         int(margin + arrow_size), int(size - margin))

        painter.drawLine(int(size - margin), int(size - margin - arrow_size),
                         int(size - margin), int(size - margin))
        painter.drawLine(int(size - margin), int(size - margin),
                         int(size - margin - arrow_size), int(size - margin))

    @staticmethod
    def _draw_camera_icon(painter: QPainter, size: int):
        """绘制相机图标"""
        margin = size * 0.2
        painter.setPen(QPen(QColor(200, 200, 200), 1.5))
        painter.setBrush(QColor(200, 200, 200, 100))

        # 相机主体
        painter.drawRect(int(margin), int(size * 0.35),
                         int(size - margin * 2), int(size * 0.45))

        # 闪光灯
        painter.drawRect(int(size * 0.55), int(size * 0.3),
                         int(size * 0.2), int(size * 0.1))

        # 镜头
        painter.drawEllipse(int(size * 0.3), int(size * 0.4),
                            int(size * 0.4), int(size * 0.3))

    @staticmethod
    def _draw_reset_view_icon(painter: QPainter, size: int):
        """绘制重置视角图标"""
        margin = size * 0.15
        painter.setPen(QPen(QColor(200, 200, 200), 1.5))
        painter.setBrush(Qt.NoBrush)

        # 圆形箭头
        painter.drawArc(int(margin), int(margin),
                        int(size - margin * 2), int(size - margin * 2),
                        0, 270 * 16)

        # 箭头
        painter.drawLine(int(size * 0.8), int(margin),
                         int(size * 0.9), int(margin))
        painter.drawLine(int(size * 0.8), int(margin),
                         int(size * 0.8), int(size * 0.1))

    @staticmethod
    def _draw_app_icon(painter: QPainter, size: int):
        """绘制应用图标"""
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 120, 212))

        # 辐射符号
        painter.drawEllipse(int(size * 0.3), int(size * 0.3),
                            int(size * 0.4), int(size * 0.4))

        # 中心点
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(int(size * 0.42), int(size * 0.42),
                            int(size * 0.16), int(size * 0.16))

    @staticmethod
    def _draw_default_icon(painter: QPainter, size: int):
        """绘制默认图标"""
        margin = size * 0.2
        painter.setPen(QPen(QColor(150, 150, 150), 1.5))
        painter.setBrush(QColor(150, 150, 150, 100))
        painter.drawRect(int(margin), int(margin),
                         int(size - margin * 2), int(size - margin * 2))