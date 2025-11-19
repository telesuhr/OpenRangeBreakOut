#!/usr/bin/env python3
"""
エヌビディア決算を考慮した明日の推奨銘柄分析
- 半導体関連銘柄を特定
- リスク別の推奨を提示
"""
import pandas as pd
from pathlib import Path

# 半導体関連銘柄の定義
SEMICONDUCTOR_STOCKS = {
    '8035.T': {'name': '東京エレクトロン', 'category': '半導体製造装置', 'nvidia_sensitivity': 'Very High'},
    '6146.T': {'name': 'ディスコ', 'category': '半導体製造装置', 'nvidia_sensitivity': 'Very High'},
    '6920.T': {'name': 'レーザーテック', 'category': '半導体検査装置', 'nvidia_sensitivity': 'Very High'},
    '7741.T': {'name': 'HOYA', 'category': '半導体材料', 'nvidia_sensitivity': 'High'},
    '6503.T': {'name': '三菱電機', 'category': '半導体関連', 'nvidia_sensitivity': 'Medium'},
    '6752.T': {'name': 'パナソニック', 'category': '半導体関連', 'nvidia_sensitivity': 'Low'},
}

def recommend_with_nvidia_earnings():
    """エヌビディア決算を考慮した推奨"""

    output_dir = Path("Output/20251119_221548")

    print("\n" + "=" * 80)
    print("エヌビディア決算を考慮した明日（2025/11/20）の推奨銘柄分析")
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

        # 半導体関連フラグ
        is_semiconductor = symbol in SEMICONDUCTOR_STOCKS

        symbol_stats[symbol] = {
            'total_pnl': total_pnl,
            'trade_count': len(df),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
            'is_semiconductor': is_semiconductor,
            'nvidia_sensitivity': SEMICONDUCTOR_STOCKS[symbol]['nvidia_sensitivity'] if is_semiconductor else 'None',
            'name': SEMICONDUCTOR_STOCKS[symbol]['name'] if is_semiconductor else ''
        }

    # 推奨銘柄（前回の基準）
    recommended = []
    for symbol, stats in symbol_stats.items():
        if ((stats['total_pnl'] > 0 and stats['win_rate'] >= 45) or
            (stats['total_pnl'] > 0 and stats['win_rate'] >= 40)):
            recommended.append({'symbol': symbol, **stats})

    recommended_df = pd.DataFrame(recommended).sort_values('total_pnl', ascending=False)

    # 半導体関連と非半導体関連に分類
    semiconductor_stocks = recommended_df[recommended_df['is_semiconductor'] == True]
    non_semiconductor_stocks = recommended_df[recommended_df['is_semiconductor'] == False]

    print(f"\n【推奨銘柄の分類】")
    print(f"半導体関連: {len(semiconductor_stocks)}銘柄")
    print(f"非半導体関連: {len(non_semiconductor_stocks)}銘柄")

    # 半導体関連銘柄の詳細
    if len(semiconductor_stocks) > 0:
        print(f"\n" + "=" * 80)
        print("【半導体関連銘柄（エヌビディア決算の影響大）】")
        print("=" * 80)

        print(f"\n{'銘柄':<8} {'企業名':<12} {'感度':<10} {'勝率':<7} {'PF':<6} {'総損益':<12} {'平均損益':<10}")
        print("-" * 80)

        for idx, row in semiconductor_stocks.iterrows():
            print(f"{row['symbol']:<8} {row['name']:<12} {row['nvidia_sensitivity']:<10} "
                  f"{row['win_rate']:>5.1f}% {row['profit_factor']:>5.2f} "
                  f"{row['total_pnl']:>11,.0f}円 {row['avg_pnl']:>9,.0f}円")

        semi_total_pnl = semiconductor_stocks['total_pnl'].sum()
        semi_avg_pnl = semiconductor_stocks['avg_pnl'].sum()
        semi_win_rate = semiconductor_stocks['win_rate'].mean()

        print(f"\n【半導体関連銘柄の期待パフォーマンス】")
        print(f"  期待損益（1日）: {semi_avg_pnl:+,.0f}円")
        print(f"  平均勝率: {semi_win_rate:.1f}%")
        print(f"  6ヶ月累計: {semi_total_pnl:+,.0f}円")

    # シナリオ別推奨
    print(f"\n" + "=" * 80)
    print("【エヌビディア決算を考慮したシナリオ別推奨】")
    print("=" * 80)

    # シナリオA: 決算ポジティブ想定（半導体関連を含める）
    print(f"\n■ シナリオA: 決算ポジティブ想定（ハイリスク・ハイリターン）")
    print("-" * 80)

    if len(recommended_df) >= 16:
        scenario_a = recommended_df.head(16)
        scenario_a_semi = scenario_a[scenario_a['is_semiconductor'] == True]

        print(f"\n推奨: 上位16銘柄（半導体関連{len(scenario_a_semi)}銘柄を含む）")
        print(f"  半導体関連: {', '.join(scenario_a_semi['symbol'].tolist())}")

        symbols_list = scenario_a['symbol'].tolist()
        print(f"\n全銘柄リスト:")
        for i in range(0, len(symbols_list), 8):
            batch = symbols_list[i:i+8]
            print(f"  {', '.join(batch)}")

        expected_pnl_a = scenario_a['avg_pnl'].sum()
        print(f"\n期待損益: {expected_pnl_a:+,.0f}円/日")
        print(f"平均勝率: {scenario_a['win_rate'].mean():.1f}%")

        print(f"\nリスク:")
        print(f"  ✓ エヌビディア決算が好調なら、半導体関連が大きく上昇")
        print(f"  ✗ 決算が不調なら、半導体関連が大きく下落し、全体損益悪化")

    # シナリオB: リスク軽減（半導体関連を除外）
    print(f"\n■ シナリオB: リスク軽減想定（決算リスク回避）")
    print("-" * 80)

    if len(non_semiconductor_stocks) >= 10:
        scenario_b_count = min(16, len(non_semiconductor_stocks))
        scenario_b = non_semiconductor_stocks.head(scenario_b_count)

        print(f"\n推奨: 非半導体関連の上位{scenario_b_count}銘柄")

        symbols_list = scenario_b['symbol'].tolist()
        print(f"\n銘柄リスト:")
        for i in range(0, len(symbols_list), 8):
            batch = symbols_list[i:i+8]
            print(f"  {', '.join(batch)}")

        expected_pnl_b = scenario_b['avg_pnl'].sum()
        print(f"\n期待損益: {expected_pnl_b:+,.0f}円/日")
        print(f"平均勝率: {scenario_b['win_rate'].mean():.1f}%")

        print(f"\nリスク:")
        print(f"  ✓ エヌビディア決算の影響を最小化")
        print(f"  ✓ 安定したトレードが期待できる")
        print(f"  ✗ 決算が好調でも大きな上昇を逃す可能性")

    else:
        print(f"\n非半導体関連銘柄が少ないため、シナリオBは非推奨")

    # シナリオC: バランス型（半導体関連を限定）
    print(f"\n■ シナリオC: バランス型（半導体関連を2-3銘柄に限定）")
    print("-" * 80)

    if len(semiconductor_stocks) >= 2 and len(non_semiconductor_stocks) >= 10:
        # 半導体関連のトップ2-3銘柄 + 非半導体関連のトップ13-14銘柄
        semi_limited = semiconductor_stocks.head(2)
        non_semi_for_balance = non_semiconductor_stocks.head(14)
        scenario_c = pd.concat([semi_limited, non_semi_for_balance]).sort_values('total_pnl', ascending=False)

        print(f"\n推奨: 半導体関連{len(semi_limited)}銘柄 + 非半導体関連{len(non_semi_for_balance)}銘柄")
        print(f"  半導体関連（優良2銘柄のみ）: {', '.join(semi_limited['symbol'].tolist())}")

        symbols_list = scenario_c['symbol'].tolist()
        print(f"\n全銘柄リスト:")
        for i in range(0, len(symbols_list), 8):
            batch = symbols_list[i:i+8]
            print(f"  {', '.join(batch)}")

        expected_pnl_c = scenario_c['avg_pnl'].sum()
        print(f"\n期待損益: {expected_pnl_c:+,.0f}円/日")
        print(f"平均勝率: {scenario_c['win_rate'].mean():.1f}%")

        print(f"\nリスク:")
        print(f"  ✓ 決算好調時は半導体関連で利益獲得")
        print(f"  ✓ 決算不調時も非半導体関連で損失を限定")
        print(f"  ✓ リスクとリターンのバランスが最適")

    # 推奨判定
    print(f"\n" + "=" * 80)
    print("【最終推奨】")
    print("=" * 80)

    print(f"\n今晩のエヌビディア決算を考慮した推奨:")
    print(f"\n1. エヌビディア決算に自信がある → シナリオA（半導体含む16銘柄）")
    print(f"   期待損益が最大だが、決算リスクも最大")

    print(f"\n2. 決算リスクを避けたい → シナリオB（非半導体のみ）")
    print(f"   安定志向、決算の影響を最小化")

    print(f"\n3. バランス重視（推奨） → シナリオC（半導体2銘柄+非半導体14銘柄）")
    print(f"   リスクとリターンのバランスが最適")
    print(f"   決算が好調でも不調でも対応可能")

    print(f"\n【補足情報】")
    print(f"  - 今日は大損失日（-190万円）の翌日")
    print(f"  - 統計的には54.5%の確率で反発")
    print(f"  - エヌビディア決算は22:30（日本時間）発表予定")
    print(f"  - 決算発表は日本市場の取引時間外のため、影響は明日の寄り付きから")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    recommend_with_nvidia_earnings()
