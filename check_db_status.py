"""
データベースの状態確認
"""
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port='5432',
    database='market_data',
    user='postgres',
    password='postgres'
)

cursor = conn.cursor()

# データ件数確認
cursor.execute("SELECT COUNT(*) FROM intraday_data")
intraday_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM data_fetch_log")
log_count = cursor.fetchone()[0]

print("データベース状態:")
print(f"  intraday_data: {intraday_count}行")
print(f"  data_fetch_log: {log_count}行")

if intraday_count > 0:
    # 銘柄別データ件数
    cursor.execute("""
        SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp)
        FROM intraday_data
        GROUP BY symbol
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    
    print("\n保存されている銘柄（上位10件）:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}行 ({row[2]} - {row[3]})")

cursor.close()
conn.close()
