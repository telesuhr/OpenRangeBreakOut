#!/usr/bin/env python3
"""
本日（2025/11/14）のデータ取得テスト
"""

from datetime import datetime
from src.data.refinitiv_client import RefinitivClient

def test_today_data():
    print("=" * 80)
    print("2025/11/14 データ取得テスト")
    print("=" * 80)

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=False)  # キャッシュ無効

    try:
        client.connect()

        # テスト銘柄
        test_symbols = [
            ('6762.T', 'TDK'),
            ('9984.T', 'ソフトバンクG'),
            ('5706.T', '三井金属鉱業'),
        ]

        today = datetime(2025, 11, 14)

        print(f"\n取得対象日: {today.date()}")
        print("-" * 80)

        for symbol, name in test_symbols:
            print(f"\n【{name} ({symbol})】")

            try:
                data = client.get_intraday_data(
                    symbol=symbol,
                    start_date=today,
                    end_date=today,
                    interval='1min'
                )

                if data is not None and not data.empty:
                    print(f"  ✅ データ取得成功")
                    print(f"  データ件数: {len(data)}件")
                    print(f"  時間範囲: {data.index[0]} ～ {data.index[-1]}")
                    print(f"  最初の5件:")
                    print(data.head().to_string())
                else:
                    print(f"  ❌ データなし（まだ取得できない可能性）")

            except Exception as e:
                print(f"  ❌ エラー: {e}")

        client.disconnect()

        print("\n" + "=" * 80)
        print("テスト完了")
        print("=" * 80)

    except Exception as e:
        print(f"接続エラー: {e}")

if __name__ == "__main__":
    test_today_data()
