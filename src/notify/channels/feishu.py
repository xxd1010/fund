"""
飞书通知渠道实现
支持飞书群机器人通知
"""

import requests
import json
import time
import hashlib
import hmac
import base64
from typing import Dict, Any, Union, List
from loguru import logger

from ..base import BaseNotifier, Message, MessagePriority


class FeishuNotifier(BaseNotifier):
    """
    飞书通知器
    
    支持飞书群机器人通知
    文档: https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # 飞书特定配置
        self.webhook_url = config.get('webhook_url', '')
        self.secret = config.get('secret', '')
        
    def get_required_fields(self) -> List[str]:
        """
        获取必要配置字段
        
        Returns:
            必要配置字段列表
        """
        return ['webhook_url']
    
    def send(self, message: Union[str, Message], **kwargs) -> bool:
        """
        发送消息到飞书
        
        Args:
            message: 消息内容或Message对象
            **kwargs: 额外参数
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            logger.debug(f"飞书通知器 {self.name} 已禁用，跳过发送")
            return False
        
        # 格式化消息
        formatted_message = self.format_message(message, **kwargs)
        
        # 发送消息
        return self._send_message(formatted_message)
    
    async def send_async(self, message: Union[str, Message], **kwargs) -> bool:
        """
        异步发送消息到飞书
        
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
                logger.error(f"飞书异步发送异常: {e}")
                return False
    
    def _send_message(self, message: Message) -> bool:
        """
        发送消息到飞书
        
        Args:
            message: 消息对象
            
        Returns:
            发送是否成功
        """
        try:
            # 构建消息内容
            content = message.content
            if message.title:
                content = f"{message.title}\n\n{content}"
            
            # 构建请求数据
            data = {
                'msg_type': 'text',
                'content': {
                    'text': content
                }
            }
            
            # 如果有标题，使用富文本格式
            if message.title:
                data = {
                    'msg_type': 'post',
                    'content': {
                        'post': {
                            'zh_cn': {
                                'title': message.title,
                                'content': [
                                    [
                                        {
                                            'tag': 'text',
                                            'text': message.content
                                        }
                                    ]
                                ]
                            }
                        }
                    }
                }
            
            # 如果有密钥，添加签名
            if self.secret:
                timestamp = str(int(time.time()))
                sign = self._generate_sign(timestamp, self.secret)
                data['timestamp'] = timestamp
                data['sign'] = sign
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                headers={'Content-Type': 'application/json'},
                json=data,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                logger.debug(f"飞书消息发送成功: {message.content[:50]}...")
                return True
            else:
                logger.error(f"飞书消息发送失败: {response.status_code} - {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"飞书请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"飞书发送异常: {e}")
            return False
    
    def _generate_sign(self, timestamp: str, secret: str) -> str:
        """
        生成飞书签名
        
        Args:
            timestamp: 时间戳
            secret: 密钥
            
        Returns:
            签名字符串
        """
        # 拼接 timestamp 和 secret
        string_to_sign = f'{timestamp}\n{secret}'
        
        # 使用 HMAC-SHA256 加密
        hmac_code = hmac.new(
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        # 对结果进行 Base64 编码
        sign = base64.b64encode(hmac_code).decode('utf-8')
        
        return sign
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        if not super().validate_config():
            return False
        
        # 检查 webhook_url 是否为空
        if not self.webhook_url:
            logger.error("飞书配置错误: webhook_url 不能为空")
            return False
        
        # 检查 webhook_url 格式
        if not self.webhook_url.startswith(('http://', 'https://')):
            logger.error(f"飞书配置错误: webhook_url URL 格式不正确: {self.webhook_url}")
            return False
        
        # 检查是否是飞书 webhook URL
        if 'open.feishu.cn' not in self.webhook_url and 'larkoffice.com' not in self.webhook_url:
            logger.warning(f"飞书 webhook_url 可能不是有效的飞书 URL: {self.webhook_url}")
        
        return True
    
    def __str__(self) -> str:
        return f"FeishuNotifier(name={self.name}, enabled={self.enabled})"