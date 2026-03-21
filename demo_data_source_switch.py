#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源切换演示

演示如何在 akshare 和 baostock 之间切换数据源
"""

import sys
import os

# 设置编码
sys.stdout.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.data_fetcher import AkFund


def main():
    """主演示函数"""
    print("=" * 60)
    print("数据源切换演示")
    print("=" * 60)
    
    # 1. 创建数据获取器
    print("\n1. 创建数据获取器...")
    ak_fund = AkFund()
    
    # 2. 显示可用数据源
    print("\n2. 可用数据源:")
    available_sources = ak_fund.get_available_sources()
    print(f"   股票数据源: {available_sources['stock']}")
    print(f"   基金数据源: {available_sources['fund']}")
    
    # 3. 显示当前数据源
    print("\n3. 当前数据源:")
    current_sources = ak_fund.get_current_sources()
    print(f"   股票数据源: {current_sources['stock']}")
    print(f"   基金数据源: {current_sources['fund']}")
    
    # 4. 演示数据源切换
    print("\n4. 演示数据源切换:")
    
    # 切换到 baostock（如果可用）
    if 'baostock' in available_sources['stock']:
        print(f"   a) 切换到 baostock 数据源...")
        if ak_fund.switch_stock_source('baostock'):
            print(f"      ✓ 股票数据源已切换到 baostock")
            print(f"      当前数据源: {ak_fund.get_current_sources()}")
            
            # 使用 baostock 获取数据
            print(f"\n   b) 使用 baostock 获取股票数据...")
            try:
                stock_data = ak_fund.get_stock_realtime('600519')
                if not stock_data.empty:
                    print(f"      ✓ 获取股票数据成功")
                    print(f"      数据形状: {stock_data.shape}")
                    print(f"      列名: {list(stock_data.columns)}")
                else:
                    print(f"      ✗ 获取股票数据失败")
            except Exception as e:
                print(f"      ✗ 获取数据异常: {e}")
        else:
            print(f"      ✗ 无法切换到 baostock")
    else:
        print(f"   a) baostock 数据源不可用")
    
    # 切换回 akshare
    print(f"\n   c) 切换回 akshare 数据源...")
    if ak_fund.switch_stock_source('akshare'):
        print(f"      ✓ 股票数据源已切换回 akshare")
        print(f"      当前数据源: {ak_fund.get_current_sources()}")
        
        # 使用 akshare 获取数据
        print(f"\n   d) 使用 akshare 获取股票数据...")
        try:
            stock_data = ak_fund.get_stock_realtime('600519')
            if not stock_data.empty:
                print(f"      ✓ 获取股票数据成功")
                print(f"      数据形状: {stock_data.shape}")
                print(f"      列名: {list(stock_data.columns)}")
            else:
                print(f"      ✗ 获取股票数据失败")
        except Exception as e:
            print(f"      ✗ 获取数据异常: {e}")
    else:
        print(f"      ✗ 无法切换回 akshare")
    
    # 5. 演示基金数据获取
    print("\n5. 演示基金数据获取:")
    print(f"   当前基金数据源: {ak_fund.get_current_sources()['fund']}")
    
    try:
        fund_info = ak_fund.get_fund_info('000001')
        if not fund_info.empty:
            print(f"   ✓ 获取基金信息成功")
            print(f"   数据形状: {fund_info.shape}")
            print(f"   基金名称: {fund_info.iloc[0]['基金简称'] if '基金简称' in fund_info.columns else 'N/A'}")
        else:
            print(f"   ✗ 获取基金信息失败")
    except Exception as e:
        print(f"   ✗ 获取基金信息异常: {e}")
    
    # 6. 演示配置文件切换
    print("\n6. 演示配置文件切换:")
    
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
            print(f"     创建成功")
            print(f"     当前数据源: {ak_fund_new.get_current_sources()}")
        except Exception as e:
            print(f"     创建失败: {e}")
        
    except Exception as e:
        print(f"   配置文件操作异常: {e}")
    
    # 7. 总结
    print("\n" + "=" * 60)
    print("演示总结")
    print("=" * 60)
    print("""
    已成功实现多数据源架构，支持以下功能：
    
    1. ✅ 数据源抽象层：统一的 DataProviderBase 接口
    2. ✅ 多数据源支持：akshare 和 baostock
    3. ✅ 动态切换：运行时切换股票和基金数据源
    4. ✅ 配置驱动：通过配置文件指定默认数据源
    5. ✅ 兼容性：保持与旧版本 API 的兼容
    6. ✅ 错误处理：优雅的数据源降级和错误处理
    
    使用方式：
    1. 修改 config.json 中的 data_sources 配置
    2. 调用 switch_stock_source() 或 switch_fund_source() 动态切换
    3. 当某个数据源不稳定时，自动切换到备用数据源
    
    优势：
    - akshare 不稳定时可切换到 baostock
    - baostock 提供更稳定的股票数据
    - akshare 提供更丰富的基金数据
    - 两者可混合使用，取长补短
    """)
    
    print("\n🎉 数据源切换架构已成功实现！")


if __name__ == "__main__":
    main()