"""
代理池模块使用示例与演示
"""
import asyncio
import logging
from proxy_pool import (
    ProxyPoolAPI,
    ProxyPoolConfig,
    ProtocolType,
    AnonymityLevel,
    get_proxy,
    setup_logger
)


async def basic_usage_demo():
    """基础使用演示"""
    print("=" * 50)
    print("基础使用演示")
    print("=" * 50)
    
    # 配置日志
    setup_logger(level=logging.DEBUG)
    
    # 创建API实例
    api = ProxyPoolAPI()
    
    # 查看当前统计
    stats = api.stats()
    print(f"\n当前代理池状态: {stats}")
    
    # 手动添加一些测试代理
    print("\n添加测试代理...")
    api.add("127.0.0.1", 8080, "http")
    api.add("192.168.1.1", 3128, "https")
    api.add("10.0.0.1", 1080, "socks5")
    
    # 获取一个HTTP代理
    print("\n获取HTTP代理:")
    proxy = api.get("http")
    if proxy:
        print(f"  IP: {proxy.ip}:{proxy.port}")
        print(f"  协议: {proxy.protocol.value}")
        print(f"  匿名级别: {proxy.anonymity.value}")
    else:
        print("  暂无可用代理")
    
    # 获取多个HTTPS代理
    print("\n获取多个HTTPS代理:")
    proxies = api.get_multi("https", count=5)
    for p in proxies:
        print(f"  {p.ip}:{p.port} (响应时间: {p.response_time:.2f}s)")
    
    # 按匿名级别获取
    print("\n获取高匿名代理:")
    proxy = api.get_by_anonymity("high_anonymous", "https")
    if proxy:
        print(f"  {proxy.ip}:{proxy.port}")
    
    # 获取最优代理
    print("\n获取最优代理:")
    best = api.get_best("http")
    if best:
        print(f"  {best.ip}:{best.port} (响应时间: {best.response_time:.2f}s)")
    
    print("\n基础演示完成!")


async def fetch_and_verify_demo():
    """抓取与验证演示"""
    print("=" * 50)
    print("抓取与验证演示")
    print("=" * 50)
    
    api = ProxyPoolAPI()
    
    # 抓取新代理
    print("\n开始抓取代理...")
    count = await api.fetch()
    print(f"新增代理数量: {count}")
    
    # 验证代理
    print("\n开始验证代理（仅验证前20个）...")
    result = await api.verify(max_proxies=20)
    print(f"验证结果: {result}")
    
    # 查看统计
    stats = api.stats()
    print(f"\n更新后统计: {stats}")
    
    print("\n抓取与验证演示完成!")


def sync_usage_demo():
    """同步使用演示"""
    print("=" * 50)
    print("同步使用演示")
    print("=" * 50)
    
    api = ProxyPoolAPI()
    
    # 同步验证
    print("\n同步验证代理...")
    result = api.verify_sync(max_proxies=10)
    print(f"验证结果: {result}")
    
    # 获取代理
    print("\n获取代理:")
    proxy = api.get("http")
    if proxy:
        print(f"  {proxy.ip}:{proxy.port}")
    
    print("\n同步演示完成!")


def scheduler_demo():
    """定时任务演示"""
    print("=" * 50)
    print("定时任务演示")
    print("=" * 50)
    
    api = ProxyPoolAPI()
    
    # 启动定时任务
    print("\n启动定时任务（抓取间隔: 3600s, 验证间隔: 1800s）...")
    api.start(fetch_interval=3600, verify_interval=1800)
    
    print(f"调度器运行状态: {api.is_running()}")
    
    # 等待一段时间后停止（实际使用中不会这么早停止）
    # import time
    # time.sleep(10)
    # api.stop()
    
    print("\n定时任务已启动!")
    print("提示: 使用 api.stop() 停止定时任务")


def proxy_session_demo():
    """代理会话演示"""
    print("=" * 50)
    print("代理会话演示")
    print("=" * 50)
    
    from proxy_pool import ProxySession
    
    session = ProxySession()
    
    # 获取代理
    proxy = session.get_proxy("http")
    if proxy:
        print(f"\n当前代理: {proxy.ip}:{proxy.port}")
        print(f"代理URL: {session.proxy_url}")
        
        # 获取session配置用于requests
        config = session.get_session_config()
        print(f"Session配置: {config}")
        
        # 轮换代理
        new_proxy = session.rotate("https")
        print(f"\n轮换后代理: {new_proxy.ip}:{new_proxy.port}" if new_proxy else "轮换失败")
    
    print("\n代理会话演示完成!")


def advanced_usage_demo():
    """高级使用演示"""
    print("=" * 50)
    print("高级使用演示")
    print("=" * 50)
    
    # 自定义配置
    config = ProxyPoolConfig(
        verify_timeout=10,
        verify_concurrency=30,
        min_response_time=3.0,
        min_success_rate=0.5,
        fetch_interval=3600,
        verify_interval=1800,
        max_pool_size=500,
        db_path="my_proxies.db",
        enable_memory_cache=True
    )
    
    # 创建自定义API
    api = ProxyPoolAPI()
    
    # 注册回调函数
    def on_fetch_callback(proxies):
        print(f"抓取回调: 新增 {len(proxies)} 个代理")
    
    def on_verify_callback(proxy):
        print(f"验证回调: {proxy.ip}:{proxy.port} - {proxy.status.value}")
    
    # 这里可以注册回调（需要访问底层pool）
    # api.pool.on_fetch(on_fetch_callback)
    # api.pool.on_verify(on_verify_callback)
    
    # 清理维护
    print("\n执行清理...")
    result = api.cleanup()
    print(f"清理结果: {result}")
    
    # 获取详细统计
    stats = api.stats()
    print(f"\n详细统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n高级演示完成!")


def quick_start():
    """快速开始示例"""
    print("=" * 50)
    print("快速开始")
    print("=" * 50)
    
    print("""

# 方式1: 使用便捷函数
from proxy_pool import get_proxy

proxy = get_proxy('http')
print(f"代理: {proxy.ip}:{proxy.port}")

# 方式2: 使用API
from proxy_pool import ProxyPoolAPI

api = ProxyPoolAPI()

# 获取代理
proxy = api.get('https')
proxies = api.get_multi('http', count=5)

# 抓取和验证
import asyncio
asyncio.run(api.fetch())
asyncio.run(api.verify())

# 启动定时任务
api.start()

# 查看统计
print(api.stats())

""")


async def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("代理池模块演示")
    print("=" * 50 + "\n")
    
    # 运行各个演示
    # await basic_usage_demo()
    # await fetch_and_verify_demo()
    # sync_usage_demo()
    # scheduler_demo()
    # proxy_session_demo()
    advanced_usage_demo()
    
    # 快速开始
    quick_start()
    
    print("\n" + "=" * 50)
    print("演示结束")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
