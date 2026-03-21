# 通知模块使用文档

## 概述

通知模块为基金持仓股票分析系统提供了统一的通知功能，支持多种通知渠道（ntfy、QQ、飞书）。模块设计参考了青龙项目的通知模块架构，提供了简单易用的接口。

## 安装依赖

通知模块需要额外的依赖包，请安装：

```bash
pip install requests
```

如果需要异步支持，可以安装：

```bash
pip install aiohttp
```

## 配置

### 配置文件

在 `config.json` 中添加 `notify` 配置节：

```json
{
  "notify": {
    "enabled": true,
    "default_channel": "ntfy",
    "channels": {
      "ntfy": {
        "enabled": true,
        "topic": "your-topic",
        "server": "https://ntfy.sh",
        "priority": "default",
        "max_retries": 3,
        "retry_delay": 1.0
      },
      "qq": {
        "enabled": false,
        "bot_token": "your-bot-token",
        "group_id": "your-group-id",
        "message_type": "group",
        "max_retries": 3,
        "retry_delay": 1.0
      },
      "feishu": {
        "enabled": false,
        "webhook_url": "your-webhook-url",
        "secret": "your-secret",
        "max_retries": 3,
        "retry_delay": 1.0
      }
    },
    "templates": {
      "analysis_start": "🔍 开始分析基金 {fund_code}",
      "analysis_complete": "✅ 基金 {fund_code} 分析完成\n得分: {score:.3f}\n建议: {recommendation}",
      "error": "❌ 处理 {fund_code} 时出错: {error}",
      "signal_detected": "🚨 检测到信号: {signal_type}\n股票: {stock_code}\n级别: {level}",
      "fund_recommendation": "📊 基金 {fund_code} 建议: {recommendation}\n加权得分: {score:.3f}\n置信度: {confidence:.1%}"
    }
  }
}
```

### 各渠道配置说明

#### ntfy
- `topic`: ntfy 主题名称
- `server`: ntfy 服务器地址（默认：https://ntfy.sh）
- `priority`: 消息优先级（default, min, low, high, max）

#### QQ
- `bot_token`: QQ 机器人 token
- `group_id`: 群组 ID（群聊消息需要）
- `message_type`: 消息类型（group 或 private）
- `api_base`: API 基础地址（默认：https://api.q.qq.com）

#### 飞书
- `webhook_url`: 飞书机器人 webhook URL
- `secret`: 飞书机器人密钥（可选）

## 使用方法

### 基本使用

```python
from src.notify import notify

# 发送简单消息
notify.send("基金分析开始")

# 发送格式化消息
notify.send("基金 {fund_code} 分析完成，得分: {score:.3f}", 
            fund_code="005538", score=0.85)

# 发送到特定渠道
notify.send_to("ntfy", "重要消息", priority="high")

# 使用模板发送消息
notify.send_template("analysis_complete", 
                     fund_code="005538", 
                     score=0.85, 
                     recommendation="强烈建议买入")
```

### 异步使用

```python
import asyncio
from src.notify import notify

async def send_notification():
    # 异步发送消息
    await notify.send_async("异步消息")
    
    # 异步使用模板
    await notify.send_template_async("analysis_start", fund_code="005538")
    
    # 异步广播到所有渠道
    results = await notify.broadcast_async("广播消息")
    
asyncio.run(send_notification())
```

### 消息优先级

```python
from src.notify import MessagePriority

# 使用不同的优先级
notify.send("低优先级消息", priority=MessagePriority.LOW)
notify.send("默认优先级消息", priority=MessagePriority.DEFAULT)
notify.send("高优先级消息", priority=MessagePriority.HIGH)
notify.send("紧急消息", priority=MessagePriority.URGENT)
```

### 自定义消息对象

```python
from src.notify import Message, MessagePriority

# 创建自定义消息
message = Message(
    content="详细的分析报告内容",
    title="基金分析报告",
    priority=MessagePriority.HIGH,
    tags=["基金", "分析", "报告"]
)

# 发送自定义消息
notify.send(message)
```

## 集成到现有代码

通知模块已经集成到主程序的以下关键节点：

1. **基金分析开始**：发送 `analysis_start` 模板消息
2. **基金分析完成**：发送 `analysis_complete` 模板消息
3. **基金加权平均分析结果**：发送 `fund_recommendation` 模板消息
4. **错误处理**：发送 `error` 模板消息

## 添加自定义模板

在配置文件的 `templates` 节中添加自定义模板：

```json
{
  "notify": {
    "templates": {
      "custom_template": "自定义消息: {param1} {param2}"
    }
  }
}
```

使用自定义模板：

```python
notify.send_template("custom_template", param1="值1", param2="值2")
```

## 测试通知模块

### 测试脚本

创建测试脚本 `test_notify.py`：

```python
#!/usr/bin/env python3
"""
测试通知模块
"""

import sys
sys.path.append('.')

from src.notify import notify, MessagePriority

def test_notify():
    print("测试通知模块...")
    
    # 测试简单消息
    print("1. 测试简单消息...")
    success = notify.send("测试消息: 通知模块工作正常")
    print(f"   结果: {'成功' if success else '失败'}")
    
    # 测试模板消息
    print("2. 测试模板消息...")
    success = notify.send_template("analysis_start", fund_code="TEST001")
    print(f"   结果: {'成功' if success else '失败'}")
    
    # 测试不同优先级
    print("3. 测试不同优先级...")
    for priority in [MessagePriority.LOW, MessagePriority.DEFAULT, 
                     MessagePriority.HIGH, MessagePriority.URGENT]:
        success = notify.send(f"测试 {priority.value} 优先级消息", priority=priority)
        print(f"   {priority.value}: {'成功' if success else '失败'}")
    
    print("测试完成!")

if __name__ == "__main__":
    test_notify()
```

### 运行测试

```bash
python test_notify.py
```

## 故障排除

### 常见问题

1. **通知未发送**
   - 检查 `notify.enabled` 是否为 `true`
   - 检查渠道配置是否正确
   - 查看日志文件中的错误信息

2. **ntfy 通知失败**
   - 检查 `topic` 是否正确
   - 检查网络连接是否正常
   - 检查 ntfy 服务器状态

3. **QQ 通知失败**
   - 检查 `bot_token` 是否正确
   - 检查 `group_id` 是否正确（群聊消息）
   - 检查 QQ 机器人权限

4. **飞书通知失败**
   - 检查 `webhook_url` 是否正确
   - 检查 `secret` 是否正确（如果有）
   - 检查飞书机器人是否启用

### 日志查看

通知模块使用 `loguru` 记录日志，可以在 `ak_fund.log` 文件中查看详细日志：

```bash
tail -f ak_fund.log
```

## 扩展通知渠道

要添加新的通知渠道，需要：

1. 在 `src/notify/channels/` 目录下创建新的渠道类
2. 继承 `BaseNotifier` 基类
3. 实现 `send()` 和 `send_async()` 方法
4. 在 `NotificationManager` 中注册新渠道
5. 更新配置文件支持新渠道

## 性能考虑

1. **异步发送**：对于大量通知，建议使用异步发送避免阻塞主程序
2. **失败重试**：模块内置重试机制，默认重试3次
3. **连接池**：对于高频通知，可以考虑使用连接池优化性能

## 安全建议

1. **敏感信息**：不要在通知中发送敏感信息
2. **API 密钥**：妥善保管各渠道的 API 密钥
3. **访问控制**：限制通知渠道的访问权限