import os
import json
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime

# Path for the database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "company_cache.sqlite")

def _get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the SQLite database tables if they do not exist."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Table for company profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_profiles (
            cnpj TEXT PRIMARY KEY,
            razao_social TEXT,
            nome_fantasia TEXT,
            data_inicio_atividade TEXT,
            descricao_situacao_cadastral TEXT,
            cnae_fiscal INTEGER,
            cnae_fiscal_descricao TEXT,
            codigo_natureza_juridica INTEGER,
            natureza_juridica TEXT,
            porte TEXT,
            uf TEXT,
            municipio TEXT,
            capital_social REAL,
            payload TEXT,
            updated_at TEXT
        )
    """)
    
    # Table for QSA members
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_qsa_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT,
            nome_socio TEXT,
            cnpj_cpf_do_socio TEXT,
            qualificacao_socio TEXT,
            data_entrada_sociedade TEXT,
            FOREIGN KEY(cnpj) REFERENCES company_profiles(cnpj)
        )
    """)
    
    # Table for secondary CNAEs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_cnaes_secundarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT,
            codigo INTEGER,
            descricao TEXT,
            FOREIGN KEY(cnpj) REFERENCES company_profiles(cnpj)
        )
    """)
    
    # Create indexes for faster lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qsa_cnpj ON company_qsa_members(cnpj)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cnae_cnpj ON company_cnaes_secundarios(cnpj)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qsa_socio_cpf ON company_qsa_members(cnpj_cpf_do_socio)")
    
    conn.commit()
    conn.close()

def save_company(payload: dict) -> None:
    """Saves a company full payload into the repository."""
    if not payload or "cnpj" not in payload:
        return
        
    cnpj = payload["cnpj"]
    now = datetime.now().isoformat()
    
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        # Save profile
        cursor.execute("""
            INSERT OR REPLACE INTO company_profiles (
                cnpj, razao_social, nome_fantasia, data_inicio_atividade,
                descricao_situacao_cadastral, cnae_fiscal, cnae_fiscal_descricao,
                codigo_natureza_juridica, natureza_juridica, porte, uf, municipio, 
                capital_social, payload, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cnpj,
            payload.get("razao_social"),
            payload.get("nome_fantasia"),
            payload.get("data_inicio_atividade"),
            payload.get("descricao_situacao_cadastral"),
            payload.get("cnae_fiscal"),
            payload.get("cnae_fiscal_descricao"),
            payload.get("codigo_natureza_juridica"),
            payload.get("natureza_juridica"),
            payload.get("porte"),
            payload.get("uf"),
            payload.get("municipio"),
            payload.get("capital_social"),
            json.dumps(payload),
            now
        ))
        
        # Save QSA
        # First remove old QSA for this CNPJ
        cursor.execute("DELETE FROM company_qsa_members WHERE cnpj = ?", (cnpj,))
        
        qsa = payload.get("qsa", [])
        if qsa:
            qsa_values = [
                (
                    cnpj,
                    s.get("nome_socio", ""),
                    s.get("cnpj_cpf_do_socio", ""),
                    s.get("qualificacao_socio", ""),
                    s.get("data_entrada_sociedade", "")
                )
                for s in qsa
            ]
            cursor.executemany("""
                INSERT INTO company_qsa_members (
                    cnpj, nome_socio, cnpj_cpf_do_socio, 
                    qualificacao_socio, data_entrada_sociedade
                ) VALUES (?, ?, ?, ?, ?)
            """, qsa_values)
            
        # Save Secondary CNAEs
        cursor.execute("DELETE FROM company_cnaes_secundarios WHERE cnpj = ?", (cnpj,))
        cnaes = payload.get("cnaes_secundarios", [])
        if cnaes:
            cnae_values = [
                (cnpj, c.get("codigo"), c.get("descricao", ""))
                for c in cnaes
            ]
            cursor.executemany("""
                INSERT INTO company_cnaes_secundarios (cnpj, codigo, descricao)
                VALUES (?, ?, ?)
            """, cnae_values)
            
        conn.commit()
    except Exception as e:
        print(f"Error saving company {cnpj} to DB: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_company(cnpj: str) -> Optional[dict]:
    """Retrieves a complete company payload from cache if it exists."""
    # Clean CNPJ
    cnpj = "".join(filter(str.isdigit, cnpj))
    
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT payload FROM company_profiles WHERE cnpj = ?", (cnpj,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row["payload"])
    return None

def get_companies_by_socio(cpf_mascarado: str) -> List[dict]:
    """Retrieves all companies associated with a specific masked CPF in the QSA."""
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.payload 
        FROM company_profiles p
        JOIN company_qsa_members q ON p.cnpj = q.cnpj
        WHERE q.cnpj_cpf_do_socio = ?
    """, (cpf_mascarado,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [json.loads(row["payload"]) for row in rows]

# Initialize DB on import
init_db()
