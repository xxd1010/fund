"""
通知渠道注册
"""

from .ntfy import NtfyChannel
from .qq import QQChannel
from .feishu import FeishuChannel
from .markdown import MarkdownChannel

# 渠道名称到类的映射
CHANNEL_REGISTRY = {
    'ntfy': NtfyChannel,
    'qq': QQChannel,
    'feishu': FeishuChannel,
    'markdown': MarkdownChannel,
}


def get_channel_class(channel_name: str):
    """根据渠道名称获取渠道类"""
    return CHANNEL_REGISTRY.get(channel_name)
