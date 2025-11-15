#!/usr/bin/env python3
"""
テクノロジー代表銘柄の直近1ヶ月バックテスト
以前パフォーマンスが良かった銘柄を再検証
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

# テクノロジー代表銘柄（以前好成績だった銘柄）
TECH_LEADERS = [
    # ハイテク・半導体（以前のトップパフォーマー）
    ('6762.T', 'TDK'),
    ('6857.T', 'アドバンテスト'),
    ('6758.T', 'キーエンス'),
    ('8035.T', '東京エレクトロン'),
    ('6861.T', 'キーコム'),
    ('6503.T', 'ソニー'),
    ('6752.T', 'パナソニック'),

    # 通信・ソフトウェア
    ('9984.T', 'ソフトバンクG'),
    ('9433.T', 'KDDI'),
    ('9434.T', 'ソフトバンク'),
    ('4704.T', 'トレンドマイクロ'),

    # 非鉄金属（以前のトップパフォーマー）
    ('5706.T', '三井金属鉱業'),
    ('5713.T', '住友金属鉱山'),
    ('5801.T', '古河電気工業'),
]

# バックテスト期間（直近1ヶ月）
END_DATE = datetime(2025, 11, 12)
START_DATE = datetime(2025, 10, 12)

# 最適化済みパラメータ
OPTIMIZED_PARAMS = {
    'initial_capital': 10000000,
    'commission_rate': 0.001,
    'range_start': jst_to_utc_time('09:05'),
    'range_end': jst_to_utc_time('09:15'),
    'entry_start': jst_to_utc_time('09:15'),
    'entry_end': jst_to_utc_time('11:00'),
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,   # 4.0%
    'stop_loss': 0.0075,     # 0.75%
}

def run_backtest(client, symbol, name):
    """単一銘柄のバックテスト実行"""
    try:
        engine = BacktestEngine(**OPTIMIZED_PARAMS)
        results = engine.run_backtest(
            client=client,
            symbols=[symbol],
            start_date=START_DATE,
            end_date=END_DATE
        )

        if 'trades' in results and results['trades'] is not None:
            trades_data = results['trades']

            if isinstance(trades_data, pd.DataFrame) and not trades_data.empty:
                total_pnl = trades_data['pnl'].sum()
                num_trades = len(trades_data)
                win_count = (trades_data['pnl'] > 0).sum()
                win_rate = win_count / num_trades * 100 if num_trades > 0 else 0

                # 損益レシオ
                wins = trades_data[trades_data['pnl'] > 0]['pnl']
                losses = trades_data[trades_data['pnl'] < 0]['pnl']
                avg_win = wins.mean() if len(wins) > 0 else 0
                avg_loss = losses.mean() if len(losses) > 0 else 0
                profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

                # 日次損益を取得
                trades_data['date'] = pd.to_datetime(trades_data['entry_time']).dt.date
                daily_pnl = trades_data.groupby('date')['pnl'].sum()

                return {
                    'symbol': symbol,
                    'name': name,
                    'total_pnl': total_pnl,
                    'total_return': total_pnl / OPTIMIZED_PARAMS['initial_capital'] * 100,
                    'num_trades': num_trades,
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'daily_pnl': daily_pnl,
                    'trades': trades_data,
                }

        return None

    except Exception as e:
        print(f"  エラー: {e}")
        return None

def main():
    print("=" * 80)
    print("テクノロジー代表銘柄 直近1ヶ月バックテスト")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()} (1ヶ月)")
    print(f"テスト銘柄数: {len(TECH_LEADERS)}")
    print(f"\n【最適化済みパラメータ】")
    print(f"  損切り: 0.75%")
    print(f"  エントリー時間: 09:15-11:00")
    print(f"  利確目標: 4.0%")
    print(f"  初期資金: 1,000万円")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    results = []
    all_daily_pnl = {}

    for idx, (symbol, name) in enumerate(TECH_LEADERS, 1):
        print(f"\n[{idx}/{len(TECH_LEADERS)}] {name:20s} ({symbol})", end='', flush=True)

        result = run_backtest(client, symbol, name)

        if result:
            print(f" | {result['num_trades']}トレード, {result['total_pnl']:+,.0f}円 ({result['win_rate']:.1f}%)")
            results.append({
                'symbol': result['symbol'],
                'name': result['name'],
                'total_pnl': result['total_pnl'],
                'total_return': result['total_return'],
                'num_trades': result['num_trades'],
                'win_rate': result['win_rate'],
                'profit_factor': result['profit_factor'],
                'avg_win': result['avg_win'],
                'avg_loss': result['avg_loss'],
            })
            all_daily_pnl[name] = result['daily_pnl']
        else:
            print(" | データなし")

    client.disconnect()

    if not results:
        print("\n有効な結果がありませんでした")
        return

    # 結果をDataFrameに変換
    df = pd.DataFrame(results)

    # 総損益でソート
    df = df.sort_values('total_pnl', ascending=False).reset_index(drop=True)

    print(f"\n{'='*80}")
    print("バックテスト結果サマリー（総損益順）")
    print(f"{'='*80}\n")

    print("【全銘柄】")
    print(df.to_string(index=False))

    # 統計サマリー
    print(f"\n{'='*80}")
    print("全体統計")
    print(f"{'='*80}\n")

    total_tested = len(df)
    profitable = (df['total_pnl'] > 0).sum()
    unprofitable = (df['total_pnl'] < 0).sum()

    print(f"テスト銘柄数: {total_tested}")
    print(f"利益銘柄数: {profitable} ({profitable/total_tested*100:.1f}%)")
    print(f"損失銘柄数: {unprofitable} ({unprofitable/total_tested*100:.1f}%)")
    print(f"\n平均損益: {df['total_pnl'].mean():+,.0f}円")
    print(f"平均リターン: {df['total_return'].mean():+.2f}%")
    print(f"平均勝率: {df['win_rate'].mean():.1f}%")
    print(f"平均損益レシオ: {df['profit_factor'].mean():.2f}")

    # トップ5とワースト5
    print(f"\n{'='*80}")
    print("トップ5銘柄")
    print(f"{'='*80}")
    top5 = df.head(5)
    for idx, row in top5.iterrows():
        print(f"{idx+1}. {row['name']:20s} {row['total_pnl']:+12,.0f}円 ({row['total_return']:+6.2f}%) "
              f"勝率{row['win_rate']:5.1f}% {row['num_trades']}トレード")

    print(f"\n{'='*80}")
    print("ワースト5銘柄")
    print(f"{'='*80}")
    worst5 = df.tail(5).iloc[::-1]
    for idx, row in worst5.iterrows():
        print(f"{len(df)-idx}. {row['name']:20s} {row['total_pnl']:+12,.0f}円 ({row['total_return']:+6.2f}%) "
              f"勝率{row['win_rate']:5.1f}% {row['num_trades']}トレード")

    # CSV保存
    df.to_csv('results/optimization/tech_leaders_1month.csv', index=False, encoding='utf-8-sig')
    print(f"\n結果を results/optimization/tech_leaders_1month.csv に保存しました")

    # 日次損益の集計
    if all_daily_pnl:
        print(f"\n{'='*80}")
        print("日次損益サマリー（全銘柄合計）")
        print(f"{'='*80}\n")

        # 全銘柄の日次損益を統合
        all_dates = sorted(set().union(*[set(pnl.index) for pnl in all_daily_pnl.values()]))
        daily_total = pd.Series(0.0, index=all_dates)

        for name, pnl in all_daily_pnl.items():
            daily_total = daily_total.add(pnl, fill_value=0)

        print(f"{'日付':12s} {'合計損益':>15s} {'累積損益':>15s}")
        print("-" * 50)
        cumsum = 0
        for date, pnl in daily_total.items():
            cumsum += pnl
            print(f"{str(date):12s} {pnl:>15,.0f} {cumsum:>15,.0f}")

    # 可視化
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    # 1. 総損益バーチャート
    ax1 = axes[0, 0]
    colors = ['green' if pnl > 0 else 'red' for pnl in df['total_pnl']]
    ax1.barh(range(len(df)), df['total_pnl'], color=colors, alpha=0.7, edgecolor='black')
    ax1.set_yticks(range(len(df)))
    ax1.set_yticklabels(df['name'], fontsize=9)
    ax1.set_xlabel('総損益（円）', fontsize=12)
    ax1.set_title('テクノロジー代表銘柄 総損益（直近1ヶ月）', fontsize=14, fontweight='bold')
    ax1.axvline(x=0, color='black', linewidth=1)
    ax1.grid(True, axis='x', alpha=0.3)
    ax1.invert_yaxis()

    # 2. 勝率 vs 総損益
    ax2 = axes[0, 1]
    colors = ['green' if pnl > 0 else 'red' for pnl in df['total_pnl']]
    ax2.scatter(df['win_rate'], df['total_pnl'], c=colors, alpha=0.6, s=150, edgecolors='black')
    for _, row in df.iterrows():
        ax2.annotate(row['name'], (row['win_rate'], row['total_pnl']),
                    fontsize=8, alpha=0.7)
    ax2.set_xlabel('勝率（%）', fontsize=12)
    ax2.set_ylabel('総損益（円）', fontsize=12)
    ax2.set_title('勝率 vs 総損益', fontsize=14, fontweight='bold')
    ax2.axhline(y=0, color='black', linewidth=1, linestyle='--')
    ax2.grid(True, alpha=0.3)

    # 3. トレード数 vs 総損益
    ax3 = axes[1, 0]
    colors = ['green' if pnl > 0 else 'red' for pnl in df['total_pnl']]
    ax3.scatter(df['num_trades'], df['total_pnl'], c=colors, alpha=0.6, s=150, edgecolors='black')
    for _, row in df.iterrows():
        ax3.annotate(row['name'], (row['num_trades'], row['total_pnl']),
                    fontsize=8, alpha=0.7)
    ax3.set_xlabel('トレード数', fontsize=12)
    ax3.set_ylabel('総損益（円）', fontsize=12)
    ax3.set_title('トレード数 vs 総損益', fontsize=14, fontweight='bold')
    ax3.axhline(y=0, color='black', linewidth=1, linestyle='--')
    ax3.grid(True, alpha=0.3)

    # 4. 日次累積損益（全銘柄合計）
    ax4 = axes[1, 1]
    if all_daily_pnl:
        cumsum_series = daily_total.cumsum()
        ax4.plot(range(len(cumsum_series)), cumsum_series.values,
                marker='o', linewidth=2, markersize=6, color='steelblue')
        ax4.axhline(y=0, color='red', linewidth=1, linestyle='--')
        ax4.set_xlabel('取引日', fontsize=12)
        ax4.set_ylabel('累積損益（円）', fontsize=12)
        ax4.set_title('日次累積損益（全銘柄合計）', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)

        # X軸ラベルを日付に
        date_labels = [str(d) for d in cumsum_series.index]
        step = max(1, len(date_labels) // 10)
        ax4.set_xticks(range(0, len(date_labels), step))
        ax4.set_xticklabels([date_labels[i] for i in range(0, len(date_labels), step)],
                           rotation=45, ha='right', fontsize=8)

    plt.tight_layout()
    plt.savefig('results/optimization/tech_leaders_1month.png', dpi=200, bbox_inches='tight')

    print(f"可視化を results/optimization/tech_leaders_1month.png に保存しました")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
