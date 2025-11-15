#!/usr/bin/env python3
"""
非鉄金属セクター詳細分析
最近強い非鉄金属セクターでOpen Range Breakout戦略の有効性を検証
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

# 非鉄金属セクター銘柄
NONFERROUS_METALS_STOCKS = [
    ('5801.T', '古河電気工業'),
    ('5803.T', 'フジクラ'),
    ('5706.T', '三井金属鉱業'),
    ('5711.T', '三菱マテリアル'),
    ('5802.T', '住友電気工業'),
    ('5713.T', '住友金属鉱山'),
    ('5714.T', 'DOWAホールディングス'),
]

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

def main():
    print("=" * 80)
    print("非鉄金属セクター詳細分析")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()} (6ヶ月)")
    print(f"銘柄数: {len(NONFERROUS_METALS_STOCKS)}")
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
    stock_results = []

    print(f"\n{'='*80}")
    print("非鉄金属セクター")
    print(f"{'='*80}")
    print("-" * 80)

    for idx, (symbol, name) in enumerate(NONFERROUS_METALS_STOCKS, 1):
        print(f"[{idx}/{len(NONFERROUS_METALS_STOCKS)}] {name:20s} ({symbol})", end='', flush=True)

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
                        trade_dict['sector'] = '非鉄金属'
                        all_trades.append(trade_dict)

                    stock_results.append({
                        'sector': '非鉄金属',
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

    client.disconnect()

    # 結果を保存
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df.to_csv('results/optimization/nonferrous_metals_trades.csv', index=False, encoding='utf-8-sig')

    if stock_results:
        stocks_df = pd.DataFrame(stock_results)
        stocks_df.to_csv('results/optimization/nonferrous_metals_summary.csv', index=False, encoding='utf-8-sig')

    # 詳細分析
    print(f"\n{'='*80}")
    print("非鉄金属セクター総合分析")
    print(f"{'='*80}\n")

    if stock_results:
        stocks_df = pd.DataFrame(stock_results)

        # セクター合計
        total_trades = stocks_df['trades'].sum()
        total_pnl = stocks_df['pnl'].sum()
        avg_return = stocks_df['return'].mean() * 100
        avg_win_rate = stocks_df['win_rate'].mean()
        avg_profit_factor = stocks_df['profit_factor'].mean()

        print("■ 非鉄金属セクター サマリー")
        print(f"  総損益: {total_pnl:+,.0f}円")
        print(f"  平均リターン: {avg_return:.2f}%")
        print(f"  総トレード: {total_trades:.0f}回")
        print(f"  平均勝率: {avg_win_rate:.1f}%")
        print(f"  平均損益レシオ: {avg_profit_factor:.2f}")

        # 銘柄別ランキング
        print(f"\n■ 銘柄別パフォーマンス（損益順）")
        print(f"{'順位':<6s}{'銘柄':<20s}{'損益':<15s}{'リターン':<12s}{'トレード':<10s}{'勝率':<10s}{'損益レシオ':<12s}")
        print("-" * 80)

        sorted_stocks = stocks_df.sort_values('pnl', ascending=False)
        for rank, (_, stock) in enumerate(sorted_stocks.iterrows(), 1):
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
            print(f"{emoji}{rank:<4d}{stock['name']:<20s}{stock['pnl']:>13,.0f}円  "
                  f"{stock['return']*100:>9.2f}%  {stock['trades']:>8.0f}回  "
                  f"{stock['win_rate']:>8.1f}%  {stock['profit_factor']:>10.2f}")

        # 他セクターとの比較
        print(f"\n■ 他セクターとの比較")
        print("\n過去の分析結果:")
        print(f"  テクノロジー: +476万円 (リターン9.52%, 勝率35.6%, 損益レシオ2.23)")
        print(f"  通信:        +394万円 (リターン13.14%, 勝率42.6%, 損益レシオ1.81)")
        print(f"  素材・化学:   +245万円 (リターン4.91%, 勝率43.4%, 損益レシオ1.53)")

        print(f"\n非鉄金属:")
        print(f"  総損益:      {total_pnl:+,.0f}円")
        print(f"  平均リターン: {avg_return:.2f}%")
        print(f"  平均勝率:     {avg_win_rate:.1f}%")
        print(f"  損益レシオ:   {avg_profit_factor:.2f}")

        # ランキング判定
        print(f"\n■ 結論")
        print("=" * 80)

        if total_pnl > 4760000:
            print("✅ 非鉄金属セクターはテクノロジーを超える最高パフォーマンス！")
        elif total_pnl > 3941000:
            print("✅ 非鉄金属セクターは通信に次ぐ第2位のパフォーマンス")
        elif total_pnl > 2452000:
            print("✅ 非鉄金属セクターは素材・化学を超える第3位のパフォーマンス")
        elif total_pnl > 0:
            print("⭕ 非鉄金属セクターはプラスだが、トップ3には及ばない")
        else:
            print("❌ 非鉄金属セクターは損失")

        print(f"\n総合評価: {total_pnl:+,.0f}円 ({avg_return:+.2f}%)")

        if avg_profit_factor > 2.0:
            print("損益レシオが優秀（2.0超）- 損小利大を実現")
        elif avg_profit_factor > 1.5:
            print("損益レシオは良好（1.5超）")

    else:
        print("データ不足のため分析をスキップ")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
