# Resultados da avaliação da busca

48 perguntas escritas à mão: 42 respondidas pelas leis e 6 fora do escopo (devem ser recusadas).

| modelo | modo | acerto@1 | acerto@3 | acerto@5 | MRR | decisão responder/recusar | tempo/pergunta |
|---|---|---|---|---|---|---|---|
| — | palavras | 0.36 | 0.64 | 0.81 | 0.53 | 42/48 (limiar 0.17) | 28 ms |
| paraphrase-multilingual-MiniLM-L12-v2 | vetorial | 0.36 | 0.55 | 0.71 | 0.48 | 43/48 (limiar 0.43) | 5 ms |
| paraphrase-multilingual-MiniLM-L12-v2 | hibrida | 0.62 | 0.88 | 0.93 | 0.75 | 42/48 (limiar 0.32) | 7 ms |
| paraphrase-multilingual-mpnet-base-v2 | vetorial | 0.45 | 0.69 | 0.74 | 0.57 | 45/48 (limiar 0.47) | 20 ms |
| paraphrase-multilingual-mpnet-base-v2 | hibrida | 0.57 | 0.83 | 0.88 | 0.69 | 45/48 (limiar 0.47) | 23 ms |
| multilingual-e5-large | vetorial | 0.76 | 0.93 | 0.98 | 0.85 | 46/48 (limiar 0.83) | 100 ms |
| multilingual-e5-large | hibrida | 0.76 | 0.90 | 0.95 | 0.84 | 46/48 (limiar 0.82) | 105 ms |

## Onde a busca híbrida errou o 1º lugar

**paraphrase-multilingual-MiniLM-L12-v2** (16 perguntas)

- 3. Posso ficar mais de dois anos estagiando na mesma empresa? → veio [('estagio', '17'), ('estagio', '11'), ('estagio', '15')]
- 6. Estágio gera vínculo de emprego com a empresa? → veio [('estagio', '5'), ('estagio', '17'), ('estagio', '15')]
- 10. A empresa precisa fazer seguro contra acidentes para o estagiário? → veio [('cdc', '101'), ('lgpd', '46'), ('estagio', '14')]
- 13. Quantos estagiários um mesmo supervisor pode acompanhar? → veio [('estagio', '17'), ('estagio', '9'), ('estagio', '15')]
- 16. Em que casos uma empresa pode usar meus dados sem eu autorizar? → veio [('lgpd', '18'), ('lgpd', '7'), ('lgpd', '4')]
- 18. Quais direitos eu tenho sobre os meus dados pessoais? → veio [('lgpd', '7'), ('lgpd', '18'), ('lgpd', '9')]
- 19. Qual o valor máximo da multa para quem descumpre a LGPD? → veio [('lgpd', '54'), ('cdc', '57'), ('lgpd', '52')]
- 21. A empresa tem que avisar quando acontece um vazamento de dados? → veio [('lgpd', '18'), ('lgpd', '55-J'), ('lgpd', '19')]
- 26. Quando a empresa deve parar de usar os meus dados? → veio [('lgpd', '18'), ('lgpd', '16'), ('lgpd', '12')]
- 28. Meus dados podem ser enviados para empresas em outro país? → veio [('lgpd', '26'), ('lgpd', '55-J'), ('lgpd', '34')]
- 31. Em quanto tempo a loja tem que consertar um produto com defeito? → veio [('cdc', '26'), ('cdc', '12'), ('cdc', '58')]
- 37. Uma cláusula abusiva no contrato vale? → veio [('cdc', '54'), ('cdc', '51'), ('cdc', '53')]
- 39. A empresa pode me constranger ou ameaçar para cobrar uma dívida? → veio [('cdc', '104-A'), ('cdc', '42'), ('cdc', '71')]
- 40. Por quanto tempo meu nome pode ficar sujo no cadastro de inadimplentes? → veio [('cdc', '28'), ('cdc', '43'), ('cdc', '64')]
- 41. Quem a lei considera consumidor? → veio [('cdc', '43'), ('cdc', '5'), ('cdc', '54-B')]
- 42. Qual o prazo para pedir indenização por um acidente causado por produto defeituoso? → veio [('cdc', '58'), ('cdc', '100'), ('cdc', '27')]

**paraphrase-multilingual-mpnet-base-v2** (18 perguntas)

- 3. Posso ficar mais de dois anos estagiando na mesma empresa? → veio [('estagio', '17'), ('estagio', '3'), ('estagio', '11')]
- 10. A empresa precisa fazer seguro contra acidentes para o estagiário? → veio [('cdc', '101'), ('estagio', '14'), ('estagio', '12')]
- 13. Quantos estagiários um mesmo supervisor pode acompanhar? → veio [('estagio', '17'), ('estagio', '9'), ('estagio', '11')]
- 16. Em que casos uma empresa pode usar meus dados sem eu autorizar? → veio [('lgpd', '18'), ('lgpd', '14'), ('lgpd', '19')]
- 19. Qual o valor máximo da multa para quem descumpre a LGPD? → veio [('lgpd', '54'), ('cdc', '57'), ('cdc', '77')]
- 20. O que faz o encarregado de dados, o DPO? → veio [('lgpd', '3'), ('lgpd', '5'), ('lgpd', '37')]
- 21. A empresa tem que avisar quando acontece um vazamento de dados? → veio [('lgpd', '18'), ('lgpd', '26'), ('lgpd', '55-J')]
- 23. A LGPD se aplica a dados usados só em reportagens jornalísticas? → veio [('lgpd', '3'), ('lgpd', '4'), ('lgpd', '43')]
- 25. Quais são os princípios da LGPD, como finalidade e necessidade? → veio [('lgpd', '1'), ('lgpd', '15'), ('lgpd', '6')]
- 26. Quando a empresa deve parar de usar os meus dados? → veio [('lgpd', '18'), ('cdc', '43'), ('lgpd', '16')]
- 28. Meus dados podem ser enviados para empresas em outro país? → veio [('lgpd', '5'), ('lgpd', '26'), ('lgpd', '34')]
- 31. Em quanto tempo a loja tem que consertar um produto com defeito? → veio [('cdc', '26'), ('cdc', '18'), ('cdc', '12')]
- 34. A loja pode me obrigar a comprar um produto para levar outro (venda casada)? → veio [('cdc', '18'), ('cdc', '54-F'), ('cdc', '39')]
- 35. Quais são os direitos básicos do consumidor? → veio [('cdc', '4'), ('cdc', '5'), ('cdc', '7')]
- 37. Uma cláusula abusiva no contrato vale? → veio [('cdc', '53'), ('cdc', '51'), ('cdc', '54')]
- 39. A empresa pode me constranger ou ameaçar para cobrar uma dívida? → veio [('cdc', '104-A'), ('cdc', '42'), ('lgpd', '52')]
- 41. Quem a lei considera consumidor? → veio [('cdc', '5'), ('cdc', '106'), ('cdc', '40')]
- 42. Qual o prazo para pedir indenização por um acidente causado por produto defeituoso? → veio [('cdc', '26'), ('cdc', '12'), ('cdc', '27')]

**multilingual-e5-large** (10 perguntas)

- 3. Posso ficar mais de dois anos estagiando na mesma empresa? → veio [('estagio', '17'), ('estagio', '11'), ('estagio', '15')]
- 10. A empresa precisa fazer seguro contra acidentes para o estagiário? → veio [('estagio', '5'), ('estagio', '9'), ('estagio', '12')]
- 19. Qual o valor máximo da multa para quem descumpre a LGPD? → veio [('lgpd', '54'), ('lgpd', '52'), ('lgpd', '53')]
- 21. A empresa tem que avisar quando acontece um vazamento de dados? → veio [('lgpd', '26'), ('lgpd', '50'), ('lgpd', '18')]
- 26. Quando a empresa deve parar de usar os meus dados? → veio [('lgpd', '26'), ('lgpd', '16'), ('lgpd', '18')]
- 28. Meus dados podem ser enviados para empresas em outro país? → veio [('lgpd', '26'), ('lgpd', '11'), ('lgpd', '34')]
- 31. Em quanto tempo a loja tem que consertar um produto com defeito? → veio [('cdc', '12'), ('cdc', '26'), ('cdc', '18')]
- 34. A loja pode me obrigar a comprar um produto para levar outro (venda casada)? → veio [('cdc', '18'), ('cdc', '39'), ('cdc', '54-F')]
- 41. Quem a lei considera consumidor? → veio [('cdc', '4'), ('cdc', '43'), ('cdc', '5')]
- 42. Qual o prazo para pedir indenização por um acidente causado por produto defeituoso? → veio [('cdc', '12'), ('cdc', '18'), ('cdc', '26')]
