# データベースセットアップガイド

PostgreSQLを使用してティックデータをキャッシュし、API制限を回避します。

## 前提条件

PostgreSQLがインストールされている必要があります。

### macOS
```bash
brew install postgresql@14
brew services start postgresql@14
```

### Ubuntu/Debian
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Windows
PostgreSQLの公式サイトからインストーラーをダウンロード
https://www.postgresql.org/download/windows/

## セットアップ手順

### 1. パッケージインストール
```bash
pip install psycopg2-binary
```

### 2. データベース作成

デフォルト設定で自動作成する場合：
```bash
python database/setup_db.py
```

カスタム設定の場合、環境変数を設定：
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=market_data
export DB_USER=postgres
export DB_PASSWORD=your_password

python database/setup_db.py
```

### 3. 接続確認

正常に完了すると以下のメッセージが表示されます：
```
✓ データベース作成完了
✓ テーブル作成完了

作成されたテーブル:
  - intraday_data
  - data_fetch_log
```

## 環境変数設定（オプション）

`.env`ファイルを作成して設定を保存できます：

```bash
# .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=market_data
DB_USER=postgres
DB_PASSWORD=postgres
```

## データベーススキーマ

### intraday_data テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | SERIAL | 主キー |
| symbol | VARCHAR(20) | 銘柄コード |
| timestamp | TIMESTAMP | 時刻 |
| open | NUMERIC(12,2) | 始値 |
| high | NUMERIC(12,2) | 高値 |
| low | NUMERIC(12,2) | 安値 |
| close | NUMERIC(12,2) | 終値 |
| volume | BIGINT | 出来高 |
| interval | VARCHAR(10) | 時間間隔 |
| created_at | TIMESTAMP | 作成日時 |

### data_fetch_log テーブル
| カラム | 型 | 説明 |
|--------|-----|------|
| id | SERIAL | 主キー |
| symbol | VARCHAR(20) | 銘柄コード |
| start_date | TIMESTAMP | 開始日時 |
| end_date | TIMESTAMP | 終了日時 |
| interval | VARCHAR(10) | 時間間隔 |
| source | VARCHAR(20) | データソース (api/cache) |
| records_count | INT | レコード数 |
| fetched_at | TIMESTAMP | 取得日時 |

## 使用方法

### バックテストでキャッシュを使用

バックテストスクリプトは自動的にキャッシュを使用します：

```python
from src.data.refinitiv_client import RefinitivClient

# キャッシュ有効（デフォルト）
client = RefinitivClient(app_key=api_key, use_cache=True)

# キャッシュ無効
client = RefinitivClient(app_key=api_key, use_cache=False)
```

### データの確認

```sql
-- キャッシュされているデータの確認
SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp)
FROM intraday_data
GROUP BY symbol
ORDER BY symbol;

-- データ取得履歴の確認
SELECT *
FROM data_fetch_log
ORDER BY fetched_at DESC
LIMIT 10;

-- API vs キャッシュの使用状況
SELECT source, COUNT(*), SUM(records_count)
FROM data_fetch_log
GROUP BY source;
```

## トラブルシューティング

### 接続エラー
```
psycopg2.OperationalError: could not connect to server
```

**解決策：**
1. PostgreSQLが起動しているか確認
   ```bash
   # macOS
   brew services list
   
   # Linux
   sudo systemctl status postgresql
   ```

2. ポート5432が使用されているか確認
   ```bash
   lsof -i :5432
   ```

### 認証エラー
```
psycopg2.OperationalError: FATAL: password authentication failed
```

**解決策：**
環境変数でパスワードを正しく設定
```bash
export DB_PASSWORD=correct_password
```

## パフォーマンス

### キャッシュヒット率の確認
```sql
SELECT 
    source,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM data_fetch_log
GROUP BY source;
```

### ストレージ使用量
```sql
SELECT 
    pg_size_pretty(pg_total_relation_size('intraday_data')) as total_size,
    COUNT(*) as row_count
FROM intraday_data;
```
