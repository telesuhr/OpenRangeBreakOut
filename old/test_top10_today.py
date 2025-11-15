#!/usr/bin/env python3
"""
推奨トップ10銘柄 2025/11/13 バックテスト
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
import warnings
warnings.filterwarnings('ignore')

def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)

# 推奨トップ10銘柄
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

# 本日の日付
TARGET_DATE = datetime(2025, 11, 13)

# バックテストパラメータ
PARAMS = {
    'initial_capital': 10000000,
    'commission_rate': 0.001,
    'range_start': jst_to_utc_time('09:05'),
    'range_end': jst_to_utc_time('09:15'),
    'entry_start': jst_to_utc_time('09:15'),
    'entry_end': jst_to_utc_time('10:00'),
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,
    'stop_loss': 0.005,
}

def main():
    print("=" * 80)
    print("推奨トップ10銘柄 2025/11/13 バックテスト")
    print("=" * 80)
    print(f"\n対象日: {TARGET_DATE.date()}")
    print(f"銘柄数: {len(TOP_10_STOCKS)}")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    all_trades = []
    results_summary = []

    print(f"\n{'-'*80}")

    for idx, (symbol, name) in enumerate(TOP_10_STOCKS, 1):
        print(f"[{idx}/{len(TOP_10_STOCKS)}] {name:20s} ({symbol})", end='', flush=True)

        try:
            engine = BacktestEngine(**PARAMS)
            results = engine.run_backtest(
                client=client,
                symbols=[symbol],
                start_date=TARGET_DATE,
                end_date=TARGET_DATE
            )

            if 'trades' in results and results['trades'] is not None:
                trades_data = results['trades']

                if isinstance(trades_data, pd.DataFrame) and not trades_data.empty:
                    num_trades = len(trades_data)
                    total_pnl = trades_data['pnl'].sum()
                    total_return = total_pnl / PARAMS['initial_capital'] * 100

                    print(f" | {num_trades}トレード, {total_pnl:+,.0f}円 ({total_return:+.2f}%)")

                    # データ保存
                    for _, trade in trades_data.iterrows():
                        trade_dict = trade.to_dict()
                        trade_dict['symbol'] = symbol
                        trade_dict['stock_name'] = name
                        all_trades.append(trade_dict)

                    results_summary.append({
                        'rank': idx,
                        'symbol': symbol,
                        'name': name,
                        'trades': num_trades,
                        'pnl': total_pnl,
                        'return_pct': total_return
                    })
                else:
                    print(" | トレードなし")
                    results_summary.append({
                        'rank': idx,
                        'symbol': symbol,
                        'name': name,
                        'trades': 0,
                        'pnl': 0,
                        'return_pct': 0
                    })
            else:
                print(" | データなし")
                results_summary.append({
                    'rank': idx,
                    'symbol': symbol,
                    'name': name,
                    'trades': 0,
                    'pnl': 0,
                    'return_pct': 0
                })

        except Exception as e:
            print(f" | エラー: {e}")
            results_summary.append({
                'rank': idx,
                'symbol': symbol,
                'name': name,
                'trades': 0,
                'pnl': 0,
                'return_pct': 0
            })
            continue

    client.disconnect()

    # 結果を保存
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df.to_csv('results/optimization/top10_trades_20251113.csv', index=False, encoding='utf-8-sig')
        print(f"\n\nトレード詳細を保存: results/optimization/top10_trades_20251113.csv")
        print(f"総トレード数: {len(trades_df)}")

    # サマリー
    if results_summary:
        summary_df = pd.DataFrame(results_summary)
        summary_df = summary_df.sort_values('pnl', ascending=False)

        print(f"\n{'='*80}")
        print("本日のパフォーマンスランキング")
        print(f"{'='*80}\n")

        print(f"{'順位':<6s}{'銘柄':<20s}{'トレード':<10s}{'損益':<15s}{'リターン':<10s}")
        print("-" * 70)

        for position, (_, row) in enumerate(summary_df.iterrows(), 1):
            emoji = "🥇" if position == 1 else "🥈" if position == 2 else "🥉" if position == 3 else "  "
            print(f"{emoji}{position:<4d}{row['name']:<20s}{row['trades']:>8.0f}回  {row['pnl']:>13,.0f}円  {row['return_pct']:>8.2f}%")

        # 合計
        total_pnl = summary_df['pnl'].sum()
        total_trades = summary_df['trades'].sum()
        avg_return = summary_df['return_pct'].mean()

        print(f"\n{'-'*70}")
        print(f"{'合計':<26s}{total_trades:>8.0f}回  {total_pnl:>13,.0f}円  {avg_return:>8.2f}%")

        summary_df.to_csv('results/optimization/top10_summary_20251113.csv', index=False, encoding='utf-8-sig')

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
