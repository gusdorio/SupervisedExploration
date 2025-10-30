import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json 
import os 

# Importar a classe
try:
    from classes.algotithms import AnalisadorCestaBasicaPro
except ImportError:
    st.error("Erro: Não foi possível encontrar o arquivo 'algotithms.py'. "
             "Certifique-se de que ele está na pasta 'classes'.")
    st.stop()

# --- Constantes de Arquivos ---
BASE_DATA_PATH = "./data"
DATA_FILE = os.path.join(BASE_DATA_PATH, "dados_limpos_ICB.xlsx")
MAPA_PRODUTO_FILE = os.path.join(BASE_DATA_PATH, "mapa_Produto.json")
MAPA_ESTAB_FILE = os.path.join(BASE_DATA_PATH, "mapa_Estabelecimento.json")

# MODIFICAÇÃO: Lista de Categorias para Q1 (baseado no CSV)
LISTA_CATEGORIAS = [
    "Classe_Carnes Vermelhas",
    "Classe_Grãos & Massas",
    "Classe_Laticínios",
    "Classe_Padaria & Cozinha",
    "Classe_Vegetais"
]

# Configuração da Página
st.set_page_config(layout="wide", page_title="Análise Cesta Básica")

# --- Funções de Carregamento (com Caching) ---

@st.cache_data
def carregar_mapas():
    """Carrega os mapas de ID para Nome dos arquivos JSON (usado pela Q2)."""
    try:
        with open(MAPA_PRODUTO_FILE, 'r', encoding='utf-8') as f:
            mapa_produto = json.load(f)  
        
        with open(MAPA_ESTAB_FILE, 'r', encoding='utf-8') as f:
            mapa_estab = json.load(f)    
            
        mapa_id_para_produto = {v: k for k, v in mapa_produto.items()}
        mapa_id_para_estab = {v: k for k, v in mapa_estab.items()}

        return mapa_produto, mapa_estab, mapa_id_para_produto, mapa_id_para_estab
        
    except FileNotFoundError:
        st.error(f"Erro Crítico: Arquivos de mapeamento JSON não encontrados (necessários para Q2).")
        st.error(f"Verifique se '{MAPA_PRODUTO_FILE}' e '{MAPA_ESTAB_FILE}' existem.")
        st.info("Você precisa executar o notebook 'statistical_analysis.ipynb' primeiro para gerar esses arquivos.")
        st.stop()
    except json.JSONDecodeError:
        st.error("Erro ao ler os arquivos JSON. Verifique se eles não estão corrompidos.")
        st.stop()

@st.cache_data
def load_data(file_path):
    """Carrega e pré-processa os dados limpos."""
    try:
        df = pd.read_excel(file_path, sheet_name="Sheet1", engine='openpyxl')
    except FileNotFoundError:
        st.error(f"Erro: Arquivo de dados '{file_path}' não encontrado.")
        st.info("Verifique se o arquivo 'dados_limpos_ICB.xlsx' está na pasta 'data'.")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel: {e}")
        st.stop()

    if df.empty:
        st.error("O arquivo de dados está vazio.")
        st.stop()
        
    if 'Data' in df.columns:
        try:
            df['Data'] = pd.to_datetime(df['Data'])
            df = df.set_index('Data')
        except Exception as e:
            st.warning(f"Não foi possível processar a coluna 'Data': {e}")
            
    try:
        cols_to_int = ['Produto', 'Estabelecimento']
        for col in cols_to_int:
            if col in df.columns:
                df[col] = df[col].astype(int)
    except Exception as e:
        st.error(f"Erro ao converter colunas para inteiro: {e}")
        st.stop()
        
    return df

# --- Funções de Plotagem (Sem Alterações) ---

def plot_previsao_q1(df_plot):
    fig = px.line(df_plot, title="Comparação: Preço Real vs. Previsão do Modelo (em semanas de teste)",
                  labels={'value': 'Preço (PPK)', 'index': 'Semana', 'variable': 'Legenda'})
    fig.update_traces(line=dict(width=2.5))
    fig.update_layout(hovermode="x unified")
    return fig

def plot_series_q2(df_plot, estab_A_nome, estab_B_nome):
    fig = px.line(df_plot, title=f"Série de Preços: {estab_A_nome} vs. {estab_B_nome}",
                  labels={'value': 'Preço (PPK)', 'index': 'Semana', 'variable': 'Mercado'})
    fig.update_traces(line=dict(width=2.5))
    fig.update_layout(hovermode="x unified", legend_title="Mercado")
    return fig

def plot_ccf_q2(ccf_df):
    fig = px.bar(ccf_df, x='Lag', y='CCF', title="Análise de Atraso (Cross-Correlation)",
                 labels={'Lag': 'Atraso (Semanas)', 'CCF': 'Correlação'})
    
    max_lag = ccf_df.loc[ccf_df['CCF'].abs().idxmax()]
    
    fig.add_shape(type="line",
                  x0=max_lag['Lag'], y0=0, x1=max_lag['Lag'], y1=max_lag['CCF'],
                  line=dict(color="red", width=2, dash="dash"))
    
    fig.add_annotation(x=max_lag['Lag'], y=max_lag['CCF'],
                       text=f"Max. Correlação em {max_lag['Lag']} semanas",
                       showarrow=True, arrowhead=1, ax=20, ay=-30)
    
    fig.update_layout(hovermode="x unified")
    return fig

# --- Funções de Análise (Backend) ---

@st.cache_data
# MODIFICAÇÃO: Recebe 'nome_categoria' (string)
def rodar_analise_q1(_analisador, nome_categoria, n_semanas):
    """Executa a análise da Questão 1 (Previsão)."""
    try:
        # MODIFICAÇÃO: Chama a função 'analisar_previsao_categoria'
        df_plot, mse, mae, mape, erro = _analisador.analisar_previsao_categoria(nome_categoria, n_semanas)
        
        if erro:
            return {'df_plot': None, 'mse': None, 'mae': None, 'mape': None, 'erro': erro}
        
        return {'df_plot': df_plot, 'mse': mse, 'mae': mae, 'mape': mape, 'erro': None}

    except Exception as e:
        return {'df_plot': None, 'mse': None, 'mae': None, 'mape': None, 'erro': f"Erro inesperado na análise Q1: {e}"}

@st.cache_data
def rodar_analise_q2(_analisador, produto_id, estab_a_id, estab_b_id, max_lag):
    """Executa a análise da Questão 2 (Liderança de Preço). (Sem alteração)"""
    try:
        dados_pares_plot, ccf_df, p_A_causa_B, p_B_causa_A, erro = \
            _analisador.analisar_lideranca_preco(produto_id, estab_a_id, estab_b_id, max_lag)
        
        if erro:
            return {'erro': erro}
            
        return {
            'dados_pares_plot': dados_pares_plot,
            'ccf_df': ccf_df,
            'p_A_causa_B': p_A_causa_B,
            'p_B_causa_A': p_B_causa_A,
            'erro': None
        }
    except Exception as e:
        return {'erro': f"Erro inesperado na análise Q2: {e}"}

# --- INÍCIO DO APLICATIVO ---

# Carrega mapas de PRODUTO e ESTAB (necessários para Q2)
mapa_produto, mapa_estab, mapa_id_para_produto, mapa_id_para_estab = carregar_mapas()

try:
    analisador = AnalisadorCestaBasicaPro(DATA_FILE)
except Exception as e:
    st.error(f"Erro ao inicializar o Analisador: {e}")
    st.info(f"Verifique se o arquivo '{DATA_FILE}' existe e está correto.")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---

st.sidebar.title("Painel de Controle")
st.sidebar.info("Navegue pelas análises usando os botões abaixo.")

pagina = st.sidebar.radio(
    "Selecione a Análise:",
    ("Visão Geral", "Questão 1: Previsão de Preços", "Questão 2: Liderança de Preços"),
    label_visibility="collapsed"
)

# --- PÁGINA 1: VISÃO GERAL ---
if pagina == "Visão Geral":
    st.title("Visão Geral da Cesta Básica")
    st.write("Visualização dos dados limpos e mapeados.")
    
    df_raw = load_data(DATA_FILE)
    
    st.subheader("Visualização dos Dados Limpos (Amostra)")
    st.dataframe(df_raw.head())
    
    st.info(f"Total de {len(df_raw)} registros carregados.")
    
    df_display = df_raw.copy()
    df_display['Produto'] = df_display['Produto'].map(mapa_id_para_produto).fillna('ID Desconhecido')
    df_display['Estabelecimento'] = df_display['Estabelecimento'].map(mapa_id_para_estab).fillna('ID Desconhecido')
    
    st.subheader("Dados Mapeados (Amostra)")
    st.dataframe(df_display.head())
    
# --- PÁGINA 2: QUESTÃO 1 (Previsão) ---
elif pagina == "Questão 1: Previsão de Preços":
    st.title("Questão 1: Previsão de Preços Futuros por Categoria")
    st.write("""
    Esta análise avalia a previsibilidade dos preços de uma categoria da cesta básica.
    O objetivo é criar um modelo de machine learning (Random Forest) para prever o preço
    médio para as próximas semanas com um **Erro Percentual Médio (MAPE) inferior a 10%**.
    """)

    # Filtros Q1
    st.sidebar.subheader("Filtros - Questão 1")
    
    # MODIFICAÇÃO: Filtro usa a LISTA_CATEGORIAS
    categoria_nome_q1 = st.sidebar.selectbox(
        "Selecione a Categoria:",
        LISTA_CATEGORIAS, # Usa a lista de strings
        key='cat_q1',
        help="Análise do preço médio de todos os itens desta categoria."
    )
    
    n_semanas_q1 = st.sidebar.slider("Semanas para Previsão (Teste):", 4, 24, 8, key='sem_q1')

    if st.sidebar.button("Rodar Previsão", type="primary", key='btn_q1'):
        # MODIFICAÇÃO: Passa o 'nome_categoria' (string) para a análise
        resultados_q1 = rodar_analise_q1(analisador, categoria_nome_q1, n_semanas_q1)
        st.session_state.resultados_q1 = resultados_q1
        st.session_state.categoria_nome_q1 = categoria_nome_q1 # Salva o nome da categoria
    
    # Exibição de Resultados Q1
    if 'resultados_q1' in st.session_state:
        resultados_q1 = st.session_state.resultados_q1
        # MODIFICAÇÃO: Recupera o nome da categoria
        categoria_nome_q1 = st.session_state.categoria_nome_q1 

        if resultados_q1['erro']:
            st.error(resultados_q1['erro'])
        else:
            # MODIFICAÇÃO: Exibe o nome da categoria
            st.subheader(f"Resultados da Previsão para: {categoria_nome_q1}")
            
            fig_q1 = plot_previsao_q1(resultados_q1['df_plot'])
            st.plotly_chart(fig_q1, use_container_width=True)
            
            st.subheader("Métricas de Erro do Modelo (em semanas de teste)")
            col1, col2, col3 = st.columns(3)
            col1.metric("Mean Squared Error (MSE)", f"{resultados_q1['mse']:.4f}")
            col2.metric("Mean Absolute Error (MAE)", f"{resultados_q1['mae']:.4f}")
            
            mape_percent = resultados_q1['mape'] * 100
            objetivo_atingido = " (Atingido ✅)" if mape_percent < 10 else " (Não Atingido ❌)"
            
            col3.metric(
                f"MAPE (Objetivo: < 10%)",
                f"{mape_percent:.2f} %",
                help=f"O objetivo do relatório era um MAPE < 10%.{objetivo_atingido}"
            )


# --- PÁGINA 3: QUESTÃO 2 (Liderança) ---
elif pagina == "Questão 2: Liderança de Preços":
    st.title("Questão 2: Análise de Liderança de Preços")
    st.write("""
    Esta análise investiga qual mercado "lidera" ou "puxa" o preço de outro para um item específico.
    Utilizamos duas técnicas (conforme Abordagem 1 do relatório):
    1.  **Causalidade de Granger:** Testa estatisticamente se a série de preços do Mercado A é útil para prever a série do Mercado B (e vice-versa).
    2.  **Cross-Correlation (CCF):** Mede a semelhança entre as duas séries em diferentes "atrasos" (lags), mostrando quem se move primeiro e por quantas semanas.
    """)

    # Filtros Q2 (Sem alteração, usa mapa_produto)
    st.sidebar.subheader("Filtros - Questão 2")
    
    nomes_produtos_ordenados_q2 = sorted(mapa_produto.keys())
    produto_nome_q2 = st.sidebar.selectbox(
        "Selecione o Produto (Item Específico):",
        nomes_produtos_ordenados_q2,
        key='prod_q2'
    )
    prod_q2_id = mapa_produto[produto_nome_q2]
    
    nomes_estab_ordenados = sorted(mapa_estab.keys())
    
    estab_A_nome = st.sidebar.selectbox(
        "Mercado 'Líder' (A):",
        nomes_estab_ordenados,
        index=0, 
        key='estab_A'
    )
    estab_A_id = mapa_estab[estab_A_nome]

    estab_B_nome = st.sidebar.selectbox(
        "Mercado 'Seguidor' (B):",
        nomes_estab_ordenados,
        index=1, 
        key='estab_B'
    )
    estab_B_id = mapa_estab[estab_B_nome]
    
    max_lag_q2 = st.sidebar.slider("Atraso Máximo (Semanas):", 2, 12, 8, key='lag_q2')

    if estab_A_id == estab_B_id:
        st.sidebar.error("Selecione dois mercados diferentes.")
    elif st.sidebar.button("Rodar Análise de Liderança", type="primary", key='btn_q2'):
        resultados_q2 = rodar_analise_q2(
            analisador,
            prod_q2_id,
            estab_A_id,
            estab_B_id,
            max_lag_q2
        )
        st.session_state.resultados_q2 = resultados_q2
        st.session_state.q2_nomes = {
            'produto': produto_nome_q2,
            'estab_A': estab_A_nome,
            'estab_B': estab_B_nome
        }
        
    # Exibição de Resultados Q2
    if 'resultados_q2' in st.session_state:
        resultados_q2 = st.session_state.resultados_q2
        nomes = st.session_state.q2_nomes 
        
        if resultados_q2['erro']:
            st.error(resultados_q2['erro'])
        else:
            st.subheader(f"Resultados da Análise para: {nomes['produto']}")
            
            df_plot_q2 = resultados_q2['dados_pares_plot'].rename(columns={
                str(estab_A_id): nomes['estab_A'], 
                str(estab_B_id): nomes['estab_B']
            })

            fig_series_q2 = plot_series_q2(df_plot_q2, nomes['estab_A'], nomes['estab_B'])
            st.plotly_chart(fig_series_q2, use_container_width=True)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Análise de Causalidade (Granger)")
                st.caption(f"Verifica se '{nomes['estab_A']}' estatisticamente 'puxa' '{nomes['estab_B']}' (e vice-versa).")
                
                p_A_B = resultados_q2['p_A_causa_B']
                p_B_A = resultados_q2['p_B_causa_A']
                
                valor_A_B = "Sim ✅" if p_A_B < 0.05 else "Não ❌"
                st.metric(
                    label=f"Mercado '{nomes['estab_A']}' puxa o preço de '{nomes['estab_B']}'?",
                    value=valor_A_B,
                    help=f"Teste de Causalidade de Granger (p-valor={p_A_B:.4f}). Se p-valor < 0.05, consideramos 'Sim'."
                )
                
                valor_B_A = "Sim ✅" if p_B_A < 0.05 else "Não ❌"
                st.metric(
                    label=f"Mercado '{nomes['estab_B']}' puxa o preço de '{nomes['estab_A']}'?",
                    value=valor_B_A,
                    help=f"Teste de Causalidade de Granger (p-valor={p_B_A:.4f}). Se p-valor < 0.05, consideramos 'Sim'."
                )

            with col2:
                st.subheader("Análise de Atraso (Cross-Correlation)")
                st.caption("Se um mercado puxa o outro, quantas semanas ele demora?")
                
                fig_ccf_q2 = plot_ccf_q2(resultados_q2['ccf_df'])
                st.plotly_chart(fig_ccf_q2, use_container_width=True)
                
                max_corr_lag = resultados_q2['ccf_df']['CCF'].abs().idxmax()
                max_lag_val = resultados_q2['ccf_df'].loc[max_corr_lag, 'Lag']
                
                st.metric(
                    label="Atraso de Maior Impacto:",
                    value=f"{max_lag_val} semanas"
                )