import unicodedata
import re

# V4.1.1: Expanded from 15 to ~50 entries to eliminate false-positive family clusters
COMMON_SURNAMES = {
    # Original 15
    "SILVA", "SOUZA", "SANTOS", "COSTA", "RODRIGUES",
    "DIAS", "PEREIRA", "OLIVEIRA", "MELO", "MACHADO",
    "ALVES", "FERREIRA", "LIMA", "ROCHA", "GOMES",
    # Patronymic suffixes (generate massive clusters)
    "JUNIOR", "FILHO", "NETO", "SEGUNDO", "TERCEIRO",
    # Very common BR surnames
    "NASCIMENTO", "CARVALHO", "ARAUJO", "RIBEIRO", "MARTINS",
    "VIEIRA", "BARROS", "FREITAS", "MORAES", "MOREIRA",
    "MONTEIRO", "MENDES", "NUNES", "BARBOSA", "PINTO",
    "CARDOSO", "TEIXEIRA", "BATISTA", "MIRANDA", "LOPES",
    "CORREIA", "RAMOS", "MEDEIROS", "SOARES", "REIS",
    "ANDRADE", "FONSECA",
    "CUNHA", "AMARAL", "BRITO", "AZEVEDO",
    # Note: CAMPOS not included — key investigative surname for Prefeito SGROTT
}

# V4.1.1: First names commonly used as middle tokens — never treat as surname
FIRST_NAME_TOKENS = {
    "JOSE", "MARIA", "JOAO", "ANA", "PEDRO", "PAULO",
    "CARLOS", "FRANCISCO", "ANTONIO", "LUIZ", "LUIS",
    "EDUARDO", "FERNANDO", "MARCOS", "LUCAS", "GABRIEL",
    "HENRIQUE", "CESAR", "ROBERTO", "DIEGO", "RAFAEL",
    "MIGUEL", "JORGE", "SERGIO", "CLAUDIO", "FLAVIO",
    "MARIO", "JULIO", "MARCIO", "ANDRE",
}

# Combined set for quick lookup
_EXCLUDED_SURNAME_TOKENS = COMMON_SURNAMES | FIRST_NAME_TOKENS

STOP_WORDS = {"DE", "DA", "DO", "DOS", "DAS", "E"}

def normalize_name(name: str) -> str:
    """Removes accents, converts to uppercase and removes extra spaces."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(ascii_text.upper().split())


def get_tokens(name: str) -> list[str]:
    """Returns a list of upper case tokens of length > 2 ignoring stop words."""
    parts = normalize_name(name).split()
    return [p for p in parts if p not in STOP_WORDS and len(p) > 2]


def relevant_surnames(name: str) -> list[str]:
    """Extracts non-common, non-first-name surnames from a full name."""
    parts = normalize_name(name).split()
    tokens = [p for p in parts[1:] if p not in STOP_WORDS and len(p) > 2]
    return [t for t in tokens if t not in _EXCLUDED_SURNAME_TOKENS]


def all_surnames(name: str) -> list[str]:
    """Returns all surname tokens, excluding stop words, common surnames, and first-name tokens."""
    parts = normalize_name(name).split()
    return [p for p in parts[1:] if p not in STOP_WORDS and len(p) > 2 and p not in _EXCLUDED_SURNAME_TOKENS]


def extract_cpf_mid(masked_cpf: str) -> str:
    """Extracts the middle 6 digits from a masked CPF (***.XXX.XXX-**)."""
    if not masked_cpf: return ""
    m = re.search(r"\*{3}\.(\d{3})\.(\d{3})-\*{2}", masked_cpf)
    return m.group(1) + m.group(2) if m else ""


def extract_cpf_mid_full(full_cpf: str) -> str:
    """Extracts the middle 6 digits from a full CPF (XXX.XXX.XXX-XX)."""
    if not full_cpf: return ""
    m = re.match(r"\d{3}\.(\d{3})\.(\d{3})-\d{2}", full_cpf)
    return m.group(1) + m.group(2) if m else ""


def is_cpf(doc: str) -> bool:
    """Checks if a string is formatted as CPF (not CNPJ)."""
    return bool(doc) and "/" not in doc and len(doc) <= 14 and "-" in doc


def parse_salary(val_str: str) -> float:
    """Converts BR salary format string '6.891,78' -> 6891.78"""
    if not val_str: return 0.0
    try:
        return float(val_str.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def parse_value(val) -> float:
    """Converts a US formatted value string/int '15000.00' -> 15000.0"""
    if not val: return 0.0
    try:
        return float(str(val))
    except ValueError:
        return 0.0


def extract_human_name_from_credor(nome: str) -> str:
    """
    Extracts a likely human name from a CNPJ string, e.g:
    '45.102.106 PAULO SAMPAIO' -> 'PAULO SAMPAIO'
    'JOAO DA SILVA 12345678900' -> 'JOAO DA SILVA'
    'MARIA X LTDA' -> 'MARIA X'
    """
    if not nome:
        return ""
    
    nome = normalize_name(nome)
    # Remove leading numeric prefixes like CNPJs or IDs at the start
    nome = re.sub(r'^\d+(\.\d+)*[-\/]?\d*\s*', '', nome)
    # Remove trailing numeric suffixes like CPFs at the end
    nome = re.sub(r'\s*\d+$', '', nome) 
    # Remove common corporate legal entities
    nome = re.sub(r'\b(LTDA|ME|MEI|EIRELI|S\/?A|EI|EPP|SS|LTDA[\s\-]ME)\b', '', nome)
    
    return " ".join(nome.split())

