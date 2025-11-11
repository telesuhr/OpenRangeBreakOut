#!/usr/bin/env python3
"""
最優秀5銘柄の追加ヒストリカルデータ取得スクリプト
期間: 2025-02-01 〜 2025-07-31 (6ヶ月)
"""

import sys
import os
from datetime import datetime, timedelta
from src.data.refinitiv_client import RefinitivClient
import time

# Best 5 stocks
BEST_STOCKS = [
    ('6762.T', 'TDK'),
    ('9984.T', 'ソフトバンクG'),
    ('6857.T', 'アドバンテスト'),
    ('6752.T', 'パナソニック'),
    ('6758.T', 'ソニーグループ'),
]

def main():
    print("=" * 80)
    print("最優秀5銘柄の追加ヒストリカルデータ取得")
    print("=" * 80)
    print()

    # 追加取得期間
    start_date = datetime(2025, 2, 1)
    end_date = datetime(2025, 7, 31)

    print(f"取得期間: {start_date.strftime('%Y-%m-%d')} 〜 {end_date.strftime('%Y-%m-%d')}")
    print(f"銘柄数: {len(BEST_STOCKS)}")
    print()

    # Refinitiv client initialization
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    total_stocks = len(BEST_STOCKS)

    for idx, (symbol, name) in enumerate(BEST_STOCKS, 1):
        print(f"\n[{idx}/{total_stocks}] {name} ({symbol})")
        print("-" * 60)

        try:
            # Check existing data
            existing_data = client.get_intraday_data(
                symbol,
                start_date,
                end_date,
                interval='1min'
            )

            if existing_data is not None and len(existing_data) > 0:
                print(f"  ✓ キャッシュ済みデータ: {len(existing_data):,} 行")
                print(f"  ✓ 期間: {existing_data['timestamp'].min()} 〜 {existing_data['timestamp'].max()}")
            else:
                print(f"  ⚠ データなし - API取得を試行中...")

                # Fetch from API (RefinitivClient will handle caching automatically)
                # Split into monthly chunks to avoid timeout
                current_date = start_date
                total_rows = 0

                while current_date < end_date:
                    # Calculate end of current month
                    month_end = datetime(current_date.year, current_date.month, 28) + timedelta(days=4)
                    month_end = datetime(month_end.year, month_end.month, 1) - timedelta(days=1)
                    month_end = min(month_end, end_date)

                    print(f"    月別取得: {current_date.strftime('%Y-%m-%d')} 〜 {month_end.strftime('%Y-%m-%d')}")

                    month_data = client.get_intraday_data(
                        symbol,
                        current_date,
                        month_end,
                        interval='1min'
                    )

                    if month_data is not None:
                        rows = len(month_data)
                        total_rows += rows
                        print(f"      取得: {rows:,} 行")
                    else:
                        print(f"      ⚠ データ取得失敗")

                    # Move to next month
                    current_date = month_end + timedelta(days=1)

                    # Rate limiting
                    time.sleep(1)

                print(f"  ✓ 合計取得: {total_rows:,} 行")

        except Exception as e:
            print(f"  ✗ エラー: {e}")
            import traceback
            traceback.print_exc()

        # Rate limiting between stocks
        if idx < total_stocks:
            time.sleep(2)

    print()
    print("=" * 80)
    print("データ取得完了")
    print("=" * 80)

if __name__ == "__main__":
    main()
