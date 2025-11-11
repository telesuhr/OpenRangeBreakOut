"""
バックテストを再実行して取引データを抽出し、日次分析を実行

最小限のコストでデータを取得（キャッシュ使用）
"""
import yaml
import pandas as pd
from datetime import datetime
from collections import defaultdict
import logging

from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from run_individual_backtest import SECTORS, STOCK_NAMES, get_sector

logging.basicConfig(
    level=logging.WARNING  # エラーのみ表示
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

print("=" * 80)
print("日次パフォーマンス分析")
print("=" * 80)
print("データ取得中（DBキャッシュ使用）...")

# 設定読み込み
with open('config/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

# 全銘柄リスト
all_symbols = []
for symbols in SECTORS.values():
    all_symbols.extend(symbols)

# バックテスト期間
start_date = datetime(2025, 10, 1)
end_date = datetime(2025, 10, 31)

# クライアント初期化（キャッシュ使用）
client = RefinitivClient(app_key=app_key, use_cache=True)
client.connect()

# JST時刻をUTC時刻に変換する関数
def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return datetime.strptime(f'{utc_hour:02d}:{m:02d}', '%H:%M').time()

# 全取引データを収集
all_trades = []

for idx, symbol in enumerate(all_symbols, 1):
    print(f"\r[{idx}/{len(all_symbols)}] {STOCK_NAMES.get(symbol, symbol):20s}", end='', flush=True)

    try:
        # バックテストエンジン初期化（JST→UTC変換を適用）
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

        # 取引データに銘柄情報を追加
        if results['total_trades'] > 0:
            trades_df = results['trades'].copy()
            trades_df['symbol'] = symbol
            trades_df['stock_name'] = STOCK_NAMES.get(symbol, symbol)
            trades_df['sector'] = get_sector(symbol)

            all_trades.append(trades_df)

    except Exception as e:
        print(f"\r[{idx}/{len(all_symbols)}] {STOCK_NAMES.get(symbol, symbol):20s} - エラー: {e}")
        continue

client.disconnect()

print(f"\n\n✓ {len(all_trades)}銘柄のデータを取得")

# 全取引データを結合
if all_trades:
    all_trades_df = pd.concat(all_trades, ignore_index=True)

    # 日付カラムを追加
    all_trades_df['trade_date'] = pd.to_datetime(all_trades_df['entry_time']).dt.date

    # CSV保存
    all_trades_df.to_csv('results/all_trades.csv', index=False, encoding='utf-8-sig')
    print(f"✓ 取引データを results/all_trades.csv に保存 ({len(all_trades_df)}件)")

    # 日次分析
    print("\n" + "=" * 80)
    print("日次パフォーマンス分析")
    print("=" * 80)

    # セクター別日次集計
    sector_daily_stats = defaultdict(lambda: {'days_positive': 0, 'days_total': 0, 'total_pnl': 0})

    # 日付×セクター別に集計
    daily_sector_pnl = all_trades_df.groupby(['trade_date', 'sector'])['pnl'].sum().reset_index()

    # 日付でループ
    for trade_date in sorted(all_trades_df['trade_date'].unique()):
        day_data = all_trades_df[all_trades_df['trade_date'] == trade_date]

        # セクター別集計
        sector_summary = day_data.groupby('sector').agg({
            'pnl': 'sum',
            'symbol': 'count'
        }).rename(columns={'symbol': 'trades'})

        # 勝ち取引数を追加
        sector_summary['wins'] = day_data[day_data['pnl'] > 0].groupby('sector').size()
        sector_summary['wins'] = sector_summary['wins'].fillna(0).astype(int)

        # 日次トータル
        day_total_pnl = sector_summary['pnl'].sum()
        day_total_trades = sector_summary['trades'].sum()

        result_symbol = "📈" if day_total_pnl > 0 else "📉"
        print(f"\n{trade_date} {result_symbol} 総損益: {day_total_pnl:+12,.0f}円 ({int(day_total_trades)}取引)")

        # セクター別表示（損益順）
        sector_summary_sorted = sector_summary.sort_values('pnl', ascending=False)

        for sector, row in sector_summary_sorted.iterrows():
            win_rate = (row['wins'] / row['trades'] * 100) if row['trades'] > 0 else 0
            symbol = "✅" if row['pnl'] > 0 else "❌"

            # セクター統計を更新
            sector_daily_stats[sector]['days_total'] += 1
            sector_daily_stats[sector]['total_pnl'] += row['pnl']
            if row['pnl'] > 0:
                sector_daily_stats[sector]['days_positive'] += 1

            print(f"  {symbol} {sector:20s}: {row['pnl']:+12,.0f}円 "
                  f"({int(row['wins'])}/{int(row['trades'])}勝, {win_rate:5.1f}%)")

    # セクター別日次勝率
    print("\n" + "=" * 80)
    print("セクター別 日次勝率（その日プラスだった割合）")
    print("=" * 80)
    print(f"\n{'セクター':20s} {'プラス日数':>12s} {'総取引日数':>12s} {'日次勝率':>10s} {'累積損益':>15s}")
    print("-" * 80)

    sorted_sectors = sorted(sector_daily_stats.items(),
                           key=lambda x: (x[1]['days_positive'] / x[1]['days_total']) if x[1]['days_total'] > 0 else 0,
                           reverse=True)

    for sector, stats in sorted_sectors:
        daily_win_rate = (stats['days_positive'] / stats['days_total'] * 100) if stats['days_total'] > 0 else 0
        symbol = "✅" if daily_win_rate >= 50 else "⚠️" if daily_win_rate >= 40 else "❌"

        print(f"{symbol} {sector:20s} {stats['days_positive']:12d} {stats['days_total']:12d} "
              f"{daily_win_rate:9.1f}% {stats['total_pnl']:+15,.0f}円")

    # 結論
    print("\n" + "=" * 80)
    print("結論")
    print("=" * 80)

    # テクノロジーセクターの分析
    tech_stats = sector_daily_stats.get('テクノロジー・通信', {})
    if tech_stats:
        tech_daily_win_rate = (tech_stats['days_positive'] / tech_stats['days_total'] * 100) if tech_stats['days_total'] > 0 else 0

        print(f"\nテクノロジー・通信セクター:")
        print(f"  プラスの日: {tech_stats['days_positive']}/{tech_stats['days_total']}日")
        print(f"  日次勝率: {tech_daily_win_rate:.1f}%")
        print(f"  累積損益: {tech_stats['total_pnl']:+,.0f}円")

        if tech_daily_win_rate >= 50:
            print("\n✅ テクノロジー・通信セクターは日次ベースでも一貫して優秀")
            print("   → 過半数の営業日でプラスリターン")
            print("   → 安定して収益を上げている")
        elif tech_daily_win_rate >= 40:
            print("\n⚠️ テクノロジー・通信セクターは日次では不安定")
            print("   → トータルではプラスだが、日によってバラツキが大きい")
            print("   → 大勝ちする日と負ける日が混在")
        else:
            print("\n❌ テクノロジー・通信セクターは特定の日の大勝によるもの")
            print("   → 日次勝率が低く、数日の大勝で全体がプラスになっている")
            print("   → 安定性に欠ける")

    # 商社セクターとの比較
    shosha_stats = sector_daily_stats.get('商社', {})
    if shosha_stats:
        shosha_daily_win_rate = (shosha_stats['days_positive'] / shosha_stats['days_total'] * 100) if shosha_stats['days_total'] > 0 else 0

        print(f"\n商社セクター（比較）:")
        print(f"  プラスの日: {shosha_stats['days_positive']}/{shosha_stats['days_total']}日")
        print(f"  日次勝率: {shosha_daily_win_rate:.1f}%")
        print(f"  累積損益: {shosha_stats['total_pnl']:+,.0f}円")

    print("\n" + "=" * 80)

else:
    print("✗ 取引データが取得できませんでした")
