"""
ポジション管理のテスト

TDDプロセス:
1. このテストを実行 → 失敗を確認
2. 最小限の実装でテストをパス
3. リファクタリング
"""
import pytest
from datetime import datetime
from src.backtester.position import Position


class TestPosition:
    """ポジションクラスのテスト"""

    def test_create_long_position(self):
        """ロングポジションの作成"""
        position = Position(
            symbol='7203.T',  # トヨタ自動車
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        assert position.symbol == '7203.T'
        assert position.side == 'long'
        assert position.entry_price == 1000
        assert position.quantity == 100
        assert position.is_open is True
        assert position.exit_price is None

    def test_create_short_position(self):
        """ショートポジションの作成"""
        position = Position(
            symbol='9984.T',  # ソフトバンクグループ
            side='short',
            entry_price=2000,
            quantity=50,
            entry_time=datetime(2025, 1, 6, 9, 25)
        )

        assert position.side == 'short'
        assert position.entry_price == 2000
        assert position.quantity == 50

    def test_calculate_unrealized_pnl_long_profit(self):
        """ロングポジションの含み益計算"""
        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        # 現在価格1020円（+2%）での含み損益
        unrealized_pnl = position.calculate_unrealized_pnl(current_price=1020)

        # 期待値: (1020 - 1000) * 100 = 2,000円
        assert unrealized_pnl == 2000

    def test_calculate_unrealized_pnl_long_loss(self):
        """ロングポジションの含み損計算"""
        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        # 現在価格990円（-1%）での含み損益
        unrealized_pnl = position.calculate_unrealized_pnl(current_price=990)

        # 期待値: (990 - 1000) * 100 = -1,000円
        assert unrealized_pnl == -1000

    def test_calculate_unrealized_pnl_short_profit(self):
        """ショートポジションの含み益計算"""
        position = Position(
            symbol='9984.T',
            side='short',
            entry_price=2000,
            quantity=50,
            entry_time=datetime(2025, 1, 6, 9, 25)
        )

        # 現在価格1960円（-2%）での含み損益
        unrealized_pnl = position.calculate_unrealized_pnl(current_price=1960)

        # 期待値: (2000 - 1960) * 50 = 2,000円
        assert unrealized_pnl == 2000

    def test_calculate_unrealized_pnl_short_loss(self):
        """ショートポジションの含み損計算"""
        position = Position(
            symbol='9984.T',
            side='short',
            entry_price=2000,
            quantity=50,
            entry_time=datetime(2025, 1, 6, 9, 25)
        )

        # 現在価格2020円（+1%）での含み損益
        unrealized_pnl = position.calculate_unrealized_pnl(current_price=2020)

        # 期待値: (2000 - 2020) * 50 = -1,000円
        assert unrealized_pnl == -1000

    def test_close_position_with_profit(self):
        """利益確定での決済"""
        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        # 1020円で決済（+2%利確）
        position.close(
            exit_price=1020,
            exit_time=datetime(2025, 1, 6, 9, 45)
        )

        assert position.is_open is False
        assert position.exit_price == 1020
        assert position.exit_time == datetime(2025, 1, 6, 9, 45)
        assert position.realized_pnl == 2000

    def test_close_position_with_loss(self):
        """損切りでの決済"""
        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        # 990円で決済（-1%損切り）
        position.close(
            exit_price=990,
            exit_time=datetime(2025, 1, 6, 9, 35)
        )

        assert position.is_open is False
        assert position.realized_pnl == -1000

    def test_check_profit_target_reached(self):
        """利確目標到達の判定"""
        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20),
            profit_target=0.02  # +2%
        )

        # 1020円で+2%到達
        assert position.should_exit_profit(current_price=1020) is True

        # 1019円ではまだ未到達
        assert position.should_exit_profit(current_price=1019) is False

    def test_check_stop_loss_reached(self):
        """損切りライン到達の判定"""
        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20),
            stop_loss=0.01  # -1%
        )

        # 990円で-1%到達
        assert position.should_exit_loss(current_price=990) is True

        # 991円ではまだ未到達
        assert position.should_exit_loss(current_price=991) is False

    def test_check_profit_target_reached_short(self):
        """ショートポジションの利確判定"""
        position = Position(
            symbol='9984.T',
            side='short',
            entry_price=2000,
            quantity=50,
            entry_time=datetime(2025, 1, 6, 9, 25),
            profit_target=0.02  # +2%
        )

        # 1960円で+2%到達（エントリーより40円下落）
        assert position.should_exit_profit(current_price=1960) is True

        # 1961円ではまだ未到達
        assert position.should_exit_profit(current_price=1961) is False

    def test_check_stop_loss_reached_short(self):
        """ショートポジションの損切り判定"""
        position = Position(
            symbol='9984.T',
            side='short',
            entry_price=2000,
            quantity=50,
            entry_time=datetime(2025, 1, 6, 9, 25),
            stop_loss=0.01  # -1%
        )

        # 2020円で-1%到達（エントリーより20円上昇）
        assert position.should_exit_loss(current_price=2020) is True

        # 2019円ではまだ未到達
        assert position.should_exit_loss(current_price=2019) is False

    def test_cannot_close_already_closed_position(self):
        """既に決済済みのポジションは再度決済できない"""
        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        # 1度目の決済
        position.close(exit_price=1020, exit_time=datetime(2025, 1, 6, 9, 45))

        # 2度目の決済はエラー
        with pytest.raises(ValueError, match="既に決済済み"):
            position.close(exit_price=1030, exit_time=datetime(2025, 1, 6, 10, 0))

    def test_position_duration(self):
        """ポジション保有時間の計算"""
        position = Position(
            symbol='7203.T',
            side='long',
            entry_price=1000,
            quantity=100,
            entry_time=datetime(2025, 1, 6, 9, 20)
        )

        position.close(
            exit_price=1020,
            exit_time=datetime(2025, 1, 6, 9, 50)
        )

        # 30分間保有
        duration = position.get_duration()
        assert duration.total_seconds() == 30 * 60

    def test_invalid_side(self):
        """不正なサイド指定"""
        with pytest.raises(ValueError, match="side は 'long' または 'short'"):
            Position(
                symbol='7203.T',
                side='buy',  # 不正な値
                entry_price=1000,
                quantity=100,
                entry_time=datetime(2025, 1, 6, 9, 20)
            )

    def test_negative_quantity(self):
        """負の数量"""
        with pytest.raises(ValueError, match="数量は正の値"):
            Position(
                symbol='7203.T',
                side='long',
                entry_price=1000,
                quantity=-100,
                entry_time=datetime(2025, 1, 6, 9, 20)
            )

    def test_negative_price(self):
        """負の価格"""
        with pytest.raises(ValueError, match="価格は正の値"):
            Position(
                symbol='7203.T',
                side='long',
                entry_price=-1000,
                quantity=100,
                entry_time=datetime(2025, 1, 6, 9, 20)
            )
