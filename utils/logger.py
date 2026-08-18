"""接口自动化框架统一日志初始化模块。

本模块建立控制台日志和按大小轮转的文件日志，并在启动时清理 30 天前的历史
日志。其他框架模块统一导入 ``logs`` 使用同一个 logger，避免重复添加 handler。
"""
from __future__ import annotations

import datetime
import logging
import os
import time
from logging.handlers import RotatingFileHandler

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_PATH, exist_ok=True)


class RecordLog:
    """创建并维护框架统一的滚动日志记录器。"""

    def __init__(self, log_path=LOG_PATH, level=logging.DEBUG) -> None:
        """保存日志目录和最低文件日志级别，并清理过期文件。"""
        self.log_path = log_path
        self.level = level
        self._clean_old_logs()

    def _clean_old_logs(self) -> None:
        """删除超过 30 天的框架日志文件。"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=30)).timestamp()
        if os.path.exists(self.log_path):
            for name in os.listdir(self.log_path):
                path = os.path.join(self.log_path, name)
                if os.path.isfile(path) and os.path.getctime(path) < cutoff:
                    os.remove(path)

    def get_logger(self) -> logging.Logger:
        """返回单例风格的框架 Logger，并在首次调用时配置 handler。"""
        logger = logging.getLogger("api_autotest")
        # 同一个进程多次 import 时复用已有 handler，防止一条日志重复打印。
        if logger.handlers:
            return logger
        logger.setLevel(self.level)
        fmt = logging.Formatter(
            "%(levelname)s - %(asctime)s - %(filename)s:%(lineno)d "
            "-[%(module)s:%(funcName)s] - %(message)s"
        )
        log_file = os.path.join(self.log_path, f"test.{time.strftime('%Y%m%d')}.log")
        file_handler = RotatingFileHandler(
            log_file,
            mode="a",
            maxBytes=5_242_880,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(fmt)
        logger.addHandler(stream_handler)
        return logger


logs = RecordLog().get_logger()
