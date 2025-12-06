#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曜日別パフォーマンス分析

バックテスト結果を曜日別に分析し、
曜日ごとの特徴やパターンを特定する
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np

def analyze_weekday_performance(result_folder: str = "Output/20251203_081519"):
    """曜日別パフォーマンス分析"""

    print("=" * 80)
    print("曜日別パフォーマンス分析")
    print("=" * 80)

    output_path = Path(result_folder)

    # 全CSVファイル読み込み
    csv_files = list(output_path.glob("*_trades.csv"))

    print(f"\n銘柄数: {len(csv_files)}")

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
    combined_df['exit_time'] = pd.to_datetime(combined_df['exit_time'])

    # 曜日を追加（0=月曜, 4=金曜）
    combined_df['weekday'] = combined_df['entry_time'].dt.dayofweek
    combined_df['weekday_name'] = combined_df['entry_time'].dt.day_name()

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
    print("曜日別統計サマリー")
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
        losses = len(day_df[day_df['pnl'] < 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0

        # 利益目標達成（reason == 'profit'）
        profit_targets = len(day_df[day_df['reason'] == 'profit'])
        profit_target_rate = profit_targets / total_trades * 100 if total_trades > 0 else 0

        # 損切り（reason == 'loss'）
        stop_losses = len(day_df[day_df['reason'] == 'loss'])
        stop_loss_rate = stop_losses / total_trades * 100 if total_trades > 0 else 0

        # 強制決済（reason == 'force' or 'day_end'）
        force_exits = len(day_df[(day_df['reason'] == 'force') | (day_df['reason'] == 'day_end')])
        force_exit_rate = force_exits / total_trades * 100 if total_trades > 0 else 0

        # PF計算
        profits = day_df[day_df['pnl'] > 0]['pnl'].sum()
        losses_sum = abs(day_df[day_df['pnl'] < 0]['pnl'].sum())
        pf = profits / losses_sum if losses_sum > 0 else float('inf')

        # 平均損益
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

        # 平均利益・平均損失
        avg_win = profits / wins if wins > 0 else 0
        avg_loss = losses_sum / losses if losses > 0 else 0

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
            'force_exit_rate': force_exit_rate
        })

    stats_df = pd.DataFrame(weekday_stats)

    # サマリー表示
    print("\n曜日別パフォーマンス:")
    print("-" * 80)

    for _, row in stats_df.iterrows():
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"

        print(f"\n【{row['weekday_jp']}】")
        print(f"  総損益: {row['total_pnl']:>12,.0f}円")
        print(f"  トレード数: {row['trades']:>6,}回")
        print(f"  勝率: {row['win_rate']:>6.1f}% ({row['wins']}勝 {row['losses']}敗)")
        print(f"  PF: {pf_str:>6s}")
        print(f"  平均損益: {row['avg_pnl']:>10,.0f}円/回")
        print(f"  平均利益: {row['avg_win']:>10,.0f}円")
        print(f"  平均損失: {row['avg_loss']:>10,.0f}円")
        print(f"  利益目標達成率: {row['profit_target_rate']:>5.1f}%")
        print(f"  損切り率: {row['stop_loss_rate']:>5.1f}%")
        print(f"  強制決済率: {row['force_exit_rate']:>5.1f}%")

    # ランキング
    print("\n" + "=" * 80)
    print("曜日別ランキング")
    print("=" * 80)

    # 総損益ランキング
    print("\n【総損益ランキング】")
    sorted_pnl = stats_df.sort_values('total_pnl', ascending=False)
    for i, (_, row) in enumerate(sorted_pnl.iterrows(), 1):
        print(f"  {i}位: {row['weekday_jp']} {row['total_pnl']:>12,.0f}円 (PF:{row['pf']:.2f})")

    # 勝率ランキング
    print("\n【勝率ランキング】")
    sorted_wr = stats_df.sort_values('win_rate', ascending=False)
    for i, (_, row) in enumerate(sorted_wr.iterrows(), 1):
        print(f"  {i}位: {row['weekday_jp']} {row['win_rate']:>5.1f}% ({row['trades']}回)")

    # 利益目標達成率ランキング
    print("\n【利益目標達成率ランキング】")
    sorted_pt = stats_df.sort_values('profit_target_rate', ascending=False)
    for i, (_, row) in enumerate(sorted_pt.iterrows(), 1):
        print(f"  {i}位: {row['weekday_jp']} {row['profit_target_rate']:>5.1f}% ({row['trades']}回)")

    # 平均損益ランキング
    print("\n【平均損益ランキング】")
    sorted_avg = stats_df.sort_values('avg_pnl', ascending=False)
    for i, (_, row) in enumerate(sorted_avg.iterrows(), 1):
        print(f"  {i}位: {row['weekday_jp']} {row['avg_pnl']:>10,.0f}円/回")

    # 統計的特徴
    print("\n" + "=" * 80)
    print("統計的特徴")
    print("=" * 80)

    print(f"\n全期間平均勝率: {stats_df['win_rate'].mean():.1f}%")
    print(f"全期間平均PF: {stats_df[stats_df['pf'] != float('inf')]['pf'].mean():.2f}")
    print(f"全期間平均損益/回: {stats_df['avg_pnl'].mean():,.0f}円")

    # 最良・最悪の曜日
    best_day = stats_df.loc[stats_df['total_pnl'].idxmax()]
    worst_day = stats_df.loc[stats_df['total_pnl'].idxmin()]

    print(f"\n最良の曜日: {best_day['weekday_jp']}")
    print(f"  総損益: {best_day['total_pnl']:,.0f}円")
    print(f"  勝率: {best_day['win_rate']:.1f}%")
    print(f"  PF: {best_day['pf']:.2f}")

    print(f"\n最悪の曜日: {worst_day['weekday_jp']}")
    print(f"  総損益: {worst_day['total_pnl']:,.0f}円")
    print(f"  勝率: {worst_day['win_rate']:.1f}%")
    print(f"  PF: {worst_day['pf']:.2f}")

    # 曜日ごとのボラティリティ
    print("\n" + "=" * 80)
    print("曜日別損益のばらつき")
    print("=" * 80)

    for day in range(5):
        day_df = combined_df[combined_df['weekday'] == day]
        if len(day_df) == 0:
            continue

        pnl_std = day_df['pnl'].std()
        pnl_median = day_df['pnl'].median()

        print(f"\n{weekday_jp[day]}:")
        print(f"  損益標準偏差: {pnl_std:>10,.0f}円（ばらつき大きい = ボラタイル）")
        print(f"  損益中央値: {pnl_median:>10,.0f}円")

    # LONG/SHORT別の曜日パフォーマンス
    print("\n" + "=" * 80)
    print("LONG/SHORT別 曜日パフォーマンス")
    print("=" * 80)

    for side in ['long', 'short']:
        print(f"\n【{side.upper()}】")
        side_df = combined_df[combined_df['side'] == side]

        for day in range(5):
            day_df = side_df[side_df['weekday'] == day]
            if len(day_df) == 0:
                continue

            total_pnl = day_df['pnl'].sum()
            trades = len(day_df)
            win_rate = len(day_df[day_df['pnl'] > 0]) / trades * 100 if trades > 0 else 0

            print(f"  {weekday_jp[day]}: {total_pnl:>12,.0f}円 (勝率:{win_rate:>5.1f}%, {trades}回)")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)

    return stats_df, combined_df


if __name__ == "__main__":
    analyze_weekday_performance()
