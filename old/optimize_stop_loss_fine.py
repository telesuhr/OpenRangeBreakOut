#!/usr/bin/env python3
"""
損切りライン最適化（細かい刻み）
0.5%, 0.6%, 0.7%, 0.75%, 0.8%, 0.9%, 1.0% を比較
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)

# トップ10銘柄（推奨銘柄）
TOP_10_STOCKS = [
    ('6762.T', 'TDK'),
    ('6594.T', '日本電産'),
    ('6857.T', 'アドバンテスト'),
    ('4188.T', '三菱ケミカルG'),
    ('5802.T', '住友電気工業'),
    ('9984.T', 'ソフトバンクG'),
    ('9501.T', '東京電力HD'),
    ('5706.T', '三井金属鉱業'),
    ('6752.T', 'パナソニック'),
    ('5711.T', '三菱マテリアル'),
]

# バックテスト期間（6ヶ月）
END_DATE = datetime(2025, 11, 12)
START_DATE = datetime(2025, 5, 12)

# 基本パラメータ
BASE_PARAMS = {
    'initial_capital': 10000000,
    'commission_rate': 0.001,
    'range_start': jst_to_utc_time('09:05'),
    'range_end': jst_to_utc_time('09:15'),
    'entry_start': jst_to_utc_time('09:15'),
    'entry_end': jst_to_utc_time('10:00'),
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,  # 4.0%固定
}

# テストする損切りライン
STOP_LOSS_VALUES = [0.005, 0.006, 0.007, 0.0075, 0.008, 0.009, 0.01]
STOP_LOSS_LABELS = ['0.5%', '0.6%', '0.7%', '0.75%', '0.8%', '0.9%', '1.0%']

def run_backtest_with_stop_loss(client, stop_loss_value, label):
    """指定された損切り値でバックテストを実行"""
    print(f"\n{'='*80}")
    print(f"損切りライン: {label} ({stop_loss_value*100:.2f}%)")
    print(f"{'='*80}")

    params = BASE_PARAMS.copy()
    params['stop_loss'] = stop_loss_value

    all_trades = []

    for idx, (symbol, name) in enumerate(TOP_10_STOCKS, 1):
        print(f"[{idx}/{len(TOP_10_STOCKS)}] {name:20s} ({symbol})", end='', flush=True)

        try:
            engine = BacktestEngine(**params)
            results = engine.run_backtest(
                client=client,
                symbols=[symbol],
                start_date=START_DATE,
                end_date=END_DATE
            )

            if 'trades' in results and results['trades'] is not None:
                trades_data = results['trades']

                if isinstance(trades_data, pd.DataFrame) and not trades_data.empty:
                    num_trades = len(trades_data)
                    total_pnl = trades_data['pnl'].sum()

                    print(f" | {num_trades}トレード, {total_pnl:+,.0f}円")

                    # データ保存
                    for _, trade in trades_data.iterrows():
                        trade_dict = trade.to_dict()
                        trade_dict['symbol'] = symbol
                        trade_dict['stock_name'] = name
                        trade_dict['stop_loss'] = stop_loss_value
                        all_trades.append(trade_dict)
                else:
                    print(" | トレードなし")
            else:
                print(" | データなし")

        except Exception as e:
            print(f" | エラー: {e}")
            continue

    return pd.DataFrame(all_trades) if all_trades else pd.DataFrame()

def analyze_results(results_dict):
    """結果を分析して比較"""
    summary = []

    for label, df in results_dict.items():
        if df.empty:
            continue

        total_pnl = df['pnl'].sum()
        total_trades = len(df)
        win_count = (df['pnl'] > 0).sum()
        win_rate = win_count / total_trades * 100 if total_trades > 0 else 0

        # 決済理由別
        exit_reasons = df['reason'].value_counts()
        profit_exits = exit_reasons.get('profit', 0)
        loss_exits = exit_reasons.get('loss', 0)
        day_end_exits = exit_reasons.get('day_end', 0)

        # 損益レシオ
        wins = df[df['pnl'] > 0]['pnl']
        losses = df[df['pnl'] < 0]['pnl']
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        summary.append({
            'label': label,
            'stop_loss': df['stop_loss'].iloc[0],
            'total_pnl': total_pnl,
            'total_return': total_pnl / BASE_PARAMS['initial_capital'] * 100,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_exits': profit_exits,
            'loss_exits': loss_exits,
            'day_end_exits': day_end_exits,
        })

    return pd.DataFrame(summary).sort_values('stop_loss')

def main():
    print("=" * 80)
    print("損切りライン最適化（細かい刻み）")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()} (6ヶ月)")
    print(f"銘柄数: {len(TOP_10_STOCKS)}")
    print(f"テスト対象: {', '.join(STOP_LOSS_LABELS)}")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 各損切りラインでバックテスト
    results_dict = {}

    for stop_loss, label in zip(STOP_LOSS_VALUES, STOP_LOSS_LABELS):
        df = run_backtest_with_stop_loss(client, stop_loss, label)
        results_dict[label] = df

    client.disconnect()

    # 分析結果
    summary_df = analyze_results(results_dict)

    print(f"\n{'='*80}")
    print("損切りライン比較結果")
    print(f"{'='*80}\n")

    print(summary_df.to_string(index=False))

    # CSV保存
    summary_df.to_csv('results/optimization/stop_loss_fine_comparison.csv', index=False, encoding='utf-8-sig')

    # 可視化
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. 総損益
    ax1 = axes[0, 0]
    colors = ['green' if pnl > 0 else 'red' for pnl in summary_df['total_pnl']]
    ax1.bar(summary_df['label'], summary_df['total_pnl'], color=colors, alpha=0.7, edgecolor='black')
    ax1.set_title('損切りライン別 総損益', fontsize=14, fontweight='bold')
    ax1.set_xlabel('損切りライン', fontsize=12)
    ax1.set_ylabel('総損益（円）', fontsize=12)
    ax1.grid(True, axis='y', alpha=0.3)
    ax1.axhline(y=0, color='black', linewidth=1)

    # 数値ラベル
    for i, (label, pnl) in enumerate(zip(summary_df['label'], summary_df['total_pnl'])):
        y_pos = pnl + (100000 if pnl > 0 else -100000)
        ax1.text(i, y_pos, f'{pnl:+,.0f}円', ha='center', fontsize=9, fontweight='bold')

    # 2. 勝率
    ax2 = axes[0, 1]
    ax2.plot(summary_df['label'], summary_df['win_rate'], marker='o', linewidth=2, markersize=10, color='blue')
    ax2.set_title('損切りライン別 勝率', fontsize=14, fontweight='bold')
    ax2.set_xlabel('損切りライン', fontsize=12)
    ax2.set_ylabel('勝率（%）', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 100)

    # 数値ラベル
    for i, (label, wr) in enumerate(zip(summary_df['label'], summary_df['win_rate'])):
        ax2.text(i, wr + 2, f'{wr:.1f}%', ha='center', fontsize=9, fontweight='bold')

    # 3. 損益レシオ
    ax3 = axes[1, 0]
    ax3.plot(summary_df['label'], summary_df['profit_factor'], marker='s', linewidth=2, markersize=10, color='green')
    ax3.set_title('損切りライン別 損益レシオ', fontsize=14, fontweight='bold')
    ax3.set_xlabel('損切りライン', fontsize=12)
    ax3.set_ylabel('損益レシオ', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=1.0, color='red', linestyle='--', linewidth=1, label='損益レシオ=1.0')
    ax3.legend()

    # 数値ラベル
    for i, (label, pf) in enumerate(zip(summary_df['label'], summary_df['profit_factor'])):
        ax3.text(i, pf + 0.05, f'{pf:.2f}', ha='center', fontsize=9, fontweight='bold')

    # 4. 決済理由の内訳
    ax4 = axes[1, 1]
    x = np.arange(len(summary_df))
    width = 0.25

    ax4.bar(x - width, summary_df['profit_exits'], width, label='利益確定', color='green', alpha=0.7)
    ax4.bar(x, summary_df['loss_exits'], width, label='損切り', color='red', alpha=0.7)
    ax4.bar(x + width, summary_df['day_end_exits'], width, label='日中終了', color='blue', alpha=0.7)

    ax4.set_title('損切りライン別 決済理由の内訳', fontsize=14, fontweight='bold')
    ax4.set_xlabel('損切りライン', fontsize=12)
    ax4.set_ylabel('回数', fontsize=12)
    ax4.set_xticks(x)
    ax4.set_xticklabels(summary_df['label'])
    ax4.legend()
    ax4.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/optimization/stop_loss_fine_comparison.png', dpi=200, bbox_inches='tight')

    print(f"\n\n可視化を results/optimization/stop_loss_fine_comparison.png に保存しました")

    # 推奨の判定
    print(f"\n{'='*80}")
    print("推奨損切りライン")
    print(f"{'='*80}\n")

    best_idx = summary_df['total_pnl'].idxmax()
    best_row = summary_df.loc[best_idx]

    print(f"最も総損益が高い: {best_row['label']}")
    print(f"  総損益: {best_row['total_pnl']:+,.0f}円 ({best_row['total_return']:+.2f}%)")
    print(f"  勝率: {best_row['win_rate']:.1f}%")
    print(f"  損益レシオ: {best_row['profit_factor']:.2f}")

    # 0.5%と0.75%の直接比較
    sl_05 = summary_df[summary_df['label'] == '0.5%'].iloc[0]
    sl_075 = summary_df[summary_df['label'] == '0.75%'].iloc[0]

    print(f"\n{'='*80}")
    print("0.5% vs 0.75% 直接比較")
    print(f"{'='*80}\n")

    print(f"【0.5%（現行）】")
    print(f"  総損益: {sl_05['total_pnl']:+,.0f}円 ({sl_05['total_return']:+.2f}%)")
    print(f"  勝率: {sl_05['win_rate']:.1f}%")
    print(f"  損益レシオ: {sl_05['profit_factor']:.2f}")
    print(f"  利益確定: {sl_05['profit_exits']:.0f}回, 損切り: {sl_05['loss_exits']:.0f}回")

    print(f"\n【0.75%（提案）】")
    print(f"  総損益: {sl_075['total_pnl']:+,.0f}円 ({sl_075['total_return']:+.2f}%)")
    print(f"  勝率: {sl_075['win_rate']:.1f}%")
    print(f"  損益レシオ: {sl_075['profit_factor']:.2f}")
    print(f"  利益確定: {sl_075['profit_exits']:.0f}回, 損切り: {sl_075['loss_exits']:.0f}回")

    diff_pnl = sl_075['total_pnl'] - sl_05['total_pnl']
    diff_pct = (diff_pnl / abs(sl_05['total_pnl'])) * 100 if sl_05['total_pnl'] != 0 else 0

    print(f"\n【差分】")
    print(f"  損益差: {diff_pnl:+,.0f}円 ({diff_pct:+.1f}%)")
    print(f"  勝率差: {sl_075['win_rate'] - sl_05['win_rate']:+.1f}%")
    print(f"  損益レシオ差: {sl_075['profit_factor'] - sl_05['profit_factor']:+.2f}")

    if diff_pnl > 0:
        print(f"\n✅ 0.75%の方が{abs(diff_pnl):,.0f}円優れている")
    elif diff_pnl < 0:
        print(f"\n❌ 0.5%の方が{abs(diff_pnl):,.0f}円優れている")
    else:
        print(f"\n⭕ 両者ほぼ同等")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
