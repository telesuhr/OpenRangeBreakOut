"""
取引コスト計算のテスト

TDDプロセス:
1. このテストを実行 → 失敗を確認
2. 最小限の実装でテストをパス
3. リファクタリング
"""
import pytest
from src.utils.cost_calculator import CostCalculator


class TestCostCalculator:
    """取引コスト計算機のテスト"""

    def test_calculate_commission_buy(self):
        """買い注文の手数料計算"""
        calculator = CostCalculator(commission_rate=0.001)  # 0.1%

        # 100万円の買い注文
        cost = calculator.calculate_commission(
            price=1000,
            quantity=1000,
            side='buy'
        )

        # 期待値: 1000 * 1000 * 0.001 = 1,000円
        assert cost == 1000

    def test_calculate_commission_sell(self):
        """売り注文の手数料計算"""
        calculator = CostCalculator(commission_rate=0.001)

        # 200万円の売り注文
        cost = calculator.calculate_commission(
            price=2000,
            quantity=1000,
            side='sell'
        )

        # 期待値: 2000 * 1000 * 0.001 = 2,000円
        assert cost == 2000

    def test_calculate_roundtrip_cost(self):
        """往復（買い→売り）の総コスト計算"""
        calculator = CostCalculator(commission_rate=0.001)

        # エントリー: 100万円
        # エグジット: 102万円（+2%利確）
        total_cost = calculator.calculate_roundtrip_cost(
            entry_price=1000,
            exit_price=1020,
            quantity=1000
        )

        # 期待値:
        # - 買い手数料: 1000 * 1000 * 0.001 = 1,000円
        # - 売り手数料: 1020 * 1000 * 0.001 = 1,020円
        # - 合計: 2,020円
        assert total_cost == 2020

    def test_calculate_net_profit_with_profit(self):
        """利益が出た場合の手数料控除後損益"""
        calculator = CostCalculator(commission_rate=0.001)

        net_profit = calculator.calculate_net_profit(
            entry_price=1000,
            exit_price=1020,  # +2%
            quantity=1000
        )

        # 期待値:
        # - 総利益: (1020 - 1000) * 1000 = 20,000円
        # - 手数料: 2,020円
        # - 純利益: 20,000 - 2,020 = 17,980円
        assert net_profit == 17980

    def test_calculate_net_profit_with_loss(self):
        """損失が出た場合の手数料控除後損益"""
        calculator = CostCalculator(commission_rate=0.001)

        net_profit = calculator.calculate_net_profit(
            entry_price=1000,
            exit_price=990,  # -1%
            quantity=1000
        )

        # 期待値:
        # - 総損失: (990 - 1000) * 1000 = -10,000円
        # - 手数料: 1,000 + 990 = 1,990円
        # - 純損失: -10,000 - 1,990 = -11,990円
        assert net_profit == -11990

    def test_calculate_short_position_profit(self):
        """ショートポジションの損益計算"""
        calculator = CostCalculator(commission_rate=0.001)

        # ショート: 1000円で売り → 980円で買い戻し（+2%利益）
        net_profit = calculator.calculate_net_profit(
            entry_price=1000,
            exit_price=980,
            quantity=1000,
            side='short'
        )

        # 期待値:
        # - 総利益: (1000 - 980) * 1000 = 20,000円
        # - 手数料: 1,000 + 980 = 1,980円
        # - 純利益: 20,000 - 1,980 = 18,020円
        assert net_profit == 18020

    def test_calculate_short_position_loss(self):
        """ショートポジションの損失計算"""
        calculator = CostCalculator(commission_rate=0.001)

        # ショート: 1000円で売り → 1010円で買い戻し（-1%損失）
        net_profit = calculator.calculate_net_profit(
            entry_price=1000,
            exit_price=1010,
            quantity=1000,
            side='short'
        )

        # 期待値:
        # - 総損失: (1000 - 1010) * 1000 = -10,000円
        # - 手数料: 1,000 + 1,010 = 2,010円
        # - 純損失: -10,000 - 2,010 = -12,010円
        assert net_profit == -12010

    def test_zero_commission_rate(self):
        """手数料ゼロの場合"""
        calculator = CostCalculator(commission_rate=0.0)

        net_profit = calculator.calculate_net_profit(
            entry_price=1000,
            exit_price=1020,
            quantity=1000
        )

        # 手数料なし、純粋な損益のみ
        assert net_profit == 20000

    def test_invalid_commission_rate(self):
        """不正な手数料率の場合はエラー"""
        with pytest.raises(ValueError):
            CostCalculator(commission_rate=-0.001)

        with pytest.raises(ValueError):
            CostCalculator(commission_rate=1.1)  # 110%はありえない

    def test_zero_quantity(self):
        """数量ゼロの場合"""
        calculator = CostCalculator(commission_rate=0.001)

        cost = calculator.calculate_commission(
            price=1000,
            quantity=0,
            side='buy'
        )

        assert cost == 0
