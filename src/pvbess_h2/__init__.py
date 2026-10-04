"""Lance mínimo e custo de oportunidade de baterias no Leilão de Reserva de Capacidade:
o papel da produção de hidrogênio verde em sistemas híbridos fotovoltaicos.

Modelo de operação e de contratação de um sistema PV-BESS-H2 no LRCAP."""

from .dados import montar_series
from .modelo import construir_modelo, resolver
from .parametros import Parametros, carregar_parametros
from .resultados import grafico_operacao, indicadores, serie_resultados

__all__ = [
    "Parametros", "carregar_parametros", "montar_series", "construir_modelo", "resolver",
    "serie_resultados", "indicadores", "grafico_operacao",
]
