#!/usr/bin/env python3
"""
損失日の連続性分析
- 大損失の翌日はどうなる？
- 損失は連続するのか？
"""
import pandas as pd
from pathlib import Path

def analyze_loss_streaks():
    """損失の連続性を分析"""

    output_dir = Path("Output/20251119_221548")

    print("\n" + "=" * 80)
    print("損失日の連続性分析（6ヶ月間）")
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
        'pnl': 'sum'
    }).reset_index()
    daily_stats.columns = ['date', 'pnl']
    daily_stats = daily_stats.sort_values('date')

    # 前日損益を追加
    daily_stats['prev_pnl'] = daily_stats['pnl'].shift(1)
    daily_stats['next_pnl'] = daily_stats['pnl'].shift(-1)

    print(f"\n【基本統計】")
    print(f"取引日数: {len(daily_stats)}日")
    print(f"総損益: {daily_stats['pnl'].sum():+,.0f}円")

    # 大損失日の定義
    big_loss_threshold = -500000  # -50万円
    big_loss_days = daily_stats[daily_stats['pnl'] < big_loss_threshold]

    print(f"\n" + "=" * 80)
    print(f"【大損失日（-50万円以下）の翌日分析】")
    print("=" * 80)
    print(f"\n大損失日: {len(big_loss_days)}日")

    # 翌日のパフォーマンス
    big_loss_with_next = big_loss_days[big_loss_days['next_pnl'].notna()]

    if len(big_loss_with_next) > 0:
        next_day_avg = big_loss_with_next['next_pnl'].mean()
        next_day_median = big_loss_with_next['next_pnl'].median()
        next_day_positive = len(big_loss_with_next[big_loss_with_next['next_pnl'] > 0])
        next_day_negative = len(big_loss_with_next[big_loss_with_next['next_pnl'] < 0])

        print(f"\n翌日のパフォーマンス:")
        print(f"  平均: {next_day_avg:+,.0f}円")
        print(f"  中央値: {next_day_median:+,.0f}円")
        print(f"  プラス: {next_day_positive}日 ({next_day_positive/len(big_loss_with_next)*100:.1f}%)")
        print(f"  マイナス: {next_day_negative}日 ({next_day_negative/len(big_loss_with_next)*100:.1f}%)")

        # 比較: 全体平均
        overall_avg = daily_stats['pnl'].mean()
        print(f"\n比較（全体平均）: {overall_avg:+,.0f}円")

        if next_day_avg > overall_avg:
            print(f"→ 大損失の翌日は平均より{next_day_avg - overall_avg:+,.0f}円良い（反発傾向）")
        else:
            print(f"→ 大損失の翌日は平均より{abs(next_day_avg - overall_avg):,.0f}円悪い（継続傾向）")

    # 連続損失の分析
    print(f"\n" + "=" * 80)
    print("【損失の連続性】")
    print("=" * 80)

    # マイナス日の翌日
    minus_days = daily_stats[daily_stats['pnl'] < 0]
    minus_with_next = minus_days[minus_days['next_pnl'].notna()]

    if len(minus_with_next) > 0:
        consecutive_minus = len(minus_with_next[minus_with_next['next_pnl'] < 0])

        print(f"\nマイナス日（-0円以下）: {len(minus_days)}日")
        print(f"翌日もマイナス: {consecutive_minus}日 ({consecutive_minus/len(minus_with_next)*100:.1f}%)")
        print(f"翌日はプラス: {len(minus_with_next) - consecutive_minus}日 ({(len(minus_with_next) - consecutive_minus)/len(minus_with_next)*100:.1f}%)")

    # 連続日数の計算
    daily_stats['is_minus'] = daily_stats['pnl'] < 0

    streaks = []
    current_streak = 0

    for is_minus in daily_stats['is_minus']:
        if is_minus:
            current_streak += 1
        else:
            if current_streak > 0:
                streaks.append(current_streak)
            current_streak = 0

    if current_streak > 0:
        streaks.append(current_streak)

    if streaks:
        print(f"\n損失連続日数の分布:")
        print(f"  1日: {streaks.count(1)}回")
        print(f"  2日連続: {streaks.count(2)}回")
        print(f"  3日連続: {streaks.count(3)}回")
        print(f"  4日以上連続: {sum(1 for s in streaks if s >= 4)}回")
        print(f"  最大連続: {max(streaks)}日")

    # プラス日の翌日
    print(f"\n" + "=" * 80)
    print("【参考: プラス日の翌日】")
    print("=" * 80)

    plus_days = daily_stats[daily_stats['pnl'] > 0]
    plus_with_next = plus_days[plus_days['next_pnl'].notna()]

    if len(plus_with_next) > 0:
        next_day_avg_plus = plus_with_next['next_pnl'].mean()
        next_day_positive_plus = len(plus_with_next[plus_with_next['next_pnl'] > 0])

        print(f"\nプラス日: {len(plus_days)}日")
        print(f"翌日の平均: {next_day_avg_plus:+,.0f}円")
        print(f"翌日もプラス: {next_day_positive_plus}日 ({next_day_positive_plus/len(plus_with_next)*100:.1f}%)")

    # 最悪の日の詳細
    print(f"\n" + "=" * 80)
    print("【最悪の5日間とその翌日】")
    print("=" * 80)

    worst_days = daily_stats.nsmallest(5, 'pnl')

    for idx, row in worst_days.iterrows():
        next_pnl = row['next_pnl']
        next_str = f"{next_pnl:+,.0f}円" if pd.notna(next_pnl) else "データなし"
        print(f"\n{row['date']}: {row['pnl']:+,.0f}円")
        print(f"  → 翌日: {next_str}")

    print("\n" + "=" * 80)
    print("【結論】")
    print("=" * 80)

    # 結論を導出
    if len(big_loss_with_next) > 0:
        if next_day_avg > 0:
            print("\n✓ 大損失の翌日は平均的にプラス（反発傾向）")
            print("  → 大損失の翌日も通常通りトレード推奨")
        else:
            print("\n✗ 大損失の翌日も平均的にマイナス（継続傾向）")
            print("  → 大損失の翌日は慎重に")

    if len(minus_with_next) > 0:
        consecutive_rate = consecutive_minus / len(minus_with_next)
        if consecutive_rate > 0.55:
            print(f"\n✗ マイナス日の翌日もマイナスになる確率が高い（{consecutive_rate*100:.1f}%）")
            print("  → 損失日の翌日は警戒が必要")
        else:
            print(f"\n✓ マイナス日の翌日は約半々（マイナス継続率{consecutive_rate*100:.1f}%）")
            print("  → 損失日の翌日も通常通りトレード可能")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    analyze_loss_streaks()
