"""
仓位分配器
"""


class PositionSizer:
    """确定每笔交易的资金分配"""

    def __init__(self, method: str = "equal_weight", max_positions: int = 10):
        self.method = method
        self.max_positions = max_positions

    def calculate_size(
        self,
        cash: float,
        portfolio_total: float,
        signal_strength: float = 1.0,
        num_active: int = 0,
    ) -> float:
        """
        计算单笔交易可分配资金比例

        Args:
            cash: 当前现金
            portfolio_total: 总资产
            signal_strength: 信号强度 (0-1)
            num_active: 当前持仓数

        Returns:
            可分配资金占总资产比例 (0-1)
        """
        available_slots = max(self.max_positions - num_active, 1)

        if self.method == "equal_weight":
            base_pct = 1.0 / self.max_positions
        elif self.method == "signal_weighted":
            base_pct = (1.0 / self.max_positions) * signal_strength
        else:
            base_pct = 1.0 / self.max_positions

        return min(base_pct, 1.0 / available_slots) if available_slots > 0 else 0
