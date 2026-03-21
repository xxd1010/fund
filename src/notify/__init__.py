"""
通知模块主入口
提供统一的 notify 接口，支持多种通知渠道
"""

import os
import sys
from typing import Dict, Any, Optional, List, Union
from loguru import logger

from .manager import NotificationManager
from .config import load_notify_config

# 全局通知管理器实例
_notify_manager: Optional[NotificationManager] = None


def init_notify(config_path: str = 'config.json') -> NotificationManager:
    """
    初始化通知模块
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        NotificationManager 实例
    """
    global _notify_manager
    
    try:
        config = load_notify_config(config_path)
        _notify_manager = NotificationManager(config)
        logger.info(f"通知模块初始化完成，启用渠道: {list(_notify_manager.enabled_channels.keys())}")
        return _notify_manager
    except Exception as e:
        logger.error(f"通知模块初始化失败: {e}")
        # 创建一个禁用的管理器作为回退
        _notify_manager = NotificationManager({'enabled': False})
        return _notify_manager


def get_notify() -> NotificationManager:
    """
    获取通知管理器实例
    
    Returns:
        NotificationManager 实例
    """
    global _notify_manager
    
    if _notify_manager is None:
        # 自动初始化
        _notify_manager = init_notify()
    
    return _notify_manager


# 创建全局 notify 对象
notify = get_notify()

# 导出常用函数
send = notify.send
send_to = notify.send_to
send_template = notify.send_template
send_async = notify.send_async
send_to_async = notify.send_to_async
send_template_async = notify.send_template_async

# 导出类型
from .base import MessagePriority
from .manager import NotificationManager

__all__ = [
    'notify',
    'send',
    'send_to',
    'send_template',
    'send_async',
    'send_to_async',
    'send_template_async',
    'MessagePriority',
    'NotificationManager',
    'init_notify',
    'get_notify'
]