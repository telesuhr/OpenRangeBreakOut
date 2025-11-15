# TradingSystem セットアップガイド

## 必要要件

- Python 3.8以上
- PostgreSQL 12以上
- Refinitiv Workspace (EIKON) またはRefinitiv Data Platform アカウント

## インストール手順

### 1. 仮想環境のセットアップ

#### macOS / Linux

```bash
# TradingSystemディレクトリに移動
cd TradingSystem

# セットアップスクリプトを実行
./setup_venv.sh

# 仮想環境を有効化
source venv/bin/activate
```

#### Windows

```cmd
REM TradingSystemディレクトリに移動
cd TradingSystem

REM セットアップスクリプトを実行
setup_venv.bat

REM 仮想環境を有効化
venv\Scripts\activate.bat
```

#### 手動セットアップ

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化 (macOS/Linux)
source venv/bin/activate

# 仮想環境を有効化 (Windows)
venv\Scripts\activate.bat

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 2. PostgreSQLデータベースのセットアップ

```bash
# PostgreSQLサービスを起動
# macOS (Homebrew)
brew services start postgresql

# Linux
sudo systemctl start postgresql

# データベースを作成
psql -U postgres -c "CREATE DATABASE market_data;"

# スキーマを作成
psql -U postgres -d market_data -f database/schema.sql

# または、Pythonスクリプトで初期化
python database/setup_db.py
```

### 3. 設定ファイルの編集

`config/strategy_config.yaml`を開いて、以下を設定：

```yaml
# データベース接続情報
database:
  host: "localhost"
  port: 5432
  database: "market_data"
  user: "postgres"
  password: "your_password"  # 実際のパスワードに変更

# Refinitiv API設定
data:
  refinitiv:
    app_key: "YOUR_APP_KEY"  # 実際のAPIキーに変更
```

### 4. 環境変数の設定（オプション）

機密情報を環境変数で管理する場合：

```bash
# .envファイルを作成（gitignore済み）
cat > .env << 'ENVEOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=market_data
DB_USER=postgres
DB_PASSWORD=your_password
REFINITIV_APP_KEY=your_app_key
ENVEOF
```

## システム実行

```bash
# 仮想環境が有効化されていることを確認
# プロンプトに (venv) が表示されているはず

# システムを実行
python run_trading_system.py
```

## トラブルシューティング

### psycopg2のインストールエラー

```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install libpq-dev python3-dev

# その後再度インストール
pip install psycopg2-binary
```

### Refinitiv APIエラー

1. Refinitiv Workspace (EIKON) が起動していることを確認
2. APIキーが正しいことを確認
3. ネットワーク接続を確認

### データベース接続エラー

```bash
# PostgreSQLが起動しているか確認
# macOS
brew services list | grep postgresql

# Linux
sudo systemctl status postgresql

# 接続テスト
psql -U postgres -c "SELECT version();"
```

## パッケージのアップデート

```bash
# 仮想環境を有効化
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate.bat  # Windows

# パッケージをアップデート
pip install --upgrade -r requirements.txt
```

## 仮想環境の削除

```bash
# 仮想環境を無効化
deactivate

# venvディレクトリを削除
rm -rf venv  # macOS/Linux
rmdir /s venv  # Windows
```

## 追加パッケージのインストール

新しいパッケージを追加する場合：

```bash
# パッケージをインストール
pip install package_name

# requirements.txtを更新
pip freeze > requirements.txt
```
