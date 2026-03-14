from .identity_resolution import IdentityResolver
from .utils import parse_value

class PaymentLinker:
    def __init__(self, identity_resolver: IdentityResolver, despesas: list, restos: list):
        self.resolver = identity_resolver
        self.despesas = despesas
        self.restos = restos
        self.linked_despesas = []
        self.linked_restos = []
        
    def resolve_all_payments(self):
        """Resolves all payments to any funcionário and builds the audit trail."""
        for d in self.despesas:
            cpf_cnpj = d.get("cpfCnpjCredor", "")
            nome = d.get("nomeCredor", "")
            matches = self.resolver.resolve_credor(cpf_cnpj, nome)
            if matches:
                 self.linked_despesas.append({
                     "despesa": d,
                     "matches": matches
                 })
                 
        for r in self.restos:
             cpf_cnpj = r.get("cpfCnpjCredor", "")
             nome = r.get("nomeCredor", "")
             matches = self.resolver.resolve_credor(cpf_cnpj, nome)
             if matches:
                 self.linked_restos.append({
                     "resto": r,
                     "matches": matches
                 })
                 
        return self.linked_despesas, self.linked_restos

    def get_payments_for_funcionario(self, func_idx: int) -> dict:
        """Extracts direct matching payments for a specific func_idx."""
        matched_despesas = []
        matched_restos = []
        total_pago = 0.0
        
        for link in self.linked_despesas:
            for m in link["matches"]:
                if m["func_idx"] == func_idx:
                    matched_despesas.append({
                        "despesa": link["despesa"],
                        "evidencia": m
                    })
                    total_pago += parse_value(link["despesa"].get("valorPago", 0))
                    
        for link in self.linked_restos:
            for m in link["matches"]:
                if m["func_idx"] == func_idx:
                    matched_restos.append({
                        "resto": link["resto"],
                        "evidencia": m
                    })
                    total_pago += parse_value(link["resto"].get("valorPago", 0))
                    
        return {
             "despesas": matched_despesas,
             "restos": matched_restos,
             "totalPago": total_pago
        }
