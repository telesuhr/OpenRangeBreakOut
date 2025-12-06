#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日次データ品質チェック

1年間の日次データを確認し、欠損や異常を検出する
"""

import sys
from pathlib import Path
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import numpy as np

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_daily_data_quality():
    """日次データ品質チェック"""

    print("=" * 80)
    print("日次データ品質チェック")
    print("=" * 80)

    # データベース接続
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="market_data",
            user="postgres",
            password="postgres"
        )
        cur = conn.cursor()
        print("\nデータベース接続成功")
    except Exception as e:
        print(f"\nデータベース接続エラー: {e}")
        return

    # バックテスト対象銘柄
    symbols = [
        '2502.T', '2503.T', '2801.T', '4183.T', '5016.T', '5332.T',
        '5706.T', '5713.T', '5714.T', '5801.T', '5802.T', '5803.T',
        '6146.T', '6752.T', '6762.T', '7013.T', '7741.T', '8001.T',
        '8015.T', '8035.T', '8053.T', '8267.T', '9501.T', '9502.T',
        '9983.T', '9984.T'
    ]

    start_date = '2024-12-01'
    end_date = '2025-12-02'

    print(f"\n期間: {start_date} ～ {end_date}")
    print(f"銘柄数: {len(symbols)}")

    # 全営業日を取得（いずれかの銘柄にデータがある日）
    cur.execute("""
        SELECT DISTINCT DATE(timestamp) as trade_date
        FROM intraday_data
        WHERE timestamp >= %s AND timestamp <= %s
        ORDER BY trade_date
    """, (start_date, end_date))

    trading_days = [row[0] for row in cur.fetchall()]
    print(f"データ有り日数: {len(trading_days)}日")

    # 日次データ件数を取得
    print("\n日次データ件数を取得中...")

    daily_data = []

    for trade_date in trading_days:
        next_day = trade_date + timedelta(days=1)

        for symbol in symbols:
            cur.execute("""
                SELECT COUNT(*) as count
                FROM intraday_data
                WHERE symbol = %s
                AND timestamp >= %s AND timestamp < %s
            """, (symbol, trade_date, next_day))

            count = cur.fetchone()[0]

            daily_data.append({
                'date': trade_date,
                'symbol': symbol,
                'count': count
            })

    df = pd.DataFrame(daily_data)

    # 統計情報
    print("\n" + "=" * 80)
    print("日次データ統計")
    print("=" * 80)

    # 日別の集計
    daily_summary = df.groupby('date').agg({
        'count': ['sum', 'mean', 'min', 'max']
    }).reset_index()
    daily_summary.columns = ['date', 'total', 'avg', 'min', 'max']

    # データがある銘柄数
    symbols_per_day = df[df['count'] > 0].groupby('date').size().reset_index(name='symbols_count')
    daily_summary = daily_summary.merge(symbols_per_day, on='date', how='left')

    print(f"\n全期間統計:")
    print(f"  平均データ数/日: {daily_summary['total'].mean():,.0f}件")
    print(f"  最小データ数/日: {daily_summary['total'].min():,.0f}件 ({daily_summary[daily_summary['total'] == daily_summary['total'].min()]['date'].values[0]})")
    print(f"  最大データ数/日: {daily_summary['total'].max():,.0f}件 ({daily_summary[daily_summary['total'] == daily_summary['total'].max()]['date'].values[0]})")

    # 異常日の検出（平均の50%未満）
    threshold = daily_summary['total'].mean() * 0.5
    abnormal_days = daily_summary[daily_summary['total'] < threshold]

    if len(abnormal_days) > 0:
        print("\n" + "=" * 80)
        print(f"⚠️ データ数が異常に少ない日（平均の50%未満: {threshold:,.0f}件未満）")
        print("=" * 80)

        for _, row in abnormal_days.iterrows():
            print(f"\n{row['date']}:")
            print(f"  総データ数: {row['total']:,.0f}件（平均の{row['total']/daily_summary['total'].mean()*100:.0f}%）")
            print(f"  データ有り銘柄数: {row['symbols_count']:.0f} / {len(symbols)}")

            # この日のデータが0の銘柄を表示
            zero_data_symbols = df[(df['date'] == row['date']) & (df['count'] == 0)]['symbol'].tolist()
            if len(zero_data_symbols) > 0:
                print(f"  データなし銘柄: {', '.join(zero_data_symbols)}")

    # 銘柄別の欠損日チェック
    print("\n" + "=" * 80)
    print("銘柄別データ欠損状況")
    print("=" * 80)

    for symbol in symbols:
        symbol_df = df[df['symbol'] == symbol]

        # データがある日数
        days_with_data = len(symbol_df[symbol_df['count'] > 0])
        missing_days = len(trading_days) - days_with_data

        if missing_days > 0:
            missing_ratio = missing_days / len(trading_days) * 100

            print(f"\n{symbol}:")
            print(f"  データ有り日数: {days_with_data} / {len(trading_days)}日")
            print(f"  欠損日数: {missing_days}日 ({missing_ratio:.1f}%)")

            # 欠損日の詳細（最初の10日のみ）
            missing_dates = symbol_df[symbol_df['count'] == 0]['date'].tolist()
            if len(missing_dates) > 0:
                print(f"  欠損日（最初の10日）: {', '.join([str(d) for d in missing_dates[:10]])}")

            # データ件数の統計
            non_zero = symbol_df[symbol_df['count'] > 0]['count']
            if len(non_zero) > 0:
                print(f"  平均データ数/日: {non_zero.mean():.1f}件")
                print(f"  最小データ数/日: {non_zero.min()}件")
                print(f"  最大データ数/日: {non_zero.max()}件")

    # 前半期間（2024-12～2025-03）の詳細チェック
    print("\n" + "=" * 80)
    print("前半期間（2024-12～2025-03）の詳細チェック")
    print("=" * 80)

    first_half_end = pd.to_datetime('2025-03-31').date()
    first_half = daily_summary[daily_summary['date'] <= first_half_end]

    print(f"\n前半期間の統計:")
    print(f"  平均データ数/日: {first_half['total'].mean():,.0f}件")
    print(f"  平均データ有り銘柄数/日: {first_half['symbols_count'].mean():.1f} / {len(symbols)}")

    # 前半期間でデータが全くない銘柄
    first_half_dates = [d for d in trading_days if d <= first_half_end]

    for symbol in symbols:
        symbol_first_half = df[(df['symbol'] == symbol) & (df['date'] <= first_half_end)]
        days_with_data = len(symbol_first_half[symbol_first_half['count'] > 0])

        if days_with_data == 0:
            print(f"\n⚠️ {symbol}: 前半期間にデータが全くありません")
        elif days_with_data < len(first_half_dates) * 0.5:
            print(f"\n⚠️ {symbol}: 前半期間のデータが少なすぎます")
            print(f"   データ有り: {days_with_data} / {len(first_half_dates)}日 ({days_with_data/len(first_half_dates)*100:.1f}%)")

    # データベース接続を閉じる
    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("チェック完了")
    print("=" * 80)

    return df, daily_summary


if __name__ == "__main__":
    check_daily_data_quality()
