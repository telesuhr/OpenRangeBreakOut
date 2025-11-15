# ORB戦略トレーディングシステム

## 概要

Open Range Breakout (ORB) 戦略を使用したバックテストシステムです。
設定ファイル（YAML）で簡単に銘柄やパラメータを変更でき、データベース優先のデータ取得により効率的な運用が可能です。

## 主な機能

- **簡単な銘柄指定**: `config/strategy_config.yaml` で銘柄リストを簡単に編集可能
- **バックテストのみ**: ライブトレーディングは含まれません（安全）
- **データベース優先**: PostgreSQL → Refinitiv API → DBに保存（効率的）
- **豊富なレポート**: 日次レポート、チャート、サマリーを自動生成
- **パラメータ設定**: 損切り、利確、エントリー時間、オープンレンジ時間を柔軟に設定
- **拡張可能**: 将来的に複数戦略を追加可能な設計

## システム構成

```
OpenRangeBreakOut/
├── config/
│   └── strategy_config.yaml       # 設定ファイル（ここを編集）
├── src/
│   ├── backtester/
│   │   └── engine.py              # バックテストエンジン
│   ├── data/
│   │   ├── refinitiv_client.py    # Refinitiv APIクライアント
│   │   └── db_manager.py          # データベース管理
│   ├── reporting/
│   │   └── report_generator.py   # レポート生成器
│   └── strategy/
│       └── range_breakout.py      # ORB戦略ロジック
├── Output/                         # レポート出力先
│   ├── daily_reports/             # 銘柄別日次レポート (CSV)
│   ├── charts/                    # 銘柄別チャート (PNG)
│   ├── summary/                   # サマリーレポート (CSV, TXT, PNG)
│   └── trading_system.log         # システムログ
├── run_trading_system.py           # メインスクリプト
└── README_TRADING_SYSTEM.md        # このファイル
```

## 使い方

### 1. 設定ファイルの編集

`config/strategy_config.yaml` を開いて、以下の項目を必要に応じて編集します：

#### 銘柄リストの変更

```yaml
stocks:
  # テクノロジーセクター
  - ["6762.T", "TDK"]
  - ["6857.T", "アドバンテスト"]
  - ["6758.T", "キーエンス"]

  # 新しい銘柄を追加
  - ["7203.T", "トヨタ自動車"]
  - ["9983.T", "ファーストリテイリング"]
```

#### パラメータの変更

```yaml
orb_strategy:
  # オープンレンジ期間
  open_range:
    start_time: "09:05"    # 開始時刻（JST）
    end_time: "09:15"      # 終了時刻（JST）

  # エントリー期間
  entry_window:
    start_time: "09:15"    # エントリー開始時刻
    end_time: "11:00"      # エントリー終了時刻

  # 強制決済時刻
  force_exit_time: "15:00"

  # 利益目標（4% = 0.04）
  profit_target: 0.04

  # 損切りライン（0.75% = 0.0075）
  stop_loss: 0.0075
```

#### バックテスト期間の変更

```yaml
backtest_period:
  start_date: "2025-05-14"    # 開始日（YYYY-MM-DD）
  end_date: "2025-11-12"      # 終了日（YYYY-MM-DD）
```

#### 資金配分の変更

```yaml
capital:
  per_stock: 5000000      # 各銘柄に配分する資金（円）
  commission_rate: 0.001  # 手数料率（0.1%）
```

### 2. システム実行

```bash
# メインスクリプトを実行
python run_trading_system.py
```

実行すると以下の処理が順次実行されます：

1. 設定ファイルの読み込み
2. データベース接続（PostgreSQL）
3. Refinitiv API接続
4. 各銘柄のバックテスト実行
5. レポート生成（CSV, PNG, TXT）

### 3. レポートの確認

実行が完了すると、`Output/` フォルダ以下にレポートが生成されます：

#### サマリーレポート

- `Output/summary/summary_{timestamp}.csv` - 全銘柄の統計情報
- `Output/summary/summary_{timestamp}.txt` - テキスト形式のサマリー
- `Output/summary/summary_charts_{timestamp}.png` - 全銘柄の比較チャート

#### 銘柄別レポート

- `Output/daily_reports/{銘柄コード}_{timestamp}_trades.csv` - トレード履歴
- `Output/daily_reports/{銘柄コード}_{timestamp}_equity.csv` - エクイティカーブ
- `Output/charts/{銘柄コード}_{timestamp}_chart.png` - 銘柄別チャート

#### システムログ

- `Output/trading_system.log` - 実行ログ

## データ取得の仕組み

### データベース優先アプローチ

1. **データベース確認**: まずPostgreSQLデータベースから必要なデータを検索
2. **APIフォールバック**: データがない場合のみRefinitiv APIにアクセス
3. **自動保存**: APIから取得したデータを自動的にデータベースに保存
4. **再利用**: 次回以降はデータベースから高速に取得

このアプローチにより：
- API呼び出し回数を最小限に抑制
- バックテストの高速化
- データの永続化と再利用

### データベース設定

PostgreSQLデータベースの設定は `config/strategy_config.yaml` で変更できます：

```yaml
database:
  host: "localhost"
  port: 5432
  database: "market_data"
  user: "postgres"
  password: "postgres"
```

環境変数でも設定可能です：
- `DB_HOST`: データベースホスト
- `DB_PORT`: ポート番号
- `DB_NAME`: データベース名
- `DB_USER`: ユーザー名
- `DB_PASSWORD`: パスワード

## ORB戦略の説明

### 戦略概要

Open Range Breakout (ORB) は、取引開始直後の一定時間（オープンレンジ）の高値・安値をブレイクしたらエントリーする戦略です。

### エントリールール

1. **オープンレンジ**: 09:05～09:15の高値・安値を記録
2. **ブレイクアウト**: エントリー時間内（09:15～11:00）にオープンレンジの高値を上抜けたらロング
3. **ポジションサイズ**: 設定資金（デフォルト: 500万円）を株価で割った株数

### イグジットルール

以下のいずれかの条件で決済：

1. **利益目標**: エントリー価格から+4%に到達
2. **損切り**: エントリー価格から-0.75%に到達
3. **強制決済**: 15:00（取引終了時刻）に到達

### パラメータのチューニング

`config/strategy_config.yaml` でパラメータを調整できます：

- **オープンレンジ時間**: 短くすると範囲が狭くなり、エントリー機会が増加
- **エントリー時間**: 長くすると遅いブレイクアウトも捕捉
- **利益目標**: 高くすると大きな利益を狙うが勝率低下
- **損切りライン**: 狭くすると損失を抑えるが勝率低下

## トラブルシューティング

### エラー: 設定ファイルが見つかりません

```bash
エラー: 設定ファイルが見つかりません
```

**解決方法**: `config/strategy_config.yaml` が存在することを確認してください。

### エラー: データベース接続失敗

```bash
データベース接続エラー
```

**解決方法**:
1. PostgreSQLが起動していることを確認
2. `config/strategy_config.yaml` のデータベース設定を確認
3. データベースユーザーの権限を確認

### エラー: Refinitiv API接続失敗

```bash
Refinitiv API接続失敗
```

**解決方法**:
1. Refinitiv Workspace (EIKON) が起動していることを確認
2. APIキーが正しいことを確認
3. ネットワーク接続を確認

### データが取得できない

**考えられる原因**:
- 週末・祝日でデータが存在しない
- 銘柄コードが間違っている（`.T` サフィックス必須）
- Refinitiv APIの制限に達している

**解決方法**:
- バックテスト期間を営業日のみに設定
- 銘柄コードの形式を確認（例: `6762.T`）
- システムログ（`Output/trading_system.log`）を確認

## よくある質問

### Q1. 銘柄を追加・削除するには？

A1. `config/strategy_config.yaml` の `stocks` セクションを編集してください。

```yaml
stocks:
  - ["銘柄コード", "銘柄名"]
```

### Q2. 複数のパラメータセットを試すには？

A2. 設定ファイルをコピーして、別の名前で保存し、実行時に指定できます（将来実装予定）。
現在は設定ファイルを手動で変更して、都度実行してください。

### Q3. ライブトレーディングはできますか？

A3. このシステムはバックテストのみを目的としています。ライブトレーディング機能はありません。

### Q4. 他の戦略を追加できますか？

A4. 設計上は可能ですが、現在はORB戦略のみ実装されています。
将来的には `src/strategy/` に新しい戦略クラスを追加し、設定ファイルで選択できるようにする予定です。

### Q5. データベースを使わずに実行できますか？

A5. `config/strategy_config.yaml` で `use_cache: false` に設定すれば、データベースを使用せずにRefinitiv APIから直接データを取得できます。

```yaml
data:
  refinitiv:
    use_cache: false
```

## 今後の拡張予定

- [ ] 複数戦略のサポート（移動平均クロス、ボリンジャーバンド等）
- [ ] パラメータ最適化機能（グリッドサーチ）
- [ ] Webダッシュボード（Flask/Dash）
- [ ] リアルタイムアラート機能
- [ ] 複数銘柄のポートフォリオ最適化

## ライセンス

このプロジェクトは個人使用を目的としています。

## サポート

問題が発生した場合は、以下を確認してください：

1. システムログ: `Output/trading_system.log`
2. エラーメッセージの内容
3. 設定ファイルの記述ミス

それでも解決しない場合は、プロジェクトメンテナーに連絡してください。
