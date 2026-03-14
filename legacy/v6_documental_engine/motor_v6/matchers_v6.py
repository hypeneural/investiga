from typing import List, Optional
from schemas_v6 import PaymentEvent, LiquidationDocument, CompanyProfile
from normalizers_v6 import normalize_doc

def match_payment_to_document(payment: PaymentEvent, documents: List[LiquidationDocument]) -> List[dict]:
    """
    Liga o pagamento macro da listagem aos documentos liquidados (NFs) do spider.
    Nível Exato: liquidacao_sequencia + liquidacao_tipo + ano_liquidacao + loa_ano (O core do IPM).
    """
    matches = []
    
    for doc in documents:
        # 1. Tentar Match Forte: Atributos estruturais do portal
        strong_match = (
            payment.empenho_ano == doc.loa_ano
            and payment.liquidacao_sequencia == doc.liquidacao_sequencia
            and payment.liquidacao_tipo == doc.liquidacao_tipo
            and payment.liquidacao_ano == doc.loa_ano
        )
        
        if strong_match:
            matches.append({
                "match_strength": "EXATO",
                "matched_on": ["liquidacao_sequencia", "liquidacao_tipo", "ano_liquidacao", "loa_ano"],
                "confidence": 1.0,
                "document": doc
            })
            continue
            
        # 2. Match Alternativo (Fallback via Documento vs Valores Monetários ou Datas)
        # Mais arriscado para V6, mas útil em bases muito fragmentadas.
        if payment.credor_documento_num and doc.credor_documento_num:
             if normalize_doc(payment.credor_documento_num) == normalize_doc(doc.credor_documento_num):
                 # Avaliando se bate pelo menos no empenho ou data
                 if payment.data_liquidacao == doc.data_documento or payment.valor_pago == doc.valor_documento:
                     matches.append({
                        "match_strength": "FORTE",
                        "matched_on": ["cpfCnpj", "data_ou_valor"],
                        "confidence": 0.85,
                        "document": doc
                     })
                     
    return matches

def match_document_to_company(doc: LiquidationDocument, companies: List[CompanyProfile]) -> Optional[CompanyProfile]:
    """
    Encontra o perfil da receita referente à nota fiscal emitida.
    Match 100% exato e determinístico pelo CNPJ.
    """
    nf_doc = normalize_doc(doc.credor_documento_num)
    if not nf_doc or len(nf_doc) != 14:
        return None
        
    for company in companies:
        if normalize_doc(company.cnpj) == nf_doc:
            return company
            
    return None
