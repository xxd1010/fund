# 技术指标计算模块文档

## 概述

`TechnicalIndicators` 类是一个功能完善的金融市场技术指标计算模块，支持计算10种主流技术指标。该模块具有以下特点：

- 支持10种常用技术指标的计算
- 灵活的参数配置
- 完善的错误处理机制
- 支持中英文列名
- 模块化设计，易于扩展
- 详细的日志记录

## 安装依赖

```bash
pip install pandas numpy loguru
```

## 快速开始

### 基本使用

```python
from technical_indicators import TechnicalIndicators
import pandas as pd

# 准备数据（必须包含OHLCV列）
data = pd.DataFrame({
    'date': ['2023-01-01', '2023-01-02', '2023-01-03'],
    'open': [100, 101, 102],
    'high': [105, 106, 107],
    'low': [99, 100, 101],
    'close': [104, 105, 106],
    'volume': [1000000, 1100000, 1200000]
})

# 创建技术指标计算器
ti = TechnicalIndicators(data)

# 计算单个指标
ma20 = ti.calculate_ma(period=20)
rsi = ti.calculate_rsi(period=14)

# 计算所有指标
all_indicators = ti.calculate_all()
```

### 与ak_fund模块结合使用

```python
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

# 保存结果
result = pd.concat([stock_data, indicators], axis=1)
ak_fund.save_data(result, 'stock_with_indicators', 'csv')
```

## 数据格式要求

### 必需列

输入数据必须包含以下列之一（支持中英文）：

| 英文列名 | 中文列名 | 说明     |
| -------- | -------- | -------- |
| date     | 日期     | 交易日期 |
| open     | 开盘     | 开盘价   |
| high     | 最高     | 最高价   |
| low      | 最低     | 最低价   |
| close    | 收盘     | 收盘价   |
| volume   | 成交量   | 成交量   |

### 数据类型

- 日期列：datetime类型或可转换为datetime的字符串
- 价格列：数值类型（float或int）
- 成交量列：数值类型（float或int）

## 技术指标详解

### 1. 移动平均线 (MA)

#### 计算公式

```
MA = (P1 + P2 + ... + Pn) / n
```

其中P为价格，n为周期

#### 参数说明

- `period`: 计算周期，默认20日
- `column`: 计算列名，默认收盘价

#### 使用示例

```python
# 计算5日、10日、20日、60日移动平均线
ma5 = ti.calculate_ma(period=5)
ma10 = ti.calculate_ma(period=10)
ma20 = ti.calculate_ma(period=20)
ma60 = ti.calculate_ma(period=60)
```

#### 应用场景

- 趋势判断：价格在MA上方为上涨趋势，下方为下跌趋势
- 支撑阻力：MA作为动态支撑位或阻力位
- 交叉信号：短期MA上穿长期MA为买入信号

### 2. 指数移动平均线 (EMA)

#### 计算公式

```
EMA今日 = (收盘价今日 × 平滑系数) + (EMA昨日 × (1 - 平滑系数))
平滑系数 = 2 / (周期 + 1)
```

#### 参数说明

- `period`: 计算周期，默认12日
- `column`: 计算列名，默认收盘价

#### 使用示例

```python
# 计算12日和26日EMA（用于MACD计算）
ema12 = ti.calculate_ema(period=12)
ema26 = ti.calculate_ema(period=26)
```

#### 应用场景

- MACD指标的基础计算
- 更敏感的趋势跟踪
- 与MA结合使用

### 3. 相对强弱指数 (RSI)

#### 计算公式

```
RSI = 100 - (100 / (1 + RS))
RS = 平均涨幅 / 平均跌幅
```

#### 参数说明

- `period`: 计算周期，默认14日
- `column`: 计算列名，默认收盘价

#### 使用示例

```python
# 计算6日、12日、24日RSI
rsi6 = ti.calculate_rsi(period=6)
rsi12 = ti.calculate_rsi(period=12)
rsi24 = ti.calculate_rsi(period=24)
```

#### 应用场景

- 超买超卖判断：RSI > 70为超买，RSI < 30为超卖
- 背离信号：价格创新高但RSI未创新高
- 趋势确认：RSI在50以上为强势，以下为弱势

### 4. MACD指标

#### 计算公式

```
DIF = EMA(快线) - EMA(慢线)
DEA = EMA(DIF)
MACD = (DIF - DEA) × 2
```

#### 参数说明

- `fast_period`: 快线周期，默认12日
- `slow_period`: 慢线周期，默认26日
- `signal_period`: 信号线周期，默认9日
- `column`: 计算列名，默认收盘价

#### 使用示例

```python
# 计算MACD
dif, dea, macd = ti.calculate_macd(
    fast_period=12,
    slow_period=26,
    signal_period=9
)
```

#### 应用场景

- 金叉死叉：DIF上穿DEA为金叉（买入），下穿为死叉（卖出）
- 零轴判断：MACD在零轴上方为多头市场，下方为空头市场
- 柱状图变化：柱状图由负转正为买入信号

### 5. 布林带 (BOLL)

#### 计算公式

```
中轨 = MA(周期)
上轨 = 中轨 + (标准差 × 倍数)
下轨 = 中轨 - (标准差 × 倍数)
```

#### 参数说明

- `period`: 计算周期，默认20日
- `std_dev`: 标准差倍数，默认2.0
- `column`: 计算列名，默认收盘价

#### 使用示例

```python
# 计算布林带
upper, middle, lower = ti.calculate_boll(
    period=20,
    std_dev=2.0
)
```

#### 应用场景

- 波动率判断：带宽变窄预示即将突破
- 超买超卖：价格触及上轨为超买，触及下轨为超卖
- 趋势判断：价格在中轨上方为上涨趋势

### 6. KDJ指标

#### 计算公式

```
RSV = (收盘价 - 最低价) / (最高价 - 最低价) × 100
K = SMA(RSV, 周期K)
D = SMA(K, 周期D)
J = 3K - 2D
```

#### 参数说明

- `k_period`: K值计算周期，默认9日
- `d_period`: D值计算周期，默认3日
- `j_period`: J值计算周期，默认3日

#### 使用示例

```python
# 计算KDJ
k, d, j = ti.calculate_kdj(
    k_period=9,
    d_period=3,
    j_period=3
)
```

#### 应用场景

- 超买超卖：K、D值大于80为超买，小于20为超卖
- 交叉信号：K上穿D为买入信号，下穿为卖出信号
- J值预警：J值大于100或小于0为极端行情

### 7. 平均真实波幅 (ATR)

#### 计算公式

```
TR = max(最高价-最低价, |最高价-昨收|, |最低价-昨收|)
ATR = MA(TR, 周期)
```

#### 参数说明

- `period`: 计算周期，默认14日

#### 使用示例

```python
# 计算14日ATR
atr = ti.calculate_atr(period=14)
```

#### 应用场景

- 波动率测量：ATR值越大，波动越剧烈
- 止损设置：根据ATR设置动态止损位
- 仓位管理：根据ATR调整仓位大小

### 8. 能量潮指标 (OBV)

#### 计算公式

```
OBV = 前日OBV + (当日成交量 × sign(当日收盘价 - 前日收盘价))
```

#### 参数说明

- 无参数

#### 使用示例

```python
# 计算OBV
obv = ti.calculate_obv()
```

#### 应用场景

- 资金流向：OBV上涨表示资金流入
- 背离信号：价格创新高但OBV未创新高
- 趋势确认：OBV与价格同向运动确认趋势

### 9. 顺势指标 (CCI)

#### 计算公式

```
TP = (最高价 + 最低价 + 收盘价) / 3
MA_TP = MA(TP, 周期)
MD = MA(|TP - MA_TP|, 周期)
CCI = (TP - MA_TP) / (0.015 × MD)
```

#### 参数说明

- `period`: 计算周期，默认20日

#### 使用示例

```python
# 计算20日CCI
cci = ti.calculate_cci(period=20)
```

#### 应用场景

- 超买超卖：CCI > 100为超买，CCI < -100为超卖
- 趋势判断：CCI在0轴上方为多头市场
- 买卖信号：CCI从超买区回落为卖出信号

### 10. 威廉指标 (Williams %R)

#### 计算公式

```
%R = (最高价 - 收盘价) / (最高价 - 最低价) × -100
```

#### 参数说明

- `period`: 计算周期，默认14日

#### 使用示例

```python
# 计算14日威廉指标
williams_r = ti.calculate_williams_r(period=14)
```

#### 应用场景

- 超买超卖：%R > -20为超买，%R < -80为超卖
- 背离信号：价格创新高但%R未创新高
- 趋势反转：%R从超买区回落为卖出信号

## 批量计算

### 计算所有指标

```python
# 计算所有可用指标
all_indicators = ti.calculate_all()
```

### 选择性计算

```python
# 只计算特定指标
selected_indicators = ti.calculate_all(
    indicators=['ma', 'rsi', 'macd', 'boll']
)
```

### 可用指标列表

- `ma`: 移动平均线（5、10、20、60日）
- `ema`: 指数移动平均线（12、26日）
- `rsi`: 相对强弱指数（6、12、24日）
- `macd`: MACD指标
- `boll`: 布林带
- `kdj`: KDJ指标
- `atr`: 平均真实波幅
- `obv`: 能量潮指标
- `cci`: 顺势指标
- `williams_r`: 威廉指标

## 错误处理

### 数据验证

模块会自动验证输入数据，常见错误包括：

```python
# 空数据
TechnicalIndicators(pd.DataFrame())  # ValueError: 输入数据不能为空

# 缺少必要列
TechnicalIndicators(pd.DataFrame({'date': [1, 2, 3]}))  # ValueError: 数据必须包含以下列

# 错误的数据类型
data['close'] = ['100', '200', '300']  # ValueError: 列 'close' 必须是数值类型
```

### 参数验证

```python
# 无效的周期参数
ti.calculate_ma(0)  # ValueError: 周期必须大于0
ti.calculate_ma(-5)  # ValueError: 周期必须大于0

# MACD参数错误
ti.calculate_macd(fast_period=26, slow_period=12)  # ValueError: 快线周期必须小于慢线周期
```

## 性能优化建议

1. **批量计算**：使用`calculate_all()`方法一次性计算多个指标，减少重复计算
2. **合理设置周期**：避免过长的计算周期，影响性能
3. **数据预处理**：确保数据质量，避免NaN值过多
4. **缓存结果**：对不变的数据缓存计算结果

## 扩展开发

### 添加新指标

```python
class TechnicalIndicators:
    def calculate_new_indicator(self, period: int = 14) -> pd.Series:
        """
        计算新指标

        Args:
            period: 计算周期

        Returns:
            新指标序列
        """
        if period <= 0:
            raise ValueError("周期必须大于0")

        # 实现指标计算逻辑
        data = self._get_column('close')
        result = data.rolling(window=period).mean()

        logger.info(f"计算新指标完成")
        return result
```

### 自定义参数

所有指标方法都支持自定义参数，可以根据实际需求调整：

```python
# 自定义RSI周期
custom_rsi = ti.calculate_rsi(period=21)

# 自定义布林带参数
custom_boll = ti.calculate_boll(period=15, std_dev=1.5)
```

## 测试

运行单元测试：

```bash
python -m pytest test_technical_indicators.py -v
```

测试覆盖：

- 数据验证
- 单个指标计算
- 批量指标计算
- 参数验证
- 边界情况
- 中英文列名支持

## 常见问题

### Q: 为什么计算结果中有NaN值？

A: 这是正常现象。由于滚动窗口计算，前N-1个值（N为周期）会是NaN。例如，20日移动平均线的前19个值都是NaN。

### Q: 如何处理NaN值？

A: 可以使用以下方法：

```python
# 删除NaN值
result = result.dropna()

# 填充NaN值
result = result.fillna(method='ffill')  # 前向填充
result = result.fillna(method='bfill')  # 后向填充
```

### Q: 支持哪些数据源？

A: 任何包含OHLCV数据的DataFrame都可以，不限制数据源。可以与akshare、tushare、baostock等数据源配合使用。

### Q: 如何提高计算效率？

A:

1. 使用`calculate_all()`批量计算
2. 合理设置周期长度
3. 避免重复计算
4. 使用向量化操作

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue或Pull Request。
