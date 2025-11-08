"""
パフォーマンス評価モジュール

バックテスト結果の分析・評価を行う
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional


class PerformanceAnalyzer:
    """パフォーマンス分析クラス"""

    def __init__(
        self,
        initial_capital: float,
        trades: List[Dict],
        equity_curve: Optional[pd.Series] = None,
        daily_returns: Optional[pd.Series] = None
    ):
        """
        Args:
            initial_capital: 初期資金
            trades: 取引履歴のリスト
            equity_curve: 資産曲線（時系列）
            daily_returns: 日次リターン
        """
        self.initial_capital = initial_capital
        self.trades = trades
        self.equity_curve = equity_curve
        self.daily_returns = daily_returns

    def calculate_total_return(self) -> float:
        """
        総リターンを計算

        Returns:
            総リターン（比率）
        """
        if not self.trades:
            return 0.0

        total_pnl = sum(trade['pnl'] for trade in self.trades)
        return total_pnl / self.initial_capital

    def calculate_win_rate(self) -> float:
        """
        勝率を計算

        Returns:
            勝率（0.0-1.0）
        """
        if not self.trades:
            return 0.0

        winning_trades = sum(1 for trade in self.trades if trade['pnl'] > 0)
        return winning_trades / len(self.trades)

    def calculate_profit_factor(self) -> float:
        """
        プロフィットファクターを計算

        Returns:
            プロフィットファクター（総利益 / 総損失）
        """
        if not self.trades:
            return 0.0

        total_profit = sum(trade['pnl'] for trade in self.trades if trade['pnl'] > 0)
        total_loss = abs(sum(trade['pnl'] for trade in self.trades if trade['pnl'] < 0))

        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0

        return total_profit / total_loss

    def calculate_max_drawdown(self) -> tuple[float, float]:
        """
        最大ドローダウンを計算

        Returns:
            (max_dd, max_dd_pct): 最大ドローダウン（円）と割合
        """
        if self.equity_curve is None or self.equity_curve.empty:
            return 0.0, 0.0

        # ピークを記録
        peak = self.equity_curve.expanding().max()

        # ドローダウンを計算
        drawdown = peak - self.equity_curve
        max_dd = drawdown.max()

        # ドローダウン率
        max_dd_pct = (drawdown / peak).max()

        return max_dd, max_dd_pct

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        シャープレシオを計算

        Args:
            risk_free_rate: リスクフリーレート（日次）

        Returns:
            シャープレシオ（年率換算）
        """
        if self.daily_returns is None or self.daily_returns.empty:
            return 0.0

        # 平均リターン
        mean_return = self.daily_returns.mean()

        # 標準偏差
        std_return = self.daily_returns.std()

        if std_return == 0:
            return 0.0

        # シャープレシオ（年率換算: √252倍）
        sharpe = (mean_return - risk_free_rate) / std_return
        return sharpe * np.sqrt(252)

    def calculate_average_pnl(self) -> float:
        """
        平均損益を計算

        Returns:
            平均損益（円）
        """
        if not self.trades:
            return 0.0

        return sum(trade['pnl'] for trade in self.trades) / len(self.trades)

    def calculate_average_win_pnl(self) -> float:
        """
        平均利益を計算（勝ちトレードのみ）

        Returns:
            平均利益（円）
        """
        winning_trades = [trade['pnl'] for trade in self.trades if trade['pnl'] > 0]

        if not winning_trades:
            return 0.0

        return sum(winning_trades) / len(winning_trades)

    def calculate_average_loss_pnl(self) -> float:
        """
        平均損失を計算（負けトレードのみ）

        Returns:
            平均損失（円）
        """
        losing_trades = [trade['pnl'] for trade in self.trades if trade['pnl'] < 0]

        if not losing_trades:
            return 0.0

        return sum(losing_trades) / len(losing_trades)

    def calculate_monthly_returns(self) -> pd.Series:
        """
        月次リターンを計算

        Returns:
            月次リターンのSeries
        """
        if self.equity_curve is None or self.equity_curve.empty:
            return pd.Series()

        # 月次でリサンプリング
        monthly = self.equity_curve.resample('ME').last()

        # 月次リターンを計算
        monthly_returns = monthly.pct_change().dropna()

        return monthly_returns

    def get_trade_count(self) -> int:
        """
        取引回数を取得

        Returns:
            取引回数
        """
        return len(self.trades)

    def get_win_count(self) -> int:
        """
        勝ちトレード数を取得

        Returns:
            勝ちトレード数
        """
        return sum(1 for trade in self.trades if trade['pnl'] > 0)

    def get_loss_count(self) -> int:
        """
        負けトレード数を取得

        Returns:
            負けトレード数
        """
        return sum(1 for trade in self.trades if trade['pnl'] < 0)

    def calculate_risk_reward_ratio(self) -> float:
        """
        リスクリワードレシオを計算

        Returns:
            リスクリワードレシオ（平均利益 / 平均損失の絶対値）
        """
        avg_win = self.calculate_average_win_pnl()
        avg_loss = abs(self.calculate_average_loss_pnl())

        if avg_loss == 0:
            return 0.0

        return avg_win / avg_loss

    def generate_summary_report(self) -> Dict:
        """
        サマリーレポートを生成

        Returns:
            パフォーマンス指標を含む辞書
        """
        max_dd, max_dd_pct = self.calculate_max_drawdown()

        return {
            'total_return': self.calculate_total_return(),
            'win_rate': self.calculate_win_rate(),
            'profit_factor': self.calculate_profit_factor(),
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'sharpe_ratio': self.calculate_sharpe_ratio(),
            'total_trades': self.get_trade_count(),
            'win_count': self.get_win_count(),
            'loss_count': self.get_loss_count(),
            'avg_pnl': self.calculate_average_pnl(),
            'avg_win': self.calculate_average_win_pnl(),
            'avg_loss': self.calculate_average_loss_pnl(),
            'risk_reward_ratio': self.calculate_risk_reward_ratio()
        }
