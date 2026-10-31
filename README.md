# Como Voto — dados eleitorais

Repositório público de dados oficiais organizados para o site [Como Voto](https://www.comovoto.com.br).

## Cobertura e uso no site

- `data/2026/presidencia/<UF>/`: votação presidencial por seção, particionada por município para as 27 UFs. É a base nacional usada pelo seletor de estado e município e pelo detalhamento por seção do site.
- `data/2026/<UF>/`: resultados estaduais e proporcionais por seção. No momento, disponíveis para RS, SC e PR.

Cada base estadual contém um índice e um manifesto; os resultados são JSON Lines compactados em gzip e separados por município. Assim, o navegador consulta o índice e baixa apenas o arquivo do município selecionado, em vez de carregar toda a base nacional de uma vez. Os manifestos registram os turnos presentes na publicação do TSE; quando o segundo turno ainda não está na fonte, usam `pending_tse_update`.

## Atualização

O GitHub Actions atualiza diariamente os arquivos oficiais do TSE e também permite execução manual. A rotina presidencial importa o arquivo nacional de votação por seção, organiza os dados pelas 27 UFs e municípios e remove o arquivo bruto temporário ao terminar. A rotina estadual busca RS, SC e PR. Se a fonte não mudar, as partições existentes são preservadas.

## Fonte e licença

Fonte: [Portal de Dados Abertos do TSE — Resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026), incluindo o recurso presidencial e os arquivos estaduais de votação por seção.

O TSE indica licença Creative Commons Attribution (CC BY). Este projeto independente não tem vínculo institucional com o TSE. Atribua a fonte ao reutilizar os dados.
