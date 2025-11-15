#!/usr/bin/env python3
"""
TDKの直近1ヶ月のトレードを詳細可視化
実際のエントリー・イグジットタイミングとP/Lを確認
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time, timedelta
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False

def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)

# バックテスト期間（直近1ヶ月）
END_DATE = datetime(2025, 11, 12)
START_DATE = datetime(2025, 10, 12)

# 最適化済みパラメータ
OPTIMIZED_PARAMS = {
    'initial_capital': 10000000,
    'commission_rate': 0.001,
    'range_start': jst_to_utc_time('09:05'),
    'range_end': jst_to_utc_time('09:15'),
    'entry_start': jst_to_utc_time('09:15'),
    'entry_end': jst_to_utc_time('11:00'),
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,   # 4.0%
    'stop_loss': 0.0075,     # 0.75%
}

def main():
    print("=" * 80)
    print("TDK 直近1ヶ月トレード詳細可視化")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()}")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # TDKのバックテスト実行
    symbol = '6762.T'
    name = 'TDK'

    print(f"\n{name} ({symbol}) のバックテスト実行中...")

    engine = BacktestEngine(**OPTIMIZED_PARAMS)
    results = engine.run_backtest(
        client=client,
        symbols=[symbol],
        start_date=START_DATE,
        end_date=END_DATE
    )

    if 'trades' not in results or results['trades'] is None or results['trades'].empty:
        print("トレードデータが取得できませんでした")
        client.disconnect()
        return

    trades = results['trades']
    print(f"\n総トレード数: {len(trades)}")
    print(f"総損益: {trades['pnl'].sum():+,.0f}円")

    # 日次データを取得
    print("\n1分足データ取得中...")
    intraday_data = client.get_intraday_data(
        symbol=symbol,
        start_date=START_DATE,
        end_date=END_DATE,
        interval='1min'
    )

    client.disconnect()

    if intraday_data is None or intraday_data.empty:
        print("1分足データが取得できませんでした")
        return

    print(f"データ件数: {len(intraday_data)}")

    # トレード日付を抽出
    trades['entry_date'] = pd.to_datetime(trades['entry_time']).dt.date
    trade_dates = sorted(trades['entry_date'].unique())

    print(f"\nトレード発生日数: {len(trade_dates)}")

    # 日次トレード詳細をプリント
    print("\n" + "=" * 80)
    print("日次トレード詳細")
    print("=" * 80)

    for date in trade_dates:
        day_trades = trades[trades['entry_date'] == date]
        day_pnl = day_trades['pnl'].sum()
        print(f"\n【{date}】 {len(day_trades)}トレード, 損益: {day_pnl:+,.0f}円")

        for idx, trade in day_trades.iterrows():
            entry_time = pd.to_datetime(trade['entry_time'])
            exit_time = pd.to_datetime(trade['exit_time'])
            pnl = trade['pnl']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']

            # イグジット理由を推測
            price_change_pct = (exit_price / entry_price - 1) * 100
            if price_change_pct >= 4.0:
                exit_reason = '利確'
            elif price_change_pct <= -0.75:
                exit_reason = '損切'
            else:
                exit_reason = '強制決済'

            print(f"  エントリー: {entry_time.strftime('%H:%M:%S')} @ {entry_price:,.0f}円")
            print(f"  イグジット: {exit_time.strftime('%H:%M:%S')} @ {exit_price:,.0f}円 ({exit_reason})")
            print(f"  損益: {pnl:+,.0f}円 ({price_change_pct:+.2f}%)")

    # 可視化（最初の10営業日を詳細表示）
    num_days_to_plot = min(10, len(trade_dates))

    fig = plt.figure(figsize=(20, 4 * num_days_to_plot))

    for i, date in enumerate(trade_dates[:num_days_to_plot]):
        ax = plt.subplot(num_days_to_plot, 1, i + 1)

        # その日のデータ
        day_data = intraday_data[intraday_data.index.date == date]

        if day_data.empty:
            continue

        # その日のトレード
        day_trades = trades[trades['entry_date'] == date]

        # 時刻をX軸用に変換（その日の開始からの分数）
        day_start = day_data.index[0]
        x_minutes = [(t - day_start).total_seconds() / 60 for t in day_data.index]

        # ローソク足プロット（簡易版：closeのみをラインプロット）
        ax.plot(x_minutes, day_data['close'], linewidth=1, color='steelblue', label='株価')

        # オープンレンジ期間をハイライト（09:05-09:15）
        range_start_time = pd.Timestamp.combine(date, time(0, 5))  # UTC 00:05 = JST 09:05
        range_end_time = pd.Timestamp.combine(date, time(0, 15))   # UTC 00:15 = JST 09:15

        range_data = day_data[(day_data.index >= range_start_time) & (day_data.index <= range_end_time)]
        if not range_data.empty:
            range_high = range_data['high'].max()
            range_low = range_data['low'].min()

            range_start_min = (range_start_time - day_start).total_seconds() / 60
            range_end_min = (range_end_time - day_start).total_seconds() / 60

            ax.axhspan(range_low, range_high, xmin=range_start_min/(x_minutes[-1]+1),
                      xmax=range_end_min/(x_minutes[-1]+1), alpha=0.2, color='yellow', label='オープンレンジ')
            ax.axhline(y=range_high, color='green', linestyle='--', linewidth=1, alpha=0.5, label=f'レンジ上限: {range_high:,.0f}')
            ax.axhline(y=range_low, color='red', linestyle='--', linewidth=1, alpha=0.5, label=f'レンジ下限: {range_low:,.0f}')

        # エントリー・イグジットポイントをプロット
        for idx, trade in day_trades.iterrows():
            entry_time = pd.to_datetime(trade['entry_time'])
            exit_time = pd.to_datetime(trade['exit_time'])
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            pnl = trade['pnl']

            # イグジット理由を推測
            price_change_pct = (exit_price / entry_price - 1) * 100
            if price_change_pct >= 4.0:
                exit_reason = 'profit_target'
            elif price_change_pct <= -0.75:
                exit_reason = 'stop_loss'
            else:
                exit_reason = 'force_exit'

            entry_min = (entry_time - day_start).total_seconds() / 60
            exit_min = (exit_time - day_start).total_seconds() / 60

            # エントリーポイント
            ax.scatter(entry_min, entry_price, color='blue', s=150, marker='^',
                      edgecolors='black', linewidths=2, zorder=5, label='エントリー' if idx == day_trades.index[0] else '')

            # イグジットポイント
            exit_color = 'green' if pnl > 0 else 'red'
            exit_marker = 'o' if exit_reason == 'profit_target' else ('x' if exit_reason == 'stop_loss' else 's')
            ax.scatter(exit_min, exit_price, color=exit_color, s=150, marker=exit_marker,
                      edgecolors='black', linewidths=2, zorder=5)

            # エントリーからイグジットまでの線
            ax.plot([entry_min, exit_min], [entry_price, exit_price],
                   color=exit_color, linewidth=2, alpha=0.6, linestyle='--')

            # P/L注釈
            ax.annotate(f'{pnl:+,.0f}円\n{exit_reason}',
                       xy=(exit_min, exit_price),
                       xytext=(10, 10 if pnl > 0 else -10),
                       textcoords='offset points',
                       fontsize=9,
                       bbox=dict(boxstyle='round,pad=0.5', facecolor=exit_color, alpha=0.3),
                       ha='left')

        # エントリー時間帯をハイライト（09:15-11:00）
        entry_start_time = pd.Timestamp.combine(date, time(0, 15))  # UTC 00:15 = JST 09:15
        entry_end_time = pd.Timestamp.combine(date, time(2, 0))     # UTC 02:00 = JST 11:00

        entry_start_min = (entry_start_time - day_start).total_seconds() / 60
        entry_end_min = (entry_end_time - day_start).total_seconds() / 60

        ax.axvspan(entry_start_min, entry_end_min, alpha=0.1, color='green', label='エントリー時間帯')

        # 強制決済時刻（15:00）
        force_exit_time = pd.Timestamp.combine(date, time(6, 0))  # UTC 06:00 = JST 15:00
        force_exit_min = (force_exit_time - day_start).total_seconds() / 60
        ax.axvline(x=force_exit_min, color='purple', linestyle=':', linewidth=2, alpha=0.5, label='強制決済時刻')

        # タイトルと軸ラベル
        day_pnl = day_trades['pnl'].sum()
        ax.set_title(f'{date} - TDK ({len(day_trades)}トレード, 損益: {day_pnl:+,.0f}円)',
                    fontsize=12, fontweight='bold')
        ax.set_xlabel('時刻（分）', fontsize=10)
        ax.set_ylabel('株価（円）', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=8)

        # X軸の時刻ラベル
        time_labels = []
        time_positions = []
        for h in range(0, 7):  # UTC 00:00-06:00 = JST 09:00-15:00
            t = pd.Timestamp.combine(date, time(h, 0))
            if t >= day_start and t <= day_data.index[-1]:
                pos = (t - day_start).total_seconds() / 60
                time_positions.append(pos)
                time_labels.append(f'{(h+9)%24:02d}:00')  # JST表示

        ax.set_xticks(time_positions)
        ax.set_xticklabels(time_labels, rotation=0, fontsize=9)

    plt.tight_layout()
    plt.savefig('results/optimization/tdk_trade_details.png', dpi=150, bbox_inches='tight')
    print(f"\n可視化を results/optimization/tdk_trade_details.png に保存しました")

    # サマリーチャート（全期間の累積損益）
    fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))

    # 1. 累積損益グラフ
    trades_sorted = trades.sort_values('entry_time')
    cumulative_pnl = trades_sorted['pnl'].cumsum()

    ax1.plot(range(len(cumulative_pnl)), cumulative_pnl.values,
            marker='o', linewidth=2, markersize=6, color='steelblue')
    ax1.axhline(y=0, color='red', linestyle='--', linewidth=1)
    ax1.set_xlabel('トレード番号', fontsize=12)
    ax1.set_ylabel('累積損益（円）', fontsize=12)
    ax1.set_title('TDK 累積損益推移（直近1ヶ月）', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # 最終損益を注釈
    final_pnl = cumulative_pnl.iloc[-1]
    ax1.annotate(f'最終損益: {final_pnl:+,.0f}円',
                xy=(len(cumulative_pnl)-1, final_pnl),
                xytext=(-100, 20),
                textcoords='offset points',
                fontsize=11,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

    # 2. トレード別P/L棒グラフ
    colors = ['green' if pnl > 0 else 'red' for pnl in trades_sorted['pnl']]
    ax2.bar(range(len(trades_sorted)), trades_sorted['pnl'], color=colors, alpha=0.7, edgecolor='black')
    ax2.axhline(y=0, color='black', linewidth=1)
    ax2.set_xlabel('トレード番号', fontsize=12)
    ax2.set_ylabel('損益（円）', fontsize=12)
    ax2.set_title('TDK トレード別損益', fontsize=14, fontweight='bold')
    ax2.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/optimization/tdk_pnl_summary.png', dpi=150, bbox_inches='tight')
    print(f"サマリーを results/optimization/tdk_pnl_summary.png に保存しました")

    # トレード統計
    print("\n" + "=" * 80)
    print("トレード統計")
    print("=" * 80)

    total_trades = len(trades)
    win_trades = (trades['pnl'] > 0).sum()
    loss_trades = (trades['pnl'] < 0).sum()
    win_rate = win_trades / total_trades * 100

    # イグジット理由を推測してカウント
    profit_target_exits = 0
    stop_loss_exits = 0
    force_exits = 0

    for _, trade in trades.iterrows():
        price_change_pct = (trade['exit_price'] / trade['entry_price'] - 1) * 100
        if price_change_pct >= 4.0:
            profit_target_exits += 1
        elif price_change_pct <= -0.75:
            stop_loss_exits += 1
        else:
            force_exits += 1

    print(f"\n総トレード数: {total_trades}")
    print(f"勝ちトレード: {win_trades} ({win_rate:.1f}%)")
    print(f"負けトレード: {loss_trades} ({(100-win_rate):.1f}%)")
    print(f"\nイグジット理由:")
    print(f"  利確: {profit_target_exits} ({profit_target_exits/total_trades*100:.1f}%)")
    print(f"  損切: {stop_loss_exits} ({stop_loss_exits/total_trades*100:.1f}%)")
    print(f"  強制: {force_exits} ({force_exits/total_trades*100:.1f}%)")

    avg_win = trades[trades['pnl'] > 0]['pnl'].mean()
    avg_loss = trades[trades['pnl'] < 0]['pnl'].mean()

    print(f"\n平均利益: {avg_win:+,.0f}円")
    print(f"平均損失: {avg_loss:+,.0f}円")
    print(f"損益レシオ: {abs(avg_win/avg_loss):.2f}")

    print(f"\n総損益: {trades['pnl'].sum():+,.0f}円")
    print(f"総リターン: {trades['pnl'].sum()/OPTIMIZED_PARAMS['initial_capital']*100:+.2f}%")

    print("\n" + "=" * 80)
    print("完了")
    print("=" * 80)

if __name__ == "__main__":
    main()
