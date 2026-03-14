import argparse
from datetime import date
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.tijucas_transparencia import TijucasTransparenciaClient
from src.tijucas_transparencia.exporters import export_csv, export_excel

def main():
    parser = argparse.ArgumentParser(description="Busca funcionários no Portal de Transparência.")
    parser.add_argument("--tipo-busca", type=int, default=1, choices=[1, 2, 3], help="1: Ativos, 2: Desligados, 3: Todos")
    parser.add_argument("--desligamento-inicio", type=str, help="Data inicial de desligamento (DD/MM/AAAA)")
    parser.add_argument("--desligamento-final", type=str, help="Data final de desligamento (DD/MM/AAAA)")
    args = parser.parse_args()

    client = TijucasTransparenciaClient()

    print(f"Buscando com tipo_busca={args.tipo_busca}...")
    df = client.pessoal.get_funcionarios_df(
        tipo_busca=args.tipo_busca,
        desligamento_inicio=args.desligamento_inicio,
        desligamento_final=args.desligamento_final
    )

    print("Total carregado:", len(df))
    if len(df) > 0:
        print("Amostra:")
        print(df[["nome", "cargo", "salarioBaseValor"]].head(5).to_string())

    today = date.today().isoformat()
    csv_path = f"data/processed/funcionarios_{today}.csv"
    export_csv(df, csv_path)
    print(f"Arquivo CSV salvo em: {csv_path}")

if __name__ == "__main__":
    main()
