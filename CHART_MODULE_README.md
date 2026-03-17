# 技术指标图表展示模块文档

## 概述

`chart_module` 是一个功能完善的金融市场技术指标图表展示模块，支持多种图表类型、实时更新、交互操作、主题切换等功能。该模块基于 ECharts 图表库，提供高性能、响应式的数据可视化能力。

## 功能特性

### 1. 支持的图表类型

- **K线图 (Candlestick)**：展示股票价格走势，支持叠加技术指标
- **成交量图 (Volume)**：展示交易量变化
- **MACD图**：展示MACD指标（DIF、DEA、MACD柱状图）
- **RSI图**：展示相对强弱指数
- **KDJ图**：展示随机指标
- **折线图 (Line)**：通用折线图
- **柱状图 (Bar)**：通用柱状图
- **面积图 (Area)**：带填充区域的折线图
- **散点图 (Scatter)**：数据点分布图
- **饼图 (Pie)**：占比分布图
- **仪表盘 (Gauge)**：单值仪表盘
- **热力图 (Heatmap)**：数据密度热力图
- **雷达图 (Radar)**：多维度雷达图

### 2. 交互功能

- **悬停提示**：鼠标悬停显示详细数据
- **数据缩放**：支持拖拽缩放和时间范围选择
- **图例切换**：点击图例显示/隐藏对应数据系列
- **图表联动**：多图表联动显示
- **工具箱**：支持数据视图、还原、保存图片

### 3. 主题系统

- **浅色主题 (Light)**：适合日间使用
- **深色主题 (Dark)**：适合夜间使用
- **技术指标专用配色**：上涨红色、下跌绿色、中性灰色
- **自定义配色**：支持自定义颜色方案

### 4. 数据处理能力

- **数据重采样**：支持日、周、月等不同时间粒度
- **日期范围过滤**：按时间范围筛选数据
- **数据归一化**：支持MinMax和ZScore归一化
- **中英文列名支持**：自动识别中英文列名

### 5. 导出功能

- **HTML导出**：生成独立的HTML文件
- **JSON导出**：导出图表配置JSON
- **图片导出**：支持PNG/SVG格式（通过浏览器）

## 安装依赖

```bash
pip install pandas numpy loguru
```

## 快速开始

### 基本使用

```python
from chart_module import ChartDashboard, ChartConfig, Theme
from ak_fund import AkFund
from technical_indicators import TechnicalIndicators

# 获取股票数据
ak_fund = AkFund()
stock_data = ak_fund.get_stock_kline('600519', period='daily', 
                                    start_date='2023-01-01', 
                                    end_date='2023-12-31')

# 计算技术指标
ti = TechnicalIndicators(stock_data)
indicators = ti.calculate_all()

# 创建图表仪表盘
dashboard = ChartDashboard(ChartConfig(
    width=1200,
    height=600,
    theme=Theme.LIGHT,
    title="贵州茅台技术指标分析"
))

# 创建K线图
kline_id = dashboard.create_kline_chart(
    stock_data,
    indicators={
        'MA5': indicators['MA5'],
        'MA10': indicators['MA10'],
        'MA20': indicators['MA20']
    },
    title="K线图与移动平均线"
)

# 导出HTML
from chart_module import HTMLTemplateGenerator

charts = dashboard.get_all_charts()
html = HTMLTemplateGenerator.generate_dashboard_html(charts)

with open('technical_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("图表已导出到 technical_dashboard.html")
```

### 创建多个图表

```python
# 创建成交量图
volume_id = dashboard.create_volume_chart(stock_data)

# 创建MACD图
macd_id = dashboard.create_macd_chart(
    indicators['DIF'],
    indicators['DEA'],
    indicators['MACD'],
    stock_data['日期']
)

# 创建RSI图
rsi_id = dashboard.create_rsi_chart(
    {
        'RSI6': indicators['RSI6'],
        'RSI12': indicators['RSI12'],
        'RSI24': indicators['RSI24']
    },
    stock_data['日期']
)

# 创建KDJ图
kdj_id = dashboard.create_kdj_chart(
    indicators['K'],
    indicators['D'],
    indicators['J'],
    stock_data['日期']
)
```

## API文档

### ChartConfig 类

图表配置类，用于设置图表的基本参数。

```python
from chart_module import ChartConfig, Theme

config = ChartConfig(
    width=1200,              # 图表宽度（像素）
    height=600,              # 图表高度（像素）
    theme=Theme.LIGHT,       # 主题模式
    title="图表标题",        # 主标题
    subtitle="副标题",       # 副标题
    x_axis_label="X轴",      # X轴标签
    y_axis_label="Y轴",      # Y轴标签
    show_legend=True,        # 是否显示图例
    show_grid=True,          # 是否显示网格
    show_tooltip=True,       # 是否显示提示框
    enable_zoom=True,        # 是否启用缩放
    enable_brush=True,       # 是否启用框选
    animation_duration=300,  # 动画持续时间（毫秒）
    colors=['#5470c6', '#91cc75', ...]  # 自定义颜色
)
```

### ChartDashboard 类

图表仪表盘类，用于管理多个图表。

#### 初始化

```python
dashboard = ChartDashboard(config=ChartConfig())
```

#### 创建图表方法

**create_kline_chart**：创建K线图
```python
chart_id = dashboard.create_kline_chart(
    data=stock_data,           # OHLCV数据
    indicators={               # 技术指标（可选）
        'MA5': ma5_series,
        'MA10': ma10_series
    },
    title="K线图"              # 图表标题
)
```

**create_volume_chart**：创建成交量图
```python
chart_id = dashboard.create_volume_chart(
    data=stock_data,           # OHLCV数据
    title="成交量"             # 图表标题
)
```

**create_macd_chart**：创建MACD图
```python
chart_id = dashboard.create_macd_chart(
    dif=dif_series,            # DIF线
    dea=dea_series,            # DEA线
    macd=macd_series,          # MACD柱状图
    dates=date_series,         # 日期序列
    title="MACD"               # 图表标题
)
```

**create_rsi_chart**：创建RSI图
```python
chart_id = dashboard.create_rsi_chart(
    rsi_data={                 # RSI数据字典
        'RSI6': rsi6_series,
        'RSI12': rsi12_series
    },
    dates=date_series,         # 日期序列
    title="RSI"                # 图表标题
)
```

**create_kdj_chart**：创建KDJ图
```python
chart_id = dashboard.create_kdj_chart(
    k=k_series,                # K值
    d=d_series,                # D值
    j=j_series,                # J值
    dates=date_series,         # 日期序列
    title="KDJ"                # 图表标题
)
```

#### 图表管理方法

```python
# 获取图表配置
config = dashboard.get_chart_config(chart_id)

# 获取所有图表
all_charts = dashboard.get_all_charts()

# 移除图表
dashboard.remove_chart(chart_id)

# 导出图表
json_str = dashboard.export_chart(chart_id, format='json')
dict_config = dashboard.export_chart(chart_id, format='dict')

# 设置主题
dashboard.set_theme(Theme.DARK)
```

#### 自动更新

```python
# 注册更新回调函数
def on_update(chart_id, data):
    print(f"图表 {chart_id} 已更新")

dashboard.register_update_callback(on_update)

# 启动自动更新（每60秒）
dashboard.start_auto_update(interval=60)

# 停止自动更新
dashboard.stop_auto_update()

# 注销回调函数
dashboard.unregister_update_callback(on_update)
```

### DataProcessor 类

数据处理器类，提供数据处理功能。

```python
from chart_module import DataProcessor

# 数据重采样（日 -> 周）
weekly_data = DataProcessor.resample_data(daily_data, rule='W')

# 按日期范围过滤
filtered_data = DataProcessor.filter_by_date_range(
    data,
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31)
)

# 数据归一化
normalized = DataProcessor.normalize_data(data['close'], method='minmax')
standardized = DataProcessor.normalize_data(data['close'], method='zscore')
```

### HTMLTemplateGenerator 类

HTML模板生成器类，用于生成可独立运行的HTML文件。

```python
from chart_module import HTMLTemplateGenerator

# 生成单个图表HTML
chart_config = dashboard.get_chart_config(chart_id)
html = HTMLTemplateGenerator.generate_chart_html(
    chart_config,
    container_id="chart"
)

with open('chart.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 生成仪表盘HTML（多个图表）
all_charts = dashboard.get_all_charts()
html = HTMLTemplateGenerator.generate_dashboard_html(
    all_charts,
    title="技术指标仪表盘"
)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
```

## 图表类型详解

### K线图 (Candlestick)

K线图是股票技术分析的基础图表，展示开盘价、收盘价、最高价、最低价四个价格信息。

**特点：**
- 红色/绿色表示涨跌
- 实体表示开盘收盘价差
- 影线表示最高最低价
- 支持叠加移动平均线

**使用场景：**
- 股票价格走势分析
- 支撑阻力位识别
- 趋势判断

### 成交量图 (Volume)

成交量图展示交易量的变化情况。

**特点：**
- 柱状图形式展示
- 颜色与K线对应（红涨绿跌）
- 可与K线图联动

**使用场景：**
- 确认价格趋势
- 识别突破信号
- 判断市场活跃度

### MACD图

MACD（移动平均收敛发散指标）是趋势跟踪动量指标。

**组成：**
- DIF线：快线减慢线
- DEA线：DIF的移动平均
- MACD柱状图：(DIF - DEA) × 2

**使用场景：**
- 趋势判断
- 买卖信号（金叉死叉）
- 背离分析

### RSI图

RSI（相对强弱指数）是动量震荡指标。

**特点：**
- 范围0-100
- 70以上为超买区
- 30以下为超卖区

**使用场景：**
- 超买超卖判断
- 背离信号
- 趋势强度评估

### KDJ图

KDJ（随机指标）是动量震荡指标。

**组成：**
- K线：快速确认线
- D线：慢速主干线
- J线：方向敏感线

**使用场景：**
- 短期买卖点判断
- 超买超卖分析
- 趋势反转信号

## 主题系统

### 预定义主题

```python
from chart_module import Theme

# 浅色主题
dashboard.set_theme(Theme.LIGHT)

# 深色主题
dashboard.set_theme(Theme.DARK)
```

### 技术指标配色

```python
from chart_module import ChartTheme

theme = ChartTheme(Theme.LIGHT)

# 获取技术指标专用颜色
up_color = theme.get_technical_color('up')        # 上涨红色
down_color = theme.get_technical_color('down')    # 下跌绿色
ma5_color = theme.get_technical_color('ma5')      # 5日均线颜色
```

### 自定义配色

```python
config = ChartConfig(
    colors=['#ff0000', '#00ff00', '#0000ff', ...]
)
```

## 性能优化

### 大数据量处理

```python
# 1. 数据重采样减少数据点
large_data = DataProcessor.resample_data(minute_data, rule='H')  # 小时线

# 2. 限制显示范围
filtered_data = DataProcessor.filter_by_date_range(
    data,
    start_date=datetime.now() - timedelta(days=365)  # 最近一年
)

# 3. 使用性能模式
config = ChartConfig(
    animation_duration=0,  # 禁用动画
    show_tooltip=False     # 禁用提示框
)
```

### 多图表优化

```python
# 批量创建图表
dashboard = ChartDashboard(config)

# 使用延迟加载
for symbol in symbols:
    data = load_data(symbol)
    dashboard.create_kline_chart(data)
    
# 一次性导出所有图表
all_charts = dashboard.get_all_charts()
html = HTMLTemplateGenerator.generate_dashboard_html(all_charts)
```

## 错误处理

### 常见错误

```python
from chart_module import ChartDashboard, ChartConfig

try:
    dashboard = ChartDashboard(config)
    chart_id = dashboard.create_kline_chart(data)
except ValueError as e:
    print(f"数据验证错误: {e}")
except KeyError as e:
    print(f"缺少必要列: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 数据验证

```python
# 验证数据格式
if data.empty:
    raise ValueError("数据不能为空")

required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
if not all(col in data.columns for col in required_cols):
    raise ValueError(f"数据必须包含以下列: {required_cols}")
```

## 最佳实践

### 1. 数据准备

```python
# 确保数据质量
data = data.dropna()  # 删除空值
data = data.sort_values('date')  # 按日期排序
```

### 2. 图表布局

```python
# 创建多个相关图表
kline_id = dashboard.create_kline_chart(price_data)
volume_id = dashboard.create_volume_chart(price_data)
macd_id = dashboard.create_macd_chart(dif, dea, macd, dates)

# 统一主题
dashboard.set_theme(Theme.DARK)
```

### 3. 响应式设计

```python
# 使用相对尺寸
config = ChartConfig(
    width=0,   # 自动宽度
    height=400 # 固定高度
)
```

### 4. 定期更新

```python
# 设置自动更新
dashboard.start_auto_update(interval=300)  # 每5分钟

# 在回调中更新数据
def update_data(chart_id, data):
    new_data = fetch_latest_data()
    dashboard.update_chart(chart_id, new_data)

dashboard.register_update_callback(update_data)
```

## 示例代码

### 完整示例：股票技术分析仪表盘

```python
import pandas as pd
from datetime import datetime, timedelta
from ak_fund import AkFund
from technical_indicators import TechnicalIndicators
from chart_module import (
    ChartDashboard, ChartConfig, Theme,
    HTMLTemplateGenerator, DataProcessor
)

def create_technical_analysis_dashboard(symbol='600519'):
    """创建股票技术分析仪表盘"""
    
    # 1. 获取数据
    ak_fund = AkFund()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    stock_data = ak_fund.get_stock_kline(
        symbol,
        period='daily',
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    # 2. 计算技术指标
    ti = TechnicalIndicators(stock_data)
    indicators = ti.calculate_all()
    
    # 3. 创建仪表盘
    config = ChartConfig(
        width=1200,
        height=400,
        theme=Theme.LIGHT,
        title=f"{symbol} 技术分析"
    )
    dashboard = ChartDashboard(config)
    
    # 4. 创建图表
    # K线图
    kline_id = dashboard.create_kline_chart(
        stock_data,
        indicators={
            'MA5': indicators['MA5'],
            'MA10': indicators['MA10'],
            'MA20': indicators['MA20'],
            'MA60': indicators['MA60']
        },
        title="K线图与移动平均线"
    )
    
    # 成交量图
    volume_id = dashboard.create_volume_chart(stock_data)
    
    # MACD图
    macd_id = dashboard.create_macd_chart(
        indicators['DIF'],
        indicators['DEA'],
        indicators['MACD'],
        stock_data['日期']
    )
    
    # RSI图
    rsi_id = dashboard.create_rsi_chart(
        {
            'RSI6': indicators['RSI6'],
            'RSI12': indicators['RSI12'],
            'RSI24': indicators['RSI24']
        },
        stock_data['日期']
    )
    
    # KDJ图
    kdj_id = dashboard.create_kdj_chart(
        indicators['K'],
        indicators['D'],
        indicators['J'],
        stock_data['日期']
    )
    
    # 5. 导出HTML
    all_charts = dashboard.get_all_charts()
    html = HTMLTemplateGenerator.generate_dashboard_html(
        all_charts,
        title=f"{symbol} 技术分析仪表盘"
    )
    
    output_file = f'{symbol}_technical_analysis.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"仪表盘已导出到: {output_file}")
    return dashboard

if __name__ == "__main__":
    dashboard = create_technical_analysis_dashboard('600519')
```

## 测试

运行单元测试：

```bash
python -m pytest test_chart_module.py -v
```

测试覆盖：
- 图表配置测试
- 数据类测试
- 主题系统测试
- 数据处理器测试
- 图表渲染器测试
- 仪表盘功能测试
- HTML生成器测试
- 性能测试
- 集成测试

## 许可证

MIT License

## 更新日志

### v1.0.0 (2026-03-15)
- 初始版本发布
- 支持10种图表类型
- 实现技术指标专用图表
- 添加主题系统
- 支持数据处理和导出
- 完整的单元测试

## 联系方式

如有问题或建议，请提交Issue或Pull Request。
