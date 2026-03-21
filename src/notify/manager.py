"""
通知管理器
统一管理多个通知渠道
"""

import asyncio
from typing import Dict, Any, Optional, List, Union
from loguru import logger

from .base import BaseNotifier, Message, MessagePriority
from .channels.ntfy import NtfyNotifier
from .channels.qq import QQNotifier
from .channels.feishu import FeishuNotifier


class NotificationManager:
    """
    通知管理器
    统一管理多个通知渠道
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化通知管理器
        
        Args:
            config: 通知配置字典
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        self.default_channel = config.get('default_channel', 'ntfy')
        self.templates = config.get('templates', {})
        
        # 初始化渠道
        self.channels: Dict[str, BaseNotifier] = {}
        self.enabled_channels: Dict[str, BaseNotifier] = {}
        
        self._init_channels()
        
    def _init_channels(self):
        """初始化所有通知渠道"""
        if not self.enabled:
            logger.info("通知模块已禁用，跳过渠道初始化")
            return
        
        channel_configs = self.config.get('channels', {})
        
        # 初始化 ntfy 渠道
        if 'ntfy' in channel_configs:
            ntfy_config = channel_configs['ntfy']
            if ntfy_config.get('enabled', False):
                try:
                    self.channels['ntfy'] = NtfyNotifier('ntfy', ntfy_config)
                    if self.channels['ntfy'].validate_config():
                        self.enabled_channels['ntfy'] = self.channels['ntfy']
                        logger.info("ntfy 通知渠道初始化成功")
                    else:
                        logger.warning("ntfy 通知渠道配置验证失败")
                except Exception as e:
                    logger.error(f"初始化 ntfy 通知渠道失败: {e}")
        
        # 初始化 QQ 渠道
        if 'qq' in channel_configs:
            qq_config = channel_configs['qq']
            if qq_config.get('enabled', False):
                try:
                    self.channels['qq'] = QQNotifier('qq', qq_config)
                    if self.channels['qq'].validate_config():
                        self.enabled_channels['qq'] = self.channels['qq']
                        logger.info("QQ 通知渠道初始化成功")
                    else:
                        logger.warning("QQ 通知渠道配置验证失败")
                except Exception as e:
                    logger.error(f"初始化 QQ 通知渠道失败: {e}")
        
        # 初始化飞书渠道
        if 'feishu' in channel_configs:
            feishu_config = channel_configs['feishu']
            if feishu_config.get('enabled', False):
                try:
                    self.channels['feishu'] = FeishuNotifier('feishu', feishu_config)
                    if self.channels['feishu'].validate_config():
                        self.enabled_channels['feishu'] = self.channels['feishu']
                        logger.info("飞书通知渠道初始化成功")
                    else:
                        logger.warning("飞书通知渠道配置验证失败")
                except Exception as e:
                    logger.error(f"初始化飞书通知渠道失败: {e}")
        
        logger.info(f"通知渠道初始化完成，启用 {len(self.enabled_channels)} 个渠道")
    
    def send(self, message: Union[str, Message], 
             channel: Optional[str] = None,
             priority: MessagePriority = MessagePriority.DEFAULT,
             **kwargs) -> bool:
        """
        发送消息
        
        Args:
            message: 消息内容或Message对象
            channel: 渠道名称，如果为None则使用默认渠道
            priority: 消息优先级
            **kwargs: 格式化参数
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            logger.debug("通知模块已禁用，跳过发送")
            return False
        
        if not self.enabled_channels:
            logger.warning("没有启用的通知渠道")
            return False
        
        # 确定目标渠道
        target_channel = channel or self.default_channel
        
        if target_channel not in self.enabled_channels:
            logger.warning(f"渠道 {target_channel} 未启用或不存在，使用默认渠道 {self.default_channel}")
            target_channel = self.default_channel
            
            if target_channel not in self.enabled_channels:
                logger.error(f"默认渠道 {target_channel} 也未启用")
                return False
        
        # 发送消息
        notifier = self.enabled_channels[target_channel]
        
        # 如果是字符串消息，创建Message对象
        if isinstance(message, str):
            message_obj = Message(content=message, priority=priority)
        else:
            message_obj = message
        
        # 发送消息
        success = notifier.send_with_retry(message_obj, **kwargs)
        
        if success:
            logger.debug(f"消息发送成功到渠道 {target_channel}")
        else:
            logger.warning(f"消息发送失败到渠道 {target_channel}")
        
        return success
    
    def send_to(self, channel: str, message: Union[str, Message], 
                priority: MessagePriority = MessagePriority.DEFAULT,
                **kwargs) -> bool:
        """
        发送消息到指定渠道
        
        Args:
            channel: 渠道名称
            message: 消息内容或Message对象
            priority: 消息优先级
            **kwargs: 格式化参数
            
        Returns:
            发送是否成功
        """
        return self.send(message, channel=channel, priority=priority, **kwargs)
    
    def send_template(self, template_name: str, 
                      channel: Optional[str] = None,
                      priority: MessagePriority = MessagePriority.DEFAULT,
                      **kwargs) -> bool:
        """
        使用模板发送消息
        
        Args:
            template_name: 模板名称
            channel: 渠道名称，如果为None则使用默认渠道
            priority: 消息优先级
            **kwargs: 模板参数
            
        Returns:
            发送是否成功
        """
        if template_name not in self.templates:
            logger.error(f"模板 {template_name} 不存在")
            return False
        
        template = self.templates[template_name]
        return self.send(template, channel=channel, priority=priority, **kwargs)
    
    def broadcast(self, message: Union[str, Message], 
                  priority: MessagePriority = MessagePriority.DEFAULT,
                  **kwargs) -> Dict[str, bool]:
        """
        广播消息到所有启用渠道
        
        Args:
            message: 消息内容或Message对象
            priority: 消息优先级
            **kwargs: 格式化参数
            
        Returns:
            各渠道发送结果字典
        """
        if not self.enabled:
            logger.debug("通知模块已禁用，跳过广播")
            return {}
        
        if not self.enabled_channels:
            logger.warning("没有启用的通知渠道")
            return {}
        
        results = {}
        
        for channel_name, notifier in self.enabled_channels.items():
            # 如果是字符串消息，创建Message对象
            if isinstance(message, str):
                message_obj = Message(content=message, priority=priority)
            else:
                message_obj = message
            
            # 发送消息
            success = notifier.send_with_retry(message_obj, **kwargs)
            results[channel_name] = success
            
            if success:
                logger.debug(f"广播消息发送成功到渠道 {channel_name}")
            else:
                logger.warning(f"广播消息发送失败到渠道 {channel_name}")
        
        return results
    
    async def send_async(self, message: Union[str, Message], 
                        channel: Optional[str] = None,
                        priority: MessagePriority = MessagePriority.DEFAULT,
                        **kwargs) -> bool:
        """
        异步发送消息
        
        Args:
            message: 消息内容或Message对象
            channel: 渠道名称，如果为None则使用默认渠道
            priority: 消息优先级
            **kwargs: 格式化参数
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            logger.debug("通知模块已禁用，跳过异步发送")
            return False
        
        if not self.enabled_channels:
            logger.warning("没有启用的通知渠道")
            return False
        
        # 确定目标渠道
        target_channel = channel or self.default_channel
        
        if target_channel not in self.enabled_channels:
            logger.warning(f"渠道 {target_channel} 未启用或不存在，使用默认渠道 {self.default_channel}")
            target_channel = self.default_channel
            
            if target_channel not in self.enabled_channels:
                logger.error(f"默认渠道 {target_channel} 也未启用")
                return False
        
        # 发送消息
        notifier = self.enabled_channels[target_channel]
        
        # 如果是字符串消息，创建Message对象
        if isinstance(message, str):
            message_obj = Message(content=message, priority=priority)
        else:
            message_obj = message
        
        # 异步发送消息
        success = await notifier.send_with_retry_async(message_obj, **kwargs)
        
        if success:
            logger.debug(f"异步消息发送成功到渠道 {target_channel}")
        else:
            logger.warning(f"异步消息发送失败到渠道 {target_channel}")
        
        return success
    
    async def send_to_async(self, channel: str, message: Union[str, Message], 
                           priority: MessagePriority = MessagePriority.DEFAULT,
                           **kwargs) -> bool:
        """
        异步发送消息到指定渠道
        
        Args:
            channel: 渠道名称
            message: 消息内容或Message对象
            priority: 消息优先级
            **kwargs: 格式化参数
            
        Returns:
            发送是否成功
        """
        return await self.send_async(message, channel=channel, priority=priority, **kwargs)
    
    async def send_template_async(self, template_name: str, 
                                 channel: Optional[str] = None,
                                 priority: MessagePriority = MessagePriority.DEFAULT,
                                 **kwargs) -> bool:
        """
        异步使用模板发送消息
        
        Args:
            template_name: 模板名称
            channel: 渠道名称，如果为None则使用默认渠道
            priority: 消息优先级
            **kwargs: 模板参数
            
        Returns:
            发送是否成功
        """
        if template_name not in self.templates:
            logger.error(f"模板 {template_name} 不存在")
            return False
        
        template = self.templates[template_name]
        return await self.send_async(template, channel=channel, priority=priority, **kwargs)
    
    async def broadcast_async(self, message: Union[str, Message], 
                             priority: MessagePriority = MessagePriority.DEFAULT,
                             **kwargs) -> Dict[str, bool]:
        """
        异步广播消息到所有启用渠道
        
        Args:
            message: 消息内容或Message对象
            priority: 消息优先级
            **kwargs: 格式化参数
            
        Returns:
            各渠道发送结果字典
        """
        if not self.enabled:
            logger.debug("通知模块已禁用，跳过异步广播")
            return {}
        
        if not self.enabled_channels:
            logger.warning("没有启用的通知渠道")
            return {}
        
        results = {}
        
        # 并行发送到所有渠道
        tasks = []
        for channel_name, notifier in self.enabled_channels.items():
            # 如果是字符串消息，创建Message对象
            if isinstance(message, str):
                message_obj = Message(content=message, priority=priority)
            else:
                message_obj = message
            
            # 创建异步任务
            task = notifier.send_with_retry_async(message_obj, **kwargs)
            tasks.append((channel_name, task))
        
        # 等待所有任务完成
        for channel_name, task in tasks:
            try:
                success = await task
                results[channel_name] = success
                
                if success:
                    logger.debug(f"异步广播消息发送成功到渠道 {channel_name}")
                else:
                    logger.warning(f"异步广播消息发送失败到渠道 {channel_name}")
            except Exception as e:
                logger.error(f"异步广播消息发送异常到渠道 {channel_name}: {e}")
                results[channel_name] = False
        
        return results
    
    def get_enabled_channels(self) -> List[str]:
        """
        获取所有启用的渠道名称
        
        Returns:
            启用的渠道名称列表
        """
        return list(self.enabled_channels.keys())
    
    def is_channel_enabled(self, channel_name: str) -> bool:
        """
        检查渠道是否启用
        
        Args:
            channel_name: 渠道名称
            
        Returns:
            渠道是否启用
        """
        return channel_name in self.enabled_channels
    
    def get_channel(self, channel_name: str) -> Optional[BaseNotifier]:
        """
        获取指定渠道的通知器
        
        Args:
            channel_name: 渠道名称
            
        Returns:
            通知器对象，如果不存在则返回None
        """
        return self.channels.get(channel_name)
    
    def __str__(self) -> str:
        return f"NotificationManager(enabled={self.enabled}, channels={list(self.enabled_channels.keys())})"