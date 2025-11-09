"""
データ粒度のテスト - 1分足、5分足、ティックデータの取得可否を確認
"""
import logging
from datetime import datetime
from src.data.refinitiv_client import RefinitivClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_data_granularity():
    """異なる粒度のデータ取得をテスト"""

    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    symbol = "9984.T"  # ソフトバンクG

    # テスト期間（10月31日の1時間のみ）
    start_date = datetime(2025, 10, 31, 0, 0)  # JST 09:00
    end_date = datetime(2025, 10, 31, 1, 0)    # JST 10:00

    logger.info("="*80)
    logger.info("データ粒度テスト")
    logger.info("="*80)
    logger.info(f"銘柄: {symbol}")
    logger.info(f"期間: {start_date} - {end_date} (UTC)")
    logger.info("")

    # キャッシュ無効化でテスト
    client = RefinitivClient(app_key=app_key, use_cache=False)
    client.connect()

    # テストする粒度
    intervals = [
        'tick',    # ティックデータ
        '1min',    # 1分足
        '5min',    # 5分足（現在使用中）
        '10min',   # 10分足
        '1h',      # 1時間足
    ]

    results = {}

    for interval in intervals:
        logger.info(f"【{interval}】データ取得テスト")
        try:
            data = client.get_intraday_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval
            )

            if data is not None and not data.empty:
                results[interval] = {
                    'success': True,
                    'rows': len(data),
                    'sample': data.head(3)
                }
                logger.info(f"  ✓ 取得成功: {len(data)}行")
                logger.info(f"  サンプル:")
                logger.info(f"{data.head(3)}")
            else:
                results[interval] = {'success': False, 'error': 'データなし'}
                logger.warning(f"  ✗ データ取得失敗")

        except Exception as e:
            results[interval] = {'success': False, 'error': str(e)}
            logger.error(f"  ✗ エラー: {e}")

        logger.info("")

    # サマリー
    logger.info("="*80)
    logger.info("取得可能な粒度サマリー")
    logger.info("="*80)

    for interval, result in results.items():
        if result['success']:
            logger.info(f"✓ {interval:10s}: {result['rows']}行取得可能")
        else:
            logger.info(f"✗ {interval:10s}: 取得不可 ({result.get('error', 'unknown')})")

    logger.info("")
    logger.info("【推奨】")
    if results.get('1min', {}).get('success'):
        logger.info("→ 1分足データが取得可能です。より精密な分析が可能になります。")
    elif results.get('5min', {}).get('success'):
        logger.info("→ 5分足データが最小粒度です（現在使用中）")

    client.disconnect()

if __name__ == "__main__":
    test_data_granularity()
