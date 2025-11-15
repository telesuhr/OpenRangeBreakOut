#!/usr/bin/env python3
"""
利益目標の変更による損益比較
4% vs 3% の利益目標でP&Lがどう変わるかを分析
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("利益目標変更による損益比較分析")
print("=" * 80)
print()

# トレードデータ読み込み
trades_df = pd.read_csv('results/optimization/recent_30days_trades.csv')
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
trades_df['date'] = trades_df['entry_time'].dt.date

print(f"総トレード数: {len(trades_df)}")
print(f"分析期間: {trades_df['date'].min()} ～ {trades_df['date'].max()}")
print()

# 現在の結果（4%利益目標）
current_total_return = trades_df['return'].sum()
current_total_pnl = trades_df['pnl'].sum()
current_profit_target_count = len(trades_df[trades_df['reason'] == 'target'])

print("=" * 80)
print("【現状】利益目標 = 4.0%")
print("=" * 80)
print(f"総リターン       : {current_total_return*100:+.2f}%")
print(f"総損益           : {current_total_pnl:+,.0f}円")
print(f"利益目標到達     : {current_profit_target_count}トレード ({current_profit_target_count/len(trades_df)*100:.1f}%)")
print()

# 3%の利益目標でシミュレーション
NEW_PROFIT_TARGET = 0.03

# 各トレードについて再計算
adjusted_trades = []

for idx, trade in trades_df.iterrows():
    adjusted_trade = trade.copy()

    # 損切りで終わったトレードはそのまま
    if trade['reason'] == 'loss':
        adjusted_trades.append(adjusted_trade)
        continue

    # 引け決済 or 既存の利益目標達成の場合
    # 実際のリターンが3%を超えているかチェック
    if trade['return'] >= NEW_PROFIT_TARGET:
        # 3%で利益確定できたはず
        adjusted_trade['return'] = NEW_PROFIT_TARGET
        adjusted_trade['pnl'] = trade['entry_price'] * NEW_PROFIT_TARGET
        adjusted_trade['reason'] = 'target'
        adjusted_trade['exit_price'] = trade['entry_price'] * (1 + NEW_PROFIT_TARGET if trade['side'] == 'long' else 1 - NEW_PROFIT_TARGET)

    adjusted_trades.append(adjusted_trade)

adjusted_df = pd.DataFrame(adjusted_trades)

# 新しい結果
new_total_return = adjusted_df['return'].sum()
new_total_pnl = adjusted_df['pnl'].sum()
new_profit_target_count = len(adjusted_df[adjusted_df['reason'] == 'target'])
new_stop_loss_count = len(adjusted_df[adjusted_df['reason'] == 'loss'])
new_day_end_count = len(adjusted_df[adjusted_df['reason'] == 'day_end'])

print("=" * 80)
print("【変更後】利益目標 = 3.0%")
print("=" * 80)
print(f"総リターン       : {new_total_return*100:+.2f}%")
print(f"総損益           : {new_total_pnl:+,.0f}円")
print(f"利益目標到達     : {new_profit_target_count}トレード ({new_profit_target_count/len(adjusted_df)*100:.1f}%)")
print(f"損切り執行       : {new_stop_loss_count}トレード ({new_stop_loss_count/len(adjusted_df)*100:.1f}%)")
print(f"引け決済         : {new_day_end_count}トレード ({new_day_end_count/len(adjusted_df)*100:.1f}%)")
print()

# 差分
diff_return = new_total_return - current_total_return
diff_pnl = new_total_pnl - current_total_pnl
diff_profit_target = new_profit_target_count - current_profit_target_count

print("=" * 80)
print("【差分】3.0% - 4.0%")
print("=" * 80)
print(f"リターン差       : {diff_return*100:+.2f}% ポイント")
print(f"損益差           : {diff_pnl:+,.0f}円")
print(f"利益目標達成増加 : {diff_profit_target:+}トレード")
print()

if diff_pnl > 0:
    print(f"✅ 利益目標を3%に下げると {diff_pnl:,.0f}円 改善")
    improvement_pct = (diff_pnl / abs(current_total_pnl)) * 100 if current_total_pnl != 0 else 0
    print(f"   改善率: {improvement_pct:+.1f}%")
elif diff_pnl < 0:
    print(f"❌ 利益目標を3%に下げると {abs(diff_pnl):,.0f}円 悪化")
    deterioration_pct = (abs(diff_pnl) / abs(current_total_pnl)) * 100 if current_total_pnl != 0 else 0
    print(f"   悪化率: -{deterioration_pct:.1f}%")
else:
    print("⚠️ 変化なし")

print()

# 銘柄別の変化
print("=" * 80)
print("【銘柄別】利益目標変更の影響")
print("=" * 80)
print()

stock_comparison = []
for stock in trades_df['stock_name'].unique():
    current_stock = trades_df[trades_df['stock_name'] == stock]
    adjusted_stock = adjusted_df[adjusted_df['stock_name'] == stock]

    current_pnl = current_stock['pnl'].sum()
    adjusted_pnl = adjusted_stock['pnl'].sum()
    diff = adjusted_pnl - current_pnl

    current_targets = len(current_stock[current_stock['reason'] == 'target'])
    adjusted_targets = len(adjusted_stock[adjusted_stock['reason'] == 'target'])

    stock_comparison.append({
        'stock_name': stock,
        'current_pnl': current_pnl,
        'adjusted_pnl': adjusted_pnl,
        'diff': diff,
        'current_targets': current_targets,
        'adjusted_targets': adjusted_targets,
        'target_increase': adjusted_targets - current_targets
    })

stock_comp_df = pd.DataFrame(stock_comparison).sort_values('diff', ascending=False)

print(f"{'銘柄':<20} {'現状P&L':>12} {'3%時P&L':>12} {'差分':>12} {'目標達成増':>10}")
print("-" * 80)
for _, row in stock_comp_df.iterrows():
    sign = "✅" if row['diff'] > 0 else ("❌" if row['diff'] < 0 else "➖")
    print(f"{row['stock_name']:<20} {row['current_pnl']:>11,.0f}円 {row['adjusted_pnl']:>11,.0f}円 "
          f"{row['diff']:>11,.0f}円 {sign}  {row['target_increase']:>+4}件")

print()

# 統計サマリー
print("=" * 80)
print("【統計サマリー】")
print("=" * 80)
print()

# 勝率の変化
current_win_rate = (trades_df['pnl'] > 0).sum() / len(trades_df) * 100
adjusted_win_rate = (adjusted_df['pnl'] > 0).sum() / len(adjusted_df) * 100

print(f"勝率: {current_win_rate:.1f}% → {adjusted_win_rate:.1f}% ({adjusted_win_rate - current_win_rate:+.1f}%pt)")

# 平均損益の変化
current_avg_pnl = trades_df['pnl'].mean()
adjusted_avg_pnl = adjusted_df['pnl'].mean()

print(f"平均損益: {current_avg_pnl:,.0f}円 → {adjusted_avg_pnl:,.0f}円 ({adjusted_avg_pnl - current_avg_pnl:+,.0f}円)")

# 損益レシオ
current_winners = trades_df[trades_df['pnl'] > 0]
current_losers = trades_df[trades_df['pnl'] < 0]
current_profit_loss_ratio = abs(current_winners['pnl'].mean() / current_losers['pnl'].mean()) if len(current_losers) > 0 else 0

adjusted_winners = adjusted_df[adjusted_df['pnl'] > 0]
adjusted_losers = adjusted_df[adjusted_df['pnl'] < 0]
adjusted_profit_loss_ratio = abs(adjusted_winners['pnl'].mean() / adjusted_losers['pnl'].mean()) if len(adjusted_losers) > 0 else 0

print(f"損益レシオ: {current_profit_loss_ratio:.2f} → {adjusted_profit_loss_ratio:.2f} ({adjusted_profit_loss_ratio - current_profit_loss_ratio:+.2f})")

print()
print("=" * 80)
print("分析完了")
print("=" * 80)
