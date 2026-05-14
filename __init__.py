"""
介入科剂量计划软件

用于放射性籽源植入治疗的剂量计划桌面软件。
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

import logging

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

__all__ = [
    'logger',
]
