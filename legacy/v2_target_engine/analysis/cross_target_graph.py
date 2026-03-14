from collections import defaultdict
from .utils import relevant_surnames

class CrossTargetGraph:
    def __init__(self, targets: list):
        self.targets = targets
        self.target_surnames = self._map_target_surnames()
        self.target_sectors = self._map_target_sectors()
        self.target_creditors = self._map_target_creditors()
        
    def _map_target_surnames(self):
        m = defaultdict(list)
        for idx, t in enumerate(self.targets):
            for s in relevant_surnames(t["alvo"]["nome"]):
                m[s].append(idx)
        return dict(m)
        
    def _map_target_sectors(self):
        m = defaultdict(list)
        for idx, t in enumerate(self.targets):
             cc = t.get("dadosFuncionais", {}).get("centroCusto", "")
             if cc:
                 m[cc].append(idx)
        return dict(m)

    def _map_target_creditors(self):
        """Maps CNPJ/CPF of creditors to the targets whose sectors paid them."""
        m = defaultdict(list)
        for idx, t in enumerate(self.targets):
            rede_creds = t.get("redeCredoresDoSetor", {})
            for c in rede_creds.get("topCredoresPF", []) + rede_creds.get("topCredoresCNPJHumanizados", []):
                doc = c.get("documento")
                if doc:
                    m[doc].append(idx)
        return dict(m)

    def find_connections(self, target_idx: int) -> dict:
        """Finds connections to other targets via shared surnames or sectors."""
        target = self.targets[target_idx]
        connections = {
            "outrosAlvosRelacionados": [],
            "motivos": []
        }
        
        # 1. Cross surnames
        t_surnames = relevant_surnames(target["alvo"]["nome"])
        connected_by_surname = set()
        for s in t_surnames:
            for other_idx in self.target_surnames.get(s, []):
                if other_idx != target_idx:
                    connected_by_surname.add((other_idx, s))
                    
        for other_idx, s in connected_by_surname:
            other_target = self.targets[other_idx]
            connections["outrosAlvosRelacionados"].append({
                "alvo": other_target["alvo"]["nome"],
                "cargo": other_target["alvo"].get("cargoInformado", ""),
                "tipoConexao": "shared_surname",
                "motivo": f"Sobrenome em comum: {s}"
            })
            
        # 2. Shared Creditors (Fornecedor Multissetorial)
        rede_creds = target.get("redeCredoresDoSetor", {})
        connected_by_cred = set()
        for c in rede_creds.get("topCredoresPF", []) + rede_creds.get("topCredoresCNPJHumanizados", []):
            doc = c.get("documento")
            if doc:
                for other_idx in self.target_creditors.get(doc, []):
                    if other_idx != target_idx:
                        connected_by_cred.add((other_idx, c.get("nomeExtraido"), doc))
                        
        for other_idx, cred_nome, doc in connected_by_cred:
            other_target = self.targets[other_idx]
            connections["outrosAlvosRelacionados"].append({
                "alvo": other_target["alvo"]["nome"],
                "cargo": other_target["alvo"].get("cargoInformado", ""),
                "tipoConexao": "shared_creditor",
                "motivo": f"Ambos pagaram o credor comum: {cred_nome} ({doc})"
            })
            
        return connections
