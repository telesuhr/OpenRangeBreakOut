"""
高ボラティリティテクノロジー銘柄 バックテスト & 可視化

レンジボラティリティ0.7%以上のテクノロジー銘柄のみで検証
結果をグラフ化して分析
"""
import logging
from datetime import datetime, time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from run_individual_backtest import STOCK_NAMES

# 日本語フォント設定
rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)


def create_visualizations(daily_stats, stock_analyses, params):
    """
    バックテスト結果の可視化

    Args:
        daily_stats: 日次統計データ
        stock_analyses: 銘柄別分析データ
        params: バックテストパラメータ
    """
    fig = plt.figure(figsize=(20, 12))

    # 1. 累積損益曲線
    ax1 = plt.subplot(3, 3, 1)
    dates = pd.to_datetime(daily_stats['date'])
    ax1.plot(dates, daily_stats['cumulative_pnl'] / 1000000, linewidth=2, color='#2E86AB')
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.set_title('Cumulative P&L (3-month)', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('P&L (Million JPY)')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # 2. 月別損益
    ax2 = plt.subplot(3, 3, 2)
    monthly = daily_stats.groupby('month')['pnl'].sum() / 1000000
    colors = ['#06A77D' if x > 0 else '#D62828' for x in monthly.values]
    bars = ax2.bar(range(len(monthly)), monthly.values, color=colors, alpha=0.7)
    ax2.set_title('Monthly P&L', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Month')
    ax2.set_ylabel('P&L (Million JPY)')
    ax2.set_xticks(range(len(monthly)))
    ax2.set_xticklabels([str(m) for m in monthly.index])
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.grid(True, alpha=0.3, axis='y')

    # 値ラベル
    for i, (bar, val) in enumerate(zip(bars, monthly.values)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}M',
                ha='center', va='bottom' if val > 0 else 'top', fontsize=9)

    # 3. 個別銘柄パフォーマンス
    ax3 = plt.subplot(3, 3, 3)
    stock_returns = [(s['stock_name'], s['total_return']*100) for s in stock_analyses]
    stock_returns.sort(key=lambda x: x[1], reverse=True)
    names = [s[0] for s in stock_returns]
    returns = [s[1] for s in stock_returns]
    colors = ['#06A77D' if r > 0 else '#D62828' for r in returns]

    bars = ax3.barh(range(len(names)), returns, color=colors, alpha=0.7)
    ax3.set_title('Stock Performance (Return %)', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Return (%)')
    ax3.set_yticks(range(len(names)))
    ax3.set_yticklabels(names, fontsize=9)
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax3.grid(True, alpha=0.3, axis='x')

    # 値ラベル
    for i, (bar, val) in enumerate(zip(bars, returns)):
        width = bar.get_width()
        ax3.text(width, bar.get_y() + bar.get_height()/2.,
                f'{val:+.2f}%',
                ha='left' if val > 0 else 'right', va='center', fontsize=8)

    # 4. レンジボラティリティ vs リターン散布図
    ax4 = plt.subplot(3, 3, 4)
    range_vols = [s['range_vol']*100 for s in stock_analyses]
    returns = [s['total_return']*100 for s in stock_analyses]
    names = [s['stock_name'] for s in stock_analyses]

    scatter = ax4.scatter(range_vols, returns, s=100, alpha=0.6, c=returns,
                          cmap='RdYlGn', edgecolors='black', linewidth=1)

    # 銘柄名ラベル
    for i, name in enumerate(names):
        ax4.annotate(name, (range_vols[i], returns[i]),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, alpha=0.8)

    # トレンドライン
    z = np.polyfit(range_vols, returns, 1)
    p = np.poly1d(z)
    ax4.plot(range_vols, p(range_vols), "r--", alpha=0.5, linewidth=2)

    ax4.set_title('Range Volatility vs Return', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Range Volatility (%)')
    ax4.set_ylabel('Return (%)')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

    # 相関係数を表示
    corr = np.corrcoef(range_vols, returns)[0, 1]
    ax4.text(0.05, 0.95, f'Correlation: {corr:.3f}',
            transform=ax4.transAxes, fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 5. 日次勝率の推移（移動平均）
    ax5 = plt.subplot(3, 3, 5)
    daily_stats['win_indicator'] = (daily_stats['pnl'] > 0).astype(int)
    daily_stats['win_rate_ma'] = daily_stats['win_indicator'].rolling(window=10, min_periods=1).mean()

    dates = pd.to_datetime(daily_stats['date'])
    ax5.plot(dates, daily_stats['win_rate_ma']*100, linewidth=2, color='#F77F00')
    ax5.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50%')
    ax5.set_title('Daily Win Rate (10-day MA)', fontsize=14, fontweight='bold')
    ax5.set_xlabel('Date')
    ax5.set_ylabel('Win Rate (%)')
    ax5.set_ylim(0, 100)
    ax5.grid(True, alpha=0.3)
    ax5.legend()
    ax5.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)

    # 6. ドローダウン
    ax6 = plt.subplot(3, 3, 6)
    cumulative = daily_stats['cumulative_pnl']
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / 1000000

    dates = pd.to_datetime(daily_stats['date'])
    ax6.fill_between(dates, 0, drawdown, color='#D62828', alpha=0.3)
    ax6.plot(dates, drawdown, color='#D62828', linewidth=2)
    ax6.set_title('Drawdown', fontsize=14, fontweight='bold')
    ax6.set_xlabel('Date')
    ax6.set_ylabel('Drawdown (Million JPY)')
    ax6.grid(True, alpha=0.3)
    ax6.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.setp(ax6.xaxis.get_majorticklabels(), rotation=45)

    # 7. 銘柄別シャープレシオ
    ax7 = plt.subplot(3, 3, 7)
    sharpes = [(s['stock_name'], s['sharpe_ratio']) for s in stock_analyses]
    sharpes.sort(key=lambda x: x[1], reverse=True)
    names = [s[0] for s in sharpes]
    values = [s[1] for s in sharpes]
    colors = ['#06A77D' if v > 0 else '#D62828' for v in values]

    bars = ax7.barh(range(len(names)), values, color=colors, alpha=0.7)
    ax7.set_title('Sharpe Ratio by Stock', fontsize=14, fontweight='bold')
    ax7.set_xlabel('Sharpe Ratio')
    ax7.set_yticks(range(len(names)))
    ax7.set_yticklabels(names, fontsize=9)
    ax7.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax7.grid(True, alpha=0.3, axis='x')

    # 値ラベル
    for bar, val in zip(bars, values):
        width = bar.get_width()
        ax7.text(width, bar.get_y() + bar.get_height()/2.,
                f'{val:.2f}',
                ha='left' if val > 0 else 'right', va='center', fontsize=8)

    # 8. 日次損益分布
    ax8 = plt.subplot(3, 3, 8)
    pnl_values = daily_stats['pnl'] / 1000
    ax8.hist(pnl_values, bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
    ax8.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Zero')
    ax8.axvline(x=pnl_values.mean(), color='green', linestyle='--', linewidth=2,
               label=f'Mean: {pnl_values.mean():.1f}k')
    ax8.set_title('Daily P&L Distribution', fontsize=14, fontweight='bold')
    ax8.set_xlabel('Daily P&L (Thousand JPY)')
    ax8.set_ylabel('Frequency')
    ax8.legend()
    ax8.grid(True, alpha=0.3, axis='y')

    # 9. サマリーテキスト
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis('off')

    total_pnl = daily_stats['pnl'].sum()
    total_investment = params['initial_capital'] * len(stock_analyses)
    total_return = total_pnl / total_investment
    avg_daily_pnl = daily_stats['pnl'].mean()
    std_daily_pnl = daily_stats['pnl'].std()
    win_days = (daily_stats['pnl'] > 0).sum()
    total_days = len(daily_stats)
    daily_win_rate = win_days / total_days
    max_dd = drawdown.min() * 1000000

    # ポートフォリオシャープレシオ
    daily_returns = daily_stats['pnl'] / total_investment
    portfolio_sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0

    summary_text = f"""
PERFORMANCE SUMMARY

Period: {daily_stats['date'].min()} - {daily_stats['date'].max()}
Stocks: {len(stock_analyses)} (High Vol Tech)

Total Investment: ¥{total_investment:,.0f}
Total P&L: ¥{total_pnl:+,.0f}
Total Return: {total_return:+.2%}

Daily Statistics:
  Avg Daily P&L: ¥{avg_daily_pnl:+,.0f}
  Std Dev: ¥{std_daily_pnl:,.0f}
  Win Rate: {daily_win_rate:.1%} ({win_days}/{total_days})

Risk Metrics:
  Sharpe Ratio: {portfolio_sharpe:.2f}
  Max Drawdown: ¥{max_dd:+,.0f} ({max_dd/total_investment:.2%})

Stock Performance:
  Profitable: {sum(1 for s in stock_analyses if s['total_return'] > 0)}/{len(stock_analyses)}
  Avg Return: {np.mean([s['total_return'] for s in stock_analyses]):.2%}
  Best: {max(stock_analyses, key=lambda x: x['total_return'])['stock_name']} ({max(s['total_return'] for s in stock_analyses):.2%})
  Worst: {min(stock_analyses, key=lambda x: x['total_return'])['stock_name']} ({min(s['total_return'] for s in stock_analyses):.2%})
"""

    ax9.text(0.1, 0.9, summary_text, transform=ax9.transAxes,
            fontsize=10, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()

    # 保存
    filename = 'results/optimization/high_volatility_tech_analysis.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n✓ グラフを {filename} に保存しました")

    return filename


def main():
    # 最適パラメータ設定
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

    # 高ボラティリティテクノロジー銘柄（レンジボラ0.7%以上）
    high_vol_tech = [
        ("6920.T", 0.0104),  # レーザーテック
        ("6857.T", 0.0095),  # アドバンテスト
        ("8035.T", 0.0089),  # 東京エレクトロン
        ("6752.T", 0.0081),  # パナソニック
        ("9984.T", 0.0076),  # ソフトバンクG
        ("6762.T", 0.0073),  # TDK
        ("6758.T", 0.0071),  # ソニーグループ
    ]

    symbols = [s[0] for s in high_vol_tech]

    # バックテスト期間（3ヶ月）
    start_date = datetime(2025, 8, 1)
    end_date = datetime(2025, 10, 31)

    print("=" * 120)
    print("高ボラティリティテクノロジー銘柄 バックテスト（レンジボラ ≥ 0.7%）")
    print("=" * 120)
    print(f"期間: {start_date.date()} - {end_date.date()}")
    print(f"対象銘柄: {len(symbols)}銘柄")
    print()
    for symbol, range_vol in high_vol_tech:
        print(f"  - {STOCK_NAMES.get(symbol, symbol):20s} ({symbol}): レンジボラ {range_vol:.2%}")
    print(f"\n初期資金: {params['initial_capital']:,}円 × {len(symbols)}銘柄 = {params['initial_capital'] * len(symbols):,}円")
    print("=" * 120)
    print()

    # APIクライアント接続
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 全銘柄のトレードデータ収集
    all_trades = []

    print("バックテスト実行中...\n")

    for idx, (symbol, _) in enumerate(high_vol_tech, 1):
        print(f"\r[{idx}/{len(symbols)}] {STOCK_NAMES.get(symbol, symbol):25s}",
              end='', flush=True)

        try:
            engine = BacktestEngine(**params)
            results = engine.run_backtest(
                client=client,
                symbols=[symbol],
                start_date=start_date,
                end_date=end_date
            )

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
    print(f"トレードデータ取得完了: {len(all_trades)}件\n")

    # 日次集計
    trades_df['entry_date'] = pd.to_datetime(trades_df['entry_time']).dt.date
    trades_df['month'] = pd.to_datetime(trades_df['entry_date']).dt.to_period('M')

    daily_stats = trades_df.groupby('entry_date').agg({
        'pnl': ['sum', 'count']
    }).reset_index()
    daily_stats.columns = ['date', 'pnl', 'trades']
    daily_stats['cumulative_pnl'] = daily_stats['pnl'].cumsum()
    daily_stats['month'] = pd.to_datetime(daily_stats['date']).dt.to_period('M')

    # 銘柄別分析
    stock_analyses = []
    for symbol, range_vol in high_vol_tech:
        stock_trades = trades_df[trades_df['symbol'] == symbol]
        if not stock_trades.empty:
            total_pnl = stock_trades['pnl'].sum()
            total_return = total_pnl / params['initial_capital']

            # 日次統計
            daily_pnl = stock_trades.groupby('entry_date')['pnl'].sum()
            daily_returns = daily_pnl / params['initial_capital']
            sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0

            stock_analyses.append({
                'symbol': symbol,
                'stock_name': STOCK_NAMES.get(symbol, symbol),
                'total_pnl': total_pnl,
                'total_return': total_return,
                'sharpe_ratio': sharpe,
                'range_vol': range_vol,
                'total_trades': len(stock_trades)
            })

    # 結果表示
    print("=" * 120)
    print("📊 バックテスト結果")
    print("=" * 120)

    total_pnl = daily_stats['pnl'].sum()
    total_investment = params['initial_capital'] * len(symbols)
    total_return = total_pnl / total_investment

    print(f"\n総投資額: {total_investment:,}円")
    print(f"総損益: {total_pnl:+,.0f}円")
    print(f"総合リターン: {total_return:+.2%}")
    print(f"営業日数: {len(daily_stats)}日")
    print(f"総取引数: {daily_stats['trades'].sum()}回")

    # 個別銘柄サマリー
    print("\n【個別銘柄パフォーマンス】\n")
    stock_analyses_sorted = sorted(stock_analyses, key=lambda x: x['total_return'], reverse=True)

    print(f"{'銘柄':20s} {'取引数':>6s} {'損益':>14s} {'リターン':>9s} {'シャープ':>8s}")
    print("-" * 70)
    for stock in stock_analyses_sorted:
        print(f"{stock['stock_name']:20s} "
              f"{stock['total_trades']:>6d} "
              f"{stock['total_pnl']:>+13,.0f}円 "
              f"{stock['total_return']:>+8.2%} "
              f"{stock['sharpe_ratio']:>8.2f}")

    # 可視化
    print("\n" + "=" * 120)
    print("📈 結果を可視化中...")
    print("=" * 120)

    create_visualizations(daily_stats, stock_analyses, params)

    # CSV出力
    csv_filename = f"results/optimization/high_vol_tech_results_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    analysis_df = pd.DataFrame(stock_analyses)
    analysis_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"✓ 詳細データを {csv_filename} に保存しました")

    print("\n" + "=" * 120)
    print("✓ 分析完了")
    print("=" * 120)


if __name__ == "__main__":
    main()
