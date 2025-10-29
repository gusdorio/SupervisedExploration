import pandas as pd
import numpy as np
from datetime import datetime
import warnings

# Bibliotecas de Modelagem

# (Questão 1) ML
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

# (Questão 1 e 2) Estatistica
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller, ccf, grangercausalitytests
from statsmodels.tools.sm_exceptions import ConvergenceWarning

# Suprime avisos de convergência dos modelos para uma saída mais limpa
warnings.simplefilter('ignore', ConvergenceWarning)
warnings.simplefilter('ignore', UserWarning)


class AnalisadorCestaBasicaPro:
    """
    Classe profissional para análise de dados da cesta básica
    """

    def __init__(self, filepath):
        """
        Carrega os dados usando Pandas, converte datas e define o índice.
        """
        print(f"Carregando dados de '{filepath}' com Pandas...")
        try:
            self.dados_brutos = pd.read_excel(filepath)
            # Converte a coluna de data para o formato datetime
            self.dados_brutos['Data_Coleta'] = pd.to_datetime(self.dados_brutos['Data_Coleta'])
            # Define a data como o índice do DataFrame
            self.dados_brutos.set_index('Data_Coleta', inplace=True)
            self.dados_brutos.sort_index(inplace=True)
            print(f"Dados carregados. {len(self.dados_brutos)} linhas.")
            print("Colunas disponíveis:", self.dados_brutos.columns.tolist())
        except FileNotFoundError:
            print(f"Erro: Arquivo não encontrado em '{filepath}'")
            self.dados_brutos = None
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            self.dados_brutos = None

    # MÉTODOS AUXILIARES

    def _preparar_serie_temporal(self, categoria_col, freq='W-MON'):
        """
        Filtra por categoria e agrega os dados por frequência (semanal).
        """
        if categoria_col not in self.dados_brutos.columns:
            print(f"Erro: Coluna de categoria '{categoria_col}' não encontrada.")
            return None
            
        dados_filtrados = self.dados_brutos[self.dados_brutos[categoria_col] == True]
        if dados_filtrados.empty:
            print(f"Aviso: Nenhum dado encontrado para a categoria '{categoria_col}'.")
            return None
            
        # Agrega os dados por semana (ou outra freq), calculando a média do PPK
        serie_temporal = dados_filtrados['PPK'].resample(freq).mean()
        
        # Preenche pequenos buracos com o último valor
        serie_temporal = serie_temporal.fillna(method='ffill')
        serie_temporal.dropna(inplace=True) # Remove NaNs restantes no início
        
        return serie_temporal

    def _criar_features_lags(self, serie, n_lags=4):
        """
        Transforma a série temporal em um DataFrame supervisionado com lags.
        """
        df = pd.DataFrame(serie)
        df.columns = ['y']
        
        # Cria as features de lag (ex: y_lag_1, y_lag_2, ...)
        for i in range(1, n_lags + 1):
            df[f'y_lag_{i}'] = df['y'].shift(i)
            
        df.dropna(inplace=True) # Remove linhas onde os lags são NaN
        
        X = df.drop('y', axis=1)
        y = df['y']
        
        return X, y

    def _verificar_estacionariedade(self, serie, nome_serie=""):
        """
        Realiza o teste ADF e aplica diferenciação se necessário.
        Retorna a série (potencialmente) estacionária.
        """
        print(f"\nVerificando estacionariedade para: {nome_serie}")
        adf_result = adfuller(serie)
        p_valor = adf_result[1]
        print(f"Teste ADF (p-valor): {p_valor:.4f}")
        
        if p_valor > 0.05:
            print("Série NÃO é estacionária. Aplicando 1ª diferenciação.")
            serie_estacionaria = serie.diff().dropna()
            # Teste novamente
            adf_result_diff = adfuller(serie_estacionaria)
            print(f"Novo p-valor (pós-diff): {adf_result_diff[1]:.4f}")
            return serie_estacionaria
        else:
            print("Série é estacionária.")
            return serie

    # QUESTÃO 1: PREVISÃO DE PREÇOS (Machine Learning)

    def analisar_previsao_preco_ml(self, categoria_col, freq='W-MON', n_lags=4, test_size_semanas=12):
        """
        Responde à Questão 1 usando RandomForestRegressor.
        """
        print("\n--- INICIANDO QUESTÃO 1: PREVISÃO DE PREÇOS (Machine Learning) ---")
        
        serie = self._preparar_serie_temporal(categoria_col, freq)
        if serie is None or serie.empty:
            print("FIM QUESTÃO 1 (ML)")
            return

        print(f"Preparando dados de ML para '{categoria_col}' com {n_lags} lags...")
        X, y = self._criar_features_lags(serie, n_lags)

        if len(y) < test_size_semanas + n_lags:
            print("Erro: Dados insuficientes para treino/teste após criação de lags.")
            print("FIM QUESTÃO 1 (ML)")
            return

        # 1. Divisão Temporal (NUNCA embaralhe séries temporais)
        X_train, X_test = X.iloc[:-test_size_semanas], X.iloc[-test_size_semanas:]
        y_train, y_test = y.iloc[:-test_size_semanas], y.iloc[-test_size_semanas:]

        print(f"Treinando modelo em {len(y_train)} amostras, testando em {len(y_test)}.")

        # 2. Treinamento
        # Usamos RandomForest por ser robusto e não exigir normalização
        modelo = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        modelo.fit(X_train, y_train)

        # 3. Avaliação
        predicoes = modelo.predict(X_test)
        mape = mean_absolute_percentage_error(y_test, predicoes)
        rmse = np.sqrt(mean_squared_error(y_test, predicoes))
        
        print("\n[Avaliação do Modelo (Random Forest)]")
        print(f"MAPE (Erro Percentual): {mape * 100:.2f}%")
        print(f"RMSE (Erro em R$): R$ {rmse:.2f}")

        if mape < 0.10:
            print("Conclusão: Objetivo atingido! (MAPE < 10%)")
        else:
            print("Conclusão: Objetivo NÃO atingido. (MAPE >= 10%)")
            
        # 4. Previsão Futura
        historico_recente = X_test.iloc[-1].values.tolist()
        proxima_previsao = modelo.predict([historico_recente])
        
        print("\n[Previsão Futura]")
        print(f"Semana T+1 (Próxima semana): R$ {proxima_previsao[0]:.2f}")
        
        print("FIM QUESTÃO 1 (ML)")

    # --- QUESTÃO 2: LIDERANÇA DE PREÇO ---
    
    def analisar_lideranca_preco(self, produto_id, estab_A, estab_B, freq='W-MON', max_lag=8):
        """
        Responde à Questão 2 usando Causalidade de Granger.
        """
        print("\nINICIANDO QUESTÃO 2: LIDERANÇA DE PREÇO (Statsmodels)")
        print(f"Analisando Produto '{produto_id}' entre Mercado '{estab_A}' e '{estab_B}'")

        # 1. Filtrar dados e pivotar
        dados_prod = self.dados_brutos[self.dados_brutos['Produto'] == produto_id]
        if dados_prod.empty:
            print(f"Erro: Produto '{produto_id}' não encontrado.")
            print("FIM QUESTÃO 2")
            return

        dados_pivot = dados_prod.pivot_table(index=dados_prod.index, 
                                             columns='Estabelecimento', 
                                             values='PPK')
        
        if estab_A not in dados_pivot.columns or estab_B not in dados_pivot.columns:
            print(f"Erro: Estabelecimento '{estab_A}' ou '{estab_B}' não possui dados para o produto '{produto_id}'.")
            print("FIM QUESTÃO 2")
            return

        # 2. Resample e alinhamento
        dados_pares = dados_pivot[[estab_A, estab_B]].resample(freq).mean().fillna(method='ffill')
        dados_pares.dropna(inplace=True) # Remove NaNs no início

        if len(dados_pares) < max_lag + 20: # Mínimo para os testes
            print("Erro: Dados insuficientes após alinhamento das séries.")
            print("FIM QUESTÃO 2")
            return

        # 3. Rigor: Verificar Estacionariedade (requerimento do Teste de Granger)
        serie_A_est = self._verificar_estacionariedade(dados_pares[estab_A], estab_A)
        serie_B_est = self._verificar_estacionariedade(dados_pares[estab_B], estab_B)
        
        # Alinha as séries estacionárias (diff() pode ter tamanhos diferentes)
        dados_estacionarios = pd.concat([serie_A_est, serie_B_est], axis=1).dropna()
        dados_estacionarios.columns = [estab_A, estab_B]

        # 4. Teste de Causalidade de Granger
        print("\n[Teste de Causalidade de Granger]")
        
        # Teste 1: A -> B (O Mercado A causa mudança no Mercado B?)
        # Colunas: [Y, X] -> Testamos se X "Granger-causa" Y
        print(f"Testando se '{estab_A}' (X) causa '{estab_B}' (Y)...")
        granger_A_causa_B = grangercausalitytests(dados_estacionarios[[estab_B, estab_A]], maxlag=max_lag, verbose=False)
        
        # Teste 2: B -> A (O Mercado B causa mudança no Mercado A?)
        print(f"Testando se '{estab_B}' (X) causa '{estab_A}' (Y)...")
        granger_B_causa_A = grangercausalitytests(dados_estacionarios[[estab_A, estab_B]], maxlag=max_lag, verbose=False)

        # 5. Interpretação dos Resultados
        p_valor_min_A_B = min(granger_A_causa_B[lag][0]['ssr_ftest'][1] for lag in range(1, max_lag + 1))
        p_valor_min_B_A = min(granger_B_causa_A[lag][0]['ssr_ftest'][1] for lag in range(1, max_lag + 1))

        print("\n[Conclusão da Causalidade (p-valor < 0.05 é significante)]")
        
        if p_valor_min_A_B < 0.05:
            print(f"SIGNIFICANTE: Mercado '{estab_A}' causa mudanças de preço no Mercado '{estab_B}' (p={p_valor_min_A_B:.4f}).")
        else:
            print(f"NÃO SIGNIFICANTE: Mercado '{estab_A}' NÃO causa mudanças no Mercado '{estab_B}' (p={p_valor_min_A_B:.4f}).")

        if p_valor_min_B_A < 0.05:
            print(f"SIGNIFICANTE: Mercado '{estab_B}' causa mudanças de preço no Mercado '{estab_A}' (p={p_valor_min_B_A:.4f}).")
        else:
            print(f"NÃO SIGNIFICANTE: Mercado '{estab_B}' NÃO causa mudanças no Mercado '{estab_A}' (p={p_valor_min_B_A:.4f}).")
            
        # 6. Correlação Cruzada (para ver o lag)
        ccf_vals = ccf(serie_A_est, serie_B_est, adjusted=True)
        # Encontra o lag com maior correlação (positiva ou negativa)
        max_corr_lag = np.argmax(np.abs(ccf_vals[1:max_lag+1])) + 1 # Ignora lag 0
        max_corr_val = ccf_vals[max_corr_lag]
        
        print(f"\n[Correlação Cruzada (força e direção)]")
        print(f"Correlação mais forte no Lag = {max_corr_lag} semanas (Valor: {max_corr_val:.3f})")
        print(f"Interpretação: Mudanças em '{estab_A}' são vistas em '{estab_B}' {max_corr_lag} semana(s) depois.")
        
        print("FIM QUESTÃO 2")