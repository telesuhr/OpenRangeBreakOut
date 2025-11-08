"""
PostgreSQLデータベースのセットアップスクリプト
"""
import psycopg2
import os


def setup_database():
    """データベースとテーブルをセットアップ"""
    
    # デフォルト設定
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'market_data'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    print("データベース接続設定:")
    print(f"  Host: {db_config['host']}")
    print(f"  Port: {db_config['port']}")
    print(f"  Database: {db_config['database']}")
    print(f"  User: {db_config['user']}")
    
    try:
        # PostgreSQLに接続（まずpostgresデータベースに接続）
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database='postgres',
            user=db_config['user'],
            password=db_config['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # データベースが存在するか確認
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_config['database'],)
        )
        exists = cursor.fetchone()
        
        if not exists:
            print(f"\nデータベース '{db_config['database']}' を作成中...")
            cursor.execute(f"CREATE DATABASE {db_config['database']}")
            print("✓ データベース作成完了")
        else:
            print(f"\nデータベース '{db_config['database']}' は既に存在します")
        
        cursor.close()
        conn.close()
        
        # 作成したデータベースに接続してテーブル作成
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # スキーマファイルを読み込んで実行
        schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        print("\nテーブルを作成中...")
        cursor.execute(schema_sql)
        conn.commit()
        print("✓ テーブル作成完了")
        
        # テーブル一覧を表示
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print("\n作成されたテーブル:")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n✓ データベースセットアップ完了!")
        return True
        
    except psycopg2.Error as e:
        print(f"\nエラー: {e}")
        print("\n確認事項:")
        print("1. PostgreSQLがインストールされているか")
        print("2. PostgreSQLサーバーが起動しているか")
        print("3. 接続情報（ホスト、ポート、ユーザー、パスワード）が正しいか")
        return False


if __name__ == "__main__":
    setup_database()
