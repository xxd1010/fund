"""
基金持仓成本计算模块

本模块提供基金持仓成本的完整计算功能，包括：
1. 单次申购成本计算
2. 多次申购/定投的加权平均成本计算
3. 分红方式（现金分红/红利再投资）对持仓成本的影响
4. 赎回操作对持仓成本的影响
5. 完整的持仓报告生成

使用示例：
    from fund_cost import FundCostCalculator, PurchaseRecord
    
    # 单次申购
    calc = FundCostCalculator()
    result = calc.calculate_single_purchase_cost(10000, 0.001, 1.5623)
    
    # 多次定投
    purchases = [PurchaseRecord(date="2024-01-15", amount=5000, fee_rate=0.001, nav=1.5)]
    calc2 = FundCostCalculator(purchases=purchases)
    result2 = calc2.calculate_weighted_average_cost()
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import math


class DividendType(Enum):
    """
    分红方式枚举
    
    属性:
        CASH: 现金分红 - 投资者获得现金分红，持有份额不变，持仓成本不变
        REINVEST: 红利再投资 - 分红金额用于再投资，增加持有份额，降低持仓成本
    """
    CASH = "cash"
    REINVEST = "reinvest"


@dataclass
class PurchaseRecord:
    """
    基金申购记录数据类
    
    用于记录单次基金申购的详细信息，包括申购日期、申购金额、申购费率和基金净值。
    自动计算手续费、净申购金额、获得份额等派生属性。
    
    属性:
        date: 申购日期，格式为 "YYYY-MM-DD"
        amount: 申购金额（元），即投资者投入的总金额
        fee_rate: 申购费率（小数形式），如0.001表示0.1%
        nav: 基金单位净值，即申购当日的基金净值
    
    示例:
        >>> record = PurchaseRecord(date="2024-01-15", amount=10000, fee_rate=0.001, nav=1.5)
        >>> record.fee  # 手续费
        10.0
        >>> record.shares  # 获得份额
        6660.0
    """
    date: str
    amount: float
    fee_rate: float
    nav: float
    
    @property
    def fee(self) -> float:
        """计算申购手续费"""
        return self.amount * self.fee_rate
    
    @property
    def net_amount(self) -> float:
        """计算净申购金额（扣除手续费后的金额）"""
        return self.amount - self.fee
    
    @property
    def shares(self) -> float:
        """计算获得的基金份额"""
        return self.net_amount / self.nav
    
    @property
    def total_cost(self) -> float:
        """返回总投入成本"""
        return self.amount


@dataclass
class DividendRecord:
    """
    基金分红记录数据类
    
    用于记录单次基金分红的详细信息，包括分红日期、每份分红金额、持有份额和分红方式。
    自动计算总分红金额。
    
    属性:
        date: 分红日期，格式为 "YYYY-MM-DD"
        dividend_per_share: 每份分红金额（元）
        shares: 持有份额（分红时的持有份额）
        dividend_type: 分红方式，详见 DividendType 枚举
    
    示例:
        >>> record = DividendRecord(date="2024-06-30", dividend_per_share=0.05, 
        ...                         shares=1000, dividend_type=DividendType.CASH)
        >>> record.total_dividend  # 总分红金额
        50.0
    """
    date: str
    dividend_per_share: float
    shares: float
    dividend_type: DividendType
    
    @property
    def total_dividend(self) -> float:
        """计算总分红金额"""
        return self.dividend_per_share * self.shares


@dataclass
class RedemptionRecord:
    """
    基金赎回记录数据类
    
    用于记录单次基金赎回的详细信息，包括赎回日期、赎回份额、基金净值和赎回费率。
    自动计算赎回金额、手续费和净到账金额。
    
    属性:
        date: 赎回日期，格式为 "YYYY-MM-DD"
        shares: 赎回份额
        nav: 基金单位净值（赎回时的净值）
        fee_rate: 赎回费率（小数形式），如0.005表示0.5%
    
    示例:
        >>> record = RedemptionRecord(date="2024-07-15", shares=1000, nav=1.68, fee_rate=0.0)
        >>> record.redemption_amount  # 赎回金额
        1680.0
    """
    date: str
    shares: float
    nav: float
    fee_rate: float
    
    @property
    def redemption_amount(self) -> float:
        """计算赎回金额（份额 × 净值）"""
        return self.shares * self.nav
    
    @property
    def fee(self) -> float:
        """计算赎回手续费"""
        return self.redemption_amount * self.fee_rate
    
    @property
    def net_amount(self) -> float:
        """计算净到账金额（扣除手续费后）"""
        return self.redemption_amount - self.fee


class FundCostCalculator:
    """
    基金持仓成本计算器
    
    核心计算类，用于计算基金持仓的各类成本和收益。支持：
    - 单次和多次申购的持仓成本计算
    - 加权平均成本法计算
    - 分红方式对成本的影响分析
    - 赎回操作对成本的影响分析
    - 完整的持仓报告生成
    
    属性:
        purchases: 申购记录列表
        dividends: 分红记录列表
        redemptions: 赎回记录列表
    
    使用示例:
        # 创建计算器
        calculator = FundCostCalculator(
            purchases=[PurchaseRecord(...)],
            dividends=[DividendRecord(...)],
            redemptions=[RedemptionRecord(...)]
        )
        
        # 计算加权平均成本
        cost_result = calculator.calculate_weighted_average_cost()
        
        # 生成完整持仓报告
        report = calculator.get_full_position_report(current_nav=1.75)
    """
    
    def __init__(self, purchases: Optional[List[PurchaseRecord]] = None,
                 dividends: Optional[List[DividendRecord]] = None,
                 redemptions: Optional[List[RedemptionRecord]] = None):
        """
        初始化基金成本计算器
        
        参数:
            purchases: 申购记录列表，默认为空列表
            dividends: 分红记录列表，默认为空列表
            redemptions: 赎回记录列表，默认为空列表
        """
        self.purchases = purchases or []
        self.dividends = dividends or []
        self.redemptions = redemptions or []
    
    def calculate_single_purchase_cost(self, amount: float, fee_rate: float, nav: float) -> dict:
        """
        计算单次申购的成本
        
        根据申购金额、申购费率和基金净值，计算单次申购的各项成本指标。
        
        参数:
            amount: 申购金额（元），投资者计划投入的金额
            fee_rate: 申购费率（小数形式），如0.001表示0.1%
            nav: 基金单位净值，申购当日的净值
        
        返回:
            包含以下键的字典:
            - 申购金额: 输入的申购金额
            - 申购费率: 输入的申购费率
            - 申购费率金额: 实际扣除的手续费
            - 净值: 输入的基金净值
            - 获得份额: 扣除手续费后获得的基金份额
            - 持仓成本(每份): 每份基金的实际成本
            - 实际投入: 实际投入的金额
        
        示例:
            >>> calc = FundCostCalculator()
            >>> result = calc.calculate_single_purchase_cost(10000, 0.001, 1.5623)
            >>> result["获得份额"]
            6394.4185
        """
        fee = amount * fee_rate
        net_amount = amount - fee
        shares = net_amount / nav
        cost_per_share = amount / shares
        return {
            "申购金额": amount,
            "申购费率": fee_rate,
            "申购费率金额": fee,
            "净值": nav,
            "获得份额": shares,
            "持仓成本(每份)": cost_per_share,
            "实际投入": amount
        }
    
    def calculate_weighted_average_cost(self) -> dict:
        """
        计算多次申购的加权平均成本
        
        使用加权平均法计算多次申购（或定投）的平均持仓成本。
        公式：加权平均成本 = 总投入金额 / 总持有份额
        
        返回:
            包含以下键的字典:
            - 总投入金额: 所有申购的累计投入
            - 总手续费: 所有申购的累计手续费
            - 总获得份额: 所有申购获得的份额总和
            - 加权平均成本(每份): 综合计算的单位持仓成本
            - 当前单位成本: 与加权平均成本相同
        
        注意:
            该计算不考虑分红和赎回的影响，仅基于申购记录
        """
        if not self.purchases:
            return {"总投入": 0, "总份额": 0, "平均成本": 0}
        
        total_invested = 0.0
        total_shares = 0.0
        total_fees = 0.0
        
        for p in self.purchases:
            total_invested += p.amount
            total_shares += p.shares
            total_fees += p.fee
        
        avg_cost = total_invested / total_shares if total_shares > 0 else 0
        
        return {
            "总投入金额": total_invested,
            "总手续费": total_fees,
            "总获得份额": total_shares,
            "加权平均成本(每份)": avg_cost,
            "当前单位成本": total_invested / total_shares if total_shares > 0 else 0
        }
    
    def calculate_dividend_impact(self, current_nav: float) -> dict:
        """
        计算分红对持仓的影响
        
        分析不同分红方式对持仓成本和份额的影响。
        
        参数:
            current_nav: 当前基金净值，用于计算红利再投资时的新增份额
        
        返回:
            包含以下键的字典:
            - 现金分红总金额: 现金分红累计金额
            - 红利再投资总金额: 红利再投资对应的金额
            - 红利再投资新增份额: 红利再投资新增的基金份额
        
        说明:
            - 现金分红：投资者获得现金，持仓份额和成本不变
            - 红利再投资：分红金额转换为新份额，降低单位持仓成本
        """
        total_dividend_cash = 0.0
        total_dividend_shares = 0.0
        additional_shares_from_reinvest = 0.0
        
        for d in self.dividends:
            div_amount = d.total_dividend
            if d.dividend_type == DividendType.CASH:
                total_dividend_cash += div_amount
            elif d.dividend_type == DividendType.REINVEST:
                reinvest_fee = 0.0
                net_div = div_amount - reinvest_fee
                new_shares = net_div / current_nav
                total_dividend_shares += div_amount
                additional_shares_from_reinvest += new_shares
        
        return {
            "现金分红总金额": total_dividend_cash,
            "红利再投资总金额": total_dividend_shares,
            "红利再投资新增份额": additional_shares_from_reinvest
        }
    
    def calculate_with_dividend_reinvestment(self, current_nav: float) -> dict:
        """
        计算包含红利再投资的调整后持仓成本
        
        考虑红利再投资后，重新计算持仓成本。
        
        参数:
            current_nav: 当前基金净值
        
        返回:
            包含以下键的字典:
            - 原始投入: 原始申购总投入
            - 原始份额: 原始申购获得的总份额
            - 红利再投资新增份额: 红利再投资增加的份额
            - 最终持有份额: 调整后的总持有份额
            - 调整后持仓成本(每份): 考虑红利再投资后的单位成本
            - 成本节省: 与原始成本相比节省的金额
        """
        purchase_cost = self.calculate_weighted_average_cost()
        total_shares = purchase_cost["总获得份额"]
        total_invested = purchase_cost["总投入金额"]
        
        dividend_impact = self.calculate_dividend_impact(current_nav)
        additional_shares = dividend_impact["红利再投资新增份额"]
        
        final_shares = total_shares + additional_shares
        adjusted_cost = total_invested / final_shares if final_shares > 0 else 0
        
        return {
            "原始投入": total_invested,
            "原始份额": total_shares,
            "红利再投资新增份额": additional_shares,
            "最终持有份额": final_shares,
            "调整后持仓成本(每份)": adjusted_cost,
            "成本节省": purchase_cost["加权平均成本(每份)"] - adjusted_cost if purchase_cost["加权平均成本(每份)"] > 0 else 0
        }
    
    def calculate_redemption_impact(self, redemption: RedemptionRecord, 
                                     current_avg_cost: float) -> dict:
        """
        计算赎回操作对持仓成本的影响
        
        分析赎回后剩余持仓的成本变化。
        
        参数:
            redemption: 赎回记录
            current_avg_cost: 当前平均持仓成本
        
        返回:
            包含以下键的字典:
            - 赎回份额: 赎回的基金份额
            - 赎回金额: 赎回总金额（份额 × 净值）
            - 赎回手续费: 赎回时扣除的手续费
            - 剩余份额: 赎回后剩余的基金份额
            - 剩余持仓成本: 赎回后剩余持仓的总成本
            - 剩余成本(每份): 赎回后剩余持仓的单位成本
        """
        remaining_shares = 0.0
        remaining_cost = 0.0
        
        total_shares = sum(p.shares for p in self.purchases)
        total_cost = sum(p.amount for p in self.purchases)
        
        if total_shares > redemption.shares:
            remaining_shares = total_shares - redemption.shares
            remaining_cost = (remaining_shares / total_shares) * total_cost
        else:
            remaining_shares = 0
            remaining_cost = 0
        
        return {
            "赎回份额": redemption.shares,
            "赎回金额": redemption.redemption_amount,
            "赎回手续费": redemption.fee,
            "剩余份额": remaining_shares,
            "剩余持仓成本": remaining_cost,
            "剩余成本(每份)": remaining_cost / remaining_shares if remaining_shares > 0 else 0
        }
    
    def get_full_position_report(self, current_nav: float) -> dict:
        """
        生成完整的基金持仓报告
        
        整合所有申购、分红记录，生成全面的持仓分析报告。
        
        参数:
            current_nav: 当前基金净值
        
        返回:
            包含以下键的嵌套字典:
            - 持仓概况: 
              - 总投入: 累计投入金额
              - 总份额: 累计持有份额
              - 当前净值: 输入的当前净值
              - 当前市值: 总份额 × 当前净值
              - 现金分红累计: 现金分红总金额
              - 总收益(含现金分红): 当前市值 - 总投入 + 现金分红
              - 持仓收益率: 收益率百分比
            - 成本分析:
              - 加权平均成本: 基于申购记录的成本
              - 调整后成本(含红利再投资): 考虑红利再投资后的成本
              - 总手续费: 累计支付的手续费
        """
        purchase_summary = self.calculate_weighted_average_cost()
        dividend_summary = self.calculate_dividend_impact(current_nav)
        
        total_shares = purchase_summary["总获得份额"] + dividend_summary["红利再投资新增份额"]
        total_invested = purchase_summary["总投入金额"]
        
        current_value = total_shares * current_nav
        total_profit = current_value - total_invested + dividend_summary["现金分红总金额"]
        
        return {
            "持仓概况": {
                "总投入": total_invested,
                "总份额": total_shares,
                "当前净值": current_nav,
                "当前市值": current_value,
                "现金分红累计": dividend_summary["现金分红总金额"],
                "总收益(含现金分红)": total_profit,
                "持仓收益率": (total_profit / total_invested * 100) if total_invested > 0 else 0
            },
            "成本分析": {
                "加权平均成本": purchase_summary["加权平均成本(每份)"],
                "调整后成本(含红利再投资)": total_invested / total_shares if total_shares > 0 else 0,
                "总手续费": purchase_summary["总手续费"]
            }
        }


def calculate_fund_cost(amount: float, fee_rate: float, nav: float) -> float:
    """
    简化的单次基金成本计算函数
    
    这是一个便捷函数，用于快速计算单次申购的持仓成本（每份）。
    
    参数:
        amount: 申购金额（元）
        fee_rate: 申购费率（小数形式）
        nav: 基金单位净值
    
    返回:
        持仓成本（每份基金的成本）
    
    示例:
        >>> cost = calculate_fund_cost(10000, 0.001, 1.5623)
        >>> cost
        1.5639
    """
    fee = amount * fee_rate
    net_amount = amount - fee
    shares = net_amount / nav
    cost_per_share = amount / shares
    return cost_per_share


def calculate_weighted_cost(purchases: List[dict]) -> float:
    """
    简化的加权平均成本计算函数
    
    这是一个便捷函数，使用字典列表计算多次申购的加权平均成本。
    
    参数:
        purchases: 申购记录列表，每个元素是包含 'amount', 'fee_rate', 'nav' 键的字典
    
    返回:
        加权平均持仓成本（每份）
    
    示例:
        >>> purchases = [
        ...     {"amount": 5000, "fee_rate": 0.001, "nav": 1.5},
        ...     {"amount": 5000, "fee_rate": 0.001, "nav": 1.6}
        ... ]
        >>> cost = calculate_weighted_cost(purchases)
        >>> cost
        1.5494
    """
    total_invested = sum(p["amount"] for p in purchases)
    total_shares = sum((p["amount"] * (1 - p["fee_rate"])) / p["nav"] for p in purchases)
    return total_invested / total_shares if total_shares > 0 else 0


def demo():
    print("=" * 70)
    print("基金持仓成本计算器 - 示例演示")
    print("=" * 70)
    
    print("\n【示例1: 单次申购】")
    print("-" * 50)
    calculator = FundCostCalculator()
    result = calculator.calculate_single_purchase_cost(
        amount=10000.0,
        fee_rate=0.001,
        nav=1.5623
    )
    print("参数: 申购金额=10000元, 申购费率=0.1%, 基金净值=1.5623")
    print("\n计算结果:")
    for key, value in result.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("【示例2: 多次申购/定投 - 加权平均法】")
    print("-" * 50)
    
    purchases = [
        PurchaseRecord(date="2024-01-15", amount=5000.0, fee_rate=0.001, nav=1.2345),
        PurchaseRecord(date="2024-02-15", amount=5000.0, fee_rate=0.001, nav=1.3456),
        PurchaseRecord(date="2024-03-15", amount=5000.0, fee_rate=0.001, nav=1.4567),
        PurchaseRecord(date="2024-04-15", amount=5000.0, fee_rate=0.001, nav=1.5678),
    ]
    
    calculator2 = FundCostCalculator(purchases=purchases)
    result2 = calculator2.calculate_weighted_average_cost()
    
    print("参数: 每月定投5000元, 连续4个月, 申购费率0.1%")
    print("\n各次申购明细:")
    for i, p in enumerate(purchases, 1):
        print(f"  第{i}次: 日期={p.date}, 金额={p.amount}元, 净值={p.nav}, 手续费={p.fee:.2f}元, 获得份额={p.shares:.4f}")
    
    print("\n加权平均成本计算结果:")
    for key, value in result2.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("【示例3: 分红方式影响 - 现金分红】")
    print("-" * 50)
    
    calculator3 = FundCostCalculator(purchases=purchases)
    div_result = calculator3.calculate_dividend_impact(current_nav=1.6500)
    
    print("假设持有期间获得现金分红: 每份0.05元, 共获得份额对应的分红")
    print("当前基金净值: 1.65")
    print("\n分红影响:")
    for key, value in div_result.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n成本分析: 现金分红不影响持仓份额和成本, 成本保持不变")
    
    print("\n" + "=" * 70)
    print("【示例4: 分红方式影响 - 红利再投资】")
    print("-" * 50)
    
    dividends = [
        DividendRecord(date="2024-06-30", dividend_per_share=0.05, 
                      shares=purchases[0].shares + purchases[1].shares + purchases[2].shares + purchases[3].shares,
                      dividend_type=DividendType.REINVEST),
    ]
    
    calculator4 = FundCostCalculator(purchases=purchases, dividends=dividends)
    reinvest_result = calculator4.calculate_with_dividend_reinvestment(current_nav=1.6500)
    
    print("参数: 获得分红0.05元/份, 选择红利再投资, 当前净值1.65")
    print("\n红利再投资效果:")
    for key, value in reinvest_result.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n结论: 红利再投资可降低持仓成本, 本例降低成本约 {:.4f} 元/份".format(
        reinvest_result.get("成本节省", 0)))
    
    print("\n" + "=" * 70)
    print("【示例5: 赎回影响】")
    print("-" * 50)
    
    redemption = RedemptionRecord(
        date="2024-07-15",
        shares=1000.0,
        nav=1.6800,
        fee_rate=0.0
    )
    
    calculator5 = FundCostCalculator(purchases=purchases)
    redemp_result = calculator5.calculate_redemption_impact(
        redemption, 
        current_avg_cost=result2["加权平均成本(每份)"]
    )
    
    print("参数: 赎回份额=1000份, 赎回时净值=1.68, 赎回费率=0%")
    print("\n赎回影响:")
    for key, value in redemp_result.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("【示例6: 完整持仓报告】")
    print("-" * 50)
    
    full_purchases = [
        PurchaseRecord(date="2024-01-15", amount=10000.0, fee_rate=0.001, nav=1.5000),
        PurchaseRecord(date="2024-03-15", amount=10000.0, fee_rate=0.001, nav=1.6000),
    ]
    
    full_dividends = [
        DividendRecord(date="2024-06-30", dividend_per_share=0.08, 
                      shares=13.3244 + 6.2469, dividend_type=DividendType.REINVEST),
    ]
    
    calculator6 = FundCostCalculator(purchases=full_purchases, dividends=full_dividends)
    full_report = calculator6.get_full_position_report(current_nav=1.7500)
    
    print("场景: 2024年1月和3月各申购10000元, 6月底分红选择再投资, 当前净值1.75")
    print("\n持仓概况:")
    for key, value in full_report["持仓概况"].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n成本分析:")
    for key, value in full_report["成本分析"].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("计算公式总结")
    print("=" * 70)
    print("""
1. 单次申购成本:
   手续费 = 申购金额 × 申购费率
   净申购金额 = 申购金额 - 手续费
   获得份额 = 净申购金额 / 基金净值
   持仓成本(每份) = 申购金额 / 获得份额

2. 多次申购加权平均成本:
   总投入 = Σ(每次申购金额)
   总份额 = Σ(每次净申购金额 / 每次净值)
   加权平均成本 = 总投入 / 总份额

3. 现金分红:
   分红金额 = 每份分红 × 持有份额
   持仓成本不变, 份额不变

4. 红利再投资:
   新增份额 = (分红金额 - 再投资费率) / 再投资时净值
   调整后成本 = 总投入 / (原份额 + 新增份额)

5. 赎回影响:
   剩余成本 = (剩余份额 / 原总份额) × 原总成本
""")
    print("=" * 70)


if __name__ == "__main__":
    demo()
