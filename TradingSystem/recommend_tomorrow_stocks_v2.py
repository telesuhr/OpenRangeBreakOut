#!/usr/bin/env python3
"""
明日のエントリー推奨銘柄分析 v2
- より実用的な基準で銘柄選定
- 全銘柄の統計も表示
"""
import pandas as pd
from pathlib import Path
import numpy as np

def recommend_tomorrow_stocks():
    """明日エントリーすべき銘柄を推奨"""

    output_dir = Path("Output/20251119_221548")

    print("\n" + "=" * 80)
    print("明日（2025/11/20）のエントリー推奨銘柄分析 v2")
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
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if len(df[df['pnl'] > 0]) > 0 else 0
        avg_loss = df[df['pnl'] < 0]['pnl'].mean() if len(df[df['pnl'] < 0]) > 0 else 0

        # リスクリターン比（プロフィットファクター）
        total_profit = df[df['pnl'] > 0]['pnl'].sum()
        total_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        symbol_stats[symbol] = {
            'total_pnl': total_pnl,
            'trade_count': len(df),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'risk_reward': abs(avg_win / avg_loss) if avg_loss != 0 else 0
        }

    if not all_trades:
        print("データなし")
        return

    df_all = pd.concat(all_trades, ignore_index=True)

    print(f"\n【基本統計】")
    print(f"銘柄数: {len(symbol_stats)}")
    print(f"総取引: {len(df_all)}回")

    # 全銘柄の統計サマリー
    stats_df = pd.DataFrame(symbol_stats).T
    print(f"\n【全銘柄統計サマリー】")
    print(f"  平均勝率: {stats_df['win_rate'].mean():.1f}%")
    print(f"  勝率中央値: {stats_df['win_rate'].median():.1f}%")
    print(f"  平均PF: {stats_df['profit_factor'].mean():.2f}")
    print(f"  PF中央値: {stats_df['profit_factor'].median():.2f}")
    print(f"  平均損益/銘柄: {stats_df['total_pnl'].mean():+,.0f}円")

    # プラス/マイナス銘柄
    positive_symbols = len(stats_df[stats_df['total_pnl'] > 0])
    negative_symbols = len(stats_df[stats_df['total_pnl'] < 0])
    print(f"\nプラス銘柄: {positive_symbols}/{len(symbol_stats)} ({positive_symbols/len(symbol_stats)*100:.1f}%)")
    print(f"マイナス銘柄: {negative_symbols}/{len(symbol_stats)} ({negative_symbols/len(symbol_stats)*100:.1f}%)")

    # より現実的な選定基準
    print(f"\n" + "=" * 80)
    print("【推奨銘柄選定基準（現実的基準）】")
    print("=" * 80)
    print("Tier 1（最優先）: 総損益プラス & 勝率45%以上")
    print("Tier 2（推奨）: 総損益プラス & 勝率40%以上")
    print("Tier 3（条件付き）: プロフィットファクター > 1.0")

    tier1 = []
    tier2 = []
    tier3 = []

    for symbol, stats in symbol_stats.items():
        if stats['total_pnl'] > 0 and stats['win_rate'] >= 45:
            tier1.append({'symbol': symbol, **stats, 'tier': 1})
        elif stats['total_pnl'] > 0 and stats['win_rate'] >= 40:
            tier2.append({'symbol': symbol, **stats, 'tier': 2})
        elif stats['profit_factor'] > 1.0:
            tier3.append({'symbol': symbol, **stats, 'tier': 3})

    # ソート（総損益順）
    tier1_df = pd.DataFrame(tier1).sort_values('total_pnl', ascending=False) if tier1 else pd.DataFrame()
    tier2_df = pd.DataFrame(tier2).sort_values('total_pnl', ascending=False) if tier2 else pd.DataFrame()
    tier3_df = pd.DataFrame(tier3).sort_values('profit_factor', ascending=False) if tier3 else pd.DataFrame()

    print(f"\nTier 1銘柄数: {len(tier1_df)}")
    print(f"Tier 2銘柄数: {len(tier2_df)}")
    print(f"Tier 3銘柄数: {len(tier3_df)}")

    # Tier 1の詳細表示
    if len(tier1_df) > 0:
        print(f"\n" + "=" * 80)
        print(f"【Tier 1: 最優先銘柄（総損益プラス & 勝率45%以上）】")
        print("=" * 80)
        print(f"\n{'銘柄':<8} {'勝率':<7} {'PF':<6} {'総損益':<12} {'平均損益':<10} {'取引数':<6}")
        print("-" * 80)

        for idx, row in tier1_df.iterrows():
            print(f"{row['symbol']:<8} {row['win_rate']:>5.1f}% {row['profit_factor']:>5.2f} "
                  f"{row['total_pnl']:>11,.0f}円 {row['avg_pnl']:>9,.0f}円 {int(row['trade_count']):>5}")

    # Tier 2の詳細表示
    if len(tier2_df) > 0:
        print(f"\n" + "=" * 80)
        print(f"【Tier 2: 推奨銘柄（総損益プラス & 勝率40%以上）】")
        print("=" * 80)
        print(f"\n{'銘柄':<8} {'勝率':<7} {'PF':<6} {'総損益':<12} {'平均損益':<10} {'取引数':<6}")
        print("-" * 80)

        for idx, row in tier2_df.iterrows():
            print(f"{row['symbol']:<8} {row['win_rate']:>5.1f}% {row['profit_factor']:>5.2f} "
                  f"{row['total_pnl']:>11,.0f}円 {row['avg_pnl']:>9,.0f}円 {int(row['trade_count']):>5}")

    # 最終推奨
    print(f"\n" + "=" * 80)
    print("【明日（2025/11/20）の最終推奨】")
    print("=" * 80)

    # 大損失日の翌日なので、保守的にTier1 + Tier2の上位を選定
    recommended = pd.concat([tier1_df, tier2_df]) if len(tier1_df) > 0 or len(tier2_df) > 0 else tier3_df

    if len(recommended) > 0:
        # リスク管理: 大損失日の翌日なので上位20-25銘柄に絞る
        if len(recommended) > 25:
            final_count = 25
            print(f"\n【推奨】上位{final_count}銘柄にエントリー")
            print("（大損失日の翌日のため、質の高い銘柄に絞る）")
        elif len(recommended) > 15:
            final_count = min(20, len(recommended))
            print(f"\n【推奨】上位{final_count}銘柄にエントリー")
        else:
            final_count = len(recommended)
            print(f"\n【推奨】推奨基準を満たす全{final_count}銘柄にエントリー")

        final_list = recommended.head(final_count)

        print(f"\n具体的な銘柄リスト:")
        symbols_list = final_list['symbol'].tolist()
        for i in range(0, len(symbols_list), 8):
            batch = symbols_list[i:i+8]
            print(f"  {', '.join(batch)}")

        # 期待パフォーマンス
        expected_total_pnl = final_list['total_pnl'].sum()
        expected_avg_pnl = final_list['avg_pnl'].sum()
        expected_win_rate = final_list['win_rate'].mean()
        expected_pf = final_list['profit_factor'].mean()

        print(f"\n【期待パフォーマンス】")
        print(f"  6ヶ月累計損益（参考）: {expected_total_pnl:+,.0f}円")
        print(f"  1日あたり期待損益: {expected_avg_pnl:+,.0f}円")
        print(f"  平均勝率: {expected_win_rate:.1f}%")
        print(f"  平均プロフィットファクター: {expected_pf:.2f}")

        print(f"\n【リスク管理】")
        print(f"  今日の損失: -1,900,000円")
        print(f"  統計的には翌日平均 +49,000円（勝率54.5%）")
        print(f"  上記{final_count}銘柄での期待値: {expected_avg_pnl:+,.0f}円")

        if expected_avg_pnl > 0:
            print(f"\n→ 明日は通常通りエントリー推奨")
            print(f"   ただし、質の高い上位{final_count}銘柄に絞ることでリスク軽減")
        else:
            print(f"\n⚠ 期待値がマイナスのため、慎重にエントリーを検討")

    else:
        print("\n⚠ 推奨基準を満たす銘柄がありません")
        print("明日のエントリーは見送り推奨")

    # 避けるべき銘柄
    worst_symbols = stats_df.nsmallest(5, 'total_pnl')
    print(f"\n" + "=" * 80)
    print("【参考: 避けるべき銘柄（ワースト5）】")
    print("=" * 80)
    print(f"\n{'銘柄':<8} {'勝率':<7} {'PF':<6} {'総損益':<12} {'平均損益':<10}")
    print("-" * 80)

    for symbol, row in worst_symbols.iterrows():
        print(f"{symbol:<8} {row['win_rate']:>5.1f}% {row['profit_factor']:>5.2f} "
              f"{row['total_pnl']:>11,.0f}円 {row['avg_pnl']:>9,.0f}円")

    print("\n" + "=" * 80)

    # CSV出力
    if len(recommended) > 0:
        output_file = "recommended_stocks_tomorrow_v2.csv"
        recommended.to_csv(output_file, index=False)
        print(f"\n詳細データを {output_file} に出力しました")
        print("=" * 80)

if __name__ == "__main__":
    recommend_tomorrow_stocks()
