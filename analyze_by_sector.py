"""
セクター別・銘柄別の戦略有効性分析

バックテスト結果を銘柄特性やセクターごとに分析
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


def analyze_by_sector(trades_df):
    """セクター別分析"""
    if trades_df.empty:
        logger.warning("取引データがありません")
        return

    # セクター情報を追加
    trades_df['sector'] = trades_df['symbol'].apply(get_sector)
    trades_df['stock_name'] = trades_df['symbol'].apply(lambda x: STOCK_NAMES.get(x, x))

    logger.info(f"\n{'='*80}")
    logger.info(f"セクター別分析")
    logger.info(f"{'='*80}")

    # セクター別集計
    sector_stats = trades_df.groupby('sector').agg({
        'pnl': ['count', 'sum', 'mean'],
        'return': 'mean'
    }).round(2)

    # 勝率計算
    win_rates = trades_df.groupby('sector').apply(
        lambda x: (x['pnl'] > 0).sum() / len(x) * 100
    ).round(2)

    for sector in sector_stats.index:
        sector_trades = trades_df[trades_df['sector'] == sector]
        total_trades = len(sector_trades)
        total_pnl = sector_trades['pnl'].sum()
        avg_pnl = sector_trades['pnl'].mean()
        avg_return = sector_trades['return'].mean()
        win_rate = win_rates[sector]

        logger.info(f"\n【{sector}】")
        logger.info(f"  取引回数: {total_trades}回")
        logger.info(f"  勝率: {win_rate:.1f}%")
        logger.info(f"  総損益: {total_pnl:+,.0f}円")
        logger.info(f"  平均損益: {avg_pnl:+,.0f}円")
        logger.info(f"  平均リターン: {avg_return:+.2%}")

        # 勝ち/負けの内訳
        wins = sector_trades[sector_trades['pnl'] > 0]
        losses = sector_trades[sector_trades['pnl'] < 0]

        if len(wins) > 0:
            logger.info(f"  平均利益: {wins['pnl'].mean():+,.0f}円")
        if len(losses) > 0:
            logger.info(f"  平均損失: {losses['pnl'].mean():+,.0f}円")


def analyze_by_stock(trades_df):
    """銘柄別分析"""
    if trades_df.empty:
        logger.warning("取引データがありません")
        return

    trades_df['stock_name'] = trades_df['symbol'].apply(lambda x: STOCK_NAMES.get(x, x))

    logger.info(f"\n{'='*80}")
    logger.info(f"銘柄別分析（取引があった銘柄のみ）")
    logger.info(f"{'='*80}")

    # 銘柄別集計
    stock_stats = trades_df.groupby(['symbol', 'stock_name']).agg({
        'pnl': ['count', 'sum', 'mean'],
        'return': 'mean'
    }).round(2)

    # 勝率計算
    win_rates = trades_df.groupby(['symbol', 'stock_name']).apply(
        lambda x: (x['pnl'] > 0).sum() / len(x) * 100 if len(x) > 0 else 0
    ).round(2)

    # 総損益でソート
    sorted_stocks = trades_df.groupby(['symbol', 'stock_name'])['pnl'].sum().sort_values(ascending=False)

    logger.info(f"\n【損益トップ10】")
    for (symbol, name), total_pnl in sorted_stocks.head(10).items():
        stock_trades = trades_df[trades_df['symbol'] == symbol]
        count = len(stock_trades)
        avg_pnl = stock_trades['pnl'].mean()
        win_rate = (stock_trades['pnl'] > 0).sum() / count * 100
        sector = get_sector(symbol)

        logger.info(
            f"{name:15s} ({sector:12s}): "
            f"{count}回, 勝率{win_rate:5.1f}%, "
            f"総損益{total_pnl:+8,.0f}円, 平均{avg_pnl:+7,.0f}円"
        )

    logger.info(f"\n【損益ワースト10】")
    for (symbol, name), total_pnl in sorted_stocks.tail(10).items():
        stock_trades = trades_df[trades_df['symbol'] == symbol]
        count = len(stock_trades)
        avg_pnl = stock_trades['pnl'].mean()
        win_rate = (stock_trades['pnl'] > 0).sum() / count * 100
        sector = get_sector(symbol)

        logger.info(
            f"{name:15s} ({sector:12s}): "
            f"{count}回, 勝率{win_rate:5.1f}%, "
            f"総損益{total_pnl:+8,.0f}円, 平均{avg_pnl:+7,.0f}円"
        )


def analyze_trade_direction(trades_df):
    """ロング/ショート別分析"""
    if trades_df.empty:
        logger.warning("取引データがありません")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"売買方向別分析")
    logger.info(f"{'='*80}")

    for side in ['long', 'short']:
        side_trades = trades_df[trades_df['side'] == side]

        if len(side_trades) == 0:
            logger.info(f"\n【{side.upper()}】: 取引なし")
            continue

        total = len(side_trades)
        wins = len(side_trades[side_trades['pnl'] > 0])
        win_rate = wins / total * 100
        total_pnl = side_trades['pnl'].sum()
        avg_pnl = side_trades['pnl'].mean()

        logger.info(f"\n【{side.upper()}】")
        logger.info(f"  取引回数: {total}回")
        logger.info(f"  勝率: {win_rate:.1f}%")
        logger.info(f"  総損益: {total_pnl:+,.0f}円")
        logger.info(f"  平均損益: {avg_pnl:+,.0f}円")


def analyze_exit_reasons(trades_df):
    """決済理由別分析"""
    if trades_df.empty:
        logger.warning("取引データがありません")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"決済理由別分析")
    logger.info(f"{'='*80}")

    reason_mapping = {
        'profit': '利益目標',
        'loss': '損切り',
        'force': '時間切れ',
        'day_end': '日次終了'
    }

    for reason_code, reason_name in reason_mapping.items():
        reason_trades = trades_df[trades_df['reason'] == reason_code]

        if len(reason_trades) == 0:
            continue

        total = len(reason_trades)
        total_pnl = reason_trades['pnl'].sum()
        avg_pnl = reason_trades['pnl'].mean()
        avg_return = reason_trades['return'].mean()

        logger.info(f"\n【{reason_name}】")
        logger.info(f"  取引回数: {total}回 ({total/len(trades_df)*100:.1f}%)")
        logger.info(f"  総損益: {total_pnl:+,.0f}円")
        logger.info(f"  平均損益: {avg_pnl:+,.0f}円")
        logger.info(f"  平均リターン: {avg_return:+.2%}")


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

    logger.info(f"\n{'='*60}")
    logger.info(f"オープンレンジブレイクアウト戦略 セクター別分析")
    logger.info(f"{'='*60}")

    # Refinitivクライアント初期化
    client = RefinitivClient(app_key=app_key)

    try:
        # API接続
        client.connect()

        # 時刻をJSTからUTCに変換
        def jst_to_utc_time(jst_time_str: str) -> time:
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

        # バックテスト期間
        start_date = datetime(2025, 10, 1)
        end_date = datetime(2025, 10, 31)

        logger.info(f"\nバックテスト実行中...")
        logger.info(f"期間: {start_date.date()} - {end_date.date()}")
        logger.info(f"銘柄数: {len(all_symbols)}")

        # バックテスト実行（ログ出力を抑制）
        logging.getLogger('src.backtester.engine').setLevel(logging.WARNING)
        logging.getLogger('src.data.refinitiv_client').setLevel(logging.WARNING)

        results = engine.run_backtest(
            client=client,
            symbols=all_symbols,
            start_date=start_date,
            end_date=end_date
        )

        # ログレベルを戻す
        logging.getLogger('src.backtester.engine').setLevel(logging.INFO)
        logging.getLogger('src.data.refinitiv_client').setLevel(logging.INFO)

        # 取引履歴を取得
        trades_df = results['trades']

        if trades_df.empty:
            logger.error("取引データがありません")
            return

        # 各種分析を実行
        analyze_by_sector(trades_df)
        analyze_by_stock(trades_df)
        analyze_trade_direction(trades_df)
        analyze_exit_reasons(trades_df)

        # 総合サマリー
        logger.info(f"\n{'='*80}")
        logger.info(f"総合サマリー")
        logger.info(f"{'='*80}")
        logger.info(f"総取引数: {len(trades_df)}回")
        logger.info(f"総リターン: {results['total_return']:.2%}")
        logger.info(f"勝率: {results['win_rate']:.2%}")
        logger.info(f"プロフィットファクター: {results['profit_factor']:.2f}")

    except Exception as e:
        logger.error(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
