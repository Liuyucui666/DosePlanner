"""
日志配置管理
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
):
    """
    设置日志配置

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        rotation: 日志文件轮转大小
        retention: 日志保留时间

    Returns:
        配置好的日志器
    """
    # 移除默认处理器
    logger.remove()

    # 添加控制台处理器
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        colorize=True,
    )

    # 添加文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_path),
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation=rotation,
            retention=retention,
            compression="gz",
        )

    # 设置异常追踪
    logger.add(
        sys.stderr,
        level="ERROR",
        format="<red>{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}</red>",
        colorize=True,
    )

    return logger


def get_logger(module_name: str = None):
    """
    获取模块日志器

    Args:
        module_name: 模块名称

    Returns:
        loguru日志器
    """
    if module_name:
        return logger.bind(module=module_name)
    return logger


# 设置全局异常处理
def setup_exception_handling():
    """设置全局异常处理"""

    import traceback

    def handle_exception(exc_type, exc_value, exc_traceback):
        """处理未捕获的异常"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error(
            "未捕获的异常: {exc_type}: {exc_value}",
            exc_type=exc_type.__name__,
            exc_value=exc_value,
        )

    sys.excepthook = handle_exception


# 在导入时设置异常处理
setup_exception_handling()