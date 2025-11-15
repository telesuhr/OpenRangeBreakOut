"""
既存データベースに15:00-15:30の延長取引時間データを追加取得するスクリプト

2024年11月5日からの取引時間延長に対応するため、
既存のデータベースに15:00-15:30のティックデータを追加取得します。
"""
import sys
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.data.refinitiv_client import RefinitivClient
from src.data.db_manager import DatabaseManager

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """設定ファイルを読み込む"""
    config_path = project_root / "config" / "strategy_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_existing_data_info(db_manager):
    """
    既存データの銘柄と日付範囲を取得

    Returns:
        dict: {symbol: {'min_date': datetime, 'max_date': datetime, 'count': int}}
    """
    query = """
    SELECT
        symbol,
        MIN(DATE(timestamp)) as min_date,
        MAX(DATE(timestamp)) as max_date,
        COUNT(*) as record_count
    FROM intraday_data
    WHERE interval = '1min'
    GROUP BY symbol
    ORDER BY symbol
    """

    cursor = db_manager.conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    data_info = {}
    for row in results:
        symbol, min_date, max_date, count = row
        data_info[symbol] = {
            'min_date': min_date,
            'max_date': max_date,
            'count': count
        }

    return data_info


def check_extended_hours_data(db_manager, symbol, date):
    """
    指定された銘柄・日付で15:00-15:30のデータが既に存在するかチェック

    Args:
        db_manager: データベースマネージャー
        symbol: 銘柄コード
        date: 対象日（datetime.date）

    Returns:
        bool: データが存在する場合True
    """
    # UTC 06:00-06:30 = JST 15:00-15:30
    start_time = datetime(date.year, date.month, date.day, 6, 0)
    end_time = datetime(date.year, date.month, date.day, 6, 30)

    query = """
    SELECT COUNT(*)
    FROM intraday_data
    WHERE symbol = %s
      AND timestamp >= %s
      AND timestamp < %s
      AND interval = '1min'
    """

    cursor = db_manager.conn.cursor()
    cursor.execute(query, (symbol, start_time, end_time))
    count = cursor.fetchone()[0]
    cursor.close()

    return count > 0


def backfill_extended_hours(db_manager, client, symbol, start_date, end_date):
    """
    指定された期間の15:00-15:30データを追加取得

    Args:
        db_manager: データベースマネージャー
        client: Refinitiv APIクライアント
        symbol: 銘柄コード
        start_date: 開始日
        end_date: 終了日
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"銘柄: {symbol}")
    logger.info(f"期間: {start_date} ～ {end_date}")
    logger.info(f"{'='*60}")

    # 日付ごとに処理
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    processed_days = 0
    skipped_days = 0
    added_records = 0

    while current_date <= end_date:
        # 週末はスキップ
        if current_date.weekday() >= 5:  # 5=土曜, 6=日曜
            current_date += timedelta(days=1)
            continue

        # 既にデータがある場合はスキップ
        if check_extended_hours_data(db_manager, symbol, current_date):
            logger.debug(f"{current_date}: 既にデータ存在（スキップ）")
            skipped_days += 1
            current_date += timedelta(days=1)
            continue

        # 15:00-15:30のデータを取得（UTC 06:00-06:30）
        start_time = datetime(current_date.year, current_date.month, current_date.day, 6, 0)
        end_time = datetime(current_date.year, current_date.month, current_date.day, 6, 30)

        try:
            # APIからデータ取得
            data = client.get_intraday_data(
                symbol=symbol,
                start_date=start_time,
                end_date=end_time,
                interval="1min"
            )

            if data is not None and not data.empty:
                # データベースに保存
                db_manager.save_intraday_data(symbol, data, interval="1min")
                added_records += len(data)
                logger.info(f"{current_date}: {len(data)}件のデータを追加")
                processed_days += 1
            else:
                logger.debug(f"{current_date}: データなし（市場休場の可能性）")

        except Exception as e:
            logger.error(f"{current_date}: エラー - {e}")
            # レート制限エラーの場合はスクリプトを終了
            if "429" in str(e) or "Too many requests" in str(e):
                logger.error("=== レート制限エラー検出 ===")
                logger.error("APIレート制限に達しました。数時間待ってから再実行してください。")
                logger.error(f"処理完了: {symbol} の {processed_days}日分")
                logger.error(f"残り: {total_days - processed_days - skipped_days}日分")
                # 接続クローズ
                client.disconnect()
                db_manager.disconnect()
                sys.exit(1)

        current_date += timedelta(days=1)

    logger.info(f"\n--- {symbol} 処理完了 ---")
    logger.info(f"処理日数: {processed_days}/{total_days}")
    logger.info(f"スキップ: {skipped_days}日")
    logger.info(f"追加レコード: {added_records}件")


def main():
    """メイン処理"""
    logger.info("="*80)
    logger.info("取引時間延長データ追加取得スクリプト")
    logger.info("15:00-15:30のティックデータを既存DBに追加します")
    logger.info("="*80)

    # 設定読み込み
    config = load_config()

    # データベース接続
    db_manager = DatabaseManager(config=config['database'])
    if not db_manager.connect():
        logger.error("データベース接続に失敗しました")
        return

    # Refinitiv APIクライアント初期化
    client = RefinitivClient(
        app_key=config['data']['refinitiv']['app_key'],
        use_cache=False  # キャッシュは使わず、直接APIから取得
    )

    # API接続
    try:
        client.connect()
        logger.info("Refinitiv API接続成功")
    except Exception as e:
        logger.error(f"Refinitiv API接続失敗: {e}")
        logger.error("Refinitiv Workspaceが起動しているか確認してください")
        return

    # 既存データの情報を取得
    logger.info("\n既存データの確認中...")
    data_info = get_existing_data_info(db_manager)

    if not data_info:
        logger.warning("データベースにデータが存在しません")
        return

    logger.info(f"\n合計 {len(data_info)} 銘柄のデータが見つかりました")

    # 各銘柄について処理
    for i, (symbol, info) in enumerate(data_info.items(), 1):
        logger.info(f"\n[{i}/{len(data_info)}] 処理中...")
        logger.info(f"銘柄: {symbol}")
        logger.info(f"既存データ期間: {info['min_date']} ～ {info['max_date']}")
        logger.info(f"既存レコード数: {info['count']:,}件")

        # 15:00-15:30のデータを追加取得
        backfill_extended_hours(
            db_manager=db_manager,
            client=client,
            symbol=symbol,
            start_date=info['min_date'],
            end_date=info['max_date']
        )

    logger.info("\n" + "="*80)
    logger.info("全ての処理が完了しました")
    logger.info("="*80)

    # 接続クローズ
    client.disconnect()
    db_manager.disconnect()


if __name__ == "__main__":
    main()
