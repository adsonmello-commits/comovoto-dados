# Como Voto — dados eleitorais

Repositório público de dados organizados para o site [Como Voto](https://www.comovoto.com.br).

## Cobertura

A cobertura municipal inicial do site inclui 34 municípios da Região Metropolitana de Porto Alegre. Este repositório está sendo preparado para publicar o conjunto oficial de votação por seção de **todo o Rio Grande do Sul**, começando pelos resultados presidenciais de 2026.

O arquivo estadual original do TSE será armazenado em:

```
data/source/2026/RS/
  votacao_secao_2026_RS.zip
  manifest.json
```

O ZIP mantém os dados oficiais completos do estado, incluindo todos os municípios e seções disponíveis na fonte. O manifesto registra a origem, a data de obtenção, o tamanho, o SHA-256 e a integridade do arquivo.

## Atualização e validação

A rotina `scripts/import_tse_rs.py` baixa o arquivo no portal/CDN oficial do TSE, verifica a integridade do ZIP e gera o manifesto. O fluxo do GitHub Actions publica o arquivo validado neste repositório. O fluxo pode ser executado novamente quando o TSE atualizar os dados.

Antes da publicação no site, os dados derivados por município devem ser conferidos contra os totais oficiais do TSE. Os dados brutos e os dados derivados devem permanecer identificados separadamente.

## Fonte e licença

Fonte: [Portal de Dados Abertos do TSE — Resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026), recurso “RS - Votação por seção eleitoral - 2026”.

O conjunto está indicado pelo TSE sob licença Creative Commons Attribution (CC BY). Este projeto independente não tem vínculo institucional com o TSE. Atribua a fonte ao reutilizar os dados.

## Uso pelo site

O site deve buscar dados sob demanda e carregar apenas o estado ou município consultado. A publicação do arquivo bruto estadual neste repositório é a etapa inicial; a integração do formato detalhado ao site requer a etapa de transformação e validação descrita acima.
