"""
基金加权平均分析模块
基于基金持仓股票的持有比例进行加权平均，判断基金是否还能继续持有
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import os

from .signal_judgment import SignalJudger, SignalLevel, SignalResult


class FundRecommendation(Enum):
    """基金持有建议枚举"""
    STRONG_BUY = "强烈建议买入"      # 加权得分 >= 0.6
    BUY = "建议买入"                # 0.2 <= 得分 < 0.6
    HOLD = "建议持有"               # -0.2 < 得分 < 0.2
    SELL = "建议卖出"               # -0.6 < 得分 <= -0.2
    STRONG_SELL = "强烈建议卖出"    # 得分 <= -0.6


@dataclass
class StockHoldings:
    """股票持仓数据类"""
    stock_code: str          # 股票代码
    stock_name: str          # 股票名称
    holding_ratio: float     # 持有比例（百分比）
    market_value: Optional[float] = None  # 持仓市值
    shares: Optional[float] = None        # 持股数量
    quarter: Optional[str] = None         # 所属季度


@dataclass
class StockSignalInfo:
    """股票信号信息数据类"""
    stock_code: str          # 股票代码
    stock_name: str          # 股票名称
    holding_ratio: float     # 持有比例（百分比）
    overall_score: float     # 综合得分（-1到1）
    signal_level: SignalLevel  # 信号等级
    recommendation: str      # 股票建议
    confidence: float        # 置信度（0-1）
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息


@dataclass
class FundAnalysisResult:
    """基金分析结果数据类"""
    fund_code: str                       # 基金代码
    fund_name: str                       # 基金名称
    total_stocks: int                    # 总股票数量
    analyzed_stocks: int                 # 已分析股票数量
    weighted_score: float                # 加权平均得分（-1到1）
    fund_recommendation: FundRecommendation  # 基金持有建议
    confidence: float                    # 置信度（0-1）
    stock_signals: List[StockSignalInfo]  # 各股票信号列表
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'fund_code': self.fund_code,
            'fund_name': self.fund_name,
            'total_stocks': self.total_stocks,
            'analyzed_stocks': self.analyzed_stocks,
            'weighted_score': self.weighted_score,
            'fund_recommendation': self.fund_recommendation.value,
            'confidence': self.confidence,
            'stock_signals': [
                {
                    'stock_code': s.stock_code,
                    'stock_name': s.stock_name,
                    'holding_ratio': s.holding_ratio,
                    'overall_score': s.overall_score,
                    'signal_level': s.signal_level.value,
                    'recommendation': s.recommendation,
                    'confidence': s.confidence
                }
                for s in self.stock_signals
            ],
            'details': self.details
        }


class FundWeightedAnalyzer:
    """
    基金加权平均分析器
    
    基于基金持仓中各股票的持有比例进行加权平均，
    计算基金的加权得分，给出基金持有建议
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化基金分析器
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        self._validate_data_dir()
    
    def _validate_data_dir(self) -> None:
        """验证数据目录是否存在"""
        if not os.path.exists(self.data_dir):
            logger.warning(f"数据目录 {self.data_dir} 不存在，将尝试创建")
            os.makedirs(self.data_dir, exist_ok=True)
    
    def load_stock_signals(self, stock_code: str) -> Optional[SignalResult]:
        """
        加载股票的信号判断结果
        
        Args:
            stock_code: 股票代码
            
        Returns:
            SignalResult对象，如果未找到则返回None
        """
        try:
            # 尝试读取信号文件
            signal_file = os.path.join(self.data_dir, f"{stock_code}_signals.csv")
            indicator_file = os.path.join(self.data_dir, f"{stock_code}_with_indicators.csv")
            
            if not os.path.exists(signal_file) or not os.path.exists(indicator_file):
                logger.warning(f"股票 {stock_code} 的信号数据文件不存在")
                return None
            
            # 读取技术指标数据
            indicator_df = pd.read_csv(indicator_file)
            
            # 技术指标配置
            tech_period = {
                'ma_period': [3, 5, 10, 14, 20, 30, 45],
                'sma_period': [3, 5, 10, 14, 20, 30, 45],
                'ema_period': [12, 26],
                'rsi_period': [6, 12, 24],
                'macd_period': ['12-26-9'],
                'boll_period': ['20-2'],
                'kdj_period': ['9-3-3'],
                'atr_period': [10],
                'cci_period': [20, 26],
                'williams_r_period': [10],
                'bias_period': [5, 10, 20, 30, 60, 120, 250],
                'psy_period': [10],
                'rsv_period': [10],
                'volume_period': [20]
            }
            
            # 创建信号判断器
            judger = SignalJudger(data=indicator_df, tech_period=tech_period)
            
            # 获取信号结果
            signal_result = judger.get_signals()
            
            return signal_result
            
        except Exception as e:
            logger.error(f"加载股票 {stock_code} 信号数据失败: {e}")
            return None
    
    def parse_holdings_data(self, holdings_df: pd.DataFrame) -> List[StockHoldings]:
        """
        解析持仓数据，提取股票持仓信息
        
        Args:
            holdings_df: 持仓DataFrame，应包含以下列：
                         - 股票代码
                         - 股票名称
                         - 持有比例（%）
                         
        Returns:
            股票持仓列表
        """
        holdings_list = []
        
        # 尝试识别列名（支持中英文）
        stock_code_col = None
        stock_name_col = None
        ratio_col = None
        
        # 常见列名映射
        possible_code_cols = ['股票代码', '股票代码', 'symbol', 'code', '证券代码']
        possible_name_cols = ['股票名称', '股票名称', 'name', 'stock_name', '证券简称']
        possible_ratio_cols = ['持有比例(%)', '持有比例', 'holding_ratio', 'ratio', '比例']
        
        for col in holdings_df.columns:
            if any(pattern in col for pattern in possible_code_cols):
                stock_code_col = col
            if any(pattern in col for pattern in possible_name_cols):
                stock_name_col = col
            if any(pattern in col for pattern in possible_ratio_cols):
                ratio_col = col
        
        if not stock_code_col:
            raise ValueError("未找到股票代码列")
        
        # 如果没有找到比例列，尝试其他可能列名
        if not ratio_col:
            for col in holdings_df.columns:
                if any(pattern in col for pattern in ['比例', '比重', '权重']):
                    ratio_col = col
                    break
        
        # 遍历每一行
        for idx, row in holdings_df.iterrows():
            try:
                stock_code = str(row[stock_code_col])
                
                # 获取股票名称
                if stock_name_col:
                    stock_name = str(row[stock_name_col])
                else:
                    stock_name = f"股票{stock_code}"
                
                # 获取持有比例
                if ratio_col:
                    ratio_str = str(row[ratio_col])
                    # 尝试提取百分比数值
                    ratio_match = None
                    if '%' in ratio_str:
                        import re
                        ratio_match = re.search(r'(\d+\.?\d*)%', ratio_str)
                    if ratio_match:
                        holding_ratio = float(ratio_match.group(1))
                    else:
                        try:
                            holding_ratio = float(ratio_str)
                        except:
                            logger.warning(f"无法解析持仓比例: {ratio_str}，使用默认值0")
                            holding_ratio = 0.0
                else:
                    # 如果没有比例列，平均分配
                    holding_ratio = 0.0
                
                # 创建持仓对象
                holding = StockHoldings(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    holding_ratio=holding_ratio
                )
                
                holdings_list.append(holding)
                
            except Exception as e:
                logger.warning(f"解析第{idx}行持仓数据失败: {e}")
                continue
        
        # 如果没有找到有效的比例数据，进行归一化处理
        if all(h.holding_ratio == 0 for h in holdings_list):
            logger.info("未找到有效的持仓比例数据，使用平均权重")
            for holding in holdings_list:
                holding.holding_ratio = 100.0 / len(holdings_list) if holdings_list else 0
            # 确保比例总和为100%（仅在使用平均权重时）
            total_ratio = sum(h.holding_ratio for h in holdings_list)
            if total_ratio > 0:
                for holding in holdings_list:
                    holding.holding_ratio = (holding.holding_ratio / total_ratio) * 100
        
        logger.info(f"解析到 {len(holdings_list)} 只股票持仓数据")
        return holdings_list
    
    def analyze_fund(self, fund_code: str, holdings_df: pd.DataFrame, 
                    fund_name: Optional[str] = None) -> FundAnalysisResult:
        """
        分析基金持有建议
        
        Args:
            fund_code: 基金代码
            holdings_df: 持仓DataFrame
            fund_name: 基金名称（可选）
            
        Returns:
            FundAnalysisResult对象
        """
        if holdings_df.empty:
            raise ValueError("持仓数据不能为空")
        
        if not fund_name:
            fund_name = f"基金{fund_code}"
        
        # 解析持仓数据
        holdings = self.parse_holdings_data(holdings_df)
        
        if not holdings:
            raise ValueError("未解析到有效的持仓数据")
        
        # 分析每只股票的信号
        stock_signals = []
        analyzed_codes = []
        
        for holding in holdings:
            logger.info(f"分析股票 {holding.stock_code} ({holding.stock_name})")
            
            # 加载股票信号
            signal_result = self.load_stock_signals(holding.stock_code)
            
            if signal_result is None:
                logger.warning(f"股票 {holding.stock_code} 信号数据缺失，跳过")
                continue
            
            # 创建股票信号信息
            stock_signal = StockSignalInfo(
                stock_code=holding.stock_code,
                stock_name=holding.stock_name,
                holding_ratio=holding.holding_ratio,
                overall_score=signal_result.overall_score,
                signal_level=signal_result.signal_level,
                recommendation=signal_result.recommendation,
                confidence=signal_result.confidence,
                details=signal_result.details
            )
            
            stock_signals.append(stock_signal)
            analyzed_codes.append(holding.stock_code)
        
        if not stock_signals:
            raise ValueError("没有股票能够成功分析")
        
        # 计算加权平均得分
        total_weight = sum(s.holding_ratio for s in stock_signals)
        
        if total_weight > 0:
            weighted_score = sum(
                s.overall_score * (s.holding_ratio / total_weight) 
                for s in stock_signals
            )
            
            # 计算平均置信度
            avg_confidence = sum(
                s.confidence * (s.holding_ratio / total_weight) 
                for s in stock_signals
            )
        else:
            # 如果没有权重信息，使用简单平均
            weighted_score = np.mean([s.overall_score for s in stock_signals])
            avg_confidence = np.mean([s.confidence for s in stock_signals])
        
        # 确保为Python float类型（避免numpy类型）
        weighted_score = float(weighted_score)
        avg_confidence = float(avg_confidence)
        
        # 确定基金持有建议
        if weighted_score >= 0.6:
            fund_recommendation = FundRecommendation.STRONG_BUY
        elif weighted_score >= 0.2:
            fund_recommendation = FundRecommendation.BUY
        elif weighted_score > -0.2:
            fund_recommendation = FundRecommendation.HOLD
        elif weighted_score > -0.6:
            fund_recommendation = FundRecommendation.SELL
        else:
            fund_recommendation = FundRecommendation.STRONG_SELL
        
        # 构建详细信息
        details = {
            'analyzed_stock_codes': analyzed_codes,
            'weighted_score': weighted_score,
            'avg_confidence': avg_confidence,
            'signal_distribution': self._get_signal_distribution(stock_signals),
            'holding_distribution': self._get_holding_distribution(stock_signals)
        }
        
        # 创建分析结果
        result = FundAnalysisResult(
            fund_code=fund_code,
            fund_name=fund_name,
            total_stocks=len(holdings),
            analyzed_stocks=len(stock_signals),
            weighted_score=weighted_score,
            fund_recommendation=fund_recommendation,
            confidence=avg_confidence,
            stock_signals=stock_signals,
            details=details
        )
        
        return result
    
    def _get_signal_distribution(self, stock_signals: List[StockSignalInfo]) -> Dict[str, int]:
        """获取信号分布统计"""
        distribution = {
            '强烈买入': 0,
            '买入': 0,
            '持有': 0,
            '卖出': 0,
            '强烈卖出': 0
        }
        
        for signal in stock_signals:
            signal_name = signal.signal_level.value
            if signal_name in distribution:
                distribution[signal_name] += 1
        
        return distribution
    
    def _get_holding_distribution(self, stock_signals: List[StockSignalInfo]) -> Dict[str, float]:
        """获取持仓分布统计"""
        distribution = {
            '强烈买入': 0.0,
            '买入': 0.0,
            '持有': 0.0,
            '卖出': 0.0,
            '强烈卖出': 0.0
        }
        
        total_weight = sum(s.holding_ratio for s in stock_signals)
        
        if total_weight > 0:
            for signal in stock_signals:
                signal_name = signal.signal_level.value
                if signal_name in distribution:
                    distribution[signal_name] += signal.holding_ratio / total_weight * 100
        
        return distribution
    
    def generate_report(self, result: FundAnalysisResult) -> str:
        """
        生成分析报告
        
        Args:
            result: FundAnalysisResult对象
            
        Returns:
            报告字符串
        """
        report_lines = []
        
        report_lines.append("=" * 80)
        report_lines.append("基金加权平均分析报告")
        report_lines.append("=" * 80)
        report_lines.append(f"基金代码: {result.fund_code}")
        report_lines.append(f"基金名称: {result.fund_name}")
        report_lines.append(f"分析日期: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("-" * 80)
        report_lines.append(f"总股票数: {result.total_stocks}")
        report_lines.append(f"已分析股票数: {result.analyzed_stocks}")
        report_lines.append(f"分析覆盖率: {(result.analyzed_stocks/result.total_stocks)*100:.1f}%")
        report_lines.append(f"加权平均得分: {result.weighted_score:.3f}")
        report_lines.append(f"置信度: {result.confidence:.1%}")
        report_lines.append("-" * 80)
        
        # 基金持有建议
        recommendation_color = ""
        if result.fund_recommendation in [FundRecommendation.STRONG_BUY, FundRecommendation.BUY]:
            recommendation_color = "✓"
        elif result.fund_recommendation in [FundRecommendation.STRONG_SELL, FundRecommendation.SELL]:
            recommendation_color = "✗"
        
        report_lines.append(f"{recommendation_color} 基金持有建议: {result.fund_recommendation.value}")
        report_lines.append("-" * 80)
        
        # 信号分布
        signal_dist = result.details['signal_distribution']
        holding_dist = result.details['holding_distribution']
        
        report_lines.append("信号分布（按股票数量）:")
        for signal_type, count in signal_dist.items():
            if count > 0:
                percentage = (count / result.analyzed_stocks) * 100
                report_lines.append(f"  {signal_type}: {count}只 ({percentage:.1f}%)")
        
        report_lines.append("\n持仓分布（按权重）:")
        for signal_type, weight in holding_dist.items():
            if weight > 0:
                report_lines.append(f"  {signal_type}: {weight:.1f}%")
        
        report_lines.append("-" * 80)
        
        # 详细股票信息
        report_lines.append("各股票详细分析:")
        report_lines.append("-" * 80)
        
        # 按持有比例降序排列
        sorted_signals = sorted(
            result.stock_signals, 
            key=lambda x: x.holding_ratio, 
            reverse=True
        )
        
        for i, signal in enumerate(sorted_signals, 1):
            report_lines.append(f"{i}. {signal.stock_code} - {signal.stock_name}")
            report_lines.append(f"   持有比例: {signal.holding_ratio:.2f}%")
            report_lines.append(f"   信号等级: {signal.signal_level.value}")
            report_lines.append(f"   综合得分: {signal.overall_score:.3f}")
            report_lines.append(f"   建议: {signal.recommendation}")
            report_lines.append(f"   置信度: {signal.confidence:.1%}")
            
            if i < len(sorted_signals):
                report_lines.append("   " + "-" * 60)
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def save_report(self, result: FundAnalysisResult, output_dir: str = "outputs/reports") -> str:
        """
        保存分析报告到文件
        
        Args:
            result: FundAnalysisResult对象
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成报告
        report_text = self.generate_report(result)
        
        # 生成文件名（格式：类型-股票/基金-代码-日期）
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        # 基金分析使用格式：fund-analysis-fund-{代码}-{日期}.txt
        filename = f"fund-analysis-fund-{result.fund_code}-{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # 保存报告
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        # 保存JSON格式结果（使用相同格式）
        json_filepath = os.path.join(output_dir, f"fund-analysis-fund-{result.fund_code}-{timestamp}.json")
        import json
        
        # 将对象转换为字典
        result_dict = result.to_dict()
        
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析报告已保存到: {filepath}")
        logger.info(f"JSON结果已保存到: {json_filepath}")
        
        return filepath


# 示例使用
if __name__ == "__main__":
    # 创建示例持仓数据
    sample_holdings = pd.DataFrame({
        '股票代码': ['002149', '002371', '002475', '002565', '002846'],
        '股票名称': ['西部材料', '北方华创', '立讯精密', '洽洽食品', '景嘉微'],
        '持有比例(%)': [15.2, 12.5, 18.8, 9.3, 8.6]
    })
    
    print("=" * 80)
    print("基金加权平均分析模块测试")
    print("=" * 80)
    
    try:
        # 创建分析器
        analyzer = FundWeightedAnalyzer(data_dir="data")
        
        # 分析基金
        print("\n分析基金 000001...")
        result = analyzer.analyze_fund(
            fund_code="000001",
            holdings_df=sample_holdings,
            fund_name="示例基金"
        )
        
        # 生成报告
        report = analyzer.generate_report(result)
        print(report)
        
        # 保存报告
        report_path = analyzer.save_report(result)
        print(f"\n报告已保存到: {report_path}")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)