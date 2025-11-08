"""
PostgreSQLデータベース管理クラス
"""
import psycopg2
import psycopg2.extras
import pandas as pd
import logging
from datetime import datetime
from typing import Optional
import os


logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQLデータベース管理"""
    
    def __init__(self, config: dict = None):
        """
        Args:
            config: データベース接続設定辞書
                   Noneの場合は環境変数から読み込む
        """
        if config is None:
            config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'market_data'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'postgres')
            }
        
        self.config = config
        self.conn = None
    
    def connect(self):
        """データベースに接続"""
        try:
            self.conn = psycopg2.connect(**self.config)
            logger.info("データベース接続成功")
            return True
        except psycopg2.Error as e:
            logger.error(f"データベース接続エラー: {e}")
            return False
    
    def disconnect(self):
        """データベース接続を切断"""
        if self.conn:
            self.conn.close()
            logger.info("データベース切断完了")
    
    def save_intraday_data(
        self,
        symbol: str,
        data: pd.DataFrame,
        interval: str = '5min'
    ) -> int:
        """
        分足データをデータベースに保存
        
        Args:
            symbol: 銘柄コード
            data: 分足データ（DatetimeIndexを持つDataFrame）
            interval: データ間隔
        
        Returns:
            保存した行数
        """
        if data.empty:
            return 0
        
        cursor = self.conn.cursor()
        inserted_count = 0
        
        try:
            for timestamp, row in data.iterrows():
                try:
                    cursor.execute("""
                        INSERT INTO intraday_data 
                        (symbol, timestamp, open, high, low, close, volume, interval)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, timestamp, interval) DO NOTHING
                    """, (
                        symbol,
                        timestamp,
                        float(row['open']) if pd.notna(row['open']) else None,
                        float(row['high']) if pd.notna(row['high']) else None,
                        float(row['low']) if pd.notna(row['low']) else None,
                        float(row['close']) if pd.notna(row['close']) else None,
                        int(row['volume']) if pd.notna(row['volume']) else None,
                        interval
                    ))
                    inserted_count += cursor.rowcount
                except Exception as e:
                    logger.warning(f"行挿入エラー ({timestamp}): {e}")
                    continue
            
            self.conn.commit()
            logger.info(f"{symbol}: {inserted_count}行をDBに保存")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"データ保存エラー: {e}")
            raise
        finally:
            cursor.close()
        
        return inserted_count
    
    def get_intraday_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = '5min'
    ) -> Optional[pd.DataFrame]:
        """
        分足データをデータベースから取得
        
        Args:
            symbol: 銘柄コード
            start_date: 開始日時
            end_date: 終了日時
            interval: データ間隔
        
        Returns:
            分足データのDataFrame、データがない場合はNone
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM intraday_data
                WHERE symbol = %s
                  AND timestamp >= %s
                  AND timestamp <= %s
                  AND interval = %s
                ORDER BY timestamp
            """, (symbol, start_date, end_date, interval))
            
            rows = cursor.fetchall()
            
            if not rows:
                return None
            
            # DataFrameに変換
            df = pd.DataFrame(
                rows,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"{symbol}: DBから{len(df)}行を取得")
            return df
            
        except Exception as e:
            logger.error(f"データ取得エラー: {e}")
            return None
        finally:
            cursor.close()
    
    def log_fetch(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str,
        source: str,
        records_count: int
    ):
        """
        データ取得ログを記録
        
        Args:
            symbol: 銘柄コード
            start_date: 開始日時
            end_date: 終了日時
            interval: データ間隔
            source: データソース ('api' or 'cache')
            records_count: 取得レコード数
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO data_fetch_log
                (symbol, start_date, end_date, interval, source, records_count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (symbol, start_date, end_date, interval, source, records_count))
            
            self.conn.commit()
            
        except Exception as e:
            logger.warning(f"ログ記録エラー: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def get_cached_date_range(
        self,
        symbol: str,
        interval: str = '5min'
    ) -> Optional[tuple]:
        """
        キャッシュされているデータの日付範囲を取得
        
        Args:
            symbol: 銘柄コード
            interval: データ間隔
        
        Returns:
            (最小日時, 最大日時) のタプル、データがない場合はNone
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT MIN(timestamp), MAX(timestamp)
                FROM intraday_data
                WHERE symbol = %s AND interval = %s
            """, (symbol, interval))
            
            result = cursor.fetchone()
            
            if result[0] is None:
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"日付範囲取得エラー: {e}")
            return None
        finally:
            cursor.close()
