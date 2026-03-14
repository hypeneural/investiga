import os
import json
from collections import defaultdict

class TransversalAnalyzer:
    """
    V4.2: Eixo A - Cartéis e Fornecedores Transversais.
    Analisa credores que atuam transversalmente (vários setores ou vários alvos políticos)
    e figuram como Top Credores globalmente.
    """
    def __init__(self, target_trees):
        self.target_trees = target_trees
        self.creditor_registry = defaultdict(lambda: {"nome": "", "total_recebido": 0.0, "alvos_ligados": set(), "setores_controlados": set(), "setores_alvo_trabalha": set(), "is_pf": False})
        
    def _build_registry(self):
        """Varre todas as árvores e constrói o mapa global de credores."""
        for tree in self.target_trees:
            alvo_nome = tree["alvo"]["nome"]
            
            # 1. Credores ligados à Família (Trilha 4)
            if "redeFamiliar" in tree:
                for nucleo in tree["redeFamiliar"].get("nucleos", []):
                    for cnpj in nucleo.get("credoresFortes", []) + nucleo.get("credoresMedios", []):
                        self.creditor_registry[cnpj]["alvos_ligados"].add(alvo_nome)
            
            # 2. Pagamentos Diretos (Trilha 1/2)
            if "pagamentosDiretos" in tree:
                # Target itself is the creditor, but wait, usually we want to see SUPPLIERS
                # Target's own direct payments don't count towards "shielded suppliers" unless the target has PJ.
                pass
                
            # 3. Credores do Setor (Privados)
            if "redeCredoresDoSetor" in tree and "topCredoresCNPJPrivados" in tree["redeCredoresDoSetor"]:
                # The target controls this sector (Trilha 3)
                for cred in tree["redeCredoresDoSetor"]["topCredoresCNPJPrivados"]:
                    cnpj = cred["documento"]
                    self.creditor_registry[cnpj]["nome"] = cred["nomeExtraido"]
                    self.creditor_registry[cnpj]["alvos_ligados"].add(f"{alvo_nome} (Gestor)")
                    for orgao in tree["redeCredoresDoSetor"].get("orgaosMonitorados", []):
                        self.creditor_registry[cnpj]["setores_controlados"].add(orgao)
                    self.creditor_registry[cnpj]["total_recebido"] += cred["totalRecebido"]
            
            # 4. Credores do Setor onde o alvo Trabalha (Trilha 2 Setorial)
            if "redeSetor" in tree and "topCredoresCNPJPrivados" in tree["redeSetor"]:
                for cred in tree["redeSetor"]["topCredoresCNPJPrivados"]:
                    cnpj = cred["documento"]
                    self.creditor_registry[cnpj]["nome"] = cred["nomeExtraido"]
                    self.creditor_registry[cnpj]["alvos_ligados"].add(f"{alvo_nome} (Empregado)")
                    self.creditor_registry[cnpj]["setores_alvo_trabalha"].add(tree["redeSetor"]["centroCusto"])
                    self.creditor_registry[cnpj]["total_recebido"] += cred["totalRecebido"]

    def analyze(self):
        self._build_registry()
        
        global_alerts = []
        
        for cnpj, data in self.creditor_registry.items():
            if not cnpj:
                continue
                
            qtd_alvos = len(data["alvos_ligados"])
            qtd_setores = len(data["setores_controlados"]) + len(data["setores_alvo_trabalha"])
            
            # Rule 1: Transversal Creditor (Cartel suspect)
            if qtd_alvos >= 2 and qtd_setores >= 2 and data["total_recebido"] > 50000:
                global_alerts.append({
                    "tipo": "CREDOR_TRANSVERSAL",
                    "credor": data["nome"],
                    "documento": cnpj,
                    "qtd_alvos": qtd_alvos,
                    "alvos": list(data["alvos_ligados"]),
                    "qtd_setores": qtd_setores,
                    "setores": list(data["setores_controlados"].union(data["setores_alvo_trabalha"])),
                    "total_estimado": data["total_recebido"]
                })
                
        # Inject back into target trees
        for tree in self.target_trees:
            alvo_nome = tree["alvo"]["nome"]
            tree_alerts = []
            
            for alert in global_alerts:
                if alvo_nome in alert["alvos"] or f"{alvo_nome} (Gestor)" in alert["alvos"] or f"{alvo_nome} (Empregado)" in alert["alvos"]:
                    tree_alerts.append(alert)
                    
            if tree_alerts:
                tree["transversal_alerts"] = tree_alerts
                
        # Sort globals by total volume
        global_alerts.sort(key=lambda x: x["total_estimado"], reverse=True)
        return global_alerts

