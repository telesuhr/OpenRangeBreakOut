#!/usr/bin/env python3
"""
トップ10銘柄の直近30営業日バックテスト
ヒートマップ用の詳細データを生成
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

# トップ10銘柄
TOP_10_STOCKS = [
    ('9984.T', 'ソフトバンクG'),
    ('6503.T', '三菱電機'),
    ('6762.T', 'TDK'),
    ('6857.T', 'アドバンテスト'),
    ('9432.T', 'NTT'),
    ('6954.T', 'ファナック'),
    ('6752.T', 'パナソニック'),
    ('6861.T', 'キーエンス'),
    ('9433.T', 'KDDI'),
    ('4901.T', '富士フイルムHD'),
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
    print("トップ10銘柄 直近30営業日バックテスト")
    print("=" * 80)
    print()

    # 直近30営業日の期間を設定（10月1日〜11月12日で約30営業日）
    start_date = datetime(2025, 10, 1)
    end_date = datetime(2025, 11, 12)

    print(f"期間: {start_date.date()} ～ {end_date.date()}")
    print(f"対象銘柄: {len(TOP_10_STOCKS)}銘柄")
    print()

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    all_trades = []

    print("-" * 80)

    for idx, (symbol, name) in enumerate(TOP_10_STOCKS, 1):
        print(f"[{idx}/{len(TOP_10_STOCKS)}] {name:20s} ({symbol})", end='', flush=True)

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

                if isinstance(trades_data, pd.DataFrame) and not trades_data.empty:
                    total_pnl = trades_data['pnl'].sum()
                    total_return = total_pnl / PARAMS['initial_capital']
                    num_trades = len(trades_data)
                    win_count = (trades_data['pnl'] > 0).sum()

                    print(f" | {num_trades}トレード, P&L: {total_pnl:+,.0f}円 ({total_return*100:+.2f}%), 勝率: {win_count}/{num_trades}")

                    # 詳細記録
                    for _, trade in trades_data.iterrows():
                        trade_dict = trade.to_dict()
                        trade_dict['symbol'] = symbol
                        trade_dict['stock_name'] = name
                        all_trades.append(trade_dict)

                elif isinstance(trades_data, list) and len(trades_data) > 0:
                    total_pnl = sum(t['pnl'] for t in trades_data)
                    total_return = total_pnl / PARAMS['initial_capital']
                    num_trades = len(trades_data)
                    win_count = sum(1 for t in trades_data if t['pnl'] > 0)

                    print(f" | {num_trades}トレード, P&L: {total_pnl:+,.0f}円 ({total_return*100:+.2f}%), 勝率: {win_count}/{num_trades}")

                    for trade in trades_data:
                        trade['symbol'] = symbol
                        trade['stock_name'] = name
                        all_trades.append(trade)
                else:
                    print(" | トレードなし")
            else:
                print(" | データなし")

        except Exception as e:
            print(f" | エラー: {e}")
            continue

    client.disconnect()

    # データ保存
    print()
    print("=" * 80)

    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        filename = "results/optimization/recent_30days_trades.csv"
        trades_df.to_csv(filename, index=False, encoding='utf-8-sig')

        print(f"総トレード数: {len(trades_df)}")
        print(f"期間: {start_date.date()} ～ {end_date.date()}")
        print()
        print(f"詳細結果を {filename} に保存しました")

        # 日付ごとの統計
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        trades_df['date'] = trades_df['entry_time'].dt.date

        unique_dates = trades_df['date'].nunique()
        unique_stocks = trades_df['stock_name'].nunique()

        print()
        print(f"実際の営業日数: {unique_dates}日")
        print(f"トレード銘柄数: {unique_stocks}銘柄")
    else:
        print("トレードデータなし")

    print()
    print("=" * 80)
    print("バックテスト完了")
    print("=" * 80)

if __name__ == "__main__":
    main()
