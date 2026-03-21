"""
QQ 通知渠道实现
支持 QQ 机器人通知
"""

import requests
import json
from typing import Dict, Any, Union, List
from loguru import logger

from ..base import BaseNotifier, Message, MessagePriority


class QQNotifier(BaseNotifier):
    """
    QQ 通知器
    
    支持 QQ 机器人通知，可通过群聊或私聊发送消息
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # QQ 特定配置
        self.bot_token = config.get('bot_token', '')
        self.group_id = config.get('group_id', '')
        self.message_type = config.get('message_type', 'group')  # group 或 private
        self.api_base = config.get('api_base', 'https://api.q.qq.com')
        
    def get_required_fields(self) -> List[str]:
        """
        获取必要配置字段
        
        Returns:
            必要配置字段列表
        """
        return ['bot_token']
    
    def send(self, message: Union[str, Message], **kwargs) -> bool:
        """
        发送消息到 QQ
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            logger.debug(f"QQ 通知器 {self.name} 已禁用，跳过发送")
            return False
        
        # 格式化消息
        formatted_message = self.format_message(message, **kwargs)
        
        # 根据消息类型选择发送方式
        if self.message_type == 'group' and self.group_id:
            return self._send_group_message(formatted_message)
        elif self.message_type == 'private':
            # 私聊消息需要用户ID，这里暂不支持
            logger.error("QQ 私聊消息暂不支持，请使用群聊消息")
            return False
        else:
            logger.error(f"QQ 消息类型不支持: {self.message_type}")
            return False
    
    async def send_async(self, message: Union[str, Message], **kwargs) -> bool:
        """
        异步发送消息到 QQ
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        # 使用线程池执行
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
                logger.error(f"QQ 异步发送异常: {e}")
                return False
    
    def _send_group_message(self, message: Message) -> bool:
        """
        发送群聊消息
        
        Args:
            message: 消息对象
            
        Returns:
            发送是否成功
        """
        try:
            # 构建请求头
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }
            
            # 构建消息内容
            content = message.content
            if message.title:
                content = f"{message.title}\n\n{content}"
            
            # 构建请求数据
            data = {
                'content': content,
                'msg_type': 0  # 文本消息
            }
            
            # 发送请求
            url = f"{self.api_base}/v2/groups/{self.group_id}/messages"
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug(f"QQ 群消息发送成功: {message.content[:50]}...")
                return True
            else:
                logger.error(f"QQ 群消息发送失败: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"QQ 请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"QQ 发送异常: {e}")
            return False
    
    def _send_private_message(self, message: Message, user_id: str) -> bool:
        """
        发送私聊消息
        
        Args:
            message: 消息对象
            user_id: 用户ID
            
        Returns:
            发送是否成功
        """
        try:
            # 构建请求头
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }
            
            # 构建消息内容
            content = message.content
            if message.title:
                content = f"{message.title}\n\n{content}"
            
            # 构建请求数据
            data = {
                'content': content,
                'msg_type': 0  # 文本消息
            }
            
            # 发送请求
            url = f"{self.api_base}/v2/users/{user_id}/messages"
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug(f"QQ 私聊消息发送成功: {message.content[:50]}...")
                return True
            else:
                logger.error(f"QQ 私聊消息发送失败: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"QQ 请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"QQ 发送异常: {e}")
            return False
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        if not super().validate_config():
            return False
        
        # 检查 bot_token 是否为空
        if not self.bot_token:
            logger.error("QQ 配置错误: bot_token 不能为空")
            return False
        
        # 检查消息类型
        if self.message_type not in ['group', 'private']:
            logger.error(f"QQ 配置错误: 不支持的消息类型: {self.message_type}")
            return False
        
        # 如果是群聊消息，检查 group_id
        if self.message_type == 'group' and not self.group_id:
            logger.error("QQ 配置错误: 群聊消息需要 group_id")
            return False
        
        # 检查 API 基础 URL
        if not self.api_base.startswith(('http://', 'https://')):
            logger.error(f"QQ 配置错误: api_base URL 格式不正确: {self.api_base}")
            return False
        
        return True
    
    def __str__(self) -> str:
        return f"QQNotifier(name={self.name}, type={self.message_type}, enabled={self.enabled})"