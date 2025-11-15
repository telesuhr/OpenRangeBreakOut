#!/usr/bin/env python3
"""
最適化済みパラメータで様々な銘柄をバックテスト
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

# テスト銘柄（トップ10を除く様々なセクター）
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

# バックテスト期間（6ヶ月）
END_DATE = datetime(2025, 11, 12)
START_DATE = datetime(2025, 5, 12)

# 最適化済みパラメータ
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
    print("最適化済みパラメータで様々な銘柄をバックテスト")
    print("=" * 80)
    print(f"\n期間: {START_DATE.date()} ～ {END_DATE.date()} (6ヶ月)")
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
    df = pd.DataFrame(results)

    # 総損益でソート
    df = df.sort_values('total_pnl', ascending=False).reset_index(drop=True)

    print(f"\n{'='*80}")
    print("バックテスト結果サマリー（総損益順）")
    print(f"{'='*80}\n")

    # トップ20を表示
    print("【トップ20銘柄】")
    print(df.head(20).to_string(index=False))

    # ワースト10を表示
    print(f"\n\n【ワースト10銘柄】")
    print(df.tail(10).to_string(index=False))

    # 統計サマリー
    print(f"\n{'='*80}")
    print("全体統計")
    print(f"{'='*80}\n")

    total_tested = len(df)
    profitable = (df['total_pnl'] > 0).sum()
    unprofitable = (df['total_pnl'] < 0).sum()

    print(f"テスト銘柄数: {total_tested}")
    print(f"利益銘柄数: {profitable} ({profitable/total_tested*100:.1f}%)")
    print(f"損失銘柄数: {unprofitable} ({unprofitable/total_tested*100:.1f}%)")
    print(f"\n平均損益: {df['total_pnl'].mean():+,.0f}円")
    print(f"平均リターン: {df['total_return'].mean():+.2f}%")
    print(f"平均勝率: {df['win_rate'].mean():.1f}%")
    print(f"平均損益レシオ: {df['profit_factor'].mean():.2f}")

    # CSV保存
    df.to_csv('results/optimization/various_stocks_optimized.csv', index=False, encoding='utf-8-sig')
    print(f"\n結果を results/optimization/various_stocks_optimized.csv に保存しました")

    # 可視化
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    # 1. トップ20 総損益
    ax1 = axes[0, 0]
    top20 = df.head(20)
    colors = ['green' if pnl > 0 else 'red' for pnl in top20['total_pnl']]
    ax1.barh(range(len(top20)), top20['total_pnl'], color=colors, alpha=0.7, edgecolor='black')
    ax1.set_yticks(range(len(top20)))
    ax1.set_yticklabels(top20['name'], fontsize=9)
    ax1.set_xlabel('総損益（円）', fontsize=12)
    ax1.set_title('トップ20銘柄 総損益', fontsize=14, fontweight='bold')
    ax1.axvline(x=0, color='black', linewidth=1)
    ax1.grid(True, axis='x', alpha=0.3)
    ax1.invert_yaxis()

    # 数値ラベル
    for i, pnl in enumerate(top20['total_pnl']):
        x_pos = pnl + (50000 if pnl > 0 else -50000)
        ha = 'left' if pnl > 0 else 'right'
        ax1.text(x_pos, i, f'{pnl:+,.0f}円', va='center', ha=ha, fontsize=8)

    # 2. 勝率 vs 総損益（散布図）
    ax2 = axes[0, 1]
    colors = ['green' if pnl > 0 else 'red' for pnl in df['total_pnl']]
    ax2.scatter(df['win_rate'], df['total_pnl'], c=colors, alpha=0.6, s=100, edgecolors='black')
    ax2.set_xlabel('勝率（%）', fontsize=12)
    ax2.set_ylabel('総損益（円）', fontsize=12)
    ax2.set_title('勝率 vs 総損益', fontsize=14, fontweight='bold')
    ax2.axhline(y=0, color='black', linewidth=1, linestyle='--')
    ax2.grid(True, alpha=0.3)

    # 3. 損益レシオ vs 総損益（散布図）
    ax3 = axes[1, 0]
    colors = ['green' if pnl > 0 else 'red' for pnl in df['total_pnl']]
    ax3.scatter(df['profit_factor'], df['total_pnl'], c=colors, alpha=0.6, s=100, edgecolors='black')
    ax3.set_xlabel('損益レシオ', fontsize=12)
    ax3.set_ylabel('総損益（円）', fontsize=12)
    ax3.set_title('損益レシオ vs 総損益', fontsize=14, fontweight='bold')
    ax3.axhline(y=0, color='black', linewidth=1, linestyle='--')
    ax3.axvline(x=1.0, color='blue', linewidth=1, linestyle='--', alpha=0.5)
    ax3.grid(True, alpha=0.3)

    # 4. 損益分布ヒストグラム
    ax4 = axes[1, 1]
    ax4.hist(df['total_pnl'], bins=30, color='steelblue', alpha=0.7, edgecolor='black')
    ax4.set_xlabel('総損益（円）', fontsize=12)
    ax4.set_ylabel('銘柄数', fontsize=12)
    ax4.set_title('総損益の分布', fontsize=14, fontweight='bold')
    ax4.axvline(x=0, color='red', linewidth=2, linestyle='--', label='損益ゼロ')
    ax4.axvline(x=df['total_pnl'].mean(), color='green', linewidth=2, linestyle='--',
                label=f'平均: {df["total_pnl"].mean():+,.0f}円')
    ax4.legend()
    ax4.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/optimization/various_stocks_optimized.png', dpi=200, bbox_inches='tight')

    print(f"可視化を results/optimization/various_stocks_optimized.png に保存しました")

    print(f"\n{'='*80}")
    print("完了")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
