# Database Migration Plan - ICB Data Processing System

## Executive Summary

Migrate from file-based data storage (Excel/JSON) to a hybrid database architecture:
- **MySQL**: Structured relational data (raw & cleaned datasets)
- **MongoDB**: ML model results and predictions (flexible schema)

---

## 1. Database Architecture

### 1.1 MySQL - Relational Data Store
**Purpose**: Store structured ICB data with proper relationships and constraints

### 1.2 MongoDB - Document Store
**Purpose**: Store ML computation results, predictions, and metrics with flexible schema

---

## 2. MySQL Schema Design

### 2.1 Core Tables

```sql
-- Products Master Table
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    original_name VARCHAR(100),
    standardized_name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50),
    class_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Brands Master Table
CREATE TABLE brands (
    id INT PRIMARY KEY AUTO_INCREMENT,
    original_name VARCHAR(100),
    standardized_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Establishments Master Table
CREATE TABLE establishments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw ICB Data
CREATE TABLE icb_raw_data (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(100),
    brand_name VARCHAR(100),
    establishment_name VARCHAR(100),
    price DECIMAL(10, 2),
    quantity DECIMAL(10, 3),
    ppk DECIMAL(10, 2),  -- Price per kg/unit
    data_date DATE,
    import_batch VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (data_date),
    INDEX idx_product (product_name),
    INDEX idx_establishment (establishment_name)
);

-- Cleaned ICB Data (normalized)
CREATE TABLE icb_clean_data (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    brand_id INT,
    establishment_id INT,
    price DECIMAL(10, 2),
    quantity DECIMAL(10, 3),
    ppk DECIMAL(10, 2),
    data_date DATE,

    -- Boolean class columns
    class_carnes_vermelhas BOOLEAN DEFAULT FALSE,
    class_graos_massas BOOLEAN DEFAULT FALSE,
    class_laticinios BOOLEAN DEFAULT FALSE,
    class_padaria_cozinha BOOLEAN DEFAULT FALSE,
    class_vegetais BOOLEAN DEFAULT FALSE,

    cleaning_batch VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (brand_id) REFERENCES brands(id),
    FOREIGN KEY (establishment_id) REFERENCES establishments(id),
    INDEX idx_date (data_date),
    INDEX idx_product_id (product_id),
    INDEX idx_establishment_id (establishment_id)
);

-- Data Processing Logs
CREATE TABLE processing_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    process_type ENUM('import', 'cleaning', 'training', 'prediction'),
    batch_id VARCHAR(50),
    status ENUM('started', 'completed', 'failed'),
    records_processed INT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL
);
```

### 2.2 ORM Models (SQLAlchemy)

```python
# models/mysql_models.py

from sqlalchemy import Column, Integer, String, Decimal, Date, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    original_name = Column(String(100))
    standardized_name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))
    class_name = Column(String(50))
    created_at = Column(DateTime)

class Brand(Base):
    __tablename__ = 'brands'
    id = Column(Integer, primary_key=True)
    original_name = Column(String(100))
    standardized_name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime)

class Establishment(Base):
    __tablename__ = 'establishments'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(50))
    created_at = Column(DateTime)

class ICBRawData(Base):
    __tablename__ = 'icb_raw_data'
    id = Column(Integer, primary_key=True)
    product_name = Column(String(100))
    brand_name = Column(String(100))
    establishment_name = Column(String(100))
    price = Column(Decimal(10, 2))
    quantity = Column(Decimal(10, 3))
    ppk = Column(Decimal(10, 2))
    data_date = Column(Date)
    import_batch = Column(String(50))
    created_at = Column(DateTime)

class ICBCleanData(Base):
    __tablename__ = 'icb_clean_data'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    brand_id = Column(Integer, ForeignKey('brands.id'))
    establishment_id = Column(Integer, ForeignKey('establishments.id'))
    price = Column(Decimal(10, 2))
    quantity = Column(Decimal(10, 3))
    ppk = Column(Decimal(10, 2))
    data_date = Column(Date)
    class_carnes_vermelhas = Column(Boolean, default=False)
    class_graos_massas = Column(Boolean, default=False)
    class_laticinios = Column(Boolean, default=False)
    class_padaria_cozinha = Column(Boolean, default=False)
    class_vegetais = Column(Boolean, default=False)
    cleaning_batch = Column(String(50))
    created_at = Column(DateTime)

    # Relationships
    product = relationship("Product")
    brand = relationship("Brand")
    establishment = relationship("Establishment")
```

---

## 3. MongoDB Schema Design

### 3.1 Collections Structure

```javascript
// Collection: ml_training_results
{
  _id: ObjectId,
  batch_id: "20241031_150000",
  category: "Classe_Carnes Vermelhas",
  model_type: "RandomForest",
  parameters: {
    n_estimators: 100,
    n_lags: 4,
    test_size_weeks: 12,
    frequency: "W-MON"
  },
  metrics: {
    mse: 0.0234,
    mae: 0.0156,
    mape: 0.0823,
    mape_percent: 8.23,
    objective_achieved: true
  },
  training_date: ISODate("2024-10-31T15:00:00Z"),
  model_blob: BinData(...)  // Serialized model
}

// Collection: predictions
{
  _id: ObjectId,
  batch_id: "20241031_150000",
  category: "Classe_Carnes Vermelhas",
  predictions: [
    {
      week: ISODate("2024-11-04T00:00:00Z"),
      predicted_value: 45.67,
      confidence_interval: {lower: 43.21, upper: 48.13}
    },
    // ... 12 weeks of predictions
  ],
  created_at: ISODate("2024-10-31T15:00:00Z")
}

// Collection: analysis_results
{
  _id: ObjectId,
  analysis_type: "price_leadership",
  product_id: 15,
  establishment_a_id: 3,
  establishment_b_id: 7,
  results: {
    ccf_values: [...],
    granger_causality: {
      a_causes_b_pvalue: 0.032,
      b_causes_a_pvalue: 0.451
    },
    max_correlation_lag: 3
  },
  created_at: ISODate("2024-10-31T15:00:00Z")
}
```

### 3.2 MongoDB Models (PyMongo/MongoEngine)

```python
# models/mongodb_models.py

from mongoengine import Document, StringField, DictField, ListField, DateTimeField, FloatField, BooleanField, BinaryField
from datetime import datetime

class MLTrainingResult(Document):
    batch_id = StringField(required=True)
    category = StringField(required=True)
    model_type = StringField(default="RandomForest")
    parameters = DictField()
    metrics = DictField()
    training_date = DateTimeField(default=datetime.utcnow)
    model_blob = BinaryField()  # Pickled model

    meta = {
        'collection': 'ml_training_results',
        'indexes': ['batch_id', 'category', 'training_date']
    }

class Prediction(Document):
    batch_id = StringField(required=True)
    category = StringField(required=True)
    predictions = ListField(DictField())
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'predictions',
        'indexes': ['batch_id', 'category']
    }

class AnalysisResult(Document):
    analysis_type = StringField(required=True)
    product_id = IntField()
    establishment_a_id = IntField()
    establishment_b_id = IntField()
    results = DictField()
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'analysis_results',
        'indexes': ['analysis_type', 'created_at']
    }
```

---

## 4. Required Changes to Applications

### 4.1 ML Model Application (`ml_model/main.py`)

#### Current State:
- Reads from `data/ICB_2s-2025.xlsx`
- Writes to `data/dados_limpos_ICB.xlsx`
- Saves JSON mappings to `data/mapa_*.json`
- Saves results to `data/results/*.csv` and `*.json`

#### Required Changes:

```python
# NEW: Database connections
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mongoengine import connect
import pandas as pd

class MLPipeline:
    def __init__(self):
        # MySQL connection
        self.mysql_engine = create_engine('mysql://user:pass@mysql:3306/icb_db')
        Session = sessionmaker(bind=self.mysql_engine)
        self.mysql_session = Session()

        # MongoDB connection
        connect('icb_ml', host='mongodb://mongodb:27017')

    def run_data_cleaning(self):
        # CHANGE: Read raw data from MySQL instead of Excel
        query = "SELECT * FROM icb_raw_data WHERE import_batch = %s"
        df_raw = pd.read_sql(query, self.mysql_engine, params=[batch_id])

        # Process with ICBDataCleaner (unchanged)
        cleaner = ICBDataCleaner()
        df_clean, mappings = cleaner.process_dataframe(df_raw)

        # CHANGE: Save to MySQL tables instead of Excel
        # 1. Update products, brands, establishments tables
        self._update_master_tables(mappings)

        # 2. Insert cleaned data
        df_clean.to_sql('icb_clean_data', self.mysql_engine,
                       if_exists='append', index=False)

    def run_model_predictions(self):
        # CHANGE: Read from MySQL instead of Excel
        query = """
            SELECT * FROM icb_clean_data
            JOIN products ON icb_clean_data.product_id = products.id
            WHERE cleaning_batch = %s
        """
        df = pd.read_sql(query, self.mysql_engine, params=[batch_id])

        # Train models (unchanged logic)
        results = self._train_and_predict(df)

        # CHANGE: Save to MongoDB instead of JSON/CSV files
        for category, result in results.items():
            # Save training results
            training_result = MLTrainingResult(
                batch_id=batch_id,
                category=category,
                metrics=result['metrics'],
                model_blob=pickle.dumps(result['model'])
            )
            training_result.save()

            # Save predictions
            prediction = Prediction(
                batch_id=batch_id,
                category=category,
                predictions=result['predictions']
            )
            prediction.save()
```

### 4.2 Streamlit Dashboard (`streamlit/dashboard.py`)

#### Current State:
- Reads from `data/dados_limpos_ICB.xlsx`
- Loads mappings from `data/mapa_*.json`
- Directly calls `AnalisadorCestaBasicaPro` with file path

#### Required Changes:

```python
# NEW: Database connections
from sqlalchemy import create_engine
import pandas as pd
from pymongo import MongoClient

# Initialize connections
@st.cache_resource
def init_db_connections():
    mysql_engine = create_engine('mysql://user:pass@mysql:3306/icb_db')
    mongo_client = MongoClient('mongodb://mongodb:27017')
    mongo_db = mongo_client['icb_ml']
    return mysql_engine, mongo_db

mysql_engine, mongo_db = init_db_connections()

# CHANGE: Load data from MySQL
@st.cache_data
def load_data():
    query = """
        SELECT cd.*, p.standardized_name as product_name,
               b.standardized_name as brand_name,
               e.name as establishment_name
        FROM icb_clean_data cd
        JOIN products p ON cd.product_id = p.id
        JOIN brands b ON cd.brand_id = b.id
        JOIN establishments e ON cd.establishment_id = e.id
        ORDER BY cd.data_date DESC
        LIMIT 10000
    """
    return pd.read_sql(query, mysql_engine)

# CHANGE: Load mappings from MySQL
@st.cache_data
def carregar_mapas():
    products = pd.read_sql("SELECT id, standardized_name FROM products", mysql_engine)
    establishments = pd.read_sql("SELECT id, name FROM establishments", mysql_engine)

    mapa_produto = dict(zip(products['standardized_name'], products['id']))
    mapa_estab = dict(zip(establishments['name'], establishments['id']))

    return mapa_produto, mapa_estab, {v:k for k,v in mapa_produto.items()}, {v:k for k,v in mapa_estab.items()}

# CHANGE: Load predictions from MongoDB
@st.cache_data
def load_predictions(category, n_weeks=12):
    collection = mongo_db['predictions']

    # Get latest prediction for category
    result = collection.find_one(
        {'category': category},
        sort=[('created_at', -1)]
    )

    if result:
        df = pd.DataFrame(result['predictions'])
        return df
    return None

# CHANGE: For Question 1 - Load from MongoDB instead of running analysis
def rodar_analise_q1(categoria, n_semanas):
    # Get latest ML results from MongoDB
    training_collection = mongo_db['ml_training_results']
    prediction_collection = mongo_db['predictions']

    # Get metrics
    training = training_collection.find_one(
        {'category': categoria},
        sort=[('training_date', -1)]
    )

    # Get predictions
    predictions = prediction_collection.find_one(
        {'category': categoria},
        sort=[('created_at', -1)]
    )

    if training and predictions:
        df_futuro = pd.DataFrame(predictions['predictions'])
        return {
            'mse': training['metrics']['mse'],
            'mae': training['metrics']['mae'],
            'mape': training['metrics']['mape'],
            'df_futuro': df_futuro,
            'erro': None
        }
    return {'erro': 'No results found in database'}
```

---

## 5. Database Connection Configuration

### 5.1 Environment Variables (.env)

```bash
# MySQL Configuration
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=icb_db
MYSQL_USER=icb_user
MYSQL_PASSWORD=secure_password

# MongoDB Configuration
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DATABASE=icb_ml
MONGO_USER=ml_user
MONGO_PASSWORD=secure_password
```

### 5.2 Docker Compose Updates

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: icb_db
      MYSQL_USER: icb_user
      MYSQL_PASSWORD: secure_password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    networks:
      - app-network

  mongodb:
    image: mongo:6.0
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: root_password
      MONGO_INITDB_DATABASE: icb_ml
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"
    networks:
      - app-network

  ml-model:
    # ... existing config ...
    depends_on:
      - mysql
      - mongodb
    environment:
      - MYSQL_HOST=mysql
      - MONGO_HOST=mongodb

  streamlit-dashboard:
    # ... existing config ...
    depends_on:
      - mysql
      - mongodb
    environment:
      - MYSQL_HOST=mysql
      - MONGO_HOST=mongodb

volumes:
  mysql_data:
  mongo_data:
```

---

## 6. Migration Strategy

### Phase 1: Database Setup
1. Deploy MySQL and MongoDB containers
2. Create database schemas
3. Run initial migrations

### Phase 2: Data Migration
1. Create migration script to:
   - Read existing Excel files
   - Populate MySQL tables
   - Migrate existing JSON results to MongoDB

### Phase 3: Application Updates
1. Update `ml_model/main.py` with database connections
2. Update `streamlit/dashboard.py` with database queries
3. Add new dependencies to requirements.txt:
   ```
   sqlalchemy==2.0.23
   pymysql==1.1.0
   mongoengine==0.27.0
   pymongo==4.5.0
   ```

### Phase 4: Testing & Validation
1. Test data insertion/retrieval
2. Validate ML pipeline with database
3. Verify dashboard functionality

---


## 7. Summary of Key Changes

### ML Model (`ml_model/main.py`):
-  Add MySQL connection for reading raw data
-  Add MongoDB connection for storing results
-  Replace file I/O with database operations
-  Update data cleaning to work with DataFrames from SQL
-  Store trained models as binary blobs in MongoDB

### Streamlit Dashboard (`streamlit/dashboard.py`):
-  Add MySQL connection for reading cleaned data
-  Add MongoDB connection for reading predictions
-  Replace file-based data loading with SQL queries
-  Cache database query results
-  Update visualization functions to work with database data

### New Files Required:
- `models/mysql_models.py` - SQLAlchemy ORM models
- `models/mongodb_models.py` - MongoEngine document models
- `config/database.py` - Database connection management
- `migrations/` - Database migration scripts
- `init.sql` - MySQL schema initialization

---

## Next Steps

1. **Approval**: Review and approve database design
2. **Implementation**: Create ORM models and connection classes
3. **Migration**: Develop data migration scripts
4. **Testing**: Set up test databases with sample data
5. **Deployment**: Update Docker compose and deploy