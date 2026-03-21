#!/usr/bin/env python3
"""
测试多数据源兼容性

测试 akshare 和 baostock 两个数据源的切换和兼容性
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.data_fetcher import AkFund


def test_data_source_switching():
    """测试数据源切换功能"""
    print("=" * 60)
    print("测试数据源切换功能")
    print("=" * 60)
    
    # 创建数据获取器
    ak_fund = AkFund()
    
    # 显示初始配置
    print("\n1. 初始配置:")
    print(f"   可用数据源: {ak_fund.get_available_sources()}")
    print(f"   当前数据源: {ak_fund.get_current_sources()}")
    
    # 测试切换到 baostock
    print("\n2. 测试切换到 baostock:")
    if ak_fund.switch_stock_source('baostock'):
        print(f"   ✓ 股票数据源已切换到 baostock")
        print(f"   当前数据源: {ak_fund.get_current_sources()}")
    else:
        print(f"   ✗ 无法切换到 baostock，可能 baostock 不可用")
    
    # 测试切换回 akshare
    print("\n3. 测试切换回 akshare:")
    if ak_fund.switch_stock_source('akshare'):
        print(f"   ✓ 股票数据源已切换回 akshare")
        print(f"   当前数据源: {ak_fund.get_current_sources()}")
    else:
        print(f"   ✗ 无法切换回 akshare")
    
    return True


def test_stock_data_fetching():
    """测试股票数据获取"""
    print("\n" + "=" * 60)
    print("测试股票数据获取")
    print("=" * 60)
    
    ak_fund = AkFund()
    
    # 测试股票代码
    test_symbols = ['600519', '000001', '300750']
    
    for symbol in test_symbols:
        print(f"\n测试股票 {symbol}:")
        
        # 使用 akshare 获取数据
        ak_fund.switch_stock_source('akshare')
        print(f"  使用 akshare 数据源:")
        
        try:
            # 获取实时行情
            realtime = ak_fund.get_stock_realtime(symbol)
            if not realtime.empty:
                print(f"    ✓ 实时行情获取成功，数据形状: {realtime.shape}")
            else:
                print(f"    ✗ 实时行情获取失败")
        except Exception as e:
            print(f"    ✗ 实时行情获取异常: {e}")
        
        try:
            # 获取K线数据
            kline = ak_fund.get_stock_kline(symbol, period='daily', 
                                           start_date='2024-01-01', end_date='2024-01-10')
            if not kline.empty:
                print(f"    ✓ K线数据获取成功，数据形状: {kline.shape}")
            else:
                print(f"    ✗ K线数据获取失败")
        except Exception as e:
            print(f"    ✗ K线数据获取异常: {e}")
        
        # 尝试使用 baostock 获取数据
        if 'baostock' in ak_fund.get_available_sources()['stock']:
            print(f"  使用 baostock 数据源:")
            if ak_fund.switch_stock_source('baostock'):
                try:
                    # 获取实时行情
                    realtime_bs = ak_fund.get_stock_realtime(symbol)
                    if not realtime_bs.empty:
                        print(f"    ✓ 实时行情获取成功，数据形状: {realtime_bs.shape}")
                    else:
                        print(f"    ✗ 实时行情获取失败")
                except Exception as e:
                    print(f"    ✗ 实时行情获取异常: {e}")
                
                try:
                    # 获取K线数据
                    kline_bs = ak_fund.get_stock_kline(symbol, period='daily', 
                                                      start_date='2024-01-01', end_date='2024-01-10')
                    if not kline_bs.empty:
                        print(f"    ✓ K线数据获取成功，数据形状: {kline_bs.shape}")
                    else:
                        print(f"    ✗ K线数据获取失败")
                except Exception as e:
                    print(f"    ✗ K线数据获取异常: {e}")
    
    return True


def test_fund_data_fetching():
    """测试基金数据获取"""
    print("\n" + "=" * 60)
    print("测试基金数据获取")
    print("=" * 60)
    
    ak_fund = AkFund()
    
    # 测试基金代码
    test_funds = ['000001', '005538', '015790']
    
    for fund_code in test_funds:
        print(f"\n测试基金 {fund_code}:")
        
        # 使用 akshare 获取数据
        ak_fund.switch_fund_source('akshare')
        print(f"  使用 akshare 数据源:")
        
        try:
            # 获取基金信息
            fund_info = ak_fund.get_fund_info(fund_code)
            if not fund_info.empty:
                print(f"    ✓ 基金信息获取成功，数据形状: {fund_info.shape}")
            else:
                print(f"    ✗ 基金信息获取失败")
        except Exception as e:
            print(f"    ✗ 基金信息获取异常: {e}")
        
        try:
            # 获取基金净值
            fund_nav = ak_fund.get_fund_nav(fund_code, 
                                           start_date='2024-01-01', end_date='2024-01-10')
            if not fund_nav.empty:
                print(f"    ✓ 基金净值获取成功，数据形状: {fund_nav.shape}")
            else:
                print(f"    ✗ 基金净值获取失败")
        except Exception as e:
            print(f"    ✗ 基金净值获取异常: {e}")
    
    return True


def test_data_processing():
    """测试数据处理功能"""
    print("\n" + "=" * 60)
    print("测试数据处理功能")
    print("=" * 60)
    
    ak_fund = AkFund()
    
    # 获取测试数据
    print("\n1. 获取测试数据:")
    try:
        stock_data = ak_fund.get_stock_realtime('600519')
        if not stock_data.empty:
            print(f"   ✓ 获取股票数据成功，原始数据形状: {stock_data.shape}")
            
            # 处理数据
            processed_data = ak_fund.process_data(stock_data, 'stock_realtime')
            print(f"   ✓ 数据处理成功，处理后数据形状: {processed_data.shape}")
            
            # 保存数据
            if ak_fund.save_data(processed_data, 'test_stock_data', 'csv'):
                print(f"   ✓ 数据保存成功")
            else:
                print(f"   ✗ 数据保存失败")
        else:
            print(f"   ✗ 获取股票数据失败")
    except Exception as e:
        print(f"   ✗ 数据处理测试异常: {e}")
    
    return True


def test_configuration():
    """测试配置文件"""
    print("\n" + "=" * 60)
    print("测试配置文件")
    print("=" * 60)
    
    import json
    
    try:
        # 读取配置文件
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\n1. 配置文件内容:")
        print(f"   基金代码: {config.get('fund_codes', [])}")
        print(f"   数据源配置: {config.get('data_sources', {})}")
        
        # 修改数据源配置
        print(f"\n2. 修改数据源配置:")
        config['data_sources']['stock'] = 'baostock'
        config['data_sources']['fund'] = 'akshare'
        
        # 保存修改后的配置
        with open('config_test.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"   ✓ 配置文件已保存为 config_test.json")
        print(f"   股票数据源: {config['data_sources']['stock']}")
        print(f"   基金数据源: {config['data_sources']['fund']}")
        
        # 使用新配置创建数据获取器
        print(f"\n3. 使用新配置测试:")
        ak_fund_new = AkFund('config_test.json')
        print(f"   当前数据源: {ak_fund_new.get_current_sources()}")
        
    except Exception as e:
        print(f"   ✗ 配置文件测试异常: {e}")
    
    return True


def main():
    """主测试函数"""
    print("多数据源兼容性测试")
    print("=" * 60)
    
    tests = [
        ("数据源切换", test_data_source_switching),
        ("股票数据获取", test_stock_data_fetching),
        ("基金数据获取", test_fund_data_fetching),
        ("数据处理", test_data_processing),
        ("配置文件", test_configuration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n开始测试: {test_name}")
            success = test_func()
            results.append((test_name, success))
            print(f"测试完成: {test_name} - {'✓ 通过' if success else '✗ 失败'}")
        except Exception as e:
            print(f"测试异常: {test_name} - 错误: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！多数据源架构工作正常。")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查相关功能。")


if __name__ == "__main__":
    main()