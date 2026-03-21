"""
代理池日志配置模块 - 使用 loguru
"""
import sys
from pathlib import Path
from typing import Optional
from loguru import logger


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


def setup_logger(
    name: str = "proxy_pool",
    level: str = "INFO",
    log_file: str = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> "logger":
    """配置日志记录器
    
    Args:
        name: 日志记录器名称（用于 loguru 的 bind）
        level: 日志级别
        log_file: 日志文件路径（可选）
        max_bytes: 单个日志文件最大字节数（对应 rotation）
        backup_count: 保留的旧日志文件数量（对应 retention）
        
    Returns:
        配置好的日志记录器
    """
    # 移除默认处理器
    logger.remove()
    
    # 控制台处理器
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level=level.upper(),
        colorize=True,
        enqueue=True
    )
    
    # 文件处理器（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 将 max_bytes 转换为 rotation 格式
        rotation_size = f"{max_bytes // (1024 * 1024)} MB" if max_bytes >= 1024 * 1024 else f"{max_bytes // 1024} KB"
        
        logger.add(
            str(log_file),
            format=LOG_FORMAT_FILE,
            level="DEBUG",
            rotation=rotation_size,
            retention=backup_count,
            compression="zip",
            encoding='utf-8',
            enqueue=True
        )
    
    return logger.bind(name=name)


def get_logger(name: str = "proxy_pool") -> "logger":
    """获取日志记录器"""
    return logger.bind(name=name)


class ProxyPoolLogger:
    """代理池专用日志记录器"""
    
    def __init__(self, name: str = "proxy_pool"):
        self.name = name
        self._log_file: Optional[str] = None
        self._configured = False
    
    def set_log_file(self, log_file: str):
        """设置日志文件"""
        self._log_file = log_file
        setup_logger(self.name, log_file=log_file)
        self._configured = True
    
    def log_fetch(self, count: int, source: str = "all"):
        """记录抓取结果"""
        logger.bind(name=self.name).info(f"[FETCH] 从 {source} 抓取到 {count} 个代理")
    
    def log_verify(self, total: int, valid: int, invalid: int, slow: int = 0):
        """记录验证结果"""
        logger.bind(name=self.name).info(
            f"[VERIFY] 总计: {total}, 有效: {valid}, 无效: {invalid}, 慢: {slow}"
        )
    
    def log_get_proxy(self, proxy, success: bool):
        """记录获取代理结果"""
        if success:
            logger.bind(name=self.name).debug(
                f"[GET] 获取代理成功: {proxy.ip}:{proxy.port} "
                f"({proxy.protocol.value}, {proxy.response_time:.2f}s)"
            )
        else:
            logger.bind(name=self.name).warning("[GET] 获取代理失败")
    
    def log_error(self, operation: str, error: Exception):
        """记录错误"""
        logger.bind(name=self.name).error(f"[ERROR] {operation}: {str(error)}")
    
    def log_warning(self, message: str):
        """记录警告"""
        logger.bind(name=self.name).warning(f"[WARN] {message}")
    
    def log_info(self, message: str):
        """记录信息"""
        logger.bind(name=self.name).info(f"[INFO] {message}")
    
    def log_debug(self, message: str):
        """记录调试信息"""
        logger.bind(name=self.name).debug(f"[DEBUG] {message}")


# 全局日志实例
_default_logger: Optional[ProxyPoolLogger] = None


def get_pool_logger() -> ProxyPoolLogger:
    """获取代理池日志记录器"""
    global _default_logger
    if _default_logger is None:
        _default_logger = ProxyPoolLogger()
    return _default_logger


__all__ = ["logger", "setup_logger", "get_logger", "ProxyPoolLogger", "get_pool_logger"]
