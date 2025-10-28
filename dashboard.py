import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
import warnings

# Ignorar avisos para uma interface mais limpa
warnings.simplefilter(action='ignore', category=FutureWarning)

# Configurações do Aplicativo
ARQUIVO_DADOS = "./data/dados_limpos_ICB.xlsx"

HORIZONTE_PREVISAO_DIAS = 180  # 6 meses

# Configuração da página do Streamlit
st.set_page_config(layout="wide", page_title="Previsão de Preços e Otimização")

@st.cache_data(show_spinner="Carregando e processando dados históricos...")
def carregar_dados(arquivo):
    """Carrega, limpa e renomeia os dados do XLSX."""
    try:
        df = pd.read_excel(arquivo)
        
    except FileNotFoundError:
        st.error(f"ERRO: Arquivo '{arquivo}' não encontrado. Verifique se o nome está correto e se ele está na pasta 'data'.")
        return None
    except Exception as e:
        st.error(f"ERRO ao ler o arquivo Excel: {e}")
        st.info("Lembre-se de instalar o 'openpyxl'. Use: pip install openpyxl")
        return None
    
    # Renomear colunas para o padrão do nosso script
    colunas_map = {
        'Data_Coleta': 'data_coleta',
        'Estabelecimento': 'estabelecimento',
        'Produto': 'produto',
        'Preco': 'preco_produto'
    }
    df = df.rename(columns=colunas_map)
    
    colunas_necessarias = ['data_coleta', 'estabelecimento', 'produto', 'preco_produto']
    if not all(col in df.columns for col in colunas_necessarias):
        st.error(f"ERRO: O .xlsx deve conter as colunas: Data_Coleta, Estabelecimento, Produto, Preco")
        return None

    # Limpeza de dados
    df = df.dropna(subset=['preco_produto'])
    df = df[pd.to_numeric(df['preco_produto'], errors='coerce').notnull()]
    df['preco_produto'] = df['preco_produto'].astype(float)
    
    df['data_coleta'] = pd.to_datetime(df['data_coleta'])
    df = df.sort_values(by='data_coleta')
    return df

def criar_features_temporais(df):
    """Cria features de data para o modelo."""
    df_feat = df.copy()
    df_feat['mes'] = df_feat['data_coleta'].dt.month
    df_feat['dia_da_semana'] = df_feat['data_coleta'].dt.dayofweek
    df_feat['dia_do_ano'] = df_feat['data_coleta'].dt.dayofyear
    df_feat['semana_do_ano'] = df_feat['data_coleta'].dt.isocalendar().week.astype(int)
    return df_feat

@st.cache_data(show_spinner="Treinando modelos e gerando previsões para 6 meses...")
def treinar_e_prever_tudo(df_historico):
    """
    Função principal que treina o modelo com todos os dados históricos
    e gera previsões para todos os produtos/estabelecimentos.
    """
    
    df_features = criar_features_temporais(df_historico)
    
    features_categoricas = ['produto', 'estabelecimento']
    features_numericas = ['mes', 'dia_da_semana', 'dia_do_ano', 'semana_do_ano']
    target = 'preco_produto'

    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    
    X_cat = pd.DataFrame(
        encoder.fit_transform(df_features[features_categoricas]),
        columns=encoder.get_feature_names_out()
    )
    X_num = df_features[features_numericas].reset_index(drop=True)
    X = pd.concat([X_num, X_cat], axis=1)
    y = df_features[target].reset_index(drop=True)

    model_final = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1, min_samples_leaf=5)
    model_final.fit(X, y)
    
    data_inicio_futuro = df_historico['data_coleta'].max() + pd.DateOffset(days=1)
    datas_futuras = pd.date_range(start=data_inicio_futuro, periods=HORIZONTE_PREVISAO_DIAS, freq='D')
    
    produtos_unicos = df_historico['produto'].unique()
    estabelecimentos_unicos = df_historico['estabelecimento'].unique()
    
    df_futuro = pd.DataFrame(
        list(pd.MultiIndex.from_product(
            [datas_futuras, produtos_unicos, estabelecimentos_unicos], 
            names=['data_coleta', 'produto', 'estabelecimento']
        ).to_flat_index()),
        columns=['data_coleta', 'produto', 'estabelecimento']
    )

    df_futuro_features = criar_features_temporais(df_futuro)
    
    X_cat_futuro = pd.DataFrame(
        encoder.transform(df_futuro_features[['produto', 'estabelecimento']]),
        columns=encoder.get_feature_names_out()
    )
    X_num_futuro = df_futuro_features[features_numericas].reset_index(drop=True)
    X_futuro = pd.concat([X_num_futuro, X_cat_futuro], axis=1)
    X_futuro = X_futuro.reindex(columns=X.columns, fill_value=0)
    
    previsoes = model_final.predict(X_futuro)
    df_futuro['preco_previsto'] = previsoes
    
    return df_futuro

# --- Interface do Dashboard ---

st.title("Dashboard de Previsão de Preços e Otimização de Compras 🛒")
st.markdown(f"Analisando dados históricos de `{ARQUIVO_DADOS}` e prevendo os próximos {HORIZONTE_PREVISAO_DIAS} dias.")

# Carregar dados
df_historico = carregar_dados(ARQUIVO_DADOS)

if df_historico is not None:
    produtos_unicos = sorted(df_historico['produto'].unique())
    
    # --- Barra Lateral (Controles) ---
    st.sidebar.header("Definições de Análise")
    
    # Seletor da Questão 2A (Produto Único)
    st.sidebar.subheader("Questão A: Produto Único")
    produto_unico_selecionado = st.sidebar.selectbox(
        "Selecione um Produto",
        produtos_unicos,
        index=0
    )
    
    # Seletor da Questão 2B (Cesta Básica)
    st.sidebar.subheader("Questão B: Cesta Básica")
    default_cesta = list(produtos_unicos[:5]) if len(produtos_unicos) >= 5 else list(produtos_unicos)
    produtos_cesta_selecionados = st.sidebar.multiselect(
        "Selecione os produtos da Cesta",
        produtos_unicos,
        default=default_cesta
    )
    
    # Botão para iniciar a análise
    if st.sidebar.button("Gerar Previsões e Análises"):
        
        # 1. Chamar a função principal de ML (usará o cache se já tiver rodado)
        df_previsoes = treinar_e_prever_tudo(df_historico)
        
        st.success("Previsões e análises concluídas!")
    
        col1, col2 = st.columns(2)
  
        with col1:
            st.header(f"Análise: {produto_unico_selecionado}")
            
            # 1a. Recomendação de melhor local
            st.subheader("Melhor Estabelecimento (Previsão)")
            df_produto = df_previsoes[df_previsoes['produto'] == produto_unico_selecionado]
            idx_melhor_local_produto = df_produto.groupby('data_coleta')['preco_previsto'].idxmin()
            df_recomendacao_produto = df_produto.loc[idx_melhor_local_produto].copy()
            df_recomendacao_produto['preco_previsto'] = df_recomendacao_produto['preco_previsto'].round(2)
            st.dataframe(
                df_recomendacao_produto[['data_coleta', 'estabelecimento', 'preco_previsto']].head(15),
                use_container_width=True
            )
            
            # 1b. Gráfico de Previsão de Preço
            st.subheader("Previsão de Preço (Próximos 6 meses)")
            fig_pred_prod = px.line(
                df_produto, 
                x='data_coleta', 
                y='preco_previsto', 
                color='estabelecimento', 
                title=f"Previsão de Preço para {produto_unico_selecionado}"
            )
            st.plotly_chart(fig_pred_prod, use_container_width=True)
            
            # 1c. Gráfico Histórico de Preço
            st.subheader("Histórico de Preço")
            df_hist_prod = df_historico[df_historico['produto'] == produto_unico_selecionado]
            fig_hist_prod = px.line(
                df_hist_prod, 
                x='data_coleta', 
                y='preco_produto', 
                color='estabelecimento', 
                title=f"Histórico de Preço para {produto_unico_selecionado}"
            )
            st.plotly_chart(fig_hist_prod, use_container_width=True)

        # --- Coluna 2: Análise da Cesta Básica ---
        with col2:
            st.header("Análise: Cesta Básica")
            
            if not produtos_cesta_selecionados:
                st.warning("Por favor, selecione ao menos um produto para a cesta.")
            else:
                # 2a. Recomendação de melhor local para a cesta
                st.subheader("Melhor Estabelecimento (Previsão)")
                df_cesta = df_previsoes[df_previsoes['produto'].isin(produtos_cesta_selecionados)]
                df_custo_cesta = df_cesta.groupby(
                    ['data_coleta', 'estabelecimento']
                )['preco_previsto'].sum().reset_index(name='custo_cesta_previsto')
                
                idx_melhor_local_cesta = df_custo_cesta.groupby('data_coleta')['custo_cesta_previsto'].idxmin()
                df_recomendacao_cesta = df_custo_cesta.loc[idx_melhor_local_cesta].copy()
                df_recomendacao_cesta['custo_cesta_previsto'] = df_recomendacao_cesta['custo_cesta_previsto'].round(2)
                st.dataframe(
                    df_recomendacao_cesta[['data_coleta', 'estabelecimento', 'custo_cesta_previsto']].head(15),
                    use_container_width=True
                )
                
                # 2b. Gráfico de Previsão de Custo da Cesta
                st.subheader("Previsão do Custo da Cesta (Próximos 6 meses)")
                fig_pred_cesta = px.line(
                    df_custo_cesta, 
                    x='data_coleta', 
                    y='custo_cesta_previsto', 
                    color='estabelecimento', 
                    title="Custo Previsto da Cesta por Estabelecimento"
                )
                st.plotly_chart(fig_pred_cesta, use_container_width=True)
                
                # 2c. Lista de produtos na cesta
                st.subheader("Produtos na Cesta:")
                st.info(", ".join(produtos_cesta_selecionados))

    else:
        st.info("Clique no botão 'Gerar Previsões e Análises' na barra lateral para iniciar.")

else:
    st.warning("Não foi possível carregar os dados. Verifique o console de erro.")