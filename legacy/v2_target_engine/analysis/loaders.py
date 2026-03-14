import json
import os

def load_data(data_dir: str):
    print("Carregando datasets principais...")
    func_path = os.path.join(data_dir, "funcionarios_ordenados.json")
    desp_path = os.path.join(data_dir, "despesas.json")
    restos_path = os.path.join(data_dir, "despesas_restos.json")
    
    with open(func_path, "r", encoding="utf-8") as f:
        funcs = json.load(f)["funcionarios"]
        
    with open(desp_path, "r", encoding="utf-8") as f:
        despesas = json.load(f)["registros"]
        
    with open(restos_path, "r", encoding="utf-8") as f:
        restos = json.load(f)["registros"]
        
    print(f"  Funcionários: {len(funcs)}")
    print(f"  Despesas: {len(despesas)}")
    print(f"  Restos a pagar: {len(restos)}")
    
    return funcs, despesas, restos


def define_targets():
    return [
        {"nome": "MAICKON CAMPOS SGROTT", "cargo": "Prefeito Municipal", "is_legislativo": False},
        {"nome": "RUDNEI DE AMORIM", "cargo": "Vice-Prefeito", "is_legislativo": False},
        {"nome": "LEILA DOS ANJOS COSTA", "cargo": "Chefia de Gabinete", "is_legislativo": False},
        {"nome": "ANA CRISTINA S. RODRIGUES", "cargo": "Sec. Finanças", "is_legislativo": False},
        {"nome": "SHEILA DIAS", "cargo": "Sec. Educação", "is_legislativo": False},
        {"nome": "JHONE RENNER POLI", "cargo": "Sec. Obras e Transportes", "is_legislativo": False},
        {"nome": "WILLIAM CLEMES", "cargo": "Sec. Administração", "is_legislativo": False},
        {"nome": "SAULO CÂMARA FARIA", "cargo": "Controladoria", "is_legislativo": False},
        {"nome": "PYERRE CABRAL", "cargo": "Dir. Comunicação Social", "is_legislativo": False},
        {"nome": "SIDNEY MACHADO", "cargo": "Dir. Trânsito", "is_legislativo": False},
        {"nome": "ERIVELTO LEAL DOS SANTOS", "cargo": "Fund. Mun. Esportes / Vereador", "is_legislativo": False},
        {"nome": "MATEUS DELLA GUISTINA GUINZANI", "cargo": "Procuradoria Geral", "is_legislativo": False},
        {"nome": "TIAGO SUCKOW S. C. GUIMARÃES", "cargo": "SAMAE", "is_legislativo": False},
        {"nome": "MARIA EDÉSIA DA SILVA VARGAS", "cargo": "Sec. Assistência Social", "is_legislativo": False},
        {"nome": "ODIRLEI RESINI", "cargo": "Sec. Agricultura", "is_legislativo": False},
        {"nome": "PAULA REGINA DA SILVA", "cargo": "Sec. Cultura, Juventude e Turismo", "is_legislativo": False},
        {"nome": "NARA ROCHA", "cargo": "Defesa Civil", "is_legislativo": False},
        {"nome": "LOISIANE DOS SANTOS", "cargo": "Sec. Desenvolvimento Econômico", "is_legislativo": False},
        {"nome": "MARGARETH CADORE", "cargo": "Sec. Saúde", "is_legislativo": False},
        {"nome": "EZEQUIEL DE AMORIM", "cargo": "Sec. Pesca e Aquicultura", "is_legislativo": False},
        {"nome": "JORDAN CAMPOS LAUS", "cargo": "Sec. Planejamento", "is_legislativo": False},
        {"nome": "MURILLO MELLO FERRANDIN", "cargo": "Sec. Segurança Pública", "is_legislativo": False},
        {"nome": "CHRISTIAN ROCHA NEVES", "cargo": "Previserti", "is_legislativo": False},
        {"nome": "JOSÉ ROBERTO GIACOMOSSI", "cargo": "PROCON", "is_legislativo": False},
        {"nome": "FRANCIELE DELLA MEA", "cargo": "Dir. Compras", "is_legislativo": False},
        {"nome": "SEBASTIÃO SILVA", "cargo": "Dir. Recursos Humanos", "is_legislativo": False},
        {"nome": "CLÁUDIO EDUARDO DE SOUZA", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "ECIO HELIO DE MELO", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "ESAÚ BAYER", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "FLAVIO HENRIQUE SOUZA", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "FABIANO MORFELLE", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "JOSÉ VICENTE DE SOUZA E SILVA", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "JULIO CESAR BUCOSKI", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "LIZANDRA DADAM", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "MAURICIO POLI", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "NADIR OLINDINA AMORIM", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "PAULO CESAR PEREIRA", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "RENATO LAURINDO JÚNIOR", "cargo": "Vereador", "is_legislativo": True},
        {"nome": "VILSON JOSÉ PORCINCULA", "cargo": "Vereador", "is_legislativo": True},
    ]

# Maps the exact names from targets to the organ/unit names present in despesas.json
# orgaoDescricao / unidadeDescricao
SECTOR_OWNERSHIP = {
    "MAICKON CAMPOS SGROTT": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Gabinete do Prefeito"]},
    "RUDNEI DE AMORIM": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": []},
    "LEILA DOS ANJOS COSTA": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Gabinete do Prefeito"]},
    "ANA CRISTINA S. RODRIGUES": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secretaria de Administração e Finanças", "Secretaria de Finanças", "Encargos Especiais"]},
    "SHEILA DIAS": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secretaria de Educação", "FUNDO MANUT.DESENV. EDUCACÃO BASICA - FUNDEB"]},
    "JHONE RENNER POLI": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secret. Mun. Obras Transportes Servi. Publicos"]},
    "WILLIAM CLEMES": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secretaria de Administração e Finanças", "Secretaria de Administração"]},
    "MARGARETH CADORE": {"orgaos": ["FUNDO M. DE SAÚDE DE TIJUCAS", "MUNICÍPIO DE TIJUCAS"], "unidades": ["Fundo de Saúde", "FUNDO MUN. DE SAÚDE  - FMS"]},
    "MARIA EDÉSIA DA SILVA VARGAS": {"orgaos": ["FUNDO MUNICIPAL ASSISTÊNCIA SOCIAL", "FUNDO MUNIC. DIREITOS DA CRIAÇA EADOLESCENTE", "MUNICÍPIO DE TIJUCAS"], "unidades": ["FUNDO MUN. ASSISTÊNCIA SOCIAL- FMAS", "Fundo M. DA Inf. e Adolescência - Fia Tijucas", "Sec. Mulher, Habitação e Assis Social"]},
    "ODIRLEI RESINI": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secretária da Agricultura"]},
    "PAULA REGINA DA SILVA": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secretaria de Cultura, Juventude e Turismo"]},
    "LOISIANE DOS SANTOS": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secretaria Desenv Econômico "]},
    "EZEQUIEL DE AMORIM": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secretaria Municipal de Pesca e Aquicultura"]},
    "JORDAN CAMPOS LAUS": {"orgaos": ["MUNICÍPIO DE TIJUCAS"], "unidades": ["Secretaria Municipal de Planejamento", "Secretaria de Desenvolvimento Urbano"]},
    "TIAGO SUCKOW S. C. GUIMARÃES": {"orgaos": ["SERVIÇO AUTÔNOMO MUNICIPAL DE ÁGUA E ESGOTO"], "unidades": ["Serviço Autônomo M. de Agua e Esgoto"]},
    "ERIVELTO LEAL DOS SANTOS": {"orgaos": ["FUNDAÇÃO MUNICIPAL DE ESPORTES"], "unidades": ["Fundação Municipal de Esportes"]},
    "CHRISTIAN ROCHA NEVES": {"orgaos": ["Instituto de Previd. dos Serv. Pub. Tijucas"], "unidades": ["PREVISERTI"]},
    # General catch-all for CÂMARA MUNICIPAL DE VEREADORES
    "CÂMARA MUNICIPAL": {"orgaos": ["CÂMARA MUNICIPAL DE DEMONSTRAÇÃO", "CÂMARA MUNICIPAL DE VEREADORES"], "unidades": []}
}
