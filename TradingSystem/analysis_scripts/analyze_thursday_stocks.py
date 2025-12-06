#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
木曜日に強い銘柄分析

木曜日の個別銘柄パフォーマンスを分析し、
明日のトレード戦略を検討する
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def analyze_thursday_stocks(
    result_folder: str = "Output/20251203_081519",
    start_date: str = "2025-06-01"  # 直近6ヶ月
):
    """木曜日に強い銘柄分析"""

    print("=" * 80)
    print("木曜日銘柄別パフォーマンス分析")
    print("=" * 80)

    output_path = Path(result_folder)

    # 全CSVファイル読み込み
    csv_files = list(output_path.glob("*_trades.csv"))

    print(f"\n銘柄数: {len(csv_files)}")
    print(f"分析期間: {start_date} 以降（直近6ヶ月）")

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

    # 曜日を追加（3=木曜日）
    combined_df['weekday'] = combined_df['entry_time'].dt.dayofweek

    # 木曜日のみ抽出
    thursday_df = combined_df[combined_df['weekday'] == 3]

    print(f"木曜日総トレード数: {len(thursday_df)}回")

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

    print("\n" + "=" * 80)
    print("木曜日 銘柄別パフォーマンス（LONG/SHORT統合）")
    print("=" * 80)

    # 銘柄別集計
    symbol_stats = []

    symbols = thursday_df['symbol'].unique()

    for symbol in symbols:
        symbol_df = thursday_df[thursday_df['symbol'] == symbol]

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

        # 木曜日の取引日数
        thursday_days = symbol_df['entry_date'].nunique()

        # 1日あたりの平均損益
        avg_pnl_per_day = total_pnl / thursday_days if thursday_days > 0 else 0

        symbol_stats.append({
            'symbol': symbol,
            'symbol_name': symbol_names.get(symbol, symbol),
            'total_pnl': total_pnl,
            'trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'pf': pf,
            'avg_pnl': avg_pnl,
            'thursday_days': thursday_days,
            'avg_pnl_per_day': avg_pnl_per_day
        })

    stats_df = pd.DataFrame(symbol_stats)
    stats_df = stats_df.sort_values('total_pnl', ascending=False)

    # 上位銘柄
    print("\n【総損益 TOP 10】（木曜日に強い）")
    print("-" * 80)

    top10 = stats_df.head(10)
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
        print(f"{i:2d}位: {row['symbol_name']:20s} ({row['symbol']})")
        print(f"      総損益: {row['total_pnl']:>12,.0f}円 | PF:{pf_str:>6s} | 勝率:{row['win_rate']:>5.1f}% | {row['trades']}回")

    # 下位銘柄
    print("\n【総損益 WORST 10】（木曜日に弱い）")
    print("-" * 80)

    worst10 = stats_df.tail(10).sort_values('total_pnl')
    for i, (_, row) in enumerate(worst10.iterrows(), 1):
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
        print(f"{i:2d}位: {row['symbol_name']:20s} ({row['symbol']})")
        print(f"      総損益: {row['total_pnl']:>12,.0f}円 | PF:{pf_str:>6s} | 勝率:{row['win_rate']:>5.1f}% | {row['trades']}回")

    # LONG/SHORT別の木曜日パフォーマンス
    print("\n" + "=" * 80)
    print("木曜日 銘柄別パフォーマンス（LONG）")
    print("=" * 80)

    long_stats = []

    for symbol in symbols:
        symbol_df = thursday_df[(thursday_df['symbol'] == symbol) & (thursday_df['side'] == 'long')]

        if len(symbol_df) == 0:
            continue

        total_pnl = symbol_df['pnl'].sum()
        total_trades = len(symbol_df)
        wins = len(symbol_df[symbol_df['pnl'] > 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0

        # PF計算
        profits = symbol_df[symbol_df['pnl'] > 0]['pnl'].sum()
        losses_sum = abs(symbol_df[symbol_df['pnl'] < 0]['pnl'].sum())
        pf = profits / losses_sum if losses_sum > 0 else float('inf')

        long_stats.append({
            'symbol': symbol,
            'symbol_name': symbol_names.get(symbol, symbol),
            'total_pnl': total_pnl,
            'trades': total_trades,
            'win_rate': win_rate,
            'pf': pf
        })

    long_df = pd.DataFrame(long_stats)
    long_df = long_df.sort_values('total_pnl', ascending=False)

    print("\n【LONG 総損益 TOP 10】")
    print("-" * 80)

    long_top10 = long_df.head(10)
    for i, (_, row) in enumerate(long_top10.iterrows(), 1):
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
        print(f"{i:2d}位: {row['symbol_name']:20s} ({row['symbol']})")
        print(f"      総損益: {row['total_pnl']:>12,.0f}円 | PF:{pf_str:>6s} | 勝率:{row['win_rate']:>5.1f}% | {row['trades']}回")

    # SHORT別の木曜日パフォーマンス
    print("\n" + "=" * 80)
    print("木曜日 銘柄別パフォーマンス（SHORT）")
    print("=" * 80)

    short_stats = []

    for symbol in symbols:
        symbol_df = thursday_df[(thursday_df['symbol'] == symbol) & (thursday_df['side'] == 'short')]

        if len(symbol_df) == 0:
            continue

        total_pnl = symbol_df['pnl'].sum()
        total_trades = len(symbol_df)
        wins = len(symbol_df[symbol_df['pnl'] > 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0

        # PF計算
        profits = symbol_df[symbol_df['pnl'] > 0]['pnl'].sum()
        losses_sum = abs(symbol_df[symbol_df['pnl'] < 0]['pnl'].sum())
        pf = profits / losses_sum if losses_sum > 0 else float('inf')

        short_stats.append({
            'symbol': symbol,
            'symbol_name': symbol_names.get(symbol, symbol),
            'total_pnl': total_pnl,
            'trades': total_trades,
            'win_rate': win_rate,
            'pf': pf
        })

    short_df = pd.DataFrame(short_stats)
    short_df = short_df.sort_values('total_pnl', ascending=False)

    print("\n【SHORT 総損益 TOP 10】")
    print("-" * 80)

    short_top10 = short_df.head(10)
    for i, (_, row) in enumerate(short_top10.iterrows(), 1):
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
        print(f"{i:2d}位: {row['symbol_name']:20s} ({row['symbol']})")
        print(f"      総損益: {row['total_pnl']:>12,.0f}円 | PF:{pf_str:>6s} | 勝率:{row['win_rate']:>5.1f}% | {row['trades']}回")

    print("\n【SHORT 総損益 WORST 10】")
    print("-" * 80)

    short_worst10 = short_df.tail(10).sort_values('total_pnl')
    for i, (_, row) in enumerate(short_worst10.iterrows(), 1):
        pf_str = f"{row['pf']:.2f}" if row['pf'] != float('inf') else "∞"
        print(f"{i:2d}位: {row['symbol_name']:20s} ({row['symbol']})")
        print(f"      総損益: {row['total_pnl']:>12,.0f}円 | PF:{pf_str:>6s} | 勝率:{row['win_rate']:>5.1f}% | {row['trades']}回")

    # 明日のトレード推奨
    print("\n" + "=" * 80)
    print("明日（12/4 木曜日）のトレード戦略")
    print("=" * 80)

    # 全体統計
    thursday_total_pnl = thursday_df['pnl'].sum()
    thursday_total_trades = len(thursday_df)
    thursday_wins = len(thursday_df[thursday_df['pnl'] > 0])
    thursday_win_rate = thursday_wins / thursday_total_trades * 100 if thursday_total_trades > 0 else 0

    thursday_profits = thursday_df[thursday_df['pnl'] > 0]['pnl'].sum()
    thursday_losses_sum = abs(thursday_df[thursday_df['pnl'] < 0]['pnl'].sum())
    thursday_pf = thursday_profits / thursday_losses_sum if thursday_losses_sum > 0 else 0

    print(f"\n木曜日全体統計（直近6ヶ月）:")
    print(f"  総損益: {thursday_total_pnl:>12,.0f}円")
    print(f"  PF: {thursday_pf:.2f}")
    print(f"  勝率: {thursday_win_rate:.1f}%")
    print(f"  トレード数: {thursday_total_trades}回")

    # 推奨戦略
    print("\n【推奨戦略】")

    if thursday_pf > 1.0:
        print(f"\n✅ 木曜日は直近6ヶ月でプラス（PF {thursday_pf:.2f}）")
        print("   → トレード可能")

        # LONG推奨銘柄
        print("\n【LONG推奨銘柄 TOP 5】")
        long_recommend = long_df[long_df['pf'] > 1.0].head(5)

        if len(long_recommend) > 0:
            for i, (_, row) in enumerate(long_recommend.iterrows(), 1):
                print(f"  {i}. {row['symbol_name']} ({row['symbol']})")
                print(f"     PF:{row['pf']:.2f}, 勝率:{row['win_rate']:.1f}%, 総損益:{row['total_pnl']:,.0f}円")
        else:
            print("  該当なし（PF>1.0の銘柄なし）")

        # SHORT推奨銘柄
        print("\n【SHORT推奨銘柄 TOP 5】")
        short_recommend = short_df[short_df['pf'] > 1.0].head(5)

        if len(short_recommend) > 0:
            for i, (_, row) in enumerate(short_recommend.iterrows(), 1):
                print(f"  {i}. {row['symbol_name']} ({row['symbol']})")
                print(f"     PF:{row['pf']:.2f}, 勝率:{row['win_rate']:.1f}%, 総損益:{row['total_pnl']:,.0f}円")
        else:
            print("  該当なし（PF>1.0の銘柄なし）")

        # 回避銘柄
        print("\n【回避推奨銘柄（木曜日に弱い）】")
        avoid_stocks = stats_df[stats_df['total_pnl'] < -50000].head(5)

        if len(avoid_stocks) > 0:
            for i, (_, row) in enumerate(avoid_stocks.iterrows(), 1):
                print(f"  {i}. {row['symbol_name']} ({row['symbol']})")
                print(f"     総損益:{row['total_pnl']:,.0f}円, PF:{row['pf']:.2f}, 勝率:{row['win_rate']:.1f}%")
    else:
        print(f"\n❌ 木曜日は直近6ヶ月でマイナス（PF {thursday_pf:.2f}）")
        print("   → エントリー見送りを推奨")

    # 注意事項
    print("\n【注意事項】")
    print("  ⚠️  昨日（水曜日）の推奨銘柄3つが全滅（-84,315円）")
    print("  ⚠️  水曜日→木曜日の連続損失リスクあり")
    print("  ⚠️  木曜日SHORTは歴史的に壊滅的（1年間で-3,570,150円）")
    print("  💡 トレードする場合はLONG中心、かつ厳選した銘柄のみ推奨")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)

    return stats_df, long_df, short_df


if __name__ == "__main__":
    analyze_thursday_stocks()
