#!/usr/bin/env python3
"""
セクター別パフォーマンス分析
- 重厚長大系セクターの分析
- 直近3ヶ月のパフォーマンス比較
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# セクター分類
SECTORS = {
    # 重厚長大セクター
    '重工業': {
        '7011.T': '三菱重工業',
        '7012.T': '川崎重工業',
        '7013.T': 'IHI',
    },
    '海運': {
        '9107.T': '川崎汽船',
        '9104.T': '商船三井',
    },
    '鉄鋼・非鉄': {
        '5401.T': '日本製鉄',
        '5711.T': '三菱マテリアル',
        '5706.T': '三井金属',
    },
    '電線・電力': {
        '5801.T': '古河電気工業',
        '5803.T': 'フジクラ',
    },

    # 半導体セクター
    '半導体製造装置': {
        '8035.T': '東京エレクトロン',
        '6146.T': 'ディスコ',
        '6920.T': 'レーザーテック',
    },
    '半導体関連': {
        '6503.T': '三菱電機',
        '7741.T': 'HOYA',
        '6752.T': 'パナソニック',
    },

    # 通信・IT
    '通信': {
        '9433.T': 'KDDI',
        '9437.T': 'NTTドコモ',
    },

    # 自動車
    '自動車': {
        '7267.T': 'ホンダ',
        '7269.T': 'スズキ',
    },

    # 建設
    '建設': {
        '1925.T': '大和ハウス',
        '1928.T': '積水ハウス',
    },

    # 金融
    '金融': {
        '8411.T': 'みずほFG',
        '8306.T': '三菱UFJ',
    },
}

def analyze_sector_performance():
    """セクター別パフォーマンスを分析"""

    output_dir = Path("Output/20251119_235250")

    print("\n" + "=" * 80)
    print("セクター別パフォーマンス分析")
    print("=" * 80)

    # 全トレードデータを読み込み
    all_trades = []
    symbol_stats = {}

    for trades_file in sorted(output_dir.glob("*_trades.csv")):
        symbol = trades_file.stem.replace("_trades", "")
        df = pd.read_csv(trades_file)

        if len(df) == 0:
            continue

        df['symbol'] = symbol
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['date'] = df['entry_time'].dt.date

        all_trades.append(df)

        # 銘柄別統計
        total_pnl = df['pnl'].sum()
        win_rate = len(df[df['pnl'] > 0]) / len(df) * 100 if len(df) > 0 else 0
        avg_pnl = df['pnl'].mean()

        total_profit = df[df['pnl'] > 0]['pnl'].sum()
        total_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        symbol_stats[symbol] = {
            'total_pnl': total_pnl,
            'trade_count': len(df),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
        }

    if not all_trades:
        print("データなし")
        return

    df_all = pd.concat(all_trades, ignore_index=True)

    # 期間の確認
    start_date = df_all['date'].min()
    end_date = df_all['date'].max()
    days_count = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days

    print(f"\n【分析期間】")
    print(f"開始日: {start_date}")
    print(f"終了日: {end_date}")
    print(f"期間: {days_count}日（約{days_count/30:.1f}ヶ月）")

    # 直近3ヶ月のデータ抽出
    three_months_ago = end_date - timedelta(days=90)
    df_3months = df_all[df_all['date'] >= three_months_ago]

    print(f"\n直近3ヶ月（{three_months_ago}以降）のデータで分析")
    print(f"取引数: {len(df_3months)}回")

    # 直近3ヶ月の銘柄別統計
    symbol_stats_3m = {}
    for symbol in df_3months['symbol'].unique():
        df_sym = df_3months[df_3months['symbol'] == symbol]

        total_pnl = df_sym['pnl'].sum()
        win_rate = len(df_sym[df_sym['pnl'] > 0]) / len(df_sym) * 100 if len(df_sym) > 0 else 0
        avg_pnl = df_sym['pnl'].mean()

        total_profit = df_sym[df_sym['pnl'] > 0]['pnl'].sum()
        total_loss = abs(df_sym[df_sym['pnl'] < 0]['pnl'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        symbol_stats_3m[symbol] = {
            'total_pnl': total_pnl,
            'trade_count': len(df_sym),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
        }

    # セクター別集計
    print(f"\n" + "=" * 80)
    print("【セクター別パフォーマンス（直近3ヶ月）】")
    print("=" * 80)

    sector_performance = {}

    for sector_name, symbols in SECTORS.items():
        sector_total_pnl = 0
        sector_trade_count = 0
        sector_win_count = 0
        sector_symbols_found = []

        for symbol, company_name in symbols.items():
            if symbol in symbol_stats_3m:
                stats = symbol_stats_3m[symbol]
                sector_total_pnl += stats['total_pnl']
                sector_trade_count += stats['trade_count']
                sector_win_count += int(stats['win_rate'] * stats['trade_count'] / 100)
                sector_symbols_found.append({
                    'symbol': symbol,
                    'name': company_name,
                    **stats
                })

        if sector_symbols_found:
            sector_win_rate = sector_win_count / sector_trade_count * 100 if sector_trade_count > 0 else 0
            sector_avg_pnl = sector_total_pnl / sector_trade_count if sector_trade_count > 0 else 0

            sector_performance[sector_name] = {
                'total_pnl': sector_total_pnl,
                'trade_count': sector_trade_count,
                'win_rate': sector_win_rate,
                'avg_pnl': sector_avg_pnl,
                'symbols': sector_symbols_found,
                'symbol_count': len(sector_symbols_found)
            }

    # セクター別ランキング
    sorted_sectors = sorted(sector_performance.items(), key=lambda x: x[1]['total_pnl'], reverse=True)

    print(f"\n{'セクター':<15} {'銘柄数':<6} {'取引数':<6} {'勝率':<7} {'総損益':<12} {'平均損益':<10}")
    print("-" * 80)

    for sector_name, stats in sorted_sectors:
        print(f"{sector_name:<15} {stats['symbol_count']:<6} {stats['trade_count']:<6} "
              f"{stats['win_rate']:>5.1f}% {stats['total_pnl']:>11,.0f}円 {stats['avg_pnl']:>9,.0f}円")

    # 重厚長大セクターの詳細分析
    print(f"\n" + "=" * 80)
    print("【重厚長大セクター詳細（直近3ヶ月）】")
    print("=" * 80)

    heavy_sectors = ['重工業', '海運', '鉄鋼・非鉄', '電線・電力']

    for sector_name in heavy_sectors:
        if sector_name in sector_performance:
            print(f"\n■ {sector_name}")
            print("-" * 80)

            stats = sector_performance[sector_name]
            print(f"セクター合計: {stats['total_pnl']:+,.0f}円 (勝率 {stats['win_rate']:.1f}%, {stats['trade_count']}回)")

            print(f"\n{'銘柄':<8} {'企業名':<12} {'勝率':<7} {'PF':<6} {'総損益':<12} {'平均損益':<10}")
            print("-" * 80)

            for sym_info in sorted(stats['symbols'], key=lambda x: x['total_pnl'], reverse=True):
                print(f"{sym_info['symbol']:<8} {sym_info['name']:<12} {sym_info['win_rate']:>5.1f}% "
                      f"{sym_info['profit_factor']:>5.2f} {sym_info['total_pnl']:>11,.0f}円 "
                      f"{sym_info['avg_pnl']:>9,.0f}円")

    # 重厚長大 vs 半導体の比較
    print(f"\n" + "=" * 80)
    print("【重厚長大 vs 半導体セクター比較（直近3ヶ月）】")
    print("=" * 80)

    heavy_total = sum(sector_performance.get(s, {'total_pnl': 0})['total_pnl'] for s in heavy_sectors)
    heavy_trades = sum(sector_performance.get(s, {'trade_count': 0})['trade_count'] for s in heavy_sectors)
    heavy_avg = heavy_total / heavy_trades if heavy_trades > 0 else 0

    semi_sectors = ['半導体製造装置', '半導体関連']
    semi_total = sum(sector_performance.get(s, {'total_pnl': 0})['total_pnl'] for s in semi_sectors)
    semi_trades = sum(sector_performance.get(s, {'trade_count': 0})['trade_count'] for s in semi_sectors)
    semi_avg = semi_total / semi_trades if semi_trades > 0 else 0

    print(f"\n重厚長大セクター:")
    print(f"  総損益: {heavy_total:+,.0f}円")
    print(f"  取引数: {heavy_trades}回")
    print(f"  平均損益: {heavy_avg:+,.0f}円/回")

    print(f"\n半導体セクター:")
    print(f"  総損益: {semi_total:+,.0f}円")
    print(f"  取引数: {semi_trades}回")
    print(f"  平均損益: {semi_avg:+,.0f}円/回")

    if heavy_avg < 0:
        print(f"\n→ 重厚長大セクターは直近3ヶ月で平均マイナス（弱い）")
    else:
        print(f"\n→ 重厚長大セクターは直近3ヶ月で平均プラス")

    if semi_avg > heavy_avg:
        diff = semi_avg - heavy_avg
        print(f"→ 半導体セクターは重厚長大より平均{diff:+,.0f}円/回優れている")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    analyze_sector_performance()
