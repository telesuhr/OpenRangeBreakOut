# パラメータ最適化ガイド

## 概要

`optimize_parameters.py`は、オープンレンジブレイクアウト戦略の各種パラメータを最適化するための汎用スクリプトです。

## 使い方

### 基本コマンド

```bash
# 利益確定ラインの最適化
python optimize_parameters.py --param profit_target

# 損切りラインの最適化
python optimize_parameters.py --param stop_loss

# レンジ計測時間の最適化
python optimize_parameters.py --param range_duration

# エントリーウィンドウの最適化
python optimize_parameters.py --param entry_window

# 強制決済時刻の最適化
python optimize_parameters.py --param force_exit_time

# 全パラメータを個別に最適化
python optimize_parameters.py --all
```

### オプション

```bash
# カスタム設定ファイルを使用
python optimize_parameters.py --param profit_target --config my_config.yaml

# カスタム最適化設定を使用
python optimize_parameters.py --param profit_target --opt-config my_optimization.yaml
```

## 最適化可能なパラメータ

### 1. profit_target（利益確定ライン）

**現状**: null（利益確定なし、15:00終値で決済）

**最適化範囲**:
- なし
- 0.5%
- 1.0%
- 1.5%
- 2.0%
- 2.5%
- 3.0%

**用途**: 利益が出たらすぐに確定するか、引っ張るかの判断

### 2. stop_loss（損切りライン）

**現状**: 1.0%

**最適化範囲**:
- 0.5%
- 0.75% ← **最適化結果（損切り最適化で判明）**
- 1.0%
- 1.25%
- 1.5%
- 1.75%
- 2.0%

**用途**: 損失をどこで切るかの判断

### 3. range_duration（レンジ計測時間）

**現状**: 10分（09:05-09:15）

**最適化範囲**:
- 5分
- 10分
- 15分
- 20分

**用途**: レンジ判定に使う時間の長さ

**注意**: レンジ開始時刻は09:05固定。エントリー開始時刻は自動調整されます。

### 4. entry_window（エントリーウィンドウ）

**現状**: 45分（09:15-10:00）

**最適化範囲**:
- 15分
- 30分
- 45分
- 60分
- 90分

**用途**: ブレイクアウト後、どれくらいの時間エントリーを受け付けるか

### 5. force_exit_time（強制決済時刻）

**現状**: 15:00

**最適化範囲**:
- 14:00
- 14:30
- 15:00

**用途**: ポジションを強制決済する時刻

## 設定ファイル

### config/optimization_config.yaml

最適化の設定を管理するファイルです。

```yaml
# 最適化対象パラメータの値を追加・変更可能
parameters:
  profit_target:
    values: [null, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
    labels: ["なし", "0.5%", "1.0%", "1.5%", "2.0%", "2.5%", "3.0%"]
    description: "利益確定ライン"
    default: null

# 固定パラメータ（最適化期間など）
fixed:
  start_date: "2025-10-01"
  end_date: "2025-10-31"
  initial_capital: 10000000

# 評価指標
optimization:
  primary_metric: "total_return"  # total_pnl, total_return, win_rate
```

### カスタマイズ例

特定のセクターのみ最適化したい場合:

```yaml
sectors:
  filter: ["テクノロジー・通信", "電機・精密"]
  sector_analysis: true
```

## 出力ファイル

最適化結果は `results/optimization/` ディレクトリに保存されます。

```
results/optimization/
├── profit_target_optimization_20251109_120000.csv
├── stop_loss_optimization_20251109_120500.csv
├── range_duration_optimization_20251109_121000.csv
└── optimization.log
```

各CSVファイルには以下の情報が含まれます:
- パラメータ値
- 総取引数
- 平均勝率
- 黒字銘柄数
- 総損益
- 総合リターン

## 既存スクリプトとの互換性

既存のバックテストスクリプトはそのまま使用可能です:

```bash
# 従来の個別バックテスト（損切り1.0%）
python run_individual_backtest.py

# 従来の損切り最適化スクリプト（互換性維持）
python optimize_stop_loss.py

# 日次パフォーマンス分析（互換性維持）
python extract_and_analyze_daily.py
```

新しい最適化フレームワークは、これらを置き換えるのではなく、補完するものです。

## ワークフロー例

### ステップ1: 損切りラインを最適化

```bash
python optimize_parameters.py --param stop_loss
```

結果: 0.75%が最適

### ステップ2: 利益確定ラインを最適化

```bash
python optimize_parameters.py --param profit_target
```

結果: 例えば1.5%が最適と判明

### ステップ3: 最適パラメータをconfig.yamlに反映

```yaml
strategy:
  profit_target: 0.015  # 1.5%
  stop_loss: 0.0075     # 0.75%
```

### ステップ4: レンジ時間・エントリー時間を最適化

```bash
python optimize_parameters.py --param range_duration
python optimize_parameters.py --param entry_window
```

### ステップ5: 最終検証

```bash
# 最適パラメータでバックテスト実行
python run_individual_backtest.py
```

## 技術的な詳細

### パラメータ依存関係

一部のパラメータは相互依存しています:

- `range_duration` が変わると、`entry_start_time` が自動調整されます
- `entry_window` が変わると、`entry_end_time` が自動調整されます

例:
```
range_start_time: 09:05（固定）
range_duration: 15分
→ range_end_time: 09:20（自動計算）
→ entry_start_time: 09:20（自動計算）

entry_window: 30分
→ entry_end_time: 09:50（自動計算）
```

### DBキャッシュ活用

全ての最適化スクリプトはPostgreSQLキャッシュを活用し、API呼び出しを最小化します。

**初回実行**: データベースに全データをキャッシュ（5-10分）
**2回目以降**: キャッシュから取得（10秒以内）

### パフォーマンス

- 1パラメータ（7値）× 49銘柄 ≈ 5分（キャッシュ使用時）
- 全パラメータ（5種） ≈ 25分

## トラブルシューティング

### エラー: "Unknown parameter: xxx"

利用可能なパラメータを確認:
```bash
python optimize_parameters.py --help
```

### エラー: "FileNotFoundError: config/optimization_config.yaml"

設定ファイルが見つかりません。カレントディレクトリを確認してください:
```bash
ls config/optimization_config.yaml
```

### 結果が空になる

セクターフィルタが厳しすぎる可能性があります。`config/optimization_config.yaml`を確認:
```yaml
sectors:
  filter: null  # 全セクター対象
```

## 今後の拡張

以下の機能を将来追加予定:

- [ ] グリッドサーチ（複数パラメータの組み合わせ最適化）
- [ ] ベイズ最適化
- [ ] 並列処理による高速化
- [ ] シャープレシオによる最適化
- [ ] 複数期間でのロバストネス検証
- [ ] 歩進分析（ウォークフォワード）

## 参考資料

- `ANALYSIS_SUMMARY.md`: 分析手法の詳細
- `EXECUTIVE_SUMMARY.md`: エグゼクティブサマリー
- `config/config.yaml`: ベース設定ファイル
- `config/optimization_config.yaml`: 最適化設定ファイル
