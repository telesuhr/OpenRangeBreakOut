"""
実データを使った戦略テスト
"""
import logging
from datetime import datetime, time
from src.data.refinitiv_client import RefinitivClient
from src.strategy.range_breakout import RangeBreakoutDetector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_strategy():
    """実データで戦略をテスト"""
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

    client = RefinitivClient(app_key=app_key)

    try:
        client.connect()

        # テスト: 2024年11月8日のトヨタ自動車
        # 日本時間(JST) 09:00-15:00 = UTC 00:00-06:00
        test_symbol = "7203.T"
        test_date = datetime(2024, 11, 8)
        start_time = datetime(2024, 11, 8, 0, 0)   # UTC 00:00 = JST 09:00
        end_time = datetime(2024, 11, 8, 6, 0)     # UTC 06:00 = JST 15:00

        logger.info(f"\n=== {test_symbol} {test_date.date()} の戦略テスト ===")
        logger.info(f"時間帯: JST 09:00-15:00 (UTC 00:00-06:00)")

        # 5分足データを取得
        data = client.get_intraday_data(
            symbol=test_symbol,
            start_date=start_time,
            end_date=end_time,
            interval="5min"
        )

        if data is None or data.empty:
            logger.error("データ取得失敗")
            return

        logger.info(f"\n✓ データ取得成功: {len(data)} 本")
        logger.info(f"\nデータサンプル:\n{data.head(20)}")

        # レンジブレイクアウト検出器を初期化
        # データはUTCなので、JST 09:05-09:15 = UTC 00:05-00:15
        detector = RangeBreakoutDetector(
            range_start=time(0, 5),   # UTC 00:05 = JST 09:05
            range_end=time(0, 15)     # UTC 00:15 = JST 09:15
        )

        # レンジを計算
        try:
            range_high, range_low = detector.calculate_range(data)
            logger.info(f"\n✓ レンジ計算成功:")
            logger.info(f"  - レンジ高値: {range_high}")
            logger.info(f"  - レンジ安値: {range_low}")
            logger.info(f"  - レンジ幅: {range_high - range_low}")

            # UTC 00:15以降(JST 09:15以降)のデータでブレイクアウトを検出
            breakout_signals = []

            for idx, row in data.iterrows():
                # UTC 00:15以降のみチェック (JST 09:15以降)
                if idx.time() < time(0, 15):
                    continue

                breakout_type = detector.detect_breakout(row, range_high, range_low)

                if breakout_type is not None:
                    entry_price = detector.get_entry_price(
                        row, breakout_type, range_high, range_low
                    )

                    signal = {
                        'time': idx,
                        'type': breakout_type,
                        'entry_price': entry_price,
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close']
                    }
                    breakout_signals.append(signal)

                    logger.info(f"\n🔔 ブレイクアウト検出!")
                    logger.info(f"  - 時刻: {idx}")
                    logger.info(f"  - タイプ: {breakout_type.upper()}")
                    logger.info(f"  - エントリー価格: {entry_price}")
                    logger.info(f"  - 高値: {row['high']}, 安値: {row['low']}")

            if breakout_signals:
                logger.info(f"\n✓ 合計 {len(breakout_signals)} 回のブレイクアウトを検出")
            else:
                logger.info("\n✗ ブレイクアウトなし（レンジ内で推移）")

        except ValueError as e:
            logger.error(f"レンジ計算エラー: {e}")

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()


if __name__ == "__main__":
    test_strategy()
