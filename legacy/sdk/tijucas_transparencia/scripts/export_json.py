import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tijucas_transparencia import TijucasTransparenciaClient

def main():
    print("Iniciando extração completa (Ativos, Afastados e Desligados)...")
    client = TijucasTransparenciaClient()
    
    # tipo_busca=3 para Todos, ou 1 para Ativos
    # A API exige desligamentoInicio e desligamentoFinal para tipo 3.
    # Caso simplificado, vamos pegar tipo=1 (somente ativos e afastados)
    # Se quiser tudo MESMO, usaria tipo 3 com datas longas.
    # O usuário pediu "todos os funcionários", vou pegar tipo=1 primeiro pois é o default util.
    # Na verdade, vou pegar o tipo_busca=3 (Todos) com um limite bem amplo para garantir "todos".
    
    funcionarios = client.pessoal.get_all_funcionarios(
        tipo_busca=3,
        desligamento_inicio="01/01/1900",
        desligamento_final="31/12/2100"
    )
    
    print(f"Total de registros obtidos: {len(funcionarios)}")
    
    # Salva o arquivo JSON
    output_path = "data/processed/todos_funcionarios_completo.json"
    import os
    os.makedirs("data/processed", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(funcionarios, f, ensure_ascii=False, indent=2, default=str)
        
    print(f"Arquivo salvo com sucesso em: {output_path}")

if __name__ == "__main__":
    main()
