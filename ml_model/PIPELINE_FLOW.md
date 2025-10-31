# ML Model Pipeline Flow

## Complete Data Processing Pipeline

This document describes the complete data processing pipeline implemented in the ml_model application, replicating all transformations from the `statistical_analysis.ipynb` notebook.

## Centralized Architecture

**All data cleaning logic is centralized in:**
📁 **`ml_model/classes/datacleaner.py`**

This file contains:
- **DataCleaner** (lines 14-404): General-purpose data cleaning class
- **ICBDataCleaner** (lines 406-628): ICB-specific cleaning that internally uses DataCleaner

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ main.py (ml_model/main.py)                                      │
│   └─► MLPipeline.run()                                          │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│ PHASE 1: DATA CLEANING      │   │ PHASE 2: MODEL TRAINING     │
│                              │   │                              │
│ ICBDataCleaner               │   │ AnalisadorCestaBasicaPro     │
│ (datacleaner.py:406-628)     │   │ (algotithms.py)             │
└─────────────────────────────┘   └─────────────────────────────┘
            │                                   │
            ▼                                   ▼
   ┌────────────────────┐            ┌────────────────────┐
   │ 1. Load Raw Data   │            │ For Each Category: │
   │    ICB_2s-2025.xlsx│            │  - Carnes Vermelhas│
   └────────────────────┘            │  - Grãos & Massas  │
            │                        │  - Laticínios      │
            ▼                        │  - Padaria/Cozinha │
   ┌────────────────────┐            │  - Vegetais        │
   │ 2. ICB Cleaning    │            └────────────────────┘
   │  ├─ Clean Products │                     │
   │  ├─ Add Classes    │                     ▼
   │  └─ Clean Brands   │            ┌────────────────────┐
   └────────────────────┘            │ 1. Filter data     │
            │                        │ 2. Create time     │
            ▼                        │    series (weekly) │
   ┌────────────────────┐            │ 3. Lagged features │
   │ 3. General Cleaning│            │    (4 lags)        │
   │                    │            │ 4. Train RF model  │
   │ DataCleaner        │            │ 5. Evaluate (MSE,  │
   │ (lines 14-404)     │            │    MAE, MAPE)      │
   │  ├─ Analyze data   │            │ 6. Retrain on full │
   │  ├─ Rm duplicates  │            │    dataset         │
   │  ├─ Handle missing │            │ 7. Future predict  │
   │  ├─ Handle outliers│            │    (12 weeks)      │
   │  └─ Encode vars    │            └────────────────────┘
   │     (creates       │                     │
   │      label_mappings)│                    ▼
   └────────────────────┘            ┌────────────────────┐
            │                        │ Save Results:      │
            ▼                        │  - predictions CSV │
   ┌────────────────────┐            │  - metrics JSON    │
   │ 4. Save Outputs:   │            │  - summary report  │
   │  ├─ dados_limpos   │            └────────────────────┘
   │  │   _ICB.xlsx     │
   │  └─ mapa_*.json    │
   │     (Produto,      │
   │      Marca,        │
   │      Estabelec.)   │
   └────────────────────┘
```

## File Structure

```
ml_model/
├── main.py                    # Orchestration script (MLPipeline)
├── classes/
│   ├── datacleaner.py         # ⭐ CENTRALIZED: All cleaning logic
│   │   ├── DataCleaner        # General cleaning (lines 14-404)
│   │   └── ICBDataCleaner     # ICB-specific cleaning (lines 406-628)
│   └── algotithms.py          # ML model & predictions
└── requirements.txt           # Python dependencies
```

## Phase 1: ICB-Specific Data Cleaning (ICBDataCleaner)

**Location:** `ml_model/classes/datacleaner.py` (lines 406-628)

### 1.1 Product Name Standardization
- Merges product name variations:
  - "Carne Acém", "Carne Acem" → "Carne Bovina Acém"
  - "Pão Francês" → "Pão"
  - "Farinha" → "Farinha de Trigo"
  - "Macarrão com Ovos" → "Macarrão"
  - etc.

### 1.2 Product Classification
Creates 6 main categories:
- **Vegetais**: Tomate, Banana Prata, Banana Nanica, Batata
- **Carnes Vermelhas**: Carne Bovina Acém, Carne Bovina Coxão Mole, Carne Suína Pernil
- **Aves**: Frango Peito, Frango Sobrecoxa
- **Laticínios**: Manteiga, Leite
- **Padaria & Cozinha**: Pão, Ovo, Farinha de Trigo, Café, Açúcar, Óleo
- **Grãos & Massas**: Arroz, Feijão, Macarrão

Adds:
- `Classe` column with category name
- `Classe_<CategoryName>` boolean columns for each category

### 1.3 Brand Name Standardization
- Assigns "Sem Marca" to unbranded products
- Standardizes brand variations:
  - "DaVaca", "Davaca" → "Da Vaca"
  - "Grão de Campo", "Grão De Campo" → "Grão Do Campo"
  - "Knor" → "Knorr"
  - etc.

## Phase 2: General Data Cleaning (DataCleaner)

**Location:** `ml_model/classes/datacleaner.py` (lines 14-404)

This class is called internally by `ICBDataCleaner.apply_datacleaner()` (line 532)

### 2.1 Data Analysis
- Identifies numeric, categorical, and datetime columns
- Analyzes missing values
- Counts duplicates

### 2.2 Duplicate Removal
- Removes exact duplicate rows
- Keeps first occurrence by default

### 2.3 Missing Value Handling
- **Numeric columns**: Auto strategy
  - High skewness (>1): median imputation
  - Low skewness (≤1): mean imputation
- **Categorical columns**: Mode imputation
- Removes columns with >50% missing values

### 2.4 Outlier Treatment
- Uses IQR (Interquartile Range) method
- Action: Capping (not removal)
- Threshold: 1.5 × IQR
- Formula: [Q1 - 1.5×IQR, Q3 + 1.5×IQR]

### 2.5 Categorical Encoding
- **Auto strategy**:
  - ≤10 categories: One-hot encoding
  - >10 categories: Label encoding
- **Creates label_mappings**: `{name: numeric_id}`
- Typically encodes:
  - `Produto` → numeric IDs
  - `Marca` → numeric IDs
  - `Estabelecimento` → numeric IDs

### 2.6 Normalization
- **Disabled** (normalize=False)
- Preserves original price values for interpretability

## Phase 3: Model Training & Predictions (AnalisadorCestaBasicaPro)

**Location:** `ml_model/classes/algotithms.py`

Called by `MLPipeline.run_model_predictions()` in main.py (line 48)

### 3.1 Data Preparation
- Loads cleaned data
- Filters by category (Classe_<CategoryName>)
- Creates weekly time series (freq='W-MON')
- Resamples to weekly averages

### 3.2 Feature Engineering
- Creates lagged features (n_lags=4):
  - `y_lag_1`: Previous week
  - `y_lag_2`: 2 weeks ago
  - `y_lag_3`: 3 weeks ago
  - `y_lag_4`: 4 weeks ago

### 3.3 Model Training
- **Algorithm**: Random Forest Regressor
- **Parameters**:
  - n_estimators=100
  - random_state=42
  - n_jobs=-1 (parallel processing)

### 3.4 Model Evaluation
- **Test set**: Last 12 weeks
- **Metrics**:
  - MSE (Mean Squared Error)
  - MAE (Mean Absolute Error)
  - MAPE (Mean Absolute Percentage Error)
- **Objective**: MAPE < 10%

### 3.5 Future Predictions
- Trains final model on ALL data
- Generates 12-week future predictions
- Uses auto-regressive approach:
  - Predicts week t+1
  - Uses prediction as input for t+2
  - Continues for 12 weeks

## Output Files

### Data Files
- `data/dados_limpos_ICB.xlsx` - Cleaned dataset
- `data/mapa_Produto.json` - Product name → ID mapping
- `data/mapa_Marca.json` - Brand name → ID mapping
- `data/mapa_Estabelecimento.json` - Store name → ID mapping

### Results Files
- `data/results/predictions_Classe_<CategoryName>.csv` - Future predictions per category
- `data/results/model_results_<timestamp>.json` - Complete results with metrics

## Execution

### Docker Container
```bash
docker-compose up --build
```

The ML model container will automatically:
1. Run the complete cleaning pipeline
2. Train models for all 5 categories
3. Generate predictions
4. Save all outputs to data/ directory

### Standalone Python
```bash
cd ml_model
python main.py
```

## Key Features

1. **Centralized Architecture**: All cleaning logic in single file (`datacleaner.py`)
2. **Exact Notebook Replication**: All transformations match the notebook
3. **Two-Stage Cleaning**: ICB-specific → General cleaning pipeline
4. **Label Mapping Persistence**: JSON files for ID→Name lookback
5. **Automated Pipeline**: No manual intervention needed
6. **Comprehensive Logging**: Detailed progress output at each stage
7. **Error Handling**: Graceful failure with informative messages

## Import Chain

```python
# main.py imports:
from ml_model.classes.datacleaner import ICBDataCleaner      # Line 16
from ml_model.classes.algotithms import AnalisadorCestaBasicaPro  # Line 17

# ICBDataCleaner internally uses:
DataCleaner (same file, lines 14-404)  # Called at line 546
```

## Dependencies

See `ml_model/requirements.txt`:
- pandas==2.0.3
- numpy==1.24.3
- scikit-learn==1.3.0
- statsmodels==0.14.0
- openpyxl==3.1.2
- scipy==1.11.1
