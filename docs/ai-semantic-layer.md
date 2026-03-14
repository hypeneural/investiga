# Camada Semântica de I.A. (OpenRouter) 🧠

Este documento detalha o papel, o funcionamento e a importância estratégica da Inteligência Artificial no **Investiga Tijucas**.

## 1. O que a Camada faz?
Diferente dos motores puramente SQL/Heurísticos, a camada semântica (implementada em `openrouter_client.py` e coordenada por `run_openrouter_nlp.py`) lida com a **incerteza da linguagem natural**. Ela executa duas tarefas principais:

### **Tarefa A: Classificação de Despesa (`classify_expense`)**
Processa o histórico textual de cada pagamento para extrair metadados estruturados:
- **Categorização**: Transforma textos como "compra de materiais para rede elétrica" em categorias exatas (`material`) e subcategorias (`infraestrutura`).
- **Detecção de Genericidade**: Avalia se o texto é propositalmente vago (ex: "serviços prestados conforme contrato"). Históricos muito genéricos sobem o score de risco.
- **Auditoria de Objeto vs CNAE**: Cruza o que a empresa faz (CNAE) com o que ela vendeu. Detecta se uma "gráfica" está vendendo "pavimentação".

### **Tarefa B: Priorização de Casos (`prioritize_audit_case`)**
Analisa um "bundle" de evidências (T1, T2, T3) e gera:
- **Prioridade de Auditoria**: Crítica, Alta, Média ou Baixa.
- **Resumo Narrativo**: Um texto explicativo para o auditor humano, conectando os pontos suspeitos.
- **Checklist**: Passos sugeridos para validar a irregularidade (ex: "verificar se o material foi entregue no local X").

---

## 2. Dados e Informações Geradas
A I.A. gera dados que são persistidos na tabela `expense_semantic_labels`:

| Informação | Significado Investigativo |
| :--- | :--- |
| **grau_genericidade** | Indica tentativa de ocultar o objeto real do gasto. |
| **compatibilidade_cnae_objeto** | Indica se a empresa tem capacidade técnica legal para o fornecimento. |
| **red_flags_semanticas** | Identificação automática de termos sensíveis no histórico. |
| **confianca** | Grau de certeza do modelo na classificação. |
| **justificativa_curta** | Explicação rápida do porquê o modelo tomou a decisão. |

---

## 3. Importância no Processo ( O "Cérebro" do Motor)
A Camada Semântica é vital por três razões:

1.  **Estruturação de Caos**: O "Histórico" de um pagamento é um campo livre e sujo. Sem I.A., é impossível agrupar gastos por natureza real apenas com SQL.
2.  **Ponte de Evidência**: Ela conecta o motor Documental (V6) ao Societário (Enriquecimento). Ela entende se o sócio oculto está operando uma empresa que fornece algo totalmente fora do escopo.
3.  **Auditabilidade e Escala**: Através do `NlpDispatcher`, o sistema processa milhares de notas de forma assíncrona, usando um **Cache SQLite (`nlp_cache.db`)** para nunca gastar tokens duas vezes com a mesma informação, garantindo que a auditoria seja barata e escalável.

## 4. Engenharia de Confiabilidade
O projeto implementa uma camada de engenharia robusta em volta da API:
- **Jitter Backoff**: Se o serviço (OpenRouter) falhar ou der rate-limit, o sistema espera e tenta novamente com intervalos aleatórios.
- **Fallback de Modelos**: Se um modelo falha, o sistema tenta automaticamente um segundo ou terceiro (ex: GPT-4o -> Claude 3 -> Nemotron).
- **JSON Estrito**: Usa schemas forçados para garantir que a I.A. nunca responda texto livre, mas sim dados que o sistema consegue processar.
