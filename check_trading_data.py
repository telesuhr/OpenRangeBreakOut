"""
商社銘柄のデータ取得確認スクリプト

10月と11月のデータを比較
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

    # 商社銘柄
    trading_companies = {
        "8058.T": "三菱商事",
        "8031.T": "三井物産",
        "8001.T": "伊藤忠商事",
        "8002.T": "丸紅",
        "8015.T": "豊田通商"
    }

    try:
        client.connect()

        logger.info(f"\n{'='*80}")
        logger.info(f"商社銘柄データ取得確認")
        logger.info(f"{'='*80}")

        # 10月のデータ確認（取引が0回だった期間）
        logger.info(f"\n\n【10月のデータ（取引0回の期間）】")
        oct_dates = [
            datetime(2025, 10, 1),
            datetime(2025, 10, 14),  # 自動車が大量損切りした日
            datetime(2025, 10, 22),
        ]

        for test_date in oct_dates:
            logger.info(f"\n--- {test_date.date()} ---")
            start_time = datetime(test_date.year, test_date.month, test_date.day, 0, 0)
            end_time = datetime(test_date.year, test_date.month, test_date.day, 6, 0)

            for symbol, name in trading_companies.items():
                data = client.get_intraday_data(
                    symbol=symbol,
                    start_date=start_time,
                    end_date=end_time,
                    interval="5min"
                )

                if data is None or data.empty:
                    logger.warning(f"{name} ({symbol}): データなし")
                else:
                    logger.info(f"{name} ({symbol}): {len(data)}本")

                    # レンジ期間のデータを確認
                    range_data = data.between_time('00:05', '00:15', inclusive='both')
                    if not range_data.empty:
                        range_high = range_data['high'].max()
                        range_low = range_data['low'].min()
                        logger.info(f"  レンジ: {range_low} - {range_high} (幅: {range_high - range_low})")

                        # エントリー期間で高値・安値
                        entry_data = data.between_time('00:15', '01:00', inclusive='left')
                        if not entry_data.empty:
                            entry_high = entry_data['high'].max()
                            entry_low = entry_data['low'].min()
                            logger.info(f"  エントリー期間: {entry_low} - {entry_high}")

                            # ブレイクアウトがあったか
                            if entry_high > range_high:
                                logger.info(f"  → 上ブレイクアウトあり！ ({entry_high} > {range_high})")
                            if entry_low < range_low:
                                logger.info(f"  → 下ブレイクアウトあり！ ({entry_low} < {range_low})")

        # 11月のデータ確認（取引があった期間）
        logger.info(f"\n\n【11月のデータ（取引があった期間）】")
        nov_dates = [
            datetime(2025, 11, 4),  # 商社の取引があった日
            datetime(2025, 11, 6),
        ]

        for test_date in nov_dates:
            logger.info(f"\n--- {test_date.date()} ---")
            start_time = datetime(test_date.year, test_date.month, test_date.day, 0, 0)
            end_time = datetime(test_date.year, test_date.month, test_date.day, 6, 0)

            for symbol, name in trading_companies.items():
                data = client.get_intraday_data(
                    symbol=symbol,
                    start_date=start_time,
                    end_date=end_time,
                    interval="5min"
                )

                if data is None or data.empty:
                    logger.warning(f"{name} ({symbol}): データなし")
                else:
                    logger.info(f"{name} ({symbol}): {len(data)}本")

                    # レンジ期間のデータを確認
                    range_data = data.between_time('00:05', '00:15', inclusive='both')
                    if not range_data.empty:
                        range_high = range_data['high'].max()
                        range_low = range_data['low'].min()
                        logger.info(f"  レンジ: {range_low} - {range_high} (幅: {range_high - range_low})")

                        # エントリー期間で高値・安値
                        entry_data = data.between_time('00:15', '01:00', inclusive='left')
                        if not entry_data.empty:
                            entry_high = entry_data['high'].max()
                            entry_low = entry_data['low'].min()
                            logger.info(f"  エントリー期間: {entry_low} - {entry_high}")

                            # ブレイクアウトがあったか
                            if entry_high > range_high:
                                logger.info(f"  → 上ブレイクアウトあり！ ({entry_high} > {range_high})")
                            if entry_low < range_low:
                                logger.info(f"  → 下ブレイクアウトあり！ ({entry_low} < {range_low})")

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
