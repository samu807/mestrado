# Textos da dissertação

| Arquivo | Conteúdo |
|---|---|
| `cap3_metodologia.md` | Fonte do Capítulo 3 (Markdown + equações em LaTeX) |
| `cap3_metodologia.docx` | Versão Word gerada a partir da fonte (formatação ABNT) |
| `figuras/` | Figuras do capítulo, geradas por `scripts/figuras_metodologia.py` |

Edite o `.md` e gere o Word novamente:

```bash
pip install pypandoc_binary
python scripts/figuras_metodologia.py
python scripts/gerar_docx.py docs/dissertacao/cap3_metodologia.md --capitulo 3
```

No texto-fonte, cada equação de destaque recebe um rótulo `$$ ... $$ {#eq:nome}` e é
citada como `{eq:nome}`; o script numera (3.1, 3.2, ...) e resolve as referências.
Se o texto for editado diretamente no Word, as alterações não voltam para o `.md`.
