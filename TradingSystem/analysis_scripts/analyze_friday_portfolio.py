#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金曜日推奨ポートフォリオ分析

1ヶ月分のバックテスト結果から金曜日に強い銘柄を特定し、
明日の推奨ポートフォリオを作成する
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def analyze_friday_portfolio(
    result_folder: str = "Output/20251204_231158",
    start_date: str = "2025-11-04"
):
    """金曜日推奨ポートフォリオ分析"""

    print("=" * 80)
    print("金曜日推奨ポートフォリオ分析（1ヶ月間）")
    print("=" * 80)

    output_path = Path(result_folder)

    # 全CSVファイル読み込み
    csv_files = list(output_path.glob("*_trades.csv"))

    print(f"\n銘柄数: {len(csv_files)}")
    print(f"分析期間: {start_date} 以降")

    # 銘柄名マッピング
    symbol_names = {
        '2502.T': 'アサヒグループHD',
        '2503.T': 'キリンHD',
        '2801.T': 'キッコーマン',
        '4183.T': '三井化学',
        '5016.T': 'JX金属',
        '5332.T': 'TOTO',
        '5706.T': '三井金属',
        '5713.T': '住友金属鉱山',
        '5714.T': 'DOWAホールディングス',
        '5801.T': '古河電気工業',
        '5802.T': '住友電気工業',
        '5803.T': 'フジクラ',
        '6146.T': 'ディスコ',
        '6752.T': 'パナソニック',
        '6762.T': 'TDK',
        '7013.T': 'IHI',
        '7741.T': 'HOYA',
        '8001.T': '伊藤忠商事',
        '8015.T': '豊田通商',
        '8035.T': '東京エレクトロン',
        '8053.T': '住友商事',
        '8267.T': 'イオン',
        '9501.T': '東京電力',
        '9502.T': '中部電力',
        '9983.T': 'ファーストリテイリング',
        '9984.T': 'ソフトバンクグループ'
    }

    # 全トレードデータを結合
    all_trades = []

    for csv_file in csv_files:
        symbol = csv_file.stem.replace('_trades', '')

        try:
            df = pd.read_csv(csv_file)

            if len(df) == 0:
                continue

            df['symbol'] = symbol
            all_trades.append(df)

        except Exception as e:
            print(f"エラー: {symbol}: {e}")
            continue

    # 全データ結合
    combined_df = pd.concat(all_trades, ignore_index=True)

    # 日付型に変換
    combined_df['entry_time'] = pd.to_datetime(combined_df['entry_time'])
    combined_df['entry_date'] = combined_df['entry_time'].dt.date

    # 期間フィルタ
    combined_df = combined_df[combined_df['entry_date'] >= pd.to_datetime(start_date).date()]

    # 曜日を追加（4=金曜日）
    combined_df['weekday'] = combined_df['entry_time'].dt.dayofweek

    # 金曜日のみ抽出
    friday_df = combined_df[combined_df['weekday'] == 4]

    print(f"金曜日総トレード数: {len(friday_df)}回")

    # 銘柄別集計
    symbol_stats = []

    symbols = friday_df['symbol'].unique()

    for symbol in symbols:
        symbol_df = friday_df[friday_df['symbol'] == symbol]

        total_pnl = symbol_df['pnl'].sum()
        total_trades = len(symbol_df)
        wins = len(symbol_df[symbol_df['pnl'] > 0])
        losses = len(symbol_df[symbol_df['pnl'] <= 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0

        # PF計算
        profits = symbol_df[symbol_df['pnl'] > 0]['pnl'].sum()
        losses_sum = abs(symbol_df[symbol_df['pnl'] < 0]['pnl'].sum())
        pf = profits / losses_sum if losses_sum > 0 else float('inf')

        # 平均損益
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

        # 金曜日の取引日数
        friday_days = symbol_df['entry_date'].nunique()

        # 1日あたりの平均損益
        avg_pnl_per_day = total_pnl / friday_days if friday_days > 0 else 0

        # 1ヶ月間全体のパフォーマンス
        month_df = combined_df[combined_df['symbol'] == symbol]
        month_total_pnl = month_df['pnl'].sum()
        month_trades = len(month_df)
        month_pf = 0
        if month_trades > 0:
            month_profits = month_df[month_df['pnl'] > 0]['pnl'].sum()
            month_losses_sum = abs(month_df[month_df['pnl'] < 0]['pnl'].sum())
            month_pf = month_profits / month_losses_sum if month_losses_sum > 0 else float('inf')

        symbol_stats.append({
            'symbol': symbol,
            'symbol_name': symbol_names.get(symbol, symbol),
            'friday_pnl': total_pnl,
            'friday_trades': total_trades,
            'friday_wins': wins,
            'friday_losses': losses,
            'friday_win_rate': win_rate,
            'friday_pf': pf,
            'friday_avg_pnl': avg_pnl,
            'friday_days': friday_days,
            'friday_avg_pnl_per_day': avg_pnl_per_day,
            'month_total_pnl': month_total_pnl,
            'month_pf': month_pf
        })

    stats_df = pd.DataFrame(symbol_stats)
    stats_df = stats_df.sort_values('friday_pnl', ascending=False)

    # 金曜日全体統計
    print("\n" + "=" * 80)
    print("金曜日全体統計")
    print("=" * 80)

    friday_total_pnl = friday_df['pnl'].sum()
    friday_total_trades = len(friday_df)
    friday_wins = len(friday_df[friday_df['pnl'] > 0])
    friday_win_rate = friday_wins / friday_total_trades * 100 if friday_total_trades > 0 else 0

    friday_profits = friday_df[friday_df['pnl'] > 0]['pnl'].sum()
    friday_losses_sum = abs(friday_df[friday_df['pnl'] < 0]['pnl'].sum())
    friday_pf = friday_profits / friday_losses_sum if friday_losses_sum > 0 else 0

    print(f"\n総損益: {friday_total_pnl:>12,.0f}円")
    print(f"PF: {friday_pf:.2f}")
    print(f"勝率: {friday_win_rate:.1f}%")
    print(f"トレード数: {friday_total_trades}回")

    # 推奨ポートフォリオ
    print("\n" + "=" * 80)
    print("明日（12/5 金曜日）の推奨ポートフォリオ")
    print("=" * 80)

    # 推奨基準：金曜日PF > 1.0 かつ 1ヶ月PF > 1.3
    recommended = stats_df[
        (stats_df['friday_pf'] > 1.0) &
        (stats_df['month_pf'] > 1.3) &
        (stats_df['friday_trades'] >= 3)  # 最低3回はトレードがある
    ].head(15)

    if len(recommended) > 0:
        print(f"\n✅ 推奨銘柄数: {len(recommended)}銘柄")
        print("\n【推奨ポートフォリオ詳細】")
        print("-" * 80)

        for i, (_, row) in enumerate(recommended.iterrows(), 1):
            friday_pf_str = f"{row['friday_pf']:.2f}" if row['friday_pf'] != float('inf') else "∞"
            month_pf_str = f"{row['month_pf']:.2f}" if row['month_pf'] != float('inf') else "∞"

            print(f"\n{i:2d}. {row['symbol_name']:20s} ({row['symbol']})")
            print(f"    金曜日: 損益{row['friday_pnl']:>10,.0f}円 | PF:{friday_pf_str:>6s} | 勝率:{row['friday_win_rate']:>5.1f}% | {row['friday_trades']}回")
            print(f"    1ヶ月間: 損益{row['month_total_pnl']:>10,.0f}円 | PF:{month_pf_str:>6s}")

        # サマリー
        print("\n" + "=" * 80)
        print("推奨ポートフォリオサマリー")
        print("=" * 80)

        recommended_symbols = recommended['symbol'].tolist()
        print(f"\n推奨銘柄リスト（{len(recommended_symbols)}銘柄）:")
        for symbol in recommended_symbols:
            name = symbol_names.get(symbol, symbol)
            print(f"  - {name} ({symbol})")

        # 期待損益
        expected_pnl = recommended['friday_avg_pnl_per_day'].sum()
        print(f"\n期待損益/日: {expected_pnl:>12,.0f}円")
        print(f"平均金曜日PF: {recommended['friday_pf'].mean():.2f}")
        print(f"平均1ヶ月PF: {recommended['month_pf'].mean():.2f}")

    else:
        print("\n⚠️ 推奨基準を満たす銘柄がありません")

    # 回避推奨銘柄
    print("\n" + "=" * 80)
    print("回避推奨銘柄（金曜日に弱い）")
    print("=" * 80)

    avoid_stocks = stats_df[
        (stats_df['friday_pf'] < 1.0) |
        (stats_df['friday_pnl'] < 0)
    ].head(10)

    if len(avoid_stocks) > 0:
        print(f"\n❌ 回避推奨: {len(avoid_stocks)}銘柄")
        for i, (_, row) in enumerate(avoid_stocks.iterrows(), 1):
            friday_pf_str = f"{row['friday_pf']:.2f}" if row['friday_pf'] != float('inf') else "∞"
            print(f"  {i}. {row['symbol_name']:20s} ({row['symbol']})")
            print(f"     金曜日: {row['friday_pnl']:>10,.0f}円 | PF:{friday_pf_str:>6s} | 勝率:{row['friday_win_rate']:>5.1f}%")
    else:
        print("\n全銘柄が金曜日にプラス！")

    # 全銘柄ランキング
    print("\n" + "=" * 80)
    print("金曜日パフォーマンスランキング（全26銘柄）")
    print("=" * 80)

    print("\n【金曜日 総損益ランキング TOP 10】")
    for i, (_, row) in enumerate(stats_df.head(10).iterrows(), 1):
        friday_pf_str = f"{row['friday_pf']:.2f}" if row['friday_pf'] != float('inf') else "∞"
        print(f"  {i:2d}位: {row['symbol_name']:20s} {row['friday_pnl']:>12,.0f}円 (PF:{friday_pf_str}, 勝率:{row['friday_win_rate']:.1f}%)")

    print("\n【金曜日 総損益ランキング WORST 5】")
    worst5 = stats_df.tail(5).sort_values('friday_pnl')
    for i, (_, row) in enumerate(worst5.iterrows(), 1):
        friday_pf_str = f"{row['friday_pf']:.2f}" if row['friday_pf'] != float('inf') else "∞"
        print(f"  {i:2d}位: {row['symbol_name']:20s} {row['friday_pnl']:>12,.0f}円 (PF:{friday_pf_str}, 勝率:{row['friday_win_rate']:.1f}%)")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)

    return stats_df, recommended


if __name__ == "__main__":
    analyze_friday_portfolio()
