# Como Voto — dados eleitorais

Repositório público de dados organizados para o site [Como Voto](https://www.comovoto.com.br).

## Cobertura inicial

A etapa de validação publica os resultados presidenciais de 2026 do **Rio Grande do Sul inteiro**, separados por município. Cada município recebe um arquivo JSON Lines compactado com os registros originais da votação por seção:

```
data/2026/RS/
  index.json
  manifest.json
  municipalities/<código-TSE>.jsonl.gz
```

O índice lista os municípios, turnos, seções e caminhos dos arquivos. O manifesto informa a origem e a verificação do arquivo oficial utilizado na importação. A rotina rejeita a publicação se não encontrar os 497 municípios ou dados dos dois turnos.

## Atualização e validação

O GitHub Actions executa `scripts/import_tse_rs.py`, baixa o arquivo oficial do TSE, verifica a integridade do ZIP e gera os arquivos particionados. O ZIP bruto fica temporário durante a importação; ele não é mantido no histórico do Git. O fluxo pode ser executado novamente quando o TSE atualizar os dados.

Antes de integrar os arquivos ao site, os totais agregados por município e seção devem ser conferidos contra os resultados oficiais. Os registros brutos por seção e quaisquer dados derivados devem permanecer identificados separadamente.

## Fonte e licença

Fonte: [Portal de Dados Abertos do TSE — Resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026), recurso “RS - Votação por seção eleitoral - 2026”.

O TSE indica licença Creative Commons Attribution (CC BY). Este projeto independente não tem vínculo institucional com o TSE. Atribua a fonte ao reutilizar os dados.
