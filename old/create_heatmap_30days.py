#!/usr/bin/env python3
"""
30日間バックテスト結果のヒートマップ作成
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

print("30日間バックテスト結果のヒートマップ作成")
print("=" * 80)

# データ読み込み
trades_df = pd.read_csv('results/optimization/recent_30days_trades.csv')
print(f"トレード数: {len(trades_df)}")

# entry_timeをdatetimeに変換
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
trades_df['date'] = trades_df['entry_time'].dt.date

# 日付×銘柄でグループ化してリターンを集計
daily_returns = trades_df.groupby(['date', 'stock_name'])['return'].sum().reset_index()

print(f"営業日数: {daily_returns['date'].nunique()}")
print(f"銘柄数: {daily_returns['stock_name'].nunique()}")

# ピボットテーブル作成
heatmap_data = daily_returns.pivot(index='stock_name', columns='date', values='return')
heatmap_data = heatmap_data * 100  # パーセント表示

# 銘柄を総リターンでソート（降順）
stock_totals = heatmap_data.sum(axis=1).sort_values(ascending=False)
heatmap_data = heatmap_data.loc[stock_totals.index]

print("\n銘柄別総リターン:")
for stock, total in stock_totals.items():
    print(f"  {stock:20s}: {total:+6.2f}%")

# ヒートマップ描画
fig, ax = plt.subplots(figsize=(24, 10))
sns.heatmap(heatmap_data,
           cmap='RdYlGn',
           center=0,
           cbar_kws={'label': 'リターン (%)'},
           linewidths=0.3,
           linecolor='lightgray',
           vmin=-5,
           vmax=5,
           ax=ax,
           fmt='.1f')

plt.title('銘柄×日付 リターンヒートマップ（2025年10月1日〜11月12日）',
         fontsize=18, fontweight='bold', pad=20)
plt.xlabel('日付', fontsize=14, fontweight='bold')
plt.ylabel('銘柄', fontsize=14, fontweight='bold')
plt.xticks(rotation=45, ha='right', fontsize=9)
plt.yticks(rotation=0, fontsize=12)
plt.tight_layout()

# 保存
output_file = 'results/optimization/heatmap_30days.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\nヒートマップを {output_file} に保存しました")

plt.close()
print("\n完了！")
