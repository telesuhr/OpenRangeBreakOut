"""
損切りライン最適化分析

損切りラインを0.5%刻みで変化させて、各パラメータでのパフォーマンスを比較
DBキャッシュを活用して高速に分析
"""
import yaml
import logging
import pandas as pd
from datetime import datetime, time
from collections import defaultdict
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from run_individual_backtest import SECTORS, STOCK_NAMES, get_sector

logging.basicConfig(
    level=logging.WARNING  # 詳細ログを抑制
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

print("=" * 80)
print("損切りライン最適化分析")
print("=" * 80)
print("データ取得中（DBキャッシュ使用）...\n")

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

# 損切りラインのリスト（0.5%刻み）
STOP_LOSS_VALUES = [0.005, 0.0075, 0.01, 0.0125, 0.015, 0.0175, 0.02, 0.025, 0.03]

# JST時刻をUTC時刻に変換する関数
def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)

# クライアント初期化（キャッシュ使用）
client = RefinitivClient(app_key=app_key, use_cache=True)
client.connect()

# 各損切りラインでの結果を保存
results_by_stop_loss = {}

for stop_loss_idx, stop_loss in enumerate(STOP_LOSS_VALUES, 1):
    print(f"\n{'='*80}")
    print(f"損切りライン: {stop_loss*100:.2f}% ({stop_loss_idx}/{len(STOP_LOSS_VALUES)})")
    print(f"{'='*80}")

    # 各銘柄の結果を保存
    symbol_results = []

    for idx, symbol in enumerate(all_symbols, 1):
        print(f"\r[{idx}/{len(all_symbols)}] {STOCK_NAMES.get(symbol, symbol):20s}", end='', flush=True)

        try:
            # バックテストエンジン初期化
            engine = BacktestEngine(
                initial_capital=config['backtest']['initial_capital'],
                range_start=jst_to_utc_time(config['strategy']['range_start_time']),
                range_end=jst_to_utc_time(config['strategy']['range_end_time']),
                entry_start=jst_to_utc_time(config['strategy']['entry_start_time']),
                entry_end=jst_to_utc_time(config['strategy']['entry_end_time']),
                profit_target=config['strategy']['profit_target'],
                stop_loss=stop_loss,  # 損切りラインを変化させる
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

            # 結果を保存
            if results['total_trades'] > 0:
                symbol_results.append({
                    'symbol': symbol,
                    'stock_name': STOCK_NAMES.get(symbol, symbol),
                    'sector': get_sector(symbol),
                    'total_trades': results['total_trades'],
                    'win_rate': results['win_rate'],
                    'total_return': results['total_return'],
                    'final_equity': results['final_equity'],
                    'pnl': results['final_equity'] - config['backtest']['initial_capital']
                })

        except Exception as e:
            logger.warning(f"\n{symbol} エラー: {e}")
            continue

    # 結果を保存
    results_by_stop_loss[stop_loss] = symbol_results

    print()  # 改行

client.disconnect()

# 結果分析
print("\n" + "=" * 80)
print("損切りライン別パフォーマンスサマリー")
print("=" * 80)

# サマリーテーブル作成
summary_data = []

for stop_loss in STOP_LOSS_VALUES:
    results = results_by_stop_loss[stop_loss]

    if not results:
        continue

    # 全体統計
    total_pnl = sum(r['pnl'] for r in results)
    total_trades = sum(r['total_trades'] for r in results)
    avg_win_rate = sum(r['win_rate'] for r in results) / len(results) if results else 0
    num_profitable = sum(1 for r in results if r['pnl'] > 0)

    # 投資額（銘柄数 × 1000万円）
    total_invested = config['backtest']['initial_capital'] * len(results)
    total_return = (total_pnl / total_invested) if total_invested > 0 else 0

    summary_data.append({
        'stop_loss': stop_loss,
        'stop_loss_pct': stop_loss * 100,
        'total_trades': total_trades,
        'avg_win_rate': avg_win_rate,
        'num_profitable': num_profitable,
        'total_symbols': len(results),
        'total_pnl': total_pnl,
        'total_return': total_return
    })

# DataFrameに変換
summary_df = pd.DataFrame(summary_data)

print("\n【全体パフォーマンス】")
print(f"\n{'損切りライン':>12s} {'取引数':>8s} {'平均勝率':>10s} {'黒字銘柄':>10s} "
      f"{'総損益':>15s} {'総合リターン':>12s}")
print("-" * 80)

for _, row in summary_df.iterrows():
    symbol = "✅" if row['total_pnl'] > 0 else "❌"
    print(f"{symbol} {row['stop_loss_pct']:>10.2f}% "
          f"{int(row['total_trades']):>8d} "
          f"{row['avg_win_rate']:>9.1%} "
          f"{int(row['num_profitable']):>4d}/{int(row['total_symbols']):<3d} "
          f"{row['total_pnl']:>+14,.0f}円 "
          f"{row['total_return']:>+11.2%}")

# 最適値を特定
best_by_pnl = summary_df.loc[summary_df['total_pnl'].idxmax()]
best_by_return = summary_df.loc[summary_df['total_return'].idxmax()]
best_by_win_rate = summary_df.loc[summary_df['avg_win_rate'].idxmax()]

print("\n" + "=" * 80)
print("最適損切りライン")
print("=" * 80)

print(f"\n【総損益で最適】")
print(f"  損切りライン: {best_by_pnl['stop_loss_pct']:.2f}%")
print(f"  総損益: {best_by_pnl['total_pnl']:+,.0f}円")
print(f"  総合リターン: {best_by_pnl['total_return']:+.2%}")
print(f"  取引数: {int(best_by_pnl['total_trades']):,}回")
print(f"  平均勝率: {best_by_pnl['avg_win_rate']:.1%}")

print(f"\n【総合リターンで最適】")
print(f"  損切りライン: {best_by_return['stop_loss_pct']:.2f}%")
print(f"  総合リターン: {best_by_return['total_return']:+.2%}")
print(f"  総損益: {best_by_return['total_pnl']:+,.0f}円")
print(f"  取引数: {int(best_by_return['total_trades']):,}回")
print(f"  平均勝率: {best_by_return['avg_win_rate']:.1%}")

print(f"\n【平均勝率で最適】")
print(f"  損切りライン: {best_by_win_rate['stop_loss_pct']:.2f}%")
print(f"  平均勝率: {best_by_win_rate['avg_win_rate']:.1%}")
print(f"  総損益: {best_by_win_rate['total_pnl']:+,.0f}円")
print(f"  総合リターン: {best_by_win_rate['total_return']:+.2%}")
print(f"  取引数: {int(best_by_win_rate['total_trades']):,}回")

# セクター別分析（最良・現在・最悪の3パターン）
print("\n" + "=" * 80)
print("セクター別パフォーマンス比較")
print("=" * 80)

# 現在の損切りライン (1.0%)
current_stop_loss = 0.01
best_stop_loss = best_by_pnl['stop_loss']
worst_stop_loss = summary_df.loc[summary_df['total_pnl'].idxmin()]['stop_loss']

for comparison_name, comparison_stop_loss in [
    ("最良", best_stop_loss),
    ("現在 (1.0%)", current_stop_loss),
    ("最悪", worst_stop_loss)
]:
    print(f"\n【{comparison_name}: {comparison_stop_loss*100:.2f}%】")

    results = results_by_stop_loss.get(comparison_stop_loss, [])
    if not results:
        continue

    # セクター別集計
    sector_summary = defaultdict(lambda: {'pnl': 0, 'trades': 0, 'symbols': 0})

    for r in results:
        sector = r['sector']
        sector_summary[sector]['pnl'] += r['pnl']
        sector_summary[sector]['trades'] += r['total_trades']
        sector_summary[sector]['symbols'] += 1

    # ソート（損益順）
    sorted_sectors = sorted(sector_summary.items(), key=lambda x: x[1]['pnl'], reverse=True)

    print(f"\n{'セクター':20s} {'銘柄数':>8s} {'取引数':>8s} {'総損益':>15s}")
    print("-" * 60)

    for sector, data in sorted_sectors:
        symbol = "✅" if data['pnl'] > 0 else "❌"
        print(f"{symbol} {sector:20s} {int(data['symbols']):>7d} {int(data['trades']):>7d} {data['pnl']:>+14,.0f}円")

# CSV保存
summary_df.to_csv('results/stop_loss_optimization.csv', index=False, encoding='utf-8-sig')
print(f"\n✓ 最適化結果を results/stop_loss_optimization.csv に保存")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
