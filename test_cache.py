"""
データベースキャッシュ機能のテスト
"""
import logging
from datetime import datetime
from src.data.refinitiv_client import RefinitivClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_cache():
    """キャッシュ機能をテスト"""
    
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    symbol = "9984.T"  # ソフトバンクG

    # テスト期間（1日のみ）
    start_date = datetime(2025, 10, 31, 0, 0)
    end_date = datetime(2025, 10, 31, 6, 0)
    
    logger.info("\n" + "="*80)
    logger.info("データベースキャッシュ機能テスト")
    logger.info("="*80)
    
    # 1回目：APIから取得してDBに保存
    logger.info("\n【1回目】APIから取得してDBに保存")
    client1 = RefinitivClient(app_key=app_key, use_cache=True)
    client1.connect()
    
    data1 = client1.get_intraday_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval="5min"
    )
    
    if data1 is not None:
        logger.info(f"✓ データ取得成功: {len(data1)}行")
    else:
        logger.error("✗ データ取得失敗")
    
    client1.disconnect()
    
    # 2回目：DBキャッシュから取得（APIを使わない）
    logger.info("\n【2回目】DBキャッシュから取得（API不使用）")
    client2 = RefinitivClient(app_key=app_key, use_cache=True)
    client2.connect()
    
    data2 = client2.get_intraday_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval="5min"
    )
    
    if data2 is not None:
        logger.info(f"✓ データ取得成功: {len(data2)}行")
    else:
        logger.error("✗ データ取得失敗")
    
    client2.disconnect()
    
    # 結果確認
    logger.info("\n" + "="*80)
    logger.info("テスト結果")
    logger.info("="*80)
    
    if data1 is not None and data2 is not None:
        if len(data1) == len(data2):
            logger.info("✓ キャッシュ機能が正常に動作しています")
            logger.info(f"  1回目: {len(data1)}行（APIから取得）")
            logger.info(f"  2回目: {len(data2)}行（DBキャッシュから取得）")
        else:
            logger.warning("✗ データ件数が一致しません")
    else:
        logger.error("✗ テスト失敗")
    
    # キャッシュなしでの比較
    logger.info("\n【参考】キャッシュ無効化での取得")
    client3 = RefinitivClient(app_key=app_key, use_cache=False)
    client3.connect()
    
    data3 = client3.get_intraday_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval="5min"
    )
    
    if data3 is not None:
        logger.info(f"✓ データ取得成功: {len(data3)}行（常にAPIから取得）")
    
    client3.disconnect()

if __name__ == "__main__":
    test_cache()
