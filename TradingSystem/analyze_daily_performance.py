#!/usr/bin/env python3
"""
日別パフォーマンス分析
- 3ヶ月間で悪い日がどれくらいの頻度で発生するか
- 悪い日の特徴を分析
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

def analyze_daily_performance():
    """日別のパフォーマンスを分析"""

    # ATRモードの結果を使用（より正確なパフォーマンス）
    output_dir = Path("Output/20251119_221548")

    print("\n" + "=" * 80)
    print("日別パフォーマンス分析（2025-05-18 ～ 2025-11-18）")
    print("=" * 80)

    # 全トレードデータを読み込み
    all_trades = []
    for trades_file in sorted(output_dir.glob("*_trades.csv")):
        df = pd.read_csv(trades_file)
        if len(df) > 0:
            df['symbol'] = trades_file.stem.replace("_trades", "")
            all_trades.append(df)

    if not all_trades:
        print("データなし")
        return

    df_all = pd.concat(all_trades, ignore_index=True)

    # entry_timeを日付に変換
    df_all['entry_time'] = pd.to_datetime(df_all['entry_time'])
    df_all['date'] = df_all['entry_time'].dt.date

    # 日別集計
    daily_stats = df_all.groupby('date').agg({
        'pnl': ['sum', 'mean', 'count'],
        'symbol': 'count'
    }).reset_index()

    daily_stats.columns = ['date', 'total_pnl', 'avg_pnl', 'trade_count', 'trade_count2']
    daily_stats = daily_stats.drop('trade_count2', axis=1)

    # 勝率計算
    daily_wins = df_all[df_all['pnl'] > 0].groupby('date').size()
    daily_stats['wins'] = daily_stats['date'].map(daily_wins).fillna(0).astype(int)
    daily_stats['win_rate'] = (daily_stats['wins'] / daily_stats['trade_count'] * 100).round(1)

    # ソート（損益順）
    daily_stats_sorted = daily_stats.sort_values('total_pnl')

    print(f"\n【基本統計】")
    print(f"取引日数: {len(daily_stats)}日")
    print(f"総損益: {daily_stats['total_pnl'].sum():+,.0f}円")
    print(f"平均日次損益: {daily_stats['total_pnl'].mean():+,.0f}円")
    print(f"中央値: {daily_stats['total_pnl'].median():+,.0f}円")

    # プラス/マイナスの日数
    positive_days = len(daily_stats[daily_stats['total_pnl'] > 0])
    negative_days = len(daily_stats[daily_stats['total_pnl'] < 0])

    print(f"\nプラス日: {positive_days}日 ({positive_days/len(daily_stats)*100:.1f}%)")
    print(f"マイナス日: {negative_days}日 ({negative_days/len(daily_stats)*100:.1f}%)")

    # 悪い日の定義：
    # 1. 損失が-50万円以上
    # 2. 勝率が30%以下
    bad_days_loss = daily_stats[daily_stats['total_pnl'] < -500000]
    bad_days_winrate = daily_stats[daily_stats['win_rate'] < 30]
    bad_days_both = daily_stats[(daily_stats['total_pnl'] < -500000) & (daily_stats['win_rate'] < 30)]

    print(f"\n" + "=" * 80)
    print("【悪い日の分類】")
    print("=" * 80)

    print(f"\n■ 大損失日（-50万円以下）: {len(bad_days_loss)}日 ({len(bad_days_loss)/len(daily_stats)*100:.1f}%)")
    if len(bad_days_loss) > 0:
        print("\n最悪の5日:")
        for idx, row in daily_stats_sorted.head(5).iterrows():
            print(f"  {row['date']}: {row['total_pnl']:+10,.0f}円 "
                  f"(勝率 {row['win_rate']:.1f}%, {int(row['wins'])}/{int(row['trade_count'])}勝)")

    print(f"\n■ 低勝率日（勝率30%以下）: {len(bad_days_winrate)}日 ({len(bad_days_winrate)/len(daily_stats)*100:.1f}%)")

    print(f"\n■ 両方該当（大損失 & 低勝率）: {len(bad_days_both)}日 ({len(bad_days_both)/len(daily_stats)*100:.1f}%)")

    # 2025/11/19のような日（ほぼ全銘柄損切り）の頻度
    # 定義: 勝率25%以下かつ損失-100万円以上
    extreme_bad_days = daily_stats[(daily_stats['total_pnl'] < -1000000) & (daily_stats['win_rate'] < 25)]

    print(f"\n" + "=" * 80)
    print("【2025/11/19のような極端に悪い日】")
    print("（定義: 損失-100万円以上 & 勝率25%以下）")
    print("=" * 80)
    print(f"\n発生頻度: {len(extreme_bad_days)}日 / {len(daily_stats)}日 ({len(extreme_bad_days)/len(daily_stats)*100:.1f}%)")

    if len(extreme_bad_days) > 0:
        print("\n該当日:")
        for idx, row in extreme_bad_days.iterrows():
            print(f"  {row['date']}: {row['total_pnl']:+10,.0f}円 "
                  f"(勝率 {row['win_rate']:.1f}%, {int(row['wins'])}/{int(row['trade_count'])}勝)")

    # 良い日の分析（参考）
    good_days = daily_stats[daily_stats['total_pnl'] > 500000]

    print(f"\n" + "=" * 80)
    print("【参考: 良い日（+50万円以上）】")
    print("=" * 80)
    print(f"発生頻度: {len(good_days)}日 / {len(daily_stats)}日 ({len(good_days)/len(daily_stats)*100:.1f}%)")

    if len(good_days) > 0:
        print("\nベスト5日:")
        for idx, row in daily_stats_sorted.tail(5).iloc[::-1].iterrows():
            print(f"  {row['date']}: {row['total_pnl']:+10,.0f}円 "
                  f"(勝率 {row['win_rate']:.1f}%, {int(row['wins'])}/{int(row['trade_count'])}勝)")

    # 分布統計
    print(f"\n" + "=" * 80)
    print("【損益分布】")
    print("=" * 80)

    bins = [
        ("-200万円以下", -2000000, float('-inf')),
        ("-150～-200万円", -1500000, -2000000),
        ("-100～-150万円", -1000000, -1500000),
        ("-50～-100万円", -500000, -1000000),
        ("0～-50万円", 0, -500000),
        ("0～+50万円", 500000, 0),
        ("+50～+100万円", 1000000, 500000),
        ("+100～+150万円", 1500000, 1000000),
        ("+150～+200万円", 2000000, 1500000),
        ("+200万円以上", float('inf'), 2000000)
    ]

    for label, upper, lower in bins:
        count = len(daily_stats[(daily_stats['total_pnl'] > lower) & (daily_stats['total_pnl'] <= upper)])
        if count > 0:
            pct = count / len(daily_stats) * 100
            print(f"{label:20}: {count:3}日 ({pct:5.1f}%)")

    print("\n" + "=" * 80)

    # CSV出力
    output_file = "daily_performance_analysis.csv"
    daily_stats.to_csv(output_file, index=False)
    print(f"\n詳細データを {output_file} に出力しました")
    print("=" * 80)

if __name__ == "__main__":
    analyze_daily_performance()
