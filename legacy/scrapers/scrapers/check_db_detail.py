import sqlite3
import json

def check_db():
    conn = sqlite3.connect('output_scraping/tijucas_raw.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id_pagamento, dados_json FROM detalhes_liquidacao LIMIT 3")
    rows = cursor.fetchall()
    for row in rows:
        print(f"--- Pagamento ID: {row[0]} ---")
        try:
            data = json.loads(row[1])
            # Se for html
            if "html" in data:
                print(f"HTML len: {len(data['html'])}")
                print(data['html'][:500])
            elif "retorno" in data and type(data["retorno"]) is list and len(data["retorno"]) > 0:
                 r0 = data["retorno"][0]
                 if "html" in r0:
                    print(f"HTML in retorno len: {len(r0['html'])}")
                    print(r0['html'][:500])
                 else:
                    print(json.dumps(r0, indent=2)[:500])
            else:
                print(json.dumps(data, indent=2)[:500])
        except Exception as e:
            print("Row data (no json):", row[1][:300])
    conn.close()

if __name__ == "__main__":
    check_db()
