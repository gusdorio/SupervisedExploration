# Presentation

The current project is intended to make an analysis from basic baskets from the region of Campinas - São Paulo (Brasil), with the final purpose of applying a qualified supervised model which could find usefull insights based on the initial statements.

## Methodology

For the project, we supposed to divide tasks across some distict actions, in order to comes with a meaningfuly implementation;

1. We will make an initial and simple statistical analysis over the dataset available (data/);
2. Followed by the insights, we will move with the definition of possible questions to answer;
3. With the questions stated we will follow to a hands-on implementation of supervised algorithms which could appears to be reliable to the answers expected.

# QUESTÕES

## QUESTÃO 1: Previsão de Preços Futuros por Categoria
É possível criar um modelo de machine learning para prever, com uma margem de erro percentual média (MAPE) inferior a 10%, o Preço médio por Kilo/Unidade (PPK) de uma categoria de produto (ex: "Classe_Carnes Vermelhas") para as próximas 4 semanas?

## OBJETIVO
Avaliar a previsibilidade dos preços de uma categoria essencial da cesta básica, utilizando tanto modelos estatísticos clássicos quanto modelos de aprendizado supervisionado, e comparar sua performance.

## MOTIVAÇÃO
Esta previsão tem aplicação direta para consumidores e pequenos varejistas. Um modelo acurado permitiria o planejamento de compras, antecipando períodos de alta e otimizando o orçamento doméstico ou a gestão de estoque.

## MÉTODO
### Manipulação dos Dados
Filtrar o dataset para a classe de interesse (ex: Classe_Carnes Vermelhas == True).
Como as coletas são diárias, agregar os dados para uma frequência mais estável (ex: semanal), calculando o PPK médio por semana. Isso suaviza ruídos diários e captura a tendência.
Analisar a série temporal agregada (verificar estacionaridade com teste ADF, decompor em tendência, sazonalidade e resíduo).

## ALGORITMOS E ABORDAGEM
### Abordagem 1 (Linha de Base Estatística)
Utilizar um modelo SARIMA (Sazonal AutoRegressivo Integrado de Médias Móveis), que é uma ferramenta clássica e robusta para séries temporais sazonais.

### Abordagem 2 (Aprendizado Supervisionado - Extensão)
Transformar a série temporal em um problema de aprendizado supervisionado. Criar features de lag (ex: PPK das últimas 4 semanas) e features de janela deslizante (ex: média móvel do último mês). Treinar modelo Random Forest Regressor para prever o PPK da próxima semana.

### Avaliação (Rigor)
Dividir os dados temporalmente: Usar os primeiros 80% dos dados para treino e os 20% finais para teste (nunca embaralhar séries temporais).
Para os modelos supervisionados, usar TimeSeriesSplit (validação cruzada específica para séries temporais) para encontrar os melhores hiperparâmetros.

### Métricas de Avaliação
MAPE (Erro Percentual Absoluto Médio), para que a conclusão seja diretamente comparável à questão, e RMSE (Raiz do Erro Quadrático Médio) para avaliar a magnitude do erro na unidade de preço.

### Conclusão (Discussão Esperada):
Analisar se o modelo (SARIMA ou XGBoost) atingiu a meta de MAPE < 10% no conjunto de teste.
Discutir qual abordagem teve a melhor performance e por quê. O modelo supervisionado conseguiu capturar relações não-lineares que o SARIMA perdeu?
O objetivo de prever os preços com antecedência foi atingido de forma prática?

# QUESTÃO 2: Análise de Liderança de Preço entre Mercados
É possível identificar uma dinâmica de "liderança de preço" entre os estabelecimentos? Ou seja, o histórico de preços de um produto no Estabelecimento "A" ajuda a prever (tem causalidade Granger) o preço futuro do mesmo produto no Estabelecimento "B"?

## OBJETIVO
Entender a dinâmica de concorrência e a velocidade de repasse de preços entre diferentes mercados, aplicando técnicas de análise de séries temporais múltiplas.

## MOTIVAÇÃO
Se um mercado "líder" for identificado, concorrentes podem usar essa informação para antecipar reajustes. Para o consumidor, identifica qual mercado tende a "puxar" as altas de preço na região, permitindo uma compra mais estratégica.

## MÉTODO
Selecionar um produto específico (ex: Produto ID '0') que esteja presente em múltiplos estabelecimentos (ex: '12' e '23').
Criar duas (ou mais) séries temporais distintas, uma para o PPK do produto no Estabelecimento 'A' e outra para o Estabelecimento 'B', alinhadas pela Data_Coleta (agregadas por semana, por exemplo).
Garantir que as séries sejam estacionárias (aplicar diferenciação se necessário) para a análise estatística.

## ALGORITMOS E ABORDAGENS

### Abordagem 1 (Análise Estatística):
Calcular a Correlação Cruzada (Cross-Correlation) entre as duas séries para identificar visualmente se uma série lidera a outra (e por quantos lags).
Aplicar o Teste de Causalidade de Granger para verificar estatisticamente se os valores passados da série A são preditores significativos para os valores futuros da série B (justificativa metodológica rigorosa).

### Abordagem 2 (Aprendizado Supervisionado):
Criar um modelo para prever o preço em 'B' (PPK_B).
Modelo Base: Usar apenas lags do próprio PPK_B como features.
Modelo Completo: Usar lags de PPK_B mais os lags de PPK_A (identificados na correlação cruzada) como features.
Treinar um Random Forest Regressor ou VAR (Vetor Autorregressivo) e comparar os dois modelos.

### Avaliação (Rigor)
Avaliar o p-valor do Teste de Granger (p < 0.05 sugere causalidade).
Nos modelos supervisionados, comparar o RMSE/MAPE do Modelo Base vs. Modelo Completo. Se o Modelo Completo for significativamente melhor, e a análise de "importância de features" (ex: SHAP) mostrar que os lags de A são importantes, temos forte evidência de liderança de preço.

### Conclusão (Discussão Esperada):
Os dados e modelos obtidos respondem se há um "líder" de preço?
O Teste de Granger foi estatisticamente significante? Qual o atraso (lag) encontrado?
Discutir se a inclusão dos dados do mercado concorrente melhorou a previsão, validando o objetivo de entender a dinâmica de mercado.

