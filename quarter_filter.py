"""
季度数据过滤模块
提供从DataFrame中提取最新季度数据的功能
"""

import pandas as pd
import numpy as np
import re
from typing import Tuple, Optional
from loguru import logger


def filter_latest_quarter_data(df: pd.DataFrame, quarter_column: str = '季度') -> pd.DataFrame:
    """
    从DataFrame中过滤出最新季度的数据
    
    Args:
        df: 输入的DataFrame，必须包含指定的季度列
        quarter_column: 季度列名，默认为'季度'
        
    Returns:
        只包含最新季度数据的DataFrame，保持原始数据结构和列顺序
        
    Raises:
        ValueError: 当季度列不存在或数据为空时
        ValueError: 当季度列格式无法解析时
    """
    # 验证输入
    if df.empty:
        raise ValueError("输入DataFrame不能为空")
    
    if quarter_column not in df.columns:
        raise ValueError(f"DataFrame中不存在列 '{quarter_column}'")
    
    # 复制DataFrame以避免修改原始数据
    result_df = df.copy()
    
    # 解析季度信息
    year_quarter_pairs = []
    invalid_indices = []
    
    for idx, quarter_str in enumerate(result_df[quarter_column]):
        try:
            year, quarter = parse_quarter_string(quarter_str)
            year_quarter_pairs.append((idx, year, quarter))
        except (ValueError, AttributeError) as e:
            logger.warning(f"无法解析第{idx}行的季度信息 '{quarter_str}': {e}")
            invalid_indices.append(idx)
    
    # 如果没有有效的季度数据，返回空DataFrame
    if not year_quarter_pairs:
        logger.error("没有找到有效的季度数据")
        return pd.DataFrame(columns=df.columns)
    
    # 识别最新的年份-季度组合
    # 先按年份降序排序，再按季度降序排序
    year_quarter_pairs.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    # 获取最新的年份和季度
    latest_idx, latest_year, latest_quarter = year_quarter_pairs[0]
    
    logger.info(f"识别到最新季度: {latest_year}年Q{latest_quarter}")
    
    # 过滤出属于最新季度的所有行
    latest_quarter_indices = [
        idx for idx, year, quarter in year_quarter_pairs
        if year == latest_year and quarter == latest_quarter
    ]
    
    # 过滤DataFrame
    filtered_df = result_df.iloc[latest_quarter_indices].copy()
    
    # 保留原始列顺序
    filtered_df = filtered_df[df.columns]
    
    logger.info(f"过滤结果: 从 {len(df)} 条记录中筛选出 {len(filtered_df)} 条最新季度数据")
    
    return filtered_df


def parse_quarter_string(quarter_str: str) -> Tuple[int, int]:
    """
    解析季度字符串，提取年份和季度信息
    
    支持的格式：
    - "YYYY年Q季度股票投资明细" (例如: "2025年1季度股票投资明细")
    - "YYYY年Q季度" (例如: "2025年Q1")
    - "YYYY-Q季度" (例如: "2025-Q1")
    - "YYYYQ季度" (例如: "2025Q1")
    
    Args:
        quarter_str: 季度字符串
        
    Returns:
        (年份, 季度) 元组
        
    Raises:
        ValueError: 当字符串格式无法解析时
        AttributeError: 当输入不是字符串时
    """
    if not isinstance(quarter_str, str):
        raise AttributeError(f"季度信息必须是字符串类型，实际类型: {type(quarter_str)}")
    
    quarter_str = quarter_str.strip()
    
    # 尝试不同的格式模式
    
    # 模式1: "YYYY年Q季度股票投资明细" 或 "YYYY年Q季度"
    pattern1 = r'(\d{4})\s*年\s*(\d+)\s*季度'
    match1 = re.search(pattern1, quarter_str)
    if match1:
        year = int(match1.group(1))
        quarter = int(match1.group(2))
        if 1 <= quarter <= 4:
            return year, quarter
    
    # 模式2: "YYYY年Q季度" (Q1, Q2, Q3, Q4)
    pattern2 = r'(\d{4})\s*年\s*Q([1-4])'
    match2 = re.search(pattern2, quarter_str)
    if match2:
        year = int(match2.group(1))
        quarter = int(match2.group(2))
        return year, quarter
    
    # 模式3: "YYYY-Q季度" (例如: 2025-Q1)
    pattern3 = r'(\d{4})-Q([1-4])'
    match3 = re.search(pattern3, quarter_str)
    if match3:
        year = int(match3.group(1))
        quarter = int(match3.group(2))
        return year, quarter
    
    # 模式4: "YYYYQ季度" (例如: 2025Q1)
    pattern4 = r'(\d{4})Q([1-4])'
    match4 = re.search(pattern4, quarter_str)
    if match4:
        year = int(match4.group(1))
        quarter = int(match4.group(2))
        return year, quarter
    
    # 模式5: "YYYY年Q季度" (中文数字)
    pattern5 = r'(\d{4})\s*年\s*([一二三四])\s*季度'
    match5 = re.search(pattern5, quarter_str)
    if match5:
        year = int(match5.group(1))
        quarter_chinese = match5.group(2)
        quarter_map = {'一': 1, '二': 2, '三': 3, '四': 4}
        quarter = quarter_map.get(quarter_chinese)
        if quarter:
            return year, quarter
    
    # 如果所有模式都不匹配，抛出异常
    raise ValueError(f"无法解析季度字符串: '{quarter_str}'")


def get_quarter_summary(df: pd.DataFrame, quarter_column: str = '季度') -> dict:
    """
    获取DataFrame中季度数据的摘要信息
    
    Args:
        df: 输入的DataFrame
        quarter_column: 季度列名，默认为'季度'
        
    Returns:
        包含季度摘要的字典：
        - total_rows: 总行数
        - unique_quarters: 唯一季度的数量
        - latest_quarter: 最新季度信息 (year, quarter)
        - quarter_distribution: 各季度的数据分布
    """
    if df.empty:
        return {
            'total_rows': 0,
            'unique_quarters': 0,
            'latest_quarter': None,
            'quarter_distribution': {}
        }
    
    if quarter_column not in df.columns:
        return {
            'total_rows': len(df),
            'unique_quarters': 0,
            'latest_quarter': None,
            'quarter_distribution': {}
        }
    
    # 解析所有季度信息
    year_quarter_list = []
    for quarter_str in df[quarter_column]:
        try:
            year, quarter = parse_quarter_string(quarter_str)
            year_quarter_list.append((year, quarter))
        except (ValueError, AttributeError):
            continue
    
    if not year_quarter_list:
        return {
            'total_rows': len(df),
            'unique_quarters': 0,
            'latest_quarter': None,
            'quarter_distribution': {}
        }
    
    # 获取最新季度
    year_quarter_list.sort(key=lambda x: (x[0], x[1]), reverse=True)
    latest_year, latest_quarter = year_quarter_list[0]
    
    # 统计季度分布
    quarter_distribution = {}
    for idx, quarter_str in enumerate(df[quarter_column]):
        try:
            year, quarter = parse_quarter_string(quarter_str)
            key = f"{year}年Q{quarter}"
            quarter_distribution[key] = quarter_distribution.get(key, 0) + 1
        except (ValueError, AttributeError):
            continue
    
    return {
        'total_rows': len(df),
        'unique_quarters': len(set(year_quarter_list)),
        'latest_quarter': (latest_year, latest_quarter),
        'quarter_distribution': quarter_distribution
    }


def filter_by_quarter_range(df: pd.DataFrame, 
                          start_year: int, 
                          start_quarter: int,
                          end_year: Optional[int] = None,
                          end_quarter: Optional[int] = None,
                          quarter_column: str = '季度') -> pd.DataFrame:
    """
    按季度范围过滤数据
    
    Args:
        df: 输入的DataFrame
        start_year: 起始年份
        start_quarter: 起始季度 (1-4)
        end_year: 结束年份（可选，默认为起始年份）
        end_quarter: 结束季度（可选，默认为起始季度）
        quarter_column: 季度列名，默认为'季度'
        
    Returns:
        过滤后的DataFrame
        
    Raises:
        ValueError: 当季度值无效时
    """
    # 验证季度值
    if not (1 <= start_quarter <= 4):
        raise ValueError(f"起始季度必须在1-4之间，实际值: {start_quarter}")
    
    # 设置默认结束年份和季度
    if end_year is None:
        end_year = start_year
    if end_quarter is None:
        end_quarter = start_quarter
    
    if not (1 <= end_quarter <= 4):
        raise ValueError(f"结束季度必须在1-4之间，实际值: {end_quarter}")
    
    # 创建起始和结束的季度元组
    start_q = (start_year, start_quarter)
    end_q = (end_year, end_quarter)
    
    # 解析所有季度信息
    filtered_indices = []
    for idx, quarter_str in enumerate(df[quarter_column]):
        try:
            year, quarter = parse_quarter_string(quarter_str)
            current_q = (year, quarter)
            
            # 检查是否在范围内
            if start_q <= current_q <= end_q:
                filtered_indices.append(idx)
        except (ValueError, AttributeError):
            continue
    
    # 过滤DataFrame
    filtered_df = df.iloc[filtered_indices].copy()
    
    # 保留原始列顺序
    filtered_df = filtered_df[df.columns]
    
    logger.info(f"按季度范围过滤: 从 {len(df)} 条记录中筛选出 {len(filtered_df)} 条记录")
    logger.info(f"范围: {start_year}年Q{start_quarter} 至 {end_year}年Q{end_quarter}")
    
    return filtered_df


# 示例用法
if __name__ == "__main__":
    # 创建示例数据
    sample_data = pd.DataFrame({
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
    
    print("=" * 80)
    print("季度数据过滤示例")
    print("=" * 80)
    
    # 显示原始数据
    print("\n【原始数据】")
    print(sample_data)
    
    # 获取季度摘要
    print("\n【季度摘要】")
    summary = get_quarter_summary(sample_data)
    print(f"总行数: {summary['total_rows']}")
    print(f"唯一季度数: {summary['unique_quarters']}")
    print(f"最新季度: {summary['latest_quarter'][0]}年Q{summary['latest_quarter'][1]}")
    print(f"季度分布: {summary['quarter_distribution']}")
    
    # 过滤最新季度数据
    print("\n【过滤最新季度数据】")
    latest_data = filter_latest_quarter_data(sample_data)
    print(latest_data)
    
    # 按季度范围过滤
    print("\n【按季度范围过滤】")
    range_data = filter_by_quarter_range(
        sample_data, 
        start_year=2024, 
        start_quarter=2,
        end_year=2024,
        end_quarter=4
    )
    print(range_data)
    
    # 测试边缘情况
    print("\n【测试边缘情况】")
    
    # 测试1: 非标准格式
    edge_case_data = pd.DataFrame({
        '季度': ['2025-Q1', '2025Q2', '2025年Q3', '2025年四季度'],
        '数值': [100, 200, 300, 400]
    })
    print("\n测试1: 非标准格式")
    print(edge_case_data)
    latest_edge = filter_latest_quarter_data(edge_case_data)
    print("最新季度数据:")
    print(latest_edge)
    
    # 测试2: 空DataFrame
    print("\n测试2: 空DataFrame")
    try:
        filter_latest_quarter_data(pd.DataFrame())
    except ValueError as e:
        print(f"✓ 正确处理空DataFrame: {e}")
    
    # 测试3: 缺少季度列
    print("\n测试3: 缺少季度列")
    try:
        filter_latest_quarter_data(pd.DataFrame({'其他列': [1, 2, 3]}))
    except ValueError as e:
        print(f"✓ 正确处理缺少列: {e}")
    
    print("\n" + "=" * 80)
    print("所有测试完成")
    print("=" * 80)
