"""
综合信号判断模块
基于多种技术指标评估股票买卖信号
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class SignalLevel(Enum):
    """信号等级枚举"""
    STRONG_BUY = "强烈买入"      # 综合得分 >= 0.6
    BUY = "买入"                # 0.2 <= 得分 < 0.6
    HOLD = "持有"               # -0.2 < 得分 < 0.2
    SELL = "卖出"               # -0.6 < 得分 <= -0.2
    STRONG_SELL = "强烈卖出"    # 得分 <= -0.6


@dataclass
class Signal:
    """单个信号数据类"""
    indicator: str              # 指标名称
    signal_type: str            # 信号类型（buy/sell/neutral）
    strength: float             # 信号强度（0-1）
    description: str            # 信号描述
    value: Any = None           # 指标值
    threshold: Any = None       # 阈值


@dataclass
class SignalResult:
    """信号判断结果数据类"""
    date: Any                  # 日期
    overall_score: float       # 综合得分（-1到1）
    signal_level: SignalLevel  # 信号等级
    signals: List[Signal]      # 所有信号列表
    confidence: float          # 置信度（0-1）
    recommendation: str        # 建议
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息


class SignalJudger:
    """
    综合信号判断器
    
    基于多种技术指标（RSI、MACD、KDJ、布林带、均线等）评估股票买卖信号
    提供综合评分和交易建议
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        初始化信号判断器
        
        Args:
            data: 包含技术指标的DataFrame，应包含至少以下列：
                  收盘价（close）、技术指标列（RSI、MACD、KDJ等）
        """
        self._validate_data(data)
        self.data = data.copy()
        self.signals_history = []
    
    def _validate_data(self, data: pd.DataFrame) -> None:
        """验证输入数据"""
        if not isinstance(data, pd.DataFrame):
            raise ValueError("输入数据必须是pandas DataFrame")
        
        if data.empty:
            raise ValueError("输入数据不能为空")
        
        # 检查必要列（支持中英文）
        required_cols = ['close', '收盘']
        has_required = any(col in data.columns for col in required_cols)
        if not has_required:
            raise ValueError("数据必须包含收盘价列（close或收盘）")
    
    def _get_column(self, col_name: str) -> Optional[pd.Series]:
        """获取列数据（支持中英文）"""
        if col_name in self.data.columns:
            return self.data[col_name]
        
        col_mapping = {
            'close': '收盘',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'volume': '成交量'
        }
        
        if col_name in col_mapping and col_mapping[col_name] in self.data.columns:
            return self.data[col_mapping[col_name]]
        
        return None
    
    def _calculate_signal_strength(self, value: float, threshold: float, 
                                 range_val: float) -> float:
        """
        计算信号强度
        
        Args:
            value: 当前值
            threshold: 阈值
            range_val: 参考范围（用于标准化）
            
        Returns:
            0-1之间的强度值
        """
        diff = abs(value - threshold)
        strength = min(diff / max(range_val, 0.01), 1.0)
        return strength
    
    def check_rsi_signal(self, period: int = 14) -> Signal:
        """
        检查RSI信号
        
        逻辑：
        - RSI < 30：超卖，可能买入机会（买入信号）
        - RSI > 70：超买，可能卖出信号（卖出信号）
        - 30-70：中性（无信号）
        
        Args:
            period: RSI周期
            
        Returns:
            Signal对象
        """
        rsi_col = f'RSI{period}'
        rsi = self._get_column(rsi_col)
        
        if rsi is None:
            logger.warning(f"未找到RSI列: {rsi_col}")
            return Signal(
                indicator='RSI',
                signal_type='neutral',
                strength=0.0,
                description='缺少RSI数据'
            )
        
        # 获取最新值
        latest_rsi = rsi.iloc[-1] if not rsi.empty else 0
        
        # 判断信号
        if latest_rsi < 30:
            signal_type = 'buy'
            strength = self._calculate_signal_strength(latest_rsi, 30, 30)
            description = f"RSI({period})超卖 ({latest_rsi:.1f} < 30)"
        elif latest_rsi > 70:
            signal_type = 'sell'
            strength = self._calculate_signal_strength(latest_rsi, 70, 30)
            description = f"RSI({period})超买 ({latest_rsi:.1f} > 70)"
        else:
            signal_type = 'neutral'
            strength = 0.0
            description = f"RSI({period})中性 ({latest_rsi:.1f})"
        
        return Signal(
            indicator='RSI',
            signal_type=signal_type,
            strength=strength,
            description=description,
            value=latest_rsi,
            threshold={'oversold': 30, 'overbought': 70}
        )
    
    def check_macd_signal(self, config: str = '12-26-9') -> Signal:
        """
        检查MACD信号
        
        逻辑：
        - DIF上穿DEA：金叉，买入信号
        - DIF下穿DEA：死叉，卖出信号
        
        Args:
            config: MACD配置，格式"快-慢-信号"
            
        Returns:
            Signal对象
        """
        dif_col = f'DIF{config}'
        dea_col = f'DEA{config}'
        macd_col = f'MACD{config}'
        
        dif = self._get_column(dif_col)
        dea = self._get_column(dea_col)
        
        if dif is None or dea is None:
            logger.warning(f"未找到MACD列: {dif_col}, {dea_col}")
            return Signal(
                indicator='MACD',
                signal_type='neutral',
                strength=0.0,
                description='缺少MACD数据'
            )
        
        if len(dif) < 2 or len(dea) < 2:
            return Signal(
                indicator='MACD',
                signal_type='neutral',
                strength=0.0,
                description='数据不足'
            )
        
        # 计算交叉
        dif_values = dif.values
        dea_values = dea.values
        
        # 最新两天的差值
        diff_current = dif_values[-1] - dea_values[-1]
        diff_prev = dif_values[-2] - dea_values[-2]
        
        if diff_prev <= 0 and diff_current > 0:
            signal_type = 'buy'
            strength = self._calculate_signal_strength(diff_current, 0, abs(diff_current) + 0.01)
            description = f"MACD({config})金叉"
        elif diff_prev >= 0 and diff_current < 0:
            signal_type = 'sell'
            strength = self._calculate_signal_strength(diff_current, 0, abs(diff_current) + 0.01)
            description = f"MACD({config})死叉"
        else:
            signal_type = 'neutral'
            strength = 0.0
            description = f"MACD({config})无交叉"
        
        return Signal(
            indicator='MACD',
            signal_type=signal_type,
            strength=strength,
            description=description,
            value={'DIF': dif_values[-1], 'DEA': dea_values[-1]},
            threshold='cross'
        )
    
    def check_kdj_signal(self, config: str = '9-3-3') -> Signal:
        """
        检查KDJ信号
        
        逻辑：
        - K上穿D：金叉，买入信号
        - K下穿D：死叉，卖出信号
        - J > 80：超买警惕
        - J < 20：超卖警惕
        
        Args:
            config: KDJ配置，格式"K-D-J"
            
        Returns:
            Signal对象
        """
        k_col = f'K{config}'
        d_col = f'D{config}'
        j_col = f'J{config}'
        
        k = self._get_column(k_col)
        d = self._get_column(d_col)
        j = self._get_column(j_col)
        
        if k is None or d is None:
            logger.warning(f"未找到KDJ列: {k_col}, {d_col}")
            return Signal(
                indicator='KDJ',
                signal_type='neutral',
                strength=0.0,
                description='缺少KDJ数据'
            )
        
        if len(k) < 2 or len(d) < 2:
            return Signal(
                indicator='KDJ',
                signal_type='neutral',
                strength=0.0,
                description='数据不足'
            )
        
        # 计算K、D交叉
        k_values = k.values
        d_values = d.values
        
        diff_current = k_values[-1] - d_values[-1]
        diff_prev = k_values[-2] - d_values[-2]
        
        signal_type = 'neutral'
        strength = 0.0
        description = 'KDJ无交叉'
        
        # 检查交叉
        if diff_prev <= 0 and diff_current > 0:
            signal_type = 'buy'
            strength = self._calculate_signal_strength(diff_current, 0, abs(diff_current) + 0.01)
            description = f"KDJ({config})金叉"
        elif diff_prev >= 0 and diff_current < 0:
            signal_type = 'sell'
            strength = self._calculate_signal_strength(diff_current, 0, abs(diff_current) + 0.01)
            description = f"KDJ({config})死叉"
        
        # 检查J值超买/超卖（作为附加信息）
        if j is not None and not j.empty:
            latest_j = j.iloc[-1]
            if latest_j > 80:
                description += f"；J值超买 ({latest_j:.1f} > 80)"
            elif latest_j < 20:
                description += f"；J值超卖 ({latest_j:.1f} < 20)"
        
        return Signal(
            indicator='KDJ',
            signal_type=signal_type,
            strength=strength,
            description=description,
            value={'K': k_values[-1], 'D': d_values[-1], 'J': j.iloc[-1] if j is not None else None},
            threshold='cross'
        )
    
    def check_boll_signal(self, config: str = '20-2') -> Signal:
        """
        检查布林带信号
        
        逻辑：
        - 价格突破上轨：可能超买，警惕回调（卖出信号）
        - 价格突破下轨：可能超卖，可能有反弹（买入信号）
        - 价格在中轨上方：偏强
        - 价格在中轨下方：偏弱
        
        Args:
            config: 布林带配置，格式"周期-标准差倍数"
            
        Returns:
            Signal对象
        """
        upper_col = f'BOLL_UPPER{config}'
        middle_col = f'BOLL_MIDDLE{config}'
        lower_col = f'BOLL_LOWER{config}'
        
        upper = self._get_column(upper_col)
        middle = self._get_column(middle_col)
        lower = self._get_column(lower_col)
        close = self._get_column('close')
        
        if any(x is None for x in [upper, middle, lower, close]):
            logger.warning(f"未找到布林带列")
            return Signal(
                indicator='BOLL',
                signal_type='neutral',
                strength=0.0,
                description='缺少布林带数据'
            )
        
        if close.empty:
            return Signal(
                indicator='BOLL',
                signal_type='neutral',
                strength=0.0,
                description='数据不足'
            )
        
        latest_close = close.iloc[-1]
        latest_upper = upper.iloc[-1]
        latest_lower = lower.iloc[-1]
        latest_middle = middle.iloc[-1]
        
        signal_type = 'neutral'
        strength = 0.0
        description = '布林带无特殊信号'
        
        if latest_close > latest_upper:
            signal_type = 'sell'
            strength = self._calculate_signal_strength(latest_close, latest_upper, latest_upper - latest_middle)
            description = f"BOLL({config})价格突破上轨"
        elif latest_close < latest_lower:
            signal_type = 'buy'
            strength = self._calculate_signal_strength(latest_close, latest_lower, latest_middle - latest_lower)
            description = f"BOLL({config})价格突破下轨"
        else:
            # 价格在通道内，判断相对位置
            position = (latest_close - latest_lower) / (latest_upper - latest_lower + 0.01)
            if position > 0.7:
                description = f"BOLL({config})价格接近上轨（偏强）"
            elif position < 0.3:
                description = f"BOLL({config})价格接近下轨（偏弱）"
            else:
                description = f"BOLL({config})价格在通道中部"
        
        return Signal(
            indicator='BOLL',
            signal_type=signal_type,
            strength=strength,
            description=description,
            value={'close': latest_close, 'upper': latest_upper, 'middle': latest_middle, 'lower': latest_lower},
            threshold={'upper': '突破', 'lower': '突破'}
        )
    
    def check_ma_signal(self, periods: List[int] = [5, 10, 20, 30, 60]) -> Signal:
        """
        检查多均线系统信号
        
        逻辑：
        - 多头排列：短周期均线 > 长周期均线，买入信号
        - 空头排列：短周期均线 < 长周期均线，卖出信号
        - 价格与均线关系
        
        Args:
            periods: 均线周期列表
            
        Returns:
            Signal对象
        """
        close = self._get_column('close')
        if close is None:
            return Signal(
                indicator='MA',
                signal_type='neutral',
                strength=0.0,
                description='缺少价格数据'
            )
        
        latest_close = close.iloc[-1] if not close.empty else 0
        
        # 获取各周期均线
        ma_values = []
        available_periods = []
        
        for period in periods:
            ma_col = f'MA{period}'
            ma = self._get_column(ma_col)
            if ma is not None and not ma.empty:
                latest_ma = ma.iloc[-1]
                ma_values.append(latest_ma)
                available_periods.append(period)
        
        if len(ma_values) < 2:
            return Signal(
                indicator='MA',
                signal_type='neutral',
                strength=0.0,
                description='均线数据不足'
            )
        
        # 判断多头/空头排列
        # 将均线按周期从小到大的顺序排列
        sorted_pairs = sorted(zip(available_periods, ma_values))
        
        all_bullish = True
        all_bearish = True
        
        for i in range(len(sorted_pairs) - 1):
            if sorted_pairs[i][1] >= sorted_pairs[i+1][1]:
                all_bullish = False
            if sorted_pairs[i][1] <= sorted_pairs[i+1][1]:
                all_bearish = False
        
        signal_type = 'neutral'
        strength = 0.0
        description = '均线系统无明确信号'
        
        if all_bullish:
            signal_type = 'buy'
            strength = 0.6  # 均线排列通常是比较强的信号
            description = f"均线多头排列（{' < '.join([str(p) for p, _ in sorted_pairs])}）"
        elif all_bearish:
            signal_type = 'sell'
            strength = 0.6
            description = f"均线空头排列（{' > '.join([str(p) for p, _ in sorted_pairs])}）"
        else:
            # 检查价格与关键均线的关系
            ma20 = None
            for period, ma_val in sorted_pairs:
                if period == 20:
                    ma20 = ma_val
                    break
            
            if ma20 is not None:
                if latest_close > ma20:
                    description += f"；价格在MA20上方（偏强）"
                else:
                    description += f"；价格在MA20下方（偏弱）"
        
        return Signal(
            indicator='MA',
            signal_type=signal_type,
            strength=strength,
            description=description,
            value={'close': latest_close, 'ma_values': dict(sorted_pairs)},
            threshold='排列'
        )
    
    def check_volume_signal(self, period: int = 20) -> Signal:
        """
        检查成交量信号
        
        逻辑：
        - 放量上涨：买入信号
        - 放量下跌：卖出信号
        - 缩量震荡：观望
        
        Args:
            period: 比较周期
            
        Returns:
            Signal对象
        """
        volume = self._get_column('volume')
        close = self._get_column('close')
        
        if volume is None or close is None:
            return Signal(
                indicator='VOLUME',
                signal_type='neutral',
                strength=0.0,
                description='缺少成交量或价格数据'
            )
        
        if len(volume) < period + 1 or len(close) < 2:
            return Signal(
                indicator='VOLUME',
                signal_type='neutral',
                strength=0.0,
                description='数据不足'
            )
        
        latest_volume = volume.iloc[-1]
        prev_volume = volume.iloc[-2]
        avg_volume = volume.iloc[-period:].mean()
        
        latest_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        price_change = (latest_close - prev_close) / prev_close * 100
        
        volume_ratio = latest_volume / (avg_volume + 1)
        is_volume_increase = latest_volume > avg_volume * 1.2
        
        signal_type = 'neutral'
        strength = 0.0
        description = '成交量无特殊信号'
        
        if is_volume_increase and price_change > 0:
            signal_type = 'buy'
            strength = min(volume_ratio / 2, 1.0)
            description = f"放量上涨（量比:{volume_ratio:.1f}, 涨幅:{price_change:.1f}%）"
        elif is_volume_increase and price_change < 0:
            signal_type = 'sell'
            strength = min(volume_ratio / 2, 1.0)
            description = f"放量下跌（量比:{volume_ratio:.1f}, 跌幅:{abs(price_change):.1f}%）"
        
        return Signal(
            indicator='VOLUME',
            signal_type=signal_type,
            strength=strength,
            description=description,
            value={'latest_volume': latest_volume, 'avg_volume': avg_volume, 'price_change': price_change},
            threshold='1.2x'
        )
    
    def calculate_overall_score(self, signals: List[Signal]) -> Tuple[float, Dict[str, float]]:
        """
        计算综合得分
        
        权重分配：
        - RSI: 15%     （超买超卖）
        - MACD: 25%    （趋势转折）
        - KDJ: 20%     （随机指标）
        - BOLL: 15%    （通道突破）
        - MA: 20%      （均线系统）
        - VOLUME: 5%   （成交量确认）
        
        Args:
            signals: 信号列表
            
        Returns:
            (综合得分, 各指标得分字典)
        """
        weights = {
            'RSI': 0.15,
            'MACD': 0.25,
            'KDJ': 0.20,
            'BOLL': 0.15,
            'MA': 0.20,
            'VOLUME': 0.05
        }
        
        indicator_scores = {}
        
        for signal in signals:
            indicator = signal.indicator
            weight = weights.get(indicator, 0.0)
            
            if signal.signal_type == 'buy':
                score = signal.strength * weight
            elif signal.signal_type == 'sell':
                score = -signal.strength * weight
            else:
                score = 0.0
            
            indicator_scores[indicator] = score
        
        overall_score = sum(indicator_scores.values())
        
        return overall_score, indicator_scores
    
    def get_signals(self, date: Any = None) -> SignalResult:
        """
        获取所有信号并生成综合判断
        
        Args:
            date: 分析日期，默认使用最新数据
            
        Returns:
            SignalResult对象
        """
        # 如果指定了日期，筛选数据（这里简化处理，默认使用最后一行为最新）
        if date is not None:
            logger.warning("指定日期功能待实现，默认使用最新数据")
        
        # 收集所有信号
        signals = []
        
        # RSI信号（多种周期）
        for period in [6, 12, 24]:
            rsi_signal = self.check_rsi_signal(period)
            if rsi_signal.strength > 0:  # 只记录有效信号
                signals.append(rsi_signal)
        
        # MACD信号（所有配置）
        for config in ['12-26-9', '12-26-12']:
            macd_signal = self.check_macd_signal(config)
            if macd_signal.strength > 0:
                signals.append(macd_signal)
        
        # KDJ信号（所有配置）
        for config in ['9-3-3', '10-3-3']:
            kdj_signal = self.check_kdj_signal(config)
            if kdj_signal.strength > 0:
                signals.append(kdj_signal)
        
        # 布林带信号
        boll_signal = self.check_boll_signal('20-2')
        signals.append(boll_signal)
        
        # 均线系统信号
        ma_signal = self.check_ma_signal([5, 10, 20, 30, 60])
        signals.append(ma_signal)
        
        # 成交量信号
        volume_signal = self.check_volume_signal(20)
        signals.append(volume_signal)
        
        # 计算综合得分
        overall_score, indicator_scores = self.calculate_overall_score(signals)
        
        # 确定信号等级
        if overall_score >= 0.6:
            signal_level = SignalLevel.STRONG_BUY
        elif overall_score >= 0.2:
            signal_level = SignalLevel.BUY
        elif overall_score > -0.2:
            signal_level = SignalLevel.HOLD
        elif overall_score > -0.6:
            signal_level = SignalLevel.SELL
        else:
            signal_level = SignalLevel.STRONG_SELL
        
        # 计算置信度（基于有效信号数量）
        effective_signals = [s for s in signals if s.strength > 0]
        confidence = min(len(effective_signals) / 6.0, 1.0)  # 归一化到0-1
        
        # 生成建议
        if signal_level == SignalLevel.STRONG_BUY:
            recommendation = "强烈建议买入，多项指标显示强势买点"
        elif signal_level == SignalLevel.BUY:
            recommendation = "建议买入，多数指标向好"
        elif signal_level == SignalLevel.HOLD:
            recommendation = "建议持有观望，等待明确信号"
        elif signal_level == SignalLevel.SELL:
            recommendation = "建议卖出，部分指标走弱"
        else:
            recommendation = "强烈建议卖出，多项指标显示危险信号"
        
        # 构建详细信息
        latest_date = self._get_column('date')
        date_value = latest_date.iloc[-1] if latest_date is not None and not latest_date.empty else None
        
        details = {
            'overall_score': overall_score,
            'indicator_scores': indicator_scores,
            'total_signals': len(signals),
            'effective_signals': len(effective_signals),
            'date': date_value
        }
        
        result = SignalResult(
            date=date_value,
            overall_score=overall_score,
            signal_level=signal_level,
            signals=signals,
            confidence=confidence,
            recommendation=recommendation,
            details=details
        )
        
        # 记录历史
        self.signals_history.append(result)
        
        return result
    
    def get_signal_summary(self, result: SignalResult) -> pd.DataFrame:
        """
        生成信号摘要表格
        
        Args:
            result: SignalResult对象
            
        Returns:
            摘要DataFrame
        """
        summary_data = []
        
        for signal in result.signals:
            summary_data.append({
                '指标': signal.indicator,
                '信号类型': signal.signal_type,
                '强度': f"{signal.strength:.1%}",
                '描述': signal.description,
                '当前值': str(signal.value) if signal.value is not None else '-'
            })
        
        summary_df = pd.DataFrame(summary_data)
        return summary_df


# 示例使用
if __name__ == "__main__":
    # 测试数据
    from technical_indicators import TechnicalIndicators
    from ak_fund import AkFund
    
    # 获取股票数据并计算技术指标
    ak_fund = AkFund()
    stock_data = ak_fund.get_stock_kline('600519', period='daily', 
                                         start_date='2023-01-01', end_date='2023-12-31')
    
    if not stock_data.empty:
        # 计算技术指标
        ti = TechnicalIndicators(stock_data)
        indicators_df = ti.calculate_all()
        
        # 合并原始数据和技术指标
        combined_df = pd.concat([stock_data.reset_index(drop=True), indicators_df], axis=1)
        
        # 创建信号判断器
        judger = SignalJudger(combined_df)
        
        # 获取信号
        signal_result = judger.get_signals()
        
        # 打印结果
        print("=" * 60)
        print("综合信号判断结果")
        print("=" * 60)
        print(f"日期: {signal_result.date}")
        print(f"综合得分: {signal_result.overall_score:.3f}")
        print(f"信号等级: {signal_result.signal_level.value}")
        print(f"置信度: {signal_result.confidence:.1%}")
        print(f"建议: {signal_result.recommendation}")
        print("\n详细信号:")
        print("-" * 60)
        
        summary_df = judger.get_signal_summary(signal_result)
        print(summary_df.to_string(index=False))
        
        print("\n各指标得分:")
        for indicator, score in signal_result.details['indicator_scores'].items():
            print(f"  {indicator}: {score:+.3f}")
    else:
        print("未能获取股票数据")