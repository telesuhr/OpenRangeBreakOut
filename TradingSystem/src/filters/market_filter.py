"""
市場環境フィルター

市場全体のトレンドを判定して、逆張りポジションを制限
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class MarketFilter:
    """
    市場環境フィルター

    日経平均やTOPIXの動きを監視して、一方的な相場の日を検出
    """

    def __init__(
        self,
        enabled: bool = True,
        index_symbol: str = ".N225",  # 日経平均
        threshold: float = 0.015,  # ±1.5%
        lookback_days: int = 1
    ):
        """
        Args:
            enabled: フィルターを有効にするか
            index_symbol: 監視する指数（.N225=日経平均, .TOPX=TOPIX）
            threshold: トレンド判定の閾値（例: 0.015 = 1.5%）
            lookback_days: 何日前との比較か（通常は1日=前日比）
        """
        self.enabled = enabled
        self.index_symbol = index_symbol
        self.threshold = threshold
        self.lookback_days = lookback_days
        self._cache = {}  # 日付ごとのキャッシュ

        if self.enabled:
            logger.info(f"市場フィルター有効: {index_symbol}, 閾値±{threshold*100:.1f}%")
        else:
            logger.info("市場フィルター無効")

    def check_market_condition(
        self,
        date: datetime,
        client
    ) -> Dict[str, bool]:
        """
        市場環境をチェックして、許可されるトレード方向を返す

        Args:
            date: チェックする日付
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

        # 市場変化率を取得
        market_change = self._get_market_change(date, client)

        if market_change is None:
            # データ取得失敗時は全方向許可（保守的）
            logger.warning(f"{date_str}: 市場データ取得失敗、全方向許可")
            result = {
                'allow_long': True,
                'allow_short': True,
                'market_change': 0.0,
                'reason': 'データなし'
            }
        else:
            # トレンド判定
            if market_change > self.threshold:
                # 強い上昇トレンド → ショート禁止
                result = {
                    'allow_long': True,
                    'allow_short': False,
                    'market_change': market_change,
                    'reason': f'強い上昇トレンド（+{market_change*100:.2f}%）'
                }
                logger.info(f"{date_str}: {result['reason']} → ショート禁止")
            elif market_change < -self.threshold:
                # 強い下降トレンド → ロング禁止
                result = {
                    'allow_long': False,
                    'allow_short': True,
                    'market_change': market_change,
                    'reason': f'強い下降トレンド（{market_change*100:.2f}%）'
                }
                logger.info(f"{date_str}: {result['reason']} → ロング禁止")
            else:
                # 通常相場 → 両方向OK
                result = {
                    'allow_long': True,
                    'allow_short': True,
                    'market_change': market_change,
                    'reason': f'通常相場（{market_change*100:+.2f}%）'
                }
                logger.debug(f"{date_str}: {result['reason']}")

        # キャッシュに保存
        self._cache[date_str] = result
        return result

    def _get_market_change(
        self,
        date: datetime,
        client
    ) -> Optional[float]:
        """
        指数の変化率を取得

        Args:
            date: 対象日
            client: Refinitivクライアント

        Returns:
            変化率（小数、例: 0.018 = 1.8%）。取得失敗時はNone
        """
        try:
            # 前日の日付を計算（営業日考慮が必要）
            end_date = date
            start_date = date - timedelta(days=5)  # 余裕を持って5日前から取得

            # 日足データを取得
            df = client.get_daily_data(
                symbol=self.index_symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) < 2:
                logger.warning(f"{self.index_symbol}: データ不足")
                return None

            # 最新2営業日の終値を取得
            df = df.sort_index()
            recent_close = df['close'].iloc[-1]  # 当日終値
            prev_close = df['close'].iloc[-2]    # 前営業日終値

            # 変化率計算
            change = (recent_close - prev_close) / prev_close

            logger.debug(f"{self.index_symbol}: {prev_close:.2f} → {recent_close:.2f} ({change*100:+.2f}%)")
            return change

        except Exception as e:
            logger.error(f"市場データ取得エラー: {e}")
            return None

    def get_statistics(self) -> Dict:
        """
        フィルター統計を取得

        Returns:
            統計情報の辞書
        """
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
