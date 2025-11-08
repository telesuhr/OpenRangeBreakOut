"""
Refinitiv API接続テスト

APIキーでデータが取得できるか確認
"""
import logging
from datetime import datetime, timedelta
from src.data.refinitiv_client import RefinitivClient

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_api_connection():
    """API接続テスト"""
    # APIキー
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

    logger.info("=== Refinitiv API接続テスト開始 ===")

    # クライアント作成
    client = RefinitivClient(app_key=app_key)

    try:
        # 接続
        logger.info("1. API接続を試行...")
        client.connect()
        logger.info("✓ API接続成功")

        # テスト1: 単一銘柄の分足データ取得
        logger.info("\n2. 分足データ取得テスト（トヨタ自動車: 7203.T）...")
        test_symbol = "7203.T"
        end_date = datetime(2025, 1, 10, 15, 0)  # 2025年1月10日 15:00
        start_date = datetime(2025, 1, 10, 9, 0)  # 2025年1月10日 09:00

        intraday_data = client.get_intraday_data(
            symbol=test_symbol,
            start_date=start_date,
            end_date=end_date,
            interval="5min"
        )

        if intraday_data is not None and not intraday_data.empty:
            logger.info(f"✓ 分足データ取得成功: {len(intraday_data)} 本")
            logger.info(f"\nデータサンプル:\n{intraday_data.head()}")
            logger.info(f"\nカラム: {list(intraday_data.columns)}")
        else:
            logger.warning("✗ 分足データが取得できませんでした")

        # テスト2: 日足データ取得
        logger.info("\n3. 日足データ取得テスト...")
        daily_start = datetime(2025, 1, 6)
        daily_end = datetime(2025, 1, 10)

        daily_data = client.get_daily_data(
            symbols=[test_symbol],
            start_date=daily_start,
            end_date=daily_end
        )

        if daily_data and test_symbol in daily_data:
            logger.info(f"✓ 日足データ取得成功: {len(daily_data[test_symbol])} 日分")
            logger.info(f"\nデータサンプル:\n{daily_data[test_symbol]}")
        else:
            logger.warning("✗ 日足データが取得できませんでした")

        # テスト3: ストップ高/安チェック
        logger.info("\n4. ストップ高/安チェックテスト...")
        limit_check = client.check_limit_up_down(
            symbol=test_symbol,
            date=datetime(2025, 1, 10)
        )
        logger.info(f"✓ チェック完了: {limit_check}")

        logger.info("\n=== すべてのテスト完了 ===")

    except Exception as e:
        logger.error(f"テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 切断
        logger.info("\n5. API切断...")
        client.disconnect()
        logger.info("✓ API切断完了")


if __name__ == "__main__":
    test_api_connection()
