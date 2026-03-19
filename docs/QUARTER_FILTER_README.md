# 季度数据过滤模块

## 概述

`quarter_filter` 模块提供了从DataFrame中过滤最新季度数据的专业功能，支持多种季度格式解析，具备完善的边缘情况处理能力。

## 主要功能

### 1. 最新季度数据过滤
- 自动识别DataFrame中的最新季度
- 支持同一季度的多个条目
- 保持原始数据结构和列顺序

### 2. 多种季度格式支持
支持以下格式：
- `YYYY年Q季度股票投资明细` (例如: "2025年1季度股票投资明细")
- `YYYY年Q季度` (例如: "2025年Q1")
- `YYYY-Q季度` (例如: "2025-Q1")
- `YYYYQ季度` (例如: "2025Q1")
- `YYYY年X季度` (中文数字，例如: "2025年一季度")

### 3. 季度范围过滤
- 按指定的季度范围过滤数据
- 支持跨年范围查询
- 灵活的起始和结束参数设置

### 4. 季度摘要分析
- 统计数据覆盖的季度数量
- 识别最新季度
- 显示各季度的数据分布

## 核心特性

### ✅ 智能解析
- 使用正则表达式解析多种季度格式
- 自动处理中文数字季度
- 容错能力强，跳过无效格式

### ✅ 准确比较
- 年份优先于季度的比较逻辑
- 正确处理不同年份相同季度的情况
- 确保最新季度的准确识别

### ✅ 边缘情况处理
- 空DataFrame处理
- 缺少季度列处理
- 无效格式跳过
- 同一季度的多个条目保留
- None值处理

### ✅ 数据完整性
- 保持原始数据结构
- 保持原始列顺序
- 不修改原始DataFrame
- 返回新的DataFrame对象

## 安装依赖

```bash
pip install pandas numpy loguru
```

## 快速开始

### 基本用法

```python
import pandas as pd
from quarter_filter import filter_latest_quarter_data

# 创建示例数据
data = pd.DataFrame({
    '季度': [
        '2024年1季度股票投资明细',
        '2024年2季度股票投资明细',
        '2025年1季度股票投资明细',
        '2025年2季度股票投资明细',
    ],
    '股票代码': ['600519', '000001', '600519', '000001'],
    '股票名称': ['贵州茅台', '平安银行', '贵州茅台', '平安银行'],
    '投资金额': [100000, 200000, 120000, 250000],
})

# 过滤最新季度数据
latest_data = filter_latest_quarter_data(data)
print(latest_data)
```

### 获取季度摘要

```python
from quarter_filter import get_quarter_summary

# 获取季度摘要
summary = get_quarter_summary(data)

print(f"总行数: {summary['total_rows']}")
print(f"唯一季度数: {summary['unique_quarters']}")
print(f"最新季度: {summary['latest_quarter'][0]}年Q{summary['latest_quarter'][1]}")
print("季度分布:")
for quarter, count in summary['quarter_distribution'].items():
    print(f"  {quarter}: {count}条")
```

### 按季度范围过滤

```python
from quarter_filter import filter_by_quarter_range

# 过滤2024年Q2到2024年Q4的数据
range_data = filter_by_quarter_range(
    data,
    start_year=2024,
    start_quarter=2,
    end_year=2024,
    end_quarter=4
)

# 过滤跨年范围（2024年Q3到2025年Q1）
cross_year_data = filter_by_quarter_range(
    data,
    start_year=2024,
    start_quarter=3,
    end_year=2025,
    end_quarter=1
)
```

## API文档

### filter_latest_quarter_data

从DataFrame中过滤出最新季度的数据。

**参数:**
- `df` (pd.DataFrame): 输入的DataFrame，必须包含指定的季度列
- `quarter_column` (str): 季度列名，默认为'季度'

**返回:**
- `pd.DataFrame`: 只包含最新季度数据的DataFrame，保持原始数据结构和列顺序

**异常:**
- `ValueError`: 当季度列不存在或数据为空时
- `ValueError`: 当季度列格式无法解析时

**示例:**
```python
latest_data = filter_latest_quarter_data(data, quarter_column='季度')
```

### get_quarter_summary

获取DataFrame中季度数据的摘要信息。

**参数:**
- `df` (pd.DataFrame): 输入的DataFrame
- `quarter_column` (str): 季度列名，默认为'季度'

**返回:**
- `dict`: 包含季度摘要的字典
  - `total_rows`: 总行数
  - `unique_quarters`: 唯一季度的数量
  - `latest_quarter`: 最新季度信息 (year, quarter)
  - `quarter_distribution`: 各季度的数据分布

**示例:**
```python
summary = get_quarter_summary(data)
print(summary)
```

### filter_by_quarter_range

按季度范围过滤数据。

**参数:**
- `df` (pd.DataFrame): 输入的DataFrame
- `start_year` (int): 起始年份
- `start_quarter` (int): 起始季度 (1-4)
- `end_year` (int, optional): 结束年份（默认为起始年份）
- `end_quarter` (int, optional): 结束季度（默认为起始季度）
- `quarter_column` (str): 季度列名，默认为'季度'

**返回:**
- `pd.DataFrame`: 过滤后的DataFrame

**异常:**
- `ValueError`: 当季度值无效时

**示例:**
```python
# 单个季度
data_q1 = filter_by_quarter_range(data, 2025, 1)

# 季度范围
data_range = filter_by_quarter_range(data, 2024, 2, 2024, 4)

# 跨年范围
data_cross_year = filter_by_quarter_range(data, 2024, 3, 2025, 1)
```

### parse_quarter_string

解析季度字符串，提取年份和季度信息。

**参数:**
- `quarter_str` (str): 季度字符串

**返回:**
- `Tuple[int, int]`: (年份, 季度) 元组

**异常:**
- `ValueError`: 当字符串格式无法解析时
- `AttributeError`: 当输入不是字符串时

**示例:**
```python
from quarter_filter import parse_quarter_string

year, quarter = parse_quarter_string("2025年1季度股票投资明细")
print(f"年份: {year}, 季度: {quarter}")  # 输出: 年份: 2025, 季度: 1
```

## 使用场景

### 1. 基金持仓分析
```python
# 获取基金最新季度的持仓数据
latest_holdings = filter_latest_quarter_data(fund_holdings)
total_value = latest_holdings['持仓市值'].sum()
print(f"最新季度总持仓市值: ¥{total_value:,.2f}")
```

### 2. 财务报表分析
```python
# 获取公司最新季度的财务数据
latest_financial = filter_latest_quarter_data(financial_reports)
revenue = latest_financial['营业收入'].sum()
print(f"最新季度营业收入: ¥{revenue:,.2f}")
```

### 3. 股票投资明细
```python
# 获取最新季度的股票投资明细
latest_investments = filter_latest_quarter_data(stock_investments)
print(latest_investments)
```

### 4. 历史数据对比
```python
# 获取2024年全年的数据
full_year_data = filter_by_quarter_range(
    data,
    start_year=2024,
    start_quarter=1,
    end_year=2024,
    end_quarter=4
)

# 与最新季度对比
latest_data = filter_latest_quarter_data(data)
```

## 测试

运行单元测试：

```bash
python -m pytest test_quarter_filter.py -v
```

运行演示程序：

```bash
python quarter_filter_demo.py
```

## 性能特点

- **高效解析**: 使用正则表达式快速解析季度字符串
- **内存优化**: 避免不必要的数据复制
- **批量处理**: 支持大规模DataFrame处理
- **快速过滤**: 使用Pandas向量化操作

## 注意事项

1. **季度列名**: 默认使用'季度'作为季度列名，可以通过`quarter_column`参数自定义
2. **格式要求**: 季度字符串必须包含年份和季度信息，否则会被跳过
3. **数据完整性**: 函数会跳过无法解析的季度格式，确保只处理有效数据
4. **原始数据**: 函数不会修改原始DataFrame，返回新的DataFrame对象

## 错误处理

模块包含完善的错误处理机制：

- **空DataFrame**: 抛出ValueError异常
- **缺少季度列**: 抛出ValueError异常
- **无效季度值**: 抛出ValueError异常
- **无效格式**: 记录警告日志并跳过
- **None值**: 记录警告日志并跳过

## 日志记录

模块使用loguru记录日志：

- `INFO`: 识别到最新季度、过滤结果等关键信息
- `WARNING`: 无法解析的季度格式、非字符串类型等警告信息

## 版本历史

### v1.0.0 (2025-03-15)
- 初始版本发布
- 支持多种季度格式解析
- 实现最新季度数据过滤
- 添加季度范围过滤功能
- 完善边缘情况处理
- 提供完整的单元测试

## 许可证

MIT License

## 贡献

欢迎提交问题和拉取请求！

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件

---

**注意**: 本模块专为处理中文季度格式设计，如需支持其他语言的季度格式，请修改`parse_quarter_string`函数中的正则表达式模式。
