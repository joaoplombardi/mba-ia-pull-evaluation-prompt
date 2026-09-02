# Screenshots da entrega

Capturas de tela que comprovam o resultado da avaliação.

## O que capturar

Rode a avaliação e capture a saída completa do terminal:

```bash
python src/evaluate.py
```

A execução leva cerca de 15 a 20 minutos (15 exemplos × 4 chamadas ao LLM, com
o free tier limitado a 15 requisições por minuto por modelo).

Salve as capturas nesta pasta:

| Arquivo sugerido | Conteúdo |
|---|---|
| `avaliacao-cli.png` | Bloco final do CLI com as 5 métricas, a média geral e o `✅ STATUS: APROVADO` |
| `avaliacao-exemplos.png` | Lista `[1/15] … [15/15]` com as notas por exemplo |
| `langsmith-dataset.png` | Dataset `prompt-optimization-challenge-resolved-eval` com os 15 exemplos |
| `langsmith-trace.png` | Tracing detalhado de uma execução, com o prompt renderizado e a resposta |
| `langsmith-prompt.png` | O prompt `joaoplombardi/bug_to_user_story_v2` publicado e público no Hub |

Se aparecer `429 ResourceExhausted` durante a execução, a métrica daquele exemplo
vira 0.0 e derruba a média — nesse caso, rode novamente antes de capturar.

## Links públicos (não precisam de screenshot)

Estes já estão acessíveis sem login e estão referenciados no README principal:

- Prompt: https://smith.langchain.com/hub/joaoplombardi/bug_to_user_story_v2
- Dataset: https://smith.langchain.com/public/258e75e3-4004-4b41-acaf-11401c102cc7/d
- Trace simples: https://smith.langchain.com/public/f2d467a6-d85b-424f-8ef8-81026fb7552f/r
- Trace médio: https://smith.langchain.com/public/94147aaa-18b6-4be2-a17d-d78a118c142f/r
- Trace complexo: https://smith.langchain.com/public/1e645a3a-9274-47c2-98e5-024524e2f72b/r
