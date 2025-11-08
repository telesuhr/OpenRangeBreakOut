"""
個別銘柄バックテスト実行スクリプト

各銘柄を独立して1000万円の資金でバックテスト
資金プールによる偏りを排除し、真の銘柄特性を評価
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


# セクター定義
SECTORS = {
    "自動車": ["7203.T", "7267.T", "7201.T", "7269.T", "7261.T"],
    "テクノロジー・通信": ["6758.T", "9984.T", "9433.T", "4063.T", "6861.T", "6920.T", "4911.T", "6857.T"],
    "金融": ["8306.T", "8316.T", "8411.T", "8604.T", "8766.T", "8750.T"],
    "小売・消費": ["9983.T", "7974.T", "3382.T", "8267.T", "2914.T"],
    "製薬": ["4502.T", "4503.T", "4568.T", "4151.T"],
    "商社": ["8058.T", "8031.T", "8001.T", "8002.T", "8015.T"],
    "電機・精密": ["6501.T", "6902.T", "6954.T", "6103.T", "6981.T", "6976.T"],
    "重工業・建設": ["7011.T", "6301.T", "6305.T", "1925.T", "1928.T"],
    "その他": ["5411.T", "5401.T", "9101.T", "9104.T", "4324.T"]
}

# 銘柄名マッピング
STOCK_NAMES = {
    "7203.T": "トヨタ自動車",
    "7267.T": "ホンダ",
    "7201.T": "日産自動車",
    "7269.T": "スズキ",
    "7261.T": "マツダ",
    "6758.T": "ソニーグループ",
    "9984.T": "ソフトバンクG",
    "9433.T": "KDDI",
    "4063.T": "信越化学工業",
    "6861.T": "キーエンス",
    "6920.T": "レーザーテック",
    "4911.T": "資生堂",
    "6857.T": "アドバンテスト",
    "8306.T": "三菱UFJ",
    "8316.T": "三井住友FG",
    "8411.T": "みずほFG",
    "8604.T": "野村HD",
    "8766.T": "東京海上",
    "8750.T": "第一生命",
    "9983.T": "ファーストリテイリング",
    "7974.T": "任天堂",
    "3382.T": "セブン&アイ",
    "8267.T": "イオン",
    "2914.T": "JT",
    "4502.T": "武田薬品",
    "4503.T": "アステラス",
    "4568.T": "第一三共",
    "4151.T": "協和キリン",
    "8058.T": "三菱商事",
    "8031.T": "三井物産",
    "8001.T": "伊藤忠商事",
    "8002.T": "丸紅",
    "8015.T": "豊田通商",
    "6501.T": "日立製作所",
    "6902.T": "デンソー",
    "6954.T": "ファナック",
    "6103.T": "オークマ",
    "6981.T": "村田製作所",
    "6976.T": "太陽誘電",
    "7011.T": "三菱重工業",
    "6301.T": "コマツ",
    "6305.T": "日立建機",
    "1925.T": "大和ハウス",
    "1928.T": "積水ハウス",
    "5411.T": "JFE",
    "5401.T": "日本製鉄",
    "9101.T": "日本郵船",
    "9104.T": "商船三井",
    "4324.T": "電通グループ"
}


def get_sector(symbol):
    """銘柄コードからセクターを取得"""
    for sector, symbols in SECTORS.items():
        if symbol in symbols:
            return sector
    return "不明"


def run_individual_backtest(
    client: RefinitivClient,
    symbol: str,
    config: dict,
    start_date: datetime,
    end_date: datetime
) -> dict:
    """
    単一銘柄のバックテストを実行

    Args:
        client: Refinitiv APIクライアント
        symbol: 銘柄コード
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
        symbols=[symbol],  # 単一銘柄のみ
        start_date=start_date,
        end_date=end_date
    )

    # 銘柄情報を追加
    results['symbol'] = symbol
    results['stock_name'] = STOCK_NAMES.get(symbol, symbol)
    results['sector'] = get_sector(symbol)

    return results


def main():
    """メイン実行関数"""

    # 設定ファイル読み込み
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # APIキー
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

    # 全銘柄リスト
    all_symbols = []
    for symbols in SECTORS.values():
        all_symbols.extend(symbols)

    # バックテスト期間
    start_date = datetime(2025, 10, 1)
    end_date = datetime(2025, 10, 31)

    logger.info(f"\n{'='*80}")
    logger.info(f"個別銘柄バックテスト")
    logger.info(f"{'='*80}")
    logger.info(f"期間: {start_date.date()} - {end_date.date()}")
    logger.info(f"銘柄数: {len(all_symbols)}")
    logger.info(f"各銘柄の初期資金: {config['backtest']['initial_capital']:,.0f} 円")

    # Refinitivクライアント初期化
    client = RefinitivClient(app_key=app_key)

    try:
        # API接続
        client.connect()

        # ログレベルを抑制（各銘柄のログが多すぎるため）
        logging.getLogger('src.backtester.engine').setLevel(logging.WARNING)
        logging.getLogger('src.data.refinitiv_client').setLevel(logging.WARNING)

        # 各銘柄を個別にバックテスト
        all_results = []

        for i, symbol in enumerate(all_symbols, 1):
            stock_name = STOCK_NAMES.get(symbol, symbol)
            sector = get_sector(symbol)

            logger.info(f"\n[{i}/{len(all_symbols)}] {stock_name} ({symbol}) - {sector}")

            try:
                result = run_individual_backtest(
                    client=client,
                    symbol=symbol,
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
        analyze_results(all_results, config['backtest']['initial_capital'])

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()


def analyze_results(all_results: list, initial_capital: float):
    """
    全銘柄の結果を集計・分析

    Args:
        all_results: 全銘柄の結果リスト
        initial_capital: 初期資金
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
    logger.info(f"総銘柄数: {len(all_results)}")
    logger.info(f"取引があった銘柄数: {len(traded_results)}")
    logger.info(f"取引がなかった銘柄数: {len(all_results) - len(traded_results)}")

    if not traded_results:
        logger.warning("取引データがないため、これ以上の分析はできません")
        return

    # 総取引数
    total_trades = sum(r['total_trades'] for r in traded_results)
    logger.info(f"総取引数: {total_trades}回")

    # 全銘柄の合計リターン（各銘柄1000万円スタート）
    total_invested = initial_capital * len(traded_results)
    total_final = sum(r['final_equity'] for r in traded_results)
    overall_return = (total_final - total_invested) / total_invested

    logger.info(f"\n【ポートフォリオ全体（{len(traded_results)}銘柄）】")
    logger.info(f"総投資額: {total_invested:,.0f} 円")
    logger.info(f"最終資産: {total_final:,.0f} 円")
    logger.info(f"総合リターン: {overall_return:+.2%}")
    logger.info(f"損益: {total_final - total_invested:+,.0f} 円")

    # セクター別分析
    analyze_by_sector(traded_results)

    # 銘柄別ランキング
    analyze_stock_ranking(traded_results)


def analyze_by_sector(traded_results: list):
    """セクター別分析"""
    logger.info(f"\n{'='*80}")
    logger.info(f"セクター別分析")
    logger.info(f"{'='*80}")

    # セクターごとに集計
    sector_data = {}

    for result in traded_results:
        sector = result['sector']
        if sector not in sector_data:
            sector_data[sector] = []
        sector_data[sector].append(result)

    # セクターごとの統計
    sector_stats = []

    for sector, results in sector_data.items():
        total_trades = sum(r['total_trades'] for r in results)
        avg_win_rate = sum(r['win_rate'] for r in results) / len(results) if results else 0

        # 合計リターン
        total_return = sum(r['final_equity'] - r['initial_capital'] for r in results)
        avg_return = sum(r['total_return'] for r in results) / len(results) if results else 0

        sector_stats.append({
            'sector': sector,
            'count': len(results),
            'total_trades': total_trades,
            'avg_win_rate': avg_win_rate,
            'total_pnl': total_return,
            'avg_return': avg_return
        })

    # 総損益でソート
    sector_stats.sort(key=lambda x: x['total_pnl'], reverse=True)

    for stat in sector_stats:
        logger.info(f"\n【{stat['sector']}】")
        logger.info(f"  銘柄数: {stat['count']}")
        logger.info(f"  総取引数: {stat['total_trades']}回")
        logger.info(f"  平均勝率: {stat['avg_win_rate']:.1%}")
        logger.info(f"  総損益: {stat['total_pnl']:+,.0f} 円")
        logger.info(f"  平均リターン: {stat['avg_return']:+.2%}")


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
            f"{i:2d}. {result['stock_name']:15s} ({result['sector']:12s}): "
            f"{result['total_trades']:2d}回, "
            f"勝率{result['win_rate']:5.1%}, "
            f"リターン{result['total_return']:+7.2%}, "
            f"損益{result['final_equity'] - result['initial_capital']:+9,.0f}円"
        )

    logger.info(f"\n【ワースト10】")
    for i, result in enumerate(sorted_results[-10:][::-1], 1):
        logger.info(
            f"{i:2d}. {result['stock_name']:15s} ({result['sector']:12s}): "
            f"{result['total_trades']:2d}回, "
            f"勝率{result['win_rate']:5.1%}, "
            f"リターン{result['total_return']:+7.2%}, "
            f"損益{result['final_equity'] - result['initial_capital']:+9,.0f}円"
        )


if __name__ == "__main__":
    main()
