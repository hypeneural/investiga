import re
from datetime import datetime, date
from typing import Optional, Any

def normalize_doc(doc: str) -> str:
    """Remove pontuação e deixa apenas dígitos."""
    if not doc:
        return ""
    return ''.join(ch for ch in str(doc) if ch.isdigit())

def doc_type(doc_num: str) -> str:
    """Identifica se a string de dígitos é CPF, CNPJ ou desconhecido."""
    clean = normalize_doc(doc_num)
    if len(clean) == 11:
        return "CPF"
    if len(clean) == 14:
        return "CNPJ"
    return "UNKNOWN"

def cnpj_root(doc_num: str) -> Optional[str]:
    """Retorna os primeiros 8 dígitos se for um CNPJ."""
    clean = normalize_doc(doc_num)
    if len(clean) == 14:
        return clean[:8]
    return None

def parse_date(date_str: str) -> Optional[date]:
    """Tenta converter strings de data conhecidas (DD/MM/YYYY ou YYYY-MM-DD) para date."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    
    # Formato DD/MM/YYYY
    if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            return None
            
    # Formato YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        try:
            return datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
            
    return None

def parse_float(val: Any) -> float:
    """Converte valor string brasileiro/americano para float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    if not val_str:
        return 0.0
        
    # Se houver os dois, é formato brasileiro ex: 1.234,56
    if '.' in val_str and ',' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    # Se só houver vírgula, e estiver nas últimas 3 posições ex: 1234,56
    elif ',' in val_str and len(val_str) - val_str.rfind(',') <= 3:
        val_str = val_str.replace(',', '.')
        
    try:
        return float(val_str)
    except ValueError:
        return 0.0
