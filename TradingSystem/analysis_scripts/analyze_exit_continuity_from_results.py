#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
利食い・損切りの連続性分析スクリプト（既存結果から）

既存のバックテスト結果から、利食いが出た翌日に再び利食いが出る確率や、
前日の結果が翌日のパフォーマンスに与える影響を分析する。
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime


def load_latest_backtest_results(output_dir: str = "Output"):
    """最新のバックテスト結果を読み込む"""

    output_path = Path(output_dir)

    # タイムスタンプ付きフォルダを探す
    result_folders = [f for f in output_path.iterdir() if f.is_dir() and f.name.startswith('202')]

    if not result_folders:
        print(f"バックテスト結果が見つかりません: {output_dir}")
        return None

    # 最新のフォルダを取得
    latest_folder = max(result_folders, key=lambda x: x.name)

    print(f"最新のバックテスト結果: {latest_folder.name}")

    # 個別銘柄のCSVファイルを読み込む
    csv_files = list(latest_folder.glob("*_trades.csv"))

    if not csv_files:
        print(f"トレードデータが見つかりません: {latest_folder}")
        return None

    print(f"銘柄数: {len(csv_files)}")

    # すべてのトレードデータを読み込む
    all_trades = []

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if len(df) > 0:
                all_trades.append(df)
        except Exception as e:
            print(f"エラー: {csv_file.name}: {e}")

    if not all_trades:
        print("有効なトレードデータがありません")
        return None

    # すべてのトレードを結合
    combined_df = pd.concat(all_trades, ignore_index=True)

    print(f"総トレード数: {len(combined_df)}")

    return combined_df, latest_folder


def analyze_exit_continuity_from_df(df: pd.DataFrame):
    """DataFrameから連続性を分析"""

    print("\n" + "=" * 80)
    print("利食い・損切り連続性分析")
    print("=" * 80)

    # 日付列をdatetimeに変換
    df['entry_date'] = pd.to_datetime(df['entry_time']).dt.date

    # 日次結果を集計
    daily_data = []

    for symbol in df['symbol'].unique():
        symbol_df = df[df['symbol'] == symbol].sort_values('entry_time')

        # 日付ごとにグループ化
        for date, group in symbol_df.groupby('entry_date'):
            total_pnl = group['pnl'].sum()
            exit_reasons = group['reason'].values

            # 主要な終了理由を判定
            if any(str(reason) == 'profit' for reason in exit_reasons):
                main_exit = 'profit_target'
            elif any(str(reason) == 'loss' for reason in exit_reasons):
                main_exit = 'stop_loss'
            elif any(str(reason) in ['force', 'day_end'] for reason in exit_reasons):
                main_exit = 'force_exit'
            else:
                main_exit = 'other'

            daily_data.append({
                'symbol': symbol,
                'date': date,
                'pnl': total_pnl,
                'exit_reason': main_exit,
                'trade_count': len(group)
            })

    daily_df = pd.DataFrame(daily_data).sort_values(['symbol', 'date'])

    # 前日の結果を追加
    daily_df['prev_exit_reason'] = daily_df.groupby('symbol')['exit_reason'].shift(1)
    daily_df['prev_pnl'] = daily_df.groupby('symbol')['pnl'].shift(1)

    print(f"\n総取引日数: {len(daily_df)}")

    # 分析1: 前日の結果別の翌日勝率
    print("\n" + "=" * 80)
    print("【分析1】前日の結果が翌日のパフォーマンスに与える影響")
    print("=" * 80)

    df_with_prev = daily_df[daily_df['prev_exit_reason'].notna()].copy()

    for prev_reason in ['profit_target', 'stop_loss', 'force_exit', 'other']:
        subset = df_with_prev[df_with_prev['prev_exit_reason'] == prev_reason]

        if len(subset) == 0:
            continue

        # 翌日の結果集計
        next_profit = len(subset[subset['exit_reason'] == 'profit_target'])
        next_loss = len(subset[subset['exit_reason'] == 'stop_loss'])
        next_force = len(subset[subset['exit_reason'] == 'force_exit'])
        total = len(subset)

        avg_pnl = subset['pnl'].mean()

        reason_names = {
            'profit_target': '利益目標達成',
            'stop_loss': '損切り',
            'force_exit': '強制決済',
            'other': 'その他'
        }

        print(f"\n【前日: {reason_names[prev_reason]}】")
        print(f"  翌日のトレード数: {total}")
        print(f"  翌日の利益目標達成: {next_profit} ({next_profit/total*100:.1f}%)")
        print(f"  翌日の損切り: {next_loss} ({next_loss/total*100:.1f}%)")
        print(f"  翌日の強制決済: {next_force} ({next_force/total*100:.1f}%)")
        print(f"  翌日の平均損益: {avg_pnl:,.0f}円")

    # 分析2: 連続利食いの確率
    print("\n" + "=" * 80)
    print("【分析2】連続利食いの分析")
    print("=" * 80)

    profit_follows_profit = len(df_with_prev[
        (df_with_prev['prev_exit_reason'] == 'profit_target') &
        (df_with_prev['exit_reason'] == 'profit_target')
    ])
    profit_days_with_prev = len(df_with_prev[df_with_prev['prev_exit_reason'] == 'profit_target'])

    all_profit_days = len(daily_df[daily_df['exit_reason'] == 'profit_target'])
    total_days = len(daily_df)

    print(f"\n全期間の利益目標達成率: {all_profit_days/total_days*100:.1f}% ({all_profit_days}/{total_days})")

    if profit_days_with_prev > 0:
        consecutive_rate = profit_follows_profit / profit_days_with_prev * 100
        baseline_rate = all_profit_days / total_days * 100
        print(f"前日利食い後の翌日利食い率: {consecutive_rate:.1f}% ({profit_follows_profit}/{profit_days_with_prev})")
        print(f"→ 通常の{consecutive_rate/baseline_rate:.2f}倍の確率")

        if consecutive_rate > baseline_rate * 1.2:
            print(f"✅ モメンタム効果が確認できます（通常の1.2倍以上）")
        elif consecutive_rate < baseline_rate * 0.8:
            print(f"⚠️ 反転傾向があります（通常の0.8倍以下）")
        else:
            print(f"➖ 特に傾向は見られません")

    # 分析3: 連続損切りの確率
    print("\n" + "=" * 80)
    print("【分析3】連続損切りの分析")
    print("=" * 80)

    loss_follows_loss = len(df_with_prev[
        (df_with_prev['prev_exit_reason'] == 'stop_loss') &
        (df_with_prev['exit_reason'] == 'stop_loss')
    ])
    loss_days_with_prev = len(df_with_prev[df_with_prev['prev_exit_reason'] == 'stop_loss'])

    all_loss_days = len(daily_df[daily_df['exit_reason'] == 'stop_loss'])

    print(f"\n全期間の損切り率: {all_loss_days/total_days*100:.1f}% ({all_loss_days}/{total_days})")

    if loss_days_with_prev > 0:
        consecutive_loss_rate = loss_follows_loss / loss_days_with_prev * 100
        baseline_loss_rate = all_loss_days / total_days * 100
        print(f"前日損切り後の翌日損切り率: {consecutive_loss_rate:.1f}% ({loss_follows_loss}/{loss_days_with_prev})")
        print(f"→ 通常の{consecutive_loss_rate/baseline_loss_rate:.2f}倍の確率")

    # 分析4: 銘柄別の連続性
    print("\n" + "=" * 80)
    print("【分析4】連続利食い率が高い銘柄TOP10")
    print("=" * 80)

    symbol_stats = []

    for symbol in daily_df['symbol'].unique():
        symbol_df = daily_df[daily_df['symbol'] == symbol].copy()
        symbol_df_with_prev = symbol_df[symbol_df['prev_exit_reason'].notna()]

        if len(symbol_df_with_prev) == 0:
            continue

        # 前日利食い後の翌日利食い
        symbol_profit_follows = len(symbol_df_with_prev[
            (symbol_df_with_prev['prev_exit_reason'] == 'profit_target') &
            (symbol_df_with_prev['exit_reason'] == 'profit_target')
        ])
        symbol_profit_days = len(symbol_df_with_prev[symbol_df_with_prev['prev_exit_reason'] == 'profit_target'])

        if symbol_profit_days >= 3:  # 最低3回以上の利食い
            consecutive_rate = symbol_profit_follows / symbol_profit_days * 100

            symbol_stats.append({
                'symbol': symbol,
                'consecutive_profit_rate': consecutive_rate,
                'profit_count': symbol_profit_days,
                'consecutive_count': symbol_profit_follows
            })

    if len(symbol_stats) > 0:
        symbol_stats_df = pd.DataFrame(symbol_stats).sort_values('consecutive_profit_rate', ascending=False)

        print("\n順位 | 銘柄コード | 連続利食い率 | 前日利食い回数 | 連続回数")
        print("-" * 70)

        for idx, row in symbol_stats_df.head(10).iterrows():
            rank = list(symbol_stats_df.index).index(idx) + 1
            print(f"{rank:2d}位 | {row['symbol']:10s} | {row['consecutive_profit_rate']:6.1f}% | "
                  f"{row['profit_count']:4.0f}回 | {row['consecutive_count']:4.0f}回")

    # 分析5: 統計的有意性の検証
    print("\n" + "=" * 80)
    print("【分析5】統計的有意性検証（カイ二乗検定）")
    print("=" * 80)

    # 前日利食い後の翌日結果
    profit_after_profit = len(df_with_prev[
        (df_with_prev['prev_exit_reason'] == 'profit_target') &
        (df_with_prev['exit_reason'] == 'profit_target')
    ])
    no_profit_after_profit = len(df_with_prev[
        (df_with_prev['prev_exit_reason'] == 'profit_target') &
        (df_with_prev['exit_reason'] != 'profit_target')
    ])

    # 前日利食い以外の後の翌日結果
    profit_after_other = len(df_with_prev[
        (df_with_prev['prev_exit_reason'] != 'profit_target') &
        (df_with_prev['exit_reason'] == 'profit_target')
    ])
    no_profit_after_other = len(df_with_prev[
        (df_with_prev['prev_exit_reason'] != 'profit_target') &
        (df_with_prev['exit_reason'] != 'profit_target')
    ])

    # カイ二乗検定
    from scipy.stats import chi2_contingency

    contingency_table = np.array([
        [profit_after_profit, no_profit_after_profit],
        [profit_after_other, no_profit_after_other]
    ])

    chi2, p_value, dof, expected = chi2_contingency(contingency_table)

    print(f"\nクロス集計表:")
    print(f"                    翌日利食い  翌日非利食い")
    print(f"前日利食い          {profit_after_profit:6d}      {no_profit_after_profit:6d}")
    print(f"前日非利食い        {profit_after_other:6d}      {no_profit_after_other:6d}")
    print(f"\nカイ二乗値: {chi2:.4f}")
    print(f"p値: {p_value:.6f}")

    if p_value < 0.05:
        print(f"✅ 統計的に有意（p < 0.05）: 前日の結果が翌日に影響を与えている可能性が高い")
    elif p_value < 0.10:
        print(f"⚠️ やや有意（p < 0.10）: 前日の結果が翌日に影響を与えている可能性がある")
    else:
        print(f"➖ 統計的に有意ではない（p >= 0.10）: 前日の結果が翌日に影響を与えているとは言えない")

    return daily_df, symbol_stats_df if len(symbol_stats) > 0 else None


def main():
    """メイン処理"""

    # 最新のバックテスト結果を読み込む
    result = load_latest_backtest_results()

    if result is None:
        return

    trades_df, latest_folder = result

    # 連続性を分析
    daily_df, symbol_stats_df = analyze_exit_continuity_from_df(trades_df)

    # 結果をCSVに保存
    output_dir = Path("analysis_reports")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    daily_df.to_csv(output_dir / f"exit_continuity_daily_{timestamp}.csv", index=False, encoding='utf-8-sig')

    if symbol_stats_df is not None:
        symbol_stats_df.to_csv(output_dir / f"exit_continuity_symbols_{timestamp}.csv", index=False, encoding='utf-8-sig')

    print(f"\n分析結果を保存しました:")
    print(f"  - {output_dir}/exit_continuity_daily_{timestamp}.csv")
    if symbol_stats_df is not None:
        print(f"  - {output_dir}/exit_continuity_symbols_{timestamp}.csv")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
