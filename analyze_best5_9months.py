#!/usr/bin/env python3
"""
最優秀5銘柄の9ヶ月間バックテスト（2025年2月〜10月）
- 全期間パフォーマンス
- 期間別比較（Q1/Q2/Q3）
- レンジボラティリティ時系列分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from run_individual_backtest import STOCK_NAMES
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans']

# Helper function
def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)

# 最優秀5銘柄
BEST_STOCKS = [
    ('6762.T', 'TDK'),
    ('9984.T', 'ソフトバンクG'),
    ('6857.T', 'アドバンテスト'),
    ('6752.T', 'パナソニック'),
    ('6758.T', 'ソニーグループ'),
]

# バックテストパラメータ
PARAMS = {
    'initial_capital': 10000000,
    'commission_rate': 0.001,
    'range_start': jst_to_utc_time('09:05'),
    'range_end': jst_to_utc_time('09:15'),
    'entry_start': jst_to_utc_time('09:15'),
    'entry_end': jst_to_utc_time('10:00'),
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,  # 4.0%
    'stop_loss': 0.005,     # 0.5%
}

# 分析期間
PERIODS = [
    ("Q1 (2-4月)", datetime(2025, 2, 1), datetime(2025, 4, 30)),
    ("Q2 (5-7月)", datetime(2025, 5, 1), datetime(2025, 7, 31)),
    ("Q3 (8-10月)", datetime(2025, 8, 1), datetime(2025, 10, 31)),
]

def run_period_backtest(client, symbols, period_name, start_date, end_date):
    """期間別バックテスト実行"""
    print(f"\n【{period_name}】{start_date.date()} 〜 {end_date.date()}")
    print("-" * 80)

    all_trades = []

    for idx, (symbol, name) in enumerate(symbols, 1):
        print(f"  [{idx}/{len(symbols)}] {name:25s}", end='', flush=True)

        try:
            engine = BacktestEngine(**PARAMS)
            results = engine.run_backtest(
                client=client,
                symbols=[symbol],
                start_date=start_date,
                end_date=end_date
            )

            if 'trades' in results and results['trades'] is not None:
                trades_data = results['trades']

                if isinstance(trades_data, pd.DataFrame):
                    if not trades_data.empty:
                        for _, trade in trades_data.iterrows():
                            trade_dict = trade.to_dict()
                            trade_dict['symbol'] = symbol
                            trade_dict['stock_name'] = name
                            all_trades.append(trade_dict)
                elif isinstance(trades_data, list):
                    for trade in trades_data:
                        trade['symbol'] = symbol
                        trade['stock_name'] = name
                        all_trades.append(trade)

            print(f" ✓")

        except Exception as e:
            print(f" ✗ エラー: {e}")
            continue

    return pd.DataFrame(all_trades) if all_trades else None

def analyze_period(trades_df, period_name):
    """期間別分析"""
    if trades_df is None or trades_df.empty:
        return None

    total_pnl = trades_df['pnl'].sum()
    total_return = total_pnl / (PARAMS['initial_capital'] * len(BEST_STOCKS))

    # 銘柄別統計
    stock_stats = []

    for symbol, name in BEST_STOCKS:
        stock_trades = trades_df[trades_df['symbol'] == symbol]

        if stock_trades.empty:
            continue

        stock_pnl = stock_trades['pnl'].sum()
        stock_return = stock_pnl / PARAMS['initial_capital']

        win_count = (stock_trades['pnl'] > 0).sum()
        total_count = len(stock_trades)
        win_rate = win_count / total_count if total_count > 0 else 0

        # 日次P&L
        stock_trades['date'] = pd.to_datetime(stock_trades['entry_time']).dt.date
        daily_pnl = stock_trades.groupby('date')['pnl'].sum()

        sharpe = 0
        if len(daily_pnl) > 1:
            daily_returns = daily_pnl / PARAMS['initial_capital']
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0

        stock_stats.append({
            'symbol': symbol,
            'name': name,
            'pnl': stock_pnl,
            'return': stock_return,
            'trades': total_count,
            'win_rate': win_rate,
            'sharpe': sharpe
        })

    stats_df = pd.DataFrame(stock_stats).sort_values('return', ascending=False)

    print(f"\n  ポートフォリオリターン: {total_return*100:+.2f}%")
    print(f"  平均Sharpe Ratio: {stats_df['sharpe'].mean():.2f}")
    print(f"  勝率: {stats_df['win_rate'].mean()*100:.1f}%")
    print()

    return{
        'period': period_name,
        'total_return': total_return,
        'avg_sharpe': stats_df['sharpe'].mean(),
        'avg_win_rate': stats_df['win_rate'].mean(),
        'trades_df': trades_df,
        'stock_stats': stats_df
    }

def main():
    print("=" * 80)
    print("最優秀5銘柄の9ヶ月間バックテスト")
    print("=" * 80)
    print()
    print(f"対象銘柄:")
    for symbol, name in BEST_STOCKS:
        print(f"  - {name} ({symbol})")
    print()
    print(f"初期資金: {PARAMS['initial_capital']:,}円 × 5銘柄 = {PARAMS['initial_capital'] * 5:,}円")
    print(f"利確目標: {PARAMS['profit_target']*100:.1f}%, 損切り: {PARAMS['stop_loss']*100:.1f}%")
    print("=" * 80)

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 期間別バックテスト
    period_results = []

    for period_name, start_date, end_date in PERIODS:
        trades_df = run_period_backtest(client, BEST_STOCKS, period_name, start_date, end_date)

        if trades_df is not None:
            result = analyze_period(trades_df, period_name)
            if result:
                period_results.append(result)

                # CSV保存
                filename = f"results/optimization/best5_{period_name.replace(' ', '_').replace('(', '').replace(')', '')}.csv"
                result['stock_stats'].to_csv(filename, index=False, encoding='utf-8-sig')

    client.disconnect()

    # 全期間サマリー
    print("\n" + "=" * 80)
    print("期間別サマリー")
    print("=" * 80)
    print()

    if period_results:
        summary_data = [{
            'period': r['period'],
            'return': f"{r['total_return']*100:+.2f}%",
            'sharpe': f"{r['avg_sharpe']:.2f}",
            'win_rate': f"{r['avg_win_rate']*100:.1f}%"
        } for r in period_results]

        summary_df = pd.DataFrame(summary_data)
        print(summary_df.to_string(index=False))
        print()

        # 全期間統計
        total_return = sum(r['total_return'] for r in period_results)
        avg_sharpe = np.mean([r['avg_sharpe'] for r in period_results])

        print(f"全期間（9ヶ月）合計リターン: {total_return*100:+.2f}%")
        print(f"平均Sharpe Ratio: {avg_sharpe:.2f}")
        print()

        # CSV保存
        summary_df.to_csv('results/optimization/best5_period_comparison.csv', index=False, encoding='utf-8-sig')

    print("=" * 80)
    print("分析完了")
    print("=" * 80)

if __name__ == "__main__":
    main()
