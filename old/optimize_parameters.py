"""
汎用パラメータ最適化スクリプト

使い方:
  python optimize_parameters.py --param profit_target
  python optimize_parameters.py --param stop_loss
  python optimize_parameters.py --param range_duration
  python optimize_parameters.py --param entry_window
  python optimize_parameters.py --all  # 全パラメータを個別に最適化
"""
import argparse
import yaml
import logging
import pandas as pd
from datetime import datetime, time, timedelta
from collections import defaultdict
from pathlib import Path
from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from run_individual_backtest import SECTORS, STOCK_NAMES, get_sector

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def load_optimization_config(config_path='config/optimization_config.yaml'):
    """最適化設定ファイルを読み込み"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def jst_to_utc_time(jst_time_str: str):
    """JST時刻文字列をUTC時刻オブジェクトに変換"""
    h, m = map(int, jst_time_str.split(':'))
    utc_hour = (h - 9) % 24
    return time(utc_hour, m)


def add_minutes_to_time(time_str: str, minutes: int):
    """時刻文字列に分を加算"""
    h, m = map(int, time_str.split(':'))
    dt = datetime(2000, 1, 1, h, m) + timedelta(minutes=minutes)
    return dt.strftime('%H:%M')


def get_parameter_values(opt_config, param_name):
    """指定パラメータの最適化値リストを取得"""
    if param_name not in opt_config['parameters']:
        raise ValueError(f"Unknown parameter: {param_name}")

    param_config = opt_config['parameters'][param_name]
    return param_config['values'], param_config.get('labels', param_config['values'])


def build_backtest_params(opt_config, param_name, param_value, base_config):
    """パラメータ値からバックテスト実行パラメータを構築"""
    params = {}

    # 固定パラメータ
    params['initial_capital'] = opt_config['fixed']['initial_capital']
    params['commission_rate'] = opt_config['fixed']['commission_rate']

    # レンジとエントリー時刻のデフォルト値（全パラメータ共通）
    range_start = opt_config['fixed']['range_start_time']
    range_duration = opt_config['parameters']['range_duration']['default']
    range_end = add_minutes_to_time(range_start, range_duration)
    entry_start = range_end
    entry_window = opt_config['parameters']['entry_window']['default']
    entry_end = add_minutes_to_time(entry_start, entry_window)

    params['range_start'] = jst_to_utc_time(range_start)
    params['range_end'] = jst_to_utc_time(range_end)
    params['entry_start'] = jst_to_utc_time(entry_start)
    params['entry_end'] = jst_to_utc_time(entry_end)

    # 最適化対象パラメータ
    if param_name == 'profit_target':
        params['profit_target'] = param_value
        params['stop_loss'] = opt_config['parameters']['stop_loss']['default']

    elif param_name == 'stop_loss':
        params['stop_loss'] = param_value
        params['profit_target'] = opt_config['parameters']['profit_target']['default']

    elif param_name == 'range_duration':
        # レンジ計測時間（分）を上書き
        range_end = add_minutes_to_time(range_start, param_value)
        params['range_end'] = jst_to_utc_time(range_end)

        # エントリー時刻も再計算
        entry_start = range_end
        entry_end = add_minutes_to_time(entry_start, entry_window)
        params['entry_start'] = jst_to_utc_time(entry_start)
        params['entry_end'] = jst_to_utc_time(entry_end)

        params['profit_target'] = opt_config['parameters']['profit_target']['default']
        params['stop_loss'] = opt_config['parameters']['stop_loss']['default']

    elif param_name == 'entry_window':
        # エントリーウィンドウ（分）を上書き
        entry_end = add_minutes_to_time(entry_start, param_value)
        params['entry_end'] = jst_to_utc_time(entry_end)

        params['profit_target'] = opt_config['parameters']['profit_target']['default']
        params['stop_loss'] = opt_config['parameters']['stop_loss']['default']

    elif param_name == 'force_exit_time':
        # 強制決済時刻を上書き
        params['force_exit_time'] = jst_to_utc_time(param_value)

        params['profit_target'] = opt_config['parameters']['profit_target']['default']
        params['stop_loss'] = opt_config['parameters']['stop_loss']['default']

    else:
        raise ValueError(f"Parameter {param_name} not implemented")

    # force_exit_timeのデフォルト設定
    if 'force_exit_time' not in params:
        params['force_exit_time'] = jst_to_utc_time(
            opt_config['parameters']['force_exit_time']['default']
        )

    return params


def optimize_parameter(param_name, opt_config, base_config, app_key):
    """指定パラメータの最適化を実行"""
    print("=" * 80)
    print(f"パラメータ最適化: {param_name}")
    print("=" * 80)
    print(f"説明: {opt_config['parameters'][param_name]['description']}")
    print(f"データ取得中（DBキャッシュ使用）...\n")

    # パラメータ値リスト取得
    param_values, param_labels = get_parameter_values(opt_config, param_name)

    # 全銘柄リスト
    all_symbols = []
    for symbols in SECTORS.values():
        all_symbols.extend(symbols)

    # セクターフィルタ
    sector_filter = opt_config.get('sectors', {}).get('filter')
    if sector_filter:
        all_symbols = [s for s in all_symbols if get_sector(s) in sector_filter]
        print(f"セクターフィルタ適用: {sector_filter}")
        print(f"対象銘柄数: {len(all_symbols)}\n")

    # バックテスト期間
    start_date = datetime.strptime(opt_config['fixed']['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(opt_config['fixed']['end_date'], '%Y-%m-%d')

    # クライアント初期化（キャッシュ使用）
    client = RefinitivClient(app_key=app_key, use_cache=True)
    client.connect()

    # 各パラメータ値での結果を保存
    results_by_param = {}

    for idx, (param_value, param_label) in enumerate(zip(param_values, param_labels), 1):
        print(f"\n{'='*80}")
        print(f"{param_name}: {param_label} ({idx}/{len(param_values)})")
        print(f"{'='*80}")

        # バックテストパラメータ構築
        bt_params = build_backtest_params(opt_config, param_name, param_value, base_config)

        # 各銘柄の結果を保存
        symbol_results = []

        for symbol_idx, symbol in enumerate(all_symbols, 1):
            print(f"\r[{symbol_idx}/{len(all_symbols)}] {STOCK_NAMES.get(symbol, symbol):20s}",
                  end='', flush=True)

            try:
                # バックテストエンジン初期化
                engine = BacktestEngine(**bt_params)

                # バックテスト実行
                results = engine.run_backtest(
                    client=client,
                    symbols=[symbol],
                    start_date=start_date,
                    end_date=end_date
                )

                # 結果を保存
                if results['total_trades'] > 0:
                    symbol_results.append({
                        'symbol': symbol,
                        'stock_name': STOCK_NAMES.get(symbol, symbol),
                        'sector': get_sector(symbol),
                        'total_trades': results['total_trades'],
                        'win_rate': results['win_rate'],
                        'total_return': results['total_return'],
                        'final_equity': results['final_equity'],
                        'pnl': results['final_equity'] - opt_config['fixed']['initial_capital']
                    })

            except Exception as e:
                logger.warning(f"\n{symbol} エラー: {e}")
                continue

        # 結果を保存
        results_by_param[param_label] = {
            'value': param_value,
            'results': symbol_results
        }
        print()  # 改行

    client.disconnect()

    return results_by_param


def analyze_results(results_by_param, param_name, opt_config):
    """最適化結果を分析"""
    print("\n" + "=" * 80)
    print(f"{param_name} 最適化結果サマリー")
    print("=" * 80)

    # サマリーテーブル作成
    summary_data = []

    for param_label, data in results_by_param.items():
        results = data['results']

        if not results:
            continue

        # 全体統計
        total_pnl = sum(r['pnl'] for r in results)
        total_trades = sum(r['total_trades'] for r in results)
        avg_win_rate = sum(r['win_rate'] for r in results) / len(results) if results else 0
        num_profitable = sum(1 for r in results if r['pnl'] > 0)

        # 投資額（銘柄数 × 初期資金）
        total_invested = opt_config['fixed']['initial_capital'] * len(results)
        total_return = (total_pnl / total_invested) if total_invested > 0 else 0

        summary_data.append({
            'param_label': param_label,
            'param_value': data['value'],
            'total_trades': total_trades,
            'avg_win_rate': avg_win_rate,
            'num_profitable': num_profitable,
            'total_symbols': len(results),
            'total_pnl': total_pnl,
            'total_return': total_return
        })

    # DataFrameに変換
    summary_df = pd.DataFrame(summary_data)

    if summary_df.empty:
        print("結果データがありません")
        return None

    # 結果表示
    print("\n【全体パフォーマンス】")
    print(f"\n{param_name:>15s} {'取引数':>8s} {'平均勝率':>10s} {'黒字銘柄':>10s} "
          f"{'総損益':>15s} {'総合リターン':>12s}")
    print("-" * 80)

    for _, row in summary_df.iterrows():
        symbol = "✅" if row['total_pnl'] > 0 else "❌"
        print(f"{symbol} {str(row['param_label']):>15s} "
              f"{int(row['total_trades']):>8d} "
              f"{row['avg_win_rate']:>9.1%} "
              f"{int(row['num_profitable']):>4d}/{int(row['total_symbols']):<3d} "
              f"{row['total_pnl']:>+14,.0f}円 "
              f"{row['total_return']:>+11.2%}")

    # 最適値を特定
    primary_metric = opt_config['optimization']['primary_metric']

    if primary_metric == 'total_return':
        best_idx = summary_df['total_return'].idxmax()
    elif primary_metric == 'total_pnl':
        best_idx = summary_df['total_pnl'].idxmax()
    elif primary_metric == 'win_rate':
        best_idx = summary_df['avg_win_rate'].idxmax()
    else:
        best_idx = summary_df['total_return'].idxmax()

    best_result = summary_df.loc[best_idx]

    print("\n" + "=" * 80)
    print(f"最適{param_name}")
    print("=" * 80)

    print(f"\n【{primary_metric}で最適】")
    print(f"  {param_name}: {best_result['param_label']}")
    print(f"  総損益: {best_result['total_pnl']:+,.0f}円")
    print(f"  総合リターン: {best_result['total_return']:+.2%}")
    print(f"  取引数: {int(best_result['total_trades']):,}回")
    print(f"  平均勝率: {best_result['avg_win_rate']:.1%}")
    print(f"  黒字銘柄: {int(best_result['num_profitable'])}/{int(best_result['total_symbols'])}")

    return summary_df


def main():
    parser = argparse.ArgumentParser(description='パラメータ最適化スクリプト')
    parser.add_argument('--param', type=str,
                       help='最適化するパラメータ名 (profit_target, stop_loss, range_duration, entry_window, force_exit_time)')
    parser.add_argument('--all', action='store_true',
                       help='全パラメータを個別に最適化')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='ベース設定ファイル（デフォルト: config/config.yaml）')
    parser.add_argument('--opt-config', type=str, default='config/optimization_config.yaml',
                       help='最適化設定ファイル（デフォルト: config/optimization_config.yaml）')

    args = parser.parse_args()

    # 設定ファイル読み込み
    with open(args.config, 'r', encoding='utf-8') as f:
        base_config = yaml.safe_load(f)

    opt_config = load_optimization_config(args.opt_config)

    app_key = "1475940198b04fdab9265b7892546cc2ead9eda6"

    # 出力ディレクトリ作成
    output_dir = Path(opt_config['output']['results_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        # 全パラメータを最適化
        all_params = list(opt_config['parameters'].keys())
        print(f"全パラメータを最適化: {all_params}\n")

        for param_name in all_params:
            results = optimize_parameter(param_name, opt_config, base_config, app_key)
            summary_df = analyze_results(results, param_name, opt_config)

            if summary_df is not None:
                # CSV保存
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filename = opt_config['output']['csv_template'].format(
                    param_name=param_name,
                    timestamp=timestamp
                )
                csv_path = output_dir / csv_filename
                summary_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"\n✓ 結果を {csv_path} に保存")

            print("\n" + "=" * 80)
            print()

    elif args.param:
        # 単一パラメータを最適化
        param_name = args.param

        if param_name not in opt_config['parameters']:
            print(f"エラー: 不明なパラメータ '{param_name}'")
            print(f"利用可能なパラメータ: {list(opt_config['parameters'].keys())}")
            return

        results = optimize_parameter(param_name, opt_config, base_config, app_key)
        summary_df = analyze_results(results, param_name, opt_config)

        if summary_df is not None:
            # CSV保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = opt_config['output']['csv_template'].format(
                param_name=param_name,
                timestamp=timestamp
            )
            csv_path = output_dir / csv_filename
            summary_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"\n✓ 結果を {csv_path} に保存")

    else:
        print("エラー: --param または --all を指定してください")
        parser.print_help()


if __name__ == "__main__":
    main()
