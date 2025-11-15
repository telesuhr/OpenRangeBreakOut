#!/usr/bin/env python3
"""
トレードのエントリー・イグジットを可視化
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, time
import pytz

from src.data.refinitiv_client import RefinitivClient

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 80)
print("トレード可視化")
print("=" * 80)
print()

# タイムゾーン設定
jst = pytz.timezone('Asia/Tokyo')
utc = pytz.UTC

# 最新の結果を読み込み
trades_df = pd.read_csv('results/optimization/latest_day_20251112.csv')
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time']).dt.tz_localize(utc)
trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time']).dt.tz_localize(utc)

print(f"トレード数: {len(trades_df)}")
print()

# Refinitiv クライアント初期化
app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
client = RefinitivClient(app_key=app_key, use_cache=True)

# セッション開始
try:
    client.connect()
    print("Refinitiv API接続成功")
except Exception as e:
    print(f"Refinitiv API接続エラー: {e}")
    print("キャッシュデータで試行します")

# 分析対象日
target_date = trades_df['entry_time'].iloc[0].date()
print(f"分析日: {target_date}")
print()

# 各銘柄のチャートを作成
num_stocks = len(trades_df)
fig, axes = plt.subplots(num_stocks, 1, figsize=(16, 5 * num_stocks))

if num_stocks == 1:
    axes = [axes]

for idx, (_, trade) in enumerate(trades_df.iterrows()):
    ax = axes[idx]

    stock_name = trade['stock_name']
    ric_code = trade['symbol']

    print(f"[{idx+1}/{num_stocks}] {stock_name} ({ric_code})")

    # 1分足データ取得（09:00-15:30）
    start_time = datetime.combine(target_date, time(9, 0)).replace(tzinfo=jst).astimezone(utc)
    end_time = datetime.combine(target_date, time(15, 30)).replace(tzinfo=jst).astimezone(utc)

    tick_data = client.get_intraday_data(
        symbol=ric_code,
        start_date=start_time,
        end_date=end_time,
        interval='1min'
    )

    if tick_data is None or len(tick_data) == 0:
        print(f"  データ取得失敗")
        ax.text(0.5, 0.5, f'{stock_name}\nデータなし',
                ha='center', va='center', fontsize=16)
        continue

    # indexからタイムスタンプを取得してJSTに変換
    # まずUTCとしてローカライズしてから、JSTに変換
    tick_data['timestamp_jst'] = tick_data.index.tz_localize(utc).tz_convert(jst)

    # ローソク足風の描画（簡易版）
    ax.plot(tick_data['timestamp_jst'], tick_data['close'],
            color='black', linewidth=1, label='価格')

    # レンジ（09:05-09:15）をハイライト
    range_start = datetime.combine(target_date, time(9, 5)).replace(tzinfo=jst)
    range_end = datetime.combine(target_date, time(9, 15)).replace(tzinfo=jst)

    range_data = tick_data[
        (tick_data['timestamp_jst'] >= range_start) &
        (tick_data['timestamp_jst'] <= range_end)
    ]

    if len(range_data) > 0:
        range_high = range_data['high'].max()
        range_low = range_data['low'].min()

        # NAチェック
        if pd.notna(range_high) and pd.notna(range_low):
            # レンジの高値・安値をライン表示
            ax.axhline(y=range_high, color='blue', linestyle='--',
                       linewidth=1.5, alpha=0.7, label=f'レンジ高値 ({range_high:.0f}円)')
            ax.axhline(y=range_low, color='purple', linestyle='--',
                       linewidth=1.5, alpha=0.7, label=f'レンジ安値 ({range_low:.0f}円)')

            # レンジ期間を塗りつぶし
            ax.axvspan(range_start, range_end, alpha=0.1, color='gray', label='レンジ期間')

    # エントリーウィンドウ（09:15-10:00）
    entry_window_start = datetime.combine(target_date, time(9, 15)).replace(tzinfo=jst)
    entry_window_end = datetime.combine(target_date, time(10, 0)).replace(tzinfo=jst)
    ax.axvspan(entry_window_start, entry_window_end, alpha=0.05, color='green',
               label='エントリーウィンドウ')

    # エントリーポイント
    entry_time_jst = trade['entry_time'].tz_convert(jst)
    entry_price = trade['entry_price']

    marker_color = 'green' if trade['side'] == 'long' else 'red'
    marker_symbol = '^' if trade['side'] == 'long' else 'v'
    side_ja = 'ロング' if trade['side'] == 'long' else 'ショート'

    ax.scatter(entry_time_jst, entry_price,
              color=marker_color, marker=marker_symbol, s=200, zorder=5,
              edgecolors='black', linewidths=1.5,
              label=f'エントリー ({side_ja})')

    # エントリー価格をテキスト表示
    ax.text(entry_time_jst, entry_price,
           f'  {entry_price:.0f}円\n  {entry_time_jst.strftime("%H:%M")}',
           fontsize=9, va='bottom' if trade['side'] == 'long' else 'top')

    # イグジットポイント
    exit_time_jst = trade['exit_time'].tz_convert(jst)
    exit_price = trade['exit_price']

    exit_color = 'darkgreen' if trade['pnl'] > 0 else 'darkred'

    ax.scatter(exit_time_jst, exit_price,
              color=exit_color, marker='x', s=200, zorder=5,
              linewidths=3,
              label=f'イグジット ({trade["reason"]})')

    # イグジット価格をテキスト表示
    ax.text(exit_time_jst, exit_price,
           f'  {exit_price:.0f}円\n  {exit_time_jst.strftime("%H:%M")}',
           fontsize=9, va='bottom' if trade['pnl'] > 0 else 'top')

    # エントリーとイグジットを線で結ぶ
    ax.plot([entry_time_jst, exit_time_jst], [entry_price, exit_price],
           color=exit_color, linestyle=':', linewidth=2, alpha=0.6)

    # 損益情報をタイトルに
    pnl_text = f"+{trade['pnl']:,.0f}円" if trade['pnl'] >= 0 else f"{trade['pnl']:,.0f}円"
    return_text = f"+{trade['return']*100:.2f}%" if trade['return'] >= 0 else f"{trade['return']*100:.2f}%"

    ax.set_title(f'{stock_name} ({ric_code}) | {side_ja} | {pnl_text} ({return_text})',
                fontsize=14, fontweight='bold')

    # X軸フォーマット
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=jst))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Y軸ラベル
    ax.set_ylabel('価格（円）', fontsize=11)
    ax.set_xlabel('時刻（JST）', fontsize=11)

    # グリッド
    ax.grid(True, alpha=0.3, linestyle='--')

    # 凡例
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)

    print(f"  エントリー: {entry_time_jst.strftime('%H:%M')} @ {entry_price:.0f}円")
    print(f"  イグジット: {exit_time_jst.strftime('%H:%M')} @ {exit_price:.0f}円")
    print(f"  損益: {pnl_text} ({return_text})")
    print()

plt.tight_layout()

# 保存
output_file = 'results/optimization/trades_visualization_20251112.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"チャートを {output_file} に保存しました")

plt.close()
print()
print("=" * 80)
print("完了")
print("=" * 80)
