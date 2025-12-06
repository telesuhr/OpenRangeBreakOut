#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
利食い・損切りの連続性分析スクリプト

利食いが出た翌日に再び利食いが出る確率や、
前日の結果が翌日のパフォーマンスに与える影響を分析する。
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.backtester.engine import BacktestEngine


def analyze_exit_continuity(config_path: str = "config/strategy_config.yaml"):
    """利食い・損切りの連続性を分析"""

    print("=" * 80)
    print("利食い・損切り連続性分析")
    print("=" * 80)

    # 設定読み込み
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    start_date = config['backtest_period']['start_date']
    end_date = config['backtest_period']['end_date']
    stocks = [(code, name) for code, name in config['stocks']]

    print(f"\n期間: {start_date} ～ {end_date}")
    print(f"銘柄数: {len(stocks)}")

    # バックテストエンジン初期化
    engine = BacktestEngine(config)

    # 全銘柄のバックテスト実行
    print("\nバックテスト実行中...")
    results = engine.run_backtest_for_stocks(stocks, start_date, end_date)

    print(f"バックテスト完了: {len(results)}銘柄")

    # 日次結果を集計
    daily_data = []

    for symbol, result in results.items():
        symbol_code, symbol_name = symbol
        trades = result.get('trades', [])

        if not trades:
            continue

        # 日付ごとにトレードを整理
        trades_by_date = {}
        for trade in trades:
            trade_date = pd.to_datetime(trade['entry_time']).date()
            if trade_date not in trades_by_date:
                trades_by_date[trade_date] = []
            trades_by_date[trade_date].append(trade)

        # 日付順にソート
        sorted_dates = sorted(trades_by_date.keys())

        for i, date in enumerate(sorted_dates):
            trades_on_date = trades_by_date[date]

            # その日のトレード結果を集計
            total_pnl = sum(t['pnl'] for t in trades_on_date)
            exit_reasons = [t['exit_reason'] for t in trades_on_date]

            # 主要な終了理由を判定
            if any('利益目標' in reason for reason in exit_reasons):
                main_exit = 'profit_target'
            elif any('ストップロス' in reason for reason in exit_reasons):
                main_exit = 'stop_loss'
            elif any('強制決済' in reason for reason in exit_reasons):
                main_exit = 'force_exit'
            else:
                main_exit = 'other'

            # 前日の結果を取得
            prev_exit = None
            prev_pnl = None
            if i > 0:
                prev_date = sorted_dates[i-1]
                prev_trades = trades_by_date[prev_date]
                prev_pnl = sum(t['pnl'] for t in prev_trades)
                prev_reasons = [t['exit_reason'] for t in prev_trades]

                if any('利益目標' in reason for reason in prev_reasons):
                    prev_exit = 'profit_target'
                elif any('ストップロス' in reason for reason in prev_reasons):
                    prev_exit = 'stop_loss'
                elif any('強制決済' in reason for reason in prev_reasons):
                    prev_exit = 'force_exit'
                else:
                    prev_exit = 'other'

            daily_data.append({
                'symbol_code': symbol_code,
                'symbol_name': symbol_name,
                'date': date,
                'pnl': total_pnl,
                'exit_reason': main_exit,
                'prev_exit_reason': prev_exit,
                'prev_pnl': prev_pnl,
                'trade_count': len(trades_on_date)
            })

    df = pd.DataFrame(daily_data)

    if len(df) == 0:
        print("分析対象のデータがありません")
        return

    print(f"\n総取引日数: {len(df)}")

    # 分析1: 前日の結果別の翌日勝率
    print("\n" + "=" * 80)
    print("【分析1】前日の結果が翌日のパフォーマンスに与える影響")
    print("=" * 80)

    df_with_prev = df[df['prev_exit_reason'].notna()].copy()

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

    all_profit_days = len(df[df['exit_reason'] == 'profit_target'])
    total_days = len(df)

    print(f"\n全期間の利益目標達成率: {all_profit_days/total_days*100:.1f}% ({all_profit_days}/{total_days})")

    if profit_days_with_prev > 0:
        consecutive_rate = profit_follows_profit / profit_days_with_prev * 100
        print(f"前日利食い後の翌日利食い率: {consecutive_rate:.1f}% ({profit_follows_profit}/{profit_days_with_prev})")
        print(f"→ 通常の{consecutive_rate/(all_profit_days/total_days*100):.2f}倍の確率")

    # 分析3: 連続損切りの確率
    print("\n" + "=" * 80)
    print("【分析3】連続損切りの分析")
    print("=" * 80)

    loss_follows_loss = len(df_with_prev[
        (df_with_prev['prev_exit_reason'] == 'stop_loss') &
        (df_with_prev['exit_reason'] == 'stop_loss')
    ])
    loss_days_with_prev = len(df_with_prev[df_with_prev['prev_exit_reason'] == 'stop_loss'])

    all_loss_days = len(df[df['exit_reason'] == 'stop_loss'])

    print(f"\n全期間の損切り率: {all_loss_days/total_days*100:.1f}% ({all_loss_days}/{total_days})")

    if loss_days_with_prev > 0:
        consecutive_loss_rate = loss_follows_loss / loss_days_with_prev * 100
        print(f"前日損切り後の翌日損切り率: {consecutive_loss_rate:.1f}% ({loss_follows_loss}/{loss_days_with_prev})")
        print(f"→ 通常の{consecutive_loss_rate/(all_loss_days/total_days*100):.2f}倍の確率")

    # 分析4: 銘柄別の連続性
    print("\n" + "=" * 80)
    print("【分析4】連続利食い率が高い銘柄TOP10")
    print("=" * 80)

    symbol_stats = []

    for symbol in df['symbol_code'].unique():
        symbol_df = df[df['symbol_code'] == symbol].copy()
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
            symbol_name = symbol_df['symbol_name'].iloc[0]

            symbol_stats.append({
                'symbol_code': symbol,
                'symbol_name': symbol_name,
                'consecutive_profit_rate': consecutive_rate,
                'profit_count': symbol_profit_days,
                'consecutive_count': symbol_profit_follows
            })

    symbol_stats_df = pd.DataFrame(symbol_stats).sort_values('consecutive_profit_rate', ascending=False)

    print("\n順位 | 銘柄コード | 銘柄名 | 連続利食い率 | 前日利食い回数 | 連続回数")
    print("-" * 90)

    for i, row in symbol_stats_df.head(10).iterrows():
        print(f"{symbol_stats_df.index.get_loc(i)+1:2d}位 | {row['symbol_code']:8s} | {row['symbol_name']:20s} | "
              f"{row['consecutive_profit_rate']:6.1f}% | {row['profit_count']:4.0f}回 | {row['consecutive_count']:4.0f}回")

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
        print(f"→ 統計的に有意（p < 0.05）: 前日の結果が翌日に影響を与えている可能性が高い")
    else:
        print(f"→ 統計的に有意ではない（p >= 0.05）: 前日の結果が翌日に影響を与えているとは言えない")

    # 結果をCSVに保存
    output_dir = Path("analysis_reports")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(output_dir / f"exit_continuity_daily_{timestamp}.csv", index=False, encoding='utf-8-sig')
    symbol_stats_df.to_csv(output_dir / f"exit_continuity_symbols_{timestamp}.csv", index=False, encoding='utf-8-sig')

    print(f"\n分析結果を保存しました:")
    print(f"  - {output_dir}/exit_continuity_daily_{timestamp}.csv")
    print(f"  - {output_dir}/exit_continuity_symbols_{timestamp}.csv")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == "__main__":
    analyze_exit_continuity()
