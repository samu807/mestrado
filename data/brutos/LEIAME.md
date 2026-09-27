# Dados brutos

| Arquivo | Fonte | Observações |
|---|---|---|
| `pld_horario_2025.csv` | CCEE — Dados Abertos, conjunto "PLD horário" | 2025, 4 submercados, R$/MWh |
| `pvgis_itajuba_2023.csv` | PVGIS 5.3 (JRC/UE), "Dados horários", base PVGIS-ERA5 | Itajubá (-22,425; -45,457; 848 m), 1 kWp c-Si, perdas 14%, inclinação 25° e azimute -165° (ótimos), ano 2023, horário UTC |

Os arquivos processados em `data/` são gerados por:

```bash
python scripts/importar_dados.py --pld data/brutos/pld_horario_2025.csv --submercado SE \
    --pv data/brutos/pvgis_itajuba_2023.csv --ano 2025
```

A série PV de 2023 é reposicionada em 2025 (mesmo mês/dia/hora) e convertida para UTC-3.
