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

## Cenários do modelo estocástico (2021–2025)

| Arquivo | Fonte | Observações |
|---|---|---|
| `pld_horario_2021.csv` … `pld_horario_2024.csv` | CCEE — Dados Abertos, "PLD horário" | Mesmo formato do arquivo de 2025 (campos entre aspas) |
| `pvgis_sarah3_itajuba_2021_2023.csv` | PVGIS 5.3, base PVGIS-SARAH3 | Itajubá (-22,425; -45,454), 1 kWp c-Si, perdas 14%, inclinação 26° e azimute -147° (ótimos), 2021–2023, UTC |

```bash
for y in 2021 2022 2023 2024; do
  python scripts/importar_dados.py --pld data/brutos/pld_horario_$y.csv --submercado SE --ano $y
done
for y in 2021 2022 2023; do
  python scripts/importar_dados.py --pv data/brutos/pvgis_sarah3_itajuba_2021_2023.csv \
      --pv-ano-origem $y --ano $y --sufixo-pv _sarah3
done
for y in 2024 2025; do   # PVGIS-SARAH3 vai até 2023: perfil de 2023 reposicionado
  python scripts/importar_dados.py --pv data/brutos/pvgis_sarah3_itajuba_2021_2023.csv \
      --pv-ano-origem 2023 --ano $y --sufixo-pv _sarah3
done
```
