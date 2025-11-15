"""
レンジブレイクアウト判定ロジックのテスト

TDDプロセス:
1. このテストを実行 → 失敗を確認
2. 最小限の実装でテストをパス
3. リファクタリング
"""
import pytest
import pandas as pd
from datetime import datetime, time
from src.strategy.range_breakout import RangeBreakoutDetector


class TestRangeBreakoutDetector:
    """レンジブレイクアウト検出器のテスト"""

    @pytest.fixture
    def sample_data(self):
        """テスト用の分足データ"""
        data = pd.DataFrame({
            'datetime': pd.to_datetime([
                '2025-01-06 09:05:00',
                '2025-01-06 09:10:00',
                '2025-01-06 09:15:00',
                '2025-01-06 09:20:00',
                '2025-01-06 09:25:00',
                '2025-01-06 09:30:00',
            ]),
            'open': [1000, 1005, 1003, 1008, 1012, 1015],
            'high': [1008, 1010, 1007, 1015, 1018, 1020],
            'low': [998, 1002, 1000, 1006, 1010, 1013],
            'close': [1005, 1003, 1005, 1012, 1015, 1018],
            'volume': [10000, 8000, 9000, 12000, 15000, 11000]
        })
        data.set_index('datetime', inplace=True)
        return data

    def test_calculate_opening_range(self, sample_data):
        """09:05-09:15のレンジ計算"""
        detector = RangeBreakoutDetector(
            range_start=time(9, 5),
            range_end=time(9, 15)
        )

        range_high, range_low = detector.calculate_range(sample_data)

        # 期待値:
        # - 09:05の高値: 1008
        # - 09:10の高値: 1010
        # - 09:15の高値: 1007
        # → レンジ高値: 1010
        #
        # - 09:05の安値: 998
        # - 09:10の安値: 1002
        # - 09:15の安値: 1000
        # → レンジ安値: 998
        assert range_high == 1010
        assert range_low == 998

    def test_detect_upside_breakout(self, sample_data):
        """高値ブレイクアウトの検出"""
        detector = RangeBreakoutDetector(
            range_start=time(9, 5),
            range_end=time(9, 15)
        )

        # レンジ計算
        range_high, range_low = detector.calculate_range(sample_data)

        # 09:20のデータでブレイクアウト判定
        # 09:20の高値: 1015 > レンジ高値: 1010 → ブレイクアウト
        breakout_type = detector.detect_breakout(
            sample_data.loc['2025-01-06 09:20:00'],
            range_high,
            range_low
        )

        assert breakout_type == 'long'

    def test_detect_downside_breakout(self):
        """安値ブレイクアウトの検出"""
        # 下抜けするデータ
        data = pd.DataFrame({
            'datetime': pd.to_datetime([
                '2025-01-06 09:05:00',
                '2025-01-06 09:10:00',
                '2025-01-06 09:15:00',
                '2025-01-06 09:20:00',
            ]),
            'open': [1000, 1005, 1003, 995],
            'high': [1008, 1010, 1007, 998],
            'low': [998, 1002, 1000, 990],  # 09:20で990まで下落
            'close': [1005, 1003, 1005, 992],
            'volume': [10000, 8000, 9000, 12000]
        })
        data.set_index('datetime', inplace=True)

        detector = RangeBreakoutDetector(
            range_start=time(9, 5),
            range_end=time(9, 15)
        )

        range_high, range_low = detector.calculate_range(data)

        # レンジ安値: 998
        # 09:20の安値: 990 < 998 → 下抜けブレイクアウト
        breakout_type = detector.detect_breakout(
            data.loc['2025-01-06 09:20:00'],
            range_high,
            range_low
        )

        assert breakout_type == 'short'

    def test_no_breakout(self):
        """ブレイクアウトなしの場合"""
        data = pd.DataFrame({
            'datetime': pd.to_datetime([
                '2025-01-06 09:05:00',
                '2025-01-06 09:10:00',
                '2025-01-06 09:15:00',
                '2025-01-06 09:20:00',
            ]),
            'open': [1000, 1005, 1003, 1004],
            'high': [1008, 1010, 1007, 1009],  # レンジ内
            'low': [998, 1002, 1000, 1001],    # レンジ内
            'close': [1005, 1003, 1005, 1006],
            'volume': [10000, 8000, 9000, 12000]
        })
        data.set_index('datetime', inplace=True)

        detector = RangeBreakoutDetector(
            range_start=time(9, 5),
            range_end=time(9, 15)
        )

        range_high, range_low = detector.calculate_range(data)

        # 09:20は高値1009、安値1001でレンジ内（998-1010）
        breakout_type = detector.detect_breakout(
            data.loc['2025-01-06 09:20:00'],
            range_high,
            range_low
        )

        assert breakout_type is None

    def test_get_entry_price_long(self, sample_data):
        """ロングエントリー価格の取得"""
        detector = RangeBreakoutDetector(
            range_start=time(9, 5),
            range_end=time(9, 15)
        )

        range_high, range_low = detector.calculate_range(sample_data)

        # ブレイクアウト時のエントリー価格
        # = レンジ高値を上抜けた直後の価格
        # 実際の取引では成行注文を想定し、ブレイク確認後の終値で約定
        entry_price = detector.get_entry_price(
            sample_data.loc['2025-01-06 09:20:00'],
            breakout_type='long',
            range_high=range_high,
            range_low=range_low
        )

        # 09:20の終値: 1012
        assert entry_price == 1012

    def test_get_entry_price_short(self):
        """ショートエントリー価格の取得"""
        data = pd.DataFrame({
            'datetime': pd.to_datetime([
                '2025-01-06 09:05:00',
                '2025-01-06 09:10:00',
                '2025-01-06 09:15:00',
                '2025-01-06 09:20:00',
            ]),
            'open': [1000, 1005, 1003, 995],
            'high': [1008, 1010, 1007, 998],
            'low': [998, 1002, 1000, 990],
            'close': [1005, 1003, 1005, 992],
            'volume': [10000, 8000, 9000, 12000]
        })
        data.set_index('datetime', inplace=True)

        detector = RangeBreakoutDetector(
            range_start=time(9, 5),
            range_end=time(9, 15)
        )

        range_high, range_low = detector.calculate_range(data)

        entry_price = detector.get_entry_price(
            data.loc['2025-01-06 09:20:00'],
            breakout_type='short',
            range_high=range_high,
            range_low=range_low
        )

        # 09:20の終値: 992
        assert entry_price == 992

    def test_insufficient_range_data(self):
        """レンジ期間のデータが不足している場合"""
        # 09:05のデータのみ
        data = pd.DataFrame({
            'datetime': pd.to_datetime(['2025-01-06 09:05:00']),
            'open': [1000],
            'high': [1008],
            'low': [998],
            'close': [1005],
            'volume': [10000]
        })
        data.set_index('datetime', inplace=True)

        detector = RangeBreakoutDetector(
            range_start=time(9, 5),
            range_end=time(9, 15)
        )

        with pytest.raises(ValueError, match="レンジ期間のデータが不足"):
            detector.calculate_range(data)

    def test_empty_data(self):
        """空のデータフレームの場合"""
        data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

        detector = RangeBreakoutDetector(
            range_start=time(9, 5),
            range_end=time(9, 15)
        )

        with pytest.raises(ValueError, match="データが空"):
            detector.calculate_range(data)
