import streamlit as st
import pandas as pd
import io
from contextlib import redirect_stdout

# --- Importar a classe do arquivo local ---
try:
    # Importa a classe do arquivo algotithms.py
    from classes.algotithms import AnalisadorCestaBasicaPro
except ImportError:
    st.error("Erro: Não foi possível encontrar o arquivo 'algotithms.py'. "
             "Certifique-se de que ele está na mesma pasta que este script 'app.py'.")
    st.stop()
except Exception as e:
    st.error(f"Erro ao importar 'algotithms.py': {e}. "
             "Verifique se o arquivo da classe não contém erros.")
    st.stop()

# Nome do arquivo de dados
DATA_FILE = "./data/dados_limpos_ICB.xlsx"

# --- Carregamento da Classe (Cache) ---
# @st.cache_resource garante que a classe seja carregada apenas uma vez.
@st.cache_resource
def carregar_analisador(filepath):
    """
    Carrega a classe AnalisadorCestaBasicaPro com o arquivo de dados.
    """
    try:
        analisador = AnalisadorCestaBasicaPro(filepath)
        if analisador.dados_brutos is None:
            raise ValueError("Os dados não foram carregados corretamente pela classe.")
        st.success("Analisador e dados carregados com sucesso!")
        return analisador
    except FileNotFoundError:
        st.error(f"Erro: Arquivo de dados '{filepath}' não encontrado. "
                 "Certifique-se de que ele está na mesma pasta do script.")
        return None
    except Exception as e:
        st.error(f"Erro ao instanciar AnalisadorCestaBasicaPro: {e}. "
                 "Verifique se a classe em 'algotithms.py' está correta e "
                 "consegue ler arquivos CSV.")
        return None

# Extração de Filtros (Cache)
@st.cache_data
def extrair_filtros(_analisador):
    """
    Extrai listas únicas para os filtros a partir dos dados brutos na classe.
    """
    dados = _analisador.dados_brutos
    classes = sorted([col for col in dados.columns if col.startswith('Classe_')])
    estabelecimentos = sorted(dados['Estabelecimento'].unique().tolist())
    produtos = sorted(dados['Produto'].unique().tolist())
    return classes, estabelecimentos, produtos

# Título e Carregamento
st.set_page_config(layout="wide", page_title="Análise Cesta Básica")
st.title("Dashboard de Análise de Preços 🛒")

analisador = carregar_analisador(DATA_FILE)

# Se o carregamento falhar, para a execução do app
if not analisador:
    st.stop()

# Extrai as listas para os filtros
classes, estabelecimentos, produtos = extrair_filtros(analisador)

# BARRA LATERAL (FILTROS)
st.sidebar.title("Painel de Controle 🎛️")
pagina = st.sidebar.radio(
    "Selecione a Análise:",
    ("Questão 1: Previsão de Preços", "Questão 2: Liderança de Preços", "Explorar Dados")
)
st.sidebar.markdown("---")

# PÁGINA 1: QUESTÃO 1 (PREVISÃO)
if pagina == "Questão 1: Previsão de Preços":
    st.header("Questão 1: Previsão de Preços Futuros por Categoria")
    st.info("Esta análise chama o método `analisar_previsao_preco_ml` da sua classe.")

    # Filtros para Questão 1
    st.sidebar.subheader("Filtros - Questão 1")
    classe_q1 = st.sidebar.selectbox("Selecione a Classe:", classes)
    
    st.sidebar.markdown("**Parâmetros do Algoritmo:**")
    n_lags_q1 = st.sidebar.slider("Nº de Lags (semanas):", min_value=1, max_value=12, value=4)
    test_size_q1 = st.sidebar.slider("Semanas para Teste:", min_value=4, max_value=26, value=12)
    
    # Botão de Execução
    if st.button("Rodar Análise da Questão 1", type="primary"):
        # Captura a saída (print) da classe
        f = io.StringIO()
        with st.spinner("Rodando análise... (chamando a classe)"):
            with redirect_stdout(f):
                analisador.analisar_previsao_preco_ml(
                    categoria_col=classe_q1,
                    freq='W-MON',  # Frequência definida na classe
                    n_lags=n_lags_q1,
                    test_size_semanas=test_size_q1
                )
        resultados = f.getvalue()
        
        st.subheader("Resultados da Análise (Saída do Console)")
        st.code(resultados, language=None) # Exibe o texto puro que seria impresso

# PÁGINA 2: QUESTÃO 2 (LIDERANÇA)
elif pagina == "Questão 2: Liderança de Preços":
    st.header("Questão 2: Análise de Liderança de Preço")
    st.info("Esta análise chama o método `analisar_lideranca_preco` da sua classe.")

    # Filtros para Questão 2
    st.sidebar.subheader("Filtros - Questão 2")
    prod_q2 = st.sidebar.selectbox("Selecione o Produto:", produtos)
    estab_A = st.sidebar.selectbox("Selecione o Mercado A:", estabelecimentos, index=0)
    estab_B = st.sidebar.selectbox("Selecione o Mercado B:", estabelecimentos, index=1)
    
    st.sidebar.markdown("**Parâmetros do Algoritmo:**")
    max_lag_q2 = st.sidebar.slider("Lag Máximo (semanas):", min_value=2, max_value=12, value=8)
    
    if estab_A == estab_B:
        st.sidebar.error("Selecione dois estabelecimentos diferentes.")
    elif st.button("Rodar Análise da Questão 2", type="primary"):
        # Captura a saída (print) da classe
        f = io.StringIO()
        with st.spinner("Rodando análise... (chamando a classe)"):
            with redirect_stdout(f):
                analisador.analisar_lideranca_preco(
                    produto_id=prod_q2,
                    estab_A=estab_A,
                    estab_B=estab_B,
                    freq='W-MON', # Frequência definida na classe
                    max_lag=max_lag_q2
                )
        resultados = f.getvalue()
        
        st.subheader("Resultados da Análise (Saída do Console)")
        st.code(resultados, language=None) # Exibe o texto puro

# PÁGINA 3: EXPLORAR DADOS
elif pagina == "Explorar Dados":
    st.header("Exploração dos Dados Brutos")
    st.info("Visualização dos dados contidos em `analisador.dados_brutos`.")

    # Filtros de Exploração
    st.sidebar.subheader("Filtros de Exploração")
    estab_filt = st.sidebar.multiselect("Filtrar Estabelecimentos:", estabelecimentos, default=estabelecimentos)
    classe_filt = st.sidebar.multiselect("Filtrar Classes:", classes, default=classes)
    
    # Lógica de filtragem
    dados_filtrados = analisador.dados_brutos[
        analisador.dados_brutos['Estabelecimento'].isin(estab_filt)
    ]
    if classes != classe_filt: # Só filtra se o usuário mudou a seleção
        dados_filtrados = dados_filtrados[
            dados_filtrados[classe_filt].any(axis=1)
        ]
    
    st.metric("Linhas Filtradas", f"{len(dados_filtrados):,}")
    st.dataframe(dados_filtrados)