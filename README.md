# Como Voto — dados eleitorais

Repositório público de dados organizados para o site [Como Voto](https://www.comovoto.com.br).

## Cobertura

O repositório mantém dois conjuntos separados para 2026:

- `data/2026/presidencia/<UF>/`: votação presidencial por seção, particionada por município. Este é o conjunto que alimenta a visão presidencial do site.
- `data/2026/<UF>/`: dados estaduais e proporcionais do respectivo estado, mantidos em separado.

Cada conjunto contém um `index.json`, um `manifest.json` e arquivos JSON Lines compactados por município. A importação presidencial cobre RS (497 municípios), SC (295) e PR (399), validando a contagem municipal e registrando os turnos que o TSE disponibilizou. Se o 2º turno ainda não estiver na fonte presidencial, o manifesto marca `pending_tse_update`.

## Atualização

O GitHub Actions atualiza diariamente os arquivos oficiais do TSE e permite execução manual. A rotina presidencial usa o recurso “Presidente - Votação por seção eleitoral - 2026”, separa os estados e municípios e preserva o arquivo bruto apenas temporariamente durante a importação. Os arquivos publicados são compactados e carregados sob demanda pelo site. Se a fonte não mudar, as partições existentes são preservadas.

## Fonte e licença

Fonte: [Portal de Dados Abertos do TSE — Resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026), incluindo o recurso presidencial e os arquivos estaduais de votação por seção.

O TSE indica licença Creative Commons Attribution (CC BY). Este projeto independente não tem vínculo institucional com o TSE. Atribua a fonte ao reutilizar os dados.
