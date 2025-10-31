import pandas as pd
import numpy as np
import warnings

# Bibliotecas de Modelagem
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, mean_absolute_error
from statsmodels.tsa.stattools import adfuller, ccf, grangercausalitytests
from statsmodels.tools.sm_exceptions import ConvergenceWarning

warnings.simplefilter('ignore', ConvergenceWarning)
warnings.simplefilter('ignore', UserWarning)

class AnalisadorCestaBasicaPro:
    """
    Classe profissional para análise de dados da cesta básica,
    MODIFICADA para funcionar com o dashboard.py (recebendo IDs).
    """

    def __init__(self, filepath):
        print(f"Carregando dados de '{filepath}' com Pandas.")
        try:
            self.dados_brutos = pd.read_excel(filepath, sheet_name="Sheet1", engine='openpyxl')
            
            if 'Data' in self.dados_brutos.columns:
                self.dados_brutos['Data'] = pd.to_datetime(self.dados_brutos['Data'])
                self.dados_brutos.set_index('Data', inplace=True)
            elif 'Data_Coleta' in self.dados_brutos.columns:
                 self.dados_brutos['Data_Coleta'] = pd.to_datetime(self.dados_brutos['Data_Coleta'])
                 self.dados_brutos.set_index('Data_Coleta', inplace=True)
            
            self.dados_brutos.sort_index(inplace=True)
            print("Dados carregados com sucesso.")
            
        except FileNotFoundError:
            print(f"Erro: Arquivo não encontrado em '{filepath}'")
            self.dados_brutos = None
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            self.dados_brutos = None
            
        if self.dados_brutos is not None:
            self.estabelecimentos = sorted(self.dados_brutos['Estabelecimento'].unique().tolist())
            self.produtos = sorted(self.dados_brutos['Produto'].unique().tolist())
            self.categorias = [col for col in self.dados_brutos.columns if col.startswith('Classe_')]
            print(f"Categorias identificadas para Q1: {self.categorias}")

    # MÉTODOS AUXILIARES (internos)

    def _criar_features_lags(self, serie, n_lags=4):
        df = pd.DataFrame(serie)
        df.columns = ['y']
        for i in range(1, n_lags + 1):
            df[f'y_lag_{i}'] = df['y'].shift(i)
        df.dropna(inplace=True)
        X = df.drop('y', axis=1)
        y = df['y']
        return X, y

    def _verificar_estacionariedade(self, serie):
        adf_result = adfuller(serie)
        p_valor = adf_result[1]
        if p_valor > 0.05:
            serie_estacionaria = serie.diff().dropna()
            if adfuller(serie_estacionaria)[1] > 0.05:
                 serie_estacionaria = serie_estacionaria.diff().dropna()
            
            if serie_estacionaria.empty:
                return serie, f"Não (p={p_valor:.3f}), falha ao estacionarizar"

            adf_result_diff = adfuller(serie_estacionaria)
            return serie_estacionaria, f"Não (p={p_valor:.3f}), Pós-Diff (p={adf_result_diff[1]:.3f})"
        else:
            return serie, f"Sim (p={p_valor:.3f})"

    # MÉTODOS DE ANÁLISE (Dashboard - Questão 1)

    def analisar_previsao_categoria(self, nome_categoria, test_size_semanas=12, freq='W-MON', n_lags=4):
        """
        Função MODIFICADA para Questão 1 (alinhada ao Relatório).
        Recebe um 'nome_categoria' string (ex: 'Classe_Carnes Vermelhas') e faz a previsão.
        Retorna (df_plot, mse, mae, mape, df_futuro, erro)
        """
        if self.dados_brutos is None:
            return None, None, None, None, None, "Dados brutos não foram carregados."

        if nome_categoria not in self.categorias:
             return None, None, None, None, None, f"Categoria '{nome_categoria}' não encontrada nos dados."

        # 1. Filtrar pela COLUNA de Categoria
        dados_cat = self.dados_brutos[self.dados_brutos[nome_categoria] == True]
        
        if dados_cat.empty:
            return None, None, None, None, None, f"Sem dados para a Categoria '{nome_categoria}'."
        
        # 2. Criar a série temporal
        serie_temporal = dados_cat['PPK'].resample(freq).mean()
        serie_temporal = serie_temporal.fillna(method='ffill')
        serie_temporal.dropna(inplace=True)
        
        if serie_temporal.empty:
            return None, None, None, None, None, f"Série temporal vazia para a Categoria '{nome_categoria}'."

        # 3. Criar features
        X, y = self._criar_features_lags(serie_temporal, n_lags)

        if len(y) < test_size_semanas + n_lags:
            return None, None, None, None, None, "Dados insuficientes para treino/teste após criação de lags."

        # 4. Dividir dados (para cálculo de métricas)
        X_train_metrica, X_test_metrica = X.iloc[:-test_size_semanas], X.iloc[-test_size_semanas:]
        y_train_metrica, y_test_metrica = y.iloc[:-test_size_semanas], y.iloc[-test_size_semanas:]

        if X_train_metrica.empty or y_train_metrica.empty:
            return None, None, None, None, None, "Dados de treino insuficientes após divisão."

        # 5. Treinar modelo (para métricas)
        modelo_metrica = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        modelo_metrica.fit(X_train_metrica, y_train_metrica)

        # 6. Avaliar (calcula MAPE conforme Relatório)
        predicoes = modelo_metrica.predict(X_test_metrica)
        mse = mean_squared_error(y_test_metrica, predicoes)
        mae = mean_absolute_error(y_test_metrica, predicoes)
        mape = mean_absolute_percentage_error(y_test_metrica, predicoes)

        # 7. Preparar dados para plotagem de teste
        df_plot_teste = pd.DataFrame({'Preço Real': y_test_metrica, 'Previsão do Modelo': predicoes})
        
        # 8. Treinar modelo final com TODOS os dados
        modelo_final = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        modelo_final.fit(X, y) # X, y é todo o dataset com lags

        # 9. Previsão Futura (Auto-regressiva)
        n_futuro = 12 # Prever 12 semanas fixas
        
        # Pega a última linha de features (lags) conhecida
        last_features = X.iloc[-1].values.reshape(1, -1)
        previsoes_futuras = []

        for _ in range(n_futuro):
            # Prever o próximo passo (t+1)
            prox_pred = modelo_final.predict(last_features)[0]
            previsoes_futuras.append(prox_pred)
            
            # Atualizar o vetor de features para prever (t+2)
            # "Empurra" os valores e insere a nova previsão no início
            last_features = np.roll(last_features, 1)
            last_features[0, 0] = prox_pred

        # 10. Criar DataFrame futuro
        ultimo_indice = y.index[-1]
        indice_futuro = pd.date_range(start=ultimo_indice + pd.Timedelta(weeks=1), periods=n_futuro, freq=freq)
        
        df_futuro = pd.DataFrame(previsoes_futuras, index=indice_futuro, columns=['Previsão Futura (PPK)'])
        df_futuro.index.name = 'Data Futura'

        # 11. Retornar
        return df_plot_teste, mse, mae, mape, df_futuro, None # erro é None


    # MÉTODOS DE ANÁLISE (Dashboard - Questão 2)

    def analisar_lideranca_preco(self, produto_id, estab_A_id, estab_B_id, max_lag=8, freq='W-MON'):
        """
        Função para Questão 2 (Item Específico). Esta função está correta.
        Recebe IDs numéricos para produto e estabelecimentos.
        """
        
        if self.dados_brutos is None:
            return None, None, None, None, "Dados brutos não foram carregados."

        dados_prod = self.dados_brutos[self.dados_brutos['Produto'] == produto_id]
        if dados_prod.empty:
            return None, None, None, None, f"Produto ID '{produto_id}' não encontrado."

        dados_pivot = dados_prod.pivot_table(index=dados_prod.index, 
                                             columns='Estabelecimento', 
                                             values='PPK')
        
        if estab_A_id not in dados_pivot.columns:
            return None, None, None, None, f"Estabelecimento ID '{estab_A_id}' não possui dados para este produto."
        if estab_B_id not in dados_pivot.columns:
             return None, None, None, None, f"Estabelecimento ID '{estab_B_id}' não possui dados para este produto."

        dados_pares = dados_pivot[[estab_A_id, estab_B_id]].resample(freq).mean().fillna(method='ffill')
        dados_pares.dropna(inplace=True)

        if len(dados_pares) < max_lag + 20: 
            return None, None, None, None, "Dados insuficientes após alinhamento das séries (menos de 20 + lag pontos)."

        serie_A_est, adf_A = self._verificar_estacionariedade(dados_pares[estab_A_id])
        serie_B_est, adf_B = self._verificar_estacionariedade(dados_pares[estab_B_id])
        
        dados_estacionarios = pd.concat([serie_A_est, serie_B_est], axis=1).dropna()
        dados_estacionarios.columns = [estab_A_id, estab_B_id]

        if dados_estacionarios.empty or len(dados_estacionarios) < max_lag + 1:
            return None, None, None, None, "Não foi possível estacionarizar as séries para o teste (dados insuficientes pós-diferenciação)."

        try:
            granger_A_causa_B = grangercausalitytests(dados_estacionarios[[estab_B_id, estab_A_id]], maxlag=max_lag, verbose=False)
            granger_B_causa_A = grangercausalitytests(dados_estacionarios[[estab_A_id, estab_B_id]], maxlag=max_lag, verbose=False)

            p_valor_min_A_B = min(granger_A_causa_B[lag][0]['ssr_ftest'][1] for lag in range(1, max_lag + 1))
            p_valor_min_B_A = min(granger_B_causa_A[lag][0]['ssr_ftest'][1] for lag in range(1, max_lag + 1))
        except Exception as e:
             return None, None, None, None, f"Erro no teste de Granger: {e}"

        ccf_vals = ccf(serie_A_est, serie_B_est, adjusted=True)
        ccf_vals_lags = ccf_vals[1:max_lag + 1] 
        
        ccf_df = pd.DataFrame({'CCF': ccf_vals_lags}, index=np.arange(1, max_lag + 1))
        ccf_df.index.name = "Lag"
        ccf_df = ccf_df.reset_index() 

        return dados_pares, ccf_df, p_valor_min_A_B, p_valor_min_B_A, None