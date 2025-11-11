"""
セクター別特性分析スクリプト

なぜテクノロジー・通信セクターでオープンレンジブレイクアウト戦略が
特に効果的なのかを定量的に分析する

分析項目:
1. ボラティリティ（日次、イントラデイ、オープンレンジ）
2. レンジブレイクアウト後のトレンド継続性
3. 流動性（取引高、価格インパクト）
4. セクター別のブレイクアウト成功率
"""
import logging
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, time
from collections import defaultdict
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from run_individual_backtest import SECTORS, STOCK_NAMES, get_sector

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)


def calculate_intraday_metrics(client, symbol, start_date, end_date):
    """
    イントラデイ指標の計算

    Returns:
        dict: {
            'avg_daily_volatility': 日次ボラティリティ（終値ベース）
            'avg_range_volatility': オープンレンジのボラティリティ
            'avg_intraday_range': イントラデイの高値-安値の平均
            'avg_volume': 平均出来高
            'breakout_continuation_rate': ブレイクアウト後の継続率
        }
    """
    try:
        # 1分足データ取得
        df = client.get_intraday_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval='1min'
        )

        if df is None or df.empty:
            return None

        # 日付カラム追加
        df['date'] = pd.to_datetime(df.index).date

        # 日次集計
        daily_stats = []

        for date, day_data in df.groupby('date'):
            # 終値の日次リターン計算用に前日終値を取得
            # 前営業日の終値
            prev_close = None
            if len(daily_stats) > 0:
                prev_close = daily_stats[-1]['close']

            if day_data.empty:
                continue

            # 基本統計
            day_open = day_data.iloc[0]['open']
            day_close = day_data.iloc[-1]['close']
            day_high = day_data['high'].max()
            day_low = day_data['low'].min()
            day_volume = day_data['volume'].sum()

            # オープンレンジ（09:05-09:15 JST = 00:05-00:15 UTC）の抽出
            range_start = pd.Timestamp.combine(date, time(0, 5))
            range_end = pd.Timestamp.combine(date, time(0, 15))

            range_data = day_data[(day_data.index >= range_start) & (day_data.index < range_end)]

            if not range_data.empty:
                range_high = range_data['high'].max()
                range_low = range_data['low'].min()
                range_size = (range_high - range_low) / day_open if day_open > 0 else 0

                # ブレイクアウト判定（09:15以降のデータ）
                post_range_data = day_data[day_data.index >= range_end]
                if not post_range_data.empty:
                    # 上方ブレイクアウト
                    upper_break = post_range_data[post_range_data['high'] > range_high]
                    # 下方ブレイクアウト
                    lower_break = post_range_data[post_range_data['low'] < range_low]

                    # ブレイクアウト後の継続性
                    breakout_continuation = None
                    if not upper_break.empty:
                        # 最初のブレイクアウト時刻
                        break_time = upper_break.index[0]
                        # ブレイクアウト後1時間のデータ
                        post_break = post_range_data[
                            (post_range_data.index >= break_time) &
                            (post_range_data.index < break_time + pd.Timedelta(hours=1))
                        ]
                        if not post_break.empty:
                            # 継続性: ブレイクアウト後の平均価格がレンジ上限より上か
                            avg_price_post_break = post_break['close'].mean()
                            breakout_continuation = 1 if avg_price_post_break > range_high else 0

                    elif not lower_break.empty:
                        break_time = lower_break.index[0]
                        post_break = post_range_data[
                            (post_range_data.index >= break_time) &
                            (post_range_data.index < break_time + pd.Timedelta(hours=1))
                        ]
                        if not post_break.empty:
                            avg_price_post_break = post_break['close'].mean()
                            breakout_continuation = 1 if avg_price_post_break < range_low else 0
                else:
                    range_size = 0
                    breakout_continuation = None
            else:
                range_size = 0
                breakout_continuation = None

            daily_stats.append({
                'date': date,
                'open': day_open,
                'close': day_close,
                'high': day_high,
                'low': day_low,
                'volume': day_volume,
                'prev_close': prev_close,
                'intraday_range': (day_high - day_low) / day_open if day_open > 0 else 0,
                'range_size': range_size,
                'breakout_continuation': breakout_continuation
            })

        if not daily_stats:
            return None

        stats_df = pd.DataFrame(daily_stats)

        # 日次リターン計算
        returns = []
        for i in range(1, len(stats_df)):
            prev_close = stats_df.iloc[i-1]['close']
            curr_close = stats_df.iloc[i]['close']
            if prev_close > 0:
                returns.append((curr_close - prev_close) / prev_close)

        # 集計
        metrics = {
            'avg_daily_volatility': np.std(returns) if returns else 0,
            'avg_range_volatility': stats_df['range_size'].mean(),
            'avg_intraday_range': stats_df['intraday_range'].mean(),
            'avg_volume': stats_df['volume'].mean(),
            'breakout_continuation_rate': stats_df['breakout_continuation'].dropna().mean() if stats_df['breakout_continuation'].notna().any() else 0,
            'trading_days': len(stats_df)
        }

        return metrics

    except Exception as e:
        logger.warning(f"{symbol} メトリクス計算エラー: {e}")
        return None


def main():
    # バックテスト期間
    start_date = datetime(2025, 10, 1)
    end_date = datetime(2025, 10, 31)

    print("=" * 100)
    print("セクター別特性分析")
    print("=" * 100)
    print(f"期間: {start_date.date()} - {end_date.date()}\n")

    # APIクライアント接続
    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # セクター別の集計
    sector_metrics = defaultdict(list)

    # 全銘柄分析
    all_symbols = []
    for sector, symbols in SECTORS.items():
        all_symbols.extend([(symbol, sector) for symbol in symbols])

    print(f"分析対象: {len(all_symbols)}銘柄\n")

    for idx, (symbol, sector) in enumerate(all_symbols, 1):
        stock_name = STOCK_NAMES.get(symbol, symbol)
        print(f"\r[{idx}/{len(all_symbols)}] {stock_name:20s} ({sector:15s})", end='', flush=True)

        metrics = calculate_intraday_metrics(client, symbol, start_date, end_date)

        if metrics:
            metrics['symbol'] = symbol
            metrics['stock_name'] = stock_name
            metrics['sector'] = sector
            sector_metrics[sector].append(metrics)

    print("\n\n" + "=" * 100)
    print("セクター別分析結果")
    print("=" * 100)

    # セクター別集計
    sector_summary = []

    for sector in sorted(sector_metrics.keys()):
        metrics_list = sector_metrics[sector]

        if not metrics_list:
            continue

        # 平均値計算
        avg_daily_vol = np.mean([m['avg_daily_volatility'] for m in metrics_list])
        avg_range_vol = np.mean([m['avg_range_volatility'] for m in metrics_list])
        avg_intraday_range = np.mean([m['avg_intraday_range'] for m in metrics_list])
        avg_volume = np.mean([m['avg_volume'] for m in metrics_list])
        avg_continuation = np.mean([m['breakout_continuation_rate'] for m in metrics_list])

        sector_summary.append({
            'sector': sector,
            'count': len(metrics_list),
            'avg_daily_volatility': avg_daily_vol,
            'avg_range_volatility': avg_range_vol,
            'avg_intraday_range': avg_intraday_range,
            'avg_volume': avg_volume,
            'breakout_continuation_rate': avg_continuation
        })

    # ボラティリティでソート
    sector_summary.sort(key=lambda x: x['avg_range_volatility'], reverse=True)

    print("\n【ボラティリティ分析】")
    print(f"\n{'セクター':15s} {'銘柄数':>6s} {'日次ボラ':>10s} {'レンジボラ':>10s} "
          f"{'日中レンジ':>10s} {'平均出来高':>12s} {'継続率':>8s}")
    print("-" * 100)

    for summary in sector_summary:
        print(f"{summary['sector']:15s} "
              f"{summary['count']:>6d} "
              f"{summary['avg_daily_volatility']:>9.2%} "
              f"{summary['avg_range_volatility']:>9.2%} "
              f"{summary['avg_intraday_range']:>9.2%} "
              f"{summary['avg_volume']:>12,.0f} "
              f"{summary['breakout_continuation_rate']:>7.1%}")

    # テクノロジーセクターのハイライト
    tech_summary = next((s for s in sector_summary if s['sector'] == 'テクノロジー・通信'), None)

    if tech_summary:
        print("\n" + "=" * 100)
        print("【テクノロジー・通信セクターの特徴】")
        print("=" * 100)

        # 各指標でのランキング
        rankings = {}

        for metric in ['avg_daily_volatility', 'avg_range_volatility', 'avg_intraday_range',
                       'avg_volume', 'breakout_continuation_rate']:
            sorted_sectors = sorted(sector_summary, key=lambda x: x[metric], reverse=True)
            rank = next((i+1 for i, s in enumerate(sorted_sectors) if s['sector'] == 'テクノロジー・通信'), None)
            rankings[metric] = (rank, len(sorted_sectors))

        print(f"\n日次ボラティリティ:      {tech_summary['avg_daily_volatility']:.2%} "
              f"(ランキング: {rankings['avg_daily_volatility'][0]}/{rankings['avg_daily_volatility'][1]})")
        print(f"レンジボラティリティ:    {tech_summary['avg_range_volatility']:.2%} "
              f"(ランキング: {rankings['avg_range_volatility'][0]}/{rankings['avg_range_volatility'][1]})")
        print(f"日中レンジ:              {tech_summary['avg_intraday_range']:.2%} "
              f"(ランキング: {rankings['avg_intraday_range'][0]}/{rankings['avg_intraday_range'][1]})")
        print(f"平均出来高:              {tech_summary['avg_volume']:,.0f}株 "
              f"(ランキング: {rankings['avg_volume'][0]}/{rankings['avg_volume'][1]})")
        print(f"ブレイクアウト継続率:    {tech_summary['breakout_continuation_rate']:.1%} "
              f"(ランキング: {rankings['breakout_continuation_rate'][0]}/{rankings['breakout_continuation_rate'][1]})")

    # 個別銘柄詳細（テクノロジーセクター）
    print("\n" + "=" * 100)
    print("【テクノロジー・通信セクター 個別銘柄詳細】")
    print("=" * 100)

    tech_stocks = sector_metrics['テクノロジー・通信']
    tech_stocks.sort(key=lambda x: x['avg_range_volatility'], reverse=True)

    print(f"\n{'銘柄名':20s} {'日次ボラ':>10s} {'レンジボラ':>10s} "
          f"{'日中レンジ':>10s} {'継続率':>8s}")
    print("-" * 100)

    for stock in tech_stocks:
        print(f"{stock['stock_name']:20s} "
              f"{stock['avg_daily_volatility']:>9.2%} "
              f"{stock['avg_range_volatility']:>9.2%} "
              f"{stock['avg_intraday_range']:>9.2%} "
              f"{stock['breakout_continuation_rate']:>7.1%}")

    # CSV保存
    all_data = []
    for sector, metrics_list in sector_metrics.items():
        all_data.extend(metrics_list)

    df = pd.DataFrame(all_data)
    csv_path = f"results/optimization/sector_characteristics_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    print(f"\n\n詳細データを {csv_path} に保存しました")

    client.disconnect()

    print("\n" + "=" * 100)
    print("分析完了")
    print("=" * 100)


if __name__ == "__main__":
    main()
