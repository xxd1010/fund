"""
通知模块配置处理
"""

import json
import os
from typing import Dict, Any, Optional
from loguru import logger


def load_notify_config(config_path: str = 'config.json') -> Dict[str, Any]:
    """
    加载通知配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        通知配置字典
    """
    default_config = {
        'enabled': False,
        'default_channel': 'ntfy',
        'channels': {
            'ntfy': {
                'enabled': False,
                'topic': '',
                'server': 'https://ntfy.sh',
                'priority': 'default',
                'max_retries': 3,
                'retry_delay': 1.0
            },
            'qq': {
                'enabled': False,
                'bot_token': '',
                'group_id': '',
                'message_type': 'group',
                'max_retries': 3,
                'retry_delay': 1.0
            },
            'feishu': {
                'enabled': False,
                'webhook_url': '',
                'secret': '',
                'max_retries': 3,
                'retry_delay': 1.0
            }
        },
        'templates': {
            'analysis_start': '🔍 开始分析基金 {fund_code}',
            'analysis_complete': '✅ 基金 {fund_code} 分析完成\n得分: {score:.3f}\n建议: {recommendation}',
            'error': '❌ 处理 {fund_code} 时出错: {error}',
            'signal_detected': '🚨 检测到信号: {signal_type}\n股票: {stock_code}\n级别: {level}',
            'fund_recommendation': '📊 基金 {fund_code} 建议: {recommendation}\n加权得分: {score:.3f}\n置信度: {confidence:.1%}'
        }
    }
    
    if not os.path.exists(config_path):
        logger.warning(f"配置文件 {config_path} 不存在，使用默认通知配置")
        return default_config
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 获取通知配置，如果不存在则使用默认配置
        notify_config = config.get('notify', {})
        
        # 合并默认配置
        merged_config = default_config.copy()
        
        # 更新启用状态
        if 'enabled' in notify_config:
            merged_config['enabled'] = notify_config['enabled']
        
        # 更新默认渠道
        if 'default_channel' in notify_config:
            merged_config['default_channel'] = notify_config['default_channel']
        
        # 更新渠道配置
        if 'channels' in notify_config:
            for channel_name, channel_config in notify_config['channels'].items():
                if channel_name in merged_config['channels']:
                    merged_config['channels'][channel_name].update(channel_config)
                else:
                    merged_config['channels'][channel_name] = channel_config
        
        # 更新模板
        if 'templates' in notify_config:
            merged_config['templates'].update(notify_config['templates'])
        
        logger.info(f"通知配置加载成功，启用状态: {merged_config['enabled']}")
        return merged_config
        
    except Exception as e:
        logger.error(f"加载通知配置失败: {e}, 使用默认配置")
        return default_config


def save_notify_config(config: Dict[str, Any], config_path: str = 'config.json') -> bool:
    """
    保存通知配置
    
    Args:
        config: 通知配置字典
        config_path: 配置文件路径
        
    Returns:
        保存是否成功
    """
    try:
        # 读取现有配置
        existing_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
        
        # 更新通知配置
        existing_config['notify'] = config
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"通知配置保存成功: {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"保存通知配置失败: {e}")
        return False


def get_channel_config(channel_name: str, config_path: str = 'config.json') -> Optional[Dict[str, Any]]:
    """
    获取指定渠道的配置
    
    Args:
        channel_name: 渠道名称
        config_path: 配置文件路径
        
    Returns:
        渠道配置字典，如果不存在则返回None
    """
    config = load_notify_config(config_path)
    
    if channel_name in config['channels']:
        return config['channels'][channel_name]
    
    return None


def update_channel_config(channel_name: str, channel_config: Dict[str, Any], 
                         config_path: str = 'config.json') -> bool:
    """
    更新指定渠道的配置
    
    Args:
        channel_name: 渠道名称
        channel_config: 渠道配置字典
        config_path: 配置文件路径
        
    Returns:
        更新是否成功
    """
    try:
        # 读取现有配置
        config = load_notify_config(config_path)
        
        # 更新渠道配置
        if channel_name not in config['channels']:
            config['channels'][channel_name] = {}
        
        config['channels'][channel_name].update(channel_config)
        
        # 保存配置
        return save_notify_config(config, config_path)
        
    except Exception as e:
        logger.error(f"更新渠道配置失败: {e}")
        return False


def get_template(template_name: str, config_path: str = 'config.json') -> Optional[str]:
    """
    获取消息模板
    
    Args:
        template_name: 模板名称
        config_path: 配置文件路径
        
    Returns:
        模板字符串，如果不存在则返回None
    """
    config = load_notify_config(config_path)
    
    if template_name in config['templates']:
        return config['templates'][template_name]
    
    return None


def update_template(template_name: str, template_content: str, 
                   config_path: str = 'config.json') -> bool:
    """
    更新消息模板
    
    Args:
        template_name: 模板名称
        template_content: 模板内容
        config_path: 配置文件路径
        
    Returns:
        更新是否成功
    """
    try:
        # 读取现有配置
        config = load_notify_config(config_path)
        
        # 更新模板
        config['templates'][template_name] = template_content
        
        # 保存配置
        return save_notify_config(config, config_path)
        
    except Exception as e:
        logger.error(f"更新模板失败: {e}")
        return False