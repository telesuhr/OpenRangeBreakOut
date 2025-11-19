"""
トレーディングシステム メインスクリプト

config/strategy_config.yamlの設定に基づいてバックテストを実行し、
Output/フォルダにレポートを生成します。

使い方:
    python run_trading_system.py

設定変更:
    config/strategy_config.yaml を編集してください
"""
import sys
import os
import yaml
import logging
from datetime import datetime, time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.data.refinitiv_client import RefinitivClient
from src.backtester.engine import BacktestEngine
from src.reporting.report_generator import ReportGenerator


def load_config(config_path: str = "config/strategy_config.yaml") -> dict:
    """
    設定ファイルを読み込む

    Args:
        config_path: 設定ファイルのパス

    Returns:
        設定辞書
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def setup_logging(config: dict):
    """
    ログ設定をセットアップ

    Args:
        config: 設定辞書
    """
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    to_file = log_config.get('to_file', True)
    file_path = log_config.get('file_path', 'Output/trading_system.log')

    # ロガー設定
    handlers = [logging.StreamHandler()]

    if to_file:
        # ディレクトリ作成
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(file_path, encoding='utf-8'))

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("トレーディングシステム起動")
    logger.info("=" * 80)


def parse_time(time_str: str) -> time:
    """
    時刻文字列をtimeオブジェクトに変換

    Args:
        time_str: 時刻文字列（"HH:MM"形式）

    Returns:
        timeオブジェクト
    """
    hour, minute = map(int, time_str.split(':'))
    return time(hour, minute)


def jst_to_utc_time(jst_time: time) -> time:
    """
    JST時刻をUTC時刻に変換

    Args:
        jst_time: JST時刻

    Returns:
        UTC時刻
    """
    # JST = UTC + 9時間
    utc_hour = (jst_time.hour - 9) % 24
    return time(utc_hour, jst_time.minute)


def run_backtest_for_stock(
    client: RefinitivClient,
    engine: BacktestEngine,
    symbol: tuple,
    start_date: datetime,
    end_date: datetime
) -> dict:
    """
    特定銘柄のバックテストを実行

    Args:
        client: Refinitivクライアント
        engine: バックテストエンジン
        symbol: (銘柄コード, 銘柄名) のタプル
        start_date: 開始日
        end_date: 終了日

    Returns:
        バックテスト結果
    """
    logger = logging.getLogger(__name__)

    symbol_code, symbol_name = symbol

    logger.info(f"\n{'=' * 80}")
    logger.info(f"{symbol_name} ({symbol_code}) バックテスト開始")
    logger.info(f"{'=' * 80}")

    try:
        # バックテスト実行
        # engine.run_backtest()は銘柄リストを受け取るので、1銘柄のリストで実行
        results = engine.run_backtest(
            client=client,
            symbols=[symbol_code],
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"{symbol_name} バックテスト完了")
        return results

    except Exception as e:
        logger.error(f"{symbol_name} バックテスト失敗: {e}", exc_info=True)
        return None


def main():
    """メイン処理"""
    try:
        # 設定読み込み
        print("\n設定ファイルを読み込み中...")
        config = load_config()

        # ログ設定
        setup_logging(config)
        logger = logging.getLogger(__name__)

        # タイムスタンプ生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 設定情報を表示
        logger.info("\n【設定情報】")
        logger.info(f"バックテスト期間: {config['backtest_period']['start_date']} ～ {config['backtest_period']['end_date']}")
        logger.info(f"対象銘柄数: {len(config['stocks'])}")
        logger.info(f"各銘柄資金: {config['capital']['per_stock']:,} 円")
        logger.info(f"オープンレンジ: {config['orb_strategy']['open_range']['start_time']} - {config['orb_strategy']['open_range']['end_time']}")
        logger.info(f"エントリー時間: {config['orb_strategy']['entry_window']['start_time']} - {config['orb_strategy']['entry_window']['end_time']}")
        logger.info(f"利益目標: {config['orb_strategy']['profit_target'] * 100:.2f}%")

        # ストップロス設定の表示
        stop_loss_config = config['orb_strategy']['stop_loss']
        if isinstance(stop_loss_config, dict):
            mode = stop_loss_config.get('mode', 'fixed')
            if mode == 'fixed':
                logger.info(f"損切り: {stop_loss_config['fixed']['value'] * 100:.2f}% (固定)")
            elif mode == 'atr':
                logger.info(f"損切り: ATRベース (倍率: {stop_loss_config['atr']['multiplier']})")
            elif mode == 'atr_adaptive':
                logger.info(f"損切り: ATR適応型 (ボラティリティに応じて自動調整)")
        else:
            # 後方互換性
            logger.info(f"損切り: {stop_loss_config * 100:.2f}% (固定)")

        # Refinitivクライアントを初期化
        logger.info("\nRefinitivクライアントを初期化中...")
        client = RefinitivClient(
            app_key=config['data']['refinitiv']['app_key'],
            use_cache=config['data']['refinitiv']['use_cache'],
            db_config=config.get('database')
        )
        client.connect()

        # 実行タイムスタンプを生成（全レポートで共通）
        run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # レポート生成器を初期化
        report_generator = ReportGenerator(
            output_dir=config['reports']['output_dir'],
            run_timestamp=run_timestamp
        )

        # バックテスト期間をパース
        start_date = datetime.strptime(config['backtest_period']['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(config['backtest_period']['end_date'], '%Y-%m-%d')

        # ORB戦略パラメータをパース
        orb_params = config['orb_strategy']

        # JST時刻をUTCに変換
        range_start_jst = parse_time(orb_params['open_range']['start_time'])
        range_end_jst = parse_time(orb_params['open_range']['end_time'])
        entry_start_jst = parse_time(orb_params['entry_window']['start_time'])
        entry_end_jst = parse_time(orb_params['entry_window']['end_time'])
        force_exit_jst = parse_time(orb_params['force_exit_time'])

        range_start_utc = jst_to_utc_time(range_start_jst)
        range_end_utc = jst_to_utc_time(range_end_jst)
        entry_start_utc = jst_to_utc_time(entry_start_jst)
        entry_end_utc = jst_to_utc_time(entry_end_jst)
        force_exit_utc = jst_to_utc_time(force_exit_jst)

        # 全銘柄の結果を保存する辞書
        all_results = {}

        # 各銘柄のバックテストを実行
        for stock_info in config['stocks']:
            symbol_code, symbol_name = stock_info

            # 各銘柄ごとに新しいBacktestEngineを作成
            # （ポートフォリオ状態をリセットするため）
            engine = BacktestEngine(
                initial_capital=config['capital']['per_stock'],
                range_start=range_start_utc,
                range_end=range_end_utc,
                entry_start=entry_start_utc,
                entry_end=entry_end_utc,
                profit_target=orb_params['profit_target'],
                stop_loss=orb_params['stop_loss'],  # 辞書またはfloat値を渡す
                force_exit_time=force_exit_utc,
                commission_rate=config['capital']['commission_rate']
            )

            # バックテスト実行
            result = run_backtest_for_stock(
                client=client,
                engine=engine,
                symbol=(symbol_code, symbol_name),
                start_date=start_date,
                end_date=end_date
            )

            if result is not None:
                # 結果を保存（キーは(銘柄コード, 銘柄名)のタプル）
                all_results[(symbol_code, symbol_name)] = result

                # 日次レポート生成（設定で有効化されている場合）
                if config['reports'].get('generate_daily', True):
                    report_generator.generate_daily_report(
                        symbol=(symbol_code, symbol_name),
                        result=result,
                        timestamp=timestamp
                    )

                # チャート生成（設定で有効化されている場合）
                if config['reports'].get('generate_charts', True):
                    report_generator.generate_charts(
                        symbol=(symbol_code, symbol_name),
                        result=result,
                        timestamp=timestamp
                    )

        # サマリーレポート生成（設定で有効化されている場合）
        if config['reports'].get('generate_summary', True) and all_results:
            logger.info("\n全銘柄のサマリーレポートを生成中...")
            report_generator.generate_summary_report(
                results=all_results,
                config=config,
                timestamp=timestamp
            )

        # Refinitivクライアントを切断
        client.disconnect()

        logger.info("\n" + "=" * 80)
        logger.info("トレーディングシステム正常終了")
        logger.info("=" * 80)
        logger.info(f"\nレポート出力先: {config['reports']['output_dir']}/{run_timestamp}/")
        logger.info(f"  - 全てのレポートが1つのフォルダに保存されました")

    except FileNotFoundError as e:
        print(f"\nエラー: 設定ファイルが見つかりません: {e}")
        print("config/strategy_config.yaml が存在することを確認してください。")
        sys.exit(1)

    except KeyError as e:
        print(f"\nエラー: 設定ファイルに必須項目が不足しています: {e}")
        print("config/strategy_config.yaml の内容を確認してください。")
        sys.exit(1)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"\n予期しないエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
