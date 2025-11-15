"""
取引コスト計算モジュール

手数料や取引コストの計算を行う
"""


class CostCalculator:
    """取引コスト計算機"""

    def __init__(self, commission_rate: float):
        """
        Args:
            commission_rate: 手数料率（片道、0-1の範囲）
        """
        if commission_rate < 0 or commission_rate > 1.0:
            raise ValueError("手数料率は0から1の範囲で指定してください")

        self.commission_rate = commission_rate

    def calculate_commission(
        self,
        price: float,
        quantity: int,
        side: str
    ) -> float:
        """
        取引手数料を計算

        Args:
            price: 価格
            quantity: 数量
            side: 取引方向（'buy' または 'sell'）

        Returns:
            手数料（円）
        """
        total_value = price * quantity
        return total_value * self.commission_rate

    def calculate_roundtrip_cost(
        self,
        entry_price: float,
        exit_price: float,
        quantity: int
    ) -> float:
        """
        往復（エントリー + エグジット）の総コストを計算

        Args:
            entry_price: エントリー価格
            exit_price: エグジット価格
            quantity: 数量

        Returns:
            往復の総手数料（円）
        """
        entry_cost = self.calculate_commission(entry_price, quantity, 'buy')
        exit_cost = self.calculate_commission(exit_price, quantity, 'sell')
        return entry_cost + exit_cost

    def calculate_net_profit(
        self,
        entry_price: float,
        exit_price: float,
        quantity: int,
        side: str = 'long'
    ) -> float:
        """
        手数料控除後の純損益を計算

        Args:
            entry_price: エントリー価格
            exit_price: エグジット価格
            quantity: 数量
            side: ポジション方向（'long' または 'short'）

        Returns:
            手数料控除後の純損益（円）
        """
        # 総損益（手数料控除前）
        if side == 'long':
            gross_profit = (exit_price - entry_price) * quantity
        elif side == 'short':
            gross_profit = (entry_price - exit_price) * quantity
        else:
            raise ValueError("side は 'long' または 'short' のいずれかを指定してください")

        # 往復手数料
        total_commission = self.calculate_roundtrip_cost(
            entry_price,
            exit_price,
            quantity
        )

        # 純損益 = 総損益 - 手数料
        return gross_profit - total_commission
