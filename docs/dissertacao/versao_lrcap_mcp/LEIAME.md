# Versão anterior: arbitragem entre o LRCAP e o MCP

**Título:** Otimização da Operação de um Sistema Híbrido PV-BESS com Produção de Hidrogênio
Verde: arbitragem entre o Leilão de Reserva de Capacidade (LRCAP) e o Mercado de Curto Prazo (MCP)

Capítulos 3 e 4 como estavam antes da mudança de enquadramento (commit `0801348`). Nesta
versão, o resultado principal é a curva de oferta de um BESS já disponível (quantidade a
contratar e operação), e a viabilidade econômica e o lance mínimo aparecem ao final (Seções 3.8.4 e 4.9).

A versão atual, com o título "Lance mínimo e custo de oportunidade de baterias no Leilão de
Reserva de Capacidade: o papel da produção de hidrogênio verde em sistemas híbridos
fotovoltaicos", está em `docs/dissertacao/cap3_metodologia.*` e `cap4_resultados.*` e trata o
BESS a construir (lance mínimo) como resultado principal.

Os números das duas versões são os mesmos; mudam a organização, a ênfase e a síntese.
Para gerar o .docx a partir do .md desta pasta:

    python scripts/gerar_docx.py docs/dissertacao/versao_lrcap_mcp/cap4_resultados.md --capitulo 4
