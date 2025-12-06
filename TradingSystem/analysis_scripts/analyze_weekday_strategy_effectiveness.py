#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曜日別戦略有効性分析

LONG/SHORTを無視して、純粋に曜日ごとの戦略パフォーマンスを検証する
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def analyze_weekday_strategy_effectiveness(
    result_folder: str = "Output/20251203_081519",
    start_date: str = "2025-06-01"  # 直近6ヶ月
):
    """曜日別戦略有効性分析（LONG/SHORT無視）"""

    print("=" * 80)
    print("曜日別戦略有効性分析（LONG/SHORT無視）")
    print("=" * 80)

    output_path = Path(result_folder)

    # 全CSVファイル読み込み
    csv_files = list(output_path.glob("*_trades.csv"))

    print(f"\n銘柄数: {len(csv_files)}")
    print(f"分析期間: {start_date} 以降")

    # 全トレードデータを結合
    all_trades = []

    for csv_file in csv_files:
        symbol = csv_file.stem.replace('_trades', '')

        try:
            df = pd.read_csv(csv_file)

            if len(df) == 0:
                continue

            df['symbol'] = symbol
            all_trades.append(df)

        except Exception as e:
            print(f"エラー: {symbol}: {e}")
            continue

    # 全データ結合
    combined_df = pd.concat(all_trades, ignore_index=True)

    # 日付型に変換
    combined_df['entry_time'] = pd.to_datetime(combined_df['entry_time'])
    combined_df['entry_date'] = combined_df['entry_time'].dt.date

    # 期間フィルタ
    combined_df = combined_df[combined_df['entry_date'] >= pd.to_datetime(start_date).date()]

    print(f"総トレード数: {len(combined_df)}回")

    # 曜日を追加（0=月曜, 4=金曜）
    combined_df['weekday'] = combined_df['entry_time'].dt.dayofweek

    # 日本語曜日名
    weekday_jp = {
        0: '月曜日',
        1: '火曜日',
        2: '水曜日',
        3: '木曜日',
        4: '金曜日'
    }
    combined_df['weekday_jp'] = combined_df['weekday'].map(weekday_jp)

    print("\n" + "=" * 80)
    print("曜日別戦略パフォーマンス（方向性無視）")
    print("=" * 80)

    # 曜日別集計
    weekday_stats = []

    for day in range(5):  # 月〜金
        day_df = combined_df[combined_df['weekday'] == day]

        if len(day_df) == 0:
            continue

        total_pnl = day_df['pnl'].sum()
        total_trades = len(day_df)
        wins = len(day_df[day_df['pnl'] > 0])
        losses = len(day_df[day_df['pnl'] <= 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0

        # PF計算
        profits = day_df[day_df['pnl'] > 0]['pnl'].sum()
        losses_sum = abs(day_df[day_df['pnl'] < 0]['pnl'].sum())
        pf = profits / losses_sum if losses_sum > 0 else float('inf')

        # 平均損益
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

        # 平均利益・平均損失
        avg_win = profits / wins if wins > 0 else 0
        avg_loss = losses_sum / (losses - len(day_df[day_df['pnl'] == 0])) if (losses - len(day_df[day_df['pnl'] == 0])) > 0 else 0

        # 利益目標達成率
        profit_targets = len(day_df[day_df['reason'] == 'profit'])
        profit_target_rate = profit_targets / total_trades * 100 if total_trades > 0 else 0

        # 損切り率
        stop_losses = len(day_df[day_df['reason'] == 'loss'])
        stop_loss_rate = stop_losses / total_trades * 100 if total_trades > 0 else 0

        # 日数（取引が発生した日数）
        trading_days = day_df['entry_date'].nunique()

        # 1日あたりの平均損益
        avg_pnl_per_day = total_pnl / trading_days if trading_days > 0 else 0

        weekday_stats.append({
            'weekday': day,
            'weekday_jp': weekday_jp[day],
            'total_pnl': total_pnl,
            'trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'pf': pf,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_target_rate': profit_target_rate,
            'stop_loss_rate': stop_loss_rate,
            'trading_days': trading_days,
            'avg_pnl_per_day': avg_pnl_per_day
        })

    stats_df = pd.DataFrame(weekday_stats)

    # サマリー表示
    print("\n曜日別パフォーマンス:")
    print("-" * 80)

    for _, row in stats_df.iterrows():
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"

        print(f"\n【{row['weekday_jp']}】")
        print(f"  総損益: {row['total_pnl']:>12,.0f}円")
        print(f"  トレード数: {row['trades']:>6,}回 ({row['trading_days']}日)")
        print(f"  勝率: {row['win_rate']:>6.1f}% ({row['wins']}勝 {row['losses']}敗)")
        print(f"  PF: {pf_str:>6s}")
        print(f"  平均損益/回: {row['avg_pnl']:>10,.0f}円")
        print(f"  平均損益/日: {row['avg_pnl_per_day']:>10,.0f}円")
        print(f"  平均利益: {row['avg_win']:>10,.0f}円")
        print(f"  平均損失: {row['avg_loss']:>10,.0f}円")
        print(f"  利益目標達成率: {row['profit_target_rate']:>5.1f}%")
        print(f"  損切り率: {row['stop_loss_rate']:>5.1f}%")

    # ランキング
    print("\n" + "=" * 80)
    print("曜日別ランキング")
    print("=" * 80)

    # 総損益ランキング
    print("\n【総損益ランキング】")
    sorted_pnl = stats_df.sort_values('total_pnl', ascending=False)
    for i, (_, row) in enumerate(sorted_pnl.iterrows(), 1):
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
        print(f"  {i}位: {row['weekday_jp']} {row['total_pnl']:>12,.0f}円 (PF:{pf_str}, 勝率:{row['win_rate']:.1f}%)")

    # 勝率ランキング
    print("\n【勝率ランキング】")
    sorted_wr = stats_df.sort_values('win_rate', ascending=False)
    for i, (_, row) in enumerate(sorted_wr.iterrows(), 1):
        print(f"  {i}位: {row['weekday_jp']} {row['win_rate']:>5.1f}% ({row['trades']}回)")

    # PFランキング
    print("\n【プロフィットファクター(PF)ランキング】")
    sorted_pf = stats_df.sort_values('pf', ascending=False)
    for i, (_, row) in enumerate(sorted_pf.iterrows(), 1):
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
        print(f"  {i}位: {row['weekday_jp']} {pf_str}")

    # 平均損益/日ランキング
    print("\n【平均損益/日ランキング】")
    sorted_avg_day = stats_df.sort_values('avg_pnl_per_day', ascending=False)
    for i, (_, row) in enumerate(sorted_avg_day.iterrows(), 1):
        print(f"  {i}位: {row['weekday_jp']} {row['avg_pnl_per_day']:>10,.0f}円/日")

    # 戦略有効性の判定
    print("\n" + "=" * 80)
    print("戦略有効性の判定")
    print("=" * 80)

    print("\n【PF > 1.0 の曜日】（戦略が機能している）")
    profitable = stats_df[stats_df['pf'] > 1.0]
    if len(profitable) > 0:
        for _, row in profitable.iterrows():
            print(f"  ✅ {row['weekday_jp']}: PF {row['pf']:.2f}, 勝率 {row['win_rate']:.1f}%, 総損益 {row['total_pnl']:,.0f}円")
    else:
        print("  なし")

    print("\n【PF < 1.0 の曜日】（戦略が機能していない）")
    unprofitable = stats_df[stats_df['pf'] < 1.0]
    if len(unprofitable) > 0:
        for _, row in unprofitable.iterrows():
            print(f"  ❌ {row['weekday_jp']}: PF {row['pf']:.2f}, 勝率 {row['win_rate']:.1f}%, 総損益 {row['total_pnl']:,.0f}円")
    else:
        print("  なし")

    print("\n【PF = 1.0 付近の曜日】（損益トントン）")
    breakeven = stats_df[(stats_df['pf'] >= 0.98) & (stats_df['pf'] <= 1.02)]
    if len(breakeven) > 0:
        for _, row in breakeven.iterrows():
            print(f"  ⚖️  {row['weekday_jp']}: PF {row['pf']:.2f}, 勝率 {row['win_rate']:.1f}%, 総損益 {row['total_pnl']:,.0f}円")
    else:
        print("  なし")

    # 統計的分析
    print("\n" + "=" * 80)
    print("統計的分析")
    print("=" * 80)

    avg_pf = stats_df[stats_df['pf'] != float('inf')]['pf'].mean()
    avg_win_rate = stats_df['win_rate'].mean()
    avg_pnl_per_day = stats_df['avg_pnl_per_day'].mean()

    print(f"\n全曜日平均:")
    print(f"  平均PF: {avg_pf:.2f}")
    print(f"  平均勝率: {avg_win_rate:.1f}%")
    print(f"  平均損益/日: {avg_pnl_per_day:,.0f}円")

    best_day = stats_df.loc[stats_df['total_pnl'].idxmax()]
    worst_day = stats_df.loc[stats_df['total_pnl'].idxmin()]

    print(f"\n最良の曜日: {best_day['weekday_jp']}")
    print(f"  総損益: {best_day['total_pnl']:,.0f}円")
    print(f"  PF: {best_day['pf']:.2f}")
    print(f"  勝率: {best_day['win_rate']:.1f}%")
    print(f"  → 戦略が最も有効")

    print(f"\n最悪の曜日: {worst_day['weekday_jp']}")
    print(f"  総損益: {worst_day['total_pnl']:,.0f}円")
    print(f"  PF: {worst_day['pf']:.2f}")
    print(f"  勝率: {worst_day['win_rate']:.1f}%")
    print(f"  → 戦略が最も機能していない")

    # 結論
    print("\n" + "=" * 80)
    print("結論")
    print("=" * 80)

    profitable_days = len(stats_df[stats_df['pf'] > 1.0])
    total_days = len(stats_df)

    print(f"\n✅ 戦略が有効な曜日: {profitable_days} / {total_days}日")
    print(f"❌ 戦略が無効な曜日: {total_days - profitable_days} / {total_days}日")

    if profitable_days > total_days / 2:
        print("\n👍 この戦略は全体的に有効です。")
    elif profitable_days == total_days / 2:
        print("\n⚖️  この戦略は曜日によって効果が分かれます。")
    else:
        print("\n👎 この戦略は全体的に苦戦しています。曜日を選択的にトレードすることを推奨します。")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)

    return stats_df


if __name__ == "__main__":
    analyze_weekday_strategy_effectiveness()
