import sqlite3
import json

db_path = r"c:\Users\Usuario\.gemini\antigravity\scratch\scrapers\output_scraping\tijucas_raw.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT raw_data FROM pagamentos_normalizados LIMIT 1")
row = cursor.fetchone()
if row:
    print(json.dumps(json.loads(row[0]), indent=2))
else:
    print("No rows found.")
conn.close()
