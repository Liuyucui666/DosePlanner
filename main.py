#!/usr/bin/env python3
"""
剂量计划软件主入口点
"""

import sys
import os
import logging
from pathlib import Path


from config.settings import Settings
from gui.main_window import MainWindow
from utils.logging_config import setup_logging
from data.database import init_database

# 配置日志
logger = setup_logging()

def main():
    """应用程序主函数"""
    try:
        # 加载配置
        settings = Settings()

        # 创建应用程序
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt

        # 设置高DPI支持
        # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName("Dose Planner")
        app.setOrganizationName("Medical Physics")
        app.setApplicationVersion("1.0.0")

        # 设置应用程序样式
        app.setStyle("Fusion")

        # 初始化数据库（自动创建表、插入默认籽源类型）
        init_database()

        # 创建主窗口
        window = MainWindow(settings)
        window.show()

        logger.info("应用程序启动成功")

        # 运行事件循环
        return_code = app.exec()

        logger.info(f"应用程序退出，返回码: {return_code}")
        return return_code

    except Exception as e:
        logger.exception("应用程序启动失败")

        # 显示错误消息
        from PySide6.QtWidgets import QMessageBox
        error_app = QApplication.instance() or QApplication([])
        QMessageBox.critical(
            None,
            "启动错误",
            f"应用程序启动失败:\n{str(e)}\n\n请查看日志文件获取详细信息。"
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())