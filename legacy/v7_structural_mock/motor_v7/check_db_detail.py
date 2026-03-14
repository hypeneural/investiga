import sqlite3
import json

db_path = r"c:\Users\Usuario\.gemini\antigravity\scratch\scrapers\output_scraping\tijucas_raw.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT dados_json FROM detalhes_liquidacao LIMIT 1")
row = cursor.fetchone()
if row and row[0]:
    try:
        data = json.loads(row[0])
        print("Chaves alto nível do JSON:", data.keys())
        if "dados" in data:
            print("Conteúdo do primeiro item em 'dados':")
            # print apenas algumas chaves para não poluir
            item = data["dados"][0] if isinstance(data["dados"], list) and len(data["dados"]) > 0 else data["dados"]
            print(json.dumps(item, indent=2)[:2000])
    except Exception as e:
        print("Erro ao decodificar JSON:", e)
else:
    print("No rows found or dados_json is null.")
conn.close()
