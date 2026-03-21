"""
ntfy.sh 通知渠道实现
"""

import requests
from typing import Dict, Any, Union, List
from loguru import logger

from ..base import BaseNotifier, Message, MessagePriority


class NtfyNotifier(BaseNotifier):
    """
    ntfy.sh 通知器
    
    使用 ntfy.sh 服务发送通知
    文档: https://ntfy.sh/docs/
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # ntfy 特定配置
        self.topic = config.get('topic', '')
        self.server = config.get('server', 'https://ntfy.sh')
        self.priority = config.get('priority', 'default')
        
        # 优先级映射
        self.priority_map = {
            MessagePriority.LOW: 'min',
            MessagePriority.DEFAULT: 'default',
            MessagePriority.HIGH: 'high',
            MessagePriority.URGENT: 'max'
        }
    
    def get_required_fields(self) -> List[str]:
        """
        获取必要配置字段
        
        Returns:
            必要配置字段列表
        """
        return ['topic']
    
    def send(self, message: Union[str, Message], **kwargs) -> bool:
        """
        发送消息到 ntfy
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            logger.debug(f"ntfy 通知器 {self.name} 已禁用，跳过发送")
            return False
        
        # 格式化消息
        formatted_message = self.format_message(message, **kwargs)
        
        # 构建请求数据
        data = {
            'topic': self.topic,
            'message': formatted_message.content,
            'priority': self._get_ntfy_priority(formatted_message.priority)
        }
        
        # 添加标题
        if formatted_message.title:
            data['title'] = formatted_message.title
        
        # 添加标签
        if formatted_message.tags:
            data['tags'] = ','.join(formatted_message.tags)
        
        # 发送请求
        try:
            response = requests.post(
                f"{self.server}/{self.topic}",
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug(f"ntfy 消息发送成功: {formatted_message.content[:50]}...")
                return True
            else:
                logger.error(f"ntfy 消息发送失败: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"ntfy 请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"ntfy 发送异常: {e}")
            return False
    
    async def send_async(self, message: Union[str, Message], **kwargs) -> bool:
        """
        异步发送消息到 ntfy
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        # 由于 requests 是同步库，这里使用线程池执行
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor() as executor:
            try:
                result = await loop.run_in_executor(
                    executor, 
                    self.send, 
                    message, 
                    **kwargs
                )
                return result
            except Exception as e:
                logger.error(f"ntfy 异步发送异常: {e}")
                return False
    
    def _get_ntfy_priority(self, priority: MessagePriority) -> str:
        """
        将内部优先级转换为 ntfy 优先级
        
        Args:
            priority: 内部优先级
            
        Returns:
            ntfy 优先级字符串
        """
        return self.priority_map.get(priority, self.priority)
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        if not super().validate_config():
            return False
        
        # 检查 topic 是否为空
        if not self.topic:
            logger.error("ntfy 配置错误: topic 不能为空")
            return False
        
        # 检查 server URL 格式
        if not self.server.startswith(('http://', 'https://')):
            logger.error(f"ntfy 配置错误: server URL 格式不正确: {self.server}")
            return False
        
        return True
    
    def __str__(self) -> str:
        return f"NtfyNotifier(name={self.name}, topic={self.topic}, enabled={self.enabled})"