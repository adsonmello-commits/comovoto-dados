# Como Voto — dados eleitorais

Repositório público de dados organizados para o site [Como Voto](https://www.comovoto.com.br).

## Cobertura inicial

A cobertura de validação abrange os **497 municípios do Rio Grande do Sul**. Os resultados presidenciais de 2026 são separados por município em arquivos JSON Lines compactados:

```
data/2026/RS/
  index.json
  manifest.json
  municipalities/<código-TSE>.jsonl.gz
```

O índice lista os municípios, turnos, seções e caminhos dos arquivos. O manifesto registra a origem, a integridade e a situação de completude da fonte. A importação exige os 497 municípios e o 1º turno. Se o TSE ainda não disponibilizou o 2º turno, essa ausência fica marcada como `pending_tse_update`, sem apresentar a base como completa.

## Atualização e validação

O GitHub Actions executa `scripts/import_tse_rs.py` diariamente e também permite execução manual. A rotina baixa o arquivo oficial do TSE, verifica a integridade do ZIP e publica somente partições compactadas por município. O arquivo bruto fica temporário durante a importação e não é mantido no histórico do Git.

Os registros detalhados permanecem separados dos dados agregados que o site exibe. Antes da integração ao site, os totais por município e seção devem ser conferidos contra os resultados oficiais.

## Fonte e licença

Fonte: [Portal de Dados Abertos do TSE — Resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026), recurso “RS - Votação por seção eleitoral - 2026”.

O TSE indica licença Creative Commons Attribution (CC BY). Este projeto independente não tem vínculo institucional com o TSE. Atribua a fonte ao reutilizar os dados.
