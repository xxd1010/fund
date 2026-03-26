"""
飞书机器人通知渠道
通过飞书 Webhook 推送消息
"""

import hashlib
import hmac
import base64
import json
import time
from typing import Dict, Any, Optional

import requests

from .base import BaseChannel, MessagePriority
from src.utils.logger import logger


class FeishuChannel(BaseChannel):
    """飞书机器人通知渠道"""

    @property
    def name(self) -> str:
        return "feishu"

    def _do_send(self, message: str, title: Optional[str] = None,
                 priority: MessagePriority = MessagePriority.DEFAULT,
                 **kwargs) -> bool:
        webhook_url = self.config.get('webhook_url', '')
        secret = self.config.get('secret', '')

        if not webhook_url:
            logger.error("飞书: 未配置 webhook_url")
            return False

        content = f"{title}\n\n{message}" if title else message

        data = {
            "msg_type": "text",
            "content": {"text": content}
        }

        # 如果配置了签名校验
        if secret:
            timestamp = str(int(time.time()))
            string_to_sign = f'{timestamp}\n{secret}'
            hmac_code = hmac.new(
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            sign = base64.b64encode(hmac_code).decode('utf-8')
            data['timestamp'] = timestamp
            data['sign'] = sign

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            webhook_url,
            data=json.dumps(data),
            headers=headers,
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                logger.info("飞书 推送成功")
                return True
            else:
                logger.error(f"飞书 推送失败: {result}")
                return False
        else:
            logger.error(f"飞书 推送失败: {response.status_code}")
            return False
