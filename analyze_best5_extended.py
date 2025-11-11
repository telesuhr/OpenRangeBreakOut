#!/usr/bin/env python3
"""
最優秀5銘柄の9ヶ月間バックテスト（2025年2月1日〜10月31日）
期間別比較とレンジボラティリティの時系列安定性分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic', 'Noto Sans CJK JP']

# Best 5 stocks
BEST_STOCKS = [
    ('6762.T', 'TDK'),
    ('9984.T', 'ソフトバンクG'),
    ('6857.T', 'アドバンテスト'),
    ('6752.T', 'パナソニック'),
    ('6758.T', 'ソニーグループ'),
]

# Optimal parameters (from previous analysis)
PROFIT_TARGET = 0.04  # 4.0%
STOP_LOSS = 0.005     # 0.5%

def calculate_range_volatility(df, start_time='09:05', end_time='09:15'):
    """Calculate range volatility for each day"""
    df = df.copy()
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df['time'] = pd.to_datetime(df['timestamp']).dt.time

    daily_stats = []

    for date in sorted(df['date'].unique()):
        day_data = df[df['date'] == date].copy()

        # Filter range period
        start_t = datetime.strptime(start_time, '%H:%M').time()
        end_t = datetime.strptime(end_time, '%H:%M').time()

        range_data = day_data[
            (day_data['time'] >= start_t) &
            (day_data['time'] <= end_t)
        ]

        if len(range_data) > 0:
            high = range_data['high'].max()
            low = range_data['low'].min()

            # Calculate volatility
            if low > 0:
                range_vol = (high - low) / low
                daily_stats.append({
                    'date': date,
                    'range_vol': range_vol,
                    'high': high,
                    'low': low
                })

    return pd.DataFrame(daily_stats)

def run_backtest_for_period(client, symbol, name, start_date, end_date):
    """Run backtest for a specific period"""
    print(f"    期間: {start_date.strftime('%Y-%m-%d')} 〜 {end_date.strftime('%Y-%m-%d')}")

    # Get data
    data = client.get_intraday_data(symbol, start_date, end_date, interval='1min')

    if data is None or len(data) == 0:
        print(f"    ⚠ データなし")
        return None, None

    # Calculate range volatility
    range_vol_df = calculate_range_volatility(data)
    avg_range_vol = range_vol_df['range_vol'].mean() if len(range_vol_df) > 0 else 0

    # Run backtest
    strategy = OpenRangeBreakoutStrategy(
        range_start=time(9, 5),
        range_end=time(9, 15),
        profit_target=PROFIT_TARGET,
        stop_loss=STOP_LOSS
    )

    engine = BacktestEngine(strategy)
    trades = engine.run(data)

    if trades is None or len(trades) == 0:
        print(f"    ⚠ トレードなし")
        return None, range_vol_df

    trades_df = pd.DataFrame(trades)
    total_pnl = trades_df['pnl'].sum()
    total_return = total_pnl / 10_000_000

    win_trades = trades_df[trades_df['pnl'] > 0]
    loss_trades = trades_df[trades_df['pnl'] <= 0]

    win_count = len(win_trades)
    loss_count = len(loss_trades)
    win_rate = win_count / len(trades_df) if len(trades_df) > 0 else 0

    avg_win = win_trades['pnl'].mean() if win_count > 0 else 0
    avg_loss = loss_trades['pnl'].mean() if loss_count > 0 else 0

    # Calculate Sharpe ratio
    trades_df['date'] = pd.to_datetime(trades_df['entry_time']).dt.date
    daily_pnl = trades_df.groupby('date')['pnl'].sum()

    if len(daily_pnl) > 1:
        daily_returns = daily_pnl / 10_000_000
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
    else:
        sharpe = 0

    print(f"    リターン: {total_return*100:.2f}%, トレード: {len(trades_df)}, 勝率: {win_rate*100:.1f}%, Sharpe: {sharpe:.2f}, レンジVol: {avg_range_vol*100:.2f}%")

    result = {
        'symbol': symbol,
        'name': name,
        'total_pnl': total_pnl,
        'total_return': total_return,
        'total_trades': len(trades_df),
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'sharpe_ratio': sharpe,
        'avg_range_vol': avg_range_vol,
        'trades': trades_df
    }

    return result, range_vol_df

def main():
    print("=" * 80)
    print("最優秀5銘柄の9ヶ月間バックテスト")
    print("=" * 80)
    print()

    # Period definition
    full_start = datetime(2025, 2, 1)
    full_end = datetime(2025, 10, 31)

    periods = [
        ("Q1 (2-4月)", datetime(2025, 2, 1), datetime(2025, 4, 30)),
        ("Q2 (5-7月)", datetime(2025, 5, 1), datetime(2025, 7, 31)),
        ("Q3 (8-10月)", datetime(2025, 8, 1), datetime(2025, 10, 31)),
    ]

    # Connect to Refinitiv
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # Results storage
    full_period_results = []
    period_results = {period_name: [] for period_name, _, _ in periods}
    range_vol_data = {}

    print(f"全期間: {full_start.strftime('%Y-%m-%d')} 〜 {full_end.strftime('%Y-%m-%d')} (9ヶ月)")
    print()

    # Run backtest for each stock
    for idx, (symbol, name) in enumerate(BEST_STOCKS, 1):
        print(f"[{idx}/5] {name} ({symbol})")
        print("-" * 60)

        # Full period backtest
        print("  【全期間】")
        full_result, full_vol = run_backtest_for_period(client, symbol, name, full_start, full_end)

        if full_result:
            full_period_results.append(full_result)
            range_vol_data[symbol] = {'full': full_vol}

        # Period-by-period backtest
        print("  【期間別】")
        for period_name, period_start, period_end in periods:
            period_result, period_vol = run_backtest_for_period(client, symbol, name, period_start, period_end)

            if period_result:
                period_result['period'] = period_name
                period_results[period_name].append(period_result)
                range_vol_data[symbol][period_name] = period_vol

        print()

    # Save results
    print("=" * 80)
    print("結果集計")
    print("=" * 80)
    print()

    # Full period summary
    if full_period_results:
        full_df = pd.DataFrame([{
            'symbol': r['symbol'],
            'name': r['name'],
            'total_pnl': r['total_pnl'],
            'total_return': r['total_return'],
            'sharpe_ratio': r['sharpe_ratio'],
            'win_rate': r['win_rate'],
            'avg_range_vol': r['avg_range_vol'],
            'total_trades': r['total_trades']
        } for r in full_period_results])

        full_df = full_df.sort_values('total_return', ascending=False)

        print("【全期間サマリー】")
        print(full_df.to_string(index=False))
        print()
        print(f"ポートフォリオ合計リターン: {full_df['total_return'].sum()*100:.2f}%")
        print(f"平均Sharpe Ratio: {full_df['sharpe_ratio'].mean():.2f}")
        print(f"平均レンジボラティリティ: {full_df['avg_range_vol'].mean()*100:.2f}%")
        print()

        full_df.to_csv('results/optimization/best5_extended_full_period.csv', index=False, encoding='utf-8-sig')

    # Period comparison
    print("【期間別比較】")
    period_summary = []

    for period_name, _, _ in periods:
        if period_results[period_name]:
            period_df = pd.DataFrame([{
                'symbol': r['symbol'],
                'name': r['name'],
                'total_return': r['total_return'],
                'sharpe_ratio': r['sharpe_ratio'],
                'avg_range_vol': r['avg_range_vol']
            } for r in period_results[period_name]])

            summary = {
                'period': period_name,
                'portfolio_return': period_df['total_return'].sum(),
                'avg_sharpe': period_df['sharpe_ratio'].mean(),
                'avg_range_vol': period_df['avg_range_vol'].mean(),
                'stocks_count': len(period_df)
            }

            period_summary.append(summary)

            # Save detailed results
            period_df.to_csv(f'results/optimization/best5_{period_name.replace(" ", "_")}.csv',
                           index=False, encoding='utf-8-sig')

    period_summary_df = pd.DataFrame(period_summary)
    print(period_summary_df.to_string(index=False))
    print()

    period_summary_df.to_csv('results/optimization/best5_period_comparison.csv', index=False, encoding='utf-8-sig')

    # Analyze range volatility stability
    print("【レンジボラティリティ時系列安定性】")

    for symbol, name in BEST_STOCKS:
        if symbol in range_vol_data and 'full' in range_vol_data[symbol]:
            vol_df = range_vol_data[symbol]['full']

            if len(vol_df) > 0:
                avg_vol = vol_df['range_vol'].mean()
                std_vol = vol_df['range_vol'].std()
                cv = std_vol / avg_vol if avg_vol > 0 else 0

                print(f"{name}: 平均 {avg_vol*100:.2f}%, 標準偏差 {std_vol*100:.2f}%, 変動係数 {cv:.2f}")

    print()
    print("=" * 80)
    print("分析完了")
    print("=" * 80)

    return full_period_results, period_results, range_vol_data, period_summary_df

if __name__ == "__main__":
    full_results, period_results, range_vol_data, period_summary = main()
