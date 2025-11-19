"""
ATR（Average True Range）計算モジュール

各銘柄のボラティリティを測定し、動的なストップロス設定に使用
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class ATRCalculator:
    """ATR計算クラス"""

    def __init__(self, period: int = 14):
        """
        Args:
            period: ATR計算期間（日数）
        """
        self.period = period
        self._cache: Dict[str, pd.Series] = {}  # 銘柄別のATRキャッシュ

    def calculate_from_1min(self, data: pd.DataFrame) -> pd.Series:
        """
        1分足データから日足を生成してATRを計算

        Args:
            data: 1分足データ（columns: open, high, low, close）

        Returns:
            日次ATR値のSeries
        """
        # 1分足から日足に変換
        daily = self._resample_to_daily(data)

        if len(daily) < self.period:
            logger.warning(f"データ不足: {len(daily)}日分 (必要: {self.period}日)")
            return pd.Series()

        # ATR計算
        return self.calculate(daily)

    def calculate(self, daily_data: pd.DataFrame) -> pd.Series:
        """
        日足データからATRを計算

        Args:
            daily_data: 日足データ（columns: high, low, close）

        Returns:
            ATR値のSeries
        """
        if daily_data.empty or len(daily_data) < 2:
            return pd.Series()

        high = daily_data['high']
        low = daily_data['low']
        close = daily_data['close']

        # True Range計算
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        # 3つのTrue Rangeの最大値を取る
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR（Wilderの指数移動平均）
        # 最初のATRは単純平均
        atr = pd.Series(index=daily_data.index, dtype=float)
        atr.iloc[self.period-1] = tr.iloc[:self.period].mean()

        # その後は指数移動平均
        for i in range(self.period, len(tr)):
            atr.iloc[i] = (atr.iloc[i-1] * (self.period - 1) + tr.iloc[i]) / self.period

        return atr.dropna()

    def calculate_percentage(self, daily_data: pd.DataFrame) -> pd.Series:
        """
        ATRを価格に対する%で返す

        Args:
            daily_data: 日足データ

        Returns:
            ATR%のSeries
        """
        atr = self.calculate(daily_data)
        if atr.empty:
            return pd.Series()

        close = daily_data.loc[atr.index, 'close']
        return (atr / close) * 100

    def _resample_to_daily(self, minute_data: pd.DataFrame) -> pd.DataFrame:
        """
        1分足データを日足に変換

        Args:
            minute_data: 1分足データ

        Returns:
            日足データ
        """
        if minute_data.empty:
            return pd.DataFrame()

        # UTCで日次集計（JST 09:00-15:30をUTC 00:00-06:30として）
        daily = minute_data.resample('D').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum' if 'volume' in minute_data.columns else 'count'
        }).dropna()

        return daily

    def get_latest_atr(self, symbol: str, data: pd.DataFrame) -> Optional[float]:
        """
        最新のATR値を取得（キャッシュ機能付き）

        Args:
            symbol: 銘柄コード
            data: 価格データ

        Returns:
            最新のATR値（%）
        """
        try:
            # 日足に変換
            daily = self._resample_to_daily(data)

            if len(daily) < self.period:
                logger.debug(f"{symbol}: データ不足でATR計算できません")
                # キャッシュから取得を試みる
                if symbol in self._cache and not self._cache[symbol].empty:
                    return self._cache[symbol].iloc[-1]
                return None

            # ATR%を計算
            atr_pct = self.calculate_percentage(daily)

            if not atr_pct.empty:
                latest_atr = atr_pct.iloc[-1]
                # キャッシュに保存
                self._cache[symbol] = atr_pct
                logger.debug(f"{symbol}: ATR = {latest_atr:.2f}%")
                return latest_atr

        except Exception as e:
            logger.warning(f"{symbol}: ATR計算エラー - {e}")
            # キャッシュから取得を試みる
            if symbol in self._cache and not self._cache[symbol].empty:
                return self._cache[symbol].iloc[-1]

        return None

    def get_volatility_level(self, atr_pct: float) -> str:
        """
        ATRからボラティリティレベルを判定

        Args:
            atr_pct: ATR（%）

        Returns:
            ボラティリティレベル（'low', 'medium', 'high', 'extreme'）
        """
        if atr_pct < 1.5:
            return 'low'
        elif atr_pct < 2.5:
            return 'medium'
        elif atr_pct < 4.0:
            return 'high'
        else:
            return 'extreme'