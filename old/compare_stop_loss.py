#!/usr/bin/env python3
"""
損切り変更による損益比較
0.5% vs 1.0% の損切りでP&Lがどう変わるかを分析
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("損切り変更による損益比較分析")
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

# 現在の結果（0.5%損切り）
current_total_return = trades_df['return'].sum()
current_total_pnl = trades_df['pnl'].sum()
current_stop_loss_count = len(trades_df[trades_df['reason'] == 'loss'])

print("=" * 80)
print("【現状】損切り = -0.5%")
print("=" * 80)
print(f"総リターン       : {current_total_return*100:+.2f}%")
print(f"総損益           : {current_total_pnl:+,.0f}円")
print(f"損切り執行       : {current_stop_loss_count}トレード ({current_stop_loss_count/len(trades_df)*100:.1f}%)")
print()

# 1%の損切りでシミュレーション
NEW_STOP_LOSS = 0.01

# 各トレードについて再計算
adjusted_trades = []

for idx, trade in trades_df.iterrows():
    adjusted_trade = trade.copy()

    # 利益目標で終わったトレードはそのまま
    if trade['reason'] == 'target':
        adjusted_trades.append(adjusted_trade)
        continue

    # 損切り or 引け決済の場合
    # 実際のリターンが-1%より大きい（損失が小さい）場合、損切りにかからない
    if trade['return'] <= -NEW_STOP_LOSS:
        # -1%で損切りされるはず
        adjusted_trade['return'] = -NEW_STOP_LOSS
        adjusted_trade['pnl'] = -trade['entry_price'] * NEW_STOP_LOSS
        adjusted_trade['reason'] = 'loss'
        adjusted_trade['exit_price'] = trade['entry_price'] * (1 - NEW_STOP_LOSS if trade['side'] == 'long' else 1 + NEW_STOP_LOSS)
    elif trade['reason'] == 'loss':
        # 現在は0.5%で損切りされたが、1%なら損切りにかからず引け決済になる
        adjusted_trade['reason'] = 'day_end'
        # リターンはそのまま（実際のリターンが-0.5%～-1%の間なので）

    adjusted_trades.append(adjusted_trade)

adjusted_df = pd.DataFrame(adjusted_trades)

# 新しい結果
new_total_return = adjusted_df['return'].sum()
new_total_pnl = adjusted_df['pnl'].sum()
new_stop_loss_count = len(adjusted_df[adjusted_df['reason'] == 'loss'])
new_profit_target_count = len(adjusted_df[adjusted_df['reason'] == 'target'])
new_day_end_count = len(adjusted_df[adjusted_df['reason'] == 'day_end'])

print("=" * 80)
print("【変更後】損切り = -1.0%")
print("=" * 80)
print(f"総リターン       : {new_total_return*100:+.2f}%")
print(f"総損益           : {new_total_pnl:+,.0f}円")
print(f"損切り執行       : {new_stop_loss_count}トレード ({new_stop_loss_count/len(adjusted_df)*100:.1f}%)")
print(f"利益目標到達     : {new_profit_target_count}トレード ({new_profit_target_count/len(adjusted_df)*100:.1f}%)")
print(f"引け決済         : {new_day_end_count}トレード ({new_day_end_count/len(adjusted_df)*100:.1f}%)")
print()

# 差分
diff_return = new_total_return - current_total_return
diff_pnl = new_total_pnl - current_total_pnl
diff_stop_loss = new_stop_loss_count - current_stop_loss_count

print("=" * 80)
print("【差分】-1.0% - (-0.5%)")
print("=" * 80)
print(f"リターン差       : {diff_return*100:+.2f}% ポイント")
print(f"損益差           : {diff_pnl:+,.0f}円")
print(f"損切り執行変化   : {diff_stop_loss:+}トレード")
print()

if diff_pnl > 0:
    print(f"✅ 損切りを-1%に緩和すると {diff_pnl:,.0f}円 改善")
    improvement_pct = (diff_pnl / abs(current_total_pnl)) * 100 if current_total_pnl != 0 else 0
    print(f"   改善率: {improvement_pct:+.1f}%")
elif diff_pnl < 0:
    print(f"❌ 損切りを-1%に緩和すると {abs(diff_pnl):,.0f}円 悪化")
    deterioration_pct = (abs(diff_pnl) / abs(current_total_pnl)) * 100 if current_total_pnl != 0 else 0
    print(f"   悪化率: -{deterioration_pct:.1f}%")
else:
    print("⚠️ 変化なし")

print()

# 銘柄別の変化
print("=" * 80)
print("【銘柄別】損切り変更の影響")
print("=" * 80)
print()

stock_comparison = []
for stock in trades_df['stock_name'].unique():
    current_stock = trades_df[trades_df['stock_name'] == stock]
    adjusted_stock = adjusted_df[adjusted_df['stock_name'] == stock]

    current_pnl = current_stock['pnl'].sum()
    adjusted_pnl = adjusted_stock['pnl'].sum()
    diff = adjusted_pnl - current_pnl

    current_losses = len(current_stock[current_stock['reason'] == 'loss'])
    adjusted_losses = len(adjusted_stock[adjusted_stock['reason'] == 'loss'])

    stock_comparison.append({
        'stock_name': stock,
        'current_pnl': current_pnl,
        'adjusted_pnl': adjusted_pnl,
        'diff': diff,
        'current_losses': current_losses,
        'adjusted_losses': adjusted_losses,
        'loss_decrease': current_losses - adjusted_losses
    })

stock_comp_df = pd.DataFrame(stock_comparison).sort_values('diff', ascending=False)

print(f"{'銘柄':<20} {'現状P&L':>12} {'1%時P&L':>12} {'差分':>12} {'損切減少':>10}")
print("-" * 80)
for _, row in stock_comp_df.iterrows():
    sign = "✅" if row['diff'] > 0 else ("❌" if row['diff'] < 0 else "➖")
    print(f"{row['stock_name']:<20} {row['current_pnl']:>11,.0f}円 {row['adjusted_pnl']:>11,.0f}円 "
          f"{row['diff']:>11,.0f}円 {sign}  {row['loss_decrease']:>+4}件")

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

# 最大損失の変化
current_max_loss = trades_df['pnl'].min()
adjusted_max_loss = adjusted_df['pnl'].min()

print(f"最大損失: {current_max_loss:,.0f}円 → {adjusted_max_loss:,.0f}円 ({adjusted_max_loss - current_max_loss:+,.0f}円)")

# 平均損失の変化
current_avg_loss = current_losers['pnl'].mean()
adjusted_avg_loss = adjusted_losers['pnl'].mean()

print(f"平均損失: {current_avg_loss:,.0f}円 → {adjusted_avg_loss:,.0f}円 ({adjusted_avg_loss - current_avg_loss:+,.0f}円)")

print()

# 損切り回避されたトレードの詳細
print("=" * 80)
print("【損切り回避トレードの分析】")
print("=" * 80)
print()

avoided_stop_loss = []
for idx, (current_trade, adjusted_trade) in enumerate(zip(trades_df.itertuples(), adjusted_df.itertuples())):
    if current_trade.reason == 'loss' and adjusted_trade.reason == 'day_end':
        avoided_stop_loss.append({
            'date': current_trade.date,
            'stock_name': current_trade.stock_name,
            'side': current_trade.side,
            'return': current_trade._4,  # return列
            'pnl': current_trade.pnl
        })

if avoided_stop_loss:
    avoided_df = pd.DataFrame(avoided_stop_loss)
    print(f"損切り回避トレード数: {len(avoided_df)}件")
    print(f"回避トレードの平均リターン: {avoided_df['return'].mean()*100:.2f}%")
    print(f"回避トレードの平均P&L: {avoided_df['pnl'].mean():,.0f}円")
    print(f"回避トレードの総P&L: {avoided_df['pnl'].sum():,.0f}円")
    print()

    print("【回避トレードの内訳（上位10件）】")
    print(f"{'日付':<12} {'銘柄':<20} {'売買':>6} {'リターン':>10} {'P&L':>12}")
    print("-" * 80)
    for _, row in avoided_df.sort_values('pnl', ascending=False).head(10).iterrows():
        side_ja = "ロング" if row['side'] == 'long' else "ショート"
        print(f"{row['date']!s:<12} {row['stock_name']:<20} {side_ja:>6} {row['return']*100:>9.2f}% {row['pnl']:>11,.0f}円")
else:
    print("損切り回避トレードなし（全ての損切りが-1%以下）")

print()
print("=" * 80)
print("分析完了")
print("=" * 80)
