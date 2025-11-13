#!/usr/bin/env python3
"""
30日間バックテスト結果の詳細分析
銘柄別・日別の統計とインサイト
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("30日間バックテスト詳細分析レポート")
print("=" * 80)
print()

# データ読み込み
trades_df = pd.read_csv('results/optimization/recent_30days_trades.csv')
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
trades_df['date'] = trades_df['entry_time'].dt.date
trades_df['hold_minutes'] = (trades_df['exit_time'] - trades_df['entry_time']).dt.total_seconds() / 60

print(f"期間: {trades_df['date'].min()} ～ {trades_df['date'].max()}")
print(f"総トレード数: {len(trades_df)}")
print(f"営業日数: {trades_df['date'].nunique()}")
print(f"銘柄数: {trades_df['stock_name'].nunique()}")
print()

# ================================================================================
# 1. 銘柄別パフォーマンス分析
# ================================================================================
print("=" * 80)
print("1. 銘柄別パフォーマンス分析")
print("=" * 80)
print()

stock_stats = trades_df.groupby('stock_name').agg({
    'return': ['sum', 'mean', 'std', 'min', 'max'],
    'pnl': ['sum', 'mean'],
    'side': 'count',
    'hold_minutes': 'mean'
}).round(4)

stock_stats.columns = ['総リターン', '平均リターン', 'リターンStd', '最小リターン', '最大リターン',
                       '総損益', '平均損益', 'トレード数', '平均保有時間(分)']

# 勝率計算
win_rates = trades_df.groupby('stock_name').apply(
    lambda x: (x['pnl'] > 0).sum() / len(x) * 100
).round(1)
stock_stats['勝率(%)'] = win_rates

# ソート
stock_stats = stock_stats.sort_values('総リターン', ascending=False)

print(f"{'銘柄名':<20} {'総リターン':>10} {'平均リターン':>12} {'勝率':>8} {'トレード数':>10} {'平均保有時間':>12}")
print("-" * 80)
for stock, row in stock_stats.iterrows():
    print(f"{stock:<20} {row['総リターン']*100:>9.2f}% {row['平均リターン']*100:>11.2f}% "
          f"{row['勝率(%)']:>7.1f}% {int(row['トレード数']):>10} {row['平均保有時間(分)']:>11.1f}分")

print()

# ================================================================================
# 2. ロング vs ショート分析
# ================================================================================
print("=" * 80)
print("2. ロング vs ショート分析")
print("=" * 80)
print()

for stock in stock_stats.index:
    stock_trades = trades_df[trades_df['stock_name'] == stock]
    long_trades = stock_trades[stock_trades['side'] == 'long']
    short_trades = stock_trades[stock_trades['side'] == 'short']

    if len(long_trades) > 0 and len(short_trades) > 0:
        long_return = long_trades['return'].sum() * 100
        short_return = short_trades['return'].sum() * 100
        long_win_rate = (long_trades['pnl'] > 0).sum() / len(long_trades) * 100
        short_win_rate = (short_trades['pnl'] > 0).sum() / len(short_trades) * 100

        print(f"{stock:<20}")
        print(f"  ロング : {long_return:>7.2f}% (勝率 {long_win_rate:.1f}%, {len(long_trades)}トレード)")
        print(f"  ショート: {short_return:>7.2f}% (勝率 {short_win_rate:.1f}%, {len(short_trades)}トレード)")
        print()

# ================================================================================
# 3. 日別パフォーマンス分析
# ================================================================================
print("=" * 80)
print("3. 日別パフォーマンス分析")
print("=" * 80)
print()

daily_stats = trades_df.groupby('date').agg({
    'return': 'sum',
    'pnl': 'sum',
    'side': 'count'
}).round(4)
daily_stats.columns = ['総リターン', '総損益', 'トレード数']
daily_stats = daily_stats.sort_values('総リターン', ascending=False)

print("【トップ5最良日】")
for date, row in daily_stats.head(5).iterrows():
    print(f"{date}: {row['総リターン']*100:+7.2f}% ({row['総損益']:+,.0f}円, {int(row['トレード数'])}トレード)")

print()
print("【ワースト5最悪日】")
for date, row in daily_stats.tail(5).iterrows():
    print(f"{date}: {row['総リターン']*100:+7.2f}% ({row['総損益']:+,.0f}円, {int(row['トレード数'])}トレード)")

print()

# ================================================================================
# 4. 利益目標 vs 損切り達成率
# ================================================================================
print("=" * 80)
print("4. 利益目標 vs 損切り達成率")
print("=" * 80)
print()

profit_target = trades_df[trades_df['reason'] == 'target']
stop_loss = trades_df[trades_df['reason'] == 'loss']
day_end = trades_df[trades_df['reason'] == 'day_end']

total_trades = len(trades_df)
print(f"利益目標到達  : {len(profit_target):>4}トレード ({len(profit_target)/total_trades*100:>5.1f}%)")
print(f"損切り執行    : {len(stop_loss):>4}トレード ({len(stop_loss)/total_trades*100:>5.1f}%)")
print(f"引け強制決済  : {len(day_end):>4}トレード ({len(day_end)/total_trades*100:>5.1f}%)")
print()

# 銘柄別の理由分布
print("【銘柄別決済理由】")
print(f"{'銘柄名':<20} {'利益目標':>10} {'損切り':>10} {'引け決済':>10}")
print("-" * 80)
for stock in stock_stats.index:
    stock_trades = trades_df[trades_df['stock_name'] == stock]
    target_count = len(stock_trades[stock_trades['reason'] == 'target'])
    loss_count = len(stock_trades[stock_trades['reason'] == 'loss'])
    day_count = len(stock_trades[stock_trades['reason'] == 'day_end'])
    print(f"{stock:<20} {target_count:>10} {loss_count:>10} {day_count:>10}")

print()

# ================================================================================
# 5. 保有時間分析
# ================================================================================
print("=" * 80)
print("5. 保有時間分析")
print("=" * 80)
print()

print(f"平均保有時間: {trades_df['hold_minutes'].mean():.1f}分")
print(f"中央値      : {trades_df['hold_minutes'].median():.1f}分")
print(f"最短        : {trades_df['hold_minutes'].min():.1f}分")
print(f"最長        : {trades_df['hold_minutes'].max():.1f}分")
print()

# 利益vs損失の保有時間比較
profit_trades = trades_df[trades_df['pnl'] > 0]
loss_trades = trades_df[trades_df['pnl'] < 0]

print(f"利益トレードの平均保有時間: {profit_trades['hold_minutes'].mean():.1f}分")
print(f"損失トレードの平均保有時間: {loss_trades['hold_minutes'].mean():.1f}分")
print()

# ================================================================================
# 6. リスク・リターン指標
# ================================================================================
print("=" * 80)
print("6. リスク・リターン指標")
print("=" * 80)
print()

# ポートフォリオ全体
total_return = trades_df['return'].sum()
sharpe_numerator = trades_df.groupby('date')['return'].sum().mean()
sharpe_denominator = trades_df.groupby('date')['return'].sum().std()
sharpe_ratio = (sharpe_numerator / sharpe_denominator) * np.sqrt(252) if sharpe_denominator > 0 else 0

max_drawdown = 0
cumulative_returns = trades_df.groupby('date')['return'].sum().cumsum()
running_max = cumulative_returns.expanding().max()
drawdowns = (cumulative_returns - running_max)
max_drawdown = drawdowns.min()

print(f"ポートフォリオ総リターン: {total_return*100:+.2f}%")
print(f"シャープレシオ (年率)  : {sharpe_ratio:.2f}")
print(f"最大ドローダウン        : {max_drawdown*100:.2f}%")
print(f"勝率                    : {len(profit_trades)/total_trades*100:.1f}%")
print(f"損益レシオ              : {abs(profit_trades['pnl'].mean() / loss_trades['pnl'].mean()):.2f}")
print()

# ================================================================================
# 7. 銘柄相関分析
# ================================================================================
print("=" * 80)
print("7. 銘柄間相関分析（日次リターン）")
print("=" * 80)
print()

# 日次リターンピボット
daily_returns_pivot = trades_df.groupby(['date', 'stock_name'])['return'].sum().unstack(fill_value=0)
correlation_matrix = daily_returns_pivot.corr()

# 高相関ペアを抽出
high_corr_pairs = []
for i in range(len(correlation_matrix.columns)):
    for j in range(i+1, len(correlation_matrix.columns)):
        corr_value = correlation_matrix.iloc[i, j]
        if abs(corr_value) > 0.5:
            high_corr_pairs.append({
                'stock1': correlation_matrix.columns[i],
                'stock2': correlation_matrix.columns[j],
                'correlation': corr_value
            })

if high_corr_pairs:
    high_corr_df = pd.DataFrame(high_corr_pairs).sort_values('correlation', key=abs, ascending=False)
    print("【高相関銘柄ペア (|相関| > 0.5)】")
    for _, row in high_corr_df.head(10).iterrows():
        print(f"{row['stock1']:<20} ⇔ {row['stock2']:<20}: {row['correlation']:+.3f}")
else:
    print("高相関ペアなし（全ペアの相関係数 < 0.5）")

print()

# ================================================================================
# 8. サマリーと推奨事項
# ================================================================================
print("=" * 80)
print("8. サマリーと推奨事項")
print("=" * 80)
print()

# トップ3銘柄
top3_stocks = stock_stats.head(3).index.tolist()
print("【推奨銘柄 トップ3】")
for i, stock in enumerate(top3_stocks, 1):
    stats = stock_stats.loc[stock]
    print(f"{i}. {stock}")
    print(f"   総リターン: {stats['総リターン']*100:+.2f}%")
    print(f"   勝率: {stats['勝率(%)']:.1f}%")
    print(f"   平均リターン: {stats['平均リターン']*100:+.2f}%")
    print()

# ワースト2銘柄
worst2_stocks = stock_stats.tail(2).index.tolist()
print("【要注意銘柄 ワースト2】")
for i, stock in enumerate(worst2_stocks, 1):
    stats = stock_stats.loc[stock]
    print(f"{i}. {stock}")
    print(f"   総リターン: {stats['総リターン']*100:+.2f}%")
    print(f"   勝率: {stats['勝率(%)']:.1f}%")
    print()

print("=" * 80)
print("分析完了")
print("=" * 80)
