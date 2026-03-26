"""
通知渠道基类
定义所有通知渠道的统一接口
"""

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional

from src.utils.logger import logger


class MessagePriority(Enum):
    """消息优先级"""
    LOW = "low"
    DEFAULT = "default"
    HIGH = "high"
    URGENT = "urgent"


class BaseChannel(ABC):
    """通知渠道基类"""

    def __init__(self, channel_config: Dict[str, Any]):
        """
        初始化渠道

        Args:
            channel_config: 渠道配置字典
        """
        self.config = channel_config
        self.enabled = channel_config.get('enabled', False)
        self.max_retries = channel_config.get('max_retries', 3)
        self.retry_delay = channel_config.get('retry_delay', 1.0)

    @abstractmethod
    def _do_send(self, message: str, title: Optional[str] = None,
                 priority: MessagePriority = MessagePriority.DEFAULT,
                 **kwargs) -> bool:
        """
        实际发送消息的实现（子类必须实现）

        Args:
            message: 消息内容
            title: 消息标题
            priority: 消息优先级
            **kwargs: 额外参数

        Returns:
            是否发送成功
        """
        pass

    def send(self, message: str, title: Optional[str] = None,
             priority: MessagePriority = MessagePriority.DEFAULT,
             **kwargs) -> bool:
        """
        发送消息（带重试机制）

        Args:
            message: 消息内容
            title: 消息标题
            priority: 消息优先级
            **kwargs: 额外参数

        Returns:
            是否发送成功
        """
        if not self.enabled:
            return False

        for attempt in range(1, self.max_retries + 1):
            try:
                success = self._do_send(message, title, priority, **kwargs)
                if success:
                    return True
                logger.warning(f"{self.__class__.__name__} 发送失败 (尝试 {attempt}/{self.max_retries})")
            except Exception as e:
                logger.error(f"{self.__class__.__name__} 发送异常 (尝试 {attempt}/{self.max_retries}): {e}")

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        return False

    @property
    @abstractmethod
    def name(self) -> str:
        """渠道名称"""
        pass
