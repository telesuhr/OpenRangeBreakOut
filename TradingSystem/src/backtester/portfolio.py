"""
ポートフォリオ管理モジュール

複数ポジションの管理、資金管理を行う
"""
from typing import List, Dict, Optional
from src.backtester.position import Position


class Portfolio:
    """ポートフォリオクラス"""

    def __init__(
        self,
        initial_capital: float,
        position_sizing: str = 'equal'
    ):
        """
        Args:
            initial_capital: 初期資金（円）
            position_sizing: ポジションサイジング方法
                - 'equal': 均等配分
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position_sizing = position_sizing

        self.open_positions: List[Position] = []
        self.closed_positions: List[Position] = []

    def add_position(self, position: Position):
        """
        ポジションを追加

        Args:
            position: 追加するポジション

        Raises:
            ValueError: 現金不足の場合
        """
        required_cash = position.entry_price * position.quantity

        if not self.has_sufficient_cash(required_cash):
            raise ValueError(
                f"現金不足です: 必要額={required_cash:,.0f}円, "
                f"利用可能={self.cash:,.0f}円"
            )

        self.open_positions.append(position)
        self.cash -= required_cash

    def close_position(self, position: Position, exit_price: float, exit_time):
        """
        ポジションを決済

        Args:
            position: 決済するポジション
            exit_price: 決済価格
            exit_time: 決済時刻
        """
        position.close(exit_price, exit_time)

        # 現金を返却：元本 + 損益
        initial_cash = position.entry_price * position.quantity
        pnl = position.realized_pnl
        self.cash += (initial_cash + pnl)

        # オープンポジションから削除し、クローズドポジションに追加
        if position in self.open_positions:
            self.open_positions.remove(position)

        self.closed_positions.append(position)

    def calculate_position_size(
        self,
        price: float,
        num_positions: int
    ) -> int:
        """
        ポジションサイズ（数量）を計算

        Args:
            price: エントリー価格
            num_positions: 同時に保有する予定のポジション数

        Returns:
            購入数量
        """
        if self.position_sizing == 'equal':
            # 均等配分: 利用可能資金をnum_positionsで割る
            capital_per_position = self.cash / num_positions
            quantity = int(capital_per_position / price)
            return quantity

        # デフォルトは均等配分
        return int(self.cash / num_positions / price)

    def get_total_value(self, current_prices: Optional[Dict[str, float]] = None) -> float:
        """
        ポートフォリオの総資産価値を取得

        Args:
            current_prices: 銘柄コード -> 現在価格の辞書

        Returns:
            総資産価値（円）
        """
        total = self.cash

        if current_prices is not None:
            for position in self.open_positions:
                if position.symbol in current_prices:
                    current_price = current_prices[position.symbol]
                    position_value = current_price * position.quantity
                    total += position_value

        return total

    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """
        未実現損益の合計を取得

        Args:
            current_prices: 銘柄コード -> 現在価格の辞書

        Returns:
            未実現損益（円）
        """
        total_unrealized = 0

        for position in self.open_positions:
            if position.symbol in current_prices:
                current_price = current_prices[position.symbol]
                unrealized_pnl = position.calculate_unrealized_pnl(current_price)
                total_unrealized += unrealized_pnl

        return total_unrealized

    def get_realized_pnl(self) -> float:
        """
        実現損益の合計を取得

        Returns:
            実現損益（円）
        """
        total_realized = sum(
            pos.realized_pnl for pos in self.closed_positions
            if pos.realized_pnl is not None
        )

        return total_realized

    def get_total_pnl(self, current_prices: Optional[Dict[str, float]] = None) -> float:
        """
        総損益（実現 + 未実現）を取得

        Args:
            current_prices: 銘柄コード -> 現在価格の辞書

        Returns:
            総損益（円）
        """
        realized = self.get_realized_pnl()
        unrealized = 0

        if current_prices is not None:
            unrealized = self.get_unrealized_pnl(current_prices)

        return realized + unrealized

    def has_sufficient_cash(self, required_amount: float) -> bool:
        """
        十分な現金があるかチェック

        Args:
            required_amount: 必要金額

        Returns:
            True: 十分な現金あり、False: 不足
        """
        return self.cash >= required_amount

    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """
        銘柄コードからオープンポジションを取得

        Args:
            symbol: 銘柄コード

        Returns:
            見つかった場合はPosition、見つからなければNone
        """
        for position in self.open_positions:
            if position.symbol == symbol:
                return position

        return None

    def get_open_position_count(self) -> int:
        """
        オープンポジション数を取得

        Returns:
            オープンポジション数
        """
        return len(self.open_positions)

    def get_win_rate(self) -> float:
        """
        勝率を計算

        Returns:
            勝率（0.0-1.0）
        """
        if not self.closed_positions:
            return 0.0

        win_count = sum(
            1 for pos in self.closed_positions
            if pos.realized_pnl is not None and pos.realized_pnl > 0
        )

        return win_count / len(self.closed_positions)
