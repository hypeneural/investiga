import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tijucas_transparencia import TijucasTransparenciaClient
from src.tijucas_transparencia.filters import filtrar_funcionarios

def main():
    client = TijucasTransparenciaClient()

    print("Buscando funcionários...")
    df = client.pessoal.get_funcionarios_df(tipo_busca=1)

    print(f"Total: {len(df)}")

    professores = filtrar_funcionarios(
        df,
        situacao="Trabalhando",
        cargo_contains="Professor",
    )
    print("\n=== Professores ===")
    print(f"Total: {len(professores)}")
    print(professores[["nome", "cargo", "localTrabalho", "salarioBaseValor"]].head(5).to_string())

    saude = filtrar_funcionarios(
        df,
        local_contains="saúde",
    )
    print("\n=== Pessoal da Saúde ===")
    print(f"Total: {len(saude)}")
    print(saude[["nome", "cargo", "localTrabalho"]].head(5).to_string())

if __name__ == "__main__":
    main()
