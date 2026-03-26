"""
ntfy 通知渠道
通过 ntfy.sh 服务推送消息
"""

from typing import Dict, Any, Optional
import urllib.parse

import requests

from .base import BaseChannel, MessagePriority
from src.utils.logger import logger


class NtfyChannel(BaseChannel):
    """ntfy 通知渠道"""

    # 优先级映射到 ntfy 的数字优先级
    PRIORITY_MAP = {
        MessagePriority.LOW: 2,
        MessagePriority.DEFAULT: 3,
        MessagePriority.HIGH: 4,
        MessagePriority.URGENT: 5,
    }

    @property
    def name(self) -> str:
        return "ntfy"

    def _do_send(
        self,
        message: str,
        title: Optional[str] = None,
        priority: MessagePriority = MessagePriority.DEFAULT,
        **kwargs,
    ) -> bool:
        server = self.config.get("server", "https://ntfy.sh")
        topic = self.config.get("topic", "")

        if not topic:
            logger.error("ntfy: 未配置 topic")
            return False

        url = f"{server}/{topic}"

        headers = {}
        if title:
            # 使用 RFC 2047 编码处理中文标题
            headers["Title"] = urllib.parse.quote(title, safe="")

        headers["Priority"] = str(self.PRIORITY_MAP.get(priority, 3))
        headers["Content-Type"] = "text/plain; charset=utf-8"

        # 可选的认证
        token = self.config.get("token", "")
        username = self.config.get("username", "")
        password = self.config.get("password", "")

        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif username and password:
            headers["Authorization"] = (
                "Basic "
                + __import__("base64")
                .b64encode(f"{username}:{password}".encode())
                .decode()
            )

        response = requests.post(
            url, data=message.encode("utf-8"), headers=headers, timeout=15
        )

        if response.status_code == 200:
            logger.info(f"ntfy 推送成功")
            return True
        else:
            logger.error(f"ntfy 推送失败: {response.status_code} {response.text}")
            return False
