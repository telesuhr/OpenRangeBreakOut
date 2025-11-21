"""
S&P500大幅下落翌日にパフォーマンスが良い銘柄を分析
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# 分析対象の日付（S&P500が1%以上下落した翌日）
TARGET_DATES = [
    "2025-11-14",  # 11/13の翌日
    "2025-11-07",  # 11/6の翌日
    "2025-11-05",  # 11/4の翌日
    "2025-10-31",  # 10/30の翌日
    # "2025-10-11",  # データなしのため除外
]

# 最新のバックテスト結果ディレクトリを取得
output_dir = Path("Output")
latest_dirs = sorted(output_dir.glob("2025*"), reverse=True)

if not latest_dirs:
    print("バックテスト結果が見つかりません")
    exit(1)

latest_result_dir = latest_dirs[0]
print(f"分析対象ディレクトリ: {latest_result_dir}")
print("=" * 80)
print()

# 全銘柄のトレードファイルを読み込む
trade_files = list(latest_result_dir.glob("*_trades.csv"))

# 銘柄別の集計
symbol_performance = {}

for trade_file in trade_files:
    symbol = trade_file.stem.replace("_trades", "")

    try:
        df = pd.read_csv(trade_file)

        if 'entry_time' not in df.columns:
            continue

        # 日付でフィルタ
        df['entry_date'] = pd.to_datetime(df['entry_time']).dt.date

        # 対象日のトレードのみ抽出
        target_trades = []
        for target_date in TARGET_DATES:
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
            date_df = df[df['entry_date'] == target_date_obj]
            if not date_df.empty:
                target_trades.append(date_df)

        if target_trades:
            symbol_df = pd.concat(target_trades, ignore_index=True)

            # 統計計算
            total_trades = len(symbol_df)
            total_pnl = symbol_df['pnl'].sum()
            winning_trades = len(symbol_df[symbol_df['pnl'] > 0])
            losing_trades = len(symbol_df[symbol_df['pnl'] < 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_pnl = symbol_df['pnl'].mean()
            avg_return = symbol_df['return'].mean() * 100

            symbol_performance[symbol] = {
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'avg_return': avg_return,
                'trades': symbol_df
            }

    except Exception as e:
        continue

# 合計損益でソート
sorted_symbols = sorted(
    symbol_performance.items(),
    key=lambda x: x[1]['total_pnl'],
    reverse=True
)

print("=" * 80)
print("S&P500大幅下落翌日の銘柄別パフォーマンス")
print("=" * 80)
print()

print(f"{'順位':<4} {'銘柄':<10} {'トレード数':<8} {'合計損益':>12} {'勝率':>6} {'平均損益':>10} {'平均損益率':>8}")
print("-" * 80)

for rank, (symbol, perf) in enumerate(sorted_symbols, 1):
    print(f"{rank:<4} {symbol:<10} {perf['total_trades']:<8} "
          f"¥{perf['total_pnl']:>10,.0f} {perf['win_rate']:>5.1f}% "
          f"¥{perf['avg_pnl']:>8,.0f} {perf['avg_return']:>6.2f}%")

# トップ3の銘柄の詳細を表示
print()
print("=" * 80)
print("トップ3銘柄の詳細")
print("=" * 80)

for rank, (symbol, perf) in enumerate(sorted_symbols[:3], 1):
    print(f"\n【第{rank}位: {symbol}】")
    print(f"  合計損益: ¥{perf['total_pnl']:,.0f}")
    print(f"  トレード数: {perf['total_trades']}件")
    print(f"  勝率: {perf['win_rate']:.1f}%")
    print(f"  平均損益: ¥{perf['avg_pnl']:,.0f}")
    print(f"  平均損益率: {perf['avg_return']:.2f}%")
    print()

    # 日付別のトレード詳細
    print("  日付別トレード:")
    for target_date in TARGET_DATES:
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        date_trades = perf['trades'][
            pd.to_datetime(perf['trades']['entry_time']).dt.date == target_date_obj
        ]

        if not date_trades.empty:
            for _, trade in date_trades.iterrows():
                pnl_sign = "+" if trade['pnl'] > 0 else ""
                print(f"    {target_date}: {trade['side']:5s} "
                      f"{pnl_sign}¥{trade['pnl']:>10,.0f} ({trade['return']*100:>6.2f}%) "
                      f"{trade['reason']}")

# ワースト3の銘柄も表示
print()
print("=" * 80)
print("ワースト3銘柄")
print("=" * 80)

for rank, (symbol, perf) in enumerate(reversed(sorted_symbols[-3:]), 1):
    print(f"\n【ワースト{rank}位: {symbol}】")
    print(f"  合計損益: ¥{perf['total_pnl']:,.0f}")
    print(f"  トレード数: {perf['total_trades']}件")
    print(f"  勝率: {perf['win_rate']:.1f}%")
    print(f"  平均損益: ¥{perf['avg_pnl']:,.0f}")

# 統計的な分析
print()
print("=" * 80)
print("統計分析")
print("=" * 80)
print()

# 全期間と比較
print("【全期間との比較】")
for symbol, perf in sorted_symbols:
    # 全期間のデータを取得
    trade_file = latest_result_dir / f"{symbol}_trades.csv"
    if trade_file.exists():
        all_df = pd.read_csv(trade_file)
        all_win_rate = (len(all_df[all_df['pnl'] > 0]) / len(all_df) * 100) if len(all_df) > 0 else 0
        all_avg_pnl = all_df['pnl'].mean() if len(all_df) > 0 else 0

        win_rate_diff = perf['win_rate'] - all_win_rate
        avg_pnl_diff = perf['avg_pnl'] - all_avg_pnl

        # 勝率が全期間より高い銘柄のみ表示
        if win_rate_diff > 0:
            print(f"{symbol:10s}: 勝率 {win_rate_diff:+.1f}%pt, 平均損益 {avg_pnl_diff:+,.0f}円 (全期間比)")

print()
print("=" * 80)
print("推奨銘柄")
print("=" * 80)
print()
print("S&P500大幅下落翌日に特にパフォーマンスが良い銘柄:")

# 合計損益がプラスで、勝率が40%以上の銘柄を推奨
recommended = [
    (symbol, perf) for symbol, perf in sorted_symbols
    if perf['total_pnl'] > 0 and perf['win_rate'] >= 40
]

if recommended:
    for symbol, perf in recommended:
        print(f"  ✓ {symbol}: 合計損益 ¥{perf['total_pnl']:,.0f}, 勝率 {perf['win_rate']:.1f}%")
else:
    print("  該当する銘柄なし")

print()
print("逆に避けるべき銘柄:")

# 合計損益がマイナスで、勝率が30%以下の銘柄
avoid = [
    (symbol, perf) for symbol, perf in sorted_symbols
    if perf['total_pnl'] < -50000 and perf['win_rate'] <= 30
]

if avoid:
    for symbol, perf in avoid:
        print(f"  ✗ {symbol}: 合計損益 ¥{perf['total_pnl']:,.0f}, 勝率 {perf['win_rate']:.1f}%")
else:
    print("  該当する銘柄なし")
