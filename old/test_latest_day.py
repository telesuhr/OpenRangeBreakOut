#!/usr/bin/env python3
"""
2025年11月12日の最新データでバックテスト
最優秀5銘柄の当日パフォーマンスを確認
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
import warnings
warnings.filterwarnings('ignore')

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

# バックテストパラメータ（最適化済み）
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

def main():
    print("=" * 80)
    print("2025年11月12日 最新データバックテスト")
    print("=" * 80)
    print()

    # 本日の日付
    test_date = datetime(2025, 11, 12)
    print(f"テスト日: {test_date.date()}")
    print(f"対象銘柄: {len(BEST_STOCKS)}銘柄")
    print()

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    all_trades = []
    results_summary = []

    print("-" * 80)

    for idx, (symbol, name) in enumerate(BEST_STOCKS, 1):
        print(f"[{idx}/{len(BEST_STOCKS)}] {name:20s} ({symbol})", end='', flush=True)

        try:
            # 当日のみのバックテスト
            engine = BacktestEngine(**PARAMS)
            results = engine.run_backtest(
                client=client,
                symbols=[symbol],
                start_date=test_date,
                end_date=test_date
            )

            if 'trades' in results and results['trades'] is not None:
                trades_data = results['trades']

                if isinstance(trades_data, pd.DataFrame) and not trades_data.empty:
                    total_pnl = trades_data['pnl'].sum()
                    total_return = total_pnl / PARAMS['initial_capital']
                    num_trades = len(trades_data)
                    win_count = (trades_data['pnl'] > 0).sum()

                    print(f" | トレード: {num_trades}, P&L: {total_pnl:+,.0f}円 ({total_return*100:+.2f}%), 勝率: {win_count}/{num_trades}")

                    # 詳細記録
                    for _, trade in trades_data.iterrows():
                        trade_dict = trade.to_dict()
                        trade_dict['symbol'] = symbol
                        trade_dict['stock_name'] = name
                        all_trades.append(trade_dict)

                    results_summary.append({
                        'symbol': symbol,
                        'name': name,
                        'trades': num_trades,
                        'pnl': total_pnl,
                        'return': total_return,
                        'win_rate': win_count / num_trades if num_trades > 0 else 0
                    })

                elif isinstance(trades_data, list) and len(trades_data) > 0:
                    total_pnl = sum(t['pnl'] for t in trades_data)
                    total_return = total_pnl / PARAMS['initial_capital']
                    num_trades = len(trades_data)
                    win_count = sum(1 for t in trades_data if t['pnl'] > 0)

                    print(f" | トレード: {num_trades}, P&L: {total_pnl:+,.0f}円 ({total_return*100:+.2f}%), 勝率: {win_count}/{num_trades}")

                    for trade in trades_data:
                        trade['symbol'] = symbol
                        trade['stock_name'] = name
                        all_trades.append(trade)

                    results_summary.append({
                        'symbol': symbol,
                        'name': name,
                        'trades': num_trades,
                        'pnl': total_pnl,
                        'return': total_return,
                        'win_rate': win_count / num_trades if num_trades > 0 else 0
                    })
                else:
                    print(" | トレードなし")
            else:
                print(" | データなし")

        except Exception as e:
            print(f" | エラー: {e}")
            continue

    client.disconnect()

    # サマリー表示
    print()
    print("=" * 80)
    print("2025年11月12日 サマリー")
    print("=" * 80)
    print()

    if results_summary:
        summary_df = pd.DataFrame(results_summary)

        # ポートフォリオ全体
        total_pnl = summary_df['pnl'].sum()
        total_return = total_pnl / (PARAMS['initial_capital'] * len(BEST_STOCKS))
        total_trades = summary_df['trades'].sum()

        print(f"ポートフォリオ全体:")
        print(f"  総トレード数: {total_trades}")
        print(f"  総損益: {total_pnl:+,.0f}円")
        print(f"  総リターン: {total_return*100:+.2f}%")
        print(f"  平均勝率: {summary_df['win_rate'].mean()*100:.1f}%")
        print()

        # 銘柄別詳細
        print("銘柄別詳細:")
        for _, row in summary_df.iterrows():
            print(f"  {row['name']:20s}: {row['return']*100:+6.2f}% ({row['pnl']:+10,.0f}円), {row['trades']}トレード, 勝率{row['win_rate']*100:.1f}%")

        # CSV保存
        if all_trades:
            trades_df = pd.DataFrame(all_trades)
            filename = f"results/optimization/latest_day_{test_date.strftime('%Y%m%d')}.csv"
            trades_df.to_csv(filename, index=False, encoding='utf-8-sig')
            print()
            print(f"詳細結果を {filename} に保存しました")
    else:
        print("本日はトレードなし、または全銘柄でデータ取得エラー")

    print()
    print("=" * 80)
    print("分析完了")
    print("=" * 80)

if __name__ == "__main__":
    main()
