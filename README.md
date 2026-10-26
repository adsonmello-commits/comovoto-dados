# Como Voto — dados eleitorais

Repositório público de dados organizados para o site [Como Voto](https://www.comovoto.com.br).

## Cobertura inicial

A cobertura inicial reúne resultados presidenciais de 2026 dos estados **Rio Grande do Sul (RS), Santa Catarina (SC) e Paraná (PR)**. Os registros de votação por seção ficam particionados por município:

```
data/2026/<UF>/
  index.json
  manifest.json
  municipalities/<código-TSE>.jsonl.gz
```

Cada índice lista os municípios, os turnos disponíveis, a quantidade de seções e os caminhos dos arquivos. Cada manifesto identifica a origem, a integridade e a situação de completude. A importação verifica a cobertura esperada de municípios: RS (497), SC (295) e PR (399). Se o TSE ainda não disponibilizou o 2º turno, a situação fica marcada como `pending_tse_update`.

## Atualização e validação

O GitHub Actions executa `scripts/import_tse_state.py` diariamente e permite execução manual. A rotina baixa os arquivos estaduais oficiais do TSE, valida o ZIP e publica partições compactadas por município. O arquivo bruto fica temporário durante a importação e não é mantido no histórico do Git. Se a fonte não mudar, os arquivos existentes são preservados.

Os registros detalhados permanecem separados dos dados agregados que o site exibe. Antes da integração ao site, os totais por município e seção devem ser conferidos contra os resultados oficiais.

## Fonte e licença

Fonte: [Portal de Dados Abertos do TSE — Resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026), recursos estaduais “Votação por seção eleitoral - 2026”.

O TSE indica licença Creative Commons Attribution (CC BY). Este projeto independente não tem vínculo institucional com o TSE. Atribua a fonte ao reutilizar os dados.
