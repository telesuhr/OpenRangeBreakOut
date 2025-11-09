"""
API制限状態の確認
"""
import logging
from datetime import datetime
from src.data.refinitiv_client import RefinitivClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def check_api_status():
    """API制限状態を確認"""
    
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    
    # 軽いテスト：1銘柄、1日のみ（10月の営業日でテスト）
    symbol = "9984.T"  # ソフトバンクG
    start_date = datetime(2025, 10, 31, 0, 0)
    end_date = datetime(2025, 10, 31, 6, 0)
    
    logger.info("="*60)
    logger.info("API制限状態チェック")
    logger.info("="*60)
    logger.info(f"テスト銘柄: {symbol}")
    logger.info(f"テスト期間: {start_date.date()}")
    
    # キャッシュを無効化してAPI直接テスト
    client = RefinitivClient(app_key=app_key, use_cache=False)
    
    try:
        client.connect()
        logger.info("\nAPI接続成功")
        
        logger.info("\nデータ取得を試行中...")
        data = client.get_intraday_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="5min"
        )
        
        if data is not None and not data.empty:
            logger.info(f"\n✅ API制限解除済み！")
            logger.info(f"データ取得成功: {len(data)}行")
            logger.info(f"\nデータサンプル:")
            logger.info(data.head())
        else:
            logger.warning(f"\n⚠️ データ取得失敗（制限継続中の可能性）")
            
    except Exception as e:
        if "429" in str(e) or "Too many requests" in str(e):
            logger.error(f"\n❌ API制限継続中")
            logger.error(f"エラー: {e}")
            logger.info(f"\n推奨: 10～30分後に再試行してください")
        else:
            logger.error(f"\n❌ その他のエラー: {e}")
    
    finally:
        client.disconnect()

if __name__ == "__main__":
    check_api_status()
