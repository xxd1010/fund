"""
季度数据过滤模块演示程序
展示如何使用quarter_filter模块过滤最新季度数据
"""

import pandas as pd
from quarter_filter import (
    filter_latest_quarter_data,
    get_quarter_summary,
    filter_by_quarter_range
)


def demo_basic_usage():
    """演示基本用法"""
    print("=" * 80)
    print("演示1: 基本用法 - 过滤最新季度数据")
    print("=" * 80)
    
    # 创建示例数据
    data = pd.DataFrame({
        '季度': [
            '2024年1季度股票投资明细',
            '2024年2季度股票投资明细',
            '2024年3季度股票投资明细',
            '2024年4季度股票投资明细',
            '2025年1季度股票投资明细',
            '2025年1季度股票投资明细',  # 同一季度的多个条目
            '2025年2季度股票投资明细',
        ],
        '股票代码': ['600519', '000001', '600036', '000002', '600519', '000001', '600036'],
        '股票名称': ['贵州茅台', '平安银行', '招商银行', '万科A', '贵州茅台', '平安银行', '招商银行'],
        '投资金额': [100000, 200000, 150000, 180000, 120000, 250000, 160000],
    })
    
    print("\n【原始数据】")
    print(data)
    
    # 过滤最新季度数据
    latest_data = filter_latest_quarter_data(data)
    
    print("\n【最新季度数据】")
    print(latest_data)
    
    # 获取季度摘要
    summary = get_quarter_summary(data)
    print("\n【季度摘要】")
    print(f"总行数: {summary['total_rows']}")
    print(f"唯一季度数: {summary['unique_quarters']}")
    print(f"最新季度: {summary['latest_quarter'][0]}年Q{summary['latest_quarter'][1]}")
    print("季度分布:")
    for quarter, count in summary['quarter_distribution'].items():
        print(f"  {quarter}: {count}条")


def demo_different_formats():
    """演示不同格式的季度字符串"""
    print("\n" + "=" * 80)
    print("演示2: 不同格式的季度字符串")
    print("=" * 80)
    
    # 创建包含不同格式的数据
    data = pd.DataFrame({
        '季度': [
            '2024年Q4',
            '2025-Q1',
            '2025Q2',
            '2025年三季度',
            '2025年4季度股票投资明细',
        ],
        '股票代码': ['600519', '000001', '600036', '000002', '600000'],
        '股票名称': ['贵州茅台', '平安银行', '招商银行', '万科A', '浦发银行'],
        '投资金额': [100000, 200000, 150000, 180000, 120000],
    })
    
    print("\n【原始数据（混合格式）】")
    print(data)
    
    # 过滤最新季度数据
    latest_data = filter_latest_quarter_data(data)
    
    print("\n【最新季度数据】")
    print(latest_data)


def demo_year_priority():
    """演示年份优先级"""
    print("\n" + "=" * 80)
    print("演示3: 年份优先级（年份优先于季度）")
    print("=" * 80)
    
    # 创建测试数据
    data = pd.DataFrame({
        '季度': [
            '2025年4季度股票投资明细',
            '2026年1季度股票投资明细',
            '2026年2季度股票投资明细',
        ],
        '股票代码': ['600519', '000001', '600036'],
        '股票名称': ['贵州茅台', '平安银行', '招商银行'],
        '投资金额': [100000, 200000, 150000],
    })
    
    print("\n【原始数据】")
    print(data)
    
    # 过滤最新季度数据
    latest_data = filter_latest_quarter_data(data)
    
    print("\n【最新季度数据】")
    print(latest_data)
    print("\n说明: 2026年Q2比2025年Q4更新，因为年份优先")


def demo_range_filter():
    """演示按季度范围过滤"""
    print("\n" + "=" * 80)
    print("演示4: 按季度范围过滤")
    print("=" * 80)
    
    # 创建测试数据
    data = pd.DataFrame({
        '季度': [
            '2024年1季度股票投资明细',
            '2024年2季度股票投资明细',
            '2024年3季度股票投资明细',
            '2024年4季度股票投资明细',
            '2025年1季度股票投资明细',
            '2025年2季度股票投资明细',
        ],
        '股票代码': ['600519', '000001', '600036', '000002', '600519', '000001'],
        '股票名称': ['贵州茅台', '平安银行', '招商银行', '万科A', '贵州茅台', '平安银行'],
        '投资金额': [100000, 200000, 150000, 180000, 120000, 250000],
    })
    
    print("\n【原始数据】")
    print(data)
    
    # 过滤2024年Q2到2024年Q4的数据
    range_data = filter_by_quarter_range(
        data,
        start_year=2024,
        start_quarter=2,
        end_year=2024,
        end_quarter=4
    )
    
    print("\n【2024年Q2至2024年Q4的数据】")
    print(range_data)
    
    # 过滤跨年范围
    cross_year_data = filter_by_quarter_range(
        data,
        start_year=2024,
        start_quarter=3,
        end_year=2025,
        end_quarter=1
    )
    
    print("\n【2024年Q3至2025年Q1的数据（跨年）】")
    print(cross_year_data)


def demo_edge_cases():
    """演示边缘情况处理"""
    print("\n" + "=" * 80)
    print("演示5: 边缘情况处理")
    print("=" * 80)
    
    # 测试1: 同一季度的多个条目
    print("\n测试1: 同一季度的多个条目")
    data1 = pd.DataFrame({
        '季度': [
            '2025年1季度股票投资明细',
            '2025年1季度股票投资明细',
            '2025年1季度股票投资明细',
        ],
        '股票代码': ['600519', '000001', '600036'],
        '股票名称': ['贵州茅台', '平安银行', '招商银行'],
        '投资金额': [100000, 200000, 150000],
    })
    print("原始数据:")
    print(data1)
    latest1 = filter_latest_quarter_data(data1)
    print("过滤结果:")
    print(latest1)
    print("✓ 所有同一季度的条目都被保留")
    
    # 测试2: 包含无效格式的数据
    print("\n测试2: 包含无效格式的数据")
    data2 = pd.DataFrame({
        '季度': [
            '2024年1季度股票投资明细',
            '无效格式',
            '2025年1季度股票投资明细',
            None,
        ],
        '股票代码': ['600519', '000001', '600036', '000002'],
        '股票名称': ['贵州茅台', '平安银行', '招商银行', '万科A'],
        '投资金额': [100000, 200000, 150000, 180000],
    })
    print("原始数据:")
    print(data2)
    latest2 = filter_latest_quarter_data(data2)
    print("过滤结果:")
    print(latest2)
    print("✓ 无效格式被跳过，返回有效数据中的最新季度")


def demo_real_world_scenario():
    """演示真实世界场景"""
    print("\n" + "=" * 80)
    print("演示6: 真实世界场景 - 基金持仓分析")
    print("=" * 80)
    
    # 模拟基金持仓数据
    fund_holdings = pd.DataFrame({
        '季度': [
            '2024年1季度股票投资明细',
            '2024年2季度股票投资明细',
            '2024年3季度股票投资明细',
            '2024年4季度股票投资明细',
            '2025年1季度股票投资明细',
            '2025年1季度股票投资明细',
            '2025年1季度股票投资明细',
            '2025年2季度股票投资明细',
            '2025年2季度股票投资明细',
        ],
        '股票代码': [
            '600519', '000001', '600036', '000002',
            '600519', '000001', '600036', '600519', '000001'
        ],
        '股票名称': [
            '贵州茅台', '平安银行', '招商银行', '万科A',
            '贵州茅台', '平安银行', '招商银行', '贵州茅台', '平安银行'
        ],
        '持仓数量': [1000, 2000, 1500, 1800, 1200, 2500, 1600, 1300, 2600],
        '持仓市值': [1000000, 200000, 150000, 180000, 1200000, 250000, 160000, 1300000, 260000],
        '占净值比例': [10.5, 2.1, 1.6, 1.9, 12.6, 2.6, 1.7, 13.7, 2.7],
    })
    
    print("\n【基金持仓数据】")
    print(fund_holdings)
    
    # 获取季度摘要
    summary = get_quarter_summary(fund_holdings)
    print("\n【季度摘要】")
    print(f"数据覆盖期间: 2024年Q1 至 {summary['latest_quarter'][0]}年Q{summary['latest_quarter'][1]}")
    print(f"总持仓记录: {summary['total_rows']}条")
    print(f"涉及季度数: {summary['unique_quarters']}个")
    
    # 过滤最新季度数据
    latest_holdings = filter_latest_quarter_data(fund_holdings)
    print(f"\n【{summary['latest_quarter'][0]}年Q{summary['latest_quarter'][1]}最新持仓】")
    print(latest_holdings)
    
    # 计算最新季度的总持仓市值
    total_value = latest_holdings['持仓市值'].sum()
    print(f"\n最新季度总持仓市值: ¥{total_value:,.2f}")
    
    # 过滤2024年全年的数据
    full_year_data = filter_by_quarter_range(
        fund_holdings,
        start_year=2024,
        start_quarter=1,
        end_year=2024,
        end_quarter=4
    )
    print(f"\n【2024年全年持仓记录】")
    print(f"记录数: {len(full_year_data)}条")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("季度数据过滤模块演示")
    print("=" * 80)
    
    # 运行各个演示
    demo_basic_usage()
    demo_different_formats()
    demo_year_priority()
    demo_range_filter()
    demo_edge_cases()
    demo_real_world_scenario()
    
    print("\n" + "=" * 80)
    print("演示完成")
    print("=" * 80)
    print("\n主要功能:")
    print("✓ 支持多种季度格式解析")
    print("✓ 准确识别最新季度数据")
    print("✓ 保持原始数据结构和列顺序")
    print("✓ 处理同一季度的多个条目")
    print("✓ 年份优先于季度的比较逻辑")
    print("✓ 按季度范围过滤数据")
    print("✓ 完善的边缘情况处理")
    print("✓ 详细的季度摘要信息")
    print("\n使用方法:")
    print("from quarter_filter import filter_latest_quarter_data")
    print("latest_data = filter_latest_quarter_data(your_dataframe)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
