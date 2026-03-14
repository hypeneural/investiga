import time
import sqlite3
import os
import sys

# Insere na raiz para achar o módulo
sys.path.insert(0, r"c:\Users\Usuario\.gemini\antigravity\scratch\scrapers")
from tijucas_scraper_detail import TijucasDetailScraper

db_path = r"c:\Users\Usuario\.gemini\antigravity\scratch\scrapers\output_scraping\tijucas_raw.db"

def main():
    scraper = TijucasDetailScraper(db_path)
    
    print("=== Iniciando Worker de Raspagem Profunda (Deep Fetch) ===")
    print(f"Alvo: {db_path}")
    
    while True:
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Testa se a tabela base existe primeiro
            try:
                c.execute("SELECT COUNT(*) FROM pagamentos_normalizados WHERE id_pagamento NOT IN (SELECT id_pagamento FROM detalhes_liquidacao)")
                pendentes = c.fetchone()[0]
            except sqlite3.OperationalError:
                pendentes = 0
                
            conn.close()
            
            if pendentes == 0:
                print("Nenhum detalhe pendente de raspagem na fila. Aguardando 10s...")
                time.sleep(10)
                continue
                
            print(f"\n[Fila] {pendentes} pagamentos aguardando Detalhes. Iniciando lote de 100...")
            scraper.run_enrichment(limite=100)
            
            time.sleep(3) # Pausa entre lotes
            
        except KeyboardInterrupt:
            print("\nFim do Deep Fetch (Cancelado pelo usuário).")
            break
        except Exception as e:
            print(f"Erro no loop principal: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
