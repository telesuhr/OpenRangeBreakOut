"""
レンジブレイクアウト戦略モジュール

09:05-09:15のレンジを計算し、ブレイクアウトを検出する
"""
import pandas as pd
from datetime import time
from typing import Tuple, Optional


class RangeBreakoutDetector:
    """レンジブレイクアウト検出器"""

    def __init__(self, range_start: time, range_end: time):
        """
        Args:
            range_start: レンジ計算開始時刻（例: time(9, 5)）
            range_end: レンジ計算終了時刻（例: time(9, 15)）
        """
        self.range_start = range_start
        self.range_end = range_end

    def calculate_range(self, data: pd.DataFrame) -> Tuple[float, float]:
        """
        指定時間帯のレンジ（高値・安値）を計算

        Args:
            data: OHLC データフレーム（datetime index必須）

        Returns:
            (range_high, range_low): レンジの高値と安値

        Raises:
            ValueError: データが空、またはレンジ期間のデータが不足
        """
        if data.empty:
            raise ValueError("データが空です")

        # 時刻でフィルタリング
        range_data = data.between_time(
            self.range_start,
            self.range_end,
            inclusive='both'
        )

        if range_data.empty or len(range_data) < 2:
            raise ValueError(
                f"レンジ期間のデータが不足しています "
                f"({self.range_start}-{self.range_end})"
            )

        # レンジの高値と安値を取得
        range_high = range_data['high'].max()
        range_low = range_data['low'].min()

        return range_high, range_low

    def detect_breakout(
        self,
        current_bar: pd.Series,
        range_high: float,
        range_low: float
    ) -> Optional[str]:
        """
        現在の足でブレイクアウトが発生したか判定

        Args:
            current_bar: 現在の足のデータ（OHLC）
            range_high: レンジの高値
            range_low: レンジの安値

        Returns:
            'long': 高値ブレイクアウト（買いシグナル）
            'short': 安値ブレイクアウト（売りシグナル）
            None: ブレイクアウトなし
        """
        # NA値チェック
        if pd.isna(current_bar['high']) or pd.isna(current_bar['low']):
            return None

        # 高値がレンジ高値を上抜けた場合
        if current_bar['high'] > range_high:
            return 'long'

        # 安値がレンジ安値を下抜けた場合
        if current_bar['low'] < range_low:
            return 'short'

        # ブレイクアウトなし
        return None

    def get_entry_price(
        self,
        current_bar: pd.Series,
        breakout_type: str,
        range_high: float,
        range_low: float
    ) -> float:
        """
        エントリー価格を取得

        ブレイクアウト確認後の終値でエントリーすると仮定

        Args:
            current_bar: 現在の足のデータ
            breakout_type: 'long' または 'short'
            range_high: レンジの高値
            range_low: レンジの安値

        Returns:
            エントリー価格
        """
        # 成行注文を想定し、ブレイクアウト確認後の終値で約定
        return current_bar['close']
