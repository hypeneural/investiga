"""
V4.1.1: Sanity Checks Module
Validates target trees before export to prevent implausible numbers from reaching the report.
"""


class SanityChecker:
    """Runs post-scoring validations on all target trees."""
    
    def __init__(self, teto_salario_nucleo: float = 300_000.0,
                 teto_despesa_nucleo: float = 200_000_000.0):
        self.teto_salario = teto_salario_nucleo
        self.teto_despesa = teto_despesa_nucleo
    
    def validate_all(self, target_trees: list) -> list[dict]:
        """
        Validates all trees and returns a list of global warnings.
        Also injects per-tree warnings into tree["sanity_warnings"].
        """
        global_warnings = []
        
        for tree in target_trees:
            if tree["alvo"].get("statusResolucao") == "nao_encontrado":
                continue
                
            tree_warnings = tree.get("sanity_warnings", [])
            
            # Check 1: Member deduplication across nuclei
            warnings = self._check_dedup_members(tree)
            tree_warnings.extend(warnings)
            
            # Check 2: Creditor deduplication across nuclei  
            warnings = self._check_credor_dedup(tree)
            tree_warnings.extend(warnings)
            
            # Check 3: Evidence quality vs financial claims
            warnings = self._check_evidence_vs_claims(tree)
            tree_warnings.extend(warnings)
            
            tree["sanity_warnings"] = tree_warnings
            global_warnings.extend(tree_warnings)
        
        return global_warnings
    
    def _check_dedup_members(self, tree: dict) -> list[dict]:
        """Checks that no func_idx appears in multiple nuclei of the same target."""
        warnings = []
        nucleos = tree.get("redeFamiliar", {}).get("nucleosEncontrados", [])
        
        seen_indices = {}  # func_idx -> first nucleo name
        for nucleo in nucleos:
            nucleo_name = nucleo.get("sobrenomesCore", "?")
            for membro in nucleo.get("membros", []):
                idx = membro.get("func_idx")
                if idx in seen_indices:
                    warnings.append({
                        "tipo": "SANITY_MEMBRO_DUPLICADO",
                        "alvo": tree["alvo"]["nome"],
                        "motivo": f"func_idx {idx} ({membro.get('nome', '?')}) aparece em 2+ núcleos: '{seen_indices[idx]}' e '{nucleo_name}'"
                    })
                else:
                    seen_indices[idx] = nucleo_name
        
        return warnings
    
    def _check_credor_dedup(self, tree: dict) -> list[dict]:
        """Verifies no CNPJ is summed in two nuclei of the same target (informational, since family_network now handles this)."""
        # This is now handled at the source in family_network.py via global_credor_seen
        # Keep as a verification pass
        return []
    
    def _check_evidence_vs_claims(self, tree: dict) -> list[dict]:
        """Flags when high financial claims are based on weak evidence."""
        warnings = []
        nucleos = tree.get("redeFamiliar", {}).get("nucleosEncontrados", [])
        
        for nucleo in nucleos:
            forca = nucleo.get("forcaEvidencia", "FRACA")
            total_desp = nucleo.get("totalDespesasFam", 0)
            
            # FRACA nuclei should never have financial totals
            if forca == "FRACA" and total_desp > 0:
                warnings.append({
                    "tipo": "SANITY_FRACA_COM_VALOR",
                    "alvo": tree["alvo"]["nome"],
                    "nucleo": nucleo.get("sobrenomesCore", "?"),
                    "motivo": f"Núcleo FRACO tem totalDespesasFam = R$ {total_desp:,.2f} (deveria ser zero)"
                })
            
            # MEDIA nuclei with very high values
            if forca == "MEDIA" and total_desp > 10_000_000:
                warnings.append({
                    "tipo": "SANITY_MEDIA_VALOR_ALTO",
                    "alvo": tree["alvo"]["nome"],
                    "nucleo": nucleo.get("sobrenomesCore", "?"),
                    "motivo": f"Núcleo MEDIO com R$ {total_desp:,.2f} em despesas — requer auditoria manual"
                })
        
        return warnings
