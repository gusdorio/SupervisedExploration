import pandas as pd
import numpy as np
import warnings

# Bibliotecas de Modelagem
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from statsmodels.tsa.stattools import adfuller, ccf, grangercausalitytests
from statsmodels.tools.sm_exceptions import ConvergenceWarning

warnings.simplefilter('ignore', ConvergenceWarning)
warnings.simplefilter('ignore', UserWarning)

class AnalisadorCestaBasicaPro:
    """
    Classe profissional para análise de dados da cesta básica,
    MODIFICADA para retornar dados para dashboards (ex: Streamlit com Plotly).
    """

    def __init__(self, filepath):
        print(f"Carregando dados de '{filepath}' com Pandas.")
        try:
            self.dados_brutos = pd.read_excel(filepath) 
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
            # Extrai filtros para o app
            self.classes = sorted([col for col in self.dados_brutos.columns if col.startswith('Classe_')])
            self.estabelecimentos = sorted(self.dados_brutos['Estabelecimento'].unique().tolist())
            self.produtos = sorted(self.dados_brutos['Produto'].unique().tolist())

    # MÉTODOS AUXILIARES (internos)

    def _preparar_serie_temporal(self, categoria_col, freq='W-MON'):
        if categoria_col not in self.dados_brutos.columns:
            return None
        dados_filtrados = self.dados_brutos[self.dados_brutos[categoria_col] == True]
        if dados_filtrados.empty:
            return None
        
        serie_temporal = dados_filtrados['PPK'].resample(freq).mean()
        serie_temporal = serie_temporal.fillna(method='ffill')
        serie_temporal.dropna(inplace=True)
        return serie_temporal

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
            adf_result_diff = adfuller(serie_estacionaria)
            return serie_estacionaria, f"Não (p={p_valor:.3f}), Pós-Diff (p={adf_result_diff[1]:.3f})"
        else:
            return serie, f"Sim (p={p_valor:.3f})"

    # MÉTODOS DE ANÁLISE (retornam dicionários)

    def analisar_previsao_preco_ml(self, categoria_col, freq='W-MON', n_lags=4, test_size_semanas=12):
        
        serie = self._preparar_serie_temporal(categoria_col, freq)
        if serie is None or serie.empty:
            return {'erro': f"Sem dados para a classe '{categoria_col}'."}

        X, y = self._criar_features_lags(serie, n_lags)

        if len(y) < test_size_semanas + n_lags:
            return {'erro': "Dados insuficientes para treino/teste."}

        X_train, X_test = X.iloc[:-test_size_semanas], X.iloc[-test_size_semanas:]
        y_train, y_test = y.iloc[:-test_size_semanas], y.iloc[-test_size_semanas:]

        modelo = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        modelo.fit(X_train, y_train)

        predicoes = modelo.predict(X_test)
        mape = mean_absolute_percentage_error(y_test, predicoes)
        rmse = np.sqrt(mean_squared_error(y_test, predicoes))

        df_plot = pd.DataFrame({'Preço Real': y_test, 'Previsão do Modelo': predicoes})
        
        historico_recente = X_test.iloc[-1].values.tolist()
        previsao_t1 = modelo.predict([historico_recente])[0]
        
        return {
            'mape': mape,
            'rmse': rmse,
            'df_plot': df_plot,
            'serie_original_plot': serie.to_frame(name='Preço Médio Semanal'),
            'previsao_t1': previsao_t1,
            'n_treino': len(y_train),
            'n_teste': len(y_test),
            'erro': None
        }

    def analisar_lideranca_preco(self, produto_id, estab_A, estab_B, freq='W-MON', max_lag=8):
        
        dados_prod = self.dados_brutos[self.dados_brutos['Produto'] == produto_id]
        if dados_prod.empty:
            return {'erro': f"Produto '{produto_id}' não encontrado."}

        dados_pivot = dados_prod.pivot_table(index=dados_prod.index, 
                                             columns='Estabelecimento', 
                                             values='PPK')
        
        if estab_A not in dados_pivot.columns or estab_B not in dados_pivot.columns:
            return {'erro': f"Estabelecimento '{estab_A}' ou '{estab_B}' não possui dados para o produto."}

        dados_pares = dados_pivot[[estab_A, estab_B]].resample(freq).mean().fillna(method='ffill')
        dados_pares.dropna(inplace=True)

        if len(dados_pares) < max_lag + 20:
            return {'erro': "Dados insuficientes após alinhamento das séries."}

        serie_A_est, adf_A = self._verificar_estacionariedade(dados_pares[estab_A])
        serie_B_est, adf_B = self._verificar_estacionariedade(dados_pares[estab_B])
        
        dados_estacionarios = pd.concat([serie_A_est, serie_B_est], axis=1).dropna()
        dados_estacionarios.columns = [estab_A, estab_B]

        if dados_estacionarios.empty or len(dados_estacionarios) < max_lag + 1:
            return {'erro': "Não foi possível estacionarizar as séries para o teste."}

        granger_A_causa_B = grangercausalitytests(dados_estacionarios[[estab_B, estab_A]], maxlag=max_lag, verbose=False)
        granger_B_causa_A = grangercausalitytests(dados_estacionarios[[estab_A, estab_B]], maxlag=max_lag, verbose=False)

        p_valor_min_A_B = min(granger_A_causa_B[lag][0]['ssr_ftest'][1] for lag in range(1, max_lag + 1))
        p_valor_min_B_A = min(granger_B_causa_A[lag][0]['ssr_ftest'][1] for lag in range(1, max_lag + 1))

        ccf_vals = ccf(serie_A_est, serie_B_est, adjusted=True)
        ccf_vals_lags = ccf_vals[1:max_lag + 1]
        
        ccf_df = pd.DataFrame({'Correlação': ccf_vals_lags}, index=np.arange(1, max_lag + 1))
        ccf_df.index.name = "Lag (Semanas)"

        best_lag = ccf_df['Correlação'].abs().idxmax()
        best_corr = ccf_df.loc[best_lag, 'Correlação']
        
        return {
            'adf_status_A': adf_A,
            'adf_status_B': adf_B,
            'p_A_causa_B': p_valor_min_A_B,
            'p_B_causa_A': p_valor_min_B_A,
            'ccf_df': ccf_df,
            'best_lag': best_lag,
            'best_corr': best_corr,
            'dados_pares_plot': dados_pares,
            'erro': None
        }