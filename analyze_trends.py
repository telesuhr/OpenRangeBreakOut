"""
オープンレンジブレイクアウト戦略の詳細な傾向分析

前回のバックテスト結果（2025年10月、49銘柄、1分足データ）を基に
セクター別、銘柄別の詳細な傾向を分析します。
"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # シンプルな出力
)

logger = logging.getLogger(__name__)


def print_section(title: str):
    """セクションタイトルを表示"""
    logger.info("\n" + "=" * 80)
    logger.info(f"  {title}")
    logger.info("=" * 80)


def analyze_sector_trends():
    """セクター別の傾向分析"""

    # セクター別データ（前回の結果から）
    sectors = {
        'テクノロジー・通信': {
            'return': 1.64,
            'pnl': 1_310_106,
            'stocks': ['ソフトバンクG', 'KDDI', 'NTT'],
            'characteristic': '唯一のプラスセクター'
        },
        'その他': {
            'return': 0.05,
            'pnl': 24_928,
            'stocks': ['商船三井', '日本郵船', '電通グループ'],
            'characteristic': 'ほぼ横ばい'
        },
        '金融': {
            'return': -1.32,
            'pnl': -792_116,
            'stocks': ['三菱UFJ', 'みずほ', '第一生命'],
            'characteristic': '軽度のマイナス'
        },
        '小売・消費': {
            'return': -1.93,
            'pnl': -965_342,
            'stocks': ['ファーストリテイリング', 'セブン&アイ'],
            'characteristic': '中程度のマイナス'
        },
        '重工業・建設': {
            'return': -2.04,
            'pnl': -1_018_967,
            'stocks': ['三菱重工', 'JFE'],
            'characteristic': '中程度のマイナス'
        },
        '電機・精密': {
            'return': -2.54,
            'pnl': -1_522_233,
            'stocks': ['ソニー', 'パナソニック', 'レーザーテック'],
            'characteristic': 'やや大きなマイナス'
        },
        '製薬': {
            'return': -3.92,
            'pnl': -1_569_824,
            'stocks': ['武田薬品', 'アステラス', '第一三共'],
            'characteristic': '大きなマイナス'
        },
        '自動車': {
            'return': -4.02,
            'pnl': -2_010_923,
            'stocks': ['トヨタ', 'ホンダ', 'デンソー', '日産'],
            'characteristic': '大きなマイナス'
        },
        '商社': {
            'return': -4.52,
            'pnl': -2_258_322,
            'stocks': ['三菱商事', '伊藤忠', '三井物産', '丸紅', '豊田通商'],
            'characteristic': '最悪パフォーマンス'
        }
    }

    print_section("セクター別パフォーマンス分析")

    logger.info("\n【セクター別リターン順位】")
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1]['return'], reverse=True)

    for rank, (sector, data) in enumerate(sorted_sectors, 1):
        symbol = "✅" if data['return'] > 0 else "⚠️" if data['return'] > -2 else "❌"
        logger.info(f"{rank}. {sector:15s} {symbol} {data['return']:+6.2f}% "
                   f"({data['pnl']:+12,.0f}円) - {data['characteristic']}")

    # 主要な傾向
    logger.info("\n【主要な傾向】")
    logger.info("1. テクノロジー・通信セクターのみがプラスリターン")
    logger.info("   → ボラティリティの高い銘柄で戦略が機能")
    logger.info("")
    logger.info("2. 商社セクターが最悪のパフォーマンス (-4.52%)")
    logger.info("   → 週次で見ると+100%勝率だったが、長期では逆転")
    logger.info("   → サンプル数の重要性を示す結果")
    logger.info("")
    logger.info("3. 製薬・自動車・商社が下位3セクター")
    logger.info("   → 大型株、流動性の高い銘柄で戦略が機能しない可能性")
    logger.info("")
    logger.info("4. 9セクター中8セクターがマイナス")
    logger.info("   → 2025年10月の市場環境では戦略全体が苦戦")


def analyze_stock_performance():
    """銘柄別パフォーマンス分析"""

    print_section("銘柄別パフォーマンス分析")

    # トップ3
    logger.info("\n【トップ3銘柄】")
    top_performers = [
        ('ソフトバンクG', 9.71, 971_270, 19, 42.1, 'テクノロジー・通信'),
        ('レーザーテック', 7.89, 789_355, 18, 38.9, '電機・精密'),
        ('JFE', 2.71, 271_388, 21, 57.1, '重工業・建設')
    ]

    for rank, (stock, ret, pnl, trades, win_rate, sector) in enumerate(top_performers, 1):
        logger.info(f"{rank}. {stock:15s} +{ret:.2f}% ({pnl:+10,.0f}円)")
        logger.info(f"   取引数: {trades}回, 勝率: {win_rate:.1f}%, セクター: {sector}")

    # ワースト3
    logger.info("\n【ワースト3銘柄】")
    worst_performers = [
        ('豊田通商', -8.97, -896_925, 20, 30.0, '商社'),
        ('デンソー', -8.87, -887_050, 21, 38.1, '自動車'),
        ('第一生命', -7.98, -798_169, 19, 21.1, '金融')
    ]

    for rank, (stock, ret, pnl, trades, win_rate, sector) in enumerate(worst_performers, 1):
        logger.info(f"{rank}. {stock:15s} {ret:.2f}% ({pnl:+10,.0f}円)")
        logger.info(f"   取引数: {trades}回, 勝率: {win_rate:.1f}%, セクター: {sector}")

    # 特徴分析
    logger.info("\n【銘柄パフォーマンスの特徴】")
    logger.info("1. トップ銘柄の勝率は38-57%と決して高くない")
    logger.info("   → 高リターンは勝率ではなく、利益の大きさによる")
    logger.info("   → 損小利大のリスクリワード比が重要")
    logger.info("")
    logger.info("2. ワースト銘柄は勝率21-38%と低い")
    logger.info("   → 特に第一生命の21.1%は極端に低い")
    logger.info("   → レンジブレイクアウトが頻繁に失敗")
    logger.info("")
    logger.info("3. レーザーテックは電機・精密セクター全体がマイナスなのに+7.89%")
    logger.info("   → 個別銘柄の特性がセクター傾向を上回る例")
    logger.info("   → 半導体関連の高ボラティリティが寄与")


def analyze_win_rate_correlation():
    """勝率とリターンの相関分析"""

    print_section("勝率とリターンの相関分析")

    logger.info("\n【重要な発見】")
    logger.info("勝率が高い ≠ 高リターン")
    logger.info("")

    # データポイント
    data_points = [
        ('ソフトバンクG', 42.1, 9.71, 'テクノロジー'),
        ('レーザーテック', 38.9, 7.89, '電機'),
        ('JFE', 57.1, 2.71, '重工業'),
        ('豊田通商', 30.0, -8.97, '商社'),
        ('デンソー', 38.1, -8.87, '自動車'),
        ('第一生命', 21.1, -7.98, '金融')
    ]

    logger.info("銘柄              勝率    リターン  セクター")
    logger.info("-" * 60)
    for stock, win_rate, ret, sector in data_points:
        logger.info(f"{stock:15s} {win_rate:5.1f}%  {ret:+7.2f}%  {sector}")

    logger.info("\n【分析】")
    logger.info("・JFEは57.1%の勝率で+2.71%（最も高い勝率）")
    logger.info("・ソフトバンクGは42.1%の勝率で+9.71%（最も高いリターン）")
    logger.info("・レーザーテックは38.9%の勝率で+7.89%")
    logger.info("")
    logger.info("→ 勝率40%前後でも大きなリターンを得られる可能性")
    logger.info("→ リスクリワード比（平均利益/平均損失）が重要")
    logger.info("→ ボラティリティの高い銘柄で大きな利益を狙う戦略が有効")


def analyze_data_granularity_impact():
    """データ粒度の影響分析"""

    print_section("データ粒度の影響（5分足 vs 1分足）")

    logger.info("\n【比較結果】")
    logger.info("                   5分足      1分足      改善")
    logger.info("-" * 60)
    logger.info(f"総取引数           669回      995回      +48.7%")
    logger.info(f"総合リターン      -1.98%     -1.80%     +0.18%")
    logger.info("")

    logger.info("【影響分析】")
    logger.info("1. 取引機会の増加: +326回（+48.7%）")
    logger.info("   → レンジブレイクアウトの検出精度が5倍向上")
    logger.info("   → より多くのエントリー機会を捕捉")
    logger.info("")
    logger.info("2. リターンの微増: +0.18%")
    logger.info("   → 劇的な改善ではないが、一貫して改善傾向")
    logger.info("   → データ精度向上が戦略パフォーマンスに寄与")
    logger.info("")
    logger.info("3. 取引頻度と収益性の関係")
    logger.info("   → 取引回数が増えても必ずしも収益向上とは限らない")
    logger.info("   → 戦略の本質的な弱点（負の期待値）は変わらない")


def analyze_market_conditions():
    """市場環境の影響分析"""

    print_section("2025年10月の市場環境分析")

    logger.info("\n【期間】2025年10月1日〜31日（23営業日）")
    logger.info("")
    logger.info("【全体的な傾向】")
    logger.info("・49銘柄中、プラスリターンは少数")
    logger.info("・総合リターン -1.80% は戦略の期待値がマイナスであることを示唆")
    logger.info("・セクター別でもテクノロジーのみプラス")
    logger.info("")
    logger.info("【可能性のある市場要因】")
    logger.info("1. トレンドレス相場（レンジ相場）")
    logger.info("   → ブレイクアウト後にすぐ反転する環境")
    logger.info("   → 09:15-09:30のレンジが真のサポート/レジスタンスとして機能せず")
    logger.info("")
    logger.info("2. ボラティリティの変化")
    logger.info("   → 朝のレンジが狭すぎてブレイクアウトが頻発")
    logger.info("   → または広すぎてブレイクアウトが起こりにくい")
    logger.info("")
    logger.info("3. ノイズトレード")
    logger.info("   → アルゴリズム取引による短時間のスパイクが誤シグナルを生成")


def identify_strategy_improvements():
    """戦略改善の提案"""

    print_section("戦略改善の提案")

    logger.info("\n【1. セクターフィルタリング】")
    logger.info("実装:")
    logger.info("  - テクノロジー・通信セクターのみに限定")
    logger.info("  - 商社、自動車、製薬セクターを除外")
    logger.info("期待効果:")
    logger.info("  - 勝率の高いセクターに集中してリターン改善")
    logger.info("  - テクノロジー銘柄は +1.64% のプラスリターン実績")
    logger.info("")

    logger.info("【2. ボラティリティフィルター】")
    logger.info("実装:")
    logger.info("  - 過去N日間のATR（Average True Range）が一定以上の銘柄のみ")
    logger.info("  - または前日のボラティリティが閾値以上の銘柄")
    logger.info("期待効果:")
    logger.info("  - ボラティリティが低い銘柄で無駄なエントリーを回避")
    logger.info("  - ソフトバンクG、レーザーテックなど高ボラ銘柄で成功実績")
    logger.info("")

    logger.info("【3. レンジ幅フィルター】")
    logger.info("実装:")
    logger.info("  - 09:05-09:15のレンジ幅が前日終値の0.5%以上の時のみエントリー")
    logger.info("  - レンジが狭すぎる日は取引しない")
    logger.info("期待効果:")
    logger.info("  - ノイズによる誤ブレイクアウトを削減")
    logger.info("  - 有意なレンジブレイクのみを捕捉")
    logger.info("")

    logger.info("【4. エントリータイミングの最適化】")
    logger.info("実装:")
    logger.info("  - ブレイクアウト後、一定のpull back（押し目）を待つ")
    logger.info("  - または出来高急増を確認してからエントリー")
    logger.info("期待効果:")
    logger.info("  - False breakout（偽のブレイクアウト）を回避")
    logger.info("  - より確実なトレンド形成を確認")
    logger.info("")

    logger.info("【5. リスク管理の強化】")
    logger.info("実装:")
    logger.info("  - 損切り -1% に加えて、トレーリングストップを導入")
    logger.info("  - 利益が+1%に到達したら損切りラインをエントリー価格に移動")
    logger.info("期待効果:")
    logger.info("  - 利益の確保")
    logger.info("  - リスクリワード比の改善")
    logger.info("")

    logger.info("【6. 時間帯フィルター】")
    logger.info("実装:")
    logger.info("  - 09:15-09:30のブレイクアウトのみに限定（現在は10:00まで）")
    logger.info("  - 寄り付き直後の動きに特化")
    logger.info("期待効果:")
    logger.info("  - 最もボラティリティが高い時間帯に集中")
    logger.info("  - 時間経過とともに勢いが失われるパターンを回避")


def summarize_findings():
    """主要な発見のサマリー"""

    print_section("主要な発見サマリー")

    logger.info("\n【✅ 確認された傾向】")
    logger.info("1. テクノロジー・通信セクターは唯一プラスリターン (+1.64%)")
    logger.info("2. 商社セクターは最悪パフォーマンス (-4.52%)")
    logger.info("3. 勝率と収益性は必ずしも相関しない")
    logger.info("   → 勝率38.9%のレーザーテックが+7.89%のリターン")
    logger.info("4. データ粒度向上（5分→1分）で取引機会+48.7%、リターン+0.18%")
    logger.info("5. 49銘柄中、大多数がマイナスリターン → 戦略の期待値が負")
    logger.info("")

    logger.info("【⚠️ 戦略の弱点】")
    logger.info("1. 市場環境に強く依存")
    logger.info("   → トレンド相場では機能、レンジ相場では苦戦")
    logger.info("2. 全銘柄一律適用は非効率")
    logger.info("   → セクター/銘柄選択が重要")
    logger.info("3. 利益目標なし（終値決済のみ）は非効率")
    logger.info("   → 利益が出ても保持せず、戻して終わるケースが多い可能性")
    logger.info("")

    logger.info("【💡 実用化への提言】")
    logger.info("1. セクターを限定（テクノロジー・通信のみ）")
    logger.info("2. ボラティリティフィルターを追加")
    logger.info("3. レンジ幅の閾値を設定")
    logger.info("4. トレーリングストップで利益確保")
    logger.info("5. より長期のバックテスト（3ヶ月〜1年）で検証")
    logger.info("6. 異なる市場環境（上昇相場/下落相場）でのパフォーマンス確認")
    logger.info("")

    logger.info("【📊 次のステップ】")
    logger.info("1. テクノロジーセクター限定バックテスト")
    logger.info("2. ボラティリティフィルター付き戦略のテスト")
    logger.info("3. より長期（2025年7月〜11月）でのバックテスト")
    logger.info("4. パラメータ最適化（レンジ期間、エントリー時間帯）")
    logger.info("5. リアルタイムシミュレーション（ペーパートレーディング）")


def main():
    """メイン実行"""

    logger.info("\n" + "🔍" * 40)
    logger.info("オープンレンジブレイクアウト戦略 - 詳細傾向分析")
    logger.info("バックテスト期間: 2025年10月1日〜31日（23営業日）")
    logger.info("対象銘柄数: 49銘柄")
    logger.info("データ粒度: 1分足")
    logger.info("🔍" * 40)

    # 各分析を実行
    analyze_sector_trends()
    analyze_stock_performance()
    analyze_win_rate_correlation()
    analyze_data_granularity_impact()
    analyze_market_conditions()
    identify_strategy_improvements()
    summarize_findings()

    logger.info("\n" + "=" * 80)
    logger.info("分析完了")
    logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    main()
