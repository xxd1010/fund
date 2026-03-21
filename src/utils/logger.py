"""
统一日志配置模块 - 使用 loguru
提供项目全局的日志配置和logger实例
"""
import sys
from pathlib import Path
from loguru import logger

# 移除默认处理器
logger.remove()

# 日志格式配置
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

LOG_FORMAT_FILE = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# 确保日志目录存在
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(
    level: str = "INFO",
    log_file: str = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    colorize: bool = True
):
    """配置全局日志
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选，默认为 logs/app.log）
        rotation: 日志文件轮转大小/时间
        retention: 日志文件保留时间
        colorize: 是否启用颜色输出
    """
    # 清除已有处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=level.upper(),
        colorize=colorize,
        enqueue=True  # 线程安全
    )
    
    # 添加文件处理器
    if log_file is None:
        log_file = LOG_DIR / "app_{time:YYYY-MM-DD}.log"
    
    logger.add(
        str(log_file),
        format=LOG_FORMAT_FILE,
        level="DEBUG",  # 文件中保存更详细的日志
        rotation=rotation,
        retention=retention,
        compression="zip",
        encoding="utf-8",
        enqueue=True  # 线程安全
    )
    
    return logger


def get_logger(name: str = None):
    """获取日志记录器
    
    Args:
        name: 模块名称（可选，用于日志标识）
    
    Returns:
        配置好的 logger 实例
    """
    if name:
        return logger.bind(name=name)
    return logger


# 默认配置 - 控制台输出
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level="INFO",
    colorize=True,
    enqueue=True
)

# 默认配置 - 文件输出
logger.add(
    str(LOG_DIR / "app_{time:YYYY-MM-DD}.log"),
    format=LOG_FORMAT_FILE,
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True
)


__all__ = ["logger", "setup_logger", "get_logger"]
