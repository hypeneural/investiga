import re
from .utils import normalize_name, get_tokens

class TargetResolver:
    def __init__(self, funcionarios: list):
        self.funcs = funcionarios
    
    def resolve_target(self, target: dict) -> list[dict]:
        """
        Fuzzy matches a target against the funcionário database.
        Returns a list of matching funcionário records with confidence.
        """
        target_name = normalize_name(target["nome"])
        target_tokens = set(get_tokens(target_name))
        
        matches = []
        for f in self.funcs:
            func_name = normalize_name(f.get("nome", ""))
            func_tokens = set(get_tokens(func_name))
            
            # 1. Exact match
            if func_name == target_name:
                matches.append({"func": f, "confianca": 0.99, "status": "EXATO"})
                continue
                
            # 2. Fuzzy match
            if not target_tokens or not func_tokens:
                continue
                
            first_target = target_name.split()[0]
            first_func = func_name.split()[0]
            last_target = target_name.split()[-1]
            last_func = func_name.split()[-1]
            
            inter = target_tokens & func_tokens
            coverage = len(inter) / max(1, min(len(target_tokens), len(func_tokens)))
            
            # If first name matches, last name matches, and coverage is >= 60%
            if first_target == first_func and last_target == last_func and coverage >= 0.6:
                matches.append({"func": f, "confianca": round(coverage, 2), "status": "FUZZY"})
                
        return sorted(matches, key=lambda x: x["confianca"], reverse=True)
