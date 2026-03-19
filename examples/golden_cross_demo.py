"""
金叉/死叉分析演示程序
展示完整的金叉/死叉分析功能
"""

import pandas as pd
import numpy as np
from datetime import datetime
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from ak_fund import AkFund
from golden_cross_analyzer import GoldenCrossAnalyzer
from golden_cross_visualizer import GoldenCrossVisualizer
from loguru import logger


def main():
    """主函数"""
    print("=" * 80)
    print("金叉/死叉技术信号分析演示")
    print("=" * 80)
    
    # 获取股票数据
    print("\n【步骤1】获取股票数据")
    print("-" * 80)
    ak_fund = AkFund()
    symbol = '600519'  # 贵州茅台
    
    try:
        stock_data = ak_fund.get_stock_kline(
            symbol=symbol,
            period='daily',
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        print(f"✓ 成功获取 {symbol} 的股票数据")
        print(f"  数据时间范围: {stock_data['date'].min()} 至 {stock_data['date'].max()}")
        print(f"  数据行数: {len(stock_data)}")
    except Exception as e:
        print(f"✗ 数据获取失败: {e}")
        return
    
    # 创建分析器
    print("\n【步骤2】创建金叉/死叉分析器")
    print("-" * 80)
    analyzer = GoldenCrossAnalyzer(stock_data)
    print("✓ 分析器创建成功")
    
    # 识别金叉
    print("\n【步骤3】识别金叉信号")
    print("-" * 80)
    start_time = time.time()
    golden_crosses = analyzer.identify_golden_cross(short_period=5, long_period=20)
    execution_time = (time.time() - start_time) * 1000
    
    print(f"✓ 金叉识别完成，耗时 {execution_time:.2f}ms")
    print(f"  识别到 {len(golden_crosses)} 个金叉信号")
    
    if not golden_crosses.empty:
        print("\n  金叉信号详情（前5个）：")
        print(golden_crosses[['date', 'price', 'strength', 'price_change_5d']].head().to_string(index=False))
    
    # 识别死叉
    print("\n【步骤4】识别死叉信号")
    print("-" * 80)
    start_time = time.time()
    death_crosses = analyzer.identify_death_cross(short_period=5, long_period=20)
    execution_time = (time.time() - start_time) * 1000
    
    print(f"✓ 死叉识别完成，耗时 {execution_time:.2f}ms")
    print(f"  识别到 {len(death_crosses)} 个死叉信号")
    
    if not death_crosses.empty:
        print("\n  死叉信号详情（前5个）：")
        print(death_crosses[['date', 'price', 'strength', 'price_change_5d']].head().to_string(index=False))
    
    # 评估信号有效性
    print("\n【步骤5】评估信号有效性")
    print("-" * 80)
    
    if not golden_crosses.empty:
        valid_golden = analyzer.evaluate_signal_validity(golden_crosses)
        print("✓ 金叉信号有效性评估完成")
        
        # 统计信号等级
        signal_levels = valid_golden['signal_level'].value_counts()
        print("\n  信号等级分布：")
        for level, count in signal_levels.items():
            print(f"    {level}: {count} 个")
        
        # 显示有效信号
        valid_signals = valid_golden[valid_golden['signal_level'] == '有效']
        if not valid_signals.empty:
            print(f"\n  有效信号示例（前3个）：")
            print(valid_signals[['date', 'strength', 'validity_score']].head(3).to_string(index=False))
    
    if not death_crosses.empty:
        valid_death = analyzer.evaluate_signal_validity(death_crosses)
        print("✓ 死叉信号有效性评估完成")
    
    # 历史回测
    print("\n【步骤6】历史回测")
    print("-" * 80)
    start_time = time.time()
    backtest_results = analyzer.backtest_signals(
        short_period=5,
        long_period=20,
        holding_period=10,
        stop_loss=-5.0,
        take_profit=10.0
    )
    execution_time = (time.time() - start_time) * 1000
    
    print(f"✓ 回测完成，耗时 {execution_time:.2f}ms")
    print(f"  总交易次数: {backtest_results['total_trades']}")
    print(f"  盈利交易: {backtest_results['profitable_trades']}")
    print(f"  亏损交易: {backtest_results['losing_trades']}")
    print(f"  准确率: {backtest_results['accuracy']:.2f}%")
    print(f"  盈亏比: {backtest_results['profit_loss_ratio']:.2f}")
    
    if not backtest_results['detailed_results'].empty:
        print(f"\n  详细交易记录（前5笔）：")
        print(backtest_results['detailed_results'][
            ['date', 'signal_type', 'entry_price', 'exit_price', 'profit', 'exit_reason']
        ].head().to_string(index=False))
    
    # 多时间周期分析
    print("\n【步骤7】多时间周期分析")
    print("-" * 80)
    
    try:
        # 获取周线数据
        weekly_data = ak_fund.get_stock_kline(
            symbol=symbol,
            period='weekly',
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        
        # 获取月线数据
        monthly_data = ak_fund.get_stock_kline(
            symbol=symbol,
            period='monthly',
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        
        # 多时间周期分析
        multi_results = analyzer.multi_timeframe_analysis(
            daily_data=stock_data,
            weekly_data=weekly_data,
            monthly_data=monthly_data,
            short_period=5,
            long_period=20
        )
        
        print("✓ 多时间周期分析完成")
        
        # 统计各时间周期的信号数量
        for timeframe, data in multi_results.items():
            golden_count = len(data['golden_cross'])
            death_count = len(data['death_cross'])
            print(f"  {timeframe}: 金叉 {golden_count} 个, 死叉 {death_count} 个")
        
    except Exception as e:
        print(f"✗ 多时间周期分析失败: {e}")
        multi_results = None
    
    # 可视化
    print("\n【步骤8】生成可视化图表")
    print("-" * 80)
    
    signals = {
        'golden_cross': golden_crosses,
        'death_cross': death_crosses
    }
    
    visualizer = GoldenCrossVisualizer(stock_data, signals)
    
    # 生成仪表盘
    dashboard = visualizer.generate_dashboard(
        short_period=5,
        long_period=20,
        backtest_results=backtest_results,
        multi_timeframe_data=multi_results
    )
    
    print("✓ 仪表盘生成成功")
    print(f"  包含 {len(dashboard['charts'])} 个图表")
    
    # 导出HTML
    output_file = 'golden_cross_demo_dashboard.html'
    html_content = visualizer.export_html(
        output_file=output_file,
        short_period=5,
        long_period=20,
        backtest_results=backtest_results,
        multi_timeframe_data=multi_results
    )
    
    print(f"✓ HTML文件已导出: {output_file}")
    print(f"  文件大小: {len(html_content)} 字符")
    
    # 获取信号摘要
    print("\n【步骤9】信号摘要")
    print("-" * 80)
    summary = analyzer.get_signal_summary()
    
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 性能验证
    print("\n【步骤10】性能验证")
    print("-" * 80)
    
    # 测试金叉识别性能
    start_time = time.time()
    analyzer.identify_golden_cross(short_period=5, long_period=20)
    golden_cross_time = (time.time() - start_time) * 1000
    
    # 测试死叉识别性能
    start_time = time.time()
    analyzer.identify_death_cross(short_period=5, long_period=20)
    death_cross_time = (time.time() - start_time) * 1000
    
    # 测试回测性能
    start_time = time.time()
    analyzer.backtest_signals(short_period=5, long_period=20, holding_period=10)
    backtest_time = (time.time() - start_time) * 1000
    
    print("✓ 性能测试结果：")
    print(f"  金叉识别: {golden_cross_time:.2f}ms")
    print(f"  死叉识别: {death_cross_time:.2f}ms")
    print(f"  回测: {backtest_time:.2f}ms")
    
    # 验证性能要求
    performance_ok = True
    if golden_cross_time >= 100:
        print(f"  ✗ 金叉识别性能不达标（要求 < 100ms）")
        performance_ok = False
    if death_cross_time >= 100:
        print(f"  ✗ 死叉识别性能不达标（要求 < 100ms）")
        performance_ok = False
    if backtest_time >= 100:
        print(f"  ✗ 回测性能不达标（要求 < 100ms）")
        performance_ok = False
    
    if performance_ok:
        print("  ✓ 所有性能测试通过")
    
    # 总结
    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)
    print(f"\n总结：")
    print(f"  识别到 {len(golden_crosses)} 个金叉信号")
    print(f"  识别到 {len(death_crosses)} 个死叉信号")
    print(f"  回测准确率: {backtest_results['accuracy']:.2f}%")
    print(f"  盈亏比: {backtest_results['profit_loss_ratio']:.2f}")
    print(f"  性能满足要求: {'是' if performance_ok else '否'}")
    print(f"\n可视化文件: {output_file}")
    print(f"请用浏览器打开该文件查看完整的可视化图表")
    
    return {
        'golden_cross_count': len(golden_crosses),
        'death_cross_count': len(death_crosses),
        'accuracy': backtest_results['accuracy'],
        'profit_loss_ratio': backtest_results['profit_loss_ratio'],
        'performance_ok': performance_ok,
        'output_file': output_file
    }


if __name__ == "__main__":
    # 配置日志
    logger.add("golden_cross_demo.log", rotation="500 MB", level="INFO")
    
    # 运行演示
    try:
        result = main()
        
        # 保存结果
        with open('golden_cross_demo_result.txt', 'w', encoding='utf-8') as f:
            f.write(f"金叉数量: {result['golden_cross_count']}\n")
            f.write(f"死叉数量: {result['death_cross_count']}\n")
            f.write(f"准确率: {result['accuracy']:.2f}%\n")
            f.write(f"盈亏比: {result['profit_loss_ratio']:.2f}\n")
            f.write(f"性能达标: {'是' if result['performance_ok'] else '否'}\n")
            f.write(f"输出文件: {result['output_file']}\n")
        
        print(f"\n结果已保存到 golden_cross_demo_result.txt")
        
    except Exception as e:
        logger.error(f"演示程序运行失败: {e}")
        import traceback
        traceback.print_exc()
