# Catálogo de Regras e Heurísticas 🔍

Este documento descreve as lógicas de detecção de anomalias aplicadas pelos diversos motores de auditoria.

## 📊 Camadas de Evidência (Tiers)
O sistema não trata todo achado como prova definitiva. Os alertas são classificados para orientar a investigação:

- **T1 (Fato Objetivo)**: Identificação direta em documentos oficiais. Ex: Sócio oculto com CPF confirmado ou empresa inativa recebendo.
- **T2 (Padrão Suspeito)**: Comportamento atípico recorrente. Ex: Fracionamento de despesas ou empresa de prateleira.
- **T3 (Hipótese Relacional)**: Inferência baseada em rede. Ex: Parentesco provável por sobrenome raro em setor comum.

---

## 🛡️ Regras de Auditoria Ativadas

### 1. Societárias (T1 e T2)
- **Sócio Oculto (T1)**: Cruzamento de miolo de CPF entre Servidor e QSA da empresa.
- **Empresa de Prateleira (T2)**: Empresa recebe primeiro empenho com menos de 180 dias de fundação.
- **Irregularidade Cadastral (T1)**: Pagamentos para empresas com situação "Baixada" ou "Inativa".
- **Incompatibilidade de CNAE (T2)**: Empresa de eventos vendendo peças mecânicas para a Secretaria de Saúde.

### 2. Relacionais e Nepotismo (T2 e T3)
- **Nepotismo Onomástico (T3)**: Agrupamento por sobrenomes raros em centros de custo comuns.
- **Hub de Contato (T2)**: Empresas distintas que compartilham o mesmo telefone ou e-mail na Receita Federal.
- **Concentração Setorial (T2)**: Um único fornecedor domina mais de 70% das compras de uma secretaria específica.

### 3. Temporais e Contábeis (T2)
- **Anomalia de Fim de Ano**: Picos de faturamento em dezembro sem justificativa sazonal clara.
- **Sincronicidade de Posse**: Empresa inicia faturamento pesado poucos dias após a posse de um alvo político relacionado.
- **Smurfing / Fracionamento**: Sequência de notas fiscais com valores logo abaixo do limite de dispensa de licitação.

---

## 📈 Lógica de Scoring (Triple Scorer)
O risco global de um alvo é composto por três dimensões:

1.  **Risco Financeiro**: Soma ponderada dos valores envolvidos em alertas T1 e T2.
2.  **Risco Relacional**: Densidade de conexões familiares e societárias suspeitas.
3.  **Peso de Evidência**: Fator redutor que diminui o score caso os matches de identidade sejam ambíguos ou baseados apenas em T3.
