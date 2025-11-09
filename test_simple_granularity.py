"""
簡易データ粒度テスト - 1分足と5分足の比較
"""
import logging
from datetime import datetime
from src.data.refinitiv_client import RefinitivClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_simple_granularity():
    """1分足と5分足を簡単にテスト"""

    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    symbol = "9984.T"  # ソフトバンクG

    # テスト期間（10月31日の最初の15分のみ）
    start_date = datetime(2025, 10, 31, 0, 0)   # JST 09:00
    end_date = datetime(2025, 10, 31, 0, 15)    # JST 09:15

    logger.info("="*80)
    logger.info("簡易データ粒度テスト（1分足 vs 5分足）")
    logger.info("="*80)
    logger.info(f"銘柄: {symbol}")
    logger.info(f"期間: JST 09:00-09:15（レンジ計算期間）")
    logger.info("")

    client = RefinitivClient(app_key=app_key, use_cache=False)
    client.connect()

    # 5分足テスト
    logger.info("【5分足】データ取得テスト（現在使用中）")
    try:
        data_5min = client.get_intraday_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="5min"
        )

        if data_5min is not None and not data_5min.empty:
            logger.info(f"  ✓ 取得成功: {len(data_5min)}行")
            logger.info(f"  データ:")
            for idx, row in data_5min.iterrows():
                logger.info(f"    {idx.strftime('%H:%M')} | "
                          f"始:{row['open']:.0f} 高:{row['high']:.0f} "
                          f"安:{row['low']:.0f} 終:{row['close']:.0f}")
        else:
            logger.warning(f"  ✗ データ取得失敗")

    except Exception as e:
        logger.error(f"  ✗ エラー: {e}")

    logger.info("")

    # 1分足テスト
    logger.info("【1分足】データ取得テスト")
    try:
        data_1min = client.get_intraday_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="1min"
        )

        if data_1min is not None and not data_1min.empty:
            logger.info(f"  ✓ 取得成功: {len(data_1min)}行")
            logger.info(f"  データサンプル（最初の5行）:")
            for idx, row in data_1min.head(5).iterrows():
                logger.info(f"    {idx.strftime('%H:%M')} | "
                          f"始:{row['open']:.0f} 高:{row['high']:.0f} "
                          f"安:{row['low']:.0f} 終:{row['close']:.0f}")
            logger.info(f"    ... 他{len(data_1min)-5}行")
        else:
            logger.warning(f"  ✗ データ取得失敗")

    except Exception as e:
        logger.error(f"  ✗ エラー: {e}")

    logger.info("")
    logger.info("="*80)
    logger.info("結論")
    logger.info("="*80)

    if data_1min is not None and not data_1min.empty:
        logger.info("✓ 1分足データが取得可能です")
        logger.info(f"  → より精密なレンジ計算が可能（{len(data_1min)}データポイント vs {len(data_5min) if data_5min is not None else 0}）")
        logger.info("  → エントリータイミングの精度向上が期待できます")
    else:
        logger.info("→ 5分足が最小粒度です（現在の設定のまま）")

    logger.info("")
    logger.info("【参考】ティックデータについて")
    logger.info("  → ティックデータ（全取引履歴）も取得可能ですが、")
    logger.info("     データ量が膨大で取得に非常に時間がかかります")
    logger.info("     （1時間で数千〜数万レコード）")

    client.disconnect()

if __name__ == "__main__":
    test_simple_granularity()
