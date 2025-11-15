#!/usr/bin/env python3
"""
トップ10銘柄のトレードサマリー可視化
エントリー・イグジットタイミングと損益を視覚的に表示
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

def main():
    print("=" * 80)
    print("トップ10銘柄 トレードサマリー可視化")
    print("=" * 80)

    # トレードデータを読み込み
    trades_df = pd.read_csv('results/optimization/top10_trades_20251113.csv')

    # 時刻をdatetimeに変換
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])

    # 時刻を時:分表示に変換（JST）
    # tz-naiveなのでまずUTCとしてlocalize、その後JSTに変換
    trades_df['entry_jst'] = trades_df['entry_time'].dt.tz_localize('UTC').dt.tz_convert('Asia/Tokyo')
    trades_df['exit_jst'] = trades_df['exit_time'].dt.tz_localize('UTC').dt.tz_convert('Asia/Tokyo')

    # ポジション保有時間（分）
    trades_df['duration_min'] = (trades_df['exit_time'] - trades_df['entry_time']).dt.total_seconds() / 60

    print(f"\n総トレード数: {len(trades_df)}")

    # 図を作成（2つのサブプロット）
    fig = plt.figure(figsize=(20, 12))

    # ========== 1. トレードタイムライン ==========
    ax1 = plt.subplot(2, 1, 1)

    # Y軸を銘柄名に
    stock_names = trades_df['stock_name'].values
    y_positions = range(len(stock_names))

    for idx, row in trades_df.iterrows():
        # エントリー時刻（09:00からの経過分）
        entry_minutes = row['entry_jst'].hour * 60 + row['entry_jst'].minute - 9*60
        exit_minutes = row['exit_jst'].hour * 60 + row['exit_jst'].minute - 9*60

        # トレード期間を横棒で表示
        color = 'green' if row['pnl'] > 0 else 'red'
        alpha = 0.6

        ax1.barh(idx, exit_minutes - entry_minutes, left=entry_minutes,
                 height=0.8, color=color, alpha=alpha, edgecolor='black', linewidth=1.5)

        # エントリーマーカー
        ax1.plot(entry_minutes, idx, marker='^', color='blue', markersize=12, zorder=10)

        # イグジットマーカー
        exit_marker = 'v' if row['pnl'] < 0 else 'o'
        ax1.plot(exit_minutes, idx, marker=exit_marker, color='darkred' if row['pnl'] < 0 else 'darkgreen',
                 markersize=12, zorder=10)

        # 損益を表示
        pnl_text = f"{row['pnl']:+,.0f}円\n({row['return']*100:+.2f}%)"
        ax1.text(exit_minutes + 5, idx, pnl_text, va='center', fontsize=9,
                 color='darkgreen' if row['pnl'] > 0 else 'darkred', fontweight='bold')

    # Y軸設定
    ax1.set_yticks(y_positions)
    ax1.set_yticklabels(stock_names, fontsize=11)
    ax1.set_ylim(-0.5, len(stock_names) - 0.5)
    ax1.invert_yaxis()

    # X軸設定（09:00-15:00）
    ax1.set_xlim(0, 360)  # 09:00-15:00は360分
    ax1.set_xticks([0, 60, 120, 180, 240, 300, 360])
    ax1.set_xticklabels(['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'], fontsize=11)

    ax1.set_xlabel('時刻 (JST)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('銘柄', fontsize=13, fontweight='bold')
    ax1.set_title('トップ10銘柄 トレードタイムライン（2025/11/13）\n'
                  '緑=利益、赤=損失 | △=エントリー、▼=損切り、○=利益確定/日中終了',
                  fontsize=14, fontweight='bold', pad=15)

    ax1.grid(True, axis='x', alpha=0.3, linestyle='--')
    ax1.axvline(x=10, color='gray', linestyle='--', alpha=0.5, linewidth=2, label='09:10 (レンジ中間)')
    ax1.axvline(x=15, color='blue', linestyle='--', alpha=0.5, linewidth=2, label='09:15 (エントリー開始)')
    ax1.legend(loc='upper right', fontsize=10)

    # ========== 2. 損益バーチャート ==========
    ax2 = plt.subplot(2, 1, 2)

    colors = ['green' if pnl > 0 else 'red' for pnl in trades_df['pnl']]
    bars = ax2.barh(y_positions, trades_df['pnl'], color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

    # Y軸設定
    ax2.set_yticks(y_positions)
    ax2.set_yticklabels(stock_names, fontsize=11)
    ax2.set_ylim(-0.5, len(stock_names) - 0.5)
    ax2.invert_yaxis()

    # X軸設定
    ax2.set_xlabel('損益（円）', fontsize=13, fontweight='bold')
    ax2.set_ylabel('銘柄', fontsize=13, fontweight='bold')
    ax2.set_title('トップ10銘柄 本日の損益', fontsize=14, fontweight='bold', pad=15)

    # ゼロラインを強調
    ax2.axvline(x=0, color='black', linewidth=2)

    # グリッド
    ax2.grid(True, axis='x', alpha=0.3, linestyle='--')

    # 各バーに数値ラベル
    for idx, (pnl, ret, side) in enumerate(zip(trades_df['pnl'], trades_df['return'], trades_df['side'])):
        label = f"{pnl:+,.0f}円 ({ret*100:+.2f}%)\n{side.upper()}"
        x_pos = pnl + (5000 if pnl > 0 else -5000)
        ha = 'left' if pnl > 0 else 'right'
        ax2.text(x_pos, idx, label, va='center', ha=ha, fontsize=9, fontweight='bold',
                 color='darkgreen' if pnl > 0 else 'darkred')

    plt.tight_layout()

    # 保存
    output_path = 'results/optimization/top10_summary_chart_20251113.png'
    plt.savefig(output_path, dpi=200, bbox_inches='tight')

    print(f"\n可視化を {output_path} に保存しました")

    # 統計サマリー
    print(f"\n{'='*80}")
    print("本日のトレードサマリー")
    print(f"{'='*80}\n")

    total_pnl = trades_df['pnl'].sum()
    avg_pnl = trades_df['pnl'].mean()
    win_trades = (trades_df['pnl'] > 0).sum()
    loss_trades = (trades_df['pnl'] < 0).sum()
    win_rate = win_trades / len(trades_df) * 100

    avg_duration = trades_df['duration_min'].mean()
    max_duration = trades_df['duration_min'].max()
    min_duration = trades_df['duration_min'].min()

    print(f"総損益: {total_pnl:+,.0f}円 ({total_pnl/10000000*100:+.2f}%)")
    print(f"平均損益: {avg_pnl:+,.0f}円")
    print(f"勝ちトレード: {win_trades}回")
    print(f"負けトレード: {loss_trades}回")
    print(f"勝率: {win_rate:.1f}%")
    print(f"\n平均保有時間: {avg_duration:.1f}分")
    print(f"最長保有時間: {max_duration:.1f}分 ({trades_df.loc[trades_df['duration_min'].idxmax(), 'stock_name']})")
    print(f"最短保有時間: {min_duration:.1f}分 ({trades_df.loc[trades_df['duration_min'].idxmin(), 'stock_name']})")

    # 決済理由の内訳
    print(f"\n決済理由:")
    for reason, count in trades_df['reason'].value_counts().items():
        print(f"  {reason}: {count}回")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
