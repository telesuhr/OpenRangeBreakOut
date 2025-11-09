"""
DBキャッシュを使ったバックテストの動作確認
"""
import logging
from datetime import datetime
import yaml
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_backtest_with_cache():
    """DBキャッシュを使ってバックテストが動作するか確認"""

    # 設定読み込み
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    symbol = "9984.T"  # ソフトバンクG（既にDBにキャッシュ済み）

    # テスト期間（1日のみ）
    start_date = datetime(2025, 10, 31)
    end_date = datetime(2025, 10, 31)

    logger.info("="*80)
    logger.info("DBキャッシュを使ったバックテスト動作確認")
    logger.info("="*80)
    logger.info(f"銘柄: {symbol} (ソフトバンクG)")
    logger.info(f"期間: {start_date.date()} - {end_date.date()}")
    logger.info("")

    # クライアント接続（キャッシュ有効）
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 時刻をJSTからUTCに変換
    def jst_to_utc_time(jst_time_str: str):
        from datetime import time
        h, m = map(int, jst_time_str.split(':'))
        utc_hour = (h - 9) % 24
        return time(utc_hour, m)

    # バックテストエンジン初期化
    engine = BacktestEngine(
        initial_capital=config['backtest']['initial_capital'],
        range_start=jst_to_utc_time(config['strategy']['range_start_time']),
        range_end=jst_to_utc_time(config['strategy']['range_end_time']),
        entry_start=jst_to_utc_time(config['strategy']['entry_start_time']),
        entry_end=jst_to_utc_time(config['strategy']['entry_end_time']),
        profit_target=config['strategy']['profit_target'],
        stop_loss=config['strategy']['stop_loss'],
        force_exit_time=jst_to_utc_time(config['strategy']['force_exit_time']),
        commission_rate=config['costs']['commission_rate']
    )

    try:
        logger.info("バックテスト実行中...")
        results = engine.run_backtest(
            client=client,
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date
        )

        logger.info("")
        logger.info("="*80)
        logger.info("バックテスト結果")
        logger.info("="*80)

        if results and 'total_trades' in results:
            # 総損益を計算
            total_pnl = results['final_equity'] - results['initial_capital']

            logger.info(f"✓ バックテスト成功")
            logger.info(f"  初期資金: {results['initial_capital']:,.0f}円")
            logger.info(f"  最終資産: {results['final_equity']:,.0f}円")
            logger.info(f"  総損益: {total_pnl:+,.0f}円")
            logger.info(f"  リターン: {results['total_return']:+.2%}")
            logger.info(f"  総取引数: {results['total_trades']}回")

            if results['total_trades'] > 0:
                # tradesはDataFrame
                trades_df = results['trades']
                winning_trades = trades_df[trades_df['pnl'] > 0]
                losing_trades = trades_df[trades_df['pnl'] < 0]

                logger.info(f"  勝ちトレード: {len(winning_trades)}回")
                logger.info(f"  負けトレード: {len(losing_trades)}回")
                logger.info(f"  勝率: {results.get('win_rate', 0):.1%}")

                logger.info("")
                logger.info("個別トレード詳細:")
                for i, (idx, trade) in enumerate(trades_df.head(5).iterrows(), 1):
                    logger.info(f"  {i}. エントリー: {trade['entry_time'].strftime('%H:%M')} "
                              f"¥{trade['entry_price']:,.0f} → "
                              f"決済: {trade['exit_time'].strftime('%H:%M')} "
                              f"¥{trade['exit_price']:,.0f} | "
                              f"損益: {trade['pnl']:+,.0f}円 ({trade['return']:+.2%})")

                logger.info("")
                logger.info("✅ DBキャッシュを使ったバックテストが正常に動作しました")
            else:
                logger.warning("⚠️ 取引が発生しませんでした（ブレイクアウト条件を満たさなかった可能性）")

        else:
            logger.error("❌ バックテスト失敗: 結果が取得できませんでした")

    except Exception as e:
        logger.error(f"❌ バックテスト失敗: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()

if __name__ == "__main__":
    test_backtest_with_cache()
