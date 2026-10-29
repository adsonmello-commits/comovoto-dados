# Urnas no tempo — Eleições 2026

Base estruturada independente do estudo de votos registrados depois das 17h no segundo turno de 2026. Os valores foram transcritos dos três relatórios por UF publicados pelo Tribunal Superior Eleitoral (TSE); não foram copiados da página de referência.

## Fontes oficiais

- [Total de votos após 17h](https://www.tse.jus.br/comunicacao/noticias/arquivos/total-de-votos-apos-17h)
- [Votos computados após 17h10](https://www.tse.jus.br/comunicacao/noticias/arquivos/votos-computados-apos-17h10)
- [Votos computados após 19h](https://www.tse.jus.br/comunicacao/noticias/arquivos/votos-computados-apos-19h)
- [Nota metodológica do TSE](https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleicoes-2026-mais-de-34-mil-votos-foram-registrados-apos-as-17h-no-2o-turno)

## Estrutura

O arquivo `votos-pos-17h-2026.json` contém totais nacionais e uma linha por UF. Cada recorte (`after17`, `after17_10`, `after19`) informa:

- `sections_closed`: seções no critério de encerramento do relatório;
- `votes_17_18`, `votes_18_19`, `votes_after_19`: votos registrados por faixa horária;
- `total_votes`: soma das três faixas.

## Critérios e limites

- Cobertura: 27 UFs; os relatórios não incluem Exterior.
- Horários de Brasília.
- O recorte `after17` considera seções com encerramento registrado depois das 17h.
- O recorte `after17_10` considera seções encerradas depois das 17h10.
- O recorte `after19` considera seções encerradas depois das 19h; as faixas de votos contam os registros pós-17h nessas mesmas seções.
- Os totais nacionais foram conferidos com o levantamento narrativo do TSE: 34.393 votos depois das 17h, 8.673 no recorte das seções encerradas após 17h10 e 4.773 nas seções encerradas após 19h.
- Estes dados não informam a candidatura escolhida por cada eleitor. Não se deve inferir preferência eleitoral pelo horário nem classificar encerramentos posteriores como irregularidade por si sós.
- O TSE esclarece que concluir os procedimentos de encerramento e emitir o boletim alguns minutos após as 17h pode ocorrer na rotina eleitoral.

Atualizado em 29/10/2026. Reutilização dos dados oficiais conforme os termos indicados pelo TSE. Projeto independente, sem vínculo institucional com o Tribunal.
