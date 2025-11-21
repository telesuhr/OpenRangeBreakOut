"""
バックテストエンジン

複数日にわたる戦略実行とポートフォリオ管理を統合
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional, Union
from ..data.refinitiv_client import RefinitivClient
from ..strategy.range_breakout import RangeBreakoutDetector
from .portfolio import Portfolio
from .position import Position
from ..analysis.performance import PerformanceAnalyzer
from ..indicators.atr import ATRCalculator
from ..filters.market_filter import NikkeiFuturesFilter

logger = logging.getLogger(__name__)


class BacktestEngine:
    """バックテストエンジン"""

    def __init__(
        self,
        initial_capital: float,
        range_start: time,
        range_end: time,
        entry_start: time,
        entry_end: time,
        profit_target: float,
        stop_loss: Union[float, Dict],
        force_exit_time: time,
        commission_rate: float,
        nikkei_futures_filter: Optional[Dict] = None
    ):
        """
        Args:
            initial_capital: 初期資金
            range_start: レンジ計算開始時刻
            range_end: レンジ計算終了時刻
            entry_start: エントリー可能開始時刻
            entry_end: エントリー可能終了時刻
            profit_target: 利益目標（例: 0.02 = 2%）
            stop_loss: 損切り設定（float値または設定辞書）
            force_exit_time: 強制決済時刻
            commission_rate: 手数料率（片道）
            nikkei_futures_filter: 日経先物フィルター設定（Noneの場合は無効）
        """
        self.initial_capital = initial_capital
        self.range_start = range_start
        self.range_end = range_end
        self.entry_start = entry_start
        self.entry_end = entry_end
        self.profit_target = profit_target
        self.force_exit_time = force_exit_time
        self.commission_rate = commission_rate

        # ストップロス設定を解析
        if isinstance(stop_loss, (int, float)):
            # 後方互換性: 単純な数値が渡された場合は固定モード
            self.stop_loss_mode = 'fixed'
            self.stop_loss_fixed = stop_loss
            self.stop_loss_config = {'mode': 'fixed', 'fixed': {'value': stop_loss}}
            self.atr_calculator = None
        elif isinstance(stop_loss, dict):
            # 新仕様: 設定辞書が渡された場合
            self.stop_loss_config = stop_loss
            self.stop_loss_mode = stop_loss.get('mode', 'fixed')

            if self.stop_loss_mode == 'fixed':
                self.stop_loss_fixed = stop_loss['fixed']['value']
                self.atr_calculator = None
            elif self.stop_loss_mode in ['atr', 'atr_adaptive']:
                self.stop_loss_fixed = stop_loss.get(self.stop_loss_mode, {}).get('min_stop', 0.0075)  # フォールバック用
                # ATR計算器を初期化
                atr_period = stop_loss.get(self.stop_loss_mode, {}).get('period', 14)
                self.atr_calculator = ATRCalculator(period=atr_period)
            else:
                raise ValueError(f"不明なストップロスモード: {self.stop_loss_mode}")
        else:
            raise ValueError(f"stop_lossは数値または辞書である必要があります: {type(stop_loss)}")

        # 銘柄別の上書き設定
        self.symbol_overrides = self.stop_loss_config.get('symbol_overrides', {})

        # 日経先物フィルターの初期化
        if nikkei_futures_filter and nikkei_futures_filter.get('enabled', False):
            self.nikkei_futures_filter = NikkeiFuturesFilter(
                enabled=True,
                futures_symbol=nikkei_futures_filter.get('symbol', 'NKDc1'),
                fallback_symbol=nikkei_futures_filter.get('fallback_symbol', '.SPX'),
                threshold=nikkei_futures_filter.get('threshold', -0.02),
                reference_time_utc=nikkei_futures_filter.get('reference_time_utc', '21:00')
            )
        else:
            self.nikkei_futures_filter = None

        # コンポーネント初期化
        self.detector = RangeBreakoutDetector(range_start, range_end)
        self.portfolio = Portfolio(initial_capital)

        # 取引履歴
        self.trades = []
        self.daily_equity = []

        # 各銘柄の最終価格を記録（日次終了時の決済用）
        self.last_prices = {}

        # ATR値のキャッシュ（銘柄ごと）
        self._atr_cache = {}

        # 日経先物フィルターで見送った日数（統計）
        self.filter_skipped_days = 0

    def run_backtest(
        self,
        client: RefinitivClient,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        バックテストを実行

        Args:
            client: Refinitiv APIクライアント
            symbols: 銘柄リスト
            start_date: 開始日
            end_date: 終了日

        Returns:
            バックテスト結果の辞書
        """
        logger.info(f"\n=== バックテスト開始 ===")
        logger.info(f"期間: {start_date.date()} - {end_date.date()}")
        logger.info(f"銘柄数: {len(symbols)}")
        logger.info(f"初期資金: {self.initial_capital:,.0f} 円")

        # 日次ループ
        current_date = start_date
        trading_days = 0

        while current_date <= end_date:
            # 営業日チェック（土日をスキップ）
            if current_date.weekday() >= 5:  # 5=土曜, 6=日曜
                current_date += timedelta(days=1)
                continue

            logger.info(f"\n--- {current_date.date()} ---")

            # 日経先物フィルターチェック
            allow_entry_today = True
            if self.nikkei_futures_filter is not None:
                filter_result = self.nikkei_futures_filter.check_entry_allowed(current_date, client)
                allow_entry_today = filter_result['allow_entry']

                if not allow_entry_today:
                    logger.info(f"エントリー見送り: {filter_result['reason']}")
                    self.filter_skipped_days += 1

            # 日次開始時に最終価格をクリア
            self.last_prices = {}

            # 各銘柄の処理
            for symbol in symbols:
                try:
                    self._process_symbol_for_day(client, symbol, current_date, allow_entry_today)
                except Exception as e:
                    logger.warning(f"{symbol} 処理エラー: {e}")
                    continue

            # 日次終了時に全ポジションを強制決済
            self._force_close_all_positions(current_date)

            # 日次エクイティを記録
            equity = self.portfolio.cash  # 全ポジションクローズ後の現金
            self.daily_equity.append({
                'date': current_date,
                'equity': equity,
                'cash': self.portfolio.cash,
                'positions': len(self.portfolio.open_positions)
            })

            logger.info(
                f"日次エクイティ: {equity:,.0f} 円 "
                f"(現金: {self.portfolio.cash:,.0f}, ポジション数: {len(self.portfolio.open_positions)})"
            )

            trading_days += 1
            current_date += timedelta(days=1)

        # 結果集計
        results = self._compile_results(trading_days)

        logger.info(f"\n=== バックテスト完了 ===")
        logger.info(f"取引日数: {trading_days}")
        logger.info(f"総取引数: {len(self.trades)}")
        logger.info(f"最終エクイティ: {results['final_equity']:,.0f} 円")
        logger.info(f"総リターン: {results['total_return']:.2%}")

        return results

    def _process_symbol_for_day(
        self,
        client: RefinitivClient,
        symbol: str,
        date: datetime,
        allow_entry: bool = True
    ):
        """
        特定の日の特定銘柄を処理

        Args:
            client: APIクライアント
            symbol: 銘柄コード
            date: 対象日
            allow_entry: エントリーを許可するか（フィルターによる制限）
        """
        # 分足データ取得（UTC時刻で指定）
        # JST 09:00 = UTC 00:00 から force_exit_time（既にUTC）まで
        start_time = datetime(date.year, date.month, date.day, 0, 0)  # JST 09:00 = UTC 00:00

        # force_exit_timeは既にUTC時刻（run_trading_system.pyでJST→UTC変換済み）
        # Refinitiv APIのendパラメータは排他的なので+1分して、force_exit_timeのデータを含める
        end_time = datetime(date.year, date.month, date.day,
                           self.force_exit_time.hour,
                           self.force_exit_time.minute) + timedelta(minutes=1)

        data = client.get_intraday_data(
            symbol=symbol,
            start_date=start_time,
            end_date=end_time,
            interval="1min"
        )

        if data is None or data.empty:
            logger.debug(f"{symbol}: データなし")
            return

        # ストップ高/ストップ安チェック（エントリー見送り判定）
        # バックテスト高速化のため一時的に無効化（API呼び出しで激遅）
        # limit_check = client.check_limit_up_down(symbol, date)
        # if limit_check['is_limit_up']:
        #     logger.warning(f"{symbol}: ストップ高のためエントリー見送り")
        #     return
        # if limit_check['is_limit_down']:
        #     logger.warning(f"{symbol}: ストップ安のためエントリー見送り")
        #     return

        # レンジ計算
        try:
            range_high, range_low = self.detector.calculate_range(data)
        except ValueError as e:
            logger.debug(f"{symbol}: レンジ計算失敗 - {e}")
            return

        # ブレイクアウト検出とエントリー
        entry_made = False

        for idx, row in data.iterrows():
            bar_time = idx.time()

            # エントリー許可チェック（日経先物フィルター）
            if not allow_entry:
                break  # この日のエントリーは見送り

            # エントリー時間帯のチェック
            if not (self.entry_start <= bar_time < self.entry_end):
                continue

            # 既存ポジションがあればスキップ
            if any(p.symbol == symbol for p in self.portfolio.open_positions):
                continue

            # ブレイクアウト検出
            breakout_type = self.detector.detect_breakout(row, range_high, range_low)

            if breakout_type is not None and not entry_made:
                # エントリー価格
                entry_price = self.detector.get_entry_price(
                    row, breakout_type, range_high, range_low
                )

                # ポジションサイズ計算（現在のポジション数+1で割る）
                num_positions = len(self.portfolio.open_positions) + 1
                quantity = self.portfolio.calculate_position_size(entry_price, num_positions)

                if quantity > 0:
                    # 動的ストップロスを計算
                    dynamic_stop_loss = self._calculate_dynamic_stop_loss(
                        symbol=symbol,
                        entry_price=entry_price,
                        client=client,
                        current_date=date
                    )

                    # ポジション作成
                    position = Position(
                        symbol=symbol,
                        side=breakout_type,
                        entry_price=entry_price,
                        quantity=quantity,
                        entry_time=idx,
                        profit_target=self.profit_target,
                        stop_loss=dynamic_stop_loss  # 動的ストップロスを使用
                    )

                    # ポートフォリオに追加
                    try:
                        self.portfolio.add_position(position)

                        # ログ出力（ストップロス情報を追加）
                        if self.stop_loss_mode == 'fixed':
                            stop_info = f"固定 {dynamic_stop_loss:.2%}"
                        else:
                            stop_info = f"{self.stop_loss_mode.upper()} {dynamic_stop_loss:.2%}"

                        logger.info(
                            f"{symbol}: {breakout_type.upper()} エントリー @ {entry_price} "
                            f"x {quantity}株 (時刻: {idx}), ストップロス: {stop_info}"
                        )
                        entry_made = True
                    except ValueError as e:
                        logger.warning(f"{symbol}: ポジション追加失敗 - {e}")

        # ポジション監視とクローズ
        self._monitor_positions(symbol, data)

        # 最終価格を記録（日次終了時の決済用）
        if not data.empty:
            last_bar = data.iloc[-1]
            if not pd.isna(last_bar['close']):
                self.last_prices[symbol] = last_bar['close']

    def _force_close_all_positions(self, current_date: datetime):
        """
        日次終了時に全オープンポジションを強制決済

        Args:
            current_date: 現在の日付
        """
        if not self.portfolio.open_positions:
            return

        logger.info(f"日次終了: {len(self.portfolio.open_positions)} ポジションを強制決済")

        # コピーを作成してイテレート（リストが変更されるため）
        positions_to_close = list(self.portfolio.open_positions)

        for position in positions_to_close:
            # 終値で決済（その銘柄の最後の取引価格を使用）
            exit_price = self.last_prices.get(position.symbol, position.entry_price)

            # force_exit_timeは既にUTC時刻なのでそのまま使用
            exit_time = datetime(current_date.year, current_date.month, current_date.day,
                                self.force_exit_time.hour,
                                self.force_exit_time.minute)

            self._close_position(position, exit_price, exit_time, 'day_end')

    def _monitor_positions(self, symbol: str, data: pd.DataFrame):
        """
        ポジションを監視し、利益目標・損切り・強制決済をチェック

        Args:
            symbol: 銘柄コード
            data: 分足データ
        """
        # 該当銘柄のポジションを取得
        positions_to_close = []

        for position in self.portfolio.open_positions:
            if position.symbol != symbol:
                continue

            # データの各バーでチェック（エントリー時刻以降のみ）
            for idx, row in data.iterrows():
                # エントリー時刻以前のバーはスキップ
                if idx <= position.entry_time:
                    continue

                bar_time = idx.time()
                current_price = row['close']

                # NA値チェック
                if pd.isna(current_price):
                    continue

                # 利益目標チェック
                if position.should_exit_profit(current_price):
                    positions_to_close.append((position, current_price, idx, 'profit'))
                    break

                # 損切りチェック
                elif position.should_exit_loss(current_price):
                    positions_to_close.append((position, current_price, idx, 'loss'))
                    break

                # 強制決済時刻チェック
                elif bar_time >= self.force_exit_time:
                    positions_to_close.append((position, current_price, idx, 'force'))
                    break

        # ポジションクローズ
        for position, exit_price, exit_time, reason in positions_to_close:
            self._close_position(position, exit_price, exit_time, reason)

    def _close_position(
        self,
        position: Position,
        exit_price: float,
        exit_time: datetime,
        reason: str
    ):
        """
        ポジションをクローズし、取引記録を保存

        Args:
            position: ポジション
            exit_price: 決済価格
            exit_time: 決済時刻
            reason: 決済理由
        """
        # ポジションクローズ（Portfolioがposition.close()を呼ぶ）
        self.portfolio.close_position(position, exit_price, exit_time)

        # リターンを計算
        return_pct = position.realized_pnl / (position.entry_price * position.quantity) if position.entry_price * position.quantity > 0 else 0

        # 取引記録
        trade_record = {
            'symbol': position.symbol,
            'side': position.side,
            'entry_time': position.entry_time,
            'exit_time': exit_time,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'pnl': position.realized_pnl,
            'return': return_pct,
            'reason': reason
        }
        self.trades.append(trade_record)

        logger.info(
            f"{position.symbol}: {position.side.upper()} クローズ @ {exit_price} "
            f"(損益: {position.realized_pnl:+,.0f} 円, {return_pct:+.2%}) - {reason}"
        )

    def _calculate_dynamic_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        client: RefinitivClient,
        current_date: datetime
    ) -> float:
        """
        銘柄とモードに応じた動的ストップロス値を計算

        Args:
            symbol: 銘柄コード
            entry_price: エントリー価格
            client: データ取得用クライアント
            current_date: 現在の日付

        Returns:
            ストップロス値（比率、例: 0.0075 = 0.75%）
        """
        # 固定モードの場合
        if self.stop_loss_mode == 'fixed':
            return self.stop_loss_fixed

        # ATRベースモードの場合、ATR計算が必要
        if self.atr_calculator is None:
            logger.warning(f"{symbol}: ATR計算器が初期化されていません。固定値を使用します。")
            return self.stop_loss_fixed

        # 過去データを取得してATR計算
        atr_pct = self._get_atr_for_symbol(symbol, client, current_date)

        if atr_pct is None:
            logger.warning(f"{symbol}: ATR計算失敗。固定値 {self.stop_loss_fixed:.2%} を使用します。")
            return self.stop_loss_fixed

        # モードに応じてストップロス計算
        if self.stop_loss_mode == 'atr':
            config = self.stop_loss_config['atr']
            multiplier = config['multiplier']

            # 銘柄別上書き
            if symbol in self.symbol_overrides:
                multiplier = multiplier * self.symbol_overrides[symbol].get('multiplier', 1.0)

            stop_loss = (atr_pct / 100) * multiplier  # %を比率に変換

            # 上限・下限制約
            min_stop = config.get('min_stop', 0.005)
            max_stop = config.get('max_stop', 0.03)

            stop_loss = np.clip(stop_loss, min_stop, max_stop)
            logger.debug(f"{symbol}: ATRモード - ATR={atr_pct:.2f}%, 倍率={multiplier:.2f}, ストップロス={stop_loss:.2%}")

        elif self.stop_loss_mode == 'atr_adaptive':
            config = self.stop_loss_config['atr_adaptive']

            # ボラティリティレベル判定
            thresholds = config['thresholds']
            if atr_pct < thresholds['low_medium']:
                multiplier = config['multipliers']['low']
                vol_level = "低"
            elif atr_pct < thresholds['medium_high']:
                multiplier = config['multipliers']['medium']
                vol_level = "中"
            elif atr_pct < thresholds['high_extreme']:
                multiplier = config['multipliers']['high']
                vol_level = "高"
            else:
                multiplier = config['multipliers']['extreme']
                vol_level = "極度"

            # 銘柄別上書き
            if symbol in self.symbol_overrides:
                multiplier = multiplier * self.symbol_overrides[symbol].get('multiplier', 1.0)

            stop_loss = (atr_pct / 100) * multiplier

            # 上限・下限制約
            min_stop = config.get('min_stop', 0.005)
            max_stop = config.get('max_stop', 0.04)

            stop_loss = np.clip(stop_loss, min_stop, max_stop)
            logger.debug(
                f"{symbol}: ATR適応型 - ATR={atr_pct:.2f}% ({vol_level}), "
                f"倍率={multiplier:.2f}, ストップロス={stop_loss:.2%}"
            )

        else:
            # 不明なモード（本来は到達しないはず）
            stop_loss = self.stop_loss_fixed

        return stop_loss

    def _get_atr_for_symbol(
        self,
        symbol: str,
        client: RefinitivClient,
        current_date: datetime
    ) -> Optional[float]:
        """
        銘柄のATR%値を取得（キャッシュ機能付き）

        Args:
            symbol: 銘柄コード
            client: データ取得用クライアント
            current_date: 現在の日付

        Returns:
            ATR%値、計算できない場合はNone
        """
        # キャッシュチェック（同じ日のATRは再利用）
        cache_key = f"{symbol}_{current_date.date()}"
        if cache_key in self._atr_cache:
            return self._atr_cache[cache_key]

        try:
            # 過去20日分のデータを取得（14日分+余裕）
            end_date = current_date
            start_date = current_date - timedelta(days=30)  # 週末を考慮して多めに取得

            # データ取得
            data = client.get_intraday_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval='1min'
            )

            if data is None or data.empty:
                logger.warning(f"{symbol}: ATR計算用のデータが取得できません")
                return None

            # ATR計算
            atr_pct = self.atr_calculator.get_latest_atr(symbol, data)

            if atr_pct is not None:
                # キャッシュに保存
                self._atr_cache[cache_key] = atr_pct
                logger.debug(f"{symbol}: ATR = {atr_pct:.2f}%")

            return atr_pct

        except Exception as e:
            logger.warning(f"{symbol}: ATR計算エラー - {e}")
            return None

    def _compile_results(self, trading_days: int) -> Dict:
        """
        バックテスト結果を集計

        Args:
            trading_days: 取引日数

        Returns:
            結果の辞書
        """
        # エクイティカーブを作成
        equity_df = pd.DataFrame(self.daily_equity)
        equity_df.set_index('date', inplace=True)

        # 取引履歴をDataFrameに
        trades_df = pd.DataFrame(self.trades)

        # パフォーマンス分析
        analyzer = PerformanceAnalyzer(
            initial_capital=self.initial_capital,
            trades=self.trades,
            equity_curve=equity_df['equity']
        )

        # 結果辞書
        results = {
            'initial_capital': self.initial_capital,
            'final_equity': self.portfolio.cash,  # 全ポジションクローズ後の現金
            'total_return': analyzer.calculate_total_return(),
            'trading_days': trading_days,
            'total_trades': len(self.trades),
            'equity_curve': equity_df,
            'trades': trades_df
        }

        # 取引がある場合のみ追加メトリクス
        if len(self.trades) > 0:
            winning_trades = trades_df[trades_df['pnl'] > 0]
            losing_trades = trades_df[trades_df['pnl'] < 0]

            results.update({
                'win_rate': len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0,
                'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
                'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
                'profit_factor': analyzer.calculate_profit_factor(),
                'max_drawdown': analyzer.calculate_max_drawdown(),
                'sharpe_ratio': analyzer.calculate_sharpe_ratio()
            })

        return results
