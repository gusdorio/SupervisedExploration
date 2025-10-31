import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from scipy import stats
from typing import Dict, List, Optional, Union, Tuple
import warnings
import json
import os

warnings.filterwarnings('ignore')


class DataCleaner:
    """
    Classe para limpeza automática e inteligente de datasets.
    Realiza preenchimento de valores nulos, tratamento de outliers,
    codificação de variáveis e normalização de dados.
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Inicializa o DataCleaner com um DataFrame.
        
        Args:
            df: DataFrame pandas a ser limpo
        """
        self.df = df.copy()
        self.original_df = df.copy()
        self.numeric_cols = []
        self.categorical_cols = []
        self.datetime_cols = []
        self.cleaning_report = {}
        self.label_mappings = {} # <-- MODIFICAÇÃO 1: Inicializa o atributo
        
    def analyze_data(self) -> Dict:
        """
        Analisa o dataset e identifica tipos de colunas.
        
        Returns:
            Dicionário com análise detalhada dos dados
        """
        print("Analisando estrutura dos dados")
        
        # Identifica tipos de colunas
        self.numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()
        self.datetime_cols = self.df.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Análise de valores ausentes
        missing_info = {
            col: {
                'count': self.df[col].isnull().sum(),
                'percentage': (self.df[col].isnull().sum() / len(self.df)) * 100
            }
            for col in self.df.columns if self.df[col].isnull().sum() > 0
        }
        
        analysis = {
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'numeric_columns': len(self.numeric_cols),
            'categorical_columns': len(self.categorical_cols),
            'datetime_columns': len(self.datetime_cols),
            'missing_values': missing_info,
            'duplicated_rows': self.df.duplicated().sum()
        }
        
        self._print_analysis(analysis)
        return analysis
    
    def _print_analysis(self, analysis: Dict):
        """Imprime análise de forma organizada."""
        print(f"\nTotal de linhas: {analysis['total_rows']}")
        print(f"Total de colunas: {analysis['total_columns']}")
        print(f"   - Numéricas: {analysis['numeric_columns']}")
        print(f"   - Categóricas: {analysis['categorical_columns']}")
        print(f"   - Data/Hora: {analysis['datetime_columns']}")
        print(f"Linhas duplicadas: {analysis['duplicated_rows']}")
        
        if analysis['missing_values']:
            print(f"\nValores ausentes encontrados em {len(analysis['missing_values'])} colunas:")
            for col, info in list(analysis['missing_values'].items())[:10]:
                print(f"   - {col}: {info['count']} ({info['percentage']:.2f}%)")
    
    def remove_duplicates(self, subset: Optional[List[str]] = None, keep: str = 'first') -> 'DataCleaner':
        """
        Remove linhas duplicadas do dataset.
        
        Args:
            subset: Lista de colunas para considerar na duplicação
            keep: 'first', 'last' ou False
        
        Returns:
            Self para encadeamento de métodos
        """
        initial_rows = len(self.df)
        self.df = self.df.drop_duplicates(subset=subset, keep=keep)
        removed = initial_rows - len(self.df)
        
        if removed > 0:
            print(f"Removidas {removed} linhas duplicadas")
            self.cleaning_report['duplicates_removed'] = removed
        
        return self
    
    def handle_missing_values(self, 
                            numeric_strategy: str = 'auto',
                            categorical_strategy: str = 'mode',
                            threshold: float = 0.5) -> 'DataCleaner':
        """
        Trata valores ausentes de forma inteligente.
        
        Args:
            numeric_strategy: 'mean', 'median', 'knn', 'auto'
            categorical_strategy: 'mode', 'constant'
            threshold: Remove colunas com mais de X% de valores ausentes
        
        Returns:
            Self para encadeamento de métodos
        """
        print("\nTratando valores ausentes...")
        
        # Remove colunas com muitos valores ausentes
        cols_to_drop = [
            col for col in self.df.columns 
            if self.df[col].isnull().sum() / len(self.df) > threshold
        ]
        
        if cols_to_drop:
            print(f"   Removendo {len(cols_to_drop)} colunas com >{threshold*100}% de valores ausentes")
            self.df = self.df.drop(columns=cols_to_drop)
            self.cleaning_report['columns_dropped'] = cols_to_drop
        
        # Atualiza listas de colunas
        self.numeric_cols = [col for col in self.numeric_cols if col in self.df.columns]
        self.categorical_cols = [col for col in self.categorical_cols if col in self.df.columns]
        
        # Trata colunas numéricas
        if self.numeric_cols:
            self._impute_numeric(numeric_strategy)
        
        # Trata colunas categóricas
        if self.categorical_cols:
            self._impute_categorical(categorical_strategy)
        
        return self
    
    def _impute_numeric(self, strategy: str):
        """Imputa valores ausentes em colunas numéricas."""
        numeric_missing = [col for col in self.numeric_cols if self.df[col].isnull().any()]
        
        if not numeric_missing:
            return
        
        print(f"   Preenchendo {len(numeric_missing)} colunas numéricas...")
        
        if strategy == 'auto':
            # Escolhe estratégia baseada na distribuição
            for col in numeric_missing:
                skewness = abs(self.df[col].skew())
                if skewness > 1:
                    self.df[col].fillna(self.df[col].median(), inplace=True)
                else:
                    self.df[col].fillna(self.df[col].mean(), inplace=True)
        
        elif strategy == 'knn':
            imputer = KNNImputer(n_neighbors=5)
            self.df[numeric_missing] = imputer.fit_transform(self.df[numeric_missing])
        
        elif strategy == 'median':
            self.df[numeric_missing] = self.df[numeric_missing].fillna(self.df[numeric_missing].median())
        
        else:  # mean
            self.df[numeric_missing] = self.df[numeric_missing].fillna(self.df[numeric_missing].mean())
    
    def _impute_categorical(self, strategy: str):
        """Imputa valores ausentes em colunas categóricas."""
        cat_missing = [col for col in self.categorical_cols if self.df[col].isnull().any()]
        
        if not cat_missing:
            return
        
        print(f"   Preenchendo {len(cat_missing)} colunas categóricas...")
        
        if strategy == 'mode':
            for col in cat_missing:
                mode_val = self.df[col].mode()
                if len(mode_val) > 0:
                    self.df[col].fillna(mode_val[0], inplace=True)
                else:
                    self.df[col].fillna('Unknown', inplace=True)
        
        else:  # constant
            self.df[cat_missing] = self.df[cat_missing].fillna('Unknown')
    
    def handle_outliers(self, 
                       method: str = 'iqr',
                       action: str = 'cap',
                       threshold: float = 1.5) -> 'DataCleaner':
        """
        Trata outliers em colunas numéricas.
        
        Args:
            method: 'iqr', 'zscore'
            action: 'cap' (limita), 'remove' (remove linhas)
            threshold: Multiplicador para IQR (padrão 1.5) ou Z-score (padrão 3)
        
        Returns:
            Self para encadeamento de métodos
        """
        print(f"\nTratando outliers (método: {method}, ação: {action})...")
        
        outliers_info = {}
        
        for col in self.numeric_cols:
            if method == 'iqr':
                Q1 = self.df[col].quantile(0.25)
                Q3 = self.df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - threshold * IQR
                upper = Q3 + threshold * IQR
                
                outliers = ((self.df[col] < lower) | (self.df[col] > upper)).sum()
                
                if outliers > 0:
                    outliers_info[col] = outliers
                    
                    if action == 'cap':
                        self.df[col] = self.df[col].clip(lower=lower, upper=upper)
                    elif action == 'remove':
                        self.df = self.df[(self.df[col] >= lower) & (self.df[col] <= upper)]
            
            elif method == 'zscore':
                z_scores = np.abs(stats.zscore(self.df[col].dropna()))
                outliers = (z_scores > threshold).sum()
                
                if outliers > 0:
                    outliers_info[col] = outliers
                    
                    if action == 'remove':
                        self.df = self.df[np.abs(stats.zscore(self.df[col])) <= threshold]
        
        if outliers_info:
            print(f"   Outliers tratados em {len(outliers_info)} colunas")
            self.cleaning_report['outliers'] = outliers_info
        else:
            print("   Nenhum outlier significativo encontrado")
        
        return self
    
    def encode_categorical(self, method: str = 'auto', max_categories: int = 10) -> 'DataCleaner':
        """
        Codifica variáveis categóricas.
        
        Args:
            method: 'auto', 'onehot', 'label'
            max_categories: Número máximo de categorias para one-hot encoding
        
        Returns:
            Self para encadeamento de métodos
        """
        if not self.categorical_cols:
            return self
        
        print(f"\nCodificando variáveis categóricas...")
        
        encoded_info = {}
        
        for col in self.categorical_cols.copy():
            n_categories = self.df[col].nunique()
            
            if method == 'auto':
                if n_categories <= max_categories:
                    # One-hot encoding
                    dummies = pd.get_dummies(self.df[col], prefix=col, drop_first=True)
                    self.df = pd.concat([self.df, dummies], axis=1)
                    self.df = self.df.drop(columns=[col])
                    encoded_info[col] = f'one-hot ({n_categories} categorias)'
                else:
                    # Label encoding
                    le = LabelEncoder()
                    self.df[col] = le.fit_transform(self.df[col].astype(str))
                    encoded_info[col] = f'label ({n_categories} categorias)'
                    
                    # <-- MODIFICAÇÃO 2: Salva o mapa {Nome: ID}
                    self.label_mappings[col] = {name: int(idx) for idx, name in enumerate(le.classes_)}
            
            elif method == 'onehot':
                dummies = pd.get_dummies(self.df[col], prefix=col, drop_first=True)
                self.df = pd.concat([self.df, dummies], axis=1)
                self.df = self.df.drop(columns=[col])
                encoded_info[col] = 'one-hot'
            
            elif method == 'label':
                le = LabelEncoder()
                self.df[col] = le.fit_transform(self.df[col].astype(str))
                encoded_info[col] = 'label'
                
                # <-- MODIFICAÇÃO 3: Salva o mapa {Nome: ID}
                self.label_mappings[col] = {name: int(idx) for idx, name in enumerate(le.classes_)}
        
        if encoded_info:
            print(f"   Codificadas {len(encoded_info)} colunas")
            self.cleaning_report['encoded_columns'] = encoded_info
        
        # Atualiza lista de colunas numéricas
        self.numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        return self
    
    def normalize_data(self, method: str = 'standard') -> 'DataCleaner':
        """
        Normaliza/padroniza colunas numéricas.
        
        Args:
            method: 'standard' (z-score) ou 'minmax'
        
        Returns:
            Self para encadeamento de métodos
        """
        if not self.numeric_cols:
            return self
        
        print(f"\nNormalizando dados (método: {method})...")
        
        if method == 'standard':
            scaler = StandardScaler()
            self.df[self.numeric_cols] = scaler.fit_transform(self.df[self.numeric_cols])
        
        elif method == 'minmax':
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()
            self.df[self.numeric_cols] = scaler.fit_transform(self.df[self.numeric_cols])
        
        self.cleaning_report['normalization'] = method
        
        return self
    
    def clean_all(self, 
                  remove_duplicates: bool = True,
                  missing_threshold: float = 0.5,
                  outlier_method: str = 'iqr',
                  encode: bool = True,
                  normalize: bool = False) -> pd.DataFrame:
        """
        Pipeline completo de limpeza com configurações padrão.
        
        Args:
            remove_duplicates: Remove duplicatas
            missing_threshold: Limite para remover colunas
            outlier_method: Método para tratar outliers
            encode: Codifica variáveis categóricas
            normalize: Normaliza dados numéricos
        
        Returns:
            DataFrame limpo
        """
        print("INICIANDO LIMPEZA COMPLETA DO DATASET")
        
        self.analyze_data()
        
        if remove_duplicates:
            self.remove_duplicates()
        
        self.handle_missing_values(threshold=missing_threshold)
        self.handle_outliers(method=outlier_method, action='cap')
        
        if encode:
            self.encode_categorical()
        
        if normalize:
            self.normalize_data()
        
        print("LIMPEZA CONCLUÍDA!")
        self._print_summary()
        
        return self.df
    
    def _print_summary(self):
        """Imprime resumo da limpeza realizada."""
        print(f"\nResumo das transformações:")
        print(f"   Linhas originais: {len(self.original_df)}")
        print(f"   Linhas finais: {len(self.df)}")
        print(f"   Colunas originais: {len(self.original_df.columns)}")
        print(f"   Colunas finais: {len(self.df.columns)}")
        
        if self.cleaning_report.get('duplicates_removed'):
            print(f"   Duplicatas removidas: {self.cleaning_report['duplicates_removed']}")
        
        if self.cleaning_report.get('outliers'):
            print(f"   Colunas com outliers tratados: {len(self.cleaning_report['outliers'])}")
        
        if self.cleaning_report.get('encoded_columns'):
            print(f"   Colunas codificadas: {len(self.cleaning_report['encoded_columns'])}")
    
    def get_cleaned_data(self) -> pd.DataFrame:
        """Retorna o DataFrame limpo."""
        return self.df
    
    def get_report(self) -> Dict:
        """Retorna relatório detalhado da limpeza."""
        return self.cleaning_report
    

class ICBDataCleaner:
    """
    Specialized cleaner for ICB (Cesta Básica) dataset.
    Performs all transformations from the notebook.
    """

    def __init__(self, input_file: str = 'data/ICB_2s-2025.xlsx'):
        """Initialize with the raw data file path."""
        self.input_file = input_file
        self.df = None
        self.label_mappings = {}
        self.product_classes = {
            'Vegetais': ['Tomate', 'Banana Prata', 'Banana Nanica', 'Batata'],
            'Carnes Vermelhas': ['Carne Bovina Acém', 'Carne Bovina Coxão Mole', 'Carne Suína Pernil'],
            'Aves': ['Frango Peito', 'Frango Sobrecoxa'],
            'Laticínios': ['Manteiga', 'Leite'],
            'Padaria & Cozinha': ['Pão', 'Ovo', 'Farinha de Trigo', 'Café', 'Açúcar', 'Óleo'],
            'Grãos & Massas': ['Arroz', 'Feijão', 'Macarrão'],
        }

    def load_data(self) -> pd.DataFrame:
        """Load the raw Excel data."""
        print(f"Loading data from '{self.input_file}'...")
        self.df = pd.read_excel(self.input_file)
        print(f"Dataset loaded: {self.df.shape[0]} rows, {self.df.shape[1]} columns")
        return self.df

    def clean_products(self) -> None:
        """Clean and standardize product names."""
        print("\nCleaning product names...")

        # Carne Bovina Acém variations
        mapping = {k: "Carne Bovina Acém" for k in ['Carne Acém', 'Carne Acem', 'Carne Bovina Acem']}
        self.df['Produto'] = self.df['Produto'].replace(mapping)

        # Carne Bovina Coxão Mole
        self.df['Produto'] = self.df['Produto'].replace({'Carne Coxão Mole': 'Carne Bovina Coxão Mole'})

        # Pão variations
        self.df['Produto'] = self.df['Produto'].replace({'Pão Francês': 'Pão'})

        # Farinha variations
        self.df['Produto'] = self.df['Produto'].replace({'Farinha': 'Farinha de Trigo'})

        # Macarrão variations
        self.df['Produto'] = self.df['Produto'].replace({'Macarrão com Ovos': 'Macarrão'})

        # Carne Suína Pernil
        self.df['Produto'] = self.df['Produto'].replace({'Carne Pernil': 'Carne Suína Pernil'})

        unique_products = len(self.df['Produto'].unique())
        print(f"Products cleaned. Unique products: {unique_products}")

    def add_product_classes(self) -> None:
        """Add product class categorization."""
        print("\nAdding product classes...")

        # Create product to class mapping
        prod_to_class = {prod: cls for cls, prods in self.product_classes.items()
                        for prod in prods}

        # Add Classe column
        self.df['Classe'] = self.df['Produto'].map(prod_to_class)

        # Create boolean columns for each class
        for class_name in self.product_classes.keys():
            col_name = f'Classe_{class_name}'
            self.df[col_name] = self.df['Classe'] == class_name

        print(f"Added {len(self.product_classes)} product classes")

    def clean_brands(self) -> None:
        """Clean and standardize brand names."""
        print("\nCleaning brand names...")

        # Products without brand (assign 'Sem Marca')
        without_brand = ['Tomate', 'Banana Prata', 'Banana Nanica', 'Batata',
                        'Pão', 'Frango Peito', 'Ovo', 'Carne Bovina Acém',
                        'Frango Sobrecoxa', 'Carne Bovina Coxão Mole', 'Carne Suína Pernil']

        self.df.loc[self.df['Produto'].isin(without_brand), 'Marca'] = 'Sem Marca'

        # Remove null values in Marca column
        self.df = self.df.dropna(subset=['Marca'])

        # Convert to string and clean variations
        self.df['Marca'] = self.df['Marca'].astype(str)

        # Brand name standardization
        brand_replacements = {
            '3 corações': '3 Corações',
            'Albaruska ': 'Albaruska',
            'Alto Alegre ': 'Alto Alegre',
            'Camil ': 'Camil',
            'DaVaca': 'Da Vaca',
            'Davaca': 'Da Vaca',
            'Emporio São João': 'Empório São João',
            'Grão De Campo': 'Grão Do Campo',
            'Grão de Campo': 'Grão Do Campo',
            'Grão de Campo ': 'Grão Do Campo',
            'Grão do Campo': 'Grão Do Campo',
            'Guarani ': 'Guarani',
            'Knor': 'Knorr',
            'Lider': 'Líder',
            'Outra': 'Outro',
            'Outro2': 'Outro',
            'Pateko': 'Patéko',
            'Paulista ': 'Paulista',
            'Piracanjuba ': 'Piracanjuba',
            'Prato Fino ': 'Prato Fino',
            'Qualita': 'Qualitá',
            'Renata ': 'Renata',
            'Saboroso ': 'Saboroso',
            'Serrazul\n': 'Serrazul',
            'São': 'São Joaquim',
            'São Joaquim ': 'São Joaquim',
            'Urbano ': 'Urbano',
            'Vasconcelos ': 'Vasconcelos',
        }

        for old, new in brand_replacements.items():
            self.df['Marca'] = self.df['Marca'].replace({old: new})

        unique_brands = len(self.df['Marca'].unique())
        print(f"Brands cleaned. Unique brands: {unique_brands}")

    def apply_datacleaner(self) -> pd.DataFrame:
        """
        Apply the general DataCleaner transformations.
        This uses the DataCleaner class from ml_model/classes/datacleaner.py
        which handles:
        - Duplicate removal
        - Missing value imputation
        - Outlier detection and capping
        - Categorical encoding (creating label mappings)
        - Optional normalization
        """
        print("\nApplying general data cleaning...")

        # Create DataCleaner instance with current dataframe
        cleaner = DataCleaner(self.df)

        # Run complete cleaning pipeline
        # This will:
        # 1. Analyze data structure
        # 2. Remove duplicates
        # 3. Handle missing values (auto strategy for numeric, mode for categorical)
        # 4. Handle outliers using IQR method with capping
        # 5. Encode categorical variables (Produto, Marca, Estabelecimento)
        # 6. NOT normalize (preserve original price values)
        df_clean = cleaner.clean_all(
            remove_duplicates=True,
            missing_threshold=0.5,
            outlier_method='iqr',
            encode=True,
            normalize=False
        )

        # Store label mappings from encoding step
        # These mappings show: {original_name: numeric_id}
        self.label_mappings = cleaner.label_mappings

        return df_clean

    def save_mappings(self, output_dir: str = 'data') -> None:
        """Save the label mappings to JSON files."""
        print(f"\nSaving mappings to {output_dir}/...")

        os.makedirs(output_dir, exist_ok=True)

        for column, mapping in self.label_mappings.items():
            filepath = os.path.join(output_dir, f'mapa_{column}.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=4)
            print(f"  Saved: mapa_{column}.json")

    def save_cleaned_data(self, output_file: str = 'data/dados_limpos_ICB.xlsx') -> None:
        """Save the cleaned data to Excel."""
        print(f"\nSaving cleaned data to '{output_file}'...")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        self.df_clean.to_excel(output_file, index=False)
        print(f"Cleaned data saved successfully!")

    def process(self) -> Tuple[pd.DataFrame, Dict]:
        """
        Execute the complete cleaning pipeline.
        Returns the cleaned dataframe and mappings.
        """
        print("=" * 60)
        print("STARTING ICB DATA CLEANING PIPELINE")
        print("=" * 60)

        # Load data
        self.load_data()

        # Clean products
        self.clean_products()

        # Add product classes
        self.add_product_classes()

        # Clean brands
        self.clean_brands()

        # Apply general cleaning
        self.df_clean = self.apply_datacleaner()

        # Save outputs
        self.save_mappings()
        self.save_cleaned_data()

        print("\n" + "=" * 60)
        print("DATA CLEANING PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)

        return self.df_clean, self.label_mappings


if __name__ == "__main__":
    # Run the cleaner when executed directly
    cleaner = ICBDataCleaner()
    df_clean, mappings = cleaner.process()
    print(f"\nFinal dataset shape: {df_clean.shape}")