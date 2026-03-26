"""
通知模块
统一的消息推送接口，支持多渠道发送
"""

from typing import Dict, Any, Optional, List

from src.notify.config import load_notify_config, get_channel_config, get_template
from src.notify.channels.base import BaseChannel, MessagePriority
from src.notify.channels import get_channel_class
from src.utils.logger import logger


class Notify:
    """通知管理器，统一管理所有通知渠道"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化通知管理器

        Args:
            config_path: 配置文件路径
        """
        self._config_path = config_path
        self._channels: Dict[str, BaseChannel] = {}
        self._load_channels()

    def _load_channels(self):
        """加载并初始化所有启用的渠道"""
        notify_config = load_notify_config(self._config_path)

        if not notify_config.get('enabled', False):
            logger.info("通知模块未启用")
            return

        channels_config = notify_config.get('channels', {})

        for channel_name, channel_conf in channels_config.items():
            if not channel_conf.get('enabled', False):
                continue

            channel_class = get_channel_class(channel_name)
            if channel_class is None:
                logger.warning(f"未知的通知渠道: {channel_name}")
                continue

            try:
                self._channels[channel_name] = channel_class(channel_conf)
                logger.info(f"通知渠道 [{channel_name}] 初始化成功")
            except Exception as e:
                logger.error(f"通知渠道 [{channel_name}] 初始化失败: {e}")

    @property
    def enabled_channels(self) -> List[str]:
        """获取已启用的渠道名称列表"""
        return list(self._channels.keys())

    def send(self, message: str, title: Optional[str] = None,
             channel: Optional[str] = None,
             priority: MessagePriority = MessagePriority.DEFAULT,
             **kwargs) -> bool:
        """
        发送消息

        Args:
            message: 消息内容
            title: 消息标题
            channel: 指定渠道名称（None 则发送到所有启用渠道）
            priority: 消息优先级
            **kwargs: 额外参数

        Returns:
            是否至少有一个渠道发送成功
        """
        if not self._channels:
            logger.warning("没有可用的通知渠道")
            return False

        if channel:
            # 发送到指定渠道
            ch = self._channels.get(channel)
            if ch is None:
                logger.error(f"渠道 [{channel}] 未配置或未启用")
                return False
            return ch.send(message, title, priority, **kwargs)
        else:
            # 发送到所有启用渠道
            results = []
            for ch_name, ch in self._channels.items():
                try:
                    result = ch.send(message, title, priority, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"渠道 [{ch_name}] 发送失败: {e}")
                    results.append(False)
            return any(results)

    def send_template(self, template_name: str,
                      channel: Optional[str] = None,
                      priority: MessagePriority = MessagePriority.DEFAULT,
                      **kwargs) -> bool:
        """
        使用模板发送消息

        Args:
            template_name: 模板名称（对应 config.json 中 notify.templates 的 key）
            channel: 指定渠道名称
            priority: 消息优先级
            **kwargs: 模板参数

        Returns:
            是否发送成功
        """
        template_str = get_template(template_name, self._config_path)
        if template_str is None:
            logger.error(f"模板 [{template_name}] 不存在")
            return False

        try:
            message = template_str.format(**kwargs)
        except KeyError as e:
            logger.error(f"模板 [{template_name}] 缺少参数: {e}")
            return False

        return self.send(message, channel=channel, priority=priority)

    def broadcast(self, message: str, title: Optional[str] = None,
                  priority: MessagePriority = MessagePriority.DEFAULT,
                  **kwargs) -> Dict[str, bool]:
        """
        广播消息到所有渠道，返回每个渠道的结果

        Args:
            message: 消息内容
            title: 消息标题
            priority: 消息优先级
            **kwargs: 额外参数

        Returns:
            渠道名称 -> 是否成功的映射
        """
        results = {}
        for ch_name, ch in self._channels.items():
            try:
                results[ch_name] = ch.send(message, title, priority, **kwargs)
            except Exception as e:
                logger.error(f"渠道 [{ch_name}] 广播失败: {e}")
                results[ch_name] = False
        return results

    def broadcast_template(self, template_name: str,
                           priority: MessagePriority = MessagePriority.DEFAULT,
                           **kwargs) -> Dict[str, bool]:
        """
        使用模板广播消息到所有渠道

        Args:
            template_name: 模板名称
            priority: 消息优先级
            **kwargs: 模板参数

        Returns:
            渠道名称 -> 是否成功的映射
        """
        template_str = get_template(template_name, self._config_path)
        if template_str is None:
            logger.error(f"模板 [{template_name}] 不存在")
            return {}

        try:
            message = template_str.format(**kwargs)
        except KeyError as e:
            logger.error(f"模板 [{template_name}] 缺少参数: {e}")
            return {}

        return self.broadcast(message, priority=priority)


# 全局通知管理器实例
notify = Notify()


# 兼容旧 API 的别名
def init_notify(config_path: Optional[str] = None) -> Notify:
    """
    初始化通知模块（兼容旧 API）

    Args:
        config_path: 配置文件路径

    Returns:
        Notify 实例
    """
    return Notify(config_path)


def send(message: str, title: Optional[str] = None,
         channel: Optional[str] = None,
         priority: MessagePriority = MessagePriority.DEFAULT,
         **kwargs) -> bool:
    """
    发送消息（兼容旧 API，作为模块级函数调用）

    Args:
        message: 消息内容
        title: 消息标题
        channel: 指定渠道名称
        priority: 消息优先级
        **kwargs: 额外参数

    Returns:
        是否发送成功
    """
    return notify.send(message, title, channel, priority, **kwargs)
