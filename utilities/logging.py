import sys
import os
from loguru import logger

def setup_logger():
    # 1. 清除并重置
    logger.remove()

    # 2. 确保日志目录存在
    log_dir = "config_logs"
    os.makedirs(log_dir, exist_ok=True)

    # 3. 控制台输出：保持不变，用于实时查看
    logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        format="{time:YYYY-MM-DD HH:mm:ss} - {level: <8} - {message}"
    )

    # 4. 错误日志文件：专门记录 ERROR 及更高级别的日志
    logger.add(
        os.path.join(log_dir, "error.log"),
        level="ERROR",  # 门槛是 ERROR
        format="{time:YYYY-MM-DD HH:mm:ss} - {level: <8} - {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8"
    )

    # 5. 信息日志文件：记录严格低于 ERROR 级别的所有日志
    logger.add(
        os.path.join(log_dir, "info.log"),
        level="INFO",   # 门槛是 INFO，会处理 INFO, WARNING, ERROR...
        # 过滤器会进行二次筛选，只允许级别数值小于 ERROR 的通过
        filter=lambda record: record["level"].no < logger.level("ERROR").no,
        format="{time:YYYY-MM-DD HH:mm:ss} - {level: <8} - {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )

# 执行配置
setup_logger()
