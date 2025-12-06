#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースのデータカバレッジ確認スクリプト

バックテスト期間（2024-12-01 ～ 2025-12-02）のデータが
データベースに正しく存在するかを確認する
"""

import sys
from pathlib import Path
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_database_coverage():
    """データベースのデータカバレッジを確認"""

    print("=" * 80)
    print("データベースデータカバレッジ確認")
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

    # 期間設定
    start_date = '2024-12-01'
    end_date = '2025-12-02'

    print(f"\nバックテスト期間: {start_date} ～ {end_date}")
    print(f"対象銘柄数: {len(symbols)}")

    # 月別のデータ集計
    print("\n" + "=" * 80)
    print("月別データレコード数")
    print("=" * 80)

    months = pd.date_range(start=start_date, end=end_date, freq='MS')

    monthly_stats = []

    for i, month_start in enumerate(months):
        # 月末を計算
        if i < len(months) - 1:
            month_end = months[i + 1] - timedelta(days=1)
        else:
            month_end = pd.to_datetime(end_date)

        month_str = month_start.strftime('%Y-%m')

        total_records = 0
        symbols_with_data = 0

        for symbol in symbols:
            cur.execute("""
                SELECT COUNT(*) FROM intraday_data
                WHERE symbol = %s
                AND timestamp >= %s AND timestamp < %s
            """, (symbol, month_start, month_end + timedelta(days=1)))

            count = cur.fetchone()[0]
            total_records += count

            if count > 0:
                symbols_with_data += 1

        monthly_stats.append({
            'month': month_str,
            'total_records': total_records,
            'symbols_with_data': symbols_with_data,
            'avg_records_per_symbol': total_records / len(symbols) if len(symbols) > 0 else 0
        })

        print(f"\n{month_str}:")
        print(f"  総レコード数: {total_records:,}")
        print(f"  データ有り銘柄数: {symbols_with_data} / {len(symbols)}")
        print(f"  銘柄あたり平均レコード数: {total_records / len(symbols):.0f}")

    # 統計サマリー
    monthly_df = pd.DataFrame(monthly_stats)

    print("\n" + "=" * 80)
    print("データ品質サマリー")
    print("=" * 80)

    print(f"\n総レコード数: {monthly_df['total_records'].sum():,}")
    print(f"月平均レコード数: {monthly_df['total_records'].mean():,.0f}")
    print(f"最少月: {monthly_df.loc[monthly_df['total_records'].idxmin(), 'month']} ({monthly_df['total_records'].min():,}件)")
    print(f"最多月: {monthly_df.loc[monthly_df['total_records'].idxmax(), 'month']} ({monthly_df['total_records'].max():,}件)")

    # 月別レコード数が極端に少ない月を特定
    mean_records = monthly_df['total_records'].mean()
    std_records = monthly_df['total_records'].std()
    threshold = mean_records - 2 * std_records  # 平均 - 2標準偏差

    low_data_months = monthly_df[monthly_df['total_records'] < threshold]

    if len(low_data_months) > 0:
        print("\n" + "=" * 80)
        print("⚠️ データ不足の可能性がある月")
        print("=" * 80)

        for _, row in low_data_months.iterrows():
            print(f"\n{row['month']}:")
            print(f"  レコード数: {row['total_records']:,} (平均の{row['total_records']/mean_records*100:.1f}%)")
            print(f"  データ有り銘柄数: {row['symbols_with_data']:.0f} / {len(symbols)}")

    # 銘柄別のデータカバレッジ
    print("\n" + "=" * 80)
    print("銘柄別データカバレッジ（期間全体）")
    print("=" * 80)

    symbol_coverage = []

    for symbol in symbols:
        cur.execute("""
            SELECT COUNT(*),
                   MIN(timestamp) as first_date,
                   MAX(timestamp) as last_date
            FROM intraday_data
            WHERE symbol = %s
            AND timestamp >= %s AND timestamp <= %s
        """, (symbol, start_date, end_date))

        count, first_date, last_date = cur.fetchone()

        # 日数を計算
        if first_date and last_date:
            days = (last_date - first_date).days + 1
        else:
            days = 0

        symbol_coverage.append({
            'symbol': symbol,
            'total_records': count,
            'first_date': first_date,
            'last_date': last_date,
            'days_covered': days
        })

    coverage_df = pd.DataFrame(symbol_coverage).sort_values('total_records', ascending=True)

    print("\n最少データ銘柄 TOP5:")
    for idx, row in coverage_df.head(5).iterrows():
        print(f"\n{row['symbol']}:")
        print(f"  レコード数: {row['total_records']:,}")
        print(f"  開始日: {row['first_date']}")
        print(f"  終了日: {row['last_date']}")
        print(f"  カバー日数: {row['days_covered']}日")

    # 特定銘柄の詳細チェック（最もレコード数が少ない銘柄）
    worst_symbol = coverage_df.iloc[0]['symbol']

    print("\n" + "=" * 80)
    print(f"最少データ銘柄の詳細: {worst_symbol}")
    print("=" * 80)

    cur.execute("""
        SELECT DATE(timestamp) as date, COUNT(*) as bars
        FROM intraday_data
        WHERE symbol = %s
        AND timestamp >= %s AND timestamp <= %s
        GROUP BY DATE(timestamp)
        ORDER BY date
    """, (worst_symbol, start_date, end_date))

    daily_counts = cur.fetchall()

    if len(daily_counts) > 0:
        daily_df = pd.DataFrame(daily_counts, columns=['date', 'bars'])
        print(f"\n日次レコード数の統計:")
        print(f"  平均: {daily_df['bars'].mean():.1f}本/日")
        print(f"  最小: {daily_df['bars'].min()}本/日")
        print(f"  最大: {daily_df['bars'].max()}本/日")
        print(f"  データ有り日数: {len(daily_df)}日")
    else:
        print(f"\n⚠️ {worst_symbol} にはデータがありません")

    # データベース接続を閉じる
    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("確認完了")
    print("=" * 80)

    return monthly_df, coverage_df


if __name__ == "__main__":
    check_database_coverage()
