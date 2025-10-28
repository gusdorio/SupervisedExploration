import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

diretorio_atual = os.path.dirname(__file__)  # Diretório de dashboard.py
caminho = os.path.join(diretorio_atual, '..', 'data', 'ICB_2s-2025.xlsx')
DATA_PATH = caminho

# Dicionário de categorização de produtos, conforme o notebook
product_classes = {
    'Vegetais': ['Tomate', 'Banana Prata', 'Banana Nanica', 'Batata'],
    'Carnes Vermelhas': ['Carne Bovina Acém', 'Carne Bovina Coxão Mole',
                         'Carne Suína Pernil'],
    'Aves': ['Frango Peito', 'Frango Sobrecoxa', 'Carne Pernil'],
    'Laticínios': ['Manteiga', 'Leite'],
    'Padaria & Cozinha': ['Pão', 'Ovo', 'Farinha de Trigo', 'Café', 'Açúcar', 'Óleo'],
    'Grãos & Massas': ['Arroz', 'Feijão', 'Macarrão'],
}
prod_to_class = {prod: cls for cls, prods in product_classes.items() for prod in prods}

# --- Layout do Aplicativo Streamlit ---
st.set_page_config(layout="wide", page_title="Análise Estatística de Cestas Básicas")

st.title("📊 Análise Estatística de Cestas Básicas")
st.markdown("Este dashboard apresenta uma análise dos preços de produtos de cestas básicas, permitindo a filtragem por tipo de produto, marca, classe e estabelecimento.")

# Carrega os dados (com cache para performance)
df = load_and_clean_data(DATA_PATH)

# Barra lateral para filtros
st.sidebar.header("Filtros")

# Filtro por Classe (Categoria de Produto) - "tipo"
all_classes = ['Todos'] + sorted(df['Classe'].unique().tolist())
selected_classes = st.sidebar.multiselect(
    "Selecione a Classe do Produto (Tipo):",
    options=all_classes,
    default='Todos'
)

# Filtro por Produto (Tipo de Produto) - dinâmico com base nas classes selecionadas
if 'Todos' in selected_classes:
    products_in_selected_classes = df['Produto'].unique().tolist()
else:
    products_in_selected_classes = df[df['Classe'].isin(selected_classes)]['Produto'].unique().tolist()

all_products = ['Todos'] + sorted(products_in_selected_classes)
selected_products = st.sidebar.multiselect(
    "Selecione o Produto:",
    options=all_products,
    default='Todos'
)

# Filtro por Estabelecimento
all_establishments = ['Todos'] + sorted(df['Estabelecimento'].unique().tolist())
selected_establishments = st.sidebar.multiselect(
    "Selecione o Estabelecimento:",
    options=all_establishments,
    default='Todos'
)

# Filtro por Marca - dinâmico com base nos produtos, classes e estabelecimentos selecionados
# Primeiro, filtra o DataFrame com base nas seleções para obter as marcas disponíveis
filtered_for_brands = df.copy()
if 'Todos' not in selected_classes:
   filtered_for_brands = filtered_for_brands[filtered_for_brands['Classe'].isin(selected_classes)]
if 'Todos' not in selected_products:
    filtered_for_brands = filtered_for_brands[filtered_for_brands['Produto'].isin(selected_products)]
if 'Todos' not in selected_establishments:
    filtered_for_brands = filtered_for_brands[filtered_for_brands['Estabelecimento'].isin(selected_establishments)]

all_brands = ['Todos'] + sorted(filtered_for_brands['Marca'].unique().tolist())
selected_brands = st.sidebar.multiselect(
    "Selecione a Marca:",
    options=all_brands,
    default='Todos'
)

# Aplica todos os filtros ao DataFrame principal
filtered_df = df.copy()

if 'Todos' not in selected_classes:
    filtered_df = filtered_df[filtered_df['Classe'].isin(selected_classes)]
if 'Todos' not in selected_products:
    filtered_df = filtered_df[filtered_df['Produto'].isin(selected_products)]
if 'Todos' not in selected_establishments:
    filtered_df = filtered_df[filtered_df['Estabelecimento'].isin(selected_establishments)]
if 'Todos' not in selected_brands:
    filtered_df = filtered_df[filtered_df['Marca'].isin(selected_brands)]

st.subheader("Dados Filtrados")
if not filtered_df.empty:
    st.dataframe(filtered_df)

    st.subheader("Estatísticas Descritivas dos Dados Filtrados")
    st.write(filtered_df.describe())

    # --- Visualizações ---
    st.subheader("Visualizações")

    # Distribuição do Preço por Kilo/Unidade (PPK)
    if 'PPK' in filtered_df.columns and not filtered_df['PPK'].isnull().all():
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        sns.histplot(filtered_df['PPK'], kde=True, ax=ax1)
        ax1.set_title('Distribuição do Preço por Kilo/Unidade (PPK)')
        ax1.set_xlabel('PPK')
        ax1.set_ylabel('Frequência')
        st.pyplot(fig1)
        plt.close(fig1) # Fecha a figura para liberar memória

    # PPK Médio por Produto (Top 10)
    if 'PPK' in filtered_df.columns and 'Produto' in filtered_df.columns and not filtered_df.empty:
        if filtered_df['Produto'].nunique() > 0:
            avg_ppk_by_product = filtered_df.groupby('Produto')['PPK'].mean().sort_values(ascending=False).head(10)
            if not avg_ppk_by_product.empty:
                fig2, ax2 = plt.subplots(figsize=(12, 7))
                sns.barplot(x=avg_ppk_by_product.index, y=avg_ppk_by_product.values, ax=ax2, palette='viridis')
                ax2.set_title('Top 10 Produtos por Preço Médio por Kilo/Unidade (PPK)')
                ax2.set_xlabel('Produto')
                ax2.set_ylabel('PPK Médio')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                st.pyplot(fig2)
                plt.close(fig2) # Fecha a figura para liberar memória
            else:
                st.info("Não há dados suficientes para exibir o PPK médio por produto.")
        else:
            st.info("Não há produtos selecionados para exibir o PPK médio.")
    else:
        st.info("Não há dados suficientes para exibir o PPK médio por produto.")

    # PPK Médio por Estabelecimento (se houver mais de um estabelecimento)
    if 'PPK' in filtered_df.columns and 'Estabelecimento' in filtered_df.columns and not filtered_df.empty:
        if filtered_df['Estabelecimento'].nunique() > 1:
            avg_ppk_by_estab = filtered_df.groupby('Estabelecimento')['PPK'].mean().sort_values(ascending=False)
            if not avg_ppk_by_estab.empty:
                fig3, ax3 = plt.subplots(figsize=(12, 7))
                sns.barplot(x=avg_ppk_by_estab.index, y=avg_ppk_by_estab.values, ax=ax3, palette='magma')
                ax3.set_title('Preço Médio por Kilo/Unidade (PPK) por Estabelecimento')
                ax3.set_xlabel('Estabelecimento')
                ax3.set_ylabel('PPK Médio')
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                st.pyplot(fig3)
                plt.close(fig3) # Fecha a figura para liberar memória
            else:
                st.info("Não há dados suficientes para exibir o PPK médio por estabelecimento.")
        elif filtered_df['Estabelecimento'].nunique() == 1:
            st.info(f"Apenas um estabelecimento selecionado ({filtered_df['Estabelecimento'].iloc[0]}). Gráfico de comparação não disponível.")
        else:
            st.info("Não há estabelecimentos selecionados para exibir o PPK médio.")
    else:
        st.info("Não há dados suficientes para exibir o PPK médio por estabelecimento.")