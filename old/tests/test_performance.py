"""
パフォーマンス評価のテスト

TDDプロセス:
1. このテストを実行 → 失敗を確認
2. 最小限の実装でテストをパス
3. リファクタリング
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.analysis.performance import PerformanceAnalyzer


class TestPerformanceAnalyzer:
    """パフォーマンス分析のテスト"""

    @pytest.fixture
    def sample_trades(self):
        """テスト用の取引履歴"""
        return [
            {
                'entry_time': datetime(2025, 1, 6, 9, 20),
                'exit_time': datetime(2025, 1, 6, 10, 30),
                'symbol': '7203.T',
                'side': 'long',
                'entry_price': 1000,
                'exit_price': 1020,
                'quantity': 1000,
                'pnl': 20000,
                'pnl_pct': 0.02
            },
            {
                'entry_time': datetime(2025, 1, 6, 9, 25),
                'exit_time': datetime(2025, 1, 6, 11, 0),
                'symbol': '9984.T',
                'side': 'long',
                'entry_price': 2000,
                'exit_price': 1980,
                'quantity': 500,
                'pnl': -10000,
                'pnl_pct': -0.01
            },
            {
                'entry_time': datetime(2025, 1, 7, 9, 30),
                'exit_time': datetime(2025, 1, 7, 14, 0),
                'symbol': '6758.T',
                'side': 'short',
                'entry_price': 5000,
                'exit_price': 4900,
                'quantity': 200,
                'pnl': 20000,
                'pnl_pct': 0.02
            },
        ]

    @pytest.fixture
    def equity_curve(self):
        """テスト用の資産曲線"""
        dates = pd.date_range('2025-01-06', periods=10, freq='D')
        equity = [10000000, 10020000, 10010000, 10050000, 10030000,
                  10080000, 10060000, 10100000, 10090000, 10120000]
        return pd.Series(equity, index=dates)

    def test_calculate_total_return(self, sample_trades):
        """総リターンの計算"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        total_return = analyzer.calculate_total_return()

        # 期待値: (20,000 - 10,000 + 20,000) / 10,000,000 = 0.003 (0.3%)
        assert abs(total_return - 0.003) < 0.0001

    def test_calculate_win_rate(self, sample_trades):
        """勝率の計算"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        win_rate = analyzer.calculate_win_rate()

        # 期待値: 2勝1敗 = 2/3 = 0.6667
        assert abs(win_rate - 0.6667) < 0.0001

    def test_calculate_profit_factor(self, sample_trades):
        """プロフィットファクターの計算"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        profit_factor = analyzer.calculate_profit_factor()

        # 期待値:
        # - 総利益: 20,000 + 20,000 = 40,000
        # - 総損失: 10,000
        # - PF: 40,000 / 10,000 = 4.0
        assert profit_factor == 4.0

    def test_calculate_max_drawdown(self, equity_curve):
        """最大ドローダウンの計算"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=[],
            equity_curve=equity_curve
        )

        max_dd, max_dd_pct = analyzer.calculate_max_drawdown()

        # equity_curveの最大ドローダウン:
        # ピーク: 10,050,000 (index 3) → 谷: 10,030,000 (index 4) = 20,000円
        # ピーク: 10,080,000 (index 5) → 谷: 10,060,000 (index 6) = 20,000円
        # → 最大DD: 20,000円、約0.198%
        assert max_dd == 20000
        assert abs(max_dd_pct - 0.00198) < 0.0001

    def test_calculate_sharpe_ratio(self):
        """シャープレシオの計算"""
        # 日次リターンのサンプル
        daily_returns = pd.Series([
            0.002, -0.001, 0.004, -0.002, 0.005,
            -0.002, 0.004, -0.001, 0.003, 0.002
        ])

        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=[],
            daily_returns=daily_returns
        )

        sharpe = analyzer.calculate_sharpe_ratio(risk_free_rate=0.001)

        # 期待値:
        # - 平均リターン: 0.0014
        # - 標準偏差: 0.00234...
        # - シャープレシオ: (0.0014 - 0.001) / 0.00234 ≈ 0.171
        # ※年率換算（√252倍）
        assert sharpe > 0  # 正の値であることを確認

    def test_calculate_average_pnl(self, sample_trades):
        """平均損益の計算"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        avg_pnl = analyzer.calculate_average_pnl()

        # 期待値: (20,000 - 10,000 + 20,000) / 3 = 10,000円
        assert avg_pnl == 10000

    def test_calculate_average_win_pnl(self, sample_trades):
        """平均利益の計算"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        avg_win = analyzer.calculate_average_win_pnl()

        # 期待値: (20,000 + 20,000) / 2 = 20,000円
        assert avg_win == 20000

    def test_calculate_average_loss_pnl(self, sample_trades):
        """平均損失の計算"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        avg_loss = analyzer.calculate_average_loss_pnl()

        # 期待値: -10,000円
        assert avg_loss == -10000

    def test_calculate_monthly_returns(self):
        """月次リターンの計算"""
        # 3ヶ月分のデータ
        dates = pd.date_range('2025-01-01', '2025-03-31', freq='D')
        equity = 10000000 * (1 + np.random.randn(len(dates)) * 0.01).cumprod()
        equity_curve = pd.Series(equity, index=dates)

        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=[],
            equity_curve=equity_curve
        )

        monthly_returns = analyzer.calculate_monthly_returns()

        # 3ヶ月分のデータだが、pct_change()で最初の月はNaNになるため2ヶ月分のリターン
        assert len(monthly_returns) == 2
        assert all(isinstance(r, (float, np.floating)) for r in monthly_returns.values)

    def test_get_trade_count(self, sample_trades):
        """取引回数の取得"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        assert analyzer.get_trade_count() == 3

    def test_get_win_count(self, sample_trades):
        """勝ちトレード数の取得"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        assert analyzer.get_win_count() == 2

    def test_get_loss_count(self, sample_trades):
        """負けトレード数の取得"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        assert analyzer.get_loss_count() == 1

    def test_calculate_risk_reward_ratio(self, sample_trades):
        """リスクリワードレシオの計算"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades
        )

        rr_ratio = analyzer.calculate_risk_reward_ratio()

        # 期待値:
        # - 平均利益: 20,000円
        # - 平均損失: 10,000円（絶対値）
        # - R/R: 20,000 / 10,000 = 2.0
        assert rr_ratio == 2.0

    def test_no_trades(self):
        """取引がない場合"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=[]
        )

        assert analyzer.calculate_total_return() == 0.0
        assert analyzer.calculate_win_rate() == 0.0
        assert analyzer.calculate_profit_factor() == 0.0
        assert analyzer.get_trade_count() == 0

    def test_only_winning_trades(self):
        """全勝の場合"""
        trades = [
            {
                'entry_time': datetime(2025, 1, 6, 9, 20),
                'exit_time': datetime(2025, 1, 6, 10, 30),
                'symbol': '7203.T',
                'side': 'long',
                'entry_price': 1000,
                'exit_price': 1020,
                'quantity': 1000,
                'pnl': 20000,
                'pnl_pct': 0.02
            },
            {
                'entry_time': datetime(2025, 1, 7, 9, 30),
                'exit_time': datetime(2025, 1, 7, 14, 0),
                'symbol': '6758.T',
                'side': 'long',
                'entry_price': 5000,
                'exit_price': 5100,
                'quantity': 200,
                'pnl': 20000,
                'pnl_pct': 0.02
            },
        ]

        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=trades
        )

        assert analyzer.calculate_win_rate() == 1.0
        # プロフィットファクターは無限大（損失ゼロ）
        assert analyzer.calculate_profit_factor() == float('inf')

    def test_only_losing_trades(self):
        """全敗の場合"""
        trades = [
            {
                'entry_time': datetime(2025, 1, 6, 9, 20),
                'exit_time': datetime(2025, 1, 6, 10, 30),
                'symbol': '7203.T',
                'side': 'long',
                'entry_price': 1000,
                'exit_price': 990,
                'quantity': 1000,
                'pnl': -10000,
                'pnl_pct': -0.01
            },
        ]

        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=trades
        )

        assert analyzer.calculate_win_rate() == 0.0
        assert analyzer.calculate_profit_factor() == 0.0

    def test_generate_summary_report(self, sample_trades, equity_curve):
        """サマリーレポートの生成"""
        analyzer = PerformanceAnalyzer(
            initial_capital=10000000,
            trades=sample_trades,
            equity_curve=equity_curve
        )

        report = analyzer.generate_summary_report()

        # 必要なキーが含まれているか確認
        required_keys = [
            'total_return',
            'win_rate',
            'profit_factor',
            'max_drawdown',
            'sharpe_ratio',
            'total_trades',
            'avg_pnl'
        ]

        for key in required_keys:
            assert key in report
