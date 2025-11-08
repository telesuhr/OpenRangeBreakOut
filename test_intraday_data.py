"""
分足データ取得のテスト（日付調整版）
"""
import logging
from datetime import datetime
from src.data.refinitiv_client import RefinitivClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_intraday_data():
    """分足データ取得テスト"""
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

    client = RefinitivClient(app_key=app_key)

    try:
        client.connect()

        # より過去の日付で試す（2024年12月）
        test_symbol = "7203.T"  # トヨタ自動車
        test_date = datetime(2024, 12, 5)  # 木曜日
        start_time = datetime(2024, 12, 5, 9, 0)
        end_time = datetime(2024, 12, 5, 15, 0)

        logger.info(f"\n=== {test_symbol} の分足データ取得テスト ===")
        logger.info(f"日付: {test_date.date()}")
        logger.info(f"時間帯: {start_time.time()} - {end_time.time()}")

        # 5分足データを取得
        data = client.get_intraday_data(
            symbol=test_symbol,
            start_date=start_time,
            end_date=end_time,
            interval="5min"
        )

        if data is not None and not data.empty:
            logger.info(f"\n✓ データ取得成功!")
            logger.info(f"取得足数: {len(data)} 本")
            logger.info(f"\nカラム: {list(data.columns)}")
            logger.info(f"\nデータサンプル (最初の10本):\n{data.head(10)}")

            # OHLCVカラムの確認
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            available_columns = [col for col in required_columns if col in data.columns]
            logger.info(f"\nOHLCVカラムの状況:")
            logger.info(f"- 利用可能: {available_columns}")
            logger.info(f"- 不足: {[col for col in required_columns if col not in data.columns]}")

        else:
            logger.warning("✗ データが取得できませんでした")

            # 別の日付でも試す
            logger.info("\n別の日付で再試行...")
            test_date2 = datetime(2024, 11, 1)
            start_time2 = datetime(2024, 11, 1, 9, 0)
            end_time2 = datetime(2024, 11, 1, 15, 0)

            data2 = client.get_intraday_data(
                symbol=test_symbol,
                start_date=start_time2,
                end_date=end_time2,
                interval="5min"
            )

            if data2 is not None and not data2.empty:
                logger.info(f"✓ 2回目のデータ取得成功: {len(data2)} 本")
                logger.info(f"カラム: {list(data2.columns)}")
            else:
                logger.warning("✗ 2回目も失敗")

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()


if __name__ == "__main__":
    test_intraday_data()
