# Author: 郝津德
"""应用日志格式配置。"""

import logging


def configure_logging() -> None:
    """设置应用日志格式和级别；无参数和返回值。"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

