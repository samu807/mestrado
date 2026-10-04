# Textos da dissertação

**Título atual:** Lance mínimo e custo de oportunidade de baterias no Leilão de Reserva de
Capacidade: o papel da produção de hidrogênio verde em sistemas híbridos fotovoltaicos.

| Arquivo | Conteúdo |
|---|---|
| `cap3_metodologia.md` / `.docx` | Capítulo 3 (Metodologia), versão atual |
| `cap4_resultados.md` / `.docx` | Capítulo 4 (Resultados e Discussão), versão atual |
| `figuras/` | Figuras dos capítulos |
| `versao_lrcap_mcp/` | Versão anterior dos Capítulos 3 e 4, com o título "…arbitragem entre o LRCAP e o MCP" |

Os `.md` são as fontes (Markdown + equações em LaTeX); os `.docx` são gerados com formatação ABNT.

Edite o `.md` e gere o Word novamente:

```bash
pip install pypandoc_binary
python scripts/figuras_metodologia.py
python scripts/gerar_docx.py docs/dissertacao/cap3_metodologia.md --capitulo 3
python scripts/gerar_docx.py docs/dissertacao/cap4_resultados.md --capitulo 4
```

No texto-fonte, cada equação de destaque recebe um rótulo `$$ ... $$ {#eq:nome}` e é
citada como `{eq:nome}`; o script numera (3.1, 3.2, ...) e resolve as referências.
Se o texto for editado diretamente no Word, as alterações não voltam para o `.md`.
