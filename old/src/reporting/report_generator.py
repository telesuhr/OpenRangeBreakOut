"""
レポート生成モジュール

バックテスト結果を日次レポート、チャート、サマリーとして出力する
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
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

    def __init__(self, output_dir: str = "Output"):
        """
        Args:
            output_dir: レポート出力先ディレクトリ
        """
        self.output_dir = Path(output_dir)

        # サブディレクトリを作成
        self.daily_reports_dir = self.output_dir / "daily_reports"
        self.charts_dir = self.output_dir / "charts"
        self.summary_dir = self.output_dir / "summary"

        for directory in [self.daily_reports_dir, self.charts_dir, self.summary_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def generate_summary_report(
        self,
        results: Dict,
        config: Dict,
        timestamp: str = None
    ):
        """
        サマリーレポートを生成

        Args:
            results: バックテスト結果の辞書（銘柄ごと）
            config: 設定辞書
            timestamp: レポートタイムスタンプ（Noneの場合は現在時刻）
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info("サマリーレポートを生成中...")

        # CSVレポートを生成
        self._generate_summary_csv(results, timestamp)

        # チャートを生成
        self._generate_summary_chart(results, timestamp)

        # テキストサマリーを生成
        self._generate_summary_text(results, config, timestamp)

        logger.info(f"サマリーレポート生成完了: {self.summary_dir}")

    def _generate_summary_csv(self, results: Dict, timestamp: str):
        """
        CSVサマリーレポートを生成

        Args:
            results: バックテスト結果の辞書
            timestamp: タイムスタンプ
        """
        summary_data = []

        for symbol, result in results.items():
            # 銘柄情報を抽出
            symbol_code, symbol_name = symbol if isinstance(symbol, tuple) else (symbol, symbol)

            # 統計情報を集計
            summary_data.append({
                '銘柄コード': symbol_code,
                '銘柄名': symbol_name,
                '初期資金': result.get('initial_capital', 0),
                '最終資金': result.get('final_equity', 0),
                '総損益': result.get('final_equity', 0) - result.get('initial_capital', 0),
                '総リターン(%)': result.get('total_return', 0) * 100,
                '総トレード数': result.get('total_trades', 0),
                '勝ちトレード数': len(result.get('trades', pd.DataFrame())[result.get('trades', pd.DataFrame())['pnl'] > 0]),
                '負けトレード数': len(result.get('trades', pd.DataFrame())[result.get('trades', pd.DataFrame())['pnl'] <= 0]),
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
        csv_path = self.summary_dir / f"summary_{timestamp}.csv"
        summary_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"CSVサマリー保存: {csv_path}")

    def _generate_summary_chart(self, results: Dict, timestamp: str):
        """
        サマリーチャートを生成

        Args:
            results: バックテスト結果の辞書
            timestamp: タイムスタンプ
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

        # 3. トレード数（棒グラフ）
        ax3 = axes[1, 0]
        ax3.bar(range(len(symbols)), trade_counts, color='steelblue', alpha=0.7)
        ax3.set_xticks(range(len(symbols)))
        ax3.set_xticklabels(symbols, rotation=45, ha='right', fontsize=10)
        ax3.set_ylabel('トレード数', fontsize=12)
        ax3.set_title('銘柄別トレード数', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')

        # 4. 累積エクイティカーブ（複合）
        ax4 = axes[1, 1]
        for symbol, result in results.items():
            symbol_code, symbol_name = symbol if isinstance(symbol, tuple) else (symbol, symbol)
            equity_curve = result.get('equity_curve', pd.Series())
            if not equity_curve.empty:
                # DataFrameの場合は'equity'カラムを取得
                if isinstance(equity_curve, pd.DataFrame):
                    equity_values = equity_curve['equity'].values
                else:
                    equity_values = equity_curve.values

                ax4.plot(equity_curve.index, equity_values, label=symbol_name, alpha=0.7)

        ax4.set_xlabel('日付', fontsize=12)
        ax4.set_ylabel('エクイティ (円)', fontsize=12)
        ax4.set_title('累積エクイティカーブ', fontsize=14, fontweight='bold')
        ax4.legend(loc='best', fontsize=8)
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # レイアウト調整と保存
        plt.tight_layout()
        chart_path = self.summary_dir / f"summary_charts_{timestamp}.png"
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        plt.close()
        logger.info(f"サマリーチャート保存: {chart_path}")

    def _generate_summary_text(self, results: Dict, config: Dict, timestamp: str):
        """
        テキストサマリーレポートを生成

        Args:
            results: バックテスト結果の辞書
            config: 設定辞書
            timestamp: タイムスタンプ
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
        lines.append(f"損切り: {config['orb_strategy']['stop_loss'] * 100:.2f}%")
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

            lines.append(f"\n{symbol_name} ({symbol_code})")
            lines.append(f"  損益: {pnl:+,.0f} 円 ({total_return:+.2f}%)")
            lines.append(f"  トレード数: {trades}")
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
        text_path = self.summary_dir / f"summary_{timestamp}.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"テキストサマリー保存: {text_path}")

        # コンソール出力
        print('\n'.join(lines))

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
            csv_path = self.daily_reports_dir / f"{symbol_code}_{timestamp}_trades.csv"
            trades_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"{symbol_name} トレード履歴保存: {csv_path}")

        # エクイティカーブをCSV保存
        equity_df = result.get('equity_curve', pd.DataFrame())
        if not equity_df.empty:
            csv_path = self.daily_reports_dir / f"{symbol_code}_{timestamp}_equity.csv"
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
        if not trades_df.empty:
            colors = ['green' if pnl > 0 else 'red' for pnl in trades_df['pnl']]
            ax2.bar(range(len(trades_df)), trades_df['pnl'], color=colors, alpha=0.7)
            ax2.set_xlabel('トレード番号', fontsize=12)
            ax2.set_ylabel('損益 (円)', fontsize=12)
            ax2.set_title('トレード別損益', fontsize=14, fontweight='bold')
            ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
            ax2.grid(True, alpha=0.3, axis='y')

        # レイアウト調整と保存
        plt.tight_layout()
        chart_path = self.charts_dir / f"{symbol_code}_{timestamp}_chart.png"
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        plt.close()
        logger.info(f"{symbol_name} チャート保存: {chart_path}")
