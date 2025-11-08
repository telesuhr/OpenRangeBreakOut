"""
最新の分足データ取得テスト
"""
import logging
from datetime import datetime, timedelta
import refinitiv.data as rd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_latest_intraday():
    """最新の分足データテスト"""
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

    try:
        # セッション開始
        rd.open_session(
            name='desktop.workspace',
            app_key=app_key
        )
        logger.info("✓ API接続成功")

        test_symbol = "7203.T"  # トヨタ自動車

        # 方法1: countパラメータで最新N件を取得
        logger.info("\n=== 方法1: 最新50件の分足データを取得 ===")
        data1 = rd.get_history(
            universe=test_symbol,
            interval="5min",
            count=50
        )

        if data1 is not None and not data1.empty:
            logger.info(f"✓ データ取得成功: {len(data1)} 件")
            logger.info(f"カラム: {list(data1.columns)}")
            logger.info(f"\n最新データ:\n{data1.tail()}")
        else:
            logger.warning("✗ データなし")

        # 方法2: timedeltaで最近1日分を取得
        logger.info("\n=== 方法2: 過去1日分のデータを取得 ===")
        data2 = rd.get_history(
            universe=test_symbol,
            interval="5min",
            start=timedelta(-1),
            end=timedelta(0)
        )

        if data2 is not None and not data2.empty:
            logger.info(f"✓ データ取得成功: {len(data2)} 件")
            logger.info(f"カラム: {list(data2.columns)}")
            logger.info(f"\nデータサンプル:\n{data2.head()}")
        else:
            logger.warning("✗ データなし")

        # 方法3: 明示的な日時指定（最近の営業日）
        logger.info("\n=== 方法3: 2024年11月8日のデータを取得 ===")
        data3 = rd.get_history(
            universe=test_symbol,
            interval="5min",
            start="2024-11-08T00:00:00",
            end="2024-11-08T23:59:59"
        )

        if data3 is not None and not data3.empty:
            logger.info(f"✓ データ取得成功: {len(data3)} 件")
            logger.info(f"\nデータサンプル:\n{data3.head()}")
        else:
            logger.warning("✗ データなし")

        # 方法4: 1分足で試す
        logger.info("\n=== 方法4: 1分足で最新50件を取得 ===")
        data4 = rd.get_history(
            universe=test_symbol,
            interval="1min",
            count=50
        )

        if data4 is not None and not data4.empty:
            logger.info(f"✓ データ取得成功: {len(data4)} 件")
            logger.info(f"カラム: {list(data4.columns)}")
        else:
            logger.warning("✗ データなし")

        # 方法5: 時間足で試す
        logger.info("\n=== 方法5: 時間足で最新20件を取得 ===")
        data5 = rd.get_history(
            universe=test_symbol,
            interval="1h",
            count=20
        )

        if data5 is not None and not data5.empty:
            logger.info(f"✓ データ取得成功: {len(data5)} 件")
            logger.info(f"カラム: {list(data5.columns)}")
            logger.info(f"\nデータサンプル:\n{data5}")
        else:
            logger.warning("✗ データなし")

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        rd.close_session()
        logger.info("\n✓ API切断完了")


if __name__ == "__main__":
    test_latest_intraday()
