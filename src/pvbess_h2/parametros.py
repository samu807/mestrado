"""Leitura e validação dos parâmetros do caso de estudo (arquivo YAML)."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Horizonte:
    inicio: str = "2025-01-06 00:00"
    dias: int = 7
    dt_h: float = 1.0
    # Condição cíclica dos estoques (SOC do módulo mercantil e tanque de H2): com false,
    # partem de bess.soc_inicial_frac e hidrogenio.tanque_inicial_kg e terminam acima
    # desses valores; com true, o nível inicial é uma variável de decisão e o horizonte
    # termina no nível em que começou.
    nivel_inicial_livre: bool = False


@dataclass
class PV:
    potencia_pico_mw: float = 50.0
    arquivo: str | None = None
    fator_capacidade_pico: float = 0.85
    nebulosidade: float = 0.25


@dataclass
class BESS:
    energia_mwh: float = 120.0
    potencia_carga_mw: float = 30.0
    potencia_descarga_mw: float = 30.0
    eficiencia_carga: float = 0.95
    eficiencia_descarga: float = 0.95
    soc_min_frac: float = 0.10
    soc_max_frac: float = 1.00
    soc_inicial_frac: float = 0.50
    custo_degradacao_rs_mwh: float = 50.0


@dataclass
class Eletrolisador:
    potencia_max_mw: float = 10.0
    carga_min_frac: float = 0.20
    consumo_especifico_kwh_kg: float = 55.0
    custo_variavel_rs_kg: float = 1.5
    custo_partida_rs: float = 0.0          # custo por partida (desgaste da pilha, purga)


@dataclass
class Hidrogenio:
    preco_venda_rs_kg: float = 35.0
    tanque_max_kg: float = 2000.0
    tanque_inicial_kg: float = 0.0
    entrega_min_diaria_kg: float = 0.0
    venda_max_kg_h: float | None = None
    # Contrato de fornecimento: teto diário de venda (demanda do comprador) e multa por
    # kg não entregue abaixo da entrega mínima (None = entrega mínima obrigatória).
    entrega_max_diaria_kg: float | None = None
    penalidade_deficit_rs_kg: float | None = None


@dataclass
class Rede:
    exportacao_max_mw: float = 40.0
    importacao_max_mw: float = 40.0
    permitir_importacao: bool = True
    h2_verde_estrito: bool = True
    custo_adicional_importacao_rs_mwh: float = 250.0


@dataclass
class Mercado:
    arquivo: str | None = None
    pld_min_rs_mwh: float = 58.60
    pld_max_rs_mwh: float = 1500.0
    pld_medio_rs_mwh: float = 180.0
    semente: int = 42
    fator_preco: float = 1.0               # multiplica o PLD lido (ex.: correção pelo IPCA)


@dataclass
class DespachoONS:
    # "fixo": descarga/recarga nas horas indicadas; "pld": descarga no bloco de
    # duracao_h horas de maior PLD fora da janela solar e recarga nas horas de menor
    # PLD dentro de janela_recarga (proxy do despacho de menor custo, art. 4º §14).
    modo: str = "fixo"
    janela_recarga: list[int] = field(default_factory=lambda: list(range(8, 17)))
    arquivo: str | None = None
    horas_descarga: list[int] = field(default_factory=lambda: [18, 19, 20, 21])
    horas_recarga: list[int] = field(default_factory=lambda: [10, 11, 12, 13, 14])
    dias: list[int] | None = None
    # Número de despachos (ciclos completos) por ano. None = todos os dias. Com valor,
    # despacham-se apenas os N dias de cada ano civil com maior PLD no período de
    # descarga (proxy de sistema mais apertado); requer PLD lido de arquivo para o
    # ranqueamento anual (com PLD sintético, o N é rateado no horizonte).
    ciclos_ano: float | None = None


@dataclass
class LRCAP:
    """Regras da Portaria Normativa MME nº 136/2026 (LRCAP de 2026 - Armazenamento)."""
    habilitado: bool = True
    receita_fixa_rs_mw_ano: float = 600000.0
    potencia_min_mw: float = 30.0
    potencia_max_oferta_mw: float | None = None
    potencia_fixa_mw: float | None = None
    duracao_h: float = 4.0
    energia_por_mw_h: float = 4.8
    rte_referencia: float = 0.85
    recarga_max_h: float = 6.0
    ciclos_max_dia: float = 2
    ciclos_max_ano: float = 366
    despacho_ons: DespachoONS = field(default_factory=DespachoONS)


@dataclass
class Cenario:
    """Um ano histórico de PLD e geração FV (cenário do 2º estágio)."""
    nome: str
    ano: int
    pld_arquivo: str
    pv_arquivo: str
    probabilidade: float | None = None     # None = uniforme
    fator_preco: float = 1.0               # correção do PLD para a moeda de referência


@dataclass
class Estocastico:
    alpha: float = 0.8                     # nível do CVaR
    beta: float = 0.0                      # peso do CVaR no objetivo (0 = neutro ao risco)
    dias_bloco: int = 7
    dias_por_cenario: int | None = None    # None = ano completo; menor = rodadas de teste
    cenarios: list = field(default_factory=list)

    def probabilidades(self) -> list[float]:
        n = len(self.cenarios)
        pr = [c.probabilidade for c in self.cenarios]
        if all(x is None for x in pr):
            return [1.0 / n] * n
        assert all(x is not None for x in pr), "informe a probabilidade de todos os cenários ou de nenhum"
        assert abs(sum(pr) - 1) < 1e-6, "probabilidades dos cenários devem somar 1"
        return pr


@dataclass
class Parametros:
    horizonte: Horizonte = field(default_factory=Horizonte)
    pv: PV = field(default_factory=PV)
    bess: BESS = field(default_factory=BESS)
    eletrolisador: Eletrolisador = field(default_factory=Eletrolisador)
    hidrogenio: Hidrogenio = field(default_factory=Hidrogenio)
    rede: Rede = field(default_factory=Rede)
    mercado: Mercado = field(default_factory=Mercado)
    lrcap: LRCAP = field(default_factory=LRCAP)
    estocastico: Estocastico = field(default_factory=Estocastico)
    # Diretório base para resolver caminhos relativos de arquivos de dados.
    base_dir: Path = field(default_factory=Path.cwd)

    def validar(self) -> None:
        b, e = self.bess, self.eletrolisador
        assert self.horizonte.dias >= 1, "horizonte.dias deve ser >= 1"
        assert 0 < b.eficiencia_carga <= 1 and 0 < b.eficiencia_descarga <= 1
        assert 0 <= b.soc_min_frac <= b.soc_inicial_frac <= b.soc_max_frac <= 1, \
            "exige soc_min_frac <= soc_inicial_frac <= soc_max_frac"
        assert 0 <= e.carga_min_frac <= 1
        assert e.consumo_especifico_kwh_kg > 0
        h2 = self.hidrogenio
        assert h2.tanque_inicial_kg <= h2.tanque_max_kg
        assert h2.entrega_max_diaria_kg is None or h2.entrega_max_diaria_kg >= h2.entrega_min_diaria_kg, \
            "hidrogenio.entrega_max_diaria_kg deve ser >= entrega_min_diaria_kg"
        lr, d = self.lrcap, self.lrcap.despacho_ons
        assert all(0 <= h <= 23 for h in d.horas_descarga + d.horas_recarga + d.janela_recarga)
        assert d.modo in ("fixo", "pld"), "lrcap.despacho_ons.modo deve ser 'fixo' ou 'pld'"
        assert d.ciclos_ano is None or 0 <= d.ciclos_ano <= 366, "lrcap.despacho_ons.ciclos_ano em [0, 366]"
        assert d.ciclos_ano is None or (d.dias is None and not d.arquivo), \
            "lrcap.despacho_ons.ciclos_ano não se combina com 'dias' nem com 'arquivo'"
        assert 0 <= self.estocastico.alpha < 1 and self.estocastico.beta >= 0
        if lr.habilitado:
            # Requisitos de habilitação técnica (Portaria MME 136/2026, art. 7º)
            faixa = b.soc_max_frac - b.soc_min_frac
            assert faixa * lr.energia_por_mw_h * b.eficiencia_descarga >= lr.duracao_h - 1e-9, (
                f"lrcap.energia_por_mw_h={lr.energia_por_mw_h} não sustenta {lr.duracao_h} h de "
                f"descarga (art. 7º, IV); mínimo = {lr.duracao_h / (faixa * b.eficiencia_descarga):.3f}")
            assert b.eficiencia_carga * b.eficiencia_descarga >= lr.rte_referencia, \
                "RTE do BESS abaixo da mínima do LRCAP (art. 7º, VI)"
            assert lr.duracao_h / (b.eficiencia_carga * b.eficiencia_descarga) <= lr.recarga_max_h, \
                "recarga completa a potência nominal excede o tempo máximo (art. 7º, VII)"
            if lr.potencia_fixa_mw is not None:
                assert lr.potencia_fixa_mw == 0 or lr.potencia_fixa_mw >= lr.potencia_min_mw, \
                    "lrcap.potencia_fixa_mw deve ser 0 ou >= potencia_min_mw (art. 7º, III)"


def _preencher(cls: type, dados: dict[str, Any] | None):
    """Cria o dataclass `cls` a partir de um dicionário, rejeitando chaves desconhecidas."""
    dados = dados or {}
    nomes = {f.name: f for f in fields(cls)}
    desconhecidas = set(dados) - set(nomes)
    if desconhecidas:
        raise KeyError(f"Chaves desconhecidas em '{cls.__name__}': {sorted(desconhecidas)}")
    kwargs = {}
    for nome, valor in dados.items():
        tipo = nomes[nome].type
        sub = globals().get(tipo) if isinstance(tipo, str) else tipo
        kwargs[nome] = _preencher(sub, valor) if is_dataclass(sub) else valor
    return cls(**kwargs)


def carregar_parametros(caminho: str | Path) -> Parametros:
    caminho = Path(caminho)
    with open(caminho, encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}
    p = _preencher(Parametros, dados)
    p.estocastico.cenarios = [c if isinstance(c, Cenario) else _preencher(Cenario, c)
                              for c in p.estocastico.cenarios]
    p.base_dir = caminho.resolve().parent.parent  # raiz do projeto (config/..)
    p.validar()
    return p
