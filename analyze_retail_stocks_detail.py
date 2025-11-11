"""
小売・消費セクター 個別銘柄詳細分析

各銘柄の日次収益、標準偏差、シャープレシオなど詳細な統計を算出
"""
import logging
from datetime import datetime, time
import pandas as pd
import numpy as np
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


def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """シャープレシオを計算"""
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    excess_returns = returns - risk_free_rate
    return excess_returns.mean() / returns.std() * np.sqrt(252)  # 年率換算


def calculate_max_drawdown(cumulative_pnl):
    """最大ドローダウンを計算"""
    if len(cumulative_pnl) == 0:
        return 0.0

    running_max = cumulative_pnl.expanding().max()
    drawdown = cumulative_pnl - running_max
    return drawdown.min()


def analyze_stock_performance(trades_df, symbol, initial_capital):
    """
    個別銘柄のパフォーマンスを詳細分析

    Returns:
        dict: 詳細統計
    """
    stock_trades = trades_df[trades_df['symbol'] == symbol].copy()

    if stock_trades.empty:
        return None

    # 基本統計
    total_trades = len(stock_trades)
    winning_trades = stock_trades[stock_trades['pnl'] > 0]
    losing_trades = stock_trades[stock_trades['pnl'] < 0]

    win_count = len(winning_trades)
    win_rate = win_count / total_trades if total_trades > 0 else 0

    total_pnl = stock_trades['pnl'].sum()
    total_return = total_pnl / initial_capital

    # 勝ち/負けトレードの平均
    avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

    # プロフィットファクター
    gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
    gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    # 日次集計
    stock_trades['entry_date'] = pd.to_datetime(stock_trades['entry_time']).dt.date
    daily_pnl = stock_trades.groupby('entry_date')['pnl'].sum()

    # 日次統計
    avg_daily_pnl = daily_pnl.mean()
    std_daily_pnl = daily_pnl.std()

    # 日次リターン（初期資金に対する比率）
    daily_returns = daily_pnl / initial_capital

    # シャープレシオ
    sharpe = calculate_sharpe_ratio(daily_returns)

    # 累積損益
    cumulative_pnl = daily_pnl.cumsum()

    # 最大ドローダウン
    max_dd = calculate_max_drawdown(cumulative_pnl)
    max_dd_pct = max_dd / initial_capital if initial_capital > 0 else 0

    # 最終資産
    final_equity = initial_capital + total_pnl

    # 勝ち日/負け日
    profitable_days = (daily_pnl > 0).sum()
    loss_days = (daily_pnl < 0).sum()
    daily_win_rate = profitable_days / len(daily_pnl) if len(daily_pnl) > 0 else 0

    # 最大連勝/連敗
    wins = (stock_trades['pnl'] > 0).astype(int)
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0

    for win in wins:
        if win:
            current_wins += 1
            current_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_losses)

    # リスクリワード比
    risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

    # 利益確定と損切りの回数
    has_reason = 'reason' in stock_trades.columns
    has_exit_reason = 'exit_reason' in stock_trades.columns

    if has_reason:
        profit_target_exits = (stock_trades['reason'] == 'profit').sum()
        stop_loss_exits = (stock_trades['reason'] == 'stop').sum()
    elif has_exit_reason:
        profit_target_exits = (stock_trades['exit_reason'] == 'profit_target').sum()
        stop_loss_exits = (stock_trades['exit_reason'] == 'stop_loss').sum()
    else:
        profit_target_exits = 0
        stop_loss_exits = 0

    return {
        'symbol': symbol,
        'stock_name': STOCK_NAMES.get(symbol, symbol),

        # 基本統計
        'total_trades': total_trades,
        'win_count': win_count,
        'loss_count': total_trades - win_count,
        'win_rate': win_rate,

        # 損益統計
        'total_pnl': total_pnl,
        'total_return': total_return,
        'final_equity': final_equity,

        # トレード別統計
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'risk_reward': risk_reward,
        'profit_factor': profit_factor,

        # 日次統計
        'trading_days': len(daily_pnl),
        'profitable_days': profitable_days,
        'loss_days': loss_days,
        'daily_win_rate': daily_win_rate,
        'avg_daily_pnl': avg_daily_pnl,
        'std_daily_pnl': std_daily_pnl,

        # リスク指標
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'max_drawdown_pct': max_dd_pct,

        # 連続統計
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,

        # エグジット理由
        'profit_target_exits': profit_target_exits,
        'stop_loss_exits': stop_loss_exits,

        # 総利益/総損失
        'gross_profit': gross_profit,
        'gross_loss': gross_loss
    }


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

    # 小売・消費セクター銘柄（出来高順）
    retail_symbols = [
        ("8267.T", 7501245),    # イオン - 最大出来高
        ("3382.T", 4239982),    # セブン&アイ
        ("7974.T", 3082555),    # 任天堂
        ("2914.T", 2337664),    # JT
        ("4911.T", 1863255),    # 資生堂
        ("9983.T", 1046991),    # ファーストリテイリング
    ]

    # 銘柄特性データ（sector_characteristics.csvから）
    stock_characteristics = {
        "9983.T": {"range_vol": 0.0069, "continuation": 0.50, "volume": 1046991},
        "7974.T": {"range_vol": 0.0079, "continuation": 0.57, "volume": 3082555},
        "3382.T": {"range_vol": 0.0050, "continuation": 0.76, "volume": 4239982},
        "8267.T": {"range_vol": 0.0111, "continuation": 0.81, "volume": 7501245},
        "2914.T": {"range_vol": 0.0040, "continuation": 0.71, "volume": 2337664},
        "4911.T": {"range_vol": 0.0064, "continuation": 0.48, "volume": 1863255},
    }

    # バックテスト期間（3ヶ月）
    start_date = datetime(2025, 8, 1)
    end_date = datetime(2025, 10, 31)

    print("=" * 120)
    print("小売・消費セクター 個別銘柄詳細分析")
    print("=" * 120)
    print(f"期間: {start_date.date()} - {end_date.date()}")
    print(f"対象銘柄: {len(retail_symbols)}銘柄")
    print(f"初期資金: {params['initial_capital']:,}円")
    print("=" * 120)
    print()

    # APIクライアント接続
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 全銘柄のトレードデータ収集
    all_trades = []

    print("バックテスト実行中...\n")

    for idx, (symbol, _) in enumerate(retail_symbols, 1):
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

    # 各銘柄を詳細分析
    stock_analyses = []

    for symbol, _ in retail_symbols:
        analysis = analyze_stock_performance(trades_df, symbol, params['initial_capital'])
        if analysis:
            # 銘柄特性を追加
            if symbol in stock_characteristics:
                analysis.update(stock_characteristics[symbol])
            stock_analyses.append(analysis)

    # DataFrameに変換
    analysis_df = pd.DataFrame(stock_analyses)

    # ソート（総合リターン順）
    analysis_df = analysis_df.sort_values('total_return', ascending=False)

    print("=" * 120)
    print("📊 個別銘柄 詳細パフォーマンス")
    print("=" * 120)

    # 基本統計
    print("\n【基本統計】")
    print(f"\n{'銘柄':20s} {'取引数':>6s} {'勝数':>5s} {'勝率':>7s} {'総損益':>14s} "
          f"{'リターン':>9s} {'PF':>6s}")
    print("-" * 120)

    for _, row in analysis_df.iterrows():
        print(f"{row['stock_name']:20s} "
              f"{int(row['total_trades']):>6d} "
              f"{int(row['win_count']):>5d} "
              f"{row['win_rate']:>6.1%} "
              f"{row['total_pnl']:>+13,.0f}円 "
              f"{row['total_return']:>+8.2%} "
              f"{row['profit_factor']:>6.2f}")

    # リスク・リターン統計
    print("\n【リスク・リターン統計】")
    print(f"\n{'銘柄':20s} {'日平均損益':>12s} {'標準偏差':>12s} {'シャープ':>8s} "
          f"{'最大DD':>12s} {'DD%':>7s}")
    print("-" * 120)

    for _, row in analysis_df.iterrows():
        print(f"{row['stock_name']:20s} "
              f"{row['avg_daily_pnl']:>+11,.0f}円 "
              f"{row['std_daily_pnl']:>11,.0f}円 "
              f"{row['sharpe_ratio']:>8.2f} "
              f"{row['max_drawdown']:>+11,.0f}円 "
              f"{row['max_drawdown_pct']:>6.2%}")

    # トレード詳細
    print("\n【トレード詳細】")
    print(f"\n{'銘柄':20s} {'平均利益':>12s} {'平均損失':>12s} {'RR比':>6s} "
          f"{'利確回数':>8s} {'損切回数':>8s}")
    print("-" * 120)

    for _, row in analysis_df.iterrows():
        print(f"{row['stock_name']:20s} "
              f"{row['avg_win']:>+11,.0f}円 "
              f"{row['avg_loss']:>+11,.0f}円 "
              f"{row['risk_reward']:>6.2f} "
              f"{int(row['profit_target_exits']):>8d} "
              f"{int(row['stop_loss_exits']):>8d}")

    # 日次統計
    print("\n【日次統計】")
    print(f"\n{'銘柄':20s} {'取引日数':>8s} {'黒字日':>7s} {'損失日':>7s} "
          f"{'日次勝率':>9s} {'最大連勝':>8s} {'最大連敗':>8s}")
    print("-" * 120)

    for _, row in analysis_df.iterrows():
        print(f"{row['stock_name']:20s} "
              f"{int(row['trading_days']):>8d} "
              f"{int(row['profitable_days']):>7d} "
              f"{int(row['loss_days']):>7d} "
              f"{row['daily_win_rate']:>8.1%} "
              f"{int(row['max_consecutive_wins']):>8d} "
              f"{int(row['max_consecutive_losses']):>8d}")

    # 銘柄特性との相関分析
    print("\n" + "=" * 120)
    print("🔍 銘柄特性との相関分析")
    print("=" * 120)

    print(f"\n{'銘柄':20s} {'出来高':>12s} {'レンジボラ':>10s} {'継続率':>8s} "
          f"{'リターン':>9s} {'シャープ':>8s}")
    print("-" * 120)

    for _, row in analysis_df.iterrows():
        print(f"{row['stock_name']:20s} "
              f"{row['volume']:>12,.0f} "
              f"{row['range_vol']:>9.2%} "
              f"{row['continuation']:>7.1%} "
              f"{row['total_return']:>+8.2%} "
              f"{row['sharpe_ratio']:>8.2f}")

    # 相関係数を計算
    print("\n【相関係数】")
    correlations = {
        'リターン vs 出来高': analysis_df['total_return'].corr(analysis_df['volume']),
        'リターン vs レンジボラ': analysis_df['total_return'].corr(analysis_df['range_vol']),
        'リターン vs 継続率': analysis_df['total_return'].corr(analysis_df['continuation']),
        'シャープ vs 出来高': analysis_df['sharpe_ratio'].corr(analysis_df['volume']),
        'シャープ vs レンジボラ': analysis_df['sharpe_ratio'].corr(analysis_df['range_vol']),
        'シャープ vs 継続率': analysis_df['sharpe_ratio'].corr(analysis_df['continuation']),
    }

    for label, corr in correlations.items():
        print(f"{label:30s}: {corr:+.3f}")

    # サマリー
    print("\n" + "=" * 120)
    print("📈 ポートフォリオサマリー")
    print("=" * 120)

    total_pnl = analysis_df['total_pnl'].sum()
    total_investment = params['initial_capital'] * len(retail_symbols)
    portfolio_return = total_pnl / total_investment

    # ポートフォリオレベルのシャープレシオ
    all_daily_returns = []
    for symbol, _ in retail_symbols:
        stock_trades = trades_df[trades_df['symbol'] == symbol].copy()
        if not stock_trades.empty:
            stock_trades['entry_date'] = pd.to_datetime(stock_trades['entry_time']).dt.date
            daily_pnl = stock_trades.groupby('entry_date')['pnl'].sum()
            daily_returns = daily_pnl / params['initial_capital']
            all_daily_returns.append(daily_returns)

    if all_daily_returns:
        portfolio_daily_returns = pd.concat(all_daily_returns).groupby(level=0).sum()
        portfolio_sharpe = calculate_sharpe_ratio(portfolio_daily_returns)
    else:
        portfolio_sharpe = 0.0

    print(f"\n総投資額:        {total_investment:,}円")
    print(f"総損益:          {total_pnl:+,.0f}円")
    print(f"ポートフォリオリターン: {portfolio_return:+.2%}")
    print(f"ポートフォリオシャープ: {portfolio_sharpe:.2f}")
    print(f"\n黒字銘柄数:      {(analysis_df['total_pnl'] > 0).sum()}/{len(analysis_df)}")
    print(f"平均シャープ:    {analysis_df['sharpe_ratio'].mean():.2f}")

    # ベスト/ワースト
    print("\n【ベスト3銘柄（リターン）】")
    for i, (_, row) in enumerate(analysis_df.head(3).iterrows(), 1):
        print(f"{i}. {row['stock_name']:15s}: {row['total_return']:+.2%} "
              f"(シャープ: {row['sharpe_ratio']:.2f})")

    print("\n【ワースト3銘柄（リターン）】")
    for i, (_, row) in enumerate(analysis_df.tail(3).iterrows(), 1):
        print(f"{i}. {row['stock_name']:15s}: {row['total_return']:+.2%} "
              f"(シャープ: {row['sharpe_ratio']:.2f})")

    # CSV出力
    csv_filename = f"results/optimization/retail_stock_detail_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    analysis_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"\n✓ 詳細データを {csv_filename} に保存しました")

    print("\n" + "=" * 120)


if __name__ == "__main__":
    main()
