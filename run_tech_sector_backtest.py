"""
テクノロジー・通信セクター特化バックテスト

パフォーマンスが良かったテクノロジー・通信セクターに絞り、
銘柄を拡充して詳細分析
"""
import logging
import yaml
import pandas as pd
from datetime import datetime, time
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# テクノロジー・通信セクター拡充版
TECH_STOCKS = {
    # 既存8銘柄
    "6758.T": "ソニーグループ",
    "9984.T": "ソフトバンクG",
    "9433.T": "KDDI",
    "4063.T": "信越化学工業",
    "6861.T": "キーエンス",
    "6920.T": "レーザーテック",
    "4911.T": "資生堂",
    "6857.T": "アドバンテスト",

    # 通信追加
    "9432.T": "NTT",
    "4755.T": "楽天グループ",

    # 半導体・製造装置
    "8035.T": "東京エレクトロン",
    "6723.T": "ルネサスエレクトロニクス",
    "7735.T": "SCREENホールディングス",
    "6146.T": "ディスコ",

    # 電子部品
    "6762.T": "TDK",
    "6971.T": "京セラ",
    "6963.T": "ローム",

    # IT・システム
    "6702.T": "富士通",
    "6701.T": "NEC",
    "4684.T": "オービック",
    "2413.T": "エムスリー",

    # ゲーム
    "7974.T": "任天堂",
    "7832.T": "バンダイナムコ",
    "9684.T": "スクウェア・エニックス",
    "9697.T": "カプコン",

    # その他テクノロジー
    "6098.T": "リクルート",
    "4689.T": "Z Holdings"
}


def run_individual_backtest(
    client: RefinitivClient,
    symbol: str,
    stock_name: str,
    config: dict,
    start_date: datetime,
    end_date: datetime
) -> dict:
    """
    単一銘柄のバックテストを実行

    Args:
        client: Refinitiv APIクライアント
        symbol: 銘柄コード
        stock_name: 銘柄名
        config: 設定辞書
        start_date: 開始日
        end_date: 終了日

    Returns:
        バックテスト結果辞書
    """
    # 時刻をJSTからUTCに変換
    def jst_to_utc_time(jst_time_str: str) -> time:
        h, m = map(int, jst_time_str.split(':'))
        utc_hour = (h - 9) % 24
        return time(utc_hour, m)

    # バックテストエンジン初期化（銘柄ごとに新規作成）
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

    # バックテスト実行
    results = engine.run_backtest(
        client=client,
        symbols=[symbol],
        start_date=start_date,
        end_date=end_date
    )

    # 銘柄情報を追加
    results['symbol'] = symbol
    results['stock_name'] = stock_name

    return results


def main():
    """メイン実行関数"""

    # 設定ファイル読み込み
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # APIキー
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

    # バックテスト期間（直近1週間）
    start_date = datetime(2025, 11, 1)
    end_date = datetime(2025, 11, 7)

    logger.info(f"\n{'='*80}")
    logger.info(f"テクノロジー・通信セクター 詳細バックテスト")
    logger.info(f"{'='*80}")
    logger.info(f"期間: {start_date.date()} - {end_date.date()}")
    logger.info(f"銘柄数: {len(TECH_STOCKS)}")
    logger.info(f"各銘柄の初期資金: {config['backtest']['initial_capital']:,.0f} 円")

    # Refinitivクライアント初期化
    client = RefinitivClient(app_key=app_key)

    try:
        # API接続
        client.connect()

        # ログレベルを抑制
        logging.getLogger('src.backtester.engine').setLevel(logging.WARNING)
        logging.getLogger('src.data.refinitiv_client').setLevel(logging.WARNING)

        # 各銘柄を個別にバックテスト
        all_results = []

        for i, (symbol, stock_name) in enumerate(TECH_STOCKS.items(), 1):
            logger.info(f"\n[{i}/{len(TECH_STOCKS)}] {stock_name} ({symbol})")

            try:
                result = run_individual_backtest(
                    client=client,
                    symbol=symbol,
                    stock_name=stock_name,
                    config=config,
                    start_date=start_date,
                    end_date=end_date
                )

                all_results.append(result)

                # 簡易サマリー表示
                if result['total_trades'] > 0:
                    logger.info(
                        f"  取引: {result['total_trades']}回, "
                        f"勝率: {result['win_rate']:.1%}, "
                        f"リターン: {result['total_return']:+.2%}"
                    )
                else:
                    logger.info(f"  取引: なし")

            except Exception as e:
                logger.error(f"  エラー: {e}")
                continue

        # ログレベルを戻す
        logging.getLogger('src.backtester.engine').setLevel(logging.INFO)
        logging.getLogger('src.data.refinitiv_client').setLevel(logging.INFO)

        # 結果分析
        analyze_results(all_results, config['backtest']['initial_capital'], start_date, end_date)

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()


def analyze_results(all_results: list, initial_capital: float, start_date: datetime, end_date: datetime):
    """
    全銘柄の結果を集計・分析

    Args:
        all_results: 全銘柄の結果リスト
        initial_capital: 初期資金
        start_date: 開始日
        end_date: 終了日
    """
    if not all_results:
        logger.warning("分析対象のデータがありません")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"総合分析結果")
    logger.info(f"{'='*80}")

    # 取引があった銘柄のみ抽出
    traded_results = [r for r in all_results if r['total_trades'] > 0]

    logger.info(f"\n【基本統計】")
    logger.info(f"期間: {start_date.date()} - {end_date.date()}")
    logger.info(f"総銘柄数: {len(all_results)}")
    logger.info(f"取引があった銘柄数: {len(traded_results)}")
    logger.info(f"取引がなかった銘柄数: {len(all_results) - len(traded_results)}")

    if not traded_results:
        logger.warning("取引データがないため、これ以上の分析はできません")
        return

    # 総取引数
    total_trades = sum(r['total_trades'] for r in traded_results)
    logger.info(f"総取引数: {total_trades}回")

    # 全銘柄の合計リターン
    total_invested = initial_capital * len(traded_results)
    total_final = sum(r['final_equity'] for r in traded_results)
    overall_return = (total_final - total_invested) / total_invested

    logger.info(f"\n【ポートフォリオ全体（{len(traded_results)}銘柄）】")
    logger.info(f"総投資額: {total_invested:,.0f} 円")
    logger.info(f"最終資産: {total_final:,.0f} 円")
    logger.info(f"総合リターン: {overall_return:+.2%}")
    logger.info(f"損益: {total_final - total_invested:+,.0f} 円")

    # カテゴリー別分析
    analyze_by_category(traded_results)

    # 銘柄別ランキング
    analyze_stock_ranking(traded_results)


def analyze_by_category(traded_results: list):
    """カテゴリー別分析（通信、半導体、IT等）"""
    logger.info(f"\n{'='*80}")
    logger.info(f"カテゴリー別分析")
    logger.info(f"{'='*80}")

    # カテゴリー定義
    categories = {
        "通信・インフラ": ["ソニーグループ", "ソフトバンクG", "KDDI", "NTT", "楽天グループ"],
        "半導体・製造装置": ["キーエンス", "レーザーテック", "アドバンテスト", "東京エレクトロン",
                       "ルネサスエレクトロニクス", "SCREENホールディングス", "ディスコ"],
        "電子部品・素材": ["信越化学工業", "TDK", "京セラ", "ローム"],
        "IT・システム": ["富士通", "NEC", "オービック", "エムスリー"],
        "ゲーム": ["任天堂", "バンダイナムコ", "スクウェア・エニックス", "カプコン"],
        "その他": ["資生堂", "リクルート", "Z Holdings"]
    }

    # カテゴリーごとに集計
    category_stats = {}

    for category, stock_names in categories.items():
        category_results = [r for r in traded_results if r['stock_name'] in stock_names]

        if not category_results:
            continue

        total_trades = sum(r['total_trades'] for r in category_results)
        avg_win_rate = sum(r['win_rate'] for r in category_results) / len(category_results)
        total_pnl = sum(r['final_equity'] - r['initial_capital'] for r in category_results)
        avg_return = sum(r['total_return'] for r in category_results) / len(category_results)

        category_stats[category] = {
            'count': len(category_results),
            'total_trades': total_trades,
            'avg_win_rate': avg_win_rate,
            'total_pnl': total_pnl,
            'avg_return': avg_return
        }

    # 総損益でソート
    sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True)

    for category, stats in sorted_categories:
        logger.info(f"\n【{category}】")
        logger.info(f"  銘柄数: {stats['count']}")
        logger.info(f"  総取引数: {stats['total_trades']}回")
        logger.info(f"  平均勝率: {stats['avg_win_rate']:.1%}")
        logger.info(f"  総損益: {stats['total_pnl']:+,.0f} 円")
        logger.info(f"  平均リターン: {stats['avg_return']:+.2%}")


def analyze_stock_ranking(traded_results: list):
    """銘柄別ランキング"""
    logger.info(f"\n{'='*80}")
    logger.info(f"銘柄別パフォーマンスランキング")
    logger.info(f"{'='*80}")

    # リターンでソート
    sorted_results = sorted(traded_results, key=lambda x: x['total_return'], reverse=True)

    logger.info(f"\n【トップ10】")
    for i, result in enumerate(sorted_results[:10], 1):
        logger.info(
            f"{i:2d}. {result['stock_name']:20s}: "
            f"{result['total_trades']:2d}回, "
            f"勝率{result['win_rate']:5.1%}, "
            f"リターン{result['total_return']:+7.2%}, "
            f"損益{result['final_equity'] - result['initial_capital']:+9,.0f}円"
        )

    if len(sorted_results) > 10:
        logger.info(f"\n【ワースト10】")
        for i, result in enumerate(sorted_results[-10:][::-1], 1):
            logger.info(
                f"{i:2d}. {result['stock_name']:20s}: "
                f"{result['total_trades']:2d}回, "
                f"勝率{result['win_rate']:5.1%}, "
                f"リターン{result['total_return']:+7.2%}, "
                f"損益{result['final_equity'] - result['initial_capital']:+9,.0f}円"
            )


if __name__ == "__main__":
    main()
