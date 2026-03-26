"""
通知配置加载模块
从 config.json 加载通知相关配置
"""

import json
import os
from typing import Dict, Any, Optional

from src.utils.logger import logger


CONFIG_FILE = "config.json"


def load_notify_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    从 config.json 加载通知配置

    Returns:
        通知配置字典，包含 enabled, default_channel, channels, templates
    """
    path = config_path or CONFIG_FILE

    default_config = {
        "enabled": False,
        "default_channel": "ntfy",
        "channels": {},
        "templates": {}
    }

    if not os.path.exists(path):
        logger.warning(f"配置文件 {path} 不存在，使用默认通知配置")
        return default_config

    try:
        with open(path, 'r', encoding='utf-8') as f:
            full_config = json.load(f)

        notify_config = full_config.get('notify', default_config)
        return notify_config

    except Exception as e:
        logger.error(f"加载通知配置失败: {e}，使用默认配置")
        return default_config


def get_channel_config(channel_name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    获取指定渠道的配置

    Args:
        channel_name: 渠道名称 (ntfy, qq, feishu, markdown)
        config_path: 配置文件路径

    Returns:
        渠道配置字典
    """
    notify_config = load_notify_config(config_path)
    channels = notify_config.get('channels', {})
    return channels.get(channel_name, {})


def get_template(template_name: str, config_path: Optional[str] = None) -> Optional[str]:
    """
    获取指定模板

    Args:
        template_name: 模板名称
        config_path: 配置文件路径

    Returns:
        模板字符串，不存在则返回 None
    """
    notify_config = load_notify_config(config_path)
    templates = notify_config.get('templates', {})
    return templates.get(template_name)
