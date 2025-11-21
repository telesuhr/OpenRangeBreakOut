"""
トレーディングシステム メインスクリプト

config/strategy_config.yamlの設定に基づいてバックテストを実行し、
Output/フォルダにレポートを生成します。

変更点:
- データベースにある全銘柄でバックテストを実行
- yamlのstocksはポートフォリオレポート作成に使用
- 全銘柄とポートフォリオの2種類のレポートを出力

使い方:
    python run_trading_system.py

設定変更:
    config/strategy_config.yaml を編集してください
"""
import sys
import yaml
import logging
import psycopg2
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


def get_all_symbols_from_db(db_config: dict) -> list:
    """
    データベースから全銘柄を取得

    Args:
        db_config: データベース設定辞書

    Returns:
        (銘柄コード, 銘柄名)のタプルのリスト
    """
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )

    cursor = conn.cursor()

    # intraday_dataテーブルから重複しない銘柄コードを取得
    query = """
    SELECT DISTINCT symbol
    FROM intraday_data
    ORDER BY symbol
    """

    cursor.execute(query)
    symbols = cursor.fetchall()

    cursor.close()
    conn.close()

    # (銘柄コード, 銘柄名)のタプルのリストに変換
    # 銘柄名はコードから生成（.Tを除去）
    result = []
    for (symbol_code,) in symbols:
        symbol_name = symbol_code.replace('.T', '')
        result.append((symbol_code, symbol_name))

    return result


def fetch_and_save_missing_stocks(
    client: RefinitivClient,
    missing_stocks: list,
    start_date: datetime,
    end_date: datetime
) -> list:
    """
    データベースに存在しない銘柄のデータを取得して保存

    Args:
        client: Refinitivクライアント
        missing_stocks: 不足している銘柄のリスト [(code, name), ...]
        start_date: 取得開始日
        end_date: 取得終了日

    Returns:
        取得成功した銘柄のリスト
    """
    logger = logging.getLogger(__name__)
    successfully_fetched = []

    if not missing_stocks:
        return successfully_fetched

    logger.info(f"\n不足している銘柄数: {len(missing_stocks)}")
    logger.info("Refinitivからデータを取得してデータベースに保存します...")

    for idx, (symbol_code, symbol_name) in enumerate(missing_stocks, 1):
        try:
            logger.info(f"\n進捗: {idx}/{len(missing_stocks)} - {symbol_name} ({symbol_code})")

            # Refinitivからイントラデイデータを取得
            data = client.get_intraday_data(
                symbol=symbol_code,
                start_date=start_date,
                end_date=end_date,
                interval='1min'
            )

            if data is not None and not data.empty:
                logger.info(f"{symbol_name}: {len(data)}行のデータを取得しました")
                successfully_fetched.append((symbol_code, symbol_name))
            else:
                logger.warning(f"{symbol_name}: データが取得できませんでした")

        except Exception as e:
            logger.error(f"{symbol_name}: データ取得エラー - {e}")
            continue

    logger.info(f"\n取得成功: {len(successfully_fetched)}/{len(missing_stocks)}銘柄")
    return successfully_fetched


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

        # データベース設定を確認
        if 'database' not in config:
            raise KeyError("database設定が見つかりません")

        # バックテスト対象モードを取得
        backtest_mode = config.get('backtest_target', {}).get('mode', 'portfolio')

        # ポートフォリオ銘柄（yamlで指定）
        portfolio_stocks = [(code, name) for code, name in config.get('stocks', [])]

        # モードに応じて対象銘柄を決定
        if backtest_mode == 'all_stocks':
            # データベースから全銘柄を取得
            logger.info("\n【バックテストモード: 全銘柄】")
            logger.info("データベースから全銘柄を取得中...")
            all_stocks = get_all_symbols_from_db(config['database'])
            logger.info(f"取得した銘柄数: {len(all_stocks)}")

            # データベースに存在しないポートフォリオ銘柄を特定
            db_symbols_set = set(all_stocks)
            missing_stocks = [stock for stock in portfolio_stocks if stock not in db_symbols_set]
        else:
            # ポートフォリオ銘柄のみを対象
            logger.info("\n【バックテストモード: ポートフォリオ銘柄のみ】")
            all_stocks = []
            missing_stocks = portfolio_stocks  # ポートフォリオ銘柄は全てチェック対象

        # 設定情報を表示
        logger.info("\n【設定情報】")
        logger.info(f"バックテスト期間: {config['backtest_period']['start_date']} ～ {config['backtest_period']['end_date']}")
        logger.info(f"バックテストモード: {backtest_mode}")
        if backtest_mode == 'all_stocks':
            logger.info(f"全銘柄数（データベース）: {len(all_stocks)}")
        logger.info(f"ポートフォリオ銘柄数（yaml指定）: {len(portfolio_stocks)}")
        if missing_stocks:
            logger.info(f"データ取得が必要な銘柄数: {len(missing_stocks)}")
        logger.info(f"各銘柄資金: {config['capital']['per_stock']:,} 円")
        logger.info(f"オープンレンジ: {config['orb_strategy']['open_range']['start_time']} - {config['orb_strategy']['open_range']['end_time']}")
        logger.info(f"エントリー時間: {config['orb_strategy']['entry_window']['start_time']} - {config['orb_strategy']['entry_window']['end_time']}")
        logger.info(f"利益目標: {config['orb_strategy']['profit_target'] * 100:.2f}%")

        # エントリーフィルター設定の表示
        entry_filters = config.get('orb_strategy', {}).get('entry_filters', {})
        nikkei_filter = entry_filters.get('nikkei_futures_filter', {})
        if nikkei_filter.get('enabled', False):
            logger.info(
                f"日経先物フィルター: 有効 "
                f"(閾値: {nikkei_filter.get('threshold', -2.0)*100:.1f}%, "
                f"シンボル: {nikkei_filter.get('symbol', 'NKDc1')}, "
                f"代替: {nikkei_filter.get('fallback_symbol', '.SPX')})"
            )
        else:
            logger.info("日経先物フィルター: 無効")

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

        # ========================================
        # 不足銘柄のデータを取得
        # ========================================
        if missing_stocks:
            logger.info(f"\n{'=' * 80}")
            logger.info("ポートフォリオ銘柄の不足データを取得")
            logger.info(f"{'=' * 80}")

            fetched_stocks = fetch_and_save_missing_stocks(
                client=client,
                missing_stocks=missing_stocks,
                start_date=start_date,
                end_date=end_date
            )

            # 取得成功した銘柄を all_stocks に追加
            if fetched_stocks:
                all_stocks.extend(fetched_stocks)
                logger.info(f"\n全銘柄数（追加後）: {len(all_stocks)}")

        # 全銘柄の結果を保存する辞書
        all_results = {}

        # ========================================
        # 全銘柄のバックテストを実行
        # ========================================
        logger.info(f"\n{'=' * 80}")
        logger.info(f"全{len(all_stocks)}銘柄のバックテストを開始")
        logger.info(f"{'=' * 80}")

        for idx, stock_info in enumerate(all_stocks, 1):
            symbol_code, symbol_name = stock_info

            logger.info(f"\n進捗: {idx}/{len(all_stocks)} - {symbol_name} ({symbol_code})")

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
                commission_rate=config['capital']['commission_rate'],
                nikkei_futures_filter=orb_params.get('entry_filters', {}).get('nikkei_futures_filter')
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

        # ========================================
        # レポート生成
        # ========================================
        if config['reports'].get('generate_summary', True) and all_results:

            if backtest_mode == 'all_stocks':
                # 全銘柄モード：2種類のレポートを生成
                # 1. 全銘柄のサマリーレポート
                logger.info("\n全銘柄のサマリーレポートを生成中...")
                report_generator.generate_summary_report(
                    results=all_results,
                    config=config,
                    timestamp=timestamp,
                    report_prefix="all_stocks"
                )
                logger.info(f"全銘柄レポート完了: {len(all_results)}銘柄")

                # 2. ポートフォリオのサマリーレポート
                if portfolio_stocks:
                    logger.info("\nポートフォリオのサマリーレポートを生成中...")

                    # ポートフォリオ銘柄のみの結果を抽出
                    portfolio_results = {
                        key: value for key, value in all_results.items()
                        if key in portfolio_stocks
                    }

                    if portfolio_results:
                        report_generator.generate_summary_report(
                            results=portfolio_results,
                            config=config,
                            timestamp=timestamp,
                            report_prefix="portfolio"
                        )
                        logger.info(f"ポートフォリオレポート完了: {len(portfolio_results)}銘柄")
                    else:
                        logger.warning("ポートフォリオ銘柄のバックテスト結果が見つかりません")
                else:
                    logger.info("ポートフォリオ銘柄が指定されていません（yamlのstocksが空）")
            else:
                # ポートフォリオモード：1種類のレポートのみ
                logger.info("\nサマリーレポートを生成中...")
                report_generator.generate_summary_report(
                    results=all_results,
                    config=config,
                    timestamp=timestamp,
                    report_prefix="portfolio"
                )
                logger.info(f"レポート完了: {len(all_results)}銘柄")

        # Refinitivクライアントを切断
        client.disconnect()

        logger.info("\n" + "=" * 80)
        logger.info("トレーディングシステム正常終了")
        logger.info("=" * 80)
        logger.info(f"\nレポート出力先: {config['reports']['output_dir']}/{run_timestamp}/")

        if backtest_mode == 'all_stocks':
            logger.info(f"  - 全銘柄レポート: all_stocks_*.csv, all_stocks_*.png")
            logger.info(f"  - ポートフォリオレポート: portfolio_*.csv, portfolio_*.png")
        else:
            logger.info(f"  - ポートフォリオレポート: portfolio_*.csv, portfolio_*.png")

        logger.info(f"  - 個別銘柄レポート: *_trades.csv, *_equity.csv, *_chart.png")

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
