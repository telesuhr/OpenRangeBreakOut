#!/usr/bin/env python3
"""
全セクター詳細分析
各セクターの代表銘柄でバックテストを実施し、
Open Range Breakout戦略の有効性を比較
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
import warnings
warnings.filterwarnings('ignore')

# Helper function
def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)

# セクター別代表銘柄
SECTOR_STOCKS = {
    'テクノロジー': [
        ('6762.T', 'TDK'),
        ('6857.T', 'アドバンテスト'),
        ('6752.T', 'パナソニック'),
        ('6758.T', 'ソニーグループ'),
        ('6594.T', '日本電産'),
    ],
    '金融': [
        ('8306.T', '三菱UFJ'),
        ('8411.T', 'みずほFG'),
        ('8316.T', '三井住友FG'),
        ('8308.T', '野村HD'),
        ('8354.T', 'ふくおかFG'),
    ],
    '通信': [
        ('9984.T', 'ソフトバンクG'),
        ('9433.T', 'KDDI'),
        ('9432.T', 'NTT'),
    ],
    '商社': [
        ('8001.T', '伊藤忠商事'),
        ('8058.T', '三菱商事'),
        ('8031.T', '三井物産'),
        ('8053.T', '住友商事'),
        ('8002.T', '丸紅'),
    ],
    '自動車': [
        ('7203.T', 'トヨタ自動車'),
        ('7267.T', '本田技研'),
        ('7201.T', '日産自動車'),
        ('7269.T', 'スズキ'),
        ('7270.T', 'SUBARU'),
    ],
    '製薬': [
        ('4502.T', '武田薬品'),
        ('4503.T', 'アステラス製薬'),
        ('4568.T', '第一三共'),
        ('4523.T', 'エーザイ'),
        ('4578.T', '大塚HD'),
    ],
    '素材・化学': [
        ('4063.T', '信越化学'),
        ('4452.T', '花王'),
        ('4183.T', '三井化学'),
        ('4911.T', '資生堂'),
        ('4188.T', '三菱ケミカルG'),
    ],
    '消費財': [
        ('2914.T', 'JT'),
        ('2802.T', '味の素'),
        ('2502.T', 'アサヒG'),
        ('2503.T', 'キリンHD'),
        ('7974.T', '任天堂'),
    ],
    'エネルギー': [
        ('5020.T', 'ENEOS'),
        ('1605.T', 'INPEX'),
        ('9501.T', '東京電力HD'),
        ('9502.T', '中部電力'),
        ('9503.T', '関西電力'),
    ],
    '不動産': [
        ('8801.T', '三井不動産'),
        ('8802.T', '三菱地所'),
        ('8830.T', '住友不動産'),
    ],
}

# バックテスト期間（6ヶ月）
END_DATE = datetime(2025, 11, 12)
START_DATE = datetime(2025, 5, 12)

# バックテストパラメータ（最適化済み）
PARAMS = {
    'initial_capital': 10000000,
    'commission_rate': 0.001,
    'range_start': jst_to_utc_time('09:05'),
    'range_end': jst_to_utc_time('09:15'),
    'entry_start': jst_to_utc_time('09:15'),
    'entry_end': jst_to_utc_time('10:00'),
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,  # 4.0%
    'stop_loss': 0.005,     # 0.5%
}

def analyze_sector(client, sector_name, stocks):
    """セクターごとにバックテストを実行"""
    print(f"\n{'='*80}")
    print(f"{sector_name}セクター")
    print(f"{'='*80}")
    print(f"銘柄数: {len(stocks)}")
    print("-" * 80)

    all_trades = []
    stock_results = []

    for idx, (symbol, name) in enumerate(stocks, 1):
        print(f"[{idx}/{len(stocks)}] {name:20s} ({symbol})", end='', flush=True)

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
                    num_trades = len(trades_data)
                    total_pnl = trades_data['pnl'].sum()
                    total_return = total_pnl / PARAMS['initial_capital']
                    win_count = (trades_data['pnl'] > 0).sum()
                    win_rate = win_count / num_trades * 100

                    # 詳細統計
                    avg_pnl = trades_data['pnl'].mean()
                    max_win = trades_data['pnl'].max()
                    max_loss = trades_data['pnl'].min()

                    wins = trades_data[trades_data['pnl'] > 0]['pnl']
                    losses = trades_data[trades_data['pnl'] < 0]['pnl']
                    avg_win = wins.mean() if len(wins) > 0 else 0
                    avg_loss = losses.mean() if len(losses) > 0 else 0
                    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

                    print(f" | {num_trades}トレード, {total_pnl:+,.0f}円 ({total_return*100:+.2f}%), 勝率{win_rate:.1f}%")

                    # データ保存
                    for _, trade in trades_data.iterrows():
                        trade_dict = trade.to_dict()
                        trade_dict['symbol'] = symbol
                        trade_dict['stock_name'] = name
                        trade_dict['sector'] = sector_name
                        all_trades.append(trade_dict)

                    stock_results.append({
                        'sector': sector_name,
                        'symbol': symbol,
                        'name': name,
                        'trades': num_trades,
                        'pnl': total_pnl,
                        'return': total_return,
                        'win_rate': win_rate,
                        'avg_pnl': avg_pnl,
                        'max_win': max_win,
                        'max_loss': max_loss,
                        'avg_win': avg_win,
                        'avg_loss': avg_loss,
                        'profit_factor': profit_factor,
                    })
                else:
                    print(" | トレードなし")
            else:
                print(" | データなし")

        except Exception as e:
            print(f" | エラー: {e}")
            continue

    return all_trades, stock_results

def main():
    print("=" * 80)
    print("全セクター詳細分析")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()} (6ヶ月)")
    print(f"セクター数: {len(SECTOR_STOCKS)}")
    print(f"総銘柄数: {sum(len(stocks) for stocks in SECTOR_STOCKS.values())}")
    print(f"\nパラメータ:")
    print(f"  - レンジ: 09:05-09:15")
    print(f"  - エントリー: 09:15-10:00")
    print(f"  - 利益目標: +4.0%")
    print(f"  - 損切り: -0.5%")
    print(f"  - 強制決済: 15:00")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    all_trades = []
    all_stock_results = []

    # 各セクターを分析
    for sector_name, stocks in SECTOR_STOCKS.items():
        sector_trades, sector_results = analyze_sector(client, sector_name, stocks)
        all_trades.extend(sector_trades)
        all_stock_results.extend(sector_results)

    client.disconnect()

    # 結果を保存
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df.to_csv('results/optimization/all_sectors_trades.csv', index=False, encoding='utf-8-sig')

    if all_stock_results:
        stocks_df = pd.DataFrame(all_stock_results)
        stocks_df.to_csv('results/optimization/all_sectors_summary.csv', index=False, encoding='utf-8-sig')

    # 詳細分析
    print(f"\n{'='*80}")
    print("セクター別総合分析")
    print(f"{'='*80}\n")

    if all_stock_results:
        stocks_df = pd.DataFrame(all_stock_results)

        # セクター別集計
        sector_summary = stocks_df.groupby('sector').agg({
            'trades': 'sum',
            'pnl': 'sum',
            'return': 'mean',
            'win_rate': 'mean',
            'avg_pnl': 'mean',
            'profit_factor': 'mean',
        }).round(2)

        sector_summary['total_return'] = sector_summary['pnl'] / (PARAMS['initial_capital'] * stocks_df.groupby('sector').size()) * 100
        sector_summary = sector_summary.sort_values('pnl', ascending=False)

        print("■ セクター別ランキング（総損益順）")
        print(f"{'順位':<6s}{'セクター':<20s}{'総損益':<15s}{'リターン':<12s}{'トレード':<10s}{'勝率':<10s}{'損益レシオ':<12s}")
        print("-" * 90)

        for rank, (sector, row) in enumerate(sector_summary.iterrows(), 1):
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
            print(f"{emoji}{rank:<4d}{sector:<20s}{row['pnl']:>13,.0f}円  {row['total_return']:>9.2f}%  {row['trades']:>8.0f}回  {row['win_rate']:>8.1f}%  {row['profit_factor']:>10.2f}")

        # トップ3セクターの詳細
        print(f"\n■ トップ3セクターの詳細")

        for rank, (sector, row) in enumerate(sector_summary.head(3).iterrows(), 1):
            print(f"\n【{rank}位】{sector}セクター")
            print(f"  総損益: {row['pnl']:+,.0f}円 ({row['total_return']:+.2f}%)")
            print(f"  総トレード: {row['trades']:.0f}回")
            print(f"  平均勝率: {row['win_rate']:.1f}%")
            print(f"  平均損益: {row['avg_pnl']:+,.0f}円")
            print(f"  損益レシオ: {row['profit_factor']:.2f}")

            # セクター内の銘柄別
            sector_stocks = stocks_df[stocks_df['sector'] == sector].sort_values('pnl', ascending=False)
            print(f"\n  銘柄別:")
            for _, stock in sector_stocks.iterrows():
                print(f"    {stock['name']:20s}: {stock['pnl']:>12,.0f}円 ({stock['return']*100:>6.2f}%), 勝率{stock['win_rate']:>5.1f}%")

        # ワースト3セクター
        print(f"\n■ ワースト3セクター")

        for rank, (sector, row) in enumerate(sector_summary.tail(3).iloc[::-1].iterrows(), 1):
            print(f"\n【ワースト{rank}】{sector}セクター")
            print(f"  総損益: {row['pnl']:+,.0f}円 ({row['total_return']:+.2f}%)")
            print(f"  総トレード: {row['trades']:.0f}回")
            print(f"  平均勝率: {row['win_rate']:.1f}%")

        # 個別銘柄トップ10
        print(f"\n■ 個別銘柄トップ10（全セクター）")
        print(f"{'順位':<6s}{'セクター':<15s}{'銘柄':<20s}{'損益':<15s}{'リターン':<12s}{'勝率':<10s}")
        print("-" * 80)

        top10_stocks = stocks_df.sort_values('pnl', ascending=False).head(10)
        for rank, (_, stock) in enumerate(top10_stocks.iterrows(), 1):
            print(f"{rank:<6d}{stock['sector']:<15s}{stock['name']:<20s}{stock['pnl']:>13,.0f}円  {stock['return']*100:>9.2f}%  {stock['win_rate']:>8.1f}%")

        # 統計的有意性の検証
        print(f"\n■ テクノロジーセクターの優位性検証")

        tech_stocks = stocks_df[stocks_df['sector'] == 'テクノロジー']
        other_stocks = stocks_df[stocks_df['sector'] != 'テクノロジー']

        tech_avg_return = tech_stocks['return'].mean() * 100
        other_avg_return = other_stocks['return'].mean() * 100

        tech_avg_winrate = tech_stocks['win_rate'].mean()
        other_avg_winrate = other_stocks['win_rate'].mean()

        tech_total_pnl = tech_stocks['pnl'].sum()
        other_total_pnl = other_stocks['pnl'].sum()

        print(f"\nテクノロジー:")
        print(f"  平均リターン: {tech_avg_return:.2f}%")
        print(f"  平均勝率: {tech_avg_winrate:.1f}%")
        print(f"  総損益: {tech_total_pnl:+,.0f}円")

        print(f"\nその他セクター:")
        print(f"  平均リターン: {other_avg_return:.2f}%")
        print(f"  平均勝率: {other_avg_winrate:.1f}%")
        print(f"  総損益: {other_total_pnl:+,.0f}円")

        print(f"\n差分:")
        print(f"  リターン差: {tech_avg_return - other_avg_return:+.2f}%")
        print(f"  勝率差: {tech_avg_winrate - other_avg_winrate:+.1f}%")

        # 結論
        print(f"\n{'='*80}")
        print("結論")
        print(f"{'='*80}\n")

        top_sector = sector_summary.index[0]
        top_pnl = sector_summary.iloc[0]['pnl']

        if top_sector == 'テクノロジー':
            print(f"✅ テクノロジーセクターが最も優れている")
            print(f"   総損益: {top_pnl:+,.0f}円")
            print(f"   戦略との適合性が最も高い")
        else:
            print(f"❌ テクノロジーより優れたセクターが存在")
            print(f"   最優秀: {top_sector}セクター ({top_pnl:+,.0f}円)")

            tech_rank = list(sector_summary.index).index('テクノロジー') + 1
            print(f"   テクノロジーは第{tech_rank}位")

        # 推奨セクター
        print(f"\n推奨セクター（トップ3）:")
        for rank, sector in enumerate(sector_summary.index[:3], 1):
            pnl = sector_summary.loc[sector, 'pnl']
            ret = sector_summary.loc[sector, 'total_return']
            print(f"  {rank}. {sector}: {pnl:+,.0f}円 ({ret:+.2f}%)")

    else:
        print("データ不足のため分析をスキップ")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
