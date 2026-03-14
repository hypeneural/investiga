import sqlite3

def check_db():
    conn = sqlite3.connect('output_scraping/tijucas_raw.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pagamentos_normalizados")
    print(f"Total: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT id_pagamento FROM pagamentos_normalizados LIMIT 5")
    rows = cursor.fetchall()
    print("\nExemplo de IDs brutos:")
    for row in rows:
        print(row[0])
        
    cursor.execute("SELECT COUNT(*) FROM pagamentos_normalizados WHERE data_pagamento LIKE '%2024'")
    print(f"\nPagos em 2024: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM pagamentos_normalizados WHERE data_pagamento LIKE '%2025' OR data_pagamento LIKE '%2026'")
    print(f"Pagos em 2025/2026: {cursor.fetchone()[0]}")

    conn.close()

if __name__ == "__main__":
    check_db()
