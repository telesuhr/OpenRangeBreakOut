#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直近2日間で利食いに到達した銘柄を分析
12月1日・12月2日に利食い到達した銘柄をピックアップし、パフォーマンスを評価
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np


def analyze_recent_profit_stocks(output_folder: str = "Output/20251202_234549"):
    """直近2日間で利食いに到達した銘柄を分析"""

    print("=" * 80)
    print("直近2日間 利食い到達銘柄分析")
    print("=" * 80)

    output_path = Path(output_folder)

    if not output_path.exists():
        print(f"エラー: フォルダが見つかりません: {output_folder}")
        return

    # 対象日（12月1日・12月2日）
    target_dates = ['2025-12-01', '2025-12-02']
    print(f"\n対象日: {', '.join(target_dates)}")

    # 全CSVファイル読み込み
    csv_files = list(output_path.glob("*_trades.csv"))
    print(f"銘柄数: {len(csv_files)}")

    results = []

    for csv_file in csv_files:
        symbol = csv_file.stem.replace('_trades', '')

        try:
            df = pd.read_csv(csv_file)

            if len(df) == 0:
                continue

            # entry_timeをdatetimeに変換
            df['entry_date'] = pd.to_datetime(df['entry_time']).dt.date
            df['entry_date_str'] = df['entry_date'].astype(str)

            # 直近2日間のトレードを抽出
            recent_trades = df[df['entry_date_str'].isin(target_dates)]

            if len(recent_trades) == 0:
                continue

            # 直近2日間で利食いがあったか
            profit_trades = recent_trades[recent_trades['reason'] == 'profit']
            has_recent_profit = len(profit_trades) > 0

            # 12月1日に利食いがあったか
            dec1_profit = len(recent_trades[
                (recent_trades['entry_date_str'] == '2025-12-01') &
                (recent_trades['reason'] == 'profit')
            ]) > 0

            # 12月2日に利食いがあったか
            dec2_profit = len(recent_trades[
                (recent_trades['entry_date_str'] == '2025-12-02') &
                (recent_trades['reason'] == 'profit')
            ]) > 0

            # 全期間のパフォーマンス集計
            total_trades = len(df)
            total_pnl = df['pnl'].sum()
            total_return = df['return'].sum()

            # 勝ちトレード
            winning_trades = df[df['pnl'] > 0]
            win_count = len(winning_trades)
            avg_win = winning_trades['pnl'].mean() if win_count > 0 else 0

            # 負けトレード
            losing_trades = df[df['pnl'] < 0]
            loss_count = len(losing_trades)
            avg_loss = losing_trades['pnl'].mean() if loss_count > 0 else 0

            # 勝率
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

            # プロフィットファクター
            total_profit = winning_trades['pnl'].sum() if win_count > 0 else 0
            total_loss = abs(losing_trades['pnl'].sum()) if loss_count > 0 else 0
            pf = (total_profit / total_loss) if total_loss > 0 else float('inf')

            # 利食い回数
            profit_count = len(df[df['reason'] == 'profit'])
            profit_rate = (profit_count / total_trades * 100) if total_trades > 0 else 0

            # 損切り回数
            loss_exit_count = len(df[df['reason'] == 'loss'])
            loss_rate = (loss_exit_count / total_trades * 100) if total_trades > 0 else 0

            results.append({
                'symbol': symbol,
                'dec1_profit': dec1_profit,
                'dec2_profit': dec2_profit,
                'recent_profit_both': dec1_profit and dec2_profit,
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'total_return_pct': total_return * 100,
                'win_rate': win_rate,
                'pf': pf,
                'profit_rate': profit_rate,
                'loss_rate': loss_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'recent_trades_count': len(recent_trades),
                'recent_profit_count': len(profit_trades)
            })

        except Exception as e:
            print(f"エラー: {symbol}: {e}")
            continue

    if not results:
        print("\n該当する銘柄がありません")
        return

    # DataFrame化
    results_df = pd.DataFrame(results)

    # 12月2日に利食いがあった銘柄（最優先）
    dec2_profit_stocks = results_df[results_df['dec2_profit']].copy()

    # 12月1日のみ利食いがあった銘柄
    dec1_only_profit_stocks = results_df[
        results_df['dec1_profit'] & ~results_df['dec2_profit']
    ].copy()

    # 両日とも利食いがあった銘柄
    both_days_profit_stocks = results_df[results_df['recent_profit_both']].copy()

    print("\n" + "=" * 80)
    print("【最優先】12月2日に利食い到達した銘柄")
    print("=" * 80)

    if len(dec2_profit_stocks) > 0:
        # PFでソート
        dec2_profit_stocks_sorted = dec2_profit_stocks.sort_values('pf', ascending=False)

        print(f"\n該当銘柄数: {len(dec2_profit_stocks)}")
        print("\n銘柄コード | PF    | 勝率  | 総損益     | 利食率 | 両日達成")
        print("-" * 75)

        for _, row in dec2_profit_stocks_sorted.iterrows():
            both_mark = "★" if row['recent_profit_both'] else " "
            pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
            print(f"{row['symbol']:10s} | {pf_str:5s} | {row['win_rate']:4.1f}% | "
                  f"{row['total_pnl']:>10,.0f}円 | {row['profit_rate']:4.1f}% | {both_mark}")
    else:
        print("\n該当なし")

    print("\n" + "=" * 80)
    print("【参考】12月1日のみ利食い到達（12月2日は未達成）")
    print("=" * 80)

    if len(dec1_only_profit_stocks) > 0:
        dec1_only_sorted = dec1_only_profit_stocks.sort_values('pf', ascending=False)

        print(f"\n該当銘柄数: {len(dec1_only_profit_stocks)}")
        print("\n銘柄コード | PF    | 勝率  | 総損益     | 利食率")
        print("-" * 65)

        for _, row in dec1_only_sorted.iterrows():
            pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
            print(f"{row['symbol']:10s} | {pf_str:5s} | {row['win_rate']:4.1f}% | "
                  f"{row['total_pnl']:>10,.0f}円 | {row['profit_rate']:4.1f}%")
    else:
        print("\n該当なし")

    print("\n" + "=" * 80)
    print("【特筆】両日連続で利食い到達した銘柄（超高確率）")
    print("=" * 80)

    if len(both_days_profit_stocks) > 0:
        both_sorted = both_days_profit_stocks.sort_values('pf', ascending=False)

        print(f"\n該当銘柄数: {len(both_days_profit_stocks)}")
        print("\n銘柄コード | PF    | 勝率  | 総損益     | 利食率 | 平均勝")
        print("-" * 75)

        for _, row in both_sorted.iterrows():
            pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
            print(f"{row['symbol']:10s} | {pf_str:5s} | {row['win_rate']:4.1f}% | "
                  f"{row['total_pnl']:>10,.0f}円 | {row['profit_rate']:4.1f}% | {row['avg_win']:>8,.0f}円")
    else:
        print("\n該当なし")

    print("\n" + "=" * 80)
    print("推奨基準によるフィルタリング")
    print("=" * 80)

    # 12月2日利食い銘柄のうち、推奨基準を満たすもの
    recommended = dec2_profit_stocks[
        (dec2_profit_stocks['pf'] > 1.2) &
        (dec2_profit_stocks['win_rate'] > 40)
    ].copy()

    if len(recommended) > 0:
        recommended_sorted = recommended.sort_values(
            ['recent_profit_both', 'pf'],
            ascending=[False, False]
        )

        print(f"\n推奨銘柄数: {len(recommended)} (PF > 1.2 かつ 勝率 > 40%)")
        print("\n優先度 | 銘柄コード | PF    | 勝率  | 総損益     | 利食率 | 連続")
        print("-" * 80)

        for idx, (_, row) in enumerate(recommended_sorted.iterrows(), 1):
            priority = "最優先" if row['recent_profit_both'] else "優先  "
            pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
            consecutive = "両日★" if row['recent_profit_both'] else "2日目"

            print(f"{priority} | {row['symbol']:10s} | {pf_str:5s} | {row['win_rate']:4.1f}% | "
                  f"{row['total_pnl']:>10,.0f}円 | {row['profit_rate']:4.1f}% | {consecutive}")
    else:
        print("\n推奨基準を満たす銘柄なし（基準緩和を検討）")

        # 基準緩和版
        relaxed = dec2_profit_stocks[
            (dec2_profit_stocks['pf'] > 1.0) &
            (dec2_profit_stocks['win_rate'] > 35)
        ].copy()

        if len(relaxed) > 0:
            print(f"\n【緩和基準】推奨銘柄数: {len(relaxed)} (PF > 1.0 かつ 勝率 > 35%)")
            relaxed_sorted = relaxed.sort_values(
                ['recent_profit_both', 'pf'],
                ascending=[False, False]
            )

            print("\n優先度 | 銘柄コード | PF    | 勝率  | 総損益     | 連続")
            print("-" * 70)

            for idx, (_, row) in enumerate(relaxed_sorted.iterrows(), 1):
                priority = "最優先" if row['recent_profit_both'] else "優先  "
                pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
                consecutive = "両日★" if row['recent_profit_both'] else "2日目"

                print(f"{priority} | {row['symbol']:10s} | {pf_str:5s} | {row['win_rate']:4.1f}% | "
                      f"{row['total_pnl']:>10,.0f}円 | {consecutive}")

    print("\n" + "=" * 80)
    print("分析結果サマリー")
    print("=" * 80)

    print(f"\n全銘柄数: {len(results_df)}")
    print(f"12月2日利食い到達: {len(dec2_profit_stocks)}銘柄")
    print(f"12月1日のみ利食い: {len(dec1_only_profit_stocks)}銘柄")
    print(f"両日連続利食い: {len(both_days_profit_stocks)}銘柄")

    # 統計情報
    if len(dec2_profit_stocks) > 0:
        print(f"\n【12月2日利食い銘柄の統計】")
        print(f"平均PF: {dec2_profit_stocks['pf'].mean():.2f}")
        print(f"平均勝率: {dec2_profit_stocks['win_rate'].mean():.1f}%")
        print(f"平均利食率: {dec2_profit_stocks['profit_rate'].mean():.1f}%")
        print(f"合計損益: {dec2_profit_stocks['total_pnl'].sum():,.0f}円")

    # CSVに保存
    output_csv = Path("analysis_reports/recent_profit_analysis.csv")
    output_csv.parent.mkdir(exist_ok=True)
    results_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n詳細データを保存: {output_csv}")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)

    return results_df, dec2_profit_stocks, both_days_profit_stocks


if __name__ == "__main__":
    analyze_recent_profit_stocks()
