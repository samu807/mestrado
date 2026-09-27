"""Otimização da operação de um sistema híbrido PV-BESS com produção de hidrogênio
verde: arbitragem entre o Leilão de Reserva de Capacidade (LRCAP) e o Mercado de
Curto Prazo (MCP)."""

from .dados import montar_series
from .modelo import construir_modelo, resolver
from .parametros import Parametros, carregar_parametros
from .resultados import grafico_operacao, indicadores, serie_resultados

__all__ = [
    "Parametros", "carregar_parametros", "montar_series", "construir_modelo", "resolver",
    "serie_resultados", "indicadores", "grafico_operacao",
]
