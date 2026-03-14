from collections import defaultdict
from .utils import extract_cpf_mid, extract_cpf_mid_full, is_cpf, normalize_name, extract_human_name_from_credor

class MatchClass:
    EXATO_FORTE = "EXATO_FORTE"
    FORTE = "FORTE"
    MEDIA = "MEDIA"
    FRACA = "FRACA"
    AMBIGUA = "AMBIGUA"

MATCH_CONFIDENCE = {
    MatchClass.EXATO_FORTE: 0.95,
    MatchClass.FORTE: 0.80,
    MatchClass.MEDIA: 0.60,
    MatchClass.FRACA: 0.30,
    MatchClass.AMBIGUA: 0.15,
}

class IdentityResolver:
    def __init__(self, funcionarios: list):
        self.funcs = funcionarios
        self.by_cpf_mid = defaultdict(list)
        self.by_name = defaultdict(list)
        self._index_funcionarios()

    def _index_funcionarios(self):
        for i, f in enumerate(self.funcs):
            mid = extract_cpf_mid(f.get("cpf", ""))
            if mid:
                self.by_cpf_mid[mid].append(i)
            
            nome_norm = normalize_name(f.get("nome", ""))
            if nome_norm:
                self.by_name[nome_norm].append(i)

    def resolve_credor(self, cpf_cnpj_credor: str, nome_credor: str) -> list[dict]:
        """
        Resolves a creditor (despesa/resto) against the funcionário database.
        Returns a list of match dicts: { func_idx, classe, confianca, motivo }.
        """
        results = []
        is_pf = is_cpf(cpf_cnpj_credor)
        mid = extract_cpf_mid_full(cpf_cnpj_credor) if is_pf else ""
        
        # Enhanced human name extraction targeting CNPJs as well
        nome_norm = extract_human_name_from_credor(nome_credor)
        
        funcs_by_cpf = self.by_cpf_mid.get(mid, []) if mid else []
        funcs_by_name = self.by_name.get(nome_norm, []) if nome_norm else []
        
        # Scenario 1: CPF matched
        if funcs_by_cpf:
            if len(funcs_by_cpf) == 1:
                idx = funcs_by_cpf[0]
                matched_func_name = normalize_name(self.funcs[idx].get("nome", ""))
                
                # Exato Forte: CPF mid unique + name matches exactly
                if matched_func_name == nome_norm:
                    results.append({
                        "func_idx": idx,
                        "classe": MatchClass.EXATO_FORTE,
                        "confianca": MATCH_CONFIDENCE[MatchClass.EXATO_FORTE],
                        "motivo": "CPF parcial e nome exato",
                        "match_keys": ["cpf", "nome"]
                    })
                else:
                    # Forte: CPF mid unique but name doesn't match perfectly
                    results.append({
                        "func_idx": idx,
                        "classe": MatchClass.FORTE,
                        "confianca": MATCH_CONFIDENCE[MatchClass.FORTE],
                        "motivo": f"CPF parcial bate, nome diverge ({matched_func_name} != {nome_norm})",
                        "match_keys": ["cpf"]
                    })
            else:
                # Ambígua: Multiple employees with same CPF middle digits
                for idx in funcs_by_cpf:
                    results.append({
                        "func_idx": idx,
                        "classe": MatchClass.AMBIGUA,
                        "confianca": MATCH_CONFIDENCE[MatchClass.AMBIGUA],
                        "motivo": "CPF parcial bate em múltiplos funcionários",
                        "match_keys": ["cpf_ambiguo"]
                    })
            
            return results  # Stop if CPF matched (don't fallback to name-only)

        # Scenario 2: Name matched (No CPF or CPF didn't match)
        if funcs_by_name:
            if len(funcs_by_name) == 1:
                idx = funcs_by_name[0]
                results.append({
                    "func_idx": idx,
                    "classe": MatchClass.MEDIA,
                    "confianca": MATCH_CONFIDENCE[MatchClass.MEDIA],
                    "motivo": "Nome exato único (sem CPF)",
                    "match_keys": ["nome"]
                })
            else:
                for idx in funcs_by_name:
                    results.append({
                        "func_idx": idx,
                        "classe": MatchClass.FRACA,
                        "confianca": MATCH_CONFIDENCE[MatchClass.FRACA],
                        "motivo": "Nome exato bate em múltiplos funcionários (sem CPF)",
                        "match_keys": ["nome_ambiguo"]
                    })
            
        return results

    def find_all_person_records(self, func_data: dict) -> list[dict]:
        """
        Given a specific employee record, find all other records in the database
        that belong to the same person (e.g., matching CPF middle digits or exact name).
        """
        cpf_mid = extract_cpf_mid(func_data.get("cpf", ""))
        nome_norm = normalize_name(func_data.get("nome", ""))
        
        records = []
        seen_indices = set()
        
        if cpf_mid and cpf_mid in self.by_cpf_mid:
            for idx in self.by_cpf_mid[cpf_mid]:
                if idx not in seen_indices:
                    records.append(self.funcs[idx])
                    seen_indices.add(idx)
                    
        # Fallback/addition: exact name matches if CPF is missing or to catch edge cases
        if nome_norm and nome_norm in self.by_name:
            for idx in self.by_name[nome_norm]:
                if idx not in seen_indices:
                    records.append(self.funcs[idx])
                    seen_indices.add(idx)
                    
        # Ensure the original record is in there if it wasn't caught somehow
        if not any(r.get("nome") == func_data.get("nome") and r.get("cargo") == func_data.get("cargo") for r in records):
             records.append(func_data)
             
        return records
