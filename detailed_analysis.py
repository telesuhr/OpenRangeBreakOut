"""
10月バックテスト結果の詳細分析

個別銘柄バックテスト（2025年10月）の結果を深掘り分析
"""
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 個別銘柄バックテスト結果（2025年10月、37銘柄）
results_summary = {
    'total_invested': 370_000_000,
    'final_equity': 362_664_647,
    'total_return': -0.0198,
    'total_trades': 669,
    'trading_stocks': 37,
    'non_trading_stocks': 12
}

# セクター別データ
sector_results = [
    {'sector': 'テクノロジー・通信', 'stocks': 8, 'trades': 144, 'win_rate': 0.461, 'total_pnl': 795682, 'avg_return': 0.0099},
    {'sector': '電機・精密', 'stocks': 4, 'trades': 60, 'win_rate': 0.405, 'total_pnl': -637588, 'avg_return': -0.0159},
    {'sector': '小売・消費', 'stocks': 5, 'trades': 93, 'win_rate': 0.432, 'total_pnl': -1010954, 'avg_return': -0.0202},
    {'sector': '金融', 'stocks': 6, 'trades': 115, 'win_rate': 0.423, 'total_pnl': -1052202, 'avg_return': -0.0175},
    {'sector': '製薬', 'stocks': 4, 'trades': 72, 'win_rate': 0.452, 'total_pnl': -1090858, 'avg_return': -0.0273},
    {'sector': '自動車', 'stocks': 5, 'trades': 91, 'win_rate': 0.410, 'total_pnl': -1953372, 'avg_return': -0.0391},
    {'sector': '商社', 'stocks': 5, 'trades': 94, 'win_rate': 0.355, 'total_pnl': -2386060, 'avg_return': -0.0477},
]

# トップ10銘柄
top_stocks = [
    {'name': 'ソフトバンクG', 'sector': 'テクノロジー・通信', 'trades': 16, 'win_rate': 0.438, 'return': 0.0912, 'pnl': 912230},
    {'name': 'レーザーテック', 'sector': 'テクノロジー・通信', 'trades': 18, 'win_rate': 0.444, 'return': 0.0673, 'pnl': 673445},
    {'name': '日立製作所', 'sector': '電機・精密', 'trades': 17, 'win_rate': 0.647, 'return': 0.0422, 'pnl': 421786},
    {'name': 'キーエンス', 'sector': 'テクノロジー・通信', 'trades': 19, 'win_rate': 0.579, 'return': 0.0275, 'pnl': 275430},
    {'name': '三井住友FG', 'sector': '金融', 'trades': 20, 'win_rate': 0.500, 'return': 0.0245, 'pnl': 245472},
    {'name': 'みずほFG', 'sector': '金融', 'trades': 20, 'win_rate': 0.500, 'return': 0.0126, 'pnl': 126113},
    {'name': '三菱UFJ', 'sector': '金融', 'trades': 18, 'win_rate': 0.556, 'return': 0.0082, 'pnl': 82406},
    {'name': '協和キリン', 'sector': '製薬', 'trades': 18, 'win_rate': 0.611, 'return': 0.0070, 'pnl': 70068},
    {'name': 'ファナック', 'sector': '電機・精密', 'trades': 19, 'win_rate': 0.474, 'return': 0.0017, 'pnl': 16860},
    {'name': 'KDDI', 'sector': 'テクノロジー・通信', 'trades': 17, 'win_rate': 0.588, 'return': -0.0024, 'pnl': -24183},
]

# ワースト10銘柄
worst_stocks = [
    {'name': '三井物産', 'sector': '商社', 'trades': 19, 'win_rate': 0.211, 'return': -0.0769, 'pnl': -769108},
    {'name': '第一生命', 'sector': '金融', 'trades': 18, 'win_rate': 0.222, 'return': -0.0715, 'pnl': -714786},
    {'name': 'デンソー', 'sector': '電機・精密', 'trades': 18, 'win_rate': 0.333, 'return': -0.0708, 'pnl': -708474},
    {'name': '日産自動車', 'sector': '自動車', 'trades': 19, 'win_rate': 0.368, 'return': -0.0593, 'pnl': -592510},
    {'name': '丸紅', 'sector': '商社', 'trades': 20, 'win_rate': 0.300, 'return': -0.0579, 'pnl': -578675},
    {'name': 'アステラス', 'sector': '製薬', 'trades': 15, 'win_rate': 0.267, 'return': -0.0576, 'pnl': -576068},
    {'name': 'トヨタ自動車', 'sector': '自動車', 'trades': 18, 'win_rate': 0.333, 'return': -0.0574, 'pnl': -573798},
    {'name': 'アドバンテスト', 'sector': 'テクノロジー・通信', 'trades': 20, 'win_rate': 0.300, 'return': -0.0519, 'pnl': -518970},
    {'name': '東京海上', 'sector': '金融', 'trades': 19, 'win_rate': 0.263, 'return': -0.0459, 'pnl': -458513},
    {'name': 'ホンダ', 'sector': '自動車', 'trades': 17, 'win_rate': 0.529, 'return': -0.0448, 'pnl': -448272},
]


def print_header(title):
    """ヘッダー表示"""
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def analyze_overall():
    """全体サマリー"""
    print_header("📊 バックテスト全体サマリー（2025年10月）")
    
    logger.info(f"\n期間: 2025年10月1日～10月31日（約1ヶ月）")
    logger.info(f"対象銘柄: {results_summary['trading_stocks'] + results_summary['non_trading_stocks']}銘柄")
    logger.info(f"  - 取引あり: {results_summary['trading_stocks']}銘柄")
    logger.info(f"  - 取引なし: {results_summary['non_trading_stocks']}銘柄")
    
    logger.info(f"\n【パフォーマンス】")
    logger.info(f"総投資額: {results_summary['total_invested']:,}円")
    logger.info(f"最終資産: {results_summary['final_equity']:,}円")
    logger.info(f"総合リターン: {results_summary['total_return']:+.2%}")
    logger.info(f"総損益: {results_summary['final_equity'] - results_summary['total_invested']:+,}円")
    
    logger.info(f"\n【取引統計】")
    logger.info(f"総取引数: {results_summary['total_trades']}回")
    logger.info(f"1銘柄あたり平均: {results_summary['total_trades'] / results_summary['trading_stocks']:.1f}回")
    
    # 1日あたりの取引
    trading_days = 23  # 10月の営業日
    logger.info(f"1日あたり平均: {results_summary['total_trades'] / trading_days:.1f}回")


def analyze_sectors():
    """セクター別詳細分析"""
    print_header("🏢 セクター別パフォーマンス分析")
    
    df = pd.DataFrame(sector_results)
    df = df.sort_values('total_pnl', ascending=False)
    
    logger.info(f"\n【セクター別ランキング（総損益順）】\n")
    
    for i, row in df.iterrows():
        status = "✅" if row['total_pnl'] > 0 else "❌"
        logger.info(f"{status} {row['sector']:20s}")
        logger.info(f"   銘柄数: {row['stocks']}  |  取引: {row['trades']}回  |  勝率: {row['win_rate']:.1%}")
        logger.info(f"   総損益: {row['total_pnl']:+,}円  |  平均リターン: {row['avg_return']:+.2%}")
        logger.info("")
    
    # セクター特性分析
    logger.info(f"\n【セクター特性】")
    
    best = df.iloc[0]
    worst = df.iloc[-1]
    
    logger.info(f"\n✨ 最良セクター: {best['sector']}")
    logger.info(f"   → 唯一のプラスリターン（+{best['avg_return']:.2%}）")
    logger.info(f"   → 勝率も比較的高い（{best['win_rate']:.1%}）")
    
    logger.info(f"\n⚠️  最悪セクター: {worst['sector']}")
    logger.info(f"   → 平均リターン {worst['avg_return']:.2%}")
    logger.info(f"   → 勝率も最低（{worst['win_rate']:.1%}）")
    logger.info(f"   → 総損失 {worst['total_pnl']:,}円")


def analyze_top_stocks():
    """トップパフォーマンス銘柄分析"""
    print_header("🏆 トップパフォーマンス銘柄（上位10）")
    
    logger.info("")
    for i, stock in enumerate(top_stocks, 1):
        logger.info(f"{i:2d}. {stock['name']:20s} ({stock['sector']:15s})")
        logger.info(f"    リターン: {stock['return']:+6.2%}  |  損益: {stock['pnl']:+,}円")
        logger.info(f"    取引: {stock['trades']:2d}回  |  勝率: {stock['win_rate']:5.1%}")
        logger.info("")
    
    # 共通特性
    logger.info(f"\n【トップ銘柄の共通特性】")
    tech_count = sum(1 for s in top_stocks if 'テクノロジー' in s['sector'])
    avg_trades = sum(s['trades'] for s in top_stocks) / len(top_stocks)
    avg_win_rate = sum(s['win_rate'] for s in top_stocks) / len(top_stocks)
    
    logger.info(f"• テクノロジー・通信セクターが{tech_count}/10銘柄")
    logger.info(f"• 平均取引回数: {avg_trades:.1f}回")
    logger.info(f"• 平均勝率: {avg_win_rate:.1%}")


def analyze_worst_stocks():
    """ワーストパフォーマンス銘柄分析"""
    print_header("⚠️  ワーストパフォーマンス銘柄（下位10）")
    
    logger.info("")
    for i, stock in enumerate(worst_stocks, 1):
        logger.info(f"{i:2d}. {stock['name']:20s} ({stock['sector']:15s})")
        logger.info(f"    リターン: {stock['return']:+6.2%}  |  損益: {stock['pnl']:+,}円")
        logger.info(f"    取引: {stock['trades']:2d}回  |  勝率: {stock['win_rate']:5.1%}")
        logger.info("")
    
    # 共通特性
    logger.info(f"\n【ワースト銘柄の共通特性】")
    trading_count = sum(1 for s in worst_stocks if '商社' in s['sector'])
    auto_count = sum(1 for s in worst_stocks if '自動車' in s['sector'])
    avg_win_rate = sum(s['win_rate'] for s in worst_stocks) / len(worst_stocks)
    
    logger.info(f"• 商社セクターが{trading_count}/10銘柄（最多）")
    logger.info(f"• 自動車セクターが{auto_count}/10銘柄")
    logger.info(f"• 平均勝率: {avg_win_rate:.1%}（トップ10の{avg_win_rate/0.507:.1%}）")


def analyze_insights():
    """戦略インサイト"""
    print_header("💡 戦略の重要インサイト")
    
    logger.info(f"\n【1. セクター依存性が極めて高い】")
    logger.info(f"   • テクノロジー・通信: +0.99% （唯一プラス）")
    logger.info(f"   • 商社: -4.77% （最悪）")
    logger.info(f"   → セクター選択が収益性を大きく左右")
    
    logger.info(f"\n【2. 2025年10月の市場環境では全体的にマイナス】")
    logger.info(f"   • 37銘柄中、プラスリターンは一部のみ")
    logger.info(f"   • 総合リターン: -1.98%")
    logger.info(f"   → この戦略は全ての市場環境で機能するわけではない")
    
    logger.info(f"\n【3. 商社セクターの意外な結果】")
    logger.info(f"   • 以前の資金プール方式: 0取引（データ偏り）")
    logger.info(f"   • 個別資金方式: 94取引、平均-4.77%")
    logger.info(f"   → 「100%勝率」は統計的誤謬だった")
    
    logger.info(f"\n【4. 勝率と収益性の相関】")
    logger.info(f"   • 日立製作所: 勝率64.7%、リターン+4.22%")
    logger.info(f"   • 三井物産: 勝率21.1%、リターン-7.69%")
    logger.info(f"   → 勝率の低さが致命的な損失に")
    
    logger.info(f"\n【5. 取引回数のバランス】")
    logger.info(f"   • 以前: 48取引（79%が自動車）← 資金配分バグ")
    logger.info(f"   • 現在: 669取引（均等分散）← 真の評価")
    logger.info(f"   → 約14倍の取引機会を発掘")


def main():
    """メイン分析実行"""
    logger.info("\n")
    analyze_overall()
    logger.info("\n")
    analyze_sectors()
    logger.info("\n")
    analyze_top_stocks()
    logger.info("\n")
    analyze_worst_stocks()
    logger.info("\n")
    analyze_insights()
    logger.info("\n")


if __name__ == "__main__":
    main()
