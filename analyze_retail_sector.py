"""
小売・消費セクター バックテスト

レンジボラティリティが高く、ブレイクアウト継続率も高い小売・消費セクターで
テクノロジーセクターと同等以上の成績が出るか検証
"""
import logging
from datetime import datetime, time
import pandas as pd
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from run_individual_backtest import STOCK_NAMES

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)


def main():
    # 最適パラメータ設定（テクノロジーセクターで最適化されたもの）
    params = {
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

    # 小売・消費セクター銘柄
    retail_symbols = [
        "9983.T",  # ファーストリテイリング
        "7974.T",  # 任天堂
        "3382.T",  # セブン&アイ
        "8267.T",  # イオン
        "2914.T",  # JT
        "4911.T",  # 資生堂
    ]

    # バックテスト期間（3ヶ月）
    start_date = datetime(2025, 8, 1)
    end_date = datetime(2025, 10, 31)

    print("=" * 100)
    print("小売・消費セクター バックテスト")
    print("=" * 100)
    print(f"期間: {start_date.date()} - {end_date.date()}")
    print(f"対象銘柄: {len(retail_symbols)}銘柄")
    print(f"利益確定: {params['profit_target']:.1%}、損切り: {params['stop_loss']:.1%}")
    print(f"初期資金: {params['initial_capital']:,}円 × {len(retail_symbols)}銘柄")
    print("=" * 100)
    print()

    # APIクライアント接続（DBキャッシュ使用）
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 全銘柄の全トレードを収集
    all_trades = []

    print("データ取得・バックテスト実行中...\n")

    for idx, symbol in enumerate(retail_symbols, 1):
        print(f"\r[{idx}/{len(retail_symbols)}] {STOCK_NAMES.get(symbol, symbol):25s}",
              end='', flush=True)

        try:
            engine = BacktestEngine(**params)
            results = engine.run_backtest(
                client=client,
                symbols=[symbol],
                start_date=start_date,
                end_date=end_date
            )

            # トレード詳細を取得
            if 'trades' in results and results['trades'] is not None:
                trades_data = results['trades']
                if isinstance(trades_data, pd.DataFrame):
                    if not trades_data.empty:
                        for _, trade in trades_data.iterrows():
                            trade_dict = trade.to_dict()
                            trade_dict['symbol'] = symbol
                            trade_dict['stock_name'] = STOCK_NAMES.get(symbol, symbol)
                            all_trades.append(trade_dict)
                elif isinstance(trades_data, list):
                    for trade in trades_data:
                        trade['symbol'] = symbol
                        trade['stock_name'] = STOCK_NAMES.get(symbol, symbol)
                        all_trades.append(trade)

        except Exception as e:
            logger.warning(f"\n{symbol} エラー: {e}")
            continue

    print("\n")
    client.disconnect()

    if not all_trades:
        print("トレードデータがありません")
        return

    # DataFrameに変換
    trades_df = pd.DataFrame(all_trades)

    print(f"\nトレードデータ取得完了: {len(all_trades)}件")
    print(f"カラム: {trades_df.columns.tolist()}\n")

    # entry_time を日付に変換
    trades_df['entry_date'] = pd.to_datetime(trades_df['entry_time']).dt.date
    trades_df['exit_date'] = pd.to_datetime(trades_df['exit_time']).dt.date

    # 月の追加
    trades_df['month'] = pd.to_datetime(trades_df['entry_date']).dt.to_period('M')

    # direction と exit_reason カラムの存在チェック
    has_direction = 'direction' in trades_df.columns
    has_side = 'side' in trades_df.columns
    has_exit_reason = 'exit_reason' in trades_df.columns
    has_reason = 'reason' in trades_df.columns

    # 日次集計（エントリー日基準）
    agg_dict = {'pnl': ['sum', 'count']}

    if has_direction:
        agg_dict['direction'] = lambda x: (x == 'LONG').sum()
    elif has_side:
        agg_dict['side'] = lambda x: (x == 'LONG').sum()

    if has_exit_reason:
        agg_dict['exit_reason'] = lambda x: (x == 'profit_target').sum()
    elif has_reason:
        agg_dict['reason'] = lambda x: (x == 'profit').sum()

    daily_stats = trades_df.groupby('entry_date').agg(agg_dict).reset_index()

    # カラム名を動的に設定
    col_names = ['date', 'pnl', 'trades']
    if has_direction or has_side:
        col_names.append('long_count')
    if has_exit_reason or has_reason:
        col_names.append('profit_target_count')

    daily_stats.columns = col_names

    # LONG/SHORT カウント
    if has_direction or has_side:
        daily_stats['short_count'] = daily_stats['trades'] - daily_stats['long_count']
    else:
        daily_stats['long_count'] = 0
        daily_stats['short_count'] = 0

    # 勝数と勝率
    daily_stats['win_count'] = trades_df.groupby('entry_date')['pnl'].apply(lambda x: (x > 0).sum()).values
    daily_stats['win_rate'] = daily_stats['win_count'] / daily_stats['trades']

    # 利確数がない場合は0で埋める
    if 'profit_target_count' not in daily_stats.columns:
        daily_stats['profit_target_count'] = 0

    # 累積損益
    daily_stats['cumulative_pnl'] = daily_stats['pnl'].cumsum()

    # 月別追加
    daily_stats['month'] = pd.to_datetime(daily_stats['date']).dt.to_period('M')

    print("\n" + "=" * 100)
    print("📅 日次パフォーマンス詳細")
    print("=" * 100)

    # 月ごとに表示
    for month in sorted(daily_stats['month'].unique()):
        month_data = daily_stats[daily_stats['month'] == month].copy()
        month_total_pnl = month_data['pnl'].sum()
        month_total_trades = month_data['trades'].sum()
        month_avg_win_rate = month_data['win_rate'].mean()

        print(f"\n{'─' * 100}")
        print(f"📆 {month} ({len(month_data)}営業日)")
        print(f"   月間損益: {month_total_pnl:+,.0f}円 | 取引数: {month_total_trades}回 | 平均勝率: {month_avg_win_rate:.1%}")
        print(f"{'─' * 100}")
        print(f"{'日付':^12s} {'取引数':>6s} {'LONG':>5s} {'SHORT':>5s} {'勝数':>5s} {'勝率':>7s} "
              f"{'日次損益':>14s} {'累積損益':>14s}")
        print("─" * 100)

        for _, row in month_data.iterrows():
            symbol = "✅" if row['pnl'] > 0 else "❌" if row['pnl'] < 0 else "➖"
            date_str = str(row['date'])

            print(f"{symbol} {date_str:10s} "
                  f"{int(row['trades']):>6d} "
                  f"{int(row['long_count']):>5d} "
                  f"{int(row['short_count']):>5d} "
                  f"{int(row['win_count']):>5d} "
                  f"{row['win_rate']:>6.1%} "
                  f"{row['pnl']:>+13,.0f}円 "
                  f"{row['cumulative_pnl']:>+13,.0f}円")

    # 全期間サマリー
    print("\n" + "=" * 100)
    print("📊 全期間サマリー（3ヶ月）")
    print("=" * 100)

    total_pnl = daily_stats['pnl'].sum()
    total_trades = daily_stats['trades'].sum()
    profitable_days = (daily_stats['pnl'] > 0).sum()
    loss_days = (daily_stats['pnl'] < 0).sum()
    breakeven_days = (daily_stats['pnl'] == 0).sum()
    avg_daily_pnl = daily_stats['pnl'].mean()
    max_daily_gain = daily_stats['pnl'].max()
    max_daily_loss = daily_stats['pnl'].min()
    best_day = daily_stats.loc[daily_stats['pnl'].idxmax(), 'date']
    worst_day = daily_stats.loc[daily_stats['pnl'].idxmin(), 'date']

    total_investment = params['initial_capital'] * len(retail_symbols)
    total_return = total_pnl / total_investment

    print(f"\n総損益:          {total_pnl:+,.0f}円")
    print(f"総合リターン:    {total_return:+.2%}")
    print(f"総取引数:        {total_trades:,}回")
    print(f"営業日数:        {len(daily_stats)}日")
    print(f"  - 黒字日:      {profitable_days}日 ({profitable_days/len(daily_stats):.1%})")
    print(f"  - 損失日:      {loss_days}日 ({loss_days/len(daily_stats):.1%})")
    print(f"  - トントン:    {breakeven_days}日")
    print(f"\n平均日次損益:    {avg_daily_pnl:+,.0f}円")
    print(f"最大日次利益:    {max_daily_gain:+,.0f}円 ({best_day})")
    print(f"最大日次損失:    {max_daily_loss:+,.0f}円 ({worst_day})")

    # 月別サマリー
    print("\n" + "=" * 100)
    print("📅 月別サマリー")
    print("=" * 100)

    monthly_summary = daily_stats.groupby('month').agg({
        'pnl': ['sum', 'mean'],
        'trades': 'sum',
        'win_rate': 'mean',
        'date': 'count'  # 営業日数
    }).reset_index()

    monthly_summary.columns = ['month', 'total_pnl', 'avg_daily_pnl', 'trades', 'avg_win_rate', 'trading_days']

    print(f"\n{'月':^10s} {'営業日':>6s} {'取引数':>7s} {'平均勝率':>9s} {'月間損益':>15s} {'日平均損益':>15s} {'月次リターン':>12s}")
    print("─" * 100)

    for _, row in monthly_summary.iterrows():
        monthly_return = row['total_pnl'] / total_investment
        symbol = "✅" if row['total_pnl'] > 0 else "❌"

        print(f"{symbol} {str(row['month']):>10s} "
              f"{int(row['trading_days']):>6d} "
              f"{int(row['trades']):>7d} "
              f"{row['avg_win_rate']:>8.1%} "
              f"{row['total_pnl']:>+14,.0f}円 "
              f"{row['avg_daily_pnl']:>+14,.0f}円 "
              f"{monthly_return:>+11.2%}")

    print("\n" + "=" * 100)

    # テクノロジーセクターとの比較
    print("\n" + "=" * 100)
    print("📈 テクノロジーセクターとの比較")
    print("=" * 100)

    tech_total_return = 0.0464  # テクノロジー16銘柄の実績
    tech_daily_profit = 119711  # テクノロジー16銘柄の日平均利益
    tech_win_rate = 0.548       # テクノロジー16銘柄の日次勝率

    print(f"\n{'指標':20s} {'小売・消費':>15s} {'テクノロジー':>15s} {'差分':>15s}")
    print("─" * 70)
    print(f"{'総合リターン':20s} {total_return:>14.2%} {tech_total_return:>14.2%} {total_return - tech_total_return:>+14.2%}")
    print(f"{'日平均利益':20s} {avg_daily_pnl:>14,.0f}円 {tech_daily_profit:>14,.0f}円 {avg_daily_pnl - tech_daily_profit:>+14,.0f}円")
    print(f"{'日次勝率':20s} {profitable_days/len(daily_stats):>14.1%} {tech_win_rate:>14.1%} {profitable_days/len(daily_stats) - tech_win_rate:>+14.1%}")

    # CSV出力
    csv_filename = f"results/optimization/retail_daily_performance_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    daily_stats_export = daily_stats.copy()
    daily_stats_export['month'] = daily_stats_export['month'].astype(str)
    daily_stats_export.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"\n✓ 日次データを {csv_filename} に保存しました")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
