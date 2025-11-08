"""
データ品質チェックスクリプト

トヨタ自動車のデータを詳細に確認
"""
import logging
from datetime import datetime
from src.data.refinitiv_client import RefinitivClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key)

    try:
        client.connect()

        # トヨタ自動車のデータを取得
        symbol = "7203.T"
        start_time = datetime(2024, 11, 8, 0, 0)  # UTC 00:00 = JST 09:00
        end_time = datetime(2024, 11, 8, 6, 0)    # UTC 06:00 = JST 15:00

        logger.info(f"\n=== {symbol} データ品質チェック ===")
        logger.info(f"期間: JST 2024-11-08 09:00-15:00 (UTC 00:00-06:00)")

        data = client.get_intraday_data(
            symbol=symbol,
            start_date=start_time,
            end_date=end_time,
            interval="5min"
        )

        if data is None or data.empty:
            logger.error("データ取得失敗")
            return

        logger.info(f"\n✓ データ取得成功: {len(data)} 本")
        logger.info(f"\n全データ:\n{data}")

        logger.info(f"\n\n基本統計:")
        logger.info(f"高値: 最小={data['high'].min()}, 最大={data['high'].max()}")
        logger.info(f"安値: 最小={data['low'].min()}, 最大={data['low'].max()}")
        logger.info(f"始値: 最小={data['open'].min()}, 最大={data['open'].max()}")
        logger.info(f"終値: 最小={data['close'].min()}, 最大={data['close'].max()}")

        # レンジ計算（09:05-09:15 = UTC 00:05-00:15）
        range_data = data.between_time('00:05', '00:15', inclusive='both')
        logger.info(f"\n\nレンジ期間 (JST 09:05-09:15) のデータ:")
        logger.info(f"{range_data}")

        if not range_data.empty:
            range_high = range_data['high'].max()
            range_low = range_data['low'].min()
            logger.info(f"\nレンジ高値: {range_high}")
            logger.info(f"レンジ安値: {range_low}")

        # エントリー時間帯（09:15-10:00 = UTC 00:15-01:00）
        entry_window = data.between_time('00:15', '01:00', inclusive='left')
        logger.info(f"\n\nエントリー時間帯 (JST 09:15-10:00) のデータ:")
        logger.info(f"{entry_window}")

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
