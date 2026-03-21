"""
通知模块基础类
定义通知接口和基础实现
"""

import abc
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from loguru import logger


class MessagePriority(Enum):
    """消息优先级枚举"""
    LOW = "low"          # 低优先级
    DEFAULT = "default"  # 默认优先级
    HIGH = "high"        # 高优先级
    URGENT = "urgent"    # 紧急优先级


@dataclass
class Message:
    """消息数据类"""
    content: str                     # 消息内容
    title: Optional[str] = None      # 消息标题
    priority: MessagePriority = MessagePriority.DEFAULT  # 消息优先级
    tags: List[str] = field(default_factory=list)       # 消息标签
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


class BaseNotifier(abc.ABC):
    """
    通知器基类
    所有具体通知渠道需要继承此类
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化通知器
        
        Args:
            name: 通知器名称
            config: 配置字典
        """
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        
    @abc.abstractmethod
    def send(self, message: Union[str, Message], **kwargs) -> bool:
        """
        发送消息
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        pass
    
    @abc.abstractmethod
    async def send_async(self, message: Union[str, Message], **kwargs) -> bool:
        """
        异步发送消息
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        pass
    
    def format_message(self, message: Union[str, Message], **kwargs) -> Message:
        """
        格式化消息
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 格式化参数
            
        Returns:
            Message对象
        """
        if isinstance(message, Message):
            # 如果已经是Message对象，直接返回
            return message
        
        # 如果是字符串，创建Message对象
        content = message
        if kwargs:
            # 格式化字符串
            try:
                content = content.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"格式化消息失败: {e}, 使用原始内容")
        
        return Message(content=content)
    
    def send_with_retry(self, message: Union[str, Message], **kwargs) -> bool:
        """
        带重试的发送消息
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            logger.debug(f"通知器 {self.name} 已禁用，跳过发送")
            return False
        
        formatted_message = self.format_message(message, **kwargs)
        
        for attempt in range(self.max_retries):
            try:
                success = self.send(formatted_message, **kwargs)
                if success:
                    logger.debug(f"通知器 {self.name} 发送成功")
                    return True
                else:
                    logger.warning(f"通知器 {self.name} 发送失败，尝试 {attempt + 1}/{self.max_retries}")
            except Exception as e:
                logger.error(f"通知器 {self.name} 发送异常: {e}, 尝试 {attempt + 1}/{self.max_retries}")
            
            # 如果不是最后一次尝试，等待重试
            if attempt < self.max_retries - 1:
                import time
                time.sleep(self.retry_delay)
        
        logger.error(f"通知器 {self.name} 所有重试都失败")
        return False
    
    async def send_with_retry_async(self, message: Union[str, Message], **kwargs) -> bool:
        """
        异步带重试的发送消息
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            logger.debug(f"通知器 {self.name} 已禁用，跳过发送")
            return False
        
        formatted_message = self.format_message(message, **kwargs)
        
        for attempt in range(self.max_retries):
            try:
                success = await self.send_async(formatted_message, **kwargs)
                if success:
                    logger.debug(f"通知器 {self.name} 异步发送成功")
                    return True
                else:
                    logger.warning(f"通知器 {self.name} 异步发送失败，尝试 {attempt + 1}/{self.max_retries}")
            except Exception as e:
                logger.error(f"通知器 {self.name} 异步发送异常: {e}, 尝试 {attempt + 1}/{self.max_retries}")
            
            # 如果不是最后一次尝试，等待重试
            if attempt < self.max_retries - 1:
                import asyncio
                await asyncio.sleep(self.retry_delay)
        
        logger.error(f"通知器 {self.name} 所有异步重试都失败")
        return False
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        if not self.enabled:
            return True
        
        required_fields = self.get_required_fields()
        for field in required_fields:
            if field not in self.config:
                logger.error(f"通知器 {self.name} 缺少必要配置字段: {field}")
                return False
        
        return True
    
    @abc.abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        获取必要配置字段
        
        Returns:
            必要配置字段列表
        """
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, enabled={self.enabled})"