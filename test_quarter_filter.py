"""
季度数据过滤模块测试
验证过滤功能的正确性和边缘情况处理
"""

import pytest
import pandas as pd
import numpy as np
from quarter_filter import (
    filter_latest_quarter_data,
    parse_quarter_string,
    get_quarter_summary,
    filter_by_quarter_range
)


class TestParseQuarterString:
    """测试季度字符串解析"""
    
    def test_standard_format(self):
        """测试标准格式"""
        # 测试 "YYYY年Q季度股票投资明细" 格式
        year, quarter = parse_quarter_string("2025年1季度股票投资明细")
        assert year == 2025
        assert quarter == 1
        
        year, quarter = parse_quarter_string("2024年4季度股票投资明细")
        assert year == 2024
        assert quarter == 4
    
    def test_q_format(self):
        """测试Q格式"""
        # 测试 "YYYY年Q季度" 格式
        year, quarter = parse_quarter_string("2025年Q1")
        assert year == 2025
        assert quarter == 1
        
        year, quarter = parse_quarter_string("2024年Q4")
        assert year == 2024
        assert quarter == 4
    
    def test_dash_format(self):
        """测试短横线格式"""
        # 测试 "YYYY-Q季度" 格式
        year, quarter = parse_quarter_string("2025-Q1")
        assert year == 2025
        assert quarter == 1
    
    def test_compact_format(self):
        """测试紧凑格式"""
        # 测试 "YYYYQ季度" 格式
        year, quarter = parse_quarter_string("2025Q1")
        assert year == 2025
        assert quarter == 1
    
    def test_chinese_number_format(self):
        """测试中文数字格式"""
        # 测试 "YYYY年X季度" 格式（中文数字）
        year, quarter = parse_quarter_string("2025年一季度")
        assert year == 2025
        assert quarter == 1
        
        year, quarter = parse_quarter_string("2025年四季度")
        assert year == 2025
        assert quarter == 4
    
    def test_invalid_format(self):
        """测试无效格式"""
        # 测试无法解析的格式
        with pytest.raises(ValueError):
            parse_quarter_string("无效格式")
        
        with pytest.raises(ValueError):
            parse_quarter_string("2025/01/01")
    
    def test_non_string_input(self):
        """测试非字符串输入"""
        # 测试非字符串输入
        with pytest.raises(AttributeError):
            parse_quarter_string(2025)
        
        with pytest.raises(AttributeError):
            parse_quarter_string(None)
    
    def test_invalid_quarter_value(self):
        """测试无效的季度值"""
        # 测试超出范围的季度值
        with pytest.raises(ValueError):
            parse_quarter_string("2025年0季度")
        
        with pytest.raises(ValueError):
            parse_quarter_string("2025年5季度")


class TestFilterLatestQuarterData:
    """测试最新季度数据过滤"""
    
    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        return pd.DataFrame({
            '季度': [
                '2024年1季度股票投资明细',
                '2024年2季度股票投资明细',
                '2024年3季度股票投资明细',
                '2024年4季度股票投资明细',
                '2025年1季度股票投资明细',
                '2025年1季度股票投资明细',  # 同一季度的多个条目
                '2025年2季度股票投资明细',
                '2025年2季度股票投资明细',  # 添加第二个Q2条目
            ],
            '股票代码': ['600519', '000001', '600036', '000002', '600519', '000001', '600036', '000002'],
            '股票名称': ['贵州茅台', '平安银行', '招商银行', '万科A', '贵州茅台', '平安银行', '招商银行', '万科A'],
            '投资金额': [100000, 200000, 150000, 180000, 120000, 250000, 160000, 180000],
        })
    
    def test_basic_filtering(self, sample_data):
        """测试基本过滤功能"""
        result = filter_latest_quarter_data(sample_data)
        
        # 验证结果
        assert len(result) == 2  # 2025年Q2应该有2条记录
        assert all(result['季度'] == '2025年2季度股票投资明细')
    
    def test_preserve_columns(self, sample_data):
        """测试保持原始列顺序"""
        original_columns = sample_data.columns.tolist()
        result = filter_latest_quarter_data(sample_data)
        result_columns = result.columns.tolist()
        
        assert original_columns == result_columns
    
    def test_empty_dataframe(self):
        """测试空DataFrame"""
        with pytest.raises(ValueError):
            filter_latest_quarter_data(pd.DataFrame())
    
    def test_missing_quarter_column(self):
        """测试缺少季度列"""
        data = pd.DataFrame({'其他列': [1, 2, 3]})
        with pytest.raises(ValueError):
            filter_latest_quarter_data(data)
    
    def test_different_formats(self):
        """测试不同格式的季度字符串"""
        data = pd.DataFrame({
            '季度': [
                '2024年Q4',
                '2025-Q1',
                '2025Q2',
                '2025年三季度',
            ],
            '数值': [100, 200, 300, 400]
        })
        
        result = filter_latest_quarter_data(data)
        
        # 验证最新季度是2025年Q3
        assert len(result) == 1
        assert result.iloc[0]['季度'] == '2025年三季度'
    
    def test_multiple_years_same_quarter(self):
        """测试不同年份相同季度的情况"""
        data = pd.DataFrame({
            '季度': [
                '2024年1季度股票投资明细',
                '2025年1季度股票投资明细',
                '2026年1季度股票投资明细',
            ],
            '数值': [100, 200, 300]
        })
        
        result = filter_latest_quarter_data(data)
        
        # 验证最新季度是2026年Q1
        assert len(result) == 1
        assert result.iloc[0]['季度'] == '2026年1季度股票投资明细'
    
    def test_year_priority(self):
        """测试年份优先级"""
        data = pd.DataFrame({
            '季度': [
                '2025年4季度股票投资明细',
                '2026年1季度股票投资明细',
            ],
            '数值': [100, 200]
        })
        
        result = filter_latest_quarter_data(data)
        
        # 验证2026年Q1比2025年Q4更新
        assert len(result) == 1
        assert result.iloc[0]['季度'] == '2026年1季度股票投资明细'


class TestGetQuarterSummary:
    """测试季度摘要功能"""
    
    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        return pd.DataFrame({
            '季度': [
                '2024年1季度股票投资明细',
                '2024年2季度股票投资明细',
                '2024年3季度股票投资明细',
                '2024年4季度股票投资明细',
                '2025年1季度股票投资明细',
                '2025年1季度股票投资明细',  # 同一季度的多个条目
                '2025年2季度股票投资明细',
                '2025年2季度股票投资明细',  # 添加第二个Q2条目
            ],
            '股票代码': ['600519', '000001', '600036', '000002', '600519', '000001', '600036', '000002'],
            '股票名称': ['贵州茅台', '平安银行', '招商银行', '万科A', '贵州茅台', '平安银行', '招商银行', '万科A'],
            '投资金额': [100000, 200000, 150000, 180000, 120000, 250000, 160000, 180000],
        })
    
    def test_basic_summary(self, sample_data):
        """测试基本摘要功能"""
        summary = get_quarter_summary(sample_data)
        
        assert summary['total_rows'] == 8
        assert summary['unique_quarters'] == 6  # 2024Q1, 2024Q2, 2024Q3, 2024Q4, 2025Q1, 2025Q2
        assert summary['latest_quarter'] == (2025, 2)
        assert '2024年Q1' in summary['quarter_distribution']
        assert '2025年Q1' in summary['quarter_distribution']
        assert '2025年Q2' in summary['quarter_distribution']
    
    def test_empty_dataframe(self):
        """测试空DataFrame"""
        summary = get_quarter_summary(pd.DataFrame())
        
        assert summary['total_rows'] == 0
        assert summary['unique_quarters'] == 0
        assert summary['latest_quarter'] is None
        assert summary['quarter_distribution'] == {}
    
    def test_missing_quarter_column(self):
        """测试缺少季度列"""
        data = pd.DataFrame({'其他列': [1, 2, 3]})
        summary = get_quarter_summary(data)
        
        # 当季度列不存在时，应该返回0个唯一季度
        assert summary['total_rows'] == 3
        assert summary['unique_quarters'] == 0
        assert summary['latest_quarter'] is None


class TestFilterByQuarterRange:
    """测试按季度范围过滤"""
    
    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        return pd.DataFrame({
            '季度': [
                '2024年1季度股票投资明细',
                '2024年2季度股票投资明细',
                '2024年3季度股票投资明细',
                '2024年4季度股票投资明细',
                '2025年1季度股票投资明细',
                '2025年2季度股票投资明细',
            ],
            '数值': [100, 200, 300, 400, 500, 600]
        })
    
    def test_basic_range_filter(self, sample_data):
        """测试基本范围过滤"""
        result = filter_by_quarter_range(
            sample_data,
            start_year=2024,
            start_quarter=2,
            end_year=2024,
            end_quarter=4
        )
        
        # 验证结果包含2024年Q2-Q4
        assert len(result) == 3
        assert all([
            '2024年2季度股票投资明细' in result['季度'].values,
            '2024年3季度股票投资明细' in result['季度'].values,
            '2024年4季度股票投资明细' in result['季度'].values
        ])
    
    def test_single_quarter(self, sample_data):
        """测试单个季度过滤"""
        result = filter_by_quarter_range(
            sample_data,
            start_year=2025,
            start_quarter=1,
            end_year=2025,
            end_quarter=1
        )
        
        # 验证结果只包含2025年Q1
        assert len(result) == 1
        assert result.iloc[0]['季度'] == '2025年1季度股票投资明细'
    
    def test_cross_year_range(self, sample_data):
        """测试跨年范围"""
        result = filter_by_quarter_range(
            sample_data,
            start_year=2024,
            start_quarter=3,
            end_year=2025,
            end_quarter=1
        )
        
        # 验证结果包含2024年Q3-Q4和2025年Q1
        assert len(result) == 3
        assert '2024年3季度股票投资明细' in result['季度'].values
        assert '2024年4季度股票投资明细' in result['季度'].values
        assert '2025年1季度股票投资明细' in result['季度'].values
    
    def test_invalid_quarter_values(self):
        """测试无效的季度值"""
        data = pd.DataFrame({
            '季度': ['2024年1季度股票投资明细'],
            '数值': [100]
        })
        
        # 测试无效的起始季度
        with pytest.raises(ValueError):
            filter_by_quarter_range(data, start_year=2024, start_quarter=0)
        
        # 测试无效的结束季度
        with pytest.raises(ValueError):
            filter_by_quarter_range(data, start_year=2024, start_quarter=1, end_quarter=5)
    
    def test_default_end_values(self, sample_data):
        """测试默认结束值"""
        result = filter_by_quarter_range(
            sample_data,
            start_year=2024,
            start_quarter=2
        )
        
        # 验证默认结束值与起始值相同
        assert len(result) == 1
        assert result.iloc[0]['季度'] == '2024年2季度股票投资明细'


class TestEdgeCases:
    """测试边缘情况"""
    
    def test_multiple_entries_same_quarter(self):
        """测试同一季度的多个条目"""
        data = pd.DataFrame({
            '季度': [
                '2025年1季度股票投资明细',
                '2025年1季度股票投资明细',
                '2025年1季度股票投资明细',
            ],
            '数值': [100, 200, 300]
        })
        
        result = filter_latest_quarter_data(data)
        
        # 验证所有同一季度的条目都被保留
        assert len(result) == 3
        assert all(result['季度'] == '2025年1季度股票投资明细')
    
    def test_mixed_formats(self):
        """测试混合格式"""
        data = pd.DataFrame({
            '季度': [
                '2024年Q4',
                '2025-Q1',
                '2025年二季度',
            ],
            '数值': [100, 200, 300]
        })
        
        result = filter_latest_quarter_data(data)
        
        # 验证能正确识别最新季度
        assert len(result) == 1
        assert result.iloc[0]['季度'] == '2025年二季度'
    
    def test_year_then_quarter_comparison(self):
        """测试年份优先于季度的比较"""
        data = pd.DataFrame({
            '季度': [
                '2025年4季度股票投资明细',
                '2026年1季度股票投资明细',
                '2026年2季度股票投资明细',
            ],
            '数值': [100, 200, 300]
        })
        
        result = filter_latest_quarter_data(data)
        
        # 验证2026年Q2比2025年Q4更新
        assert len(result) == 1
        assert result.iloc[0]['季度'] == '2026年2季度股票投资明细'
    
    def test_invalid_formats_handling(self):
        """测试无效格式的处理"""
        data = pd.DataFrame({
            '季度': [
                '2024年1季度股票投资明细',
                '无效格式',
                '2025年1季度股票投资明细',
                None,
            ],
            '数值': [100, 200, 300, 400]
        })
        
        # 应该跳过无效格式，返回有效数据中的最新季度
        result = filter_latest_quarter_data(data)
        
        # 验证结果
        assert len(result) == 1
        assert result.iloc[0]['季度'] == '2025年1季度股票投资明细'


class TestIntegration:
    """集成测试"""
    
    def test_complete_workflow(self):
        """测试完整工作流程"""
        # 创建测试数据
        data = pd.DataFrame({
            '季度': [
                '2024年1季度股票投资明细',
                '2024年2季度股票投资明细',
                '2024年3季度股票投资明细',
                '2024年4季度股票投资明细',
                '2025年1季度股票投资明细',
                '2025年1季度股票投资明细',
                '2025年2季度股票投资明细',
            ],
            '股票代码': ['600519', '000001', '600036', '000002', '600519', '000001', '600036'],
            '股票名称': ['贵州茅台', '平安银行', '招商银行', '万科A', '贵州茅台', '平安银行', '招商银行'],
            '投资金额': [100000, 200000, 150000, 180000, 120000, 250000, 160000],
        })
        
        # 获取季度摘要
        summary = get_quarter_summary(data)
        assert summary['total_rows'] == 7
        assert summary['latest_quarter'] == (2025, 2)
        
        # 过滤最新季度
        latest_data = filter_latest_quarter_data(data)
        assert len(latest_data) == 1
        assert latest_data.iloc[0]['季度'] == '2025年2季度股票投资明细'
        
        # 按范围过滤
        range_data = filter_by_quarter_range(
            data,
            start_year=2024,
            start_quarter=2,
            end_year=2024,
            end_quarter=4
        )
        assert len(range_data) == 3
        
        print("✓ 完整工作流程测试通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
