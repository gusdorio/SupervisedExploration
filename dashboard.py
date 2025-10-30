import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Importar a classe modificada
try:
    from classes.algotithms import AnalisadorCestaBasicaPro
except ImportError:
    st.error("Erro: Não foi possível encontrar o arquivo 'algotithms_plotly.py'. "
             "Certifique-se de que ele está salvo na mesma pasta que este script 'app.py'.")
    st.stop()

# Nome do arquivo de dados
DATA_FILE = "./data/dados_limpos_ICB.xlsx"

# Configuração da Página
st.set_page_config(layout="wide", page_title="Análise Cesta Básica")

# Funções de Plotagem

def plot_previsao_q1(df_plot):
    """Cria um gráfico Plotly comparando Real vs. Previsto."""
    fig = px.line(df_plot, title="Comparação: Preço Real vs. Previsão do Modelo (em semanas de teste)",
                  labels={'value': 'Preço (PPK)', 'index': 'Semana', 'variable': 'Legenda'})
    fig.update_traces(line=dict(width=2.5))
    fig.update_layout(hovermode="x unified")
    return fig

def plot_series_q2(df_plot, estab_A, estab_B):
    """Cria um gráfico Plotly comparando as duas séries de preço."""
    fig = px.line(df_plot, y=[estab_A, estab_B], 
                  title=f"Preço Médio Semanal: {estab_A} vs. {estab_B}",
                  labels={'value': 'Preço (PPK)', 'index': 'Data', 'variable': 'Estabelecimento'})
    fig.update_traces(line=dict(width=2.5))
    fig.update_layout(hovermode="x unified")
    return fig

def plot_ccf_q2(df_plot):
    """Cria um gráfico de barras Plotly para a Correlação Cruzada."""
    df_plot_reset = df_plot.reset_index() # Plotly bar prefere colunas
    fig = px.bar(df_plot_reset, x='Lag (Semanas)', y='Correlação',
                 title="Correlação Cruzada (Qual mercado se move primeiro?)",
                 color='Correlação',
                 color_continuous_scale='RdBu_r',
                 hover_data={'Lag (Semanas)': True, 'Correlação': ':.3f'})
    fig.update_layout(coloraxis_showscale=False)
    return fig

def plot_vis_geral_linhas(dados, classe_selecionada):
    """Cria um gráfico Plotly da tendência de preço para uma classe."""
    dados_classe = dados[dados[classe_selecionada] == True]
    ppk_medio_semanal = dados_classe['PPK'].resample('W-MON').mean().fillna(method='ffill').to_frame()
    
    fig = px.line(ppk_medio_semanal, y='PPK', 
                  title=f"Preço Médio Semanal para {classe_selecionada.replace('Classe_', '')}",
                  labels={'PPK': 'Preço Médio (PPK)', 'Data_Coleta': 'Data'})
    fig.update_traces(line=dict(color='#1E90FF', width=3))
    return fig
    
def plot_vis_geral_box(dados, classe_selecionada):
    """Cria um boxplot Plotly de preços por estabelecimento."""
    dados_classe = dados[dados[classe_selecionada] == True]
    
    fig = px.box(dados_classe, x='Estabelecimento', y='PPK',
                 title=f"Distribuição de Preços por Estabelecimento (para {classe_selecionada.replace('Classe_', '')})",
                 color='Estabelecimento',
                 labels={'PPK': 'Preço Médio (PPK)', 'Estabelecimento': 'Mercado'})
    fig.update_layout(showlegend=False)
    return fig


# Carregamento da Classe (Cache)
@st.cache_resource
def carregar_analisador(filepath):
    try:
        analisador = AnalisadorCestaBasicaPro(filepath)
        if analisador.dados_brutos is None:
            return None
        return analisador
    except Exception as e:
        st.error(f"Erro ao carregar o analisador: {e}")
        return None

# Cache das Análises
@st.cache_data
def rodar_analise_q1(_analisador, classe, n_lags, test_size):
    return _analisador.analisar_previsao_preco_ml(
        categoria_col=classe,
        n_lags=n_lags,
        test_size_semanas=test_size
    )

@st.cache_data
def rodar_analise_q2(_analisador, produto, estab_A, estab_B, max_lag):
    return _analisador.analisar_lideranca_preco(
        produto_id=produto,
        estab_A=estab_A,
        estab_B=estab_B,
        max_lag=max_lag
    )

# INÍCIO DO APP
st.title("Dashboard de Análise de Preços da Cesta Básica 🛒")

analisador = carregar_analisador(DATA_FILE)

if not analisador:
    st.error(f"Não foi possível carregar o arquivo de dados '{DATA_FILE}'.")
    st.stop()

# BARRA LATERAL (FILTROS) 
st.sidebar.title("Painel de Controle")
pagina = st.sidebar.radio(
    "Selecione a Análise:",
    ("Visão Geral", "Questão 1: Previsão de Preços", "Questão 2: Liderança de Preços")
)
st.sidebar.markdown("---")

# PÁGINA 1: VISÃO GERAL
if pagina == "Visão Geral":
    st.header("Visão Geral e Exploração dos Dados")
    st.info("Uma visão interativa dos dados brutos para o público geral.")
    
    # Filtro para a página
    st.sidebar.subheader("Filtros - Visão Geral")
    classe_vis = st.sidebar.selectbox("Selecione a Classe para explorar:", analisador.classes)
    
    if classe_vis:
        st.plotly_chart(plot_vis_geral_linhas(analisador.dados_brutos, classe_vis), use_container_width=True)
        st.plotly_chart(plot_vis_geral_box(analisador.dados_brutos, classe_vis), use_container_width=True)
        
    st.subheader("Dados Brutos")
    with st.expander("Clique para ver os dados completos"):
        st.dataframe(analisador.dados_brutos)

# PÁGINA 2: QUESTÃO 1 (PREVISÃO)
elif pagina == "Questão 1: Previsão de Preços":
    st.header("Questão 1: O modelo consegue prever o preço futuro?")
    st.info("""
    **Objetivo:** Testar se um modelo de Machine Learning consegue prever o preço
    médio de uma categoria para as próximas semanas.
    """)

    # Filtros Q1
    st.sidebar.subheader("Filtros - Questão 1")
    classe_q1 = st.sidebar.selectbox("Selecione a Classe:", analisador.classes)
    n_lags_q1 = st.sidebar.slider("Semanas de 'Memória' (Lags):", 1, 12, 4)
    test_size_q1 = st.sidebar.slider("Semanas para Teste:", 4, 26, 12)
    
    if st.sidebar.button("Rodar Análise de Previsão", type="primary"):
        resultados_q1 = rodar_analise_q1(analisador, classe_q1, n_lags_q1, test_size_q1)
        
        if resultados_q1['erro']:
            st.error(resultados_q1['erro'])
        else:
            st.subheader("Resultados da Previsão")
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric(
                label="Erro Percentual Médio (MAPE)",
                value=f"{resultados_q1['mape']*100:.2f}%",
                help="Em média, o modelo erra a previsão em X%. Quanto menor, melhor."
            )
            col2.metric(
                label="Erro Médio em Reais (RMSE)",
                value=f"R$ {resultados_q1['rmse']:.2f}",
                help="Em média, o modelo erra a previsão em X Reais. Quanto menor, melhor."
            )
            col3.metric(
                label="Previsão para Próxima Semana",
                value=f"R$ {resultados_q1['previsao_t1']:.2f}"
            )
            
            # Gráfico Plotly
            fig_q1 = plot_previsao_q1(resultados_q1['df_plot'])
            st.plotly_chart(fig_q1, use_container_width=True)
            
            with st.expander("O que este gráfico significa?"):
                st.markdown("""
                - A linha **'Preço Real'** é o que de fato aconteceu com o preço nas últimas semanas de teste.
                - A linha **'Previsão do Modelo'** é o que o modelo *achou* que ia acontecer.
                
                Quanto mais próximas as duas linhas, melhor é o nosso modelo.
                """)
            
            with st.expander("Ver série histórica completa"):
                fig_hist = px.line(resultados_q1['serie_original_plot'], title="Série de Preço Completa (Treino + Teste)")
                st.plotly_chart(fig_hist, use_container_width=True)

# PÁGINA 3: QUESTÃO 2 (LIDERANÇA)
elif pagina == "Questão 2: Liderança de Preços":
    st.header("Questão 2: Um mercado 'puxa' o preço do outro?")
    st.info("""
    **Objetivo:** Analisar se a mudança de preço de um produto em um mercado
    antecipa a mudança de preço em outro mercado.
    """)

    # Filtros Q2
    st.sidebar.subheader("Filtros - Questão 2")
    prod_q2 = st.sidebar.selectbox("Selecione o Produto:", analisador.produtos)
    estab_A = st.sidebar.selectbox("Mercado 'Líder' (A):", analisador.estabelecimentos, index=0)
    estab_B = st.sidebar.selectbox("Mercado 'Seguidor' (B):", analisador.estabelecimentos, index=1)
    max_lag_q2 = st.sidebar.slider("Atraso Máximo (Semanas):", 2, 12, 8)
    
    if estab_A == estab_B:
        st.sidebar.error("Selecione dois mercados diferentes.")
    elif st.sidebar.button("Rodar Análise de Liderança", type="primary"):
        resultados_q2 = rodar_analise_q2(analisador, prod_q2, estab_A, estab_B, max_lag_q2)
        
        if resultados_q2['erro']:
            st.error(resultados_q2['erro'])
        else:
            st.subheader("Resultados da Análise")
            
            # Gráfico de Séries
            fig_series_q2 = plot_series_q2(resultados_q2['dados_pares_plot'], estab_A, estab_B)
            st.plotly_chart(fig_series_q2, use_container_width=True)
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Análise de Causalidade")
                st.caption(f"Verifica se '{estab_A}' estatisticamente 'puxa' '{estab_B}' (e vice-versa).")
                
                p_A_B = resultados_q2['p_A_causa_B']
                p_B_A = resultados_q2['p_B_causa_A']
                
                # Métrica A -> B
                valor_A_B = "Sim ✅" if p_A_B < 0.05 else "Não ❌"
                st.metric(
                    label=f"Mercado '{estab_A}' puxa o preço de '{estab_B}'?",
                    value=valor_A_B,
                    help=f"Teste de Causalidade de Granger (p-valor={p_A_B:.4f}). Se p-valor < 0.05, consideramos 'Sim'."
                )
                
                # Métrica B -> A
                valor_B_A = "Sim ✅" if p_B_A < 0.05 else "Não ❌"
                st.metric(
                    label=f"Mercado '{estab_B}' puxa o preço de '{estab_A}'?",
                    value=valor_B_A,
                    help=f"Teste de Causalidade de Granger (p-valor={p_B_A:.4f}). Se p-valor < 0.05, consideramos 'Sim'."
                )

            with col2:
                st.subheader("Análise de Atraso (Lag)")
                st.caption("Se um mercado puxa o outro, quantas semanas ele demora?")
                
                # Gráfico CCF
                fig_ccf_q2 = plot_ccf_q2(resultados_q2['ccf_df'])
                st.plotly_chart(fig_ccf_q2, use_container_width=True)
                
                st.metric(
                    label="Atraso com Maior Correlação:",
                    value=f"{resultados_q2['best_lag']} Semana(s)",
                    help=f"O 'eco' da mudança de preço do mercado A no mercado B é mais forte após este número de semanas (Correlação: {resultados_q2['best_corr']:.3f})."
                )