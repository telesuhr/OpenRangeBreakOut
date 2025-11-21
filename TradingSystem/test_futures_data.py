"""
日経先物およびその代替データの取得テスト
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.data.refinitiv_client import RefinitivClient

# 設定読み込み
with open('config/strategy_config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# クライアント初期化
client = RefinitivClient(
    app_key=config['data']['refinitiv']['app_key'],
    use_cache=False,  # キャッシュを使わずに直接API確認
    db_config=config.get('database')
)
client.connect()

# テスト対象のシンボルリスト
test_symbols = [
    ("NKDc1", "SGX日経225先物 (Generic 1st)"),
    ("NKDc2", "SGX日経225先物 (Generic 2nd)"),
    (".SPX", "S&P500指数"),
    (".N225", "日経平均株価指数"),
    (".DJI", "ダウ・ジョーンズ工業株価平均"),
    ("JPY=", "USD/JPY為替レート"),
    ("NI225", "日経225先物 (大阪取引所)"),
    ("JNIc1", "日経225先物 (Generic)"),
]

# テスト期間（直近2日間）
end_date = datetime.now()
start_date = end_date - timedelta(days=2)

print("=" * 80)
print("日経先物・代替データ取得テスト")
print("=" * 80)
print(f"テスト期間: {start_date.date()} ～ {end_date.date()}\n")

results = {}

for symbol, description in test_symbols:
    print(f"\n【{symbol}】 - {description}")
    print("-" * 80)

    # 分足データ取得テスト
    try:
        print("  分足データ取得中...")
        intraday_data = client.get_intraday_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="1min"
        )

        if intraday_data is not None and not intraday_data.empty:
            print(f"  ✓ 分足データ取得成功: {len(intraday_data)}行")
            print(f"    期間: {intraday_data.index[0]} ～ {intraday_data.index[-1]}")
            print(f"    サンプル価格: {intraday_data['close'].iloc[0]:.2f}")
            results[symbol] = {"intraday": "OK", "rows": len(intraday_data)}
        else:
            print(f"  ✗ 分足データ取得失敗: データなし")
            results[symbol] = {"intraday": "NG"}
    except Exception as e:
        print(f"  ✗ 分足データ取得エラー: {str(e)[:100]}")
        results[symbol] = {"intraday": "ERROR", "error": str(e)[:100]}

    # 日足データ取得テスト
    try:
        print("  日足データ取得中...")
        daily_data = client.get_daily_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        if daily_data is not None and not daily_data.empty:
            print(f"  ✓ 日足データ取得成功: {len(daily_data)}行")
            print(f"    サンプル価格: {daily_data['close'].iloc[0]:.2f}")
            results[symbol]["daily"] = "OK"
        else:
            print(f"  ✗ 日足データ取得失敗: データなし")
            results[symbol]["daily"] = "NG"
    except Exception as e:
        print(f"  ✗ 日足データ取得エラー: {str(e)[:100]}")
        results[symbol]["daily"] = "ERROR"

# サマリー
print("\n" + "=" * 80)
print("テスト結果サマリー")
print("=" * 80)
print(f"{'シンボル':<15} {'分足':<10} {'日足':<10} {'説明'}")
print("-" * 80)

for symbol, description in test_symbols:
    if symbol in results:
        intraday_status = results[symbol].get("intraday", "N/A")
        daily_status = results[symbol].get("daily", "N/A")
        print(f"{symbol:<15} {intraday_status:<10} {daily_status:<10} {description}")

# 推奨シンボル
print("\n" + "=" * 80)
print("推奨設定")
print("=" * 80)

successful_symbols = [
    symbol for symbol, desc in test_symbols
    if results.get(symbol, {}).get("daily") == "OK"
]

if successful_symbols:
    print(f"\n✓ 以下のシンボルが利用可能です:")
    for symbol in successful_symbols:
        desc = dict(test_symbols)[symbol]
        print(f"  - {symbol}: {desc}")

    print(f"\n推奨設定 (strategy_config.yaml):")
    print(f"  nikkei_futures_filter:")
    print(f"    symbol: \"{successful_symbols[0]}\"")
    if len(successful_symbols) > 1:
        print(f"    fallback_symbol: \"{successful_symbols[1]}\"")
else:
    print("\n✗ 利用可能なシンボルが見つかりませんでした")
    print("  契約内容を確認するか、フィルターを無効化してください:")
    print("  nikkei_futures_filter:")
    print("    enabled: false")

client.disconnect()
print("\n" + "=" * 80)
print("テスト完了")
print("=" * 80)
