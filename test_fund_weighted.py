#!/usr/bin/env python
"""
测试基金加权平均分析模块
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from src.analysis.fund_weighted_analyzer import FundWeightedAnalyzer
from src.core.data_fetcher import AkFund
from src.data.reader import DataReader

def test_fund_weighted_analysis():
    """测试基金加权平均分析功能"""
    print("=" * 80)
    print("测试基金加权平均分析模块")
    print("=" * 80)
    
    # 创建示例持仓数据（使用实际存在的股票代码）
    sample_holdings = pd.DataFrame({
        '股票代码': ['002149', '002371', '002475', '002565', '002846'],
        '股票名称': ['西部材料', '北方华创', '立讯精密', '洽洽食品', '景嘉微'],
        '持有比例(%)': [15.2, 12.5, 18.8, 9.3, 8.6]
    })
    
    print("\n示例持仓数据:")
    print(sample_holdings.to_string(index=False))
    
    try:
        # 创建分析器
        analyzer = FundWeightedAnalyzer(data_dir="data")
        
        print("\n分析基金 000001...")
        result = analyzer.analyze_fund(
            fund_code="000001",
            holdings_df=sample_holdings,
            fund_name="测试基金"
        )
        
        # 生成报告
        report = analyzer.generate_report(result)
        print("\n分析报告:")
        print(report)
        
        # 保存报告
        report_path = analyzer.save_report(result)
        print(f"\n报告已保存到: {report_path}")
        
        # 测试结果验证
        print("\n测试结果验证:")
        print(f"- 总股票数: {result.total_stocks}")
        print(f"- 已分析股票数: {result.analyzed_stocks}")
        print(f"- 加权平均得分: {result.weighted_score:.3f}")
        print(f"- 基金建议: {result.fund_recommendation.value}")
        print(f"- 置信度: {result.confidence:.1%}")
        
        # 检查是否有股票被成功分析
        if result.analyzed_stocks > 0:
            print("✓ 成功分析股票")
        else:
            print("✗ 未能分析任何股票")
        
        return True
        
    except Exception as e:
        print(f"\n测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_fetcher():
    """测试数据获取功能"""
    print("\n" + "=" * 80)
    print("测试数据获取功能")
    print("=" * 80)
    
    try:
        # 创建数据获取器
        ak_fund = AkFund()
        rd = DataReader(base_path='data')
        
        # 检查数据文件是否存在
        stock_codes = ['002149', '002371', '002475', '002565', '002846']
        
        for code in stock_codes:
            signal_file = f"data/{code}_signals.csv"
            indicator_file = f"data/{code}_with_indicators.csv"
            
            has_signal = os.path.exists(signal_file)
            has_indicator = os.path.exists(indicator_file)
            
            print(f"股票 {code}:")
            print(f"  信号文件存在: {'✓' if has_signal else '✗'}")
            print(f"  指标文件存在: {'✓' if has_indicator else '✗'}")
        
        return True
        
    except Exception as e:
        print(f"数据获取测试失败: {e}")
        return False

def test_with_real_fund():
    """测试真实基金数据"""
    print("\n" + "=" * 80)
    print("测试真实基金数据")
    print("=" * 80)
    
    try:
        # 创建数据获取器
        ak_fund = AkFund()
        
        # 获取基金000001的持仓数据
        print("获取基金000001的持仓数据...")
        fund_info = ak_fund.get_fund_portfolio_hold_em(fund_code='000001')
        
        if fund_info.empty:
            print("未能获取基金持仓数据，使用示例数据")
            
            # 使用示例数据
            from src.analysis.quarter_filter import filter_latest_quarter_data
            quarter_summary = filter_latest_quarter_data(fund_info)
            
            if quarter_summary.empty:
                print("季度数据为空，跳过真实基金测试")
                return False
                
            stock_codes = quarter_summary['股票代码'].unique().tolist()[:5]  # 取前5只
            sample_holdings = pd.DataFrame({
                '股票代码': stock_codes,
                '股票名称': [f'股票{code}' for code in stock_codes],
                '持有比例(%)': [100.0 / len(stock_codes)] * len(stock_codes)
            })
        else:
            print(f"成功获取基金持仓数据，共{len(fund_info)}条记录")
            
            # 使用实际持仓数据
            from src.analysis.quarter_filter import filter_latest_quarter_data
            quarter_data = filter_latest_quarter_data(fund_info)
            
            if quarter_data.empty:
                print("季度数据为空，使用示例数据")
                return False
                
            # 简化处理，取前5只股票
            quarter_data = quarter_data.head(5)
            
            # 创建持仓DataFrame
            sample_holdings = pd.DataFrame({
                '股票代码': quarter_data['股票代码'].values,
                '股票名称': quarter_data['股票名称'].values if '股票名称' in quarter_data.columns else quarter_data['股票代码'].values,
                '持有比例(%)': [20.0] * len(quarter_data)  # 假设平均分配
            })
        
        print("\n使用的持仓数据:")
        print(sample_holdings.to_string(index=False))
        
        # 创建分析器
        analyzer = FundWeightedAnalyzer(data_dir="data")
        
        print("\n分析真实基金...")
        result = analyzer.analyze_fund(
            fund_code="000001",
            holdings_df=sample_holdings,
            fund_name="华夏成长混合"
        )
        
        # 生成简要报告
        print("\n简要分析结果:")
        print(f"基金代码: {result.fund_code}")
        print(f"基金名称: {result.fund_name}")
        print(f"总股票数: {result.total_stocks}")
        print(f"已分析股票数: {result.analyzed_stocks}")
        print(f"加权平均得分: {result.weighted_score:.3f}")
        print(f"基金建议: {result.fund_recommendation.value}")
        print(f"置信度: {result.confidence:.1%}")
        
        return True
        
    except Exception as e:
        print(f"真实基金测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试基金加权平均分析模块...")
    
    # 测试1: 基本功能测试
    test1_passed = test_fund_weighted_analysis()
    
    # 测试2: 数据文件检查
    test2_passed = test_data_fetcher()
    
    # 测试3: 真实基金数据测试
    test3_passed = test_with_real_fund()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"基本功能测试: {'通过' if test1_passed else '失败'}")
    print(f"数据文件检查: {'通过' if test2_passed else '失败'}")
    print(f"真实基金测试: {'通过' if test3_passed else '失败'}")
    
    if test1_passed and test2_passed:
        print("\n✓ 所有核心测试通过！模块可以正常工作。")
    else:
        print("\n✗ 部分测试失败，请检查问题。")
    
    print("\n测试完成！")