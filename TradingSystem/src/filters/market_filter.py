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


class NikkeiFuturesFilter:
    """
    日経先物フィルター

    前日NY時間の日経先物の変化率を監視して、大幅下落時のエントリーを制限
    """

    def __init__(
        self,
        enabled: bool = True,
        futures_symbol: str = "NKDc1",  # SGX日経225先物
        fallback_symbol: str = ".SPX",  # フォールバック用シンボル（S&P500）
        threshold: float = -0.02,  # -2.0%
        reference_time_utc: str = "21:00"
    ):
        """
        Args:
            enabled: フィルターを有効にするか
            futures_symbol: 監視する先物銘柄（NKDc1=SGX日経225先物）
            fallback_symbol: 代替シンボル（.SPX=S&P500）
            threshold: 下落率閾値（例: -0.02 = -2.0%）マイナス値で指定
            reference_time_utc: 参照時刻（前日の何時のデータと比較するか、UTC）
        """
        self.enabled = enabled
        self.futures_symbol = futures_symbol
        self.fallback_symbol = fallback_symbol
        self.threshold = threshold
        self.reference_time_utc = reference_time_utc
        self._cache = {}  # 日付ごとのキャッシュ

        if self.enabled:
            logger.info(
                f"日経先物フィルター有効: {futures_symbol} (代替: {fallback_symbol}), "
                f"閾値 {threshold*100:.1f}%"
            )
        else:
            logger.info("日経先物フィルター無効")

    def check_entry_allowed(
        self,
        date: datetime,
        client
    ) -> Dict[str, bool]:
        """
        日経先物の前日NY時間からの変化率をチェックして、エントリー可否を返す

        Args:
            date: チェックする日付（東京市場の取引日）
            client: Refinitivクライアント

        Returns:
            {'allow_entry': bool, 'futures_change': float, 'reason': str}
        """
        if not self.enabled:
            return {
                'allow_entry': True,
                'futures_change': 0.0,
                'reason': 'フィルター無効'
            }

        # キャッシュチェック
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self._cache:
            return self._cache[date_str]

        # 前日NY時間から当日東京市場開始前までの先物変化率を取得
        futures_change = self._get_futures_overnight_change(date, client)

        if futures_change is None:
            # データ取得失敗時はエントリー許可（保守的）
            logger.warning(f"{date_str}: 日経先物データ取得失敗、エントリー許可")
            result = {
                'allow_entry': True,
                'futures_change': 0.0,
                'reason': 'データなし'
            }
        else:
            # 閾値チェック（閾値はマイナス値、futures_changeもマイナス値）
            import pandas as pd

            # pd.NAの場合は変化率を0として扱う（データ不完全）
            if pd.isna(futures_change):
                logger.warning(f"{date_str}: 先物データが不完全（NA値）、エントリー許可")
                result = {
                    'allow_entry': True,
                    'futures_change': 0.0,
                    'reason': '先物データ不完全'
                }
            elif futures_change < self.threshold:
                # 大幅下落 → エントリー見送り
                result = {
                    'allow_entry': False,
                    'futures_change': futures_change,
                    'reason': f'日経先物大幅下落（{futures_change*100:.2f}%）'
                }
                logger.info(f"{date_str}: {result['reason']} → エントリー見送り")
            else:
                # 正常範囲 → エントリーOK
                result = {
                    'allow_entry': True,
                    'futures_change': futures_change,
                    'reason': f'日経先物正常範囲（{futures_change*100:+.2f}%）'
                }
                logger.debug(f"{date_str}: {result['reason']}")

        # キャッシュに保存
        self._cache[date_str] = result
        return result

    def _get_futures_overnight_change(
        self,
        date: datetime,
        client
    ) -> Optional[float]:
        """
        前日NY時間から当日東京市場開始前までの先物変化率を取得
        日経先物データが取得できない場合は、S&P500の前日変化率を代用

        Args:
            date: 対象日（東京市場の取引日）
            client: Refinitivクライアント

        Returns:
            変化率（小数、例: -0.025 = -2.5%）。取得失敗時はNone
        """
        # まず日経先物で取得を試みる
        change = self._get_futures_change(date, client, self.futures_symbol)

        if change is not None:
            return change

        # 日経先物が取得できない場合は代替指標（S&P500）を使用
        logger.warning(
            f"{self.futures_symbol}データ取得失敗。代替指標{self.fallback_symbol}を使用します。"
        )
        change = self._get_fallback_change(date, client)

        return change

    def _get_futures_change(
        self,
        date: datetime,
        client,
        symbol: str
    ) -> Optional[float]:
        """
        先物の前日NY時間から当日朝までの変化率を取得

        Args:
            date: 対象日
            client: Refinitivクライアント
            symbol: 先物シンボル

        Returns:
            変化率、取得失敗時はNone
        """
        try:
            # 前日の日付
            prev_date = date - timedelta(days=1)

            # 前日21:00 UTC（日本時間翌6:00）の価格を取得
            prev_start = datetime(prev_date.year, prev_date.month, prev_date.day, 20, 0)
            prev_end = datetime(prev_date.year, prev_date.month, prev_date.day, 22, 0)

            prev_data = client.get_intraday_data(
                symbol=symbol,
                start_date=prev_start,
                end_date=prev_end,
                interval="1min"
            )

            # 当日の東京市場開始前（00:00-01:00 UTC = JST 09:00-10:00）の価格を取得
            current_start = datetime(date.year, date.month, date.day, 0, 0)
            current_end = datetime(date.year, date.month, date.day, 1, 0)

            current_data = client.get_intraday_data(
                symbol=symbol,
                start_date=current_start,
                end_date=current_end,
                interval="1min"
            )

            # データ存在チェック
            if prev_data is None or prev_data.empty:
                logger.debug(f"{symbol}: 前日データなし")
                return None

            if current_data is None or current_data.empty:
                logger.debug(f"{symbol}: 当日データなし")
                return None

            # 前日21:00 UTC付近の終値（最後の有効な価格）
            prev_data = prev_data.sort_index()
            prev_close = prev_data['close'].iloc[-1]

            # 当日東京市場開始時の始値（最初の有効な価格）
            current_data = current_data.sort_index()
            current_open = current_data['close'].iloc[0]

            # 変化率計算
            change = (current_open - prev_close) / prev_close

            logger.debug(
                f"{symbol}: {prev_close:.2f} ({prev_date.date()} 21:00 UTC) "
                f"→ {current_open:.2f} ({date.date()} 09:00 JST) ({change*100:+.2f}%)"
            )
            return change

        except Exception as e:
            logger.debug(f"{symbol}データ取得エラー: {e}")
            return None

    def _get_fallback_change(
        self,
        date: datetime,
        client
    ) -> Optional[float]:
        """
        代替指標（S&P500）の前日変化率を取得

        Args:
            date: 対象日
            client: Refinitivクライアント

        Returns:
            変化率、取得失敗時はNone
        """
        try:
            # 前日の日付を計算（営業日考慮）
            end_date = date
            start_date = date - timedelta(days=5)  # 余裕を持って5日前から取得

            # 日足データを取得
            df = client.get_daily_data(
                symbol=self.fallback_symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) < 2:
                logger.warning(f"{self.fallback_symbol}: データ不足")
                return None

            # 最新2営業日の終値を取得
            df = df.sort_index()
            recent_close = df['close'].iloc[-1]  # 当日終値
            prev_close = df['close'].iloc[-2]    # 前営業日終値

            # 変化率計算
            change = (recent_close - prev_close) / prev_close

            logger.info(
                f"{self.fallback_symbol}（代替）: {prev_close:.2f} → {recent_close:.2f} "
                f"({change*100:+.2f}%)"
            )
            return change

        except Exception as e:
            logger.error(f"代替指標{self.fallback_symbol}データ取得エラー: {e}")
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
        entry_blocked = sum(1 for v in self._cache.values() if not v['allow_entry'])
        entry_allowed = sum(1 for v in self._cache.values() if v['allow_entry'])

        return {
            'total_days': total_days,
            'entry_blocked_days': entry_blocked,
            'entry_allowed_days': entry_allowed,
            'block_rate': entry_blocked / total_days * 100 if total_days > 0 else 0
        }
