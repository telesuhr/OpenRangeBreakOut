"""
Refinitiv API接続モジュール

Refinitiv Data Platform APIを使用してデータを取得
PostgreSQLキャッシュ機能を実装
"""
import refinitiv.data as rd
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from .db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class RefinitivClient:
    """Refinitiv API クライアント（DBキャッシュ機能付き）"""

    def __init__(self, app_key: str, use_cache: bool = True, db_config: dict = None):
        """
        Args:
            app_key: Refinitiv API キー
            use_cache: データベースキャッシュを使用するか
            db_config: データベース接続設定（Noneの場合は環境変数から読み込み）
        """
        self.app_key = app_key
        self._session = None
        self.use_cache = use_cache
        self.db_manager = None

        if use_cache:
            try:
                self.db_manager = DatabaseManager(db_config)
                self.db_manager.connect()
                logger.info("データベースキャッシュ機能を有効化")
            except Exception as e:
                logger.warning(f"データベース接続失敗、キャッシュ無効化: {e}")
                self.use_cache = False

    def connect(self):
        """APIセッションを開始"""
        try:
            session = rd.open_session(
                name='desktop.workspace',
                app_key=self.app_key
            )
            self._session = session
            logger.info("Refinitiv API接続成功")
        except Exception as e:
            logger.error(f"Refinitiv API接続失敗: {e}")
            raise

    def disconnect(self):
        """APIセッションを終了"""
        try:
            rd.close_session()
            self._session = None
            logger.info("Refinitiv API切断完了")
        except Exception as e:
            logger.error(f"Refinitiv API切断失敗: {e}")

        # データベース接続も切断
        if self.db_manager:
            self.db_manager.disconnect()

    def get_universe_constituents(self, universe: str = "0#.TOPXP") -> List[str]:
        """
        ユニバース構成銘柄を取得

        Args:
            universe: ユニバースコード（デフォルト: 東証プライム）

        Returns:
            銘柄コードのリスト
        """
        try:
            # ユニバース構成銘柄を取得
            data = rd.get_data(
                universe=universe,
                fields=['TR.CommonName']
            )

            if data is None or data.empty:
                logger.warning(f"ユニバース {universe} のデータが取得できませんでした")
                return []

            # 銘柄コードを抽出
            symbols = data.index.tolist()
            logger.info(f"ユニバース {universe} から {len(symbols)} 銘柄を取得")

            return symbols

        except Exception as e:
            logger.error(f"ユニバース取得エラー: {e}")
            return []

    def get_intraday_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "5min"
    ) -> Optional[pd.DataFrame]:
        """
        分足データを取得（DBキャッシュ優先）

        Args:
            symbol: 銘柄コード（例: '7203.T'）
            start_date: 開始日時
            end_date: 終了日時
            interval: 時間間隔（'1min', '5min', '10min', '30min', '1h'等）

        Returns:
            OHLCV データフレーム
        """
        # 1. DBキャッシュから取得を試みる
        if self.use_cache and self.db_manager:
            cached_data = self.db_manager.get_intraday_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval
            )

            if cached_data is not None and not cached_data.empty:
                logger.info(f"{symbol}: DBキャッシュから{len(cached_data)}行を取得 ✓")
                # ログに記録
                self.db_manager.log_fetch(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    source='cache',
                    records_count=len(cached_data)
                )
                return cached_data

        # 2. キャッシュにない場合、APIから取得
        logger.info(f"{symbol}: DBキャッシュにデータなし、APIから取得...")

        try:
            # 分足データを取得
            data = rd.get_history(
                universe=symbol,
                start=start_date.strftime('%Y-%m-%dT%H:%M:%S'),
                end=end_date.strftime('%Y-%m-%dT%H:%M:%S'),
                interval=interval
            )

            if data is None or data.empty:
                logger.warning(f"{symbol} のデータが取得できませんでした")
                return None

            # Refinitivの分足データのカラム名をマッピング
            # HIGH_1 → high, LOW_1 → low, OPEN_PRC → open, TRDPRC_1 → close, ACVOL_UNS → volume
            column_mapping = {
                'HIGH_1': 'high',
                'LOW_1': 'low',
                'OPEN_PRC': 'open',
                'TRDPRC_1': 'close',
                'ACVOL_UNS': 'volume'
            }

            # 存在するカラムのみマッピング
            existing_mapping = {k: v for k, v in column_mapping.items() if k in data.columns}
            data = data.rename(columns=existing_mapping)

            # 必要なカラムのみ抽出
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            available_cols = [col for col in required_cols if col in data.columns]
            data = data[available_cols]

            logger.info(
                f"{symbol}: APIから{len(data)}行を取得 "
                f"({start_date.date()} - {end_date.date()})"
            )

            # 3. 取得したデータをDBに保存
            if self.use_cache and self.db_manager and not data.empty:
                saved_count = self.db_manager.save_intraday_data(
                    symbol=symbol,
                    data=data,
                    interval=interval
                )
                logger.info(f"{symbol}: {saved_count}行をDBに保存 ✓")

                # ログに記録
                self.db_manager.log_fetch(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    source='api',
                    records_count=len(data)
                )

            return data

        except Exception as e:
            logger.error(f"{symbol} のデータ取得エラー: {e}")
            return None

    def get_daily_data(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """
        日足データを一括取得

        Args:
            symbols: 銘柄コードのリスト
            start_date: 開始日
            end_date: 終了日

        Returns:
            {symbol: DataFrame} の辞書
        """
        results = {}

        try:
            # 日足データを取得（フィールド指定なし）
            data = rd.get_history(
                universe=symbols,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval='daily'
            )

            if data is None or data.empty:
                logger.warning("日足データが取得できませんでした")
                return results

            # カラム名を小文字に変換
            data.columns = [col.lower() for col in data.columns]

            # カラム名のマッピング
            column_mapping = {}
            for col in data.columns:
                col_lower = col.lower()
                if 'trdprc' in col_lower or 'close' in col_lower:
                    column_mapping[col] = 'close'
                elif 'openprc' in col_lower or col_lower == 'open':
                    column_mapping[col] = 'open'
                elif col_lower == 'high' or 'high' in col_lower:
                    column_mapping[col] = 'high'
                elif col_lower == 'low' or 'low' in col_lower:
                    column_mapping[col] = 'low'
                elif 'volume' in col_lower or 'vol' in col_lower:
                    column_mapping[col] = 'volume'

            data.rename(columns=column_mapping, inplace=True)

            # 銘柄が1つの場合
            if len(symbols) == 1:
                results[symbols[0]] = data
            else:
                # 複数銘柄の場合は銘柄ごとに分割
                for symbol in symbols:
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            symbol_data = data.xs(symbol, level=0, axis=1)
                        else:
                            symbol_data = data
                        results[symbol] = symbol_data
                    except (KeyError, ValueError):
                        logger.warning(f"{symbol} のデータが見つかりません")
                        continue

            logger.info(f"{len(results)} 銘柄の日足データを取得")

        except Exception as e:
            logger.error(f"日足データ取得エラー: {e}")

        return results

    def check_limit_up_down(
        self,
        symbol: str,
        date: datetime
    ) -> dict:
        """
        ストップ高/ストップ安をチェック

        Args:
            symbol: 銘柄コード
            date: 確認日

        Returns:
            {'is_limit_up': bool, 'is_limit_down': bool}
        """
        try:
            # 当日と前日のデータを取得
            prev_date = date - timedelta(days=5)  # 余裕を持って5日前から

            data = rd.get_history(
                universe=symbol,
                start=prev_date.strftime('%Y-%m-%d'),
                end=date.strftime('%Y-%m-%d'),
                interval='daily'
            )

            if data is not None and not data.empty:
                # カラム名を小文字に変換
                data.columns = [col.lower() for col in data.columns]

                # カラム名のマッピング
                column_mapping = {}
                for col in data.columns:
                    col_lower = col.lower()
                    if 'trdprc' in col_lower or 'close' in col_lower:
                        column_mapping[col] = 'close'
                    elif col_lower == 'high' or 'high' in col_lower:
                        column_mapping[col] = 'high'
                    elif col_lower == 'low' or 'low' in col_lower:
                        column_mapping[col] = 'low'

                data.rename(columns=column_mapping, inplace=True)

            if data is None or len(data) < 2:
                return {'is_limit_up': False, 'is_limit_down': False}

            # 前日終値
            prev_close = data['close'].iloc[-2]

            # 当日の高値・安値
            today_high = data['high'].iloc[-1]
            today_low = data['low'].iloc[-1]

            # ストップ高/ストップ安の閾値（簡易計算）
            # 実際の制限値幅は株価水準により異なる
            if prev_close < 100:
                limit_range = 30
            elif prev_close < 200:
                limit_range = 50
            elif prev_close < 500:
                limit_range = 80
            elif prev_close < 700:
                limit_range = 100
            elif prev_close < 1000:
                limit_range = 150
            elif prev_close < 1500:
                limit_range = 300
            elif prev_close < 2000:
                limit_range = 400
            elif prev_close < 3000:
                limit_range = 500
            elif prev_close < 5000:
                limit_range = 700
            elif prev_close < 7000:
                limit_range = 1000
            elif prev_close < 10000:
                limit_range = 1500
            elif prev_close < 15000:
                limit_range = 3000
            elif prev_close < 20000:
                limit_range = 4000
            else:
                limit_range = 5000

            limit_up = prev_close + limit_range
            limit_down = prev_close - limit_range

            is_limit_up = today_high >= limit_up
            is_limit_down = today_low <= limit_down

            return {
                'is_limit_up': is_limit_up,
                'is_limit_down': is_limit_down
            }

        except Exception as e:
            logger.error(f"{symbol} のストップ高/安チェックエラー: {e}")
            return {'is_limit_up': False, 'is_limit_down': False}
