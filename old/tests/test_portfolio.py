"""
ポートフォリオ管理のテスト

TDDプロセス:
1. このテストを実行 → 失敗を確認
2. 最小限の実装でテストをパス
3. リファクタリング
"""
import pytest
from datetime import datetime
from src.backtester.portfolio import Portfolio
from src.backtester.position import Position


class TestPortfolio:
    """ポートフォリオクラスのテスト"""

    def test_create_portfolio(self):
        """ポートフォリオの初期化"""
        portfolio = Portfolio(initial_capital=10000000)

        assert portfolio.initial_capital == 10000000
        assert portfolio.cash == 10000000
        assert portfolio.get_total_value() == 10000000
        assert len(portfolio.open_positions) == 0

    def test_add_position(self):
        """ポジションの追加"""
        portfolio = Portfolio(initial_capital=10000000)

        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        portfolio.add_position(position)

        assert len(portfolio.open_positions) == 1
        assert portfolio.cash == 10000000 - (1000 * 100)

    def test_calculate_position_size_equal(self):
        """均等配分でのポジションサイズ計算"""
        portfolio = Portfolio(
            initial_capital=10000000,
            position_sizing='equal'
        )

        # 10銘柄同時エントリーを想定
        # 1銘柄あたり: 10,000,000 / 10 = 1,000,000円
        position_size = portfolio.calculate_position_size(
            price=1000,
            num_positions=10
        )

        # 期待値: 1,000,000 / 1000 = 1,000株
        assert position_size == 1000

    def test_calculate_position_size_available_cash(self):
        """利用可能資金でのポジションサイズ計算"""
        portfolio = Portfolio(initial_capital=10000000)

        # 既に500万円使用済み（残り500万円）
        portfolio.cash = 5000000

        # 残り5銘柄エントリー予定
        position_size = portfolio.calculate_position_size(
            price=1000,
            num_positions=5
        )

        # 期待値: 5,000,000 / 5 / 1000 = 1,000株
        assert position_size == 1000

    def test_get_total_value_with_positions(self):
        """ポジション保有時の総資産評価"""
        portfolio = Portfolio(initial_capital=10000000)

        # ポジション1: 100万円 → 102万円（+2万円）
        pos1 = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        # ポジション2: 200万円 → 196万円（-4万円）
        pos2 = Position(
            symbol='9984.T',
            side='long',
            entry_price=2000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 25)
        )

        portfolio.add_position(pos1)
        portfolio.add_position(pos2)

        # 現在価格での評価
        current_prices = {
            '7203.T': 1020,  # +2%
            '9984.T': 1960   # -2%
        }

        total_value = portfolio.get_total_value(current_prices)

        # 期待値:
        # - 残り現金: 10,000,000 - 1,000,000 - 2,000,000 = 7,000,000
        # - ポジション1評価: 1020 * 1000 = 1,020,000
        # - ポジション2評価: 1960 * 1000 = 1,960,000
        # - 合計: 7,000,000 + 1,020,000 + 1,960,000 = 9,980,000
        assert total_value == 9980000

    def test_close_position(self):
        """ポジションの決済"""
        portfolio = Portfolio(initial_capital=10000000)

        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        portfolio.add_position(position)

        # 1020円で決済（+2万円の利益）
        portfolio.close_position(
            position,
            exit_price=1020,
            exit_time=datetime(2025, 1, 6, 9, 45)
        )

        # 期待値:
        # - 元の現金: 10,000,000 - 1,000,000 = 9,000,000
        # - 決済後: 9,000,000 + 1,020,000 = 10,020,000
        assert portfolio.cash == 10020000
        assert len(portfolio.open_positions) == 0
        assert len(portfolio.closed_positions) == 1

    def test_get_unrealized_pnl(self):
        """未実現損益の計算"""
        portfolio = Portfolio(initial_capital=10000000)

        pos1 = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        pos2 = Position(
            symbol='9984.T',
            side='long',
            entry_price=2000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 25)
        )

        portfolio.add_position(pos1)
        portfolio.add_position(pos2)

        current_prices = {
            '7203.T': 1020,  # +20円 * 1000株 = +20,000円
            '9984.T': 1960   # -40円 * 1000株 = -40,000円
        }

        unrealized_pnl = portfolio.get_unrealized_pnl(current_prices)

        # 期待値: +20,000 - 40,000 = -20,000円
        assert unrealized_pnl == -20000

    def test_get_realized_pnl(self):
        """実現損益の計算"""
        portfolio = Portfolio(initial_capital=10000000)

        # ポジション1: +20,000円で決済
        pos1 = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )
        portfolio.add_position(pos1)
        portfolio.close_position(pos1, 1020, datetime(2025, 1, 6, 9, 45))

        # ポジション2: -10,000円で決済
        pos2 = Position(
            symbol='9984.T',
            side='long',
            entry_price=2000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 25)
        )
        portfolio.add_position(pos2)
        portfolio.close_position(pos2, 1990, datetime(2025, 1, 6, 9, 50))

        realized_pnl = portfolio.get_realized_pnl()

        # 期待値: +20,000 - 10,000 = +10,000円
        assert realized_pnl == 10000

    def test_get_total_pnl(self):
        """総損益（実現 + 未実現）の計算"""
        portfolio = Portfolio(initial_capital=10000000)

        # 決済済み: +20,000円
        pos1 = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )
        portfolio.add_position(pos1)
        portfolio.close_position(pos1, 1020, datetime(2025, 1, 6, 9, 45))

        # 未決済: -10,000円
        pos2 = Position(
            symbol='9984.T',
            side='long',
            entry_price=2000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 25)
        )
        portfolio.add_position(pos2)

        current_prices = {'9984.T': 1990}
        total_pnl = portfolio.get_total_pnl(current_prices)

        # 期待値: +20,000 - 10,000 = +10,000円
        assert total_pnl == 10000

    def test_has_sufficient_cash(self):
        """十分な現金があるかチェック"""
        portfolio = Portfolio(initial_capital=10000000)

        # 100万円の注文
        assert portfolio.has_sufficient_cash(1000000) is True

        # 1000万円の注文（ギリギリOK）
        assert portfolio.has_sufficient_cash(10000000) is True

        # 1001万円の注文（NG）
        assert portfolio.has_sufficient_cash(10010000) is False

    def test_get_position_by_symbol(self):
        """銘柄コードでポジション取得"""
        portfolio = Portfolio(initial_capital=10000000)

        pos = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=1000,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )
        portfolio.add_position(pos)

        retrieved_pos = portfolio.get_position_by_symbol('7203.T')

        assert retrieved_pos is not None
        assert retrieved_pos.symbol == '7203.T'

        # 存在しない銘柄
        assert portfolio.get_position_by_symbol('9999.T') is None

    def test_get_open_position_count(self):
        """オープンポジション数の取得"""
        portfolio = Portfolio(initial_capital=10000000)

        assert portfolio.get_open_position_count() == 0

        # 3ポジション追加
        for i, symbol in enumerate(['7203.T', '9984.T', '6758.T']):
            pos = Position(
                symbol=symbol,
                side='long',
                entry_price=1000,
                quantity=100,
                entry_time=datetime(2025, 1, 6, 9, 20 + i)
            )
            portfolio.add_position(pos)

        assert portfolio.get_open_position_count() == 3

        # 1つ決済
        portfolio.close_position(
            portfolio.open_positions[0],
            1020,
            datetime(2025, 1, 6, 9, 45)
        )

        assert portfolio.get_open_position_count() == 2

    def test_get_win_rate(self):
        """勝率の計算"""
        portfolio = Portfolio(initial_capital=10000000)

        # 勝ち: 2回
        for i in range(2):
            pos = Position(
                symbol=f'WIN{i}.T',
                side='long',
                entry_price=1000,
                quantity=100,
                entry_time=datetime(2025, 1, 6, 9, 20)
            )
            portfolio.add_position(pos)
            portfolio.close_position(pos, 1020, datetime(2025, 1, 6, 9, 45))

        # 負け: 1回
        pos = Position(
            symbol='LOSS.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )
        portfolio.add_position(pos)
        portfolio.close_position(pos, 990, datetime(2025, 1, 6, 9, 45))

        win_rate = portfolio.get_win_rate()

        # 期待値: 2/3 = 0.6666...
        assert abs(win_rate - 0.6667) < 0.0001

    def test_insufficient_cash_error(self):
        """現金不足時のエラー"""
        portfolio = Portfolio(initial_capital=1000000)  # 100万円

        # 200万円のポジション追加（現金不足）
        pos = Position(
            symbol='7203.T',
            side='long',
            entry_price=2000,
            quantity=1000,  # 2000 * 1000 = 200万円
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        with pytest.raises(ValueError, match="現金不足"):
            portfolio.add_position(pos)
