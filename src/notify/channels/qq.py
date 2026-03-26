"""
QQ 机器人通知渠道
通过 QQ 机器人推送消息
"""

import json
from typing import Dict, Any, Optional

import requests

from .base import BaseChannel, MessagePriority
from src.utils.logger import logger


class QQChannel(BaseChannel):
    """QQ 机器人通知渠道"""

    @property
    def name(self) -> str:
        return "qq"

    def _do_send(self, message: str, title: Optional[str] = None,
                 priority: MessagePriority = MessagePriority.DEFAULT,
                 **kwargs) -> bool:
        bot_token = self.config.get('bot_token', '')
        group_id = self.config.get('group_id', '')
        message_type = self.config.get('message_type', 'group')

        if not bot_token or not group_id:
            logger.error("QQ: 未配置 bot_token 或 group_id")
            return False

        content = f"{title}\n\n{message}" if title else message

        if message_type == 'group':
            url = f"https://api.q.qq.com/api/send/group_msg"
        else:
            url = f"https://api.q.qq.com/api/send/private_msg"

        data = {
            "access_token": bot_token,
            "group_id": group_id,
            "message": content
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('retcode') == 0:
                logger.info("QQ 推送成功")
                return True
            else:
                logger.error(f"QQ 推送失败: {result}")
                return False
        else:
            logger.error(f"QQ 推送失败: {response.status_code}")
            return False
