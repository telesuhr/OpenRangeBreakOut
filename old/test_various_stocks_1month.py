#!/usr/bin/env python3
"""
最適化済みパラメータで様々な銘柄をバックテスト（直近1ヶ月）
損切り: 0.75%
エントリー: 09:15-11:00
利確: 4.0%
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time
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

# テスト銘柄（6ヶ月テストと同じ）
TEST_STOCKS = [
    # ハイテク・半導体
    ('6503.T', 'ソニー'),
    ('6758.T', 'キーエンス'),
    ('8035.T', '東京エレクトロン'),
    ('6902.T', 'デンソー'),
    ('6861.T', 'キーコム'),

    # 商社
    ('8058.T', '三菱商事'),
    ('8031.T', '三井物産'),
    ('8001.T', '伊藤忠商事'),
    ('8053.T', '住友商事'),

    # 自動車
    ('7203.T', 'トヨタ自動車'),
    ('7267.T', 'ホンダ'),
    ('7201.T', '日産自動車'),
    ('7269.T', 'スズキ'),

    # 金融
    ('8306.T', '三菱UFJ'),
    ('8316.T', '三井住友FG'),
    ('8411.T', 'みずほFG'),

    # 通信
    ('9433.T', 'KDDI'),
    ('9434.T', 'ソフトバンク'),
    ('9613.T', 'NTTデータ'),

    # 素材・化学
    ('4063.T', '信越化学'),
    ('4452.T', '花王'),
    ('4901.T', '富士フイルム'),
    ('3407.T', '旭化成'),

    # 鉄鋼・非鉄
    ('5401.T', '新日鐵住金'),
    ('5411.T', 'JFE'),
    ('5332.T', 'TOTO'),

    # エネルギー・電力
    ('1605.T', 'INPEX'),
    ('5020.T', 'JXTGホールディングス'),
    ('9503.T', '関西電力'),

    # 不動産
    ('8802.T', '三菱地所'),
    ('8801.T', '三井不動産'),

    # 小売
    ('3382.T', 'セブン&アイ'),
    ('8267.T', 'イオン'),
    ('9983.T', 'ファーストリテイリング'),

    # 食品・飲料
    ('2502.T', 'アサヒグループ'),
    ('2503.T', 'キリンHD'),
    ('2801.T', 'キッコーマン'),

    # 医薬品
    ('4502.T', '武田薬品'),
    ('4503.T', 'アステラス製薬'),
    ('4568.T', '第一三共'),
]

# バックテスト期間（直近1ヶ月）
END_DATE = datetime(2025, 11, 12)
START_DATE = datetime(2025, 10, 12)

# 最適化済みパラメータ（6ヶ月テストと同じ）
OPTIMIZED_PARAMS = {
    'initial_capital': 10000000,
    'commission_rate': 0.001,
    'range_start': jst_to_utc_time('09:05'),
    'range_end': jst_to_utc_time('09:15'),
    'entry_start': jst_to_utc_time('09:15'),
    'entry_end': jst_to_utc_time('11:00'),  # 最適化: 11:00まで
    'force_exit_time': jst_to_utc_time('15:00'),
    'profit_target': 0.04,   # 4.0%
    'stop_loss': 0.0075,     # 最適化: 0.75%
}

def run_backtest(client, symbol, name):
    """単一銘柄のバックテスト実行"""
    try:
        engine = BacktestEngine(**OPTIMIZED_PARAMS)
        results = engine.run_backtest(
            client=client,
            symbols=[symbol],
            start_date=START_DATE,
            end_date=END_DATE
        )

        if 'trades' in results and results['trades'] is not None:
            trades_data = results['trades']

            if isinstance(trades_data, pd.DataFrame) and not trades_data.empty:
                total_pnl = trades_data['pnl'].sum()
                num_trades = len(trades_data)
                win_count = (trades_data['pnl'] > 0).sum()
                win_rate = win_count / num_trades * 100 if num_trades > 0 else 0

                # 損益レシオ
                wins = trades_data[trades_data['pnl'] > 0]['pnl']
                losses = trades_data[trades_data['pnl'] < 0]['pnl']
                avg_win = wins.mean() if len(wins) > 0 else 0
                avg_loss = losses.mean() if len(losses) > 0 else 0
                profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

                return {
                    'symbol': symbol,
                    'name': name,
                    'total_pnl': total_pnl,
                    'total_return': total_pnl / OPTIMIZED_PARAMS['initial_capital'] * 100,
                    'num_trades': num_trades,
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                }

        return None

    except Exception as e:
        print(f"  エラー: {e}")
        return None

def main():
    print("=" * 80)
    print("最適化済みパラメータで様々な銘柄をバックテスト（直近1ヶ月）")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()} (1ヶ月)")
    print(f"テスト銘柄数: {len(TEST_STOCKS)}")
    print(f"\n【最適化済みパラメータ】")
    print(f"  損切り: 0.75%")
    print(f"  エントリー時間: 09:15-11:00")
    print(f"  利確目標: 4.0%")
    print(f"  初期資金: 1,000万円")

    # APIクライアント
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    results = []

    for idx, (symbol, name) in enumerate(TEST_STOCKS, 1):
        print(f"\n[{idx}/{len(TEST_STOCKS)}] {name:20s} ({symbol})", end='', flush=True)

        result = run_backtest(client, symbol, name)

        if result:
            print(f" | {result['num_trades']}トレード, {result['total_pnl']:+,.0f}円 ({result['win_rate']:.1f}%)")
            results.append(result)
        else:
            print(" | データなし")

    client.disconnect()

    if not results:
        print("\n有効な結果がありませんでした")
        return

    # 結果をDataFrameに変換
    df_1month = pd.DataFrame(results)

    # 総損益でソート
    df_1month = df_1month.sort_values('total_pnl', ascending=False).reset_index(drop=True)

    # 6ヶ月の結果を読み込み
    df_6month = pd.read_csv('results/optimization/various_stocks_optimized.csv')

    print(f"\n{'='*80}")
    print("バックテスト結果比較（1ヶ月 vs 6ヶ月）")
    print(f"{'='*80}\n")

    # トップ20を表示（1ヶ月）
    print("【直近1ヶ月 トップ20銘柄】")
    print(df_1month.head(20).to_string(index=False))

    # 統計サマリー比較
    print(f"\n{'='*80}")
    print("全体統計比較")
    print(f"{'='*80}\n")

    print(f"{'':30s} {'1ヶ月':>15s} {'6ヶ月':>15s} {'差分':>15s}")
    print("-" * 80)

    # 比較指標
    metrics = [
        ('テスト銘柄数', len(df_1month), len(df_6month)),
        ('利益銘柄数', (df_1month['total_pnl'] > 0).sum(), (df_6month['total_pnl'] > 0).sum()),
        ('損失銘柄数', (df_1month['total_pnl'] < 0).sum(), (df_6month['total_pnl'] < 0).sum()),
    ]

    for label, val_1m, val_6m in metrics:
        diff = val_1m - val_6m
        print(f"{label:30s} {val_1m:>15,} {val_6m:>15,} {diff:>+15,}")

    print()

    financial_metrics = [
        ('平均損益（円）', df_1month['total_pnl'].mean(), df_6month['total_pnl'].mean()),
        ('平均リターン（%）', df_1month['total_return'].mean(), df_6month['total_return'].mean()),
        ('平均勝率（%）', df_1month['win_rate'].mean(), df_6month['win_rate'].mean()),
        ('平均損益レシオ', df_1month['profit_factor'].mean(), df_6month['profit_factor'].mean()),
    ]

    for label, val_1m, val_6m in financial_metrics:
        diff = val_1m - val_6m
        if '（円）' in label:
            print(f"{label:30s} {val_1m:>15,.0f} {val_6m:>15,.0f} {diff:>+15,.0f}")
        else:
            print(f"{label:30s} {val_1m:>15.2f} {val_6m:>15.2f} {diff:>+15.2f}")

    # CSV保存
    df_1month.to_csv('results/optimization/various_stocks_1month.csv', index=False, encoding='utf-8-sig')
    print(f"\n結果を results/optimization/various_stocks_1month.csv に保存しました")

    # 可視化
    fig, axes = plt.subplots(2, 3, figsize=(24, 12))

    # 1. 1ヶ月 トップ20 総損益
    ax1 = axes[0, 0]
    top20_1m = df_1month.head(20)
    colors = ['green' if pnl > 0 else 'red' for pnl in top20_1m['total_pnl']]
    ax1.barh(range(len(top20_1m)), top20_1m['total_pnl'], color=colors, alpha=0.7, edgecolor='black')
    ax1.set_yticks(range(len(top20_1m)))
    ax1.set_yticklabels(top20_1m['name'], fontsize=9)
    ax1.set_xlabel('総損益（円）', fontsize=12)
    ax1.set_title('1ヶ月 トップ20銘柄 総損益', fontsize=14, fontweight='bold')
    ax1.axvline(x=0, color='black', linewidth=1)
    ax1.grid(True, axis='x', alpha=0.3)
    ax1.invert_yaxis()

    # 2. 6ヶ月 トップ20 総損益
    ax2 = axes[0, 1]
    top20_6m = df_6month.head(20)
    colors = ['green' if pnl > 0 else 'red' for pnl in top20_6m['total_pnl']]
    ax2.barh(range(len(top20_6m)), top20_6m['total_pnl'], color=colors, alpha=0.7, edgecolor='black')
    ax2.set_yticks(range(len(top20_6m)))
    ax2.set_yticklabels(top20_6m['name'], fontsize=9)
    ax2.set_xlabel('総損益（円）', fontsize=12)
    ax2.set_title('6ヶ月 トップ20銘柄 総損益', fontsize=14, fontweight='bold')
    ax2.axvline(x=0, color='black', linewidth=1)
    ax2.grid(True, axis='x', alpha=0.3)
    ax2.invert_yaxis()

    # 3. 平均損益の比較
    ax3 = axes[0, 2]
    comparison_data = {
        '平均損益': [df_1month['total_pnl'].mean(), df_6month['total_pnl'].mean()],
        '平均リターン': [df_1month['total_return'].mean(), df_6month['total_return'].mean()],
    }
    x = np.arange(len(comparison_data))
    width = 0.35
    ax3.bar(x - width/2, [comparison_data['平均損益'][0], comparison_data['平均リターン'][0]],
            width, label='1ヶ月', color='steelblue', alpha=0.7)
    ax3.bar(x + width/2, [comparison_data['平均損益'][1], comparison_data['平均リターン'][1]],
            width, label='6ヶ月', color='orange', alpha=0.7)
    ax3.set_ylabel('値', fontsize=12)
    ax3.set_title('平均パフォーマンス比較', fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(['平均損益（円）', '平均リターン（%）'])
    ax3.legend()
    ax3.grid(True, axis='y', alpha=0.3)

    # 4. 勝率分布比較
    ax4 = axes[1, 0]
    ax4.hist([df_1month['win_rate'], df_6month['win_rate']], bins=20,
             label=['1ヶ月', '6ヶ月'], color=['steelblue', 'orange'], alpha=0.6, edgecolor='black')
    ax4.set_xlabel('勝率（%）', fontsize=12)
    ax4.set_ylabel('銘柄数', fontsize=12)
    ax4.set_title('勝率分布比較', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, axis='y', alpha=0.3)

    # 5. 損益分布比較
    ax5 = axes[1, 1]
    ax5.hist([df_1month['total_pnl'], df_6month['total_pnl']], bins=20,
             label=['1ヶ月', '6ヶ月'], color=['steelblue', 'orange'], alpha=0.6, edgecolor='black')
    ax5.set_xlabel('総損益（円）', fontsize=12)
    ax5.set_ylabel('銘柄数', fontsize=12)
    ax5.set_title('総損益分布比較', fontsize=14, fontweight='bold')
    ax5.axvline(x=0, color='red', linewidth=2, linestyle='--')
    ax5.legend()
    ax5.grid(True, axis='y', alpha=0.3)

    # 6. 利益・損失銘柄数の比較
    ax6 = axes[1, 2]
    profit_comparison = [
        [(df_1month['total_pnl'] > 0).sum(), (df_1month['total_pnl'] < 0).sum()],
        [(df_6month['total_pnl'] > 0).sum(), (df_6month['total_pnl'] < 0).sum()]
    ]
    x = np.arange(2)
    width = 0.35
    ax6.bar(x - width/2, [profit_comparison[0][0], profit_comparison[0][1]],
            width, label='1ヶ月', color='steelblue', alpha=0.7)
    ax6.bar(x + width/2, [profit_comparison[1][0], profit_comparison[1][1]],
            width, label='6ヶ月', color='orange', alpha=0.7)
    ax6.set_ylabel('銘柄数', fontsize=12)
    ax6.set_title('利益・損失銘柄数比較', fontsize=14, fontweight='bold')
    ax6.set_xticks(x)
    ax6.set_xticklabels(['利益銘柄', '損失銘柄'])
    ax6.legend()
    ax6.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/optimization/various_stocks_1month_comparison.png', dpi=200, bbox_inches='tight')

    print(f"可視化を results/optimization/various_stocks_1month_comparison.png に保存しました")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
