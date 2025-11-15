"""
バックテスト実行スクリプト

オープンレンジブレイクアウト戦略のフルバックテストを実行
"""
import logging
import yaml
from datetime import datetime, time
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """メイン実行関数"""

    # 設定ファイル読み込み
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # APIキー
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

    # テスト対象銘柄（東証プライム主要銘柄50銘柄）
    test_symbols = [
        # 自動車
        "7203.T",  # トヨタ自動車
        "7267.T",  # ホンダ
        "7201.T",  # 日産自動車
        "7269.T",  # スズキ
        "7261.T",  # マツダ

        # テクノロジー・通信
        "6758.T",  # ソニーグループ
        "9984.T",  # ソフトバンクグループ
        "9433.T",  # KDDI
        "4063.T",  # 信越化学工業
        "6861.T",  # キーエンス
        "6920.T",  # レーザーテック
        "4911.T",  # 資生堂
        "6857.T",  # アドバンテスト

        # 金融
        "8306.T",  # 三菱UFJフィナンシャル・グループ
        "8316.T",  # 三井住友フィナンシャルグループ
        "8411.T",  # みずほフィナンシャルグループ
        "8604.T",  # 野村ホールディングス
        "8766.T",  # 東京海上ホールディングス
        "8750.T",  # 第一生命ホールディングス

        # 小売・消費
        "9983.T",  # ファーストリテイリング
        "7974.T",  # 任天堂
        "3382.T",  # セブン&アイ・ホールディングス
        "8267.T",  # イオン
        "2914.T",  # 日本たばこ産業

        # 製薬
        "4502.T",  # 武田薬品工業
        "4503.T",  # アステラス製薬
        "4568.T",  # 第一三共
        "4151.T",  # 協和キリン

        # 商社
        "8058.T",  # 三菱商事
        "8031.T",  # 三井物産
        "8001.T",  # 伊藤忠商事
        "8002.T",  # 丸紅
        "8015.T",  # 豊田通商

        # 電機・精密
        "6501.T",  # 日立製作所
        "6902.T",  # デンソー
        "6954.T",  # ファナック
        "6103.T",  # オークマ
        "6981.T",  # 村田製作所
        "6976.T",  # 太陽誘電

        # 重工業・建設
        "7011.T",  # 三菱重工業
        "6301.T",  # コマツ
        "6305.T",  # 日立建機
        "1925.T",  # 大和ハウス工業
        "1928.T",  # 積水ハウス

        # その他主要銘柄
        "5411.T",  # JFEホールディングス
        "5401.T",  # 日本製鉄
        "9101.T",  # 日本郵船
        "9104.T",  # 商船三井
        "4324.T",  # 電通グループ
    ]

    logger.info(f"\n{'='*60}")
    logger.info(f"オープンレンジブレイクアウト戦略 バックテスト")
    logger.info(f"{'='*60}")

    # Refinitivクライアント初期化
    client = RefinitivClient(app_key=app_key)

    try:
        # API接続
        client.connect()

        # 時刻をJSTからUTCに変換（JST = UTC+9）
        def jst_to_utc_time(jst_time_str: str) -> time:
            """JST時刻文字列をUTC timeオブジェクトに変換"""
            h, m = map(int, jst_time_str.split(':'))
            # JSTからUTCへ（-9時間）
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

        # バックテスト期間
        # 2025年10月全体（約1ヶ月）
        start_date = datetime(2025, 10, 1)
        end_date = datetime(2025, 10, 31)

        logger.info(f"\nテスト設定:")
        logger.info(f"- 期間: {start_date.date()} - {end_date.date()}")
        logger.info(f"- 銘柄数: {len(test_symbols)}")
        logger.info(f"- レンジ計算: {config['strategy']['range_start_time']} - {config['strategy']['range_end_time']}")
        logger.info(f"- エントリー時間: {config['strategy']['entry_start_time']} - {config['strategy']['entry_end_time']}")

        profit_target = config['strategy']['profit_target']
        if profit_target is not None:
            logger.info(f"- 利益目標: {profit_target:.1%}")
        else:
            logger.info(f"- 利益目標: なし（15:00終値で決済）")

        logger.info(f"- 損切り: {config['strategy']['stop_loss']:.1%}")

        # バックテスト実行
        results = engine.run_backtest(
            client=client,
            symbols=test_symbols,
            start_date=start_date,
            end_date=end_date
        )

        # 結果表示
        print_results(results)

        # 取引履歴の詳細表示
        if not results['trades'].empty:
            logger.info(f"\n{'='*60}")
            logger.info(f"取引履歴:")
            logger.info(f"{'='*60}")
            for idx, trade in results['trades'].iterrows():
                logger.info(
                    f"{trade['symbol']} | {trade['side'].upper():5s} | "
                    f"エントリー: {trade['entry_time']} @ {trade['entry_price']:,.0f} | "
                    f"クローズ: {trade['exit_time']} @ {trade['exit_price']:,.0f} | "
                    f"損益: {trade['pnl']:+,.0f} 円 ({trade['return']:+.2%}) | "
                    f"理由: {trade['reason']}"
                )

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()


def print_results(results):
    """
    バックテスト結果を表示

    Args:
        results: バックテスト結果辞書
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"バックテスト結果サマリー")
    logger.info(f"{'='*60}")

    logger.info(f"\n【基本情報】")
    logger.info(f"初期資金:       {results['initial_capital']:>15,.0f} 円")
    logger.info(f"最終エクイティ: {results['final_equity']:>15,.0f} 円")
    logger.info(f"総リターン:     {results['total_return']:>15.2%}")
    logger.info(f"取引日数:       {results['trading_days']:>15} 日")
    logger.info(f"総取引数:       {results['total_trades']:>15} 回")

    if results['total_trades'] > 0:
        logger.info(f"\n【取引統計】")
        logger.info(f"勝率:           {results['win_rate']:>15.2%}")
        logger.info(f"平均利益:       {results['avg_win']:>15,.0f} 円")
        logger.info(f"平均損失:       {results['avg_loss']:>15,.0f} 円")
        logger.info(f"プロフィットファクター: {results['profit_factor']:>10.2f}")

        logger.info(f"\n【リスク指標】")
        max_dd, max_dd_pct = results['max_drawdown']
        logger.info(f"最大ドローダウン: {max_dd:>13,.0f} 円 ({max_dd_pct:>6.2%})")
        logger.info(f"シャープレシオ:   {results['sharpe_ratio']:>15.2f}")

    logger.info(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
