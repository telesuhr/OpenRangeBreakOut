#!/usr/bin/env python3
"""
テクノロジー+非鉄金属 上位20銘柄の日次パフォーマンスヒートマップ
直近60営業日
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
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

# 上位20銘柄（パフォーマンス順）
TOP_STOCKS = [
    # 非鉄金属（トップ7全て）
    ('5803.T', 'フジクラ', '非鉄'),
    ('5801.T', '古河電気工業', '非鉄'),
    ('5802.T', '住友電気工業', '非鉄'),
    ('5706.T', '三井金属鉱業', '非鉄'),
    ('5713.T', '住友金属鉱山', '非鉄'),
    ('5711.T', '三菱マテリアル', '非鉄'),
    ('5714.T', 'DOWAホールディングス', '非鉄'),

    # テクノロジー（トップ5全て）
    ('6762.T', 'TDK', 'テック'),
    ('6857.T', 'アドバンテスト', 'テック'),
    ('6752.T', 'パナソニック', 'テック'),
    ('6758.T', 'ソニーグループ', 'テック'),
    ('6594.T', '日本電産', 'テック'),

    # 通信（トップ3）
    ('9984.T', 'ソフトバンクG', '通信'),
    ('9433.T', 'KDDI', '通信'),
    ('9432.T', 'NTT', '通信'),

    # 素材・化学（トップ3）
    ('4183.T', '三井化学', '素材'),
    ('4063.T', '信越化学', '素材'),
    ('4188.T', '三菱ケミカルG', '素材'),

    # エネルギー（トップ2）
    ('9501.T', '東京電力HD', 'エネ'),
    ('1605.T', 'INPEX', 'エネ'),
]

# バックテスト期間（直近60営業日 ≈ 3ヶ月）
END_DATE = datetime(2025, 11, 12)
START_DATE = datetime(2025, 8, 1)  # 約3ヶ月前

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
    print("上位20銘柄 日次パフォーマンスヒートマップ作成")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()} (約60営業日)")
    print(f"銘柄数: {len(TOP_STOCKS)}")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 日次パフォーマンスを収集
    all_daily_pnl = {}

    for idx, (symbol, name, sector) in enumerate(TOP_STOCKS, 1):
        print(f"[{idx}/{len(TOP_STOCKS)}] {name:20s} ({symbol})", end='', flush=True)

        try:
            engine = BacktestEngine(**PARAMS)
            results = engine.run_backtest(
                client=client,
                symbols=[symbol],
                start_date=START_DATE,
                end_date=END_DATE
            )

            if 'trades' in results and results['trades'] is not None:
                trades_data = results['trades']

                if isinstance(trades_data, pd.DataFrame) and not trades_data.empty:
                    # 日次集計
                    trades_data['date'] = pd.to_datetime(trades_data['entry_time']).dt.date
                    daily_pnl = trades_data.groupby('date')['pnl'].sum()

                    # リターン率に変換
                    daily_return = (daily_pnl / PARAMS['initial_capital']) * 100

                    all_daily_pnl[f"{name}({sector})"] = daily_return

                    total_pnl = trades_data['pnl'].sum()
                    num_trades = len(trades_data)
                    print(f" | {num_trades}トレード, {total_pnl:+,.0f}円")
                else:
                    print(" | トレードなし")
                    all_daily_pnl[f"{name}({sector})"] = pd.Series(dtype=float)
            else:
                print(" | データなし")
                all_daily_pnl[f"{name}({sector})"] = pd.Series(dtype=float)

        except Exception as e:
            print(f" | エラー: {e}")
            all_daily_pnl[f"{name}({sector})"] = pd.Series(dtype=float)
            continue

    client.disconnect()

    # データフレームに変換
    df = pd.DataFrame(all_daily_pnl)
    df = df.fillna(0)  # トレードがない日は0

    # 日付順にソート
    df = df.sort_index()

    # 最近60営業日に絞る
    if len(df) > 60:
        df = df.tail(60)

    print(f"\n\nヒートマップ作成中...")
    print(f"データ期間: {df.index[0]} ～ {df.index[-1]}")
    print(f"営業日数: {len(df)}")

    # ヒートマップ作成
    fig, ax = plt.subplots(figsize=(20, 12))

    # 転置して銘柄を縦軸、日付を横軸に
    df_T = df.T

    # カラーマップ（赤＝損失、緑＝利益）
    sns.heatmap(
        df_T,
        cmap='RdYlGn',  # 赤-黄-緑
        center=0,
        vmin=-2,  # -2%
        vmax=2,   # +2%
        linewidths=0.5,
        linecolor='gray',
        cbar_kws={'label': '日次リターン (%)'},
        ax=ax,
        fmt='.2f'
    )

    # タイトルとラベル
    ax.set_title('上位20銘柄 日次パフォーマンス ヒートマップ\n（直近60営業日）',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('日付', fontsize=12)
    ax.set_ylabel('銘柄', fontsize=12)

    # X軸のラベルを見やすく
    n_dates = len(df_T.columns)
    step = max(1, n_dates // 15)  # 最大15個のラベル
    tick_positions = list(range(0, n_dates, step))
    tick_labels = [df_T.columns[i].strftime('%m/%d') if i < n_dates else ''
                   for i in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha='right')

    # Y軸のラベルを調整
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, ha='right')

    plt.tight_layout()

    # 保存
    output_path = 'results/optimization/top20_heatmap_60days.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nヒートマップを {output_path} に保存しました")

    # 統計情報
    print(f"\n{'='*80}")
    print("統計サマリー（60営業日）")
    print(f"{'='*80}\n")

    # 銘柄ごとの統計
    stats = pd.DataFrame({
        '平均日次リターン': df.mean(),
        '累積リターン': df.sum(),
        'プラス日数': (df > 0).sum(),
        'マイナス日数': (df < 0).sum(),
        '最大日次リターン': df.max(),
        '最小日次リターン': df.min(),
    })

    stats = stats.sort_values('累積リターン', ascending=False)

    print("■ 銘柄別パフォーマンス（累積リターン順）")
    print(stats.to_string())

    # CSV保存
    df.to_csv('results/optimization/top20_daily_returns_60days.csv', encoding='utf-8-sig')
    stats.to_csv('results/optimization/top20_stats_60days.csv', encoding='utf-8-sig')

    print(f"\n\n詳細データを以下に保存:")
    print(f"  - results/optimization/top20_daily_returns_60days.csv")
    print(f"  - results/optimization/top20_stats_60days.csv")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
