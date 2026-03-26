"""
Markdown 文件保存渠道
将通知消息保存为 Markdown 文件
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional

from .base import BaseChannel, MessagePriority
from src.utils.logger import logger


class MarkdownChannel(BaseChannel):
    """Markdown 文件保存渠道"""

    @property
    def name(self) -> str:
        return "markdown"

    def _do_send(self, message: str, title: Optional[str] = None,
                 priority: MessagePriority = MessagePriority.DEFAULT,
                 **kwargs) -> bool:
        output_dir = self.config.get('output_dir', './notify_logs')
        file_prefix = self.config.get('file_prefix', 'notify')
        include_timestamp = self.config.get('include_timestamp', True)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 构建文件名
        if include_timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{file_prefix}_{timestamp}.md"
        else:
            filename = f"{file_prefix}.md"

        filepath = os.path.join(output_dir, filename)

        # 构建 Markdown 内容
        content_parts = []
        if title:
            content_parts.append(f"# {title}\n")

        # 添加时间戳
        content_parts.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 添加优先级标记
        if priority != MessagePriority.DEFAULT:
            priority_labels = {
                MessagePriority.LOW: "低优先级",
                MessagePriority.HIGH: "高优先级",
                MessagePriority.URGENT: "紧急",
            }
            label = priority_labels.get(priority, "")
            if label:
                content_parts.append(f"> 优先级: {label}\n")

        content_parts.append("\n")
        content_parts.append(message)

        full_content = "\n".join(content_parts)

        # 写入文件（追加模式到固定文件，或覆盖模式到带时间戳文件）
        if include_timestamp:
            # 每次创建新文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_content)
        else:
            # 追加到已有文件
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write("\n\n---\n\n")
                f.write(full_content)

        logger.info(f"Markdown 文件已保存: {filepath}")

        # 同时保存/更新一个 latest 文件方便读取
        latest_path = os.path.join(output_dir, f"{file_prefix}.md")
        try:
            with open(latest_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
        except Exception:
            pass

        return True
