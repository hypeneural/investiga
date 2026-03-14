import sqlite3

def check_raw():
    conn = sqlite3.connect('output_scraping/tijucas_raw.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pagamentos_normalizados ORDER BY data_pagamento DESC LIMIT 3")
    rows = cursor.fetchall()
    for row in rows:
        d = dict(row)
        print("---")
        for k, v in d.items():
            print(f"{k}: {v} (Type: {type(v)})")
            
if __name__ == "__main__":
    check_raw()
