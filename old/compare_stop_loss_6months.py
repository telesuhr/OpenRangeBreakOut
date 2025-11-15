#!/usr/bin/env python3
"""
6ヶ月間のバックテストで損切り-0.5%と-1%を比較
詳細な分析を実施
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

# 最優秀5銘柄
BEST_STOCKS = [
    ('6762.T', 'TDK'),
    ('9984.T', 'ソフトバンクG'),
    ('6857.T', 'アドバンテスト'),
    ('6752.T', 'パナソニック'),
    ('6758.T', 'ソニーグループ'),
]

# バックテスト期間（6ヶ月 = 約120営業日）
END_DATE = datetime(2025, 11, 12)
START_DATE = datetime(2025, 5, 12)  # 6ヶ月前

# 共通パラメータ
BASE_PARAMS = {
    'initial_capital': 10000000,
    'commission_rate': 0.001,
    'range_start': jst_to_utc_time('09:05'),
    'range_end': jst_to_utc_time('09:15'),
    'entry_start': jst_to_utc_time('09:15'),
    'entry_end': jst_to_utc_time('10:00'),
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,  # 4.0%
}

def run_backtest_with_stop_loss(client, stop_loss_value, label):
    """指定された損切り値でバックテストを実行"""
    print(f"\n{'='*80}")
    print(f"{label}: 損切り = {stop_loss_value*100:.1f}%")
    print(f"{'='*80}")

    params = BASE_PARAMS.copy()
    params['stop_loss'] = stop_loss_value

    all_trades = []

    for idx, (symbol, name) in enumerate(BEST_STOCKS, 1):
        print(f"[{idx}/{len(BEST_STOCKS)}] {name:20s} ({symbol})", end='', flush=True)

        try:
            engine = BacktestEngine(**params)
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
                    win_count = (trades_data['pnl'] > 0).sum()

                    print(f" | {num_trades}トレード, {total_pnl:+,.0f}円, 勝率{win_count}/{num_trades}")

                    # データ保存
                    for _, trade in trades_data.iterrows():
                        trade_dict = trade.to_dict()
                        trade_dict['symbol'] = symbol
                        trade_dict['stock_name'] = name
                        all_trades.append(trade_dict)
                else:
                    print(" | トレードなし")
            else:
                print(" | データなし")

        except Exception as e:
            print(f" | エラー: {e}")
            continue

    return pd.DataFrame(all_trades) if all_trades else pd.DataFrame()

def analyze_results(df_05, df_10):
    """2つの結果を詳細に比較分析"""
    print(f"\n{'='*80}")
    print("詳細比較分析")
    print(f"{'='*80}\n")

    # 基本統計
    print("■ 基本統計")
    print(f"{'項目':<30s} | 損切り-0.5% | 損切り-1.0% | 差分")
    print("-" * 80)

    total_trades_05 = len(df_05)
    total_trades_10 = len(df_10)
    print(f"{'総トレード数':<30s} | {total_trades_05:>12d} | {total_trades_10:>12d} | {total_trades_10-total_trades_05:>+12d}")

    total_pnl_05 = df_05['pnl'].sum()
    total_pnl_10 = df_10['pnl'].sum()
    print(f"{'総損益（円）':<30s} | {total_pnl_05:>12,.0f} | {total_pnl_10:>12,.0f} | {total_pnl_10-total_pnl_05:>+12,.0f}")

    total_return_05 = total_pnl_05 / (10000000 * len(BEST_STOCKS))
    total_return_10 = total_pnl_10 / (10000000 * len(BEST_STOCKS))
    print(f"{'総リターン（%）':<30s} | {total_return_05*100:>12.2f} | {total_return_10*100:>12.2f} | {(total_return_10-total_return_05)*100:>+12.2f}")

    win_rate_05 = (df_05['pnl'] > 0).sum() / len(df_05) * 100 if len(df_05) > 0 else 0
    win_rate_10 = (df_10['pnl'] > 0).sum() / len(df_10) * 100 if len(df_10) > 0 else 0
    print(f"{'勝率（%）':<30s} | {win_rate_05:>12.1f} | {win_rate_10:>12.1f} | {win_rate_10-win_rate_05:>+12.1f}")

    avg_pnl_05 = df_05['pnl'].mean() if len(df_05) > 0 else 0
    avg_pnl_10 = df_10['pnl'].mean() if len(df_10) > 0 else 0
    print(f"{'平均損益（円）':<30s} | {avg_pnl_05:>12,.0f} | {avg_pnl_10:>12,.0f} | {avg_pnl_10-avg_pnl_05:>+12,.0f}")

    # 損切り分析
    print(f"\n■ 損切り分析")
    print(f"{'項目':<30s} | 損切り-0.5% | 損切り-1.0% | 差分")
    print("-" * 80)

    loss_trades_05 = len(df_05[df_05['reason'] == 'loss'])
    loss_trades_10 = len(df_10[df_10['reason'] == 'loss'])
    print(f"{'損切り執行回数':<30s} | {loss_trades_05:>12d} | {loss_trades_10:>12d} | {loss_trades_10-loss_trades_05:>+12d}")

    loss_rate_05 = loss_trades_05 / len(df_05) * 100 if len(df_05) > 0 else 0
    loss_rate_10 = loss_trades_10 / len(df_10) * 100 if len(df_10) > 0 else 0
    print(f"{'損切り率（%）':<30s} | {loss_rate_05:>12.1f} | {loss_rate_10:>12.1f} | {loss_rate_10-loss_rate_05:>+12.1f}")

    avg_loss_05 = df_05[df_05['pnl'] < 0]['pnl'].mean() if len(df_05[df_05['pnl'] < 0]) > 0 else 0
    avg_loss_10 = df_10[df_10['pnl'] < 0]['pnl'].mean() if len(df_10[df_10['pnl'] < 0]) > 0 else 0
    print(f"{'平均損失（円）':<30s} | {avg_loss_05:>12,.0f} | {avg_loss_10:>12,.0f} | {avg_loss_10-avg_loss_05:>+12,.0f}")

    max_loss_05 = df_05['pnl'].min() if len(df_05) > 0 else 0
    max_loss_10 = df_10['pnl'].min() if len(df_10) > 0 else 0
    print(f"{'最大損失（円）':<30s} | {max_loss_05:>12,.0f} | {max_loss_10:>12,.0f} | {max_loss_10-max_loss_05:>+12,.0f}")

    # 利益分析
    print(f"\n■ 利益分析")
    print(f"{'項目':<30s} | 損切り-0.5% | 損切り-1.0% | 差分")
    print("-" * 80)

    win_trades_05 = len(df_05[df_05['pnl'] > 0])
    win_trades_10 = len(df_10[df_10['pnl'] > 0])
    print(f"{'勝ちトレード数':<30s} | {win_trades_05:>12d} | {win_trades_10:>12d} | {win_trades_10-win_trades_05:>+12d}")

    avg_win_05 = df_05[df_05['pnl'] > 0]['pnl'].mean() if len(df_05[df_05['pnl'] > 0]) > 0 else 0
    avg_win_10 = df_10[df_10['pnl'] > 0]['pnl'].mean() if len(df_10[df_10['pnl'] > 0]) > 0 else 0
    print(f"{'平均利益（円）':<30s} | {avg_win_05:>12,.0f} | {avg_win_10:>12,.0f} | {avg_win_10-avg_win_05:>+12,.0f}")

    max_win_05 = df_05['pnl'].max() if len(df_05) > 0 else 0
    max_win_10 = df_10['pnl'].max() if len(df_10) > 0 else 0
    print(f"{'最大利益（円）':<30s} | {max_win_05:>12,.0f} | {max_win_10:>12,.0f} | {max_win_10-max_win_05:>+12,.0f}")

    # 損益レシオ
    if avg_loss_05 != 0:
        profit_factor_05 = abs(avg_win_05 / avg_loss_05)
    else:
        profit_factor_05 = 0

    if avg_loss_10 != 0:
        profit_factor_10 = abs(avg_win_10 / avg_loss_10)
    else:
        profit_factor_10 = 0

    print(f"{'損益レシオ':<30s} | {profit_factor_05:>12.2f} | {profit_factor_10:>12.2f} | {profit_factor_10-profit_factor_05:>+12.2f}")

    # イグジット理由別分析
    print(f"\n■ イグジット理由別")
    print(f"{'理由':<30s} | 損切り-0.5% | 損切り-1.0% | 差分")
    print("-" * 80)

    for reason in ['loss', 'target', 'day_end']:
        count_05 = len(df_05[df_05['reason'] == reason])
        count_10 = len(df_10[df_10['reason'] == reason])
        pct_05 = count_05 / len(df_05) * 100 if len(df_05) > 0 else 0
        pct_10 = count_10 / len(df_10) * 100 if len(df_10) > 0 else 0

        reason_ja = {'loss': '損切り', 'target': '利益目標', 'day_end': '引け決済'}[reason]
        print(f"{reason_ja:<30s} | {count_05:>7d} ({pct_05:>4.1f}%) | {count_10:>7d} ({pct_10:>4.1f}%) | {count_10-count_05:>+12d}")

    # 銘柄別分析
    print(f"\n■ 銘柄別損益")
    print(f"{'銘柄':<30s} | 損切り-0.5% | 損切り-1.0% | 差分")
    print("-" * 80)

    for symbol, name in BEST_STOCKS:
        pnl_05 = df_05[df_05['symbol'] == symbol]['pnl'].sum()
        pnl_10 = df_10[df_10['symbol'] == symbol]['pnl'].sum()

        print(f"{name:<30s} | {pnl_05:>12,.0f} | {pnl_10:>12,.0f} | {pnl_10-pnl_05:>+12,.0f}")

    # 月別分析
    print(f"\n■ 月別損益")
    df_05['month'] = pd.to_datetime(df_05['entry_time']).dt.to_period('M')
    df_10['month'] = pd.to_datetime(df_10['entry_time']).dt.to_period('M')

    monthly_05 = df_05.groupby('month')['pnl'].sum()
    monthly_10 = df_10.groupby('month')['pnl'].sum()

    all_months = sorted(set(monthly_05.index) | set(monthly_10.index))

    print(f"{'月':<30s} | 損切り-0.5% | 損切り-1.0% | 差分")
    print("-" * 80)

    for month in all_months:
        pnl_05 = monthly_05.get(month, 0)
        pnl_10 = monthly_10.get(month, 0)
        print(f"{str(month):<30s} | {pnl_05:>12,.0f} | {pnl_10:>12,.0f} | {pnl_10-pnl_05:>+12,.0f}")

    # 結論
    print(f"\n{'='*80}")
    print("結論")
    print(f"{'='*80}\n")

    diff_pnl = total_pnl_10 - total_pnl_05
    diff_pct = (diff_pnl / total_pnl_05 * 100) if total_pnl_05 != 0 else 0

    if diff_pnl > 0:
        print(f"✅ 損切り-1.0%が優れている")
        print(f"   損益改善: {diff_pnl:+,.0f}円 ({diff_pct:+.1f}%)")
        print(f"   損切り回数減少: {loss_trades_05 - loss_trades_10}回")
    else:
        print(f"❌ 損切り-0.5%が優れている")
        print(f"   損益悪化: {diff_pnl:+,.0f}円 ({diff_pct:+.1f}%)")
        print(f"   損切り回数増加: {loss_trades_10 - loss_trades_05}回")

    print(f"\n推奨: 損切り = {'-1.0%' if diff_pnl > 0 else '-0.5%'}")

def main():
    print("=" * 80)
    print("6ヶ月間バックテスト: 損切り-0.5% vs -1.0%")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()}")
    print(f"対象銘柄: {len(BEST_STOCKS)}銘柄")
    print(f"その他のパラメータ:")
    print(f"  - 利益目標: +4.0%")
    print(f"  - レンジ: 09:05-09:15")
    print(f"  - エントリー: 09:15-10:00")
    print(f"  - 強制決済: 15:00")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 損切り-0.5%でバックテスト
    df_05 = run_backtest_with_stop_loss(client, 0.005, "ケース1")

    # 損切り-1.0%でバックテスト
    df_10 = run_backtest_with_stop_loss(client, 0.010, "ケース2")

    client.disconnect()

    # 結果を保存
    if not df_05.empty:
        df_05.to_csv('results/optimization/stop_loss_05_6months.csv', index=False, encoding='utf-8-sig')
    if not df_10.empty:
        df_10.to_csv('results/optimization/stop_loss_10_6months.csv', index=False, encoding='utf-8-sig')

    # 詳細分析
    if not df_05.empty and not df_10.empty:
        analyze_results(df_05, df_10)
    else:
        print("\n⚠️ データ不足のため比較分析をスキップ")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
