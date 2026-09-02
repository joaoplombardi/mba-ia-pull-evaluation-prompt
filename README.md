# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Solução do desafio de Prompt Engineering: fazer **pull** de um prompt de baixa
qualidade do LangSmith Prompt Hub, **refatorá-lo** com técnicas avançadas,
**publicá-lo** de volta no Hub e **avaliá-lo** com 5 métricas customizadas até
que todas fiquem acima de 0.8.

**Resultado final: todas as 5 métricas ≥ 0.8, com média de 0.9057.**

| Métrica | v1 (original) | v2 (otimizado) | Δ |
|---|---|---|---|
| Helpfulness | 0.88 | **0.91** | +0.03 |
| Correctness | 0.84 | **0.89** | +0.05 |
| F1-Score | 0.84 | **0.90** | +0.06 |
| Clarity | 0.91 | **0.94** | +0.03 |
| Precision | 0.85 | **0.89** | +0.04 |
| **Média geral** | **0.8611** | **0.9057** | **+0.0446** |

### Links públicos

Todos acessíveis sem login:

| O quê | Link |
|---|---|
| Prompt otimizado no Hub | https://smith.langchain.com/hub/joaoplombardi/bug_to_user_story_v2 |
| Dataset de avaliação (15 exemplos) | https://smith.langchain.com/public/258e75e3-4004-4b41-acaf-11401c102cc7/d |
| Trace — bug simples | https://smith.langchain.com/public/f2d467a6-d85b-424f-8ef8-81026fb7552f/r |
| Trace — bug médio | https://smith.langchain.com/public/94147aaa-18b6-4be2-a17d-d78a118c142f/r |
| Trace — bug complexo | https://smith.langchain.com/public/1e645a3a-9274-47c2-98e5-024524e2f72b/r |

---

## Sumário

- [Como Executar](#como-executar)
- [Técnicas Aplicadas (Fase 2)](#técnicas-aplicadas-fase-2)
- [Resultados Finais](#resultados-finais)
- [Testes de Validação](#testes-de-validação)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Notas de Implementação](#notas-de-implementação)

---

## Como Executar

### Pré-requisitos

- Python 3.9 ou superior
- Conta no [LangSmith](https://smith.langchain.com/) com API Key
- API Key do [Google AI Studio](https://aistudio.google.com/app/apikey) (Gemini)
  ou da [OpenAI](https://platform.openai.com/api-keys)

### 1. Ambiente virtual e dependências

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

No Windows: `venv\Scripts\activate`

```bash
pip install -r requirements.txt
```

### 2. Configurar credenciais

Copie o template e preencha suas chaves:

```bash
cp .env.example .env
```

Variáveis usadas pelo projeto:

| Variável | Descrição |
|---|---|
| `LANGSMITH_API_KEY` | API Key do LangSmith |
| `LANGSMITH_PROJECT` | Nome do projeto onde os traces são gravados |
| `LANGSMITH_TRACING` | `true` para registrar o tracing detalhado |
| `USERNAME_LANGSMITH_HUB` | Seu handle público no Prompt Hub |
| `GOOGLE_API_KEY` | API Key do Gemini (quando `LLM_PROVIDER=google`) |
| `OPENAI_API_KEY` | API Key da OpenAI (quando `LLM_PROVIDER=openai`) |
| `LLM_PROVIDER` | `google` ou `openai` |
| `LLM_MODEL` | Modelo que **gera** as user stories |
| `EVAL_MODEL` | Modelo que **avalia** as respostas (LLM-as-Judge) |

Configuração usada nesta solução:

```
LLM_PROVIDER=google
LLM_MODEL=gemini-3.1-flash-lite
EVAL_MODEL=gemini-3.1-flash-lite
```

> **Por que não `gemini-2.5-flash`?** O modelo indicado no enunciado foi
> descontinuado para chaves novas — a API responde
> `404: This model models/gemini-2.5-flash is no longer available to new users`.
> Usamos `gemini-3.1-flash-lite`, que está disponível no free tier e mantém o
> mesmo limite de 15 req/min citado no desafio. Basta trocar `LLM_MODEL` e
> `EVAL_MODEL` no `.env` para usar outro provider/modelo.

### 3. Pull do prompt original

```bash
python src/pull_prompts.py
```

Baixa `leonanluppi/bug_to_user_story_v1` do Hub e grava em
`prompts/bug_to_user_story_v1.yml`.

### 4. Push do prompt otimizado

```bash
python src/push_prompts.py
```

Lê `prompts/bug_to_user_story_v2.yml`, valida a estrutura (campos obrigatórios,
ausência de `[TODO]`, presença de `{bug_report}` apenas no user prompt, mínimo de
2 técnicas) e publica como `{seu_username}/bug_to_user_story_v2`, público, com
descrição, tags e um README gerado a partir dos metadados do YAML.

### 5. Avaliação

```bash
python src/evaluate.py
```

Cria o dataset no LangSmith a partir de `datasets/bug_to_user_story.jsonl`, puxa
o prompt v2 do Hub, roda os 15 exemplos e calcula as 5 métricas.

### 6. Testes

```bash
pytest tests/test_prompts.py -v
```

---

## Técnicas Aplicadas (Fase 2)

### O problema do prompt v1

O prompt original tinha cinco defeitos que explicam suas notas baixas:

```yaml
system_prompt: |
  Você é um assistente que ajuda a transformar relatos de bugs de usuários em tarefas para desenvolvedores.
  Analise o relato de bug abaixo e crie uma user story a partir dele.
  Relato de Bug:
  ---
  {bug_report}
  ---
  User Story gerada:
user_prompt: "{bug_report}"
```

1. **`{bug_report}` duplicado** no system e no user prompt — o modelo recebe o
   bug duas vezes e trata parte do contexto como instrução.
2. **Persona genérica** ("um assistente") — sem vocabulário nem critério de
   qualidade definidos.
3. **Nenhuma definição de formato** — não exige "Como um... eu quero... para
   que...", nem critérios de aceitação, nem estrutura de seções.
4. **Zero exemplos** — o modelo adivinha o nível de detalhe esperado.
5. **Nenhuma regra de comportamento** — nada impede preâmbulos, blocos de código
   ou informação inventada.

### Técnicas escolhidas

Foram aplicadas **4 técnicas**, declaradas em `techniques_applied` no YAML.

#### 1. Role Prompting

**Por quê:** a métrica de Clarity e o tom das user stories dependem de vocabulário
e de nível de detalhe consistentes. Uma persona concreta ancora as duas coisas
muito melhor do que adjetivos soltos ("seja profissional").

**Como foi aplicado:**

```
Você é um(a) Product Owner Sênior com 10 anos de experiência em squads ágeis
de produtos digitais (e-commerce, SaaS, ERP, CRM e apps mobile). Você faz a
ponte entre suporte e engenharia: recebe relatos de bug crus — escritos por
usuários, analistas de suporte ou desenvolvedores — e os transforma em User
Stories prontas para entrar no backlog, sem que o time precise reescrevê-las.
```

Os domínios citados (e-commerce, SaaS, ERP, CRM, mobile) são exatamente os do
dataset, e a frase "sem que o time precise reescrevê-las" define o critério de
qualidade implícito.

#### 2. Few-shot Learning (obrigatória)

**Por quê:** foi a técnica de maior impacto. As respostas de referência do
dataset variam radicalmente conforme a complexidade do bug — de 6 linhas para um
bug simples até 5 seções para um bug crítico. Nenhuma instrução em prosa
transmite essa calibragem tão bem quanto ver o resultado pronto.

**Como foi aplicado:** 3 pares entrada/saída completos, um por nível de
complexidade:

| Exemplo | Nível | Bug usado | Ensina |
|---|---|---|---|
| 1 | SIMPLES | filtro de busca por data | história + 5 critérios, nada mais |
| 2 | MÉDIO | upload de foto acima de 5MB | critérios + seções técnicas/contexto |
| 3 | COMPLEXO | importação de planilhas | blocos `=== ... ===`, grupos A/B/C, tasks, métricas |

Os três bugs dos exemplos são **originais** — nenhum deles aparece no
`datasets/bug_to_user_story.jsonl`. Isso evita contaminar a avaliação: o modelo
aprende o formato, não as respostas.

#### 3. Chain of Thought (interno)

**Por quê:** identificar o ator certo é o passo que mais influencia F1 e
Precision. Bugs de webhook ou de permissão de API não têm usuário final — a
referência usa "Como o sistema". Sem raciocínio explícito o modelo inventa um
usuário e perde pontos nas duas métricas.

**Como foi aplicado:** 5 etapas obrigatórias, executadas em silêncio:

```
1. IDENTIFICAR O ATOR ... Se o bug for de infraestrutura, integração ou
   segurança e não houver um usuário final envolvido, o ator é "o sistema".
2. IDENTIFICAR A NECESSIDADE: qual comportamento CORRETO o ator espera?
3. IDENTIFICAR O VALOR: por que isso importa para o ator ou para o negócio?
4. CLASSIFICAR A COMPLEXIDADE: SIMPLES, MÉDIO ou COMPLEXO
5. DERIVAR OS CRITÉRIOS ... Todo dado técnico presente no relato (endpoint,
   código HTTP, tempo, z-index, valor em R$, versão de SO) deve reaparecer
   em algum critério ou seção de contexto.
```

O detalhe decisivo é a instrução **"NUNCA escreva o raciocínio na resposta"**.
CoT visível derruba Clarity e Precision, porque o texto do raciocínio é comparado
com a referência e conta como conteúdo irrelevante.

#### 4. Skeleton of Thought

**Por quê:** as métricas F1 e Precision comparam a resposta com uma referência.
Detalhar demais um bug simples custa Precision; detalhar de menos um bug crítico
custa Recall. Um esqueleto fixo por nível de complexidade resolve os dois lados.

**Como foi aplicado:** a etapa 4 do CoT classifica o bug e cada classe tem um
esqueleto obrigatório:

- **SIMPLES** → história + `Critérios de Aceitação:` com 5 itens. *"NADA além disso."*
- **MÉDIO** → história + 5-6 critérios + 1 a 3 seções complementares escolhidas
  de uma lista fechada (`Critérios Técnicos:`, `Critérios de Prevenção:`,
  `Contexto Técnico:`, `Exemplo de Cálculo:`, ...)
- **COMPLEXO** → blocos `=== USER STORY PRINCIPAL ===`,
  `=== CRITÉRIOS DE ACEITAÇÃO ===` (grupos A/B/C/D, um por problema),
  `=== CRITÉRIOS TÉCNICOS ===`, `=== CONTEXTO DO BUG ===`,
  `=== TASKS TÉCNICAS SUGERIDAS ===` e, quando o relato traz números de impacto,
  `=== MÉTRICAS DE SUCESSO ===`

### Regras explícitas e edge cases

Além das técnicas, o prompt traz um bloco **OBRIGATÓRIO / PROIBIDO** e uma seção
de edge cases. Os itens mais relevantes para as métricas:

| Regra | Métrica protegida |
|---|---|
| Começar direto por "Como um..."; nada de preâmbulo ou "Segue a user story:" | Precision, Clarity |
| Não usar blocos de código, `#` ou `**` | Clarity |
| Não inventar fornecedores, números ou tecnologias; usar `[nome do gateway]` | Precision |
| Não propor troca de tecnologia não solicitada (ex.: REST → GraphQL) | Precision |
| Preservar todo dado técnico do relato nos critérios | F1 (recall) |
| Bug simples recebe só história + 5 critérios | Precision |

Edge cases cobertos: relato vago (gera mesmo assim, não pede mais informação),
múltiplos problemas independentes (uma história, critérios agrupados), bug sem
usuário final ("Como o sistema"), falha de segurança (registra severidade, não
reproduz payload executável), relato que já vem como user story (normaliza) e
relato em outro idioma (responde sempre em pt-BR).

### System vs User Prompt

O defeito central da v1 era `{bug_report}` nos dois lugares. Na v2 a separação é
estrita e validada por teste automatizado:

- **System prompt** — persona, processo de raciocínio, esqueletos, regras,
  edge cases e exemplos. Tudo que é **constante** entre execuções.
- **User prompt** — apenas o relato e a ordem de execução. O único lugar com
  `{bug_report}`.

---

## Resultados Finais

### Comparativo v1 vs v2

Ambas as versões foram avaliadas com o mesmo dataset (15 exemplos), o mesmo
modelo gerador e o mesmo LLM-as-Judge, para que a comparação seja justa.

| Métrica | v1 (original) | v2 (otimizado) | Δ | Status v2 |
|---|---|---|---|---|
| Helpfulness | 0.88 | **0.91** | +0.03 | ✅ |
| Correctness | 0.84 | **0.89** | +0.05 | ✅ |
| F1-Score | 0.84 | **0.90** | +0.06 | ✅ |
| Clarity | 0.91 | **0.94** | +0.03 | ✅ |
| Precision | 0.85 | **0.89** | +0.04 | ✅ |
| **Média geral** | **0.8611** | **0.9057** | **+0.0446** | ✅ |

Além da média, a v2 é bem mais **consistente**: o pior F1 por exemplo sobe de
**0.69** (v1) para **0.79** (v2), e o número de exemplos com F1 abaixo de 0.80
cai de 4 para 1.

> **Observação honesta sobre o baseline.** O enunciado ilustra a v1 com notas na
> faixa de 0.45-0.52. Na prática, avaliada com um modelo atual, a v1 pontuou
> 0.8611 — o modelo compensa boa parte da falta de instrução. O ganho real da v2
> aparece onde a instrução importa: estrutura por complexidade, cobertura dos
> dados técnicos do relato e ausência de conteúdo inventado.

### Saída do CLI

```
==================================================
Prompt: bug_to_user_story_v2
==================================================

Métricas Derivadas:
  - Helpfulness: 0.91 ✓
  - Correctness: 0.89 ✓

Métricas Base:
  - F1-Score: 0.90 ✓
  - Clarity: 0.94 ✓
  - Precision: 0.89 ✓

--------------------------------------------------
📊 MÉDIA GERAL: 0.9057
--------------------------------------------------

✅ STATUS: APROVADO - Todas as métricas >= 0.8
```

Notas por exemplo na execução final:

| # | Complexidade | F1 | Clarity | Precision |
|---|---|---|---|---|
| 1 | simple | 0.92 | 0.95 | 0.97 |
| 2 | simple | 0.97 | 0.95 | 0.93 |
| 3 | simple | 0.92 | 0.95 | 0.93 |
| 4 | simple | 0.79 | 0.95 | 0.93 |
| 5 | simple | 0.85 | 0.95 | 0.83 |
| 6 | medium | 0.90 | 0.95 | 0.93 |
| 7 | medium | 0.97 | 0.95 | 0.93 |
| 8 | medium | 0.92 | 0.95 | 0.93 |
| 9 | medium | 0.92 | 0.95 | 0.83 |
| 10 | medium | 0.87 | 0.95 | 0.90 |
| 11 | medium | 0.87 | 0.90 | 0.83 |
| 12 | medium | 0.85 | 0.90 | 0.83 |
| 13 | complex | 0.95 | 0.95 | 0.93 |
| 14 | complex | 0.85 | 0.95 | 0.93 |
| 15 | complex | 0.95 | 0.85 | 0.66 |

### Histórico de iterações

| Iteração | Mudança | Motivação | Resultado |
|---|---|---|---|
| 1 | Reescrita completa: persona, CoT interno, esqueleto por complexidade, 3 exemplos few-shot, regras OBRIGATÓRIO/PROIBIDO, edge cases; `{bug_report}` só no user prompt | Corrigir os 5 defeitos da v1 | Primeiras amostras com F1/Clarity/Precision em 1.00 |
| 2 | Regra explícita de linha em branco entre a história, cada rótulo de seção e cada bloco de itens | As saídas vinham com seções coladas, divergindo do formato da referência | Formatação alinhada à referência |
| 3 | Push + avaliação completa dos 15 exemplos | Medir o resultado real | **0.9023** — todas as métricas ≥ 0.8 |
| 4 | Diagnóstico dos exemplos mais fracos (12 e 15) lendo o `reasoning` do juiz | Entender onde a nota escapava | Recall penalizado por critérios complementares omitidos; Precision penalizada por sugerir troca de arquitetura não solicitada |
| 5 | Três ajustes cirúrgicos: (a) nível MÉDIO passa a exigir critérios complementares (acessibilidade, prevenção, mensagem de erro); (b) nível COMPLEXO exige granularidade técnica e tasks em fases; (c) proibição explícita de reescrita arquitetural não solicitada | Ganhar recall sem perder precision | **0.9057** — todas as métricas ≥ 0.8 |

### Evidências no LangSmith

**Prompt público (acessível sem login):**

🔗 https://smith.langchain.com/hub/joaoplombardi/bug_to_user_story_v2

- **Identificador no Hub:** `joaoplombardi/bug_to_user_story_v2`
- **Visibilidade:** público
- **Tags:** `bug-analysis`, `user-story`, `product-management`, `few-shot`,
  `chain-of-thought`, `skeleton-of-thought`, `role-prompting`
- **README do prompt:** gerado automaticamente pelo `push_prompts.py` a partir
  das técnicas e do changelog declarados no YAML

**Dataset de avaliação — link público (15 exemplos):**

🔗 https://smith.langchain.com/public/258e75e3-4004-4b41-acaf-11401c102cc7/d

Contém os 15 bugs do desafio (5 simples, 7 médios, 3 complexos) com as
respectivas user stories de referência.

**Tracing detalhado — links públicos de 3 execuções:**

Uma execução por nível de complexidade. Cada link abre a cadeia completa
`ChatPromptTemplate → ChatGoogleGenerativeAI`, mostrando o prompt renderizado
com o bug injetado e a user story gerada.

| Nível | Bug | Trace público |
|---|---|---|
| Simples | #1 — botão de adicionar ao carrinho | https://smith.langchain.com/public/f2d467a6-d85b-424f-8ef8-81026fb7552f/r |
| Médio | #8 — `/api/users/:id` sem validar permissões | https://smith.langchain.com/public/94147aaa-18b6-4be2-a17d-d78a118c142f/r |
| Complexo | #15 — sincronização offline-first | https://smith.langchain.com/public/1e645a3a-9274-47c2-98e5-024524e2f72b/r |

**Dashboard completo** (requer acesso ao workspace):

- **Workspace / organização:** `9e3c8de4-6a3f-4588-baf7-1f6985c934db`
- **Projeto de tracing:** `prompt-optimization-challenge-resolved` — 719 runs
  registrados, sendo 120 cadeias `RunnableSequence` (uma por exemplo avaliado)
  mais as três chamadas de LLM-as-Judge de cada exemplo
- **Dataset de avaliação:** `prompt-optimization-challenge-resolved-eval`

> **Onde ficam as notas.** O `src/evaluate.py` fornecido calcula as 5 métricas em
> Python e as imprime no terminal — ele não grava feedback no LangSmith. Por isso
> o dashboard mostra o tracing detalhado de cada execução, mas as notas em si
> aparecem na saída do CLI (ver os screenshots abaixo).

### Screenshots

As capturas da execução de `python src/evaluate.py` com todas as métricas ≥ 0.8
estão em [`screenshots/`](screenshots/).

---

## Testes de Validação

`tests/test_prompts.py` implementa os 6 testes exigidos:

| Teste | O que valida |
|---|---|
| `test_prompt_has_system_prompt` | `system_prompt` existe, não está vazio e tem mais de 200 caracteres; `user_prompt` contém `{bug_report}` e o `system_prompt` **não** contém (o defeito da v1) |
| `test_prompt_has_role_definition` | O prompt define persona ("Você é ..." / "Você atua como ...") e cita um papel reconhecido |
| `test_prompt_mentions_format` | Exige Markdown, o template "Como um... eu quero... para que...", a seção de Critérios de Aceitação e o padrão Dado/Quando/Então |
| `test_prompt_has_few_shot_examples` | Há ao menos 2 pares `Entrada:` / `Saída:`, em quantidades iguais, e Few-shot está declarada nos metadados |
| `test_prompt_no_todos` | Nenhum `[TODO]`, `FIXME`, `TBD` ou `<preencher>` sobrou em `description`, `system_prompt` ou `user_prompt` |
| `test_minimum_techniques` | `techniques_applied` é uma lista com ao menos 2 itens não vazios; revalida pelo helper oficial `validate_prompt_structure` de `src/utils.py` |

```
$ pytest tests/test_prompts.py -v

tests/test_prompts.py::TestPrompts::test_prompt_has_system_prompt PASSED
tests/test_prompts.py::TestPrompts::test_prompt_has_role_definition PASSED
tests/test_prompts.py::TestPrompts::test_prompt_mentions_format PASSED
tests/test_prompts.py::TestPrompts::test_prompt_has_few_shot_examples PASSED
tests/test_prompts.py::TestPrompts::test_prompt_no_todos PASSED
tests/test_prompts.py::TestPrompts::test_minimum_techniques PASSED

============================== 6 passed ==============================
```

---

## Estrutura do Projeto

```
mba-ia-pull-evaluation-prompt/
├── .env.example                     # Template das variáveis de ambiente
├── requirements.txt                 # Dependências Python
├── README.md                        # Esta documentação
│
├── prompts/
│   ├── bug_to_user_story_v1.yml     # Prompt original (baixado do Hub)
│   └── bug_to_user_story_v2.yml     # Prompt otimizado
│
├── datasets/
│   └── bug_to_user_story.jsonl      # 15 exemplos de bugs (não alterado)
│
├── src/
│   ├── pull_prompts.py              # Pull do LangSmith          [implementado]
│   ├── push_prompts.py              # Push ao LangSmith          [implementado]
│   ├── evaluate.py                  # Avaliação automática       [original]
│   ├── metrics.py                   # 5 métricas                 [original]
│   └── utils.py                     # Funções auxiliares         [original]
│
└── tests/
    └── test_prompts.py              # 6 testes de validação      [implementado]
```

`src/evaluate.py`, `src/metrics.py`, `src/utils.py` e o dataset **não foram
alterados**.

---

## Notas de Implementação

### `src/pull_prompts.py`

- Percorre as mensagens do `ChatPromptTemplate` retornado por `hub.pull()` e
  separa o conteúdo por tipo (`system` / `human`), preservando as variáveis.
- Salva também `source` e `input_variables`, para deixar rastreável de onde o
  prompt veio.
- Os caminhos são resolvidos a partir da raiz do repositório (`REPO_ROOT`), então
  o script funciona a partir de qualquer diretório.

### `src/push_prompts.py`

- Valida o prompt antes de publicar: campos obrigatórios, ausência de `[TODO]`,
  `{bug_report}` presente no user prompt e ausente no system prompt, e no mínimo
  2 técnicas declaradas.
- Descobre o handle do workspace via API (`tenant_handle`) e avisa quando ele
  diverge de `USERNAME_LANGSMITH_HUB`.
- Publica com `hub.push(..., new_repo_is_public=True)` e, como `is_public` só é
  aplicado na criação do repositório, reforça a visibilidade e os metadados com
  `client.update_prompt()` nos re-pushes.
- Gera o README do prompt no Hub a partir das técnicas e do changelog do YAML.

### Limite de requisições do free tier

O free tier do Gemini permite **15 requisições por minuto por modelo**. Uma
avaliação completa faz 60 chamadas (15 gerações + 45 do LLM-as-Judge), então é
normal encontrar `429 ResourceExhausted` no meio da execução. Quando isso
acontece, `src/metrics.py` registra 0.0 naquela métrica e a média cai
artificialmente. Se o resultado vier com algum exemplo zerado, basta rodar
`python src/evaluate.py` novamente com calma — ou usar um provider sem esse
limite (`LLM_PROVIDER=openai`).

### Publicação pública do prompt

Para publicar o prompt como **público** o workspace precisa ter um *handle* no
LangChain Hub — o identificador que vira o prefixo `{seu_username}/`. Ele é
criado uma única vez pela interface do LangSmith, em
[smith.langchain.com/prompts](https://smith.langchain.com/prompts), ao tornar
qualquer prompt público; o SDK não expõe API para criá-lo.

`src/push_prompts.py` lida com os dois cenários:

- **Sem handle:** avisa, publica o prompt como privado no workspace (sem
  prefixo de owner) e explica o que fazer.
- **Com handle:** publica como `{seu_username}/bug_to_user_story_v2`, público.

O script também trata o `409 Nothing to commit` do Hub, que ocorre quando o
conteúdo não mudou desde o último commit. Isso não é falha: nesse caso ele
apenas informa que não há o que versionar e segue sincronizando descrição, tags,
README e visibilidade via `client.update_prompt()`.
