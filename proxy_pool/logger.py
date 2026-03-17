"""
代理池日志配置模块
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str = "proxy_pool",
    level: int = logging.INFO,
    log_file: str = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """配置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的旧日志文件数量
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 清除已有的处理器
    logger.handlers.clear()
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "proxy_pool") -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)


class ProxyPoolLogger:
    """代理池专用日志记录器"""
    
    def __init__(self, name: str = "proxy_pool"):
        self.logger = logging.getLogger(name)
        self._log_file = None
    
    def set_log_file(self, log_file: str):
        """设置日志文件"""
        self._log_file = log_file
        setup_logger("proxy_pool", log_file=log_file)
    
    def log_fetch(self, count: int, source: str = "all"):
        """记录抓取结果"""
        self.logger.info(f"[FETCH] 从 {source} 抓取到 {count} 个代理")
    
    def log_verify(self, total: int, valid: int, invalid: int, slow: int = 0):
        """记录验证结果"""
        self.logger.info(
            f"[VERIFY] 总计: {total}, 有效: {valid}, 无效: {invalid}, 慢: {slow}"
        )
    
    def log_get_proxy(self, proxy: "Proxy", success: bool):
        """记录获取代理结果"""
        if success:
            self.logger.debug(
                f"[GET] 获取代理成功: {proxy.ip}:{proxy.port} "
                f"({proxy.protocol.value}, {proxy.response_time:.2f}s)"
            )
        else:
            self.logger.warning(f"[GET] 获取代理失败")
    
    def log_error(self, operation: str, error: Exception):
        """记录错误"""
        self.logger.error(f"[ERROR] {operation}: {str(error)}", exc_info=True)
    
    def log_warning(self, message: str):
        """记录警告"""
        self.logger.warning(f"[WARN] {message}")
    
    def log_info(self, message: str):
        """记录信息"""
        self.logger.info(f"[INFO] {message}")
    
    def log_debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(f"[DEBUG] {message}")


# 全局日志实例
_default_logger: ProxyPoolLogger = None


def get_pool_logger() -> ProxyPoolLogger:
    """获取代理池日志记录器"""
    global _default_logger
    if _default_logger is None:
        _default_logger = ProxyPoolLogger()
    return _default_logger
