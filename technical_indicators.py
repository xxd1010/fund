from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


class TechnicalIndicators:
    """
    技术指标计算类
    
    提供多种常用技术指标的计算功能，包括移动平均线、RSI、KDJ、布林带、MACD等
    支持自定义参数，具有完善的错误处理机制
    """

    def __init__(self, data: pd.DataFrame):
        """
        初始化技术指标计算器
        
        Args:
            data: 包含OHLCV数据的DataFrame，必须包含以下列：
                  - 日期 (date)
                  - 开盘价 (open)
                  - 最高价 (high)
                  - 最低价 (low)
                  - 收盘价 (close)
                  - 成交量 (volume)
        """
        self._validate_data(data)
        self.data = data.copy()
        self.indicators = {}
        self.period_kdj = [9, 3, 3]
        self.period_ma = [5, 10, 20, 30, 60, 120, 250]
        self.period_ema = [12, 26]
        self.period_rsi = [6, 12, 24]

    def _validate_data(self, data: pd.DataFrame) -> None:
        """
        验证输入数据的完整性
        
        Args:

            data: 待验证的数据
            
        Raises:
            ValueError: 数据格式不正确或缺少必要列
        """
        if not isinstance(data, pd.DataFrame):
            raise ValueError("输入数据必须是pandas DataFrame")

        if data.empty:
            raise ValueError("输入数据不能为空")

        # 检查必要的列（支持中英文列名）
        required_cols_en = ['date', 'open', 'high', 'low', 'close', 'volume']
        required_cols_cn = ['日期', '开盘', '最高', '最低', '收盘', '成交量']

        has_en = all(col in data.columns for col in required_cols_en)
        has_cn = all(col in data.columns for col in required_cols_cn)

        if not (has_en or has_cn):
            raise ValueError(f"数据必须包含以下列之一：\n"
                             f"英文：{required_cols_en}\n"
                             f"中文：{required_cols_cn}")

        # 检查数据类型
        for col in data.columns:
            if col in ['open', 'high', 'low', 'close', 'volume', '开盘', '最高',
                       '最低', '收盘', '成交量']:
                if not pd.api.types.is_numeric_dtype(data[col]):
                    raise ValueError(f"列 '{col}' 必须是数值类型")

    def _get_column(self, col_name: str) -> pd.Series:
        """
        获取指定列的数据（支持中英文列名）
        
        Args:
            col_name: 列名（英文）
            
        Returns:
            对应列的数据
        """
        col_mapping = {
            'date': '日期',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'close': '收盘',
            'volume': '成交量'
        }

        if col_name in self.data.columns:
            return self.data[col_name]
        elif col_name in col_mapping and col_mapping[
            col_name] in self.data.columns:
            return self.data[col_mapping[col_name]]
        else:
            raise ValueError(
                f"找不到列 '{col_name}' 或 '{col_mapping.get(col_name, '')}'")

    def calculate_ma(self, period: int = 20,
                     column: str = 'close') -> pd.Series:
        """
        计算移动平均线 (Moving Average)
        
        计算公式：MA = (P1 + P2 + ... + Pn) / n
        其中P为价格，n为周期
        
        Args:
            period: 计算周期，默认20日
            column: 计算列名，默认收盘价
            
        Returns:
            移动平均线序列
        """
        if period <= 0:
            raise ValueError("周期必须大于0")

        data = self._get_column(column)
        ma = data.rolling(window=period).mean()

        logger.info(f"计算 {period} 日移动平均线完成")
        return ma

    def calculate_ema(self, period: int = 12,
                      column: str = 'close') -> pd.Series:
        """
        计算指数移动平均线 (Exponential Moving Average)
        
        计算公式：
        EMA今日 = (收盘价今日 × 平滑系数) + (EMA昨日 × (1 - 平滑系数))
        平滑系数 = 2 / (周期 + 1)
        
        Args:
            period: 计算周期，默认12日
            column: 计算列名，默认收盘价
            
        Returns:
            指数移动平均线序列
        """
        if period <= 0:
            raise ValueError("周期必须大于0")

        data = self._get_column(column)
        ema = data.ewm(span=period, adjust=False).mean()

        logger.info(f"计算 {period} 日指数移动平均线完成")
        return ema

    def calculate_rsi(self, period: int = 14,
                      column: str = 'close') -> pd.Series:
        """
        计算相对强弱指数 (Relative Strength Index)
        
        计算公式：
        RSI = 100 - (100 / (1 + RS))
        RS = 平均涨幅 / 平均跌幅
        
        Args:
            period: 计算周期，默认14日
            column: 计算列名，默认收盘价
            
        Returns:
            RSI序列，范围0-100
        """
        if period <= 0:
            raise ValueError("周期必须大于0")

        data = self._get_column(column)

        # 计算价格变化
        delta = data.diff()

        # 分离涨幅和跌幅
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 计算平均涨幅和平均跌幅
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # 计算RS和RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        logger.info(f"计算 {period} 日RSI完成")
        return rsi

    def calculate_macd(self, fast_period: int = 12, slow_period: int = 26,
                       signal_period: int = 9,
                       column: str = 'close') -> Tuple[
        pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标 (Moving Average Convergence Divergence)
        
        计算公式：
        DIF = EMA(快线) - EMA(慢线)
        DEA = EMA(DIF)
        MACD = (DIF - DEA) × 2
        
        Args:
            fast_period: 快线周期，默认12日
            slow_period: 慢线周期，默认26日
            signal_period: 信号线周期，默认9日
            column: 计算列名，默认收盘价
            
        Returns:
            (DIF, DEA, MACD) 元组
        """
        if fast_period >= slow_period:
            raise ValueError("快线周期必须小于慢线周期")

        data = self._get_column(column)

        # 计算快线和慢线EMA
        ema_fast = data.ewm(span=fast_period, adjust=False).mean()
        ema_slow = data.ewm(span=slow_period, adjust=False).mean()

        # 计算DIF
        dif = ema_fast - ema_slow

        # 计算DEA（信号线）
        dea = dif.ewm(span=signal_period, adjust=False).mean()

        # 计算MACD柱状图
        macd = (dif - dea) * 2

        logger.info(
            f"计算MACD完成：快线={fast_period}, 慢线={slow_period}, 信号线={signal_period}")
        return dif, dea, macd

    def calculate_boll(self, period: int = 20, std_dev: float = 2.0,
                       column: str = 'close') -> Tuple[
        pd.Series, pd.Series, pd.Series]:
        """
        计算布林带 (Bollinger Bands)
        
        计算公式：
        中轨 = MA(周期)
        上轨 = 中轨 + (标准差 × 倍数)
        下轨 = 中轨 - (标准差 × 倍数)
        
        Args:
            period: 计算周期，默认20日
            std_dev: 标准差倍数，默认2.0
            column: 计算列名，默认收盘价
            
        Returns:
            (上轨, 中轨, 下轨) 元组
        """
        if period <= 0:
            raise ValueError("周期必须大于0")
        if std_dev <= 0:
            raise ValueError("标准差倍数必须大于0")

        data = self._get_column(column)

        # 计算中轨（移动平均线）
        middle = data.rolling(window=period).mean()

        # 计算标准差
        std = data.rolling(window=period).std()

        # 计算上轨和下轨
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        logger.info(f"计算布林带完成：周期={period}, 标准差倍数={std_dev}")
        return upper, middle, lower

    def calculate_kdj(self, k_period: int = 9, d_period: int = 3,
                      j_period: int = 3) -> Tuple[
        pd.Series, pd.Series, pd.Series]:
        """
        计算KDJ指标 (随机指标)
        
        计算公式：
        RSV = (收盘价 - 最低价) / (最高价 - 最低价) × 100
        K = SMA(RSV, 周期K)
        D = SMA(K, 周期D)
        J = 3K - 2D
        
        Args:
            k_period: K值计算周期，默认9日
            d_period: D值计算周期，默认3日
            j_period: J值计算周期，默认3日
            
        Returns:
            (K, D, J) 元组
        """
        if self.period_kdj is None:
            self.period_kdj = [k_period, d_period, j_period]
        k_period, d_period, j_period = self.period_kdj
        if k_period <= 0 or d_period <= 0 or j_period <= 0:
            raise ValueError("周期必须大于0")

        high = self._get_column('high')
        low = self._get_column('low')
        close = self._get_column('close')

        # 计算最高价和最低价的滚动窗口
        high_n = high.rolling(window=k_period).max()
        low_n = low.rolling(window=k_period).min()

        # 计算RSV
        rsv = (close - low_n) / (high_n - low_n) * 100

        # 计算K值（简单移动平均）
        k = rsv.ewm(com=d_period - 1, adjust=False).mean()

        # 计算D值
        d = k.ewm(com=j_period - 1, adjust=False).mean()

        # 计算J值
        j = 3 * k - 2 * d

        logger.info(
            f"计算KDJ完成：K周期={k_period}, D周期={d_period}, J周期={j_period}")
        return k, d, j

    def calculate_atr(self, period: int = 14) -> pd.Series:
        """
        计算平均真实波幅 (Average True Range)
        
        计算公式：
        TR = max(最高价-最低价, |最高价-昨收|, |最低价-昨收|)
        ATR = MA(TR, 周期)
        
        Args:
            period: 计算周期，默认14日
            
        Returns:
            ATR序列
        """
        if period <= 0:
            raise ValueError("周期必须大于0")

        high = self._get_column('high')
        low = self._get_column('low')
        close = self._get_column('close')

        # 计算真实波幅TR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 计算ATR（使用RMA方法）
        atr = tr.ewm(span=period, adjust=False).mean()

        logger.info(f"计算 {period} 日ATR完成")
        return atr

    def calculate_obv(self) -> pd.Series:
        """
        计算能量潮指标 (On Balance Volume)
        
        计算公式：
        OBV = 前日OBV + (当日成交量 × sign(当日收盘价 - 前日收盘价))
        
        Returns:
            OBV序列
        """
        close = self._get_column('close')
        volume = self._get_column('volume')

        # 计算价格变化方向
        price_change = close.diff()

        # 计算OBV
        obv = (volume * np.sign(price_change)).fillna(0).cumsum()

        logger.info("计算OBV完成")
        return obv

    def calculate_cci(self, period: int = 20) -> pd.Series:
        """
        计算顺势指标 (Commodity Channel Index)
        
        计算公式：
        TP = (最高价 + 最低价 + 收盘价) / 3
        MA_TP = MA(TP, 周期)
        MD = MA(|TP - MA_TP|, 周期)
        CCI = (TP - MA_TP) / (0.015 × MD)
        
        Args:
            period: 计算周期，默认20日
            
        Returns:
            CCI序列
        """
        if period <= 0:
            raise ValueError("周期必须大于0")

        high = self._get_column('high')
        low = self._get_column('low')
        close = self._get_column('close')

        # 计算典型价格
        tp = (high + low + close) / 3

        # 计算典型价格的移动平均
        ma_tp = tp.rolling(window=period).mean()

        # 计算平均绝对偏差
        mad = tp.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean())

        # 计算CCI
        cci = (tp - ma_tp) / (0.015 * mad)

        logger.info(f"计算 {period} 日CCI完成")
        return cci

    def calculate_williams_r(self, period: int = 14) -> pd.Series:
        """
        计算威廉指标 (Williams %R)
        
        计算公式：
        %R = (最高价 - 收盘价) / (最高价 - 最低价) × -100
        
        Args:
            period: 计算周期，默认14日
            
        Returns:
            威廉指标序列，范围-100到0
        """
        if period <= 0:
            raise ValueError("周期必须大于0")

        high = self._get_column('high')
        low = self._get_column('low')
        close = self._get_column('close')

        # 计算周期内的最高价和最低价
        high_n = high.rolling(window=period).max()
        low_n = low.rolling(window=period).min()

        # 计算威廉指标
        williams_r = (high_n - close) / (high_n - low_n) * -100

        logger.info(f"计算 {period} 日威廉指标完成")
        return williams_r

    def calculate_all(self,
                      indicators: Optional[List[str]] = None) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            indicators: 要计算的指标列表，None表示计算所有指标
                      可选值：['ma', 'ema', 'rsi', 'macd', 'boll', 'kdj', 'atr', 'obv', 'cci', 'williams_r']
            
        Returns:
            包含所有计算指标的DataFrame
        """
        if indicators is None:
            indicators = ['ma', 'ema', 'rsi', 'macd', 'boll', 'kdj', 'atr',
                          'obv', 'cci', 'williams_r']

        result = pd.DataFrame()

        for indicator in indicators:
            try:
                if indicator == 'ma':
                    for period in self.period_ma:
                        result[f'MA{period}'] = self.calculate_ma(period)
                elif indicator == 'ema':
                    for period in self.period_ema:
                        result[f'EMA{period}'] = self.calculate_ema(period)
                elif indicator == 'rsi':
                    for period in self.period_rsi:
                        result[f'RSI{period}'] = self.calculate_rsi(period)
                elif indicator == 'macd':
                    dif, dea, macd = self.calculate_macd()
                    result['DIF'] = dif
                    result['DEA'] = dea
                    result['MACD'] = macd
                elif indicator == 'boll':
                    upper, middle, lower = self.calculate_boll()
                    result['BOLL_UPPER'] = upper
                    result['BOLL_MIDDLE'] = middle
                    result['BOLL_LOWER'] = lower
                elif indicator == 'kdj':
                    k, d, j = self.calculate_kdj()
                    result['K'] = k
                    result['D'] = d
                    result['J'] = j
                elif indicator == 'atr':
                    result['ATR'] = self.calculate_atr()
                elif indicator == 'obv':
                    result['OBV'] = self.calculate_obv()
                elif indicator == 'cci':
                    result['CCI'] = self.calculate_cci()
                elif indicator == 'williams_r':
                    result['Williams_R'] = self.calculate_williams_r()
                else:
                    logger.warning(f"未知的指标类型: {indicator}")
            except Exception as e:
                logger.error(f"计算指标 {indicator} 时出错: {e}")

        logger.info(f"完成计算 {len(result.columns)} 个技术指标")
        return result


if __name__ == "__main__":
    # 示例用法
    from ak_fund import AkFund

    # 获取股票数据
    ak_fund = AkFund()
    stock_data = ak_fund.get_stock_kline('600519', period='daily',
                                         start_date='2023-01-01',
                                         end_date='2023-12-31')

    # 计算技术指标
    ti = TechnicalIndicators(stock_data)

    # 计算单个指标
    print("=== 单个指标示例 ===")
    ma20 = ti.calculate_ma(20)
    print(f"20日移动平均线（最后5个值）:\n{ma20.tail()}\n")

    rsi = ti.calculate_rsi(14)
    print(f"14日RSI（最后5个值）:\n{rsi.tail()}\n")

    # 计算所有指标
    print("=== 所有指标 ===")
    all_indicators = ti.calculate_all()
    print(f"计算了 {len(all_indicators.columns)} 个指标")
    print("\n指标列表：")
    for col in all_indicators.columns:
        print(f"  - {col}")

    print(f"\n数据形状: {all_indicators.shape}")
    print(f"\n最后5行数据:")
    print(all_indicators.tail())
