#!/usr/bin/env python3
"""
全セクターの9ヶ月間バックテスト（2025年2月〜10月）
テクノロジーセクター以外の銘柄も検証
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from run_individual_backtest import SECTORS, STOCK_NAMES
import warnings
warnings.filterwarnings('ignore')

# Helper function
def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)

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

def run_sector_backtest(client, sector_name, symbols, period_name, start_date, end_date):
    """セクター別バックテスト実行"""
    print(f"  【{period_name}】", end='', flush=True)

    all_trades = []

    for symbol in symbols:
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
                            trade_dict['stock_name'] = STOCK_NAMES.get(symbol, symbol)
                            all_trades.append(trade_dict)
                elif isinstance(trades_data, list):
                    for trade in trades_data:
                        trade['symbol'] = symbol
                        trade['stock_name'] = STOCK_NAMES.get(symbol, symbol)
                        all_trades.append(trade)

        except Exception as e:
            continue

    return pd.DataFrame(all_trades) if all_trades else None

def analyze_sector_period(trades_df, sector_name, period_name, num_stocks):
    """セクター期間別分析"""
    if trades_df is None or trades_df.empty:
        return None

    total_pnl = trades_df['pnl'].sum()
    total_return = total_pnl / (PARAMS['initial_capital'] * num_stocks)

    # 日次統計
    trades_df['date'] = pd.to_datetime(trades_df['entry_time']).dt.date
    daily_pnl = trades_df.groupby('date')['pnl'].sum()

    sharpe = 0
    if len(daily_pnl) > 1:
        daily_returns = daily_pnl / (PARAMS['initial_capital'] * num_stocks)
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0

    win_count = (trades_df['pnl'] > 0).sum()
    total_count = len(trades_df)
    win_rate = win_count / total_count if total_count > 0 else 0

    print(f" リターン: {total_return*100:+.2f}%, Sharpe: {sharpe:.2f}, 勝率: {win_rate*100:.1f}%")

    return {
        'sector': sector_name,
        'period': period_name,
        'return': total_return,
        'sharpe': sharpe,
        'win_rate': win_rate,
        'trades': total_count
    }

def main():
    print("=" * 80)
    print("全セクター 9ヶ月間バックテスト（2025年2月〜10月）")
    print("=" * 80)
    print()

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 全セクター分析結果
    all_results = []

    # セクター別バックテスト
    for sector_name, symbols in SECTORS.items():
        # テクノロジー・通信は既に検証済みなのでスキップ
        if sector_name == "テクノロジー・通信":
            print(f"\n[{sector_name}] スキップ（既に検証済み）")
            continue

        print(f"\n[{sector_name}] {len(symbols)}銘柄")
        print("-" * 80)

        sector_results = []

        # 期間別バックテスト
        for period_name, start_date, end_date in PERIODS:
            trades_df = run_sector_backtest(
                client, sector_name, symbols, period_name, start_date, end_date
            )

            result = analyze_sector_period(trades_df, sector_name, period_name, len(symbols))

            if result:
                sector_results.append(result)
                all_results.append(result)

        # セクター全期間集計
        if sector_results:
            total_return = sum(r['return'] for r in sector_results)
            avg_sharpe = np.mean([r['sharpe'] for r in sector_results])
            avg_win_rate = np.mean([r['win_rate'] for r in sector_results])

            print(f"\n  セクター全期間: リターン {total_return*100:+.2f}%, 平均Sharpe {avg_sharpe:.2f}, 平均勝率 {avg_win_rate*100:.1f}%")

    client.disconnect()

    # 全体サマリー
    print("\n" + "=" * 80)
    print("全セクター期間別サマリー")
    print("=" * 80)
    print()

    if all_results:
        df = pd.DataFrame(all_results)

        # セクター別全期間集計
        print("【セクター別パフォーマンス（全期間）】")
        sector_summary = df.groupby('sector').agg({
            'return': 'sum',
            'sharpe': 'mean',
            'win_rate': 'mean',
            'trades': 'sum'
        }).sort_values('return', ascending=False)

        sector_summary['return'] = sector_summary['return'].apply(lambda x: f"{x*100:+.2f}%")
        sector_summary['sharpe'] = sector_summary['sharpe'].apply(lambda x: f"{x:.2f}")
        sector_summary['win_rate'] = sector_summary['win_rate'].apply(lambda x: f"{x*100:.1f}%")

        print(sector_summary.to_string())
        print()

        # 期間別比較
        print("【期間別パフォーマンス（全セクター平均）】")
        period_summary = df.groupby('period').agg({
            'return': 'mean',
            'sharpe': 'mean',
            'win_rate': 'mean'
        })

        period_summary['return'] = period_summary['return'].apply(lambda x: f"{x*100:+.2f}%")
        period_summary['sharpe'] = period_summary['sharpe'].apply(lambda x: f"{x:.2f}")
        period_summary['win_rate'] = period_summary['win_rate'].apply(lambda x: f"{x*100:.1f}%")

        print(period_summary.to_string())
        print()

        # CSV保存
        df.to_csv('results/optimization/all_sectors_9months_detailed.csv', index=False, encoding='utf-8-sig')
        print("詳細結果を results/optimization/all_sectors_9months_detailed.csv に保存しました")

    print()
    print("=" * 80)
    print("分析完了")
    print("=" * 80)

if __name__ == "__main__":
    main()
