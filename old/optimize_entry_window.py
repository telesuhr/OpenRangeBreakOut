#!/usr/bin/env python3
"""
エントリー時間帯最適化
09:15から何時までエントリーを許可するかを検証
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
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,
    'stop_loss': 0.0075,  # 最適化済み0.75%
}

# テストするエントリー終了時刻
ENTRY_END_TIMES = [
    ('10:00', jst_to_utc_time('10:00')),
    ('11:00', jst_to_utc_time('11:00')),
    ('12:00', jst_to_utc_time('12:00')),
    ('13:00', jst_to_utc_time('13:00')),
    ('14:00', jst_to_utc_time('14:00')),
    ('15:00', jst_to_utc_time('15:00')),
]

def run_backtest_with_entry_window(client, entry_end_time, label):
    """指定されたエントリー終了時刻でバックテストを実行"""
    print(f"\n{'='*80}")
    print(f"エントリー時間帯: 09:15～{label}")
    print(f"{'='*80}")

    params = BASE_PARAMS.copy()
    params['entry_end'] = entry_end_time

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
                        trade_dict['entry_window'] = label
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

        # 平均保有時間（分）
        if 'entry_time' in df.columns and 'exit_time' in df.columns:
            df['entry_dt'] = pd.to_datetime(df['entry_time'])
            df['exit_dt'] = pd.to_datetime(df['exit_time'])
            df['duration_min'] = (df['exit_dt'] - df['entry_dt']).dt.total_seconds() / 60
            avg_duration = df['duration_min'].mean()
        else:
            avg_duration = 0

        summary.append({
            'entry_window': label,
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
            'avg_duration_min': avg_duration,
        })

    return pd.DataFrame(summary)

def main():
    print("=" * 80)
    print("エントリー時間帯最適化")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()} (6ヶ月)")
    print(f"銘柄数: {len(TOP_10_STOCKS)}")
    print(f"テスト対象: {', '.join([label for label, _ in ENTRY_END_TIMES])}")
    print(f"固定パラメータ: 損切り0.75%, 利確4.0%")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 各エントリー終了時刻でバックテスト
    results_dict = {}

    for label, entry_end in ENTRY_END_TIMES:
        df = run_backtest_with_entry_window(client, entry_end, label)
        results_dict[label] = df

    client.disconnect()

    # 分析結果
    summary_df = analyze_results(results_dict)

    print(f"\n{'='*80}")
    print("エントリー時間帯比較結果")
    print(f"{'='*80}\n")

    print(summary_df.to_string(index=False))

    # CSV保存
    summary_df.to_csv('results/optimization/entry_window_comparison.csv', index=False, encoding='utf-8-sig')

    # 可視化
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))

    # 1. 総損益
    ax1 = axes[0, 0]
    colors = ['green' if pnl > 0 else 'red' for pnl in summary_df['total_pnl']]
    ax1.bar(summary_df['entry_window'], summary_df['total_pnl'], color=colors, alpha=0.7, edgecolor='black')
    ax1.set_title('エントリー時間帯別 総損益', fontsize=14, fontweight='bold')
    ax1.set_xlabel('エントリー終了時刻', fontsize=12)
    ax1.set_ylabel('総損益（円）', fontsize=12)
    ax1.grid(True, axis='y', alpha=0.3)
    ax1.axhline(y=0, color='black', linewidth=1)
    ax1.tick_params(axis='x', rotation=45)

    # 数値ラベル
    for i, (label, pnl) in enumerate(zip(summary_df['entry_window'], summary_df['total_pnl'])):
        y_pos = pnl + (100000 if pnl > 0 else -100000)
        ax1.text(i, y_pos, f'{pnl:+,.0f}円', ha='center', fontsize=9, fontweight='bold')

    # 2. トレード数
    ax2 = axes[0, 1]
    ax2.bar(summary_df['entry_window'], summary_df['total_trades'], color='steelblue', alpha=0.7, edgecolor='black')
    ax2.set_title('エントリー時間帯別 トレード数', fontsize=14, fontweight='bold')
    ax2.set_xlabel('エントリー終了時刻', fontsize=12)
    ax2.set_ylabel('トレード数', fontsize=12)
    ax2.grid(True, axis='y', alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)

    # 数値ラベル
    for i, (label, count) in enumerate(zip(summary_df['entry_window'], summary_df['total_trades'])):
        ax2.text(i, count + 10, f'{count:.0f}', ha='center', fontsize=9, fontweight='bold')

    # 3. 勝率
    ax3 = axes[0, 2]
    ax3.plot(summary_df['entry_window'], summary_df['win_rate'], marker='o', linewidth=2, markersize=10, color='blue')
    ax3.set_title('エントリー時間帯別 勝率', fontsize=14, fontweight='bold')
    ax3.set_xlabel('エントリー終了時刻', fontsize=12)
    ax3.set_ylabel('勝率（%）', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 100)
    ax3.tick_params(axis='x', rotation=45)

    # 数値ラベル
    for i, (label, wr) in enumerate(zip(summary_df['entry_window'], summary_df['win_rate'])):
        ax3.text(i, wr + 2, f'{wr:.1f}%', ha='center', fontsize=9, fontweight='bold')

    # 4. 損益レシオ
    ax4 = axes[1, 0]
    ax4.plot(summary_df['entry_window'], summary_df['profit_factor'], marker='s', linewidth=2, markersize=10, color='green')
    ax4.set_title('エントリー時間帯別 損益レシオ', fontsize=14, fontweight='bold')
    ax4.set_xlabel('エントリー終了時刻', fontsize=12)
    ax4.set_ylabel('損益レシオ', fontsize=12)
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=1.0, color='red', linestyle='--', linewidth=1, label='損益レシオ=1.0')
    ax4.legend()
    ax4.tick_params(axis='x', rotation=45)

    # 数値ラベル
    for i, (label, pf) in enumerate(zip(summary_df['entry_window'], summary_df['profit_factor'])):
        ax4.text(i, pf + 0.05, f'{pf:.2f}', ha='center', fontsize=9, fontweight='bold')

    # 5. 平均保有時間
    ax5 = axes[1, 1]
    ax5.bar(summary_df['entry_window'], summary_df['avg_duration_min'], color='orange', alpha=0.7, edgecolor='black')
    ax5.set_title('エントリー時間帯別 平均保有時間', fontsize=14, fontweight='bold')
    ax5.set_xlabel('エントリー終了時刻', fontsize=12)
    ax5.set_ylabel('平均保有時間（分）', fontsize=12)
    ax5.grid(True, axis='y', alpha=0.3)
    ax5.tick_params(axis='x', rotation=45)

    # 数値ラベル
    for i, (label, duration) in enumerate(zip(summary_df['entry_window'], summary_df['avg_duration_min'])):
        ax5.text(i, duration + 2, f'{duration:.1f}分', ha='center', fontsize=9, fontweight='bold')

    # 6. 決済理由の内訳
    ax6 = axes[1, 2]
    x = np.arange(len(summary_df))
    width = 0.25

    ax6.bar(x - width, summary_df['profit_exits'], width, label='利益確定', color='green', alpha=0.7)
    ax6.bar(x, summary_df['loss_exits'], width, label='損切り', color='red', alpha=0.7)
    ax6.bar(x + width, summary_df['day_end_exits'], width, label='日中終了', color='blue', alpha=0.7)

    ax6.set_title('エントリー時間帯別 決済理由の内訳', fontsize=14, fontweight='bold')
    ax6.set_xlabel('エントリー終了時刻', fontsize=12)
    ax6.set_ylabel('回数', fontsize=12)
    ax6.set_xticks(x)
    ax6.set_xticklabels(summary_df['entry_window'], rotation=45)
    ax6.legend()
    ax6.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/optimization/entry_window_comparison.png', dpi=200, bbox_inches='tight')

    print(f"\n\n可視化を results/optimization/entry_window_comparison.png に保存しました")

    # 推奨の判定
    print(f"\n{'='*80}")
    print("推奨エントリー時間帯")
    print(f"{'='*80}\n")

    best_idx = summary_df['total_pnl'].idxmax()
    best_row = summary_df.loc[best_idx]

    print(f"最も総損益が高い: 09:15～{best_row['entry_window']}")
    print(f"  総損益: {best_row['total_pnl']:+,.0f}円 ({best_row['total_return']:+.2f}%)")
    print(f"  トレード数: {best_row['total_trades']:.0f}回")
    print(f"  勝率: {best_row['win_rate']:.1f}%")
    print(f"  損益レシオ: {best_row['profit_factor']:.2f}")
    print(f"  平均保有時間: {best_row['avg_duration_min']:.1f}分")

    # 現行（10:00）との比較
    current_10am = summary_df[summary_df['entry_window'] == '10:00'].iloc[0]

    print(f"\n{'='*80}")
    print("現行（09:15～10:00）との比較")
    print(f"{'='*80}\n")

    print(f"【現行：09:15～10:00】")
    print(f"  総損益: {current_10am['total_pnl']:+,.0f}円 ({current_10am['total_return']:+.2f}%)")
    print(f"  トレード数: {current_10am['total_trades']:.0f}回")
    print(f"  勝率: {current_10am['win_rate']:.1f}%")
    print(f"  損益レシオ: {current_10am['profit_factor']:.2f}")

    if best_row['entry_window'] != '10:00':
        print(f"\n【最適：09:15～{best_row['entry_window']}】")
        print(f"  総損益: {best_row['total_pnl']:+,.0f}円 ({best_row['total_return']:+.2f}%)")
        print(f"  トレード数: {best_row['total_trades']:.0f}回")
        print(f"  勝率: {best_row['win_rate']:.1f}%")
        print(f"  損益レシオ: {best_row['profit_factor']:.2f}")

        diff_pnl = best_row['total_pnl'] - current_10am['total_pnl']
        diff_pct = (diff_pnl / abs(current_10am['total_pnl'])) * 100 if current_10am['total_pnl'] != 0 else 0
        diff_trades = best_row['total_trades'] - current_10am['total_trades']

        print(f"\n【差分】")
        print(f"  損益差: {diff_pnl:+,.0f}円 ({diff_pct:+.1f}%)")
        print(f"  トレード数差: {diff_trades:+.0f}回")
        print(f"  勝率差: {best_row['win_rate'] - current_10am['win_rate']:+.1f}%")
        print(f"  損益レシオ差: {best_row['profit_factor'] - current_10am['profit_factor']:+.2f}")

        if diff_pnl > 0:
            print(f"\n✅ 09:15～{best_row['entry_window']}の方が{abs(diff_pnl):,.0f}円優れている")
        elif diff_pnl < 0:
            print(f"\n❌ 現行09:15～10:00の方が{abs(diff_pnl):,.0f}円優れている")
        else:
            print(f"\n⭕ 両者ほぼ同等")
    else:
        print(f"\n✅ 現行の09:15～10:00が最適")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
