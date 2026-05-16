"""
回测报告生成器
"""

import json
import os
import glob
from typing import Dict, Any, Optional
import pandas as pd

from ..engine.backtest_engine import BacktestResult
from loguru import logger


class BacktestReportGenerator:
    """生成回测摘要报告和详细交易日志"""

    def __init__(self, output_dir: str = "outputs/backtest"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_summary(self, result: BacktestResult, fund_code: str = "") -> str:
        """生成中文摘要报告"""
        m = result.metrics
        bm = result.benchmark_metrics

        lines = []
        lines.append("=" * 70)
        lines.append("回测策略评估报告")
        lines.append("=" * 70)
        lines.append(f"策略名称: {result.strategy_name}")
        lines.append(f"报告时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"交易笔数: {len(result.trades)}")
        lines.append("-" * 70)

        if m:
            lines.append("【收益指标】")
            lines.append(f"  总收益率:     {m.total_return:>10.2%}")
            lines.append(f"  年化收益率:   {m.cagr:>10.2%}")
            lines.append(f"  年化波动率:   {m.annual_volatility:>10.2%}")
            lines.append("")
            lines.append("【风险指标】")
            lines.append(f"  最大回撤:     {m.max_drawdown:>10.2%}")
            lines.append(f"  回撤持续天数: {m.max_drawdown_duration:>10}")
            lines.append("")
            lines.append("【综合指标】")
            lines.append(f"  夏普比率:     {m.sharpe_ratio:>10.2f}")
            lines.append(f"  索提诺比率:   {m.sortino_ratio:>10.2f}")
            lines.append(f"  卡尔玛比率:   {m.calmar_ratio:>10.2f}")
            lines.append("")
            lines.append("【交易统计】")
            lines.append(f"  总交易次数:   {m.total_trades:>10}")
            lines.append(f"  胜率:         {m.win_rate:>10.2%}")
            lines.append(f"  盈亏比:       {m.profit_loss_ratio:>10.2f}")

        if bm:
            lines.append("-" * 70)
            lines.append("【基准对比 (沪深300买入持有)】")
            bm_dict = bm.to_dict() if hasattr(bm, 'to_dict') else bm
            if isinstance(bm_dict, dict):
                for k, v in bm_dict.items():
                    lines.append(f"  {k}: {v}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def generate_trade_log(self, result: BacktestResult) -> pd.DataFrame:
        """生成详细交易日志"""
        if result.trades.empty:
            return pd.DataFrame()
        df = result.trades.copy()

        # 计算每笔交易的盈亏
        sells = df[df["操作"] == "卖出"].copy()
        if not sells.empty:
            sells["盈亏"] = 0.0  # 需要匹配买入对来计算
        return df

    def save_report(self, result: BacktestResult, fund_code: str = "") -> str:
        """保存报告到 outputs/backtest/"""
        # 删除旧报告
        prefix = f"backtest-{fund_code}" if fund_code else "backtest"
        for pattern in [
            os.path.join(self.output_dir, f"{prefix}-summary-*.txt"),
            os.path.join(self.output_dir, f"{prefix}-metrics-*.json"),
            os.path.join(self.output_dir, f"{prefix}-trades-*.csv"),
            os.path.join(self.output_dir, f"{prefix}-equity-*.csv"),
        ]:
            for old in glob.glob(pattern):
                try:
                    os.remove(old)
                except Exception:
                    pass

        timestamp = pd.Timestamp.now().strftime("%Y%m%d-%H%M%S")

        # 保存摘要
        summary_path = os.path.join(self.output_dir, f"{prefix}-summary-{timestamp}.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(self.generate_summary(result, fund_code))

        # 保存指标 JSON
        metrics_path = os.path.join(self.output_dir, f"{prefix}-metrics-{timestamp}.json")
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(result.metrics.to_dict() if result.metrics else {}, f, ensure_ascii=False, indent=2)

        # 保存交易记录 CSV
        trades_path = os.path.join(self.output_dir, f"{prefix}-trades-{timestamp}.csv")
        if not result.trades.empty:
            result.trades.to_csv(trades_path, index=False, encoding="utf-8-sig")

        # 保存净值曲线 CSV
        equity_path = os.path.join(self.output_dir, f"{prefix}-equity-{timestamp}.csv")
        if not result.portfolio_snapshots.empty:
            result.portfolio_snapshots.to_csv(equity_path, index=False, encoding="utf-8-sig")

        logger.info(f"回测报告已保存到: {summary_path}")
        return summary_path
