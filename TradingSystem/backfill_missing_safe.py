#!/usr/bin/env python3
"""
欠けているデータを安全に補完
API制限を考慮し、段階的に取得
"""
import refinitiv.data as rd
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backfill_missing_safe.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 設定
REQUEST_DELAY = 3  # API制限回避（より保守的に）
MAX_REQUESTS_PER_RUN = 50  # 1回の実行で処理する最大件数（テスト用に少なめ）
TARGET_START_DATE = datetime(2025, 5, 18)  # 半年前
TARGET_END_DATE = datetime(2025, 11, 14)

# 進捗ファイル
PROGRESS_FILE = Path(__file__).parent / "backfill_missing_progress.csv"

def load_progress():
    """進捗読み込み"""
    if PROGRESS_FILE.exists():
        df = pd.read_csv(PROGRESS_FILE)
        completed = set(df[df['status'] == 'completed']['key'].tolist())
        logger.info(f"進捗ファイル読み込み: {len(completed)}件完了済み")
        return completed
    return set()

def save_progress(symbol, date, status, message="", row_count=0):
    """進捗保存"""
    key = f"{symbol}_{date}"

    if PROGRESS_FILE.exists():
        df = pd.read_csv(PROGRESS_FILE)
        if key in df['key'].values:
            df.loc[df['key'] == key, 'status'] = status
            df.loc[df['key'] == key, 'message'] = message
            df.loc[df['key'] == key, 'row_count'] = row_count
            df.loc[df['key'] == key, 'updated_at'] = datetime.now().isoformat()
        else:
            new_row = pd.DataFrame([{
                'key': key,
                'symbol': symbol,
                'date': date,
                'status': status,
                'message': message,
                'row_count': row_count,
                'updated_at': datetime.now().isoformat()
            }])
            df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = pd.DataFrame([{
            'key': key,
            'symbol': symbol,
            'date': date,
            'status': status,
            'message': message,
            'row_count': row_count,
            'updated_at': datetime.now().isoformat()
        }])

    df.to_csv(PROGRESS_FILE, index=False, encoding='utf-8-sig')

def get_all_symbols():
    """データベースから全銘柄リストを取得"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="market_data",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT symbol
        FROM intraday_data
        ORDER BY symbol
    """)

    symbols = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    return symbols

def get_existing_symbol_dates():
    """既存の銘柄×日付の組み合わせを取得"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="market_data",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT symbol, DATE(timestamp) as date
        FROM intraday_data
        WHERE DATE(timestamp) BETWEEN %s AND %s
        ORDER BY date DESC, symbol
    """, (TARGET_START_DATE.date(), TARGET_END_DATE.date()))

    existing = set((row[0], row[1]) for row in cursor.fetchall())
    cursor.close()
    conn.close()

    return existing

def fetch_intraday_data(symbol, date_str):
    """UTC 00:00-06:31のデータを取得"""
    start_time = f"{date_str}T00:00:00Z"
    end_time = f"{date_str}T06:31:00Z"

    try:
        data = rd.get_history(
            universe=symbol,
            start=start_time,
            end=end_time,
            interval='1min'
        )

        if data is None or data.empty:
            return None

        return data

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too many" in error_msg:
            logger.error(f"  ✗ API制限エラー: {symbol} {date_str}")
            raise  # API制限エラーは上位に伝播
        else:
            logger.error(f"  {symbol} {date_str}: API エラー - {error_msg[:100]}")
            return None

def save_to_db(symbol, data):
    """データベースに保存（UTC時刻のまま）"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="market_data",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    # カラム名変換
    column_mapping = {
        'HIGH_1': 'high',
        'LOW_1': 'low',
        'OPEN_PRC': 'open',
        'TRDPRC_1': 'close',
        'ACVOL_UNS': 'volume'
    }
    data = data.rename(columns={k: v for k, v in column_mapping.items() if k in data.columns})

    inserted = 0
    for timestamp, row in data.iterrows():
        cursor.execute("""
            INSERT INTO intraday_data (symbol, timestamp, open, high, low, close, volume, interval)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timestamp, interval) DO NOTHING
        """, (
            symbol,
            timestamp,
            float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
            float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
            float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
            float(row.get('close', 0)) if pd.notna(row.get('close')) else None,
            int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
            '1min'
        ))
        inserted += 1

    conn.commit()
    cursor.close()
    conn.close()

    return inserted

def main():
    logger.info("=" * 100)
    logger.info("欠けているデータの安全な補完")
    logger.info("=" * 100)
    logger.info(f"対象期間: {TARGET_START_DATE.date()} ～ {TARGET_END_DATE.date()}")
    logger.info(f"今回の最大処理件数: {MAX_REQUESTS_PER_RUN}")
    logger.info(f"リクエスト間隔: {REQUEST_DELAY}秒")
    logger.info("")

    # 進捗読み込み
    completed = load_progress()

    # 全銘柄取得
    all_symbols = get_all_symbols()
    logger.info(f"全銘柄数: {len(all_symbols)}")

    # 既存データ取得
    logger.info("既存データを確認中...")
    existing = get_existing_symbol_dates()
    logger.info(f"既存データ: {len(existing)}件（銘柄×日付）")

    # 営業日リスト生成（新しい日付から）
    current_date = TARGET_END_DATE
    trading_days = []

    while current_date >= TARGET_START_DATE:
        if current_date.weekday() < 5:
            trading_days.append(current_date)
        current_date -= timedelta(days=1)

    logger.info(f"対象営業日数（推定）: {len(trading_days)}日")

    # 欠けているデータを特定
    missing_tasks = []
    for date in trading_days:
        date_str = date.strftime('%Y-%m-%d')
        for symbol in all_symbols:
            key = f"{symbol}_{date_str}"
            if (symbol, date.date()) not in existing and key not in completed:
                missing_tasks.append({'symbol': symbol, 'date': date_str})

    total_missing = len(missing_tasks)
    logger.info(f"総欠損データ: {total_missing}件")
    logger.info(f"完了済み: {len(completed)}件")
    logger.info("")

    if total_missing == 0:
        logger.info("✓ すべてのデータが揃っています")
        return

    # 今回処理分を抽出
    batch_tasks = missing_tasks[:MAX_REQUESTS_PER_RUN]
    logger.info(f"今回処理: {len(batch_tasks)}件")
    logger.info("")

    # Refinitiv API接続
    try:
        rd.open_session()
        logger.info("✓ Refinitiv接続成功\n")
    except Exception as e:
        logger.error(f"✗ Refinitiv接続失敗: {e}")
        return

    # バッチ処理
    total_success = 0
    total_fail = 0
    total_rows = 0
    api_limit_hit = False

    for i, task in enumerate(batch_tasks, 1):
        symbol = task['symbol']
        date_str = task['date']

        logger.info(f"[{i}/{len(batch_tasks)}] {symbol} - {date_str}")

        try:
            # データ取得
            data = fetch_intraday_data(symbol, date_str)

            if data is not None and not data.empty:
                # データベース保存
                rows = save_to_db(symbol, data)
                logger.info(f"  ✓ DB保存完了: {rows}行")
                save_progress(symbol, date_str, 'completed', f'{rows}行保存', rows)
                total_success += 1
                total_rows += rows
            else:
                logger.warning(f"  - データなし")
                save_progress(symbol, date_str, 'no_data', 'データなし', 0)
                total_fail += 1

            # API制限回避のための待機
            if i < len(batch_tasks):
                time.sleep(REQUEST_DELAY)

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Too many" in error_msg:
                logger.error(f"  ✗ API制限に達しました\n")
                save_progress(symbol, date_str, 'api_limit', 'API制限', 0)
                api_limit_hit = True
                break
            else:
                logger.error(f"  ✗ エラー: {error_msg[:100]}\n")
                save_progress(symbol, date_str, 'error', error_msg[:100], 0)
                total_fail += 1

    # セッションクローズ
    rd.close_session()
    logger.info("✓ Refinitiv接続切断\n")

    # 結果サマリー
    logger.info("=" * 100)
    logger.info("【補完結果】")
    logger.info("=" * 100)
    logger.info(f"処理件数: {len(batch_tasks)}件")
    logger.info(f"成功: {total_success}件")
    logger.info(f"失敗/データなし: {total_fail}件")
    logger.info(f"取得行数: {total_rows:,}行")

    if api_limit_hit:
        logger.warning("\n⚠ API制限に達しました。数時間後に再実行してください。")
        logger.info(f"進捗ファイル: {PROGRESS_FILE}")
    else:
        remaining = total_missing - len(batch_tasks)
        if remaining > 0:
            logger.info(f"\n残り {remaining}件 - 続けて実行してください:")
            logger.info("python backfill_missing_safe.py")
        else:
            logger.info("\n✓ すべてのデータ取得完了！")

    logger.info("=" * 100)

if __name__ == "__main__":
    main()
