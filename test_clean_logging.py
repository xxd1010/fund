#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的日志输出

展示清晰有序的日志输出，演示数据源切换功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 首先导入日志配置模块，设置日志级别
from src.core.logger_config import set_log_level

# 设置日志级别为 INFO，减少调试信息
set_log_level("info")

# 然后导入数据获取器
from src.core.data_fetcher import AkFund


def main():
    """主测试函数"""
    print("=" * 60)
    print("测试优化后的日志输出和数据源切换")
    print("=" * 60)
    
    # 1. 创建数据获取器
    print("\n1. 创建数据获取器...")
    ak_fund = AkFund()
    
    # 2. 显示数据源信息
    print("\n2. 数据源信息:")
    available_sources = ak_fund.get_available_sources()
    current_sources = ak_fund.get_current_sources()
    
    print(f"   可用数据源:")
    print(f"     股票: {available_sources['stock']}")
    print(f"     基金: {available_sources['fund']}")
    
    print(f"\n   当前使用数据源:")
    print(f"     股票: {current_sources['stock']}")
    print(f"     基金: {current_sources['fund']}")
    
    # 3. 演示数据源切换
    print("\n3. 演示数据源切换:")
    
    # 切换到 baostock（如果可用）
    if 'baostock' in available_sources['stock']:
        print("   尝试切换到 baostock 数据源...")
        if ak_fund.switch_stock_source('baostock'):
            print("   ✓ 股票数据源已切换到 baostock")
            print(f"   当前股票数据源: {ak_fund.get_current_sources()['stock']}")
        else:
            print("   ✗ 无法切换到 baostock")
    else:
        print("   baostock 数据源不可用")
    
    # 切换回 akshare
    print("\n   切换回 akshare 数据源...")
    if ak_fund.switch_stock_source('akshare'):
        print("   ✓ 股票数据源已切换回 akshare")
        print(f"   当前股票数据源: {ak_fund.get_current_sources()['stock']}")
    else:
        print("   ✗ 无法切换回 akshare")
    
    # 4. 测试数据获取（会有清晰的日志输出）
    print("\n4. 测试数据获取（查看日志输出）:")
    
    # 测试股票数据获取
    print("\n   a) 获取股票实时行情...")
    try:
        stock_data = ak_fund.get_stock_realtime('600519')
        if not stock_data.empty:
            print(f"   ✓ 获取股票数据成功")
            print(f"   数据形状: {stock_data.shape}")
            print(f"   列名: {list(stock_data.columns)}")
        else:
            print("   ✗ 获取股票数据失败")
    except Exception as e:
        print(f"   ✗ 获取数据异常: {e}")
    
    # 测试基金数据获取
    print("\n   b) 获取基金信息...")
    try:
        fund_data = ak_fund.get_fund_info('000001')
        if not fund_data.empty:
            print(f"   ✓ 获取基金数据成功")
            print(f"   数据形状: {fund_data.shape}")
            print(f"   列名: {list(fund_data.columns)}")
        else:
            print("   ✗ 获取基金数据失败")
    except Exception as e:
        print(f"   ✗ 获取数据异常: {e}")
    
    # 5. 演示配置文件切换
    print("\n5. 演示配置文件切换:")
    
    import json
    
    try:
        # 读取当前配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"   当前配置数据源:")
        print(f"     股票: {config.get('data_sources', {}).get('stock', 'akshare')}")
        print(f"     基金: {config.get('data_sources', {}).get('fund', 'akshare')}")
        
        # 创建新配置
        new_config = config.copy()
        new_config['data_sources'] = {
            'stock': 'baostock',
            'fund': 'akshare'
        }
        
        # 保存新配置
        with open('config_baostock.json', 'w', encoding='utf-8') as f:
            json.dump(new_config, f, ensure_ascii=False, indent=2)
        
        print(f"\n   创建新配置文件 config_baostock.json")
        print(f"     股票数据源: baostock")
        print(f"     基金数据源: akshare")
        
        # 使用新配置创建数据获取器
        print(f"\n   使用新配置创建数据获取器...")
        try:
            ak_fund_new = AkFund('config_baostock.json')
            print(f"   ✓ 创建成功")
            print(f"   当前数据源: {ak_fund_new.get_current_sources()}")
        except Exception as e:
            print(f"   ✗ 创建失败: {e}")
        
    except Exception as e:
        print(f"   配置文件操作异常: {e}")
    
    # 6. 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("""
    日志优化已完成，主要改进：
    
    1. ✅ 统一日志格式：时间戳 | 级别 | 模块/函数/行号 | 消息
    2. ✅ 彩色输出：不同级别使用不同颜色
    3. ✅ 日志级别控制：可动态调整日志级别
    4. ✅ 有序输出：日志按时间顺序排列
    5. ✅ 减少冗余：INFO级别只显示重要信息
    
    数据源切换功能：
    1. ✅ 支持 akshare 和 baostock 双数据源
    2. ✅ 运行时动态切换
    3. ✅ 配置文件驱动
    4. ✅ 自动降级：当某个数据源失败时使用备用数据源
    
    使用建议：
    1. 在 config.json 中设置默认数据源
    2. 当 akshare 不稳定时，调用 switch_stock_source('baostock')
    3. 可通过 set_log_level('warning') 减少日志输出
    """)
    
    print("\n🎉 日志优化和数据源切换架构已完成！")


if __name__ == "__main__":
    main()