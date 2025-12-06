"""
レポート生成モジュール

バックテスト結果を日次レポート、チャート、サマリーとして出力する
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from matplotlib.colors import LinearSegmentedColormap
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 日本語フォント設定
rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
rcParams['axes.unicode_minus'] = False

logger = logging.getLogger(__name__)


class ReportGenerator:
    """バックテストレポート生成器"""

    def __init__(self, output_dir: str = "Output", run_timestamp: str = None):
        """
        Args:
            output_dir: レポート出力先ディレクトリ
            run_timestamp: 実行タイムスタンプ（YYYYMMDD_HHMMSS形式）
        """
        self.base_output_dir = Path(output_dir)

        # 実行タイムスタンプがない場合は現在時刻を使用
        if run_timestamp is None:
            run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 実行日時ごとのディレクトリを作成
        self.output_dir = self.base_output_dir / run_timestamp
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"出力ディレクトリ: {self.output_dir}")

    def generate_summary_report(
        self,
        results: Dict,
        config: Dict,
        timestamp: str = None,
        report_prefix: str = ""
    ):
        """
        サマリーレポートを生成

        Args:
            results: バックテスト結果の辞書（銘柄ごと）
            config: 設定辞書
            timestamp: レポートタイムスタンプ（Noneの場合は現在時刻）
            report_prefix: レポートファイル名のプレフィックス（例: "all_stocks", "portfolio"）
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"サマリーレポートを生成中... (prefix: {report_prefix or 'なし'})")

        # CSVレポートを生成
        self._generate_summary_csv(results, timestamp, report_prefix)

        # チャートを生成
        self._generate_summary_chart(results, timestamp, report_prefix)

        # 日次P&Lヒートマップを生成
        self._generate_daily_pl_heatmap(results, timestamp, report_prefix)

        # テキストサマリーを生成
        self._generate_summary_text(results, config, timestamp, report_prefix)

        logger.info(f"サマリーレポート生成完了: {self.output_dir}")

    def _generate_summary_csv(self, results: Dict, timestamp: str, report_prefix: str = ""):
        """
        CSVサマリーレポートを生成

        Args:
            results: バックテスト結果の辞書
            timestamp: タイムスタンプ
            report_prefix: レポートファイル名のプレフィックス
        """
        summary_data = []

        for symbol, result in results.items():
            # 銘柄情報を抽出
            symbol_code, symbol_name = symbol if isinstance(symbol, tuple) else (symbol, symbol)

            # 統計情報を集計
            # trades DataFrameを取得
            trades_df = result.get('trades', pd.DataFrame())

            # 勝ちトレード数と負けトレード数を計算（'pnl'カラムの有無をチェック）
            if not trades_df.empty and 'pnl' in trades_df.columns:
                win_trades = len(trades_df[trades_df['pnl'] > 0])
                loss_trades = len(trades_df[trades_df['pnl'] <= 0])
            else:
                win_trades = 0
                loss_trades = 0

            # LONGとSHORTのトレード数を計算（'side'カラムの有無をチェック）
            if not trades_df.empty and 'side' in trades_df.columns:
                long_trades = len(trades_df[trades_df['side'].str.upper() == 'LONG'])
                short_trades = len(trades_df[trades_df['side'].str.upper() == 'SHORT'])
            else:
                long_trades = 0
                short_trades = 0

            summary_data.append({
                '銘柄コード': symbol_code,
                '銘柄名': symbol_name,
                '初期資金': result.get('initial_capital', 0),
                '最終資金': result.get('final_equity', 0),
                '総損益': result.get('final_equity', 0) - result.get('initial_capital', 0),
                '総リターン(%)': result.get('total_return', 0) * 100,
                '総トレード数': result.get('total_trades', 0),
                'LONGトレード数': long_trades,
                'SHORTトレード数': short_trades,
                '勝ちトレード数': win_trades,
                '負けトレード数': loss_trades,
                '勝率(%)': result.get('win_rate', 0) * 100 if 'win_rate' in result else 0,
                '平均利益': result.get('avg_win', 0),
                '平均損失': result.get('avg_loss', 0),
                'プロフィットファクター': result.get('profit_factor', 0),
                '最大ドローダウン(%)': result.get('max_drawdown', 0) * 100 if 'max_drawdown' in result else 0,
                'シャープレシオ': result.get('sharpe_ratio', 0) if 'sharpe_ratio' in result else 0,
            })

        # DataFrameに変換
        summary_df = pd.DataFrame(summary_data)

        # 並び替え（総損益の降順）
        summary_df = summary_df.sort_values('総損益', ascending=False)

        # CSV保存
        filename = f"{report_prefix}_summary.csv" if report_prefix else "summary.csv"
        csv_path = self.output_dir / filename
        summary_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"CSVサマリー保存: {csv_path}")

    def _generate_summary_chart(self, results: Dict, timestamp: str, report_prefix: str = ""):
        """
        サマリーチャートを生成

        Args:
            results: バックテスト結果の辞書
            timestamp: タイムスタンプ
            report_prefix: レポートファイル名のプレフィックス
        """
        # 図のセットアップ
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('バックテスト結果サマリー', fontsize=16, fontweight='bold')

        # データ準備
        symbols = []
        pnls = []
        returns = []
        win_rates = []
        trade_counts = []
        long_counts = []
        short_counts = []

        for symbol, result in results.items():
            symbol_code, symbol_name = symbol if isinstance(symbol, tuple) else (symbol, symbol)
            symbols.append(symbol_name)

            initial_capital = result.get('initial_capital', 0)
            final_equity = result.get('final_equity', 0)
            pnl = final_equity - initial_capital
            pnls.append(pnl)

            returns.append(result.get('total_return', 0) * 100)
            win_rates.append(result.get('win_rate', 0) * 100 if 'win_rate' in result else 0)
            trade_counts.append(result.get('total_trades', 0))

            # LONG/SHORTトレード数をカウント
            trades_df = result.get('trades', pd.DataFrame())
            if not trades_df.empty and 'side' in trades_df.columns:
                long_count = len(trades_df[trades_df['side'].str.upper() == 'LONG'])
                short_count = len(trades_df[trades_df['side'].str.upper() == 'SHORT'])
            else:
                long_count = 0
                short_count = 0
            long_counts.append(long_count)
            short_counts.append(short_count)

        # 1. 損益ランキング（横棒グラフ）
        ax1 = axes[0, 0]
        colors = ['green' if p > 0 else 'red' for p in pnls]
        ax1.barh(symbols, pnls, color=colors, alpha=0.7)
        ax1.set_xlabel('損益 (円)', fontsize=12)
        ax1.set_title('銘柄別損益ランキング', fontsize=14, fontweight='bold')
        ax1.axvline(x=0, color='black', linestyle='--', linewidth=0.5)
        ax1.grid(True, alpha=0.3)

        # 2. リターン vs 勝率（散布図）
        ax2 = axes[0, 1]
        scatter_colors = ['green' if r > 0 else 'red' for r in returns]
        ax2.scatter(win_rates, returns, c=scatter_colors, s=100, alpha=0.6)
        for i, name in enumerate(symbols):
            ax2.annotate(name, (win_rates[i], returns[i]), fontsize=8, alpha=0.7)
        ax2.set_xlabel('勝率 (%)', fontsize=12)
        ax2.set_ylabel('リターン (%)', fontsize=12)
        ax2.set_title('勝率 vs リターン', fontsize=14, fontweight='bold')
        ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        ax2.grid(True, alpha=0.3)

        # 3. トレード数（LONG/SHORT積み上げ棒グラフ）
        ax3 = axes[1, 0]
        x_pos = range(len(symbols))
        # LONGを緑、SHORTを赤で積み上げ
        ax3.bar(x_pos, long_counts, color='#2ecc71', alpha=0.8, label='LONG')
        ax3.bar(x_pos, short_counts, bottom=long_counts, color='#e74c3c', alpha=0.8, label='SHORT')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(symbols, rotation=45, ha='right', fontsize=10)
        ax3.set_ylabel('トレード数', fontsize=12)
        ax3.set_title('銘柄別トレード数（LONG/SHORT内訳）', fontsize=14, fontweight='bold')
        ax3.legend(loc='upper right', fontsize=10)
        ax3.grid(True, alpha=0.3, axis='y')

        # 4. 累積エクイティカーブ（複合）
        ax4 = axes[1, 1]

        # まず全ての線をプロットして、ラベル情報を収集
        label_info = []  # (last_date, last_value, symbol_name, line_color)

        for symbol, result in results.items():
            symbol_code, symbol_name = symbol if isinstance(symbol, tuple) else (symbol, symbol)
            equity_curve = result.get('equity_curve', pd.Series())
            if not equity_curve.empty:
                # DataFrameの場合は'equity'カラムを取得
                if isinstance(equity_curve, pd.DataFrame):
                    equity_values = equity_curve['equity'].values
                else:
                    equity_values = equity_curve.values

                # 線をプロット
                line = ax4.plot(equity_curve.index, equity_values, alpha=0.7)[0]

                # ラベル情報を収集
                last_date = equity_curve.index[-1]
                last_value = equity_values[-1]
                label_info.append((last_date, last_value, symbol_name, line.get_color()))

        # Y軸の範囲を取得（プロット後）
        ymin, ymax = ax4.get_ylim()
        y_range = ymax - ymin
        min_spacing = y_range * 0.03  # 最小間隔を3%に設定

        # 最終値でソート（Y座標順）
        label_info.sort(key=lambda x: x[1])

        # 重複を避けてラベルを配置
        label_positions = []
        for last_date, last_value, symbol_name, line_color in label_info:
            adjusted_value = last_value

            # 既存のラベルと重複しないように調整
            for existing_pos in label_positions:
                if abs(adjusted_value - existing_pos) < min_spacing:
                    # 重複する場合は上にずらす
                    adjusted_value = existing_pos + min_spacing

            label_positions.append(adjusted_value)

            # 銘柄名を表示（線の色と同じ色で）
            ax4.text(last_date, adjusted_value, f' {symbol_name}',
                    fontsize=8, va='center', ha='left',
                    color=line_color, alpha=0.8,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                            edgecolor=line_color, alpha=0.7))

        ax4.set_xlabel('日付', fontsize=12)
        ax4.set_ylabel('エクイティ (円)', fontsize=12)
        ax4.set_title('累積エクイティカーブ', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # レイアウト調整と保存
        plt.tight_layout()
        filename = f"{report_prefix}_summary_charts.png" if report_prefix else "summary_charts.png"
        chart_path = self.output_dir / filename
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        plt.close()
        logger.info(f"サマリーチャート保存: {chart_path}")

    def _generate_summary_text(self, results: Dict, config: Dict, timestamp: str, report_prefix: str = ""):
        """
        テキストサマリーレポートを生成

        Args:
            results: バックテスト結果の辞書
            config: 設定辞書
            timestamp: タイムスタンプ
            report_prefix: レポートファイル名のプレフィックス
        """
        lines = []
        lines.append("=" * 80)
        lines.append("バックテスト結果サマリー")
        lines.append("=" * 80)
        lines.append("")

        # 設定情報
        lines.append("【設定情報】")
        lines.append(f"期間: {config['backtest_period']['start_date']} ～ {config['backtest_period']['end_date']}")
        lines.append(f"銘柄数: {len(results)}")
        lines.append(f"各銘柄資金: {config['capital']['per_stock']:,} 円")
        lines.append(f"オープンレンジ: {config['orb_strategy']['open_range']['start_time']} - {config['orb_strategy']['open_range']['end_time']}")
        lines.append(f"エントリー時間: {config['orb_strategy']['entry_window']['start_time']} - {config['orb_strategy']['entry_window']['end_time']}")
        lines.append(f"利益目標: {config['orb_strategy']['profit_target'] * 100:.2f}%")

        # ストップロス設定の表示（辞書型と数値型の両方に対応）
        stop_loss_config = config['orb_strategy']['stop_loss']
        if isinstance(stop_loss_config, dict):
            mode = stop_loss_config.get('mode', 'fixed')
            if mode == 'fixed':
                lines.append(f"損切り: {stop_loss_config['fixed']['value'] * 100:.2f}% (固定)")
            elif mode == 'atr':
                lines.append(f"損切り: ATRベース (倍率: {stop_loss_config['atr']['multiplier']})")
            elif mode == 'atr_adaptive':
                lines.append(f"損切り: ATR適応型 (ボラティリティに応じて自動調整)")
        else:
            # 後方互換性（数値型の場合）
            lines.append(f"損切り: {stop_loss_config * 100:.2f}%")

        lines.append("")

        # 全体統計
        total_pnl = sum(result.get('final_equity', 0) - result.get('initial_capital', 0) for result in results.values())
        total_trades = sum(result.get('total_trades', 0) for result in results.values())
        winning_stocks = sum(1 for result in results.values() if result.get('final_equity', 0) > result.get('initial_capital', 0))

        lines.append("【全体統計】")
        lines.append(f"総損益: {total_pnl:+,.0f} 円")
        lines.append(f"総トレード数: {total_trades}")
        lines.append(f"勝ち銘柄数: {winning_stocks} / {len(results)} ({winning_stocks / len(results) * 100:.1f}%)")
        lines.append("")

        # 銘柄別詳細
        lines.append("【銘柄別詳細】")

        # 損益順に並び替え
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].get('final_equity', 0) - x[1].get('initial_capital', 0),
            reverse=True
        )

        for symbol, result in sorted_results:
            symbol_code, symbol_name = symbol if isinstance(symbol, tuple) else (symbol, symbol)

            initial_capital = result.get('initial_capital', 0)
            final_equity = result.get('final_equity', 0)
            pnl = final_equity - initial_capital
            total_return = result.get('total_return', 0) * 100
            trades = result.get('total_trades', 0)
            win_rate = result.get('win_rate', 0) * 100 if 'win_rate' in result else 0

            # LONG/SHORTトレード数をカウント
            trades_df = result.get('trades', pd.DataFrame())
            if not trades_df.empty and 'side' in trades_df.columns:
                long_trades = len(trades_df[trades_df['side'].str.upper() == 'LONG'])
                short_trades = len(trades_df[trades_df['side'].str.upper() == 'SHORT'])
                trade_detail = f"  トレード数: {trades} (LONG: {long_trades}, SHORT: {short_trades})"
            else:
                trade_detail = f"  トレード数: {trades}"

            lines.append(f"\n{symbol_name} ({symbol_code})")
            lines.append(f"  損益: {pnl:+,.0f} 円 ({total_return:+.2f}%)")
            lines.append(trade_detail)
            lines.append(f"  勝率: {win_rate:.1f}%")

            if 'avg_win' in result and 'avg_loss' in result:
                lines.append(f"  平均利益: {result['avg_win']:+,.0f} 円")
                lines.append(f"  平均損失: {result['avg_loss']:+,.0f} 円")

            if 'profit_factor' in result:
                lines.append(f"  プロフィットファクター: {result['profit_factor']:.2f}")

        lines.append("")
        lines.append("=" * 80)
        lines.append(f"レポート生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)

        # ファイル保存
        filename = f"{report_prefix}_summary.txt" if report_prefix else "summary.txt"
        text_path = self.output_dir / filename
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"テキストサマリー保存: {text_path}")

        # コンソール出力
        print('\n'.join(lines))

    def _generate_daily_pl_heatmap(self, results: Dict, timestamp: str, report_prefix: str = ""):
        """
        日次P&Lヒートマップを生成

        Args:
            results: バックテスト結果の辞書
            timestamp: タイムスタンプ
            report_prefix: レポートファイル名のプレフィックス
        """
        logger.info("日次P&Lヒートマップを生成中...")

        # 各銘柄の日次P&Lデータと終了理由を収集
        daily_pnl_data = {}
        daily_exit_reasons = {}  # 各銘柄の各日の終了理由を記録
        all_dates = set()

        for symbol, result in results.items():
            symbol_code, symbol_name = symbol if isinstance(symbol, tuple) else (symbol, symbol)
            trades_df = result.get('trades', pd.DataFrame())

            if trades_df.empty:
                continue

            # 日付ごとのP&Lを集計
            # entry_timeカラムとpnlカラムから日付を抽出
            if 'entry_time' in trades_df.columns and 'pnl' in trades_df.columns:
                trades_df['date'] = pd.to_datetime(trades_df['entry_time']).dt.date
                daily_pnl = trades_df.groupby('date')['pnl'].sum()

                # データを保存
                daily_pnl_data[symbol_name] = daily_pnl
                all_dates.update(daily_pnl.index)

                # 日付ごとの終了理由を記録（その日に損切りまたは利食いがあったか）
                if 'reason' in trades_df.columns:
                    exit_reasons_dict = {}

                    for date in daily_pnl.index:
                        day_trades = trades_df[trades_df['date'] == date]
                        # その日のトレードに損切り(loss)または利食い(profit)があるか確認
                        has_loss = (day_trades['reason'] == 'loss').any()
                        has_profit = (day_trades['reason'] == 'profit').any()

                        # 両方ある場合は、より重要な方を優先（利食い優先）
                        if has_profit:
                            exit_reasons_dict[date] = 'profit'
                        elif has_loss:
                            exit_reasons_dict[date] = 'loss'
                        else:
                            exit_reasons_dict[date] = None

                    daily_exit_reasons[symbol_name] = exit_reasons_dict

        if not daily_pnl_data:
            logger.warning("ヒートマップ用のデータがありません")
            return

        # 日付をソート
        all_dates = sorted(list(all_dates))

        # マトリクス作成（銘柄×日付）+ 銘柄別合計列
        matrix_data = []
        symbol_names = []
        symbol_totals = []  # 銘柄ごとの合計

        for symbol_name, daily_pnl in daily_pnl_data.items():
            symbol_names.append(symbol_name)
            row = [daily_pnl.get(date, 0) for date in all_dates]
            matrix_data.append(row)
            # 銘柄ごとの合計を計算
            symbol_totals.append(sum(row))

        # 日次合計行を追加
        total_row = []
        for date_idx, date in enumerate(all_dates):
            # 各銘柄のその日の損益を合計
            daily_total = sum(matrix_data[symbol_idx][date_idx] for symbol_idx in range(len(matrix_data)))
            total_row.append(daily_total)

        # 各行に銘柄別合計を追加（合計列の作成）
        for i in range(len(matrix_data)):
            matrix_data[i].append(symbol_totals[i])

        # 合計列の日付を追加
        all_dates.append("合計")

        # 日次合計行を作成（各日の合計 + 全体合計）
        total_row.append(sum(symbol_totals))  # 全体合計

        # 日次合計行をマトリクスと銘柄リストに追加
        matrix_data.append(total_row)
        symbol_names.append('【日次合計】')

        # NumPy配列に変換
        heatmap_matrix = np.array(matrix_data)

        # カラーマップの作成
        # 日次PLと合計の両方で同じカラーマップを使用: 赤=損失、白=ゼロ、緑=利益
        colors_list = ['#d62728', '#ff7f0e', '#ffffff', '#90ee90', '#2ca02c']
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list('diverging', colors_list, N=n_bins)

        # マトリクスを転置（縦軸=日付、横軸=銘柄）
        heatmap_matrix_T = heatmap_matrix.T

        # ヒートマップのプロット（縦横を入れ替え）
        fig, ax = plt.subplots(figsize=(max(16, len(symbol_names) * 0.5), max(8, len(all_dates) * 0.3)))

        # 日次PL部分（合計行/列を除く）のデータ範囲を取得
        daily_data = heatmap_matrix_T[:-1, :-1]  # 最終行（日次合計行）と最終列（合計列）を除く
        vmax_daily = np.abs(daily_data).max() if daily_data.size > 0 else 1
        vmin_daily = -vmax_daily

        # 合計行/列のデータ範囲を取得
        total_row_data = heatmap_matrix_T[-1, :-1]  # 最終行（最終列を除く）
        total_col_data = heatmap_matrix_T[:-1, -1]  # 最終列（最終行を除く）
        total_all_data = np.concatenate([total_row_data, total_col_data])
        vmax_total = np.abs(total_all_data).max() if total_all_data.size > 0 else 1
        vmin_total = -vmax_total

        # 正規化されたマトリクスを作成（日次PLと合計で異なるスケールを使用）
        normalized_matrix = np.zeros_like(heatmap_matrix_T, dtype=float)
        # 日次PL部分を正規化
        normalized_matrix[:-1, :-1] = np.clip(heatmap_matrix_T[:-1, :-1] / vmax_daily, -1, 1)
        # 合計行を正規化
        normalized_matrix[-1, :-1] = np.clip(heatmap_matrix_T[-1, :-1] / vmax_total, -1, 1)
        # 合計列を正規化
        normalized_matrix[:-1, -1] = np.clip(heatmap_matrix_T[:-1, -1] / vmax_total, -1, 1)
        # 全体合計セル
        normalized_matrix[-1, -1] = np.clip(heatmap_matrix_T[-1, -1] / vmax_total, -1, 1)

        # ヒートマップを描画（正規化されたマトリクス）
        im = ax.imshow(normalized_matrix, cmap=cmap, aspect='auto', vmin=-1, vmax=1)

        # 合計行/列を同じカラーマップで上書き（別の正規化範囲を適用）
        from matplotlib.patches import Rectangle

        # 合計行（最終行）のセルを上書き
        for i in range(len(symbol_names)):
            normalized_value = normalized_matrix[-1, i]
            color = cmap((normalized_value + 1) / 2)  # -1～1を0～1に変換
            rect = Rectangle((i - 0.5, len(all_dates) - 1.5), 1, 1,
                           facecolor=color, edgecolor='none')
            ax.add_patch(rect)

        # 合計列（最終列）のセルを上書き（最終行を除く）
        for j in range(len(all_dates) - 1):  # 最終行は既に上書き済み
            normalized_value = normalized_matrix[j, -1]
            color = cmap((normalized_value + 1) / 2)
            rect = Rectangle((len(symbol_names) - 1.5, j - 0.5), 1, 1,
                           facecolor=color, edgecolor='none')
            ax.add_patch(rect)

        # 軸ラベルの設定（縦横を入れ替え）
        ax.set_xticks(np.arange(len(symbol_names)))
        ax.set_yticks(np.arange(len(all_dates)))

        # 日付フォーマット（"合計"以外をdatetimeに変換）
        date_labels = []
        for date in all_dates:
            if date == "合計":
                date_labels.append("合計")
            else:
                date_labels.append(pd.to_datetime(date).strftime('%m/%d'))

        ax.set_xticklabels(symbol_names, rotation=90, ha='right', fontsize=9)
        ax.set_yticklabels(date_labels, fontsize=8)

        # 合計行・合計列のラベルを太字にする
        xtick_labels = ax.get_xticklabels()
        ytick_labels = ax.get_yticklabels()
        if len(xtick_labels) > 0:
            xtick_labels[-1].set_fontweight('bold')
            xtick_labels[-1].set_fontsize(11)
        if len(ytick_labels) > 0:
            ytick_labels[-1].set_fontweight('bold')
            ytick_labels[-1].set_fontsize(11)

        # 合計列の左に区切り線を追加
        ax.axvline(x=len(symbol_names) - 1.5, color='black', linewidth=2, linestyle='-', alpha=0.8)
        # 合計行の上に区切り線を追加
        ax.axhline(y=len(all_dates) - 1.5, color='black', linewidth=2, linestyle='-', alpha=0.8)

        # 軸ラベル
        ax.set_xlabel('銘柄', fontsize=12, fontweight='bold')
        ax.set_ylabel('日付', fontsize=12, fontweight='bold')
        ax.set_title('日次損益ヒートマップ（日付 × 銘柄）', fontsize=14, fontweight='bold', pad=20)

        # カラーバーの追加
        cbar = plt.colorbar(im, ax=ax, pad=0.02)
        cbar.set_label('損益 (千円)', rotation=270, labelpad=20, fontsize=11)

        # セル内に値を表示（データ量に応じてフォントサイズと表示形式を調整）
        total_cells = len(symbol_names) * len(all_dates)

        # フォントサイズを動的に調整（最小6ポイント）
        # 常に千円単位で表示
        if total_cells < 400:
            fontsize = 8
        elif total_cells < 800:
            fontsize = 7
        else:
            fontsize = 6

        value_format = '{:,.0f}'  # 千円単位の整数表示（カンマ区切り）

        for i in range(len(symbol_names)):
            for j in range(len(all_dates)):
                value = heatmap_matrix[i, j]
                if value != 0:  # ゼロの場合は表示しない
                    # 正規化された値を使用してテキスト色を判定
                    normalized_val = normalized_matrix[j, i]  # 転置後の座標
                    text_color = 'white' if abs(normalized_val) > 0.5 else 'black'
                    # 値を千円単位で表示（カンマ区切り）
                    display_value = value_format.format(value / 1000)
                    # 転置後の座標: (銘柄index, 日付index) → (日付index, 銘柄index)
                    ax.text(i, j, display_value,
                           ha='center', va='center', color=text_color, fontsize=fontsize)

        # 損切り（×）と利食い（○）のマーカーを表示
        for i, symbol_name in enumerate(symbol_names):
            # 日次合計列はスキップ
            if symbol_name == '【日次合計】':
                continue

            # この銘柄の終了理由データを取得
            if symbol_name not in daily_exit_reasons:
                continue

            exit_reasons = daily_exit_reasons[symbol_name]

            for j, date in enumerate(all_dates):
                if date in exit_reasons:
                    reason = exit_reasons[date]

                    # マーカーの色を決定（背景の明るさに応じて）
                    # 正規化された値を使用
                    normalized_val = normalized_matrix[j, i]  # 転置後の座標
                    # 背景が暗い（損失が大きい）場合は白、明るい（利益が大きい）場合は黒
                    marker_color = 'white' if abs(normalized_val) > 0.5 else 'black'

                    if reason == 'loss':
                        # 損切り: × マーク（右上に配置）
                        # 転置後の座標: x=銘柄index, y=日付index
                        ax.text(i + 0.4, j - 0.35, '×', ha='center', va='center',
                               color=marker_color, fontsize=12, fontweight='normal', alpha=0.6)
                    elif reason == 'profit':
                        # 利食い: ○ マーク（右上に配置）
                        ax.text(i + 0.4, j - 0.35, '○', ha='center', va='center',
                               color=marker_color, fontsize=12, fontweight='normal', alpha=0.6)

        # グリッド線の追加（転置後の軸に合わせる）
        ax.set_xticks(np.arange(len(symbol_names)) - 0.5, minor=True)
        ax.set_yticks(np.arange(len(all_dates)) - 0.5, minor=True)
        ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

        # レイアウト調整と保存
        plt.tight_layout()
        filename = f"{report_prefix}_daily_pl_heatmap.png" if report_prefix else "daily_pl_heatmap.png"
        heatmap_path = self.output_dir / filename
        plt.savefig(heatmap_path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"日次P&Lヒートマップ保存: {heatmap_path}")

    def generate_daily_report(
        self,
        symbol: tuple,
        result: Dict,
        timestamp: str = None
    ):
        """
        銘柄別日次レポートを生成

        Args:
            symbol: (銘柄コード, 銘柄名) のタプル
            result: バックテスト結果
            timestamp: タイムスタンプ
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        symbol_code, symbol_name = symbol

        # トレード履歴をCSV保存
        trades_df = result.get('trades', pd.DataFrame())
        if not trades_df.empty:
            csv_path = self.output_dir / f"{symbol_code}_trades.csv"
            trades_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"{symbol_name} トレード履歴保存: {csv_path}")

        # エクイティカーブをCSV保存
        equity_df = result.get('equity_curve', pd.DataFrame())
        if not equity_df.empty:
            csv_path = self.output_dir / f"{symbol_code}_equity.csv"
            equity_df.to_csv(csv_path, encoding='utf-8-sig')
            logger.info(f"{symbol_name} エクイティカーブ保存: {csv_path}")

    def generate_charts(
        self,
        symbol: tuple,
        result: Dict,
        timestamp: str = None
    ):
        """
        銘柄別チャートを生成

        Args:
            symbol: (銘柄コード, 銘柄名) のタプル
            result: バックテスト結果
            timestamp: タイムスタンプ
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        symbol_code, symbol_name = symbol

        # トレードがない場合はスキップ
        if result.get('total_trades', 0) == 0:
            logger.info(f"{symbol_name}: トレードなし、チャートスキップ")
            return

        # 図のセットアップ
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle(f'{symbol_name} ({symbol_code}) バックテスト結果', fontsize=16, fontweight='bold')

        # 1. エクイティカーブ
        ax1 = axes[0]
        equity_curve = result.get('equity_curve', pd.Series())
        if not equity_curve.empty:
            # DataFrameの場合は'equity'カラムを取得
            if isinstance(equity_curve, pd.DataFrame):
                equity_values = equity_curve['equity'].values
            else:
                equity_values = equity_curve.values

            ax1.plot(equity_curve.index, equity_values, linewidth=2, color='steelblue')
            ax1.fill_between(equity_curve.index, equity_values,
                            result['initial_capital'], alpha=0.3, color='steelblue')
            ax1.axhline(y=result['initial_capital'], color='black', linestyle='--',
                       linewidth=1, label='初期資金')
            ax1.set_ylabel('エクイティ (円)', fontsize=12)
            ax1.set_title('エクイティカーブ', fontsize=14, fontweight='bold')
            ax1.legend(loc='best')
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # 2. トレード損益（棒グラフ）
        ax2 = axes[1]
        trades_df = result.get('trades', pd.DataFrame())
        if not trades_df.empty and 'pnl' in trades_df.columns:
            colors = ['green' if pnl > 0 else 'red' for pnl in trades_df['pnl']]
            ax2.bar(range(len(trades_df)), trades_df['pnl'], color=colors, alpha=0.7)
            ax2.set_xlabel('トレード番号', fontsize=12)
            ax2.set_ylabel('損益 (円)', fontsize=12)
            ax2.set_title('トレード別損益', fontsize=14, fontweight='bold')
            ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
            ax2.grid(True, alpha=0.3, axis='y')

        # レイアウト調整と保存
        plt.tight_layout()
        chart_path = self.output_dir / f"{symbol_code}_chart.png"
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        plt.close()
        logger.info(f"{symbol_name} チャート保存: {chart_path}")
