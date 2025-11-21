"""
特定の日付のオープンブレイクアウト戦略の成績を分析
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import glob

# 分析対象の日付（S&P500が1%以上下落した翌日）
TARGET_DATES = [
    "2025-11-14",  # 11/13の翌日
    "2025-11-07",  # 11/6の翌日
    "2025-11-05",  # 11/4の翌日
    "2025-10-31",  # 10/30の翌日
    "2025-10-11",  # 10/10の翌日
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

if not trade_files:
    print("トレードファイルが見つかりません")
    exit(1)

print(f"トレードファイル数: {len(trade_files)}")
print()

# 各日付ごとの集計
date_summary = {}

for target_date in TARGET_DATES:
    date_trades = []

    # 全銘柄のトレードを確認
    for trade_file in trade_files:
        symbol = trade_file.stem.replace("_trades", "")

        try:
            df = pd.read_csv(trade_file)

            # entry_timeカラムがあるか確認
            if 'entry_time' not in df.columns:
                continue

            # 日付でフィルタ
            df['entry_date'] = pd.to_datetime(df['entry_time']).dt.date
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()

            date_df = df[df['entry_date'] == target_date_obj]

            if not date_df.empty:
                for _, trade in date_df.iterrows():
                    date_trades.append({
                        'symbol': symbol,
                        'entry_time': trade['entry_time'],
                        'exit_time': trade['exit_time'],
                        'side': trade['side'],
                        'entry_price': trade['entry_price'],
                        'exit_price': trade['exit_price'],
                        'pnl': trade['pnl'],
                        'return': trade['return'] * 100,  # %に変換
                        'reason': trade['reason']
                    })

        except Exception as e:
            print(f"エラー ({symbol}): {e}")
            continue

    # 日付ごとのサマリーを作成
    if date_trades:
        trades_df = pd.DataFrame(date_trades)

        total_pnl = trades_df['pnl'].sum()
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = trades_df['pnl'].mean()
        avg_return = trades_df['return'].mean()

        date_summary[target_date] = {
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_return': avg_return,
            'trades': trades_df
        }
    else:
        date_summary[target_date] = {
            'total_trades': 0,
            'total_pnl': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_pnl': 0,
            'avg_return': 0,
            'trades': None
        }

# 結果を表示
print("=" * 80)
print("S&P500大幅下落翌日の成績サマリー")
print("=" * 80)
print()

for target_date in TARGET_DATES:
    summary = date_summary[target_date]

    print(f"【{target_date}】")
    print(f"  トレード数: {summary['total_trades']}件")
    print(f"  合計損益: ¥{summary['total_pnl']:,.0f}")
    print(f"  勝ちトレード: {summary['winning_trades']}件")
    print(f"  負けトレード: {summary['losing_trades']}件")
    print(f"  勝率: {summary['win_rate']:.1f}%")
    print(f"  平均損益: ¥{summary['avg_pnl']:,.0f}")
    print(f"  平均損益率: {summary['avg_return']:.2f}%")
    print()

    # 個別トレードの詳細も表示（あれば）
    if summary['trades'] is not None and not summary['trades'].empty:
        print("  個別トレード:")
        for _, trade in summary['trades'].iterrows():
            pnl_sign = "+" if trade['pnl'] > 0 else ""
            print(f"    {trade['symbol']:8s} {trade['side']:5s} "
                  f"{pnl_sign}¥{trade['pnl']:>10,.0f} ({trade['return']:>6.2f}%) "
                  f"{trade['reason']}")
        print()

# 全体の統計
print("=" * 80)
print("全体統計（対象日のみ）")
print("=" * 80)

total_all_trades = sum(s['total_trades'] for s in date_summary.values())
total_all_pnl = sum(s['total_pnl'] for s in date_summary.values())
total_winning = sum(s['winning_trades'] for s in date_summary.values())
total_losing = sum(s['losing_trades'] for s in date_summary.values())
overall_win_rate = (total_winning / total_all_trades * 100) if total_all_trades > 0 else 0
avg_all_pnl = total_all_pnl / total_all_trades if total_all_trades > 0 else 0

print(f"合計トレード数: {total_all_trades}件")
print(f"合計損益: ¥{total_all_pnl:,.0f}")
print(f"勝ちトレード: {total_winning}件")
print(f"負けトレード: {total_losing}件")
print(f"勝率: {overall_win_rate:.1f}%")
print(f"平均損益: ¥{avg_all_pnl:,.0f}")
print()

# 参考：全期間の成績と比較
print("=" * 80)
print("参考：全期間の成績")
print("=" * 80)

all_trades_count = 0
all_trades_pnl = 0
all_winning = 0
all_losing = 0

for trade_file in trade_files:
    try:
        df = pd.read_csv(trade_file)
        if 'pnl' in df.columns:
            all_trades_count += len(df)
            all_trades_pnl += df['pnl'].sum()
            all_winning += len(df[df['pnl'] > 0])
            all_losing += len(df[df['pnl'] < 0])
    except:
        continue

all_win_rate = (all_winning / all_trades_count * 100) if all_trades_count > 0 else 0
all_avg_pnl = all_trades_pnl / all_trades_count if all_trades_count > 0 else 0

print(f"合計トレード数: {all_trades_count}件")
print(f"合計損益: ¥{all_trades_pnl:,.0f}")
print(f"勝ちトレード: {all_winning}件")
print(f"負けトレード: {all_losing}件")
print(f"勝率: {all_win_rate:.1f}%")
print(f"平均損益: ¥{all_avg_pnl:,.0f}")
print()

# 比較
print("=" * 80)
print("比較（S&P500下落翌日 vs 全期間）")
print("=" * 80)
print(f"勝率の差: {overall_win_rate - all_win_rate:+.1f}%ポイント")
print(f"平均損益の差: ¥{avg_all_pnl - all_avg_pnl:+,.0f}")

if overall_win_rate < all_win_rate:
    print()
    print("→ S&P500大幅下落翌日は成績が悪い傾向があります")
    print("→ 日経先物/S&P500フィルターの導入を検討する価値があります")
elif overall_win_rate > all_win_rate:
    print()
    print("→ S&P500大幅下落翌日でも成績は良好です")
    print("→ フィルターは不要かもしれません")
else:
    print()
    print("→ 顕著な差は見られません")
