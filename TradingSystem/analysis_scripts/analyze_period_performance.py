#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期間別パフォーマンス分析

バックテスト結果を前半と後半に分けて分析し、
パフォーマンスの変化を確認する
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def analyze_period_performance(result_folder: str = "Output/20251203_081519"):
    """期間別パフォーマンス分析"""

    print("=" * 80)
    print("期間別パフォーマンス分析")
    print("=" * 80)

    output_path = Path(result_folder)

    # 全CSVファイル読み込み
    csv_files = list(output_path.glob("*_trades.csv"))

    print(f"\n銘柄数: {len(csv_files)}")

    # 期間設定
    split_date = '2025-04-01'  # 前半/後半の分割日

    first_half_results = []
    second_half_results = []

    for csv_file in csv_files:
        symbol = csv_file.stem.replace('_trades', '')

        try:
            df = pd.read_csv(csv_file)

            if len(df) == 0:
                continue

            df['entry_date'] = pd.to_datetime(df['entry_time']).dt.date

            # 前半（2024-12-01 ～ 2025-03-31）
            first_half = df[df['entry_date'] < pd.to_datetime(split_date).date()]

            # 後半（2025-04-01 ～ 2025-12-02）
            second_half = df[df['entry_date'] >= pd.to_datetime(split_date).date()]

            # 前半の統計
            if len(first_half) > 0:
                first_pnl = first_half['pnl'].sum()
                first_trades = len(first_half)
                first_wins = len(first_half[first_half['pnl'] > 0])
                first_win_rate = first_wins / first_trades * 100 if first_trades > 0 else 0

                first_profits = first_half[first_half['pnl'] > 0]['pnl'].sum() if first_wins > 0 else 0
                first_losses = abs(first_half[first_half['pnl'] < 0]['pnl'].sum())
                first_pf = first_profits / first_losses if first_losses > 0 else float('inf')

                first_half_results.append({
                    'symbol': symbol,
                    'pnl': first_pnl,
                    'trades': first_trades,
                    'win_rate': first_win_rate,
                    'pf': first_pf
                })

            # 後半の統計
            if len(second_half) > 0:
                second_pnl = second_half['pnl'].sum()
                second_trades = len(second_half)
                second_wins = len(second_half[second_half['pnl'] > 0])
                second_win_rate = second_wins / second_trades * 100 if second_trades > 0 else 0

                second_profits = second_half[second_half['pnl'] > 0]['pnl'].sum() if second_wins > 0 else 0
                second_losses = abs(second_half[second_half['pnl'] < 0]['pnl'].sum())
                second_pf = second_profits / second_losses if second_losses > 0 else float('inf')

                second_half_results.append({
                    'symbol': symbol,
                    'pnl': second_pnl,
                    'trades': second_trades,
                    'win_rate': second_win_rate,
                    'pf': second_pf
                })

        except Exception as e:
            print(f"エラー: {symbol}: {e}")
            continue

    # DataFrame化
    first_df = pd.DataFrame(first_half_results)
    second_df = pd.DataFrame(second_half_results)

    print("\n" + "=" * 80)
    print("【前半】2024-12-01 ～ 2025-03-31")
    print("=" * 80)

    if len(first_df) > 0:
        total_pnl = first_df['pnl'].sum()
        total_trades = first_df['trades'].sum()
        avg_win_rate = first_df['win_rate'].mean()
        avg_pf = first_df[first_df['pf'] != float('inf')]['pf'].mean()

        print(f"\n総損益: {total_pnl:,.0f}円")
        print(f"総トレード数: {total_trades:,}回")
        print(f"平均勝率: {avg_win_rate:.1f}%")
        print(f"平均PF: {avg_pf:.2f}")

        # 銘柄別（ワースト5）
        worst_first = first_df.sort_values('pnl').head(5)
        print("\n前半ワースト5:")
        for _, row in worst_first.iterrows():
            pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
            print(f"  {row['symbol']:10s}: {row['pnl']:>10,.0f}円 (PF:{pf_str}, 勝率:{row['win_rate']:.1f}%, {row['trades']}回)")

    print("\n" + "=" * 80)
    print("【後半】2025-04-01 ～ 2025-12-02")
    print("=" * 80)

    if len(second_df) > 0:
        total_pnl = second_df['pnl'].sum()
        total_trades = second_df['trades'].sum()
        avg_win_rate = second_df['win_rate'].mean()
        avg_pf = second_df[second_df['pf'] != float('inf')]['pf'].mean()

        print(f"\n総損益: {total_pnl:,.0f}円")
        print(f"総トレード数: {total_trades:,}回")
        print(f"平均勝率: {avg_win_rate:.1f}%")
        print(f"平均PF: {avg_pf:.2f}")

        # 銘柄別（ワースト5）
        worst_second = second_df.sort_values('pnl').head(5)
        print("\n後半ワースト5:")
        for _, row in worst_second.iterrows():
            pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
            print(f"  {row['symbol']:10s}: {row['pnl']:>10,.0f}円 (PF:{pf_str}, 勝率:{row['win_rate']:.1f}%, {row['trades']}回)")

    # トレード数が大幅に異なる銘柄を特定
    print("\n" + "=" * 80)
    print("トレード数異常検知")
    print("=" * 80)

    # 両期間にデータがある銘柄のみ
    common_symbols = set(first_df['symbol']) & set(second_df['symbol'])

    for symbol in common_symbols:
        first_trades = first_df[first_df['symbol'] == symbol]['trades'].values[0]
        second_trades = second_df[second_df['symbol'] == symbol]['trades'].values[0]

        # 通常は前半（4ヶ月）が後半（8ヶ月）の約半分のトレード数になるはず
        expected_first_trades = second_trades * 0.5  # 期間比で計算

        if first_trades < expected_first_trades * 0.5:  # 期待値の50%未満
            first_pnl = first_df[first_df['symbol'] == symbol]['pnl'].values[0]
            second_pnl = second_df[second_df['symbol'] == symbol]['pnl'].values[0]
            print(f"\n⚠️ {symbol}:")
            print(f"  前半トレード数: {first_trades}回（期待値の{first_trades/expected_first_trades*100:.0f}%）")
            print(f"  後半トレード数: {second_trades}回")
            print(f"  前半損益: {first_pnl:,.0f}円")
            print(f"  後半損益: {second_pnl:,.0f}円")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)

    return first_df, second_df


if __name__ == "__main__":
    analyze_period_performance()
