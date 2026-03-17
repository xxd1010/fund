"""
金叉/死叉技术信号分析模块
提供专业的金融市场技术信号识别和分析功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta
from loguru import logger
import time


class GoldenCrossAnalyzer:
    """
    金叉/死叉分析器
    
    提供基于移动平均线的金叉/死叉识别、有效性评估、多时间周期分析和历史回测功能
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        初始化金叉/死叉分析器
        
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
        self.signals = {}
        self.performance = {}
    
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
            if col in ['open', 'high', 'low', 'close', 'volume', '开盘', '最高', '最低', '收盘', '成交量']:
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
        elif col_name in col_mapping and col_mapping[col_name] in self.data.columns:
            return self.data[col_mapping[col_name]]
        else:
            raise ValueError(f"找不到列 '{col_name}' 或 '{col_mapping.get(col_name, '')}'")
    
    def _calculate_ma(self, period: int) -> pd.Series:
        """
        计算移动平均线
        
        Args:
            period: 计算周期
            
        Returns:
            移动平均线序列
        """
        close = self._get_column('close')
        return close.rolling(window=period).mean()
    
    def identify_golden_cross(self, short_period: int = 5, long_period: int = 20) -> pd.DataFrame:
        """
        识别金叉信号
        
        金叉定义：短期均线从下方向上穿越长期均线
        
        Args:
            short_period: 短期均线周期，默认5日
            long_period: 长期均线周期，默认20日
            
        Returns:
            包含金叉信号的DataFrame，包含以下列：
            - date: 日期
            - price: 收盘价
            - short_ma: 短期均线
            - long_ma: 长期均线
            - signal: 信号类型（1表示金叉，0表示无信号）
            - strength: 信号强度（0-1）
        """
        start_time = time.time()
        
        if short_period >= long_period:
            raise ValueError("短期均线周期必须小于长期均线周期")
        
        # 计算移动平均线
        short_ma = self._calculate_ma(short_period)
        long_ma = self._calculate_ma(long_period)
        
        # 计算均线差值
        ma_diff = short_ma - long_ma
        
        # 识别金叉：前一天差值为负，当天差值为正
        golden_cross = (ma_diff > 0) & (ma_diff.shift(1) <= 0)
        
        # 计算信号强度（基于交叉角度）
        signal_strength = self._calculate_signal_strength(ma_diff, golden_cross)
        
        # 构建结果DataFrame
        result = pd.DataFrame({
            'date': self._get_column('date'),
            'price': self._get_column('close'),
            'short_ma': short_ma,
            'long_ma': long_ma,
            'signal': golden_cross.astype(int),
            'strength': signal_strength
        })
        
        # 只保留有信号的记录
        result = result[result['signal'] == 1].copy()
        
        # 计算信号出现后的价格走势
        if not result.empty:
            result = self._analyze_post_signal_price_movement(result)
        
        execution_time = (time.time() - start_time) * 1000
        logger.info(f"金叉识别完成，共识别 {len(result)} 个信号，耗时 {execution_time:.2f}ms")
        
        self.signals['golden_cross'] = result
        return result
    
    def identify_death_cross(self, short_period: int = 5, long_period: int = 20) -> pd.DataFrame:
        """
        识别死叉信号
        
        死叉定义：短期均线从上方向下穿越长期均线
        
        Args:
            short_period: 短期均线周期，默认5日
            long_period: 长期均线周期，默认20日
            
        Returns:
            包含死叉信号的DataFrame，包含以下列：
            - date: 日期
            - price: 收盘价
            - short_ma: 短期均线
            - long_ma: 长期均线
            - signal: 信号类型（-1表示死叉，0表示无信号）
            - strength: 信号强度（0-1）
        """
        start_time = time.time()
        
        if short_period >= long_period:
            raise ValueError("短期均线周期必须小于长期均线周期")
        
        # 计算移动平均线
        short_ma = self._calculate_ma(short_period)
        long_ma = self._calculate_ma(long_period)
        
        # 计算均线差值
        ma_diff = short_ma - long_ma
        
        # 识别死叉：前一天差值为正，当天差值为负
        death_cross = (ma_diff < 0) & (ma_diff.shift(1) >= 0)
        
        # 计算信号强度（基于交叉角度）
        signal_strength = self._calculate_signal_strength(ma_diff, death_cross)
        
        # 构建结果DataFrame
        result = pd.DataFrame({
            'date': self._get_column('date'),
            'price': self._get_column('close'),
            'short_ma': short_ma,
            'long_ma': long_ma,
            'signal': -death_cross.astype(int),
            'strength': signal_strength
        })
        
        # 只保留有信号的记录
        result = result[result['signal'] == -1].copy()
        
        # 计算信号出现后的价格走势
        if not result.empty:
            result = self._analyze_post_signal_price_movement(result)
        
        execution_time = (time.time() - start_time) * 1000
        logger.info(f"死叉识别完成，共识别 {len(result)} 个信号，耗时 {execution_time:.2f}ms")
        
        self.signals['death_cross'] = result
        return result
    
    def _calculate_signal_strength(self, ma_diff: pd.Series, signal: pd.Series) -> pd.Series:
        """
        计算信号强度
        
        基于均线交叉的角度和速度计算信号强度
        
        Args:
            ma_diff: 均线差值序列
            signal: 信号序列
            
        Returns:
            信号强度序列（0-1）
        """
        strength = pd.Series(0.0, index=ma_diff.index)
        
        # 计算差值的变化率
        diff_change = ma_diff.diff()
        
        # 在信号点计算强度
        signal_points = signal[signal].index
        for point in signal_points:
            # 使用交叉前后的变化率计算强度
            if point > 0:
                prev_diff = ma_diff.iloc[point - 1]
                curr_diff = ma_diff.iloc[point]
                change = diff_change.iloc[point]
                
                # 强度基于差值的变化幅度
                strength.iloc[point] = min(abs(change) / (abs(prev_diff) + 0.01), 1.0)
        
        return strength
    
    def _analyze_post_signal_price_movement(self, signals_df: pd.DataFrame, 
                                         look_ahead: int = 5) -> pd.DataFrame:
        """
        分析信号出现后的价格走势
        
        Args:
            signals_df: 信号DataFrame
            look_ahead: 向前查看的天数
            
        Returns:
            添加了价格走势分析的DataFrame
        """
        close = self._get_column('close')
        high = self._get_column('high')
        low = self._get_column('low')
        volume = self._get_column('volume')
        
        # 创建日期到索引的映射
        date_to_idx = {date: idx for idx, date in enumerate(self._get_column('date'))}
        
        # 分析每个信号
        price_changes = []
        volume_changes = []
        
        for idx, row in signals_df.iterrows():
            signal_date = row['date']
            signal_idx = date_to_idx.get(signal_date)
            
            if signal_idx is None:
                price_changes.append([0] * look_ahead)
                volume_changes.append([0] * look_ahead)
                continue
            
            # 计算未来几天的价格变化
            price_change = []
            volume_change = []
            
            for day in range(1, look_ahead + 1):
                if signal_idx + day < len(close):
                    future_price = close.iloc[signal_idx + day]
                    current_price = close.iloc[signal_idx]
                    price_change.append((future_price - current_price) / current_price * 100)
                    
                    # 计算成交量变化
                    future_volume = volume.iloc[signal_idx + day]
                    current_volume = volume.iloc[signal_idx]
                    volume_change.append((future_volume - current_volume) / current_volume * 100)
                else:
                    price_change.append(0)
                    volume_change.append(0)
            
            price_changes.append(price_change)
            volume_changes.append(volume_change)
        
        signals_df['price_change_5d'] = [changes[0] if changes else 0 for changes in price_changes]
        signals_df['volume_change_5d'] = [changes[0] if changes else 0 for changes in volume_changes]
        
        return signals_df
    
    def evaluate_signal_validity(self, signals_df: pd.DataFrame, 
                               min_volume_increase: float = 20.0) -> pd.DataFrame:
        """
        评估信号有效性
        
        基于价格走势和成交量配合情况评估信号有效性
        
        Args:
            signals_df: 信号DataFrame
            min_volume_increase: 最小成交量增长百分比
            
        Returns:
            添加了有效性评估的DataFrame
        """
        if signals_df.empty:
            return signals_df
        
        # 评估价格走势
        signals_df['price_valid'] = signals_df['price_change_5d'].apply(
            lambda x: 1 if x > 0 else -1 if x < 0 else 0
        )
        
        # 评估成交量配合
        signals_df['volume_valid'] = signals_df['volume_change_5d'].apply(
            lambda x: 1 if x > min_volume_increase else 0
        )
        
        # 综合有效性评分
        signals_df['validity_score'] = (
            signals_df['price_valid'] * 0.6 + 
            signals_df['volume_valid'] * 0.4
        )
        
        # 信号等级
        signals_df['signal_level'] = pd.cut(
            signals_df['validity_score'],
            bins=[-float('inf'), -0.5, 0.5, 1.5],
            labels=['无效', '一般', '有效']
        )
        
        return signals_df
    
    def multi_timeframe_analysis(self, daily_data: Optional[pd.DataFrame] = None,
                                weekly_data: Optional[pd.DataFrame] = None,
                                monthly_data: Optional[pd.DataFrame] = None,
                                short_period: int = 5,
                                long_period: int = 20) -> Dict[str, pd.DataFrame]:
        """
        多时间周期信号对比分析
        
        Args:
            daily_data: 日线数据
            weekly_data: 周线数据
            monthly_data: 月线数据
            short_period: 短期均线周期
            long_period: 长期均线周期
            
        Returns:
            包含各时间周期信号的字典
        """
        results = {}
        
        # 日线分析
        if daily_data is not None:
            daily_analyzer = GoldenCrossAnalyzer(daily_data)
            results['daily'] = {
                'golden_cross': daily_analyzer.identify_golden_cross(short_period, long_period),
                'death_cross': daily_analyzer.identify_death_cross(short_period, long_period)
            }
        
        # 周线分析
        if weekly_data is not None:
            weekly_analyzer = GoldenCrossAnalyzer(weekly_data)
            results['weekly'] = {
                'golden_cross': weekly_analyzer.identify_golden_cross(short_period, long_period),
                'death_cross': weekly_analyzer.identify_death_cross(short_period, long_period)
            }
        
        # 月线分析
        if monthly_data is not None:
            monthly_analyzer = GoldenCrossAnalyzer(monthly_data)
            results['monthly'] = {
                'golden_cross': monthly_analyzer.identify_golden_cross(short_period, long_period),
                'death_cross': monthly_analyzer.identify_death_cross(short_period, long_period)
            }
        
        return results
    
    def backtest_signals(self, short_period: int = 5, long_period: int = 20,
                       holding_period: int = 10, 
                       stop_loss: float = -5.0,
                       take_profit: float = 10.0) -> Dict[str, Union[float, pd.DataFrame]]:
        """
        信号历史回测
        
        统计不同市场环境下金叉/死叉信号的准确率和盈亏比
        
        Args:
            short_period: 短期均线周期
            long_period: 长期均线周期
            holding_period: 持有周期（天）
            stop_loss: 止损百分比
            take_profit: 止盈百分比
            
        Returns:
            回测结果字典，包含：
            - accuracy: 准确率
            - profit_loss_ratio: 盈亏比
            - total_trades: 总交易次数
            - profitable_trades: 盈利交易次数
            - losing_trades: 亏损交易次数
            - detailed_results: 详细交易记录
        """
        start_time = time.time()
        
        # 识别信号
        golden_crosses = self.identify_golden_cross(short_period, long_period)
        death_crosses = self.identify_death_cross(short_period, long_period)
        
        # 合并所有信号
        all_signals = pd.concat([
            golden_crosses.assign(signal_type='golden_cross'),
            death_crosses.assign(signal_type='death_cross')
        ]).sort_values('date')
        
        if all_signals.empty:
            return {
                'accuracy': 0.0,
                'profit_loss_ratio': 0.0,
                'total_trades': 0,
                'profitable_trades': 0,
                'losing_trades': 0,
                'detailed_results': pd.DataFrame()
            }
        
        # 创建日期到索引的映射
        date_to_idx = {date: idx for idx, date in enumerate(self._get_column('date'))}
        close = self._get_column('close')
        high = self._get_column('high')
        low = self._get_column('low')
        
        # 执行回测
        trade_results = []
        
        for idx, signal in all_signals.iterrows():
            signal_date = signal['date']
            signal_idx = date_to_idx.get(signal_date)
            
            if signal_idx is None or signal_idx + holding_period >= len(close):
                continue
            
            entry_price = signal['price']
            signal_type = signal['signal_type']
            
            # 计算持有期间的价格变化
            exit_price = None
            exit_reason = None
            max_profit = 0.0
            max_loss = 0.0
            
            for day in range(1, holding_period + 1):
                if signal_idx + day >= len(close):
                    break
                
                current_price = close.iloc[signal_idx + day]
                current_high = high.iloc[signal_idx + day]
                current_low = low.iloc[signal_idx + day]
                
                # 计算盈亏
                if signal_type == 'golden_cross':
                    profit = (current_price - entry_price) / entry_price * 100
                else:
                    profit = (entry_price - current_price) / entry_price * 100
                
                # 更新最大盈亏
                max_profit = max(max_profit, profit)
                max_loss = min(max_loss, profit)
                
                # 检查止损止盈
                if profit <= stop_loss:
                    exit_price = current_price
                    exit_reason = 'stop_loss'
                    break
                elif profit >= take_profit:
                    exit_price = current_price
                    exit_reason = 'take_profit'
                    break
                elif day == holding_period:
                    exit_price = current_price
                    exit_reason = 'holding_period'
            
            if exit_price is not None:
                final_profit = (exit_price - entry_price) / entry_price * 100
                if signal_type == 'death_cross':
                    final_profit = -final_profit
                
                trade_results.append({
                    'date': signal_date,
                    'signal_type': signal_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'profit': final_profit,
                    'max_profit': max_profit,
                    'max_loss': max_loss,
                    'exit_reason': exit_reason,
                    'is_profitable': final_profit > 0
                })
        
        # 计算统计数据
        detailed_results = pd.DataFrame(trade_results)
        
        if not detailed_results.empty:
            total_trades = len(detailed_results)
            profitable_trades = len(detailed_results[detailed_results['is_profitable']])
            losing_trades = total_trades - profitable_trades
            accuracy = profitable_trades / total_trades * 100
            
            # 计算盈亏比
            profitable_avg = detailed_results[detailed_results['is_profitable']]['profit'].mean()
            losing_avg = detailed_results[~detailed_results['is_profitable']]['profit'].mean()
            profit_loss_ratio = abs(profitable_avg / losing_avg) if losing_avg != 0 else 0
        else:
            total_trades = 0
            profitable_trades = 0
            losing_trades = 0
            accuracy = 0.0
            profit_loss_ratio = 0.0
        
        execution_time = (time.time() - start_time) * 1000
        logger.info(f"回测完成，共 {total_trades} 笔交易，准确率 {accuracy:.2f}%，耗时 {execution_time:.2f}ms")
        
        self.performance = {
            'accuracy': accuracy,
            'profit_loss_ratio': profit_loss_ratio,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'detailed_results': detailed_results
        }
        
        return self.performance
    
    def get_signal_summary(self) -> Dict[str, any]:
        """
        获取信号摘要
        
        Returns:
            信号摘要字典
        """
        summary = {}
        
        if 'golden_cross' in self.signals:
            summary['golden_cross_count'] = len(self.signals['golden_cross'])
            summary['golden_cross_avg_strength'] = self.signals['golden_cross']['strength'].mean()
        
        if 'death_cross' in self.signals:
            summary['death_cross_count'] = len(self.signals['death_cross'])
            summary['death_cross_avg_strength'] = self.signals['death_cross']['strength'].mean()
        
        if self.performance:
            summary.update({
                'backtest_accuracy': self.performance['accuracy'],
                'profit_loss_ratio': self.performance['profit_loss_ratio'],
                'total_trades': self.performance['total_trades']
            })
        
        return summary


if __name__ == "__main__":
    # 示例用法
    from ak_fund import AkFund
    
    # 获取股票数据
    ak_fund = AkFund()
    stock_data = ak_fund.get_stock_kline('600519', period='daily', start_date='2023-01-01', end_date='2023-12-31')
    
    # 创建金叉/死叉分析器
    analyzer = GoldenCrossAnalyzer(stock_data)
    
    # 识别金叉
    print("=== 金叉识别 ===")
    golden_crosses = analyzer.identify_golden_cross(short_period=5, long_period=20)
    print(f"识别到 {len(golden_crosses)} 个金叉信号")
    if not golden_crosses.empty:
        print("\n金叉信号详情:")
        print(golden_crosses[['date', 'price', 'strength', 'price_change_5d']].head())
    
    # 识别死叉
    print("\n=== 死叉识别 ===")
    death_crosses = analyzer.identify_death_cross(short_period=5, long_period=20)
    print(f"识别到 {len(death_crosses)} 个死叉信号")
    if not death_crosses.empty:
        print("\n死叉信号详情:")
        print(death_crosses[['date', 'price', 'strength', 'price_change_5d']].head())
    
    # 评估信号有效性
    print("\n=== 信号有效性评估 ===")
    valid_golden = analyzer.evaluate_signal_validity(golden_crosses)
    print(valid_golden[['date', 'strength', 'validity_score', 'signal_level']].head())
    
    # 历史回测
    print("\n=== 历史回测 ===")
    backtest_results = analyzer.backtest_signals(short_period=5, long_period=20, holding_period=10)
    print(f"总交易次数: {backtest_results['total_trades']}")
    print(f"准确率: {backtest_results['accuracy']:.2f}%")
    print(f"盈亏比: {backtest_results['profit_loss_ratio']:.2f}")
    
    # 获取信号摘要
    print("\n=== 信号摘要 ===")
    summary = analyzer.get_signal_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
