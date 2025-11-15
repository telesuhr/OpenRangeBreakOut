"""
ポジション管理モジュール

個別ポジションの管理を行う
"""
from datetime import datetime
from typing import Optional


class Position:
    """個別ポジションを表すクラス"""

    def __init__(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: int,
        entry_time: datetime,
        profit_target: Optional[float] = None,
        stop_loss: Optional[float] = None
    ):
        """
        Args:
            symbol: 銘柄コード（例: '7203.T'）
            side: ポジション方向（'long' または 'short'）
            entry_price: エントリー価格
            quantity: 数量
            entry_time: エントリー時刻
            profit_target: 利確目標（比率、例: 0.02 = +2%）
            stop_loss: 損切りライン（比率、例: 0.01 = -1%）

        Raises:
            ValueError: パラメータが不正な場合
        """
        if side not in ['long', 'short']:
            raise ValueError("side は 'long' または 'short' のいずれかを指定してください")

        if quantity <= 0:
            raise ValueError("数量は正の値である必要があります")

        if entry_price <= 0:
            raise ValueError("価格は正の値である必要があります")

        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_time = entry_time
        self.profit_target = profit_target
        self.stop_loss = stop_loss

        # 決済情報
        self.is_open = True
        self.exit_price: Optional[float] = None
        self.exit_time: Optional[datetime] = None
        self.realized_pnl: Optional[float] = None

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """
        含み損益を計算

        Args:
            current_price: 現在価格

        Returns:
            含み損益（円）
        """
        if self.side == 'long':
            return (current_price - self.entry_price) * self.quantity
        else:  # short
            return (self.entry_price - current_price) * self.quantity

    def close(self, exit_price: float, exit_time: datetime):
        """
        ポジションを決済

        Args:
            exit_price: 決済価格
            exit_time: 決済時刻

        Raises:
            ValueError: 既に決済済みの場合
        """
        if not self.is_open:
            raise ValueError("このポジションは既に決済済みです")

        self.is_open = False
        self.exit_price = exit_price
        self.exit_time = exit_time

        # 実現損益を計算
        self.realized_pnl = self.calculate_unrealized_pnl(exit_price)

    def should_exit_profit(self, current_price: float) -> bool:
        """
        利確目標に到達したか判定

        Args:
            current_price: 現在価格

        Returns:
            True: 利確目標到達、False: 未到達
        """
        if self.profit_target is None:
            return False

        if self.side == 'long':
            # ロング: エントリー価格から+X%上昇
            target_price = self.entry_price * (1 + self.profit_target)
            return current_price >= target_price
        else:  # short
            # ショート: エントリー価格から-X%下落
            target_price = self.entry_price * (1 - self.profit_target)
            return current_price <= target_price

    def should_exit_loss(self, current_price: float) -> bool:
        """
        損切りラインに到達したか判定

        Args:
            current_price: 現在価格

        Returns:
            True: 損切りライン到達、False: 未到達
        """
        if self.stop_loss is None:
            return False

        if self.side == 'long':
            # ロング: エントリー価格から-X%下落
            stop_price = self.entry_price * (1 - self.stop_loss)
            return current_price <= stop_price
        else:  # short
            # ショート: エントリー価格から+X%上昇
            stop_price = self.entry_price * (1 + self.stop_loss)
            return current_price >= stop_price

    def get_duration(self):
        """
        ポジション保有時間を取得

        Returns:
            timedelta: 保有時間
        """
        if self.exit_time is None:
            return None

        return self.exit_time - self.entry_time
