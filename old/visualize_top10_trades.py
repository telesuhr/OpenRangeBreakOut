#!/usr/bin/env python3
"""
トップ10銘柄のトレード可視化
エントリー・イグジットタイミングとレンジを表示
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pytz
from datetime import datetime, timedelta
from src.data.refinitiv_client import RefinitivClient
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

# タイムゾーン設定
jst = pytz.timezone('Asia/Tokyo')
utc = pytz.UTC

def visualize_trade(client, trade, ax):
    """1つのトレードを可視化"""

    ric_code = trade['symbol']
    stock_name = trade['stock_name']

    # 時刻をUTCに変換
    entry_time_utc = pd.to_datetime(trade['entry_time'])
    if entry_time_utc.tzinfo is None:
        entry_time_utc = utc.localize(entry_time_utc)

    exit_time_utc = pd.to_datetime(trade['exit_time'])
    if exit_time_utc.tzinfo is None:
        exit_time_utc = utc.localize(exit_time_utc)

    # 当日の始値から終値までのデータを取得
    start_time = entry_time_utc.replace(hour=0, minute=0, second=0)
    end_time = exit_time_utc.replace(hour=8, minute=0, second=0)  # UTCで08:00 = JSTで17:00

    try:
        tick_data = client.get_intraday_data(
            symbol=ric_code,
            start_date=start_time,
            end_date=end_time,
            interval='1min'
        )
    except Exception as e:
        print(f"  データ取得エラー ({stock_name}): {e}")
        ax.text(0.5, 0.5, f'データ取得エラー\n{stock_name}',
                ha='center', va='center', fontsize=12)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return

    if tick_data is None or tick_data.empty:
        print(f"  データなし ({stock_name})")
        ax.text(0.5, 0.5, f'データなし\n{stock_name}',
                ha='center', va='center', fontsize=12)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return

    # タイムゾーン変換
    tick_data['timestamp_jst'] = tick_data.index.tz_localize(utc).tz_convert(jst)

    # プロット
    ax.plot(tick_data['timestamp_jst'], tick_data['close'],
            label='価格', linewidth=1.5, color='black', alpha=0.7)

    # レンジ期間をハイライト
    range_start_utc = pd.to_datetime(trade['range_start'])
    if range_start_utc.tzinfo is None:
        range_start_utc = utc.localize(range_start_utc)

    range_end_utc = pd.to_datetime(trade['range_end'])
    if range_end_utc.tzinfo is None:
        range_end_utc = utc.localize(range_end_utc)

    range_start_jst = range_start_utc.astimezone(jst)
    range_end_jst = range_end_utc.astimezone(jst)

    ax.axvspan(range_start_jst, range_end_jst, alpha=0.2, color='gray', label='レンジ期間')

    # レンジ高値・安値
    range_high = trade['range_high']
    range_low = trade['range_low']

    if pd.notna(range_high) and pd.notna(range_low):
        ax.axhline(y=range_high, color='blue', linestyle='--', alpha=0.5, label='レンジ高値')
        ax.axhline(y=range_low, color='blue', linestyle='--', alpha=0.5, label='レンジ安値')

    # エントリーポイント
    entry_time_jst = entry_time_utc.astimezone(jst)
    entry_price = trade['entry_price']
    ax.scatter([entry_time_jst], [entry_price],
               color='green', s=150, marker='^', zorder=5, label='エントリー')

    # イグジットポイント（色は損益で変える）
    exit_time_jst = exit_time_utc.astimezone(jst)
    exit_price = trade['exit_price']
    pnl = trade['pnl']

    exit_color = 'red' if pnl < 0 else 'lime'
    ax.scatter([exit_time_jst], [exit_price],
               color=exit_color, s=150, marker='v', zorder=5, label='イグジット')

    # タイトル
    pnl_pct = trade['return'] * 100
    title = f"{stock_name} ({ric_code})\n"
    title += f"エントリー: {entry_time_jst.strftime('%H:%M')} @ ¥{entry_price:,.0f}\n"
    title += f"イグジット: {exit_time_jst.strftime('%H:%M')} @ ¥{exit_price:,.0f}\n"
    title += f"損益: {pnl:+,.0f}円 ({pnl_pct:+.2f}%)"

    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_xlabel('時刻 (JST)', fontsize=9)
    ax.set_ylabel('価格 (円)', fontsize=9)
    ax.legend(loc='best', fontsize=7)
    ax.grid(True, alpha=0.3)

    # X軸フォーマット
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=jst))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)

def main():
    print("=" * 80)
    print("トップ10銘柄 トレード可視化")
    print("=" * 80)

    # トレードデータを読み込み
    trades_csv = 'results/optimization/top10_trades_20251113.csv'
    trades_df = pd.read_csv(trades_csv)

    print(f"\n総トレード数: {len(trades_df)}")
    print(f"\n可視化を開始...")

    # APIクライアント初期化
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 5行×2列のグリッド（10銘柄）
    fig, axes = plt.subplots(5, 2, figsize=(20, 25))
    axes = axes.flatten()

    for idx, (_, trade) in enumerate(trades_df.iterrows()):
        print(f"  [{idx+1}/{len(trades_df)}] {trade['stock_name']} を処理中...")
        visualize_trade(client, trade, axes[idx])

    client.disconnect()

    plt.tight_layout()

    # 保存
    output_path = 'results/optimization/top10_visualization_20251113.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')

    print(f"\n\n可視化を {output_path} に保存しました")
    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
