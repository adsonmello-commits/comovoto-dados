# com o voto — dados eleitorais

Repositório público de dados oficiais organizados para o site [com o voto](https://www.comovoto.com.br).

## Cobertura e uso no site

- `data/2024/<UF>/`: votação municipal para prefeito e vereador por seção eleitoral, particionada por município e cargo nas UFs com eleição municipal.\n- `data/2026/presidencia/<UF>/`: votação presidencial por seção, particionada por município para as 27 UFs. É a base nacional usada pela visão presidencial.
- `data/2026/<UF>/`: governador, senador, deputado federal e deputado estadual (ou distrital no DF), particionados por município e cargo. A rotina publica o 2º turno apenas quando o TSE o disponibiliza para aquele cargo e estado.

Cada estado tem um índice e manifesto. Os arquivos de votação são JSON Lines em gzip, organizados em arquivos distintos por município e cargo; o navegador carrega apenas o recorte escolhido. O importador mantém os campos mínimos para localizar a seção, identificar a opção de voto e somar votos, preservando os arquivos oficiais de origem temporariamente para conferência.

## Atualização

O GitHub Actions consulta as bases oficiais de 2024 para prefeito e vereador e, diariamente, os arquivos estaduais de votação por seção para todas as 27 UFs e o arquivo nacional presidencial. Também permite execução manual. Os índices registram cargos e turnos existentes em cada estado. A rotina valida a integridade dos ZIPs, a presença dos municípios e dos cargos esperados, e os hashes dos arquivos de origem.

## Fonte e licença

Fontes: [Portal de Dados Abertos do TSE — Resultados 2024](https://dadosabertos.tse.jus.br/dataset/resultados-2024) e [Resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026), incluindo o arquivo nacional presidencial e os arquivos estaduais de votação por seção, atualizados ao final de cada turno.

O TSE indica licença Creative Commons Attribution (CC BY). Este projeto independente não tem vínculo institucional com o TSE. Atribua a fonte ao reutilizar os dados.
