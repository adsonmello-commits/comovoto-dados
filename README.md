# Como Voto — dados eleitorais

Repositório público de dados estruturados que alimentam o site [Como Voto](https://www.comovoto.com.br).

## Escopo atual

A base local preparada para publicação contém resultados presidenciais de 2026 para 34 municípios da Região Metropolitana de Porto Alegre (RS), nos dois turnos. O índice municipal fica em `cities.json`; os arquivos detalhados estão organizados pelo código municipal do TSE.

Estrutura planejada:

```
cities.json
data/<codigo-municipal-tse>/
  audit.json
  map-data.json
  movement-audit.json
  movement-data.json.gz
```

Os arquivos resumem e organizam dados públicos eleitorais. Os registros de auditoria preservam referências aos arquivos oficiais do TSE usados na conferência. Consulte cada auditoria e os metadados antes de reutilizar os dados.

## Expansão

O repositório inicia com a cobertura atual do RS. A inclusão de outros municípios e estados deve manter a partição por código municipal, atualizar `cities.json` e registrar a origem e a validação de cada conjunto. O escopo ainda não é nacional.

## Uso pelo site

O site deve consultar este repositório por arquivos sob demanda e carregar somente os dados do município selecionado. Mudanças no caminho ou no formato dos arquivos exigem atualização correspondente no código do site.

## Transparência

Projeto independente, sem vínculo institucional com o TSE. Os dados eleitorais de origem são públicos; este repositório contém arquivos derivados e organizados pelo Como Voto.
