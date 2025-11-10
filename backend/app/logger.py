from loguru import logger


def setup_logger():
    """
    初始化结构化日志配置。

    无参数。
    返回值：无。
    """
    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO",
    )
    return logger