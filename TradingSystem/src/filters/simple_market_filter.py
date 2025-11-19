"""
シンプル市場環境フィルター

トレード対象銘柄全体の動きから市場トレンドを判定
（指数データ不要版）
"""
import logging
from datetime import datetime
from typing import Dict, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class SimpleMarketFilter:
    """
    シンプル市場環境フィルター

    トレード対象銘柄の寄り付きからの平均的な動きで市場環境を判定
    """

    def __init__(
        self,
        enabled: bool = True,
        threshold: float = 0.01,  # 1%
        min_symbols: int = 10  # 最低判定銘柄数
    ):
        """
        Args:
            enabled: フィルターを有効にするか
            threshold: トレンド判定の閾値（例: 0.01 = 1%）
            min_symbols: 判定に必要な最低銘柄数
        """
        self.enabled = enabled
        self.threshold = threshold
        self.min_symbols = min_symbols
        self._cache = {}

        if self.enabled:
            logger.info(f"シンプル市場フィルター有効: 閾値±{threshold*100:.1f}%, 最低{min_symbols}銘柄")
        else:
            logger.info("市場フィルター無効")

    def check_market_condition(
        self,
        date: datetime,
        symbols: List[str],
        client
    ) -> Dict[str, bool]:
        """
        市場環境をチェックして、許可されるトレード方向を返す

        Args:
            date: チェックする日付
            symbols: 対象銘柄リスト
            client: Refinitivクライアント

        Returns:
            {'allow_long': bool, 'allow_short': bool, 'market_change': float}
        """
        if not self.enabled:
            return {
                'allow_long': True,
                'allow_short': True,
                'market_change': 0.0,
                'reason': 'フィルター無効'
            }

        # キャッシュチェック
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self._cache:
            return self._cache[date_str]

        # 各銘柄の寄り付きからの変化率を取得
        changes = []
        for symbol in symbols:
            change = self._get_symbol_morning_change(symbol, date, client)
            if change is not None:
                changes.append(change)

        if len(changes) < self.min_symbols:
            logger.warning(f"{date_str}: データ不足({len(changes)}銘柄)、全方向許可")
            result = {
                'allow_long': True,
                'allow_short': True,
                'market_change': 0.0,
                'reason': f'データ不足({len(changes)}銘柄)'
            }
        else:
            # 市場全体の平均変化率
            market_change = np.median(changes)  # 中央値を使用（外れ値の影響を抑制）

            # トレンド判定
            if market_change > self.threshold:
                # 強い上昇トレンド → ショート禁止
                result = {
                    'allow_long': True,
                    'allow_short': False,
                    'market_change': market_change,
                    'reason': f'強い上昇トレンド（+{market_change*100:.2f}%、{len(changes)}銘柄）'
                }
                logger.info(f"{date_str}: {result['reason']} → ショート禁止")
            elif market_change < -self.threshold:
                # 強い下降トレンド → ロング禁止
                result = {
                    'allow_long': False,
                    'allow_short': True,
                    'market_change': market_change,
                    'reason': f'強い下降トレンド（{market_change*100:.2f}%、{len(changes)}銘柄）'
                }
                logger.info(f"{date_str}: {result['reason']} → ロング禁止")
            else:
                # 通常相場 → 両方向OK
                result = {
                    'allow_long': True,
                    'allow_short': True,
                    'market_change': market_change,
                    'reason': f'通常相場（{market_change*100:+.2f}%、{len(changes)}銘柄）'
                }
                logger.debug(f"{date_str}: {result['reason']}")

        # キャッシュに保存
        self._cache[date_str] = result
        return result

    def _get_symbol_morning_change(
        self,
        symbol: str,
        date: datetime,
        client
    ) -> float:
        """
        銘柄の寄り付きから09:30頃までの変化率を取得

        Args:
            symbol: 銘柄コード
            date: 対象日
            client: Refinitivクライアント

        Returns:
            変化率（小数）。取得失敗時はNone
        """
        try:
            # 1分足データを取得
            df = client.get_intraday_data(symbol, date)

            if df is None or len(df) < 10:
                return None

            # 09:00-09:05の平均価格（寄り付き付近）
            morning_start = df.loc[(df.index.time >= pd.Timestamp('09:00').time()) &
                                   (df.index.time <= pd.Timestamp('09:05').time())]

            # 09:25-09:30の平均価格（判定時点）
            morning_end = df.loc[(df.index.time >= pd.Timestamp('09:25').time()) &
                                 (df.index.time <= pd.Timestamp('09:30').time())]

            if len(morning_start) == 0 or len(morning_end) == 0:
                return None

            start_price = morning_start['close'].mean()
            end_price = morning_end['close'].mean()

            change = (end_price - start_price) / start_price

            return change

        except Exception as e:
            logger.debug(f"{symbol} 朝の変化率取得エラー: {e}")
            return None

    def get_statistics(self) -> Dict:
        """フィルター統計を取得"""
        if not self._cache:
            return {'total_days': 0}

        total_days = len(self._cache)
        long_restricted = sum(1 for v in self._cache.values() if not v['allow_long'])
        short_restricted = sum(1 for v in self._cache.values() if not v['allow_short'])
        both_allowed = sum(1 for v in self._cache.values() if v['allow_long'] and v['allow_short'])

        return {
            'total_days': total_days,
            'long_restricted_days': long_restricted,
            'short_restricted_days': short_restricted,
            'both_allowed_days': both_allowed,
            'long_restriction_rate': long_restricted / total_days * 100 if total_days > 0 else 0,
            'short_restriction_rate': short_restricted / total_days * 100 if total_days > 0 else 0
        }
