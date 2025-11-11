"""
既存のバックテストログから日次パフォーマンスを抽出・分析

バックテスト実行済みの結果ログから日次の取引データを抽出し、
セクター別の日次パフォーマンスを分析
"""
import re
import logging
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)


# 銘柄とセクターのマッピング
STOCK_SECTORS = {
    # テクノロジー・通信
    '9984.T': ('ソフトバンクG', 'テクノロジー・通信'),
    '9433.T': ('KDDI', 'テクノロジー・通信'),
    '9432.T': ('NTT', 'テクノロジー・通信'),

    # 自動車
    '7203.T': ('トヨタ自動車', '自動車'),
    '7267.T': ('ホンダ', '自動車'),
    '7201.T': ('日産自動車', '自動車'),
    '6902.T': ('デンソー', '自動車'),

    # 商社
    '8058.T': ('三菱商事', '商社'),
    '8001.T': ('伊藤忠商事', '商社'),
    '8031.T': ('三井物産', '商社'),
    '8002.T': ('丸紅', '商社'),
    '8015.T': ('豊田通商', '商社'),

    # 電機・精密
    '6758.T': ('ソニーG', '電機・精密'),
    '6752.T': ('パナソニック', '電機・精密'),
    '6861.T': ('キーエンス', '電機・精密'),
    '6954.T': ('ファナック', '電機・精密'),
    '6981.T': ('村田製作所', '電機・精密'),
    '6594.T': ('日本電産', '電機・精密'),
    '6503.T': ('三菱電機', '電機・精密'),
    '6920.T': ('レーザーテック', '電機・精密'),

    # 金融
    '8306.T': ('三菱UFJ', '金融'),
    '8316.T': ('三井住友', '金融'),
    '8411.T': ('みずほ', '金融'),
    '8750.T': ('第一生命', '金融'),
    '8725.T': ('MS&AD', '金融'),

    # 製薬
    '4502.T': ('武田薬品', '製薬'),
    '4503.T': ('アステラス', '製薬'),
    '4568.T': ('第一三共', '製薬'),

    # 小売・消費
    '9983.T': ('ファーストリテイリング', '小売・消費'),
    '3382.T': ('セブン&アイ', '小売・消費'),
    '2914.T': ('JT', '小売・消費'),

    # 重工業・建設
    '7011.T': ('三菱重工', '重工業・建設'),
    '5411.T': ('JFE', '重工業・建設'),
    '5401.T': ('新日鉄', '重工業・建設'),
    '4063.T': ('信越化学', '重工業・建設'),
    '6301.T': ('小松製作所', '重工業・建設'),
    '1801.T': ('大成建設', '重工業・建設'),
    '1803.T': ('清水建設', '重工業・建設'),

    # その他
    '9101.T': ('日本郵船', 'その他'),
    '9104.T': ('商船三井', 'その他'),
    '4324.T': ('電通グループ', 'その他'),
    '9020.T': ('JR東日本', 'その他'),
    '9022.T': ('JR東海', 'その他'),
    '9062.T': ('日本通運', 'その他'),
    '2502.T': ('アサヒ', 'その他'),
    '2503.T': ('キリン', 'その他'),
    '4452.T': ('花王', 'その他'),
}


def parse_log_file(log_file='backtest_1min_output.log'):
    """ログファイルから取引データを抽出"""

    trades_by_date = defaultdict(list)
    current_symbol = None
    current_sector = None

    # クローズログのパターン
    # 例: 2025-11-09 10:06:29,833 - INFO - 7203.T: LONG クローズ @ 2481.0 (損益: -10,000 円, -1.00%) - loss
    close_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2},\d+ - INFO - '
        r'(\d+\.\w+): (\w+) クローズ @ ([\d,.]+) '
        r'\(損益: ([\d,+-]+) 円, ([\d.+-]+)%\) - (\w+)'
    )

    # 銘柄処理開始のパターン
    # 例: [1/49] トヨタ自動車 (7203.T) - 自動車
    stock_pattern = re.compile(r'\[(\d+)/(\d+)\] (.+?) \((.+?)\) - (.+)')

    # エントリーログのパターン（日付抽出用）
    # 例: 2025-11-09 10:06:09,961 - INFO - 7203.T: LONG エントリー @ 2500 x 4000株 (時刻: 2025-10-01 00:25:00+00:00)
    entry_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2},\d+ - INFO - '
        r'(\d+\.\w+): (\w+) エントリー.+時刻: (\d{4}-\d{2}-\d{2})'
    )

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 銘柄切り替え検出
                stock_match = stock_pattern.search(line)
                if stock_match:
                    current_symbol = stock_match.group(4)
                    current_sector = stock_match.group(5)
                    continue

                # クローズ検出
                close_match = close_pattern.search(line)
                if close_match and current_symbol:
                    date_str = close_match.group(1)
                    symbol = close_match.group(2)
                    side = close_match.group(3)
                    exit_price = close_match.group(4)
                    pnl_str = close_match.group(5).replace(',', '').replace('+', '')
                    return_str = close_match.group(6).replace('+', '')
                    reason = close_match.group(7)

                    # 取引日を特定（エントリー時刻から）
                    # ログの日付は実行日なので、実際の取引日はエントリーログから取得
                    # 簡易的に、クローズログの前のエントリーログから日付を取得

                    trades_by_date[date_str].append({
                        'symbol': symbol,
                        'name': STOCK_SECTORS.get(symbol, (symbol, 'Unknown'))[0],
                        'sector': STOCK_SECTORS.get(symbol, (symbol, 'Unknown'))[1],
                        'side': side,
                        'pnl': float(pnl_str),
                        'return': float(return_str),
                        'reason': reason
                    })

    except FileNotFoundError:
        logger.error(f"ログファイル {log_file} が見つかりません")
        return None

    return trades_by_date


def extract_trade_dates(log_file='backtest_1min_output.log'):
    """ログから実際の取引日付を抽出"""

    # エントリー時刻から取引日を抽出
    # 例: 7203.T: LONG エントリー @ 2500 x 4000株 (時刻: 2025-10-01 00:25:00+00:00)
    entry_pattern = re.compile(
        r'(\d+\.\w+): (\w+) エントリー.+時刻: (\d{4}-\d{2}-\d{2})'
    )

    # クローズログのパターン
    close_pattern = re.compile(
        r'(\d+\.\w+): (\w+) クローズ @ ([\d,.]+) '
        r'\(損益: ([\d,+-]+) 円, ([\d.+-]+)%\) - (\w+)'
    )

    trades_by_date = defaultdict(list)
    current_entry_date = None
    current_symbol = None

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # エントリー検出
                entry_match = entry_pattern.search(line)
                if entry_match:
                    current_symbol = entry_match.group(1)
                    current_entry_date = entry_match.group(3)
                    continue

                # クローズ検出
                close_match = close_pattern.search(line)
                if close_match and current_entry_date and current_symbol:
                    symbol = close_match.group(1)
                    side = close_match.group(2)
                    exit_price = close_match.group(3)
                    pnl_str = close_match.group(4).replace(',', '').replace('+', '')
                    return_str = close_match.group(5).replace('+', '')
                    reason = close_match.group(6)

                    if symbol == current_symbol:
                        trades_by_date[current_entry_date].append({
                            'symbol': symbol,
                            'name': STOCK_SECTORS.get(symbol, (symbol, 'Unknown'))[0],
                            'sector': STOCK_SECTORS.get(symbol, (symbol, 'Unknown'))[1],
                            'side': side,
                            'pnl': float(pnl_str),
                            'return': float(return_str),
                            'reason': reason
                        })
                        current_entry_date = None
                        current_symbol = None

    except FileNotFoundError:
        logger.error(f"ログファイル {log_file} が見つかりません")
        return None

    return trades_by_date


def analyze_daily_performance(trades_by_date):
    """日次パフォーマンスを分析"""

    logger.info("\n" + "="*80)
    logger.info("日次パフォーマンス分析")
    logger.info("="*80)

    # セクター別の日次統計
    sector_daily_stats = defaultdict(lambda: {'days_positive': 0, 'days_total': 0, 'total_pnl': 0})

    # 日付順にソート
    sorted_dates = sorted(trades_by_date.keys())

    logger.info("\n【日別取引サマリー】")
    logger.info("-"*80)

    for date_str in sorted_dates:
        trades = trades_by_date[date_str]

        # セクター別集計
        sector_summary = defaultdict(lambda: {'trades': [], 'pnl': 0, 'wins': 0})

        for trade in trades:
            sector = trade['sector']
            sector_summary[sector]['trades'].append(trade)
            sector_summary[sector]['pnl'] += trade['pnl']
            if trade['pnl'] > 0:
                sector_summary[sector]['wins'] += 1

        # 日次トータル
        day_total_pnl = sum(s['pnl'] for s in sector_summary.values())
        day_total_trades = sum(len(s['trades']) for s in sector_summary.values())

        result_symbol = "📈" if day_total_pnl > 0 else "📉"
        logger.info(f"\n{date_str} {result_symbol} 総損益: {day_total_pnl:+12,.0f}円 ({day_total_trades}取引)")

        # セクター別表示（損益順）
        sorted_sectors = sorted(sector_summary.items(),
                               key=lambda x: x[1]['pnl'],
                               reverse=True)

        for sector, data in sorted_sectors:
            num_trades = len(data['trades'])
            win_rate = (data['wins'] / num_trades * 100) if num_trades > 0 else 0
            symbol = "✅" if data['pnl'] > 0 else "❌"

            # セクター統計を更新
            sector_daily_stats[sector]['days_total'] += 1
            sector_daily_stats[sector]['total_pnl'] += data['pnl']
            if data['pnl'] > 0:
                sector_daily_stats[sector]['days_positive'] += 1

            logger.info(f"  {symbol} {sector:20s}: {data['pnl']:+12,.0f}円 "
                       f"({data['wins']}/{num_trades}勝, {win_rate:5.1f}%)")

    # セクター別の日次勝率
    logger.info("\n" + "="*80)
    logger.info("セクター別 日次勝率（その日プラスだった割合）")
    logger.info("="*80)
    logger.info(f"\n{'セクター':20s} {'プラス日数':>12s} {'総取引日数':>12s} {'日次勝率':>10s} {'累積損益':>15s}")
    logger.info("-"*80)

    sorted_sectors = sorted(sector_daily_stats.items(),
                           key=lambda x: (x[1]['days_positive'] / x[1]['days_total']) if x[1]['days_total'] > 0 else 0,
                           reverse=True)

    for sector, stats in sorted_sectors:
        daily_win_rate = (stats['days_positive'] / stats['days_total'] * 100) if stats['days_total'] > 0 else 0
        symbol = "✅" if daily_win_rate >= 50 else "⚠️" if daily_win_rate >= 40 else "❌"

        logger.info(f"{symbol} {sector:20s} {stats['days_positive']:12d} {stats['days_total']:12d} "
                   f"{daily_win_rate:9.1f}% {stats['total_pnl']:+15,.0f}円")

    # 結論
    logger.info("\n" + "="*80)
    logger.info("結論")
    logger.info("="*80)

    # テクノロジーセクターの分析
    tech_stats = sector_daily_stats.get('テクノロジー・通信', {})
    if tech_stats:
        tech_daily_win_rate = (tech_stats['days_positive'] / tech_stats['days_total'] * 100) if tech_stats['days_total'] > 0 else 0

        logger.info(f"\nテクノロジー・通信セクター:")
        logger.info(f"  プラスの日: {tech_stats['days_positive']}/{tech_stats['days_total']}日")
        logger.info(f"  日次勝率: {tech_daily_win_rate:.1f}%")
        logger.info(f"  累積損益: {tech_stats['total_pnl']:+,.0f}円")

        if tech_daily_win_rate >= 50:
            logger.info("\n✅ テクノロジー・通信セクターは日次ベースでも一貫して優秀")
            logger.info("   → 過半数の営業日でプラスリターン")
            logger.info("   → 安定して収益を上げている")
        elif tech_daily_win_rate >= 40:
            logger.info("\n⚠️ テクノロジー・通信セクターは日次では不安定")
            logger.info("   → トータルではプラスだが、日によってバラツキが大きい")
            logger.info("   → 大勝ちする日と負ける日が混在")
        else:
            logger.info("\n❌ テクノロジー・通信セクターは特定の日の大勝によるもの")
            logger.info("   → 日次勝率が低く、数日の大勝で全体がプラスになっている")
            logger.info("   → 安定性に欠ける")

    # 商社セクターとの比較
    shosha_stats = sector_daily_stats.get('商社', {})
    if shosha_stats:
        shosha_daily_win_rate = (shosha_stats['days_positive'] / shosha_stats['days_total'] * 100) if shosha_stats['days_total'] > 0 else 0

        logger.info(f"\n商社セクター（比較）:")
        logger.info(f"  プラスの日: {shosha_stats['days_positive']}/{shosha_stats['days_total']}日")
        logger.info(f"  日次勝率: {shosha_daily_win_rate:.1f}%")
        logger.info(f"  累積損益: {shosha_stats['total_pnl']:+,.0f}円")


if __name__ == "__main__":
    logger.info("バックテストログから日次データを抽出中...")
    trades_by_date = extract_trade_dates()

    if trades_by_date:
        logger.info(f"✓ {len(trades_by_date)}営業日分のデータを抽出")
        total_trades = sum(len(trades) for trades in trades_by_date.values())
        logger.info(f"✓ 総取引数: {total_trades}件")

        analyze_daily_performance(trades_by_date)
    else:
        logger.error("データ抽出に失敗しました")
