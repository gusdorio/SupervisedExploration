# Database Migration Action Plan - Complete Implementation Guide

## Overview
This document provides a comprehensive action list for migrating from file-based storage to MySQL + MongoDB architecture.

---

## Phase 1: Infrastructure Setup

### 1.1 Docker Infrastructure
- [ ] Create `docker-compose.db.yml` for database services
- [ ] Add MySQL 8.0 container with:
  - Persistent volume for data
  - Environment variables for credentials
  - Port mapping (3306)
  - Health check configuration
- [ ] Add MongoDB 6.0 container with:
  - Persistent volume for data
  - Environment variables for credentials
  - Port mapping (27017)
  - Health check configuration
- [ ] Update main `docker-compose.yml` to include database services
- [ ] Add `depends_on` to ml-model and streamlit services
- [ ] Configure shared network for all containers

### 1.2 Environment Configuration
- [ ] Create `.env` file with database credentials:
  ```
  MYSQL_HOST=mysql
  MYSQL_PORT=3306
  MYSQL_DATABASE=icb_db
  MYSQL_USER=icb_user
  MYSQL_PASSWORD=secure_password

  MONGO_HOST=mongodb
  MONGO_PORT=27017
  MONGO_DATABASE=icb_ml
  MONGO_USER=
  MONGO_PASSWORD=
  ```
- [ ] Add `.env` to `.gitignore`
- [ ] Create `.env.example` for documentation

### 1.3 Dependencies Update
- [ ] Update `ml_model/requirements.txt`:
  ```
  sqlalchemy==2.0.23
  pymysql==1.1.0
  mongoengine==0.27.0
  pymongo==4.5.0
  python-dotenv==1.0.0
  ```
- [ ] Update `streamlit/requirements.txt` with same database libraries
- [ ] Rebuild Docker images with new dependencies

---

## Phase 2: Database Initialization

### 2.1 MySQL Schema Creation
- [ ] Create `migrations/init_mysql.sql` with:
  - Database creation
  - User permissions
  - Table creation statements
  - Index creation
  - Initial constraints
- [ ] Create `migrations/create_tables.py` using SQLAlchemy:
  ```python
  from models.database import DatabaseManager
  from models.mysql import Base

  # Create all tables
  mysql = DatabaseManager.get_mysql()
  mysql.create_tables()
  ```
- [ ] Test table creation in development environment

### 2.2 MongoDB Collections Setup
- [ ] Create `migrations/init_mongodb.js` with:
  - Database creation
  - Collection creation
  - Index definitions
  - Validation rules
- [ ] Create `migrations/setup_mongodb.py`:
  ```python
  from models.database import DatabaseManager

  # Create indexes for all collections
  mongo = DatabaseManager.get_mongodb()
  # Setup indexes...
  ```

---

## Phase 3: Data Migration Scripts

### 3.1 Create Migration Utilities
- [ ] Create `migrations/migrate_data.py` with functions:
  - `migrate_raw_data()` - Import ICB_2s-2025.xlsx to icb_raw_data
  - `migrate_cleaned_data()` - Import dados_limpos_ICB.xlsx to icb_clean_data
  - `migrate_mappings()` - Import JSON mappings to mapping tables
  - `migrate_results()` - Import existing results to MongoDB
  - `verify_migration()` - Validate data integrity

### 3.2 Implement Migration Functions
```python
# migrations/migrate_data.py

import pandas as pd
import json
from models.database import DatabaseManager
from models.mysql import *
from models.mongodb import *

def migrate_raw_data():
    """Migrate raw Excel data to MySQL"""
    # Read Excel
    df = pd.read_excel('data/ICB_2s-2025.xlsx')

    # Get MySQL session
    mysql = DatabaseManager.get_mysql()

    with mysql.session_scope() as session:
        for _, row in df.iterrows():
            record = ICBRawData(
                produto=row['Produto'],
                marca=row['Marca'],
                estabelecimento=row['Estabelecimento'],
                preco=row['Preço'],
                quantidade=row['Quantidade'],
                data_coleta=row['Data_Coleta']
            )
            session.add(record)

def migrate_mappings():
    """Migrate JSON mappings to MySQL"""
    # Load JSON files
    with open('data/mapa_Produto.json') as f:
        product_map = json.load(f)

    mysql = DatabaseManager.get_mysql()

    with mysql.session_scope() as session:
        for name, id_val in product_map.items():
            mapping = ProductMapping(id=id_val, name=name)
            session.add(mapping)
    # Similar for Brand and Establishment mappings
```

---

## Phase 4: ML Model Application Updates

### 4.1 Update Main Pipeline (`ml_model/main.py`)
- [ ] Import database models:
  ```python
  from models.database import DatabaseManager
  from models.mysql import *
  from models.mongodb import *
  ```
- [ ] Replace file loading in Phase 1:
  ```python
  # OLD: df = pd.read_excel('data/ICB_2s-2025.xlsx')
  # NEW:
  mysql = DatabaseManager.get_mysql()
  with mysql.session_scope() as session:
      raw_data = session.query(ICBRawData).all()
      df = pd.DataFrame([{
          'Produto': r.produto,
          'Marca': r.marca,
          # ...
      } for r in raw_data])
  ```
- [ ] Replace file saving in data cleaning:
  ```python
  # OLD: df_clean.to_excel('data/dados_limpos_ICB.xlsx')
  # NEW: Save to icb_clean_data table
  ```
- [ ] Replace JSON mapping saves:
  ```python
  # OLD: json.dump(mappings, open('data/mapa_Produto.json', 'w'))
  # NEW: Save to mapping tables in MySQL
  ```

### 4.2 Update DataCleaner (`ml_model/classes/datacleaner.py`)
- [ ] Modify `save_clean_data()` method:
  - Accept database session as parameter
  - Save to MySQL instead of Excel
  - Return mapping dictionaries
- [ ] Update `save_label_mappings()`:
  - Save to database tables instead of JSON files
  - Maintain backward compatibility

### 4.3 Update Algorithms (`ml_model/classes/algorithms.py`)
- [ ] Modify constructor to accept DataFrame:
  ```python
  def __init__(self, dataframe=None, filepath=None):
      if dataframe is not None:
          self.df = dataframe
      elif filepath:
          self.df = pd.read_excel(filepath)
  ```
- [ ] Update result saving:
  - Return structured dictionaries
  - Save to MongoDB collections

### 4.4 Store Results in MongoDB
- [ ] Save training metrics:
  ```python
  result = MLTrainingResult(
      batch_id=batch_id,
      category=category,
      metrics=ModelMetrics(
          mse=mse,
          mae=mae,
          mape=mape,
          objective_achieved=(mape < 0.1)
      )
  )
  result.save()
  ```
- [ ] Save predictions:
  ```python
  predictions = CategoryPrediction(
      batch_id=batch_id,
      category=category,
      predictions=[
          PredictionEntry(week=week, predicted_value=value)
          for week, value in df_future.items()
      ]
  )
  predictions.save()
  ```

---

## Phase 5: Streamlit Dashboard Updates

### 5.1 Update Data Loading (`streamlit/dashboard.py`)
- [ ] Import database models:
  ```python
  from models.database import DatabaseManager
  from models.mysql import *
  from models.mongodb import *
  ```
- [ ] Replace file loading functions:
  ```python
  @st.cache_data
  def load_data():
      mysql = DatabaseManager.get_mysql()

      query = """
      SELECT c.*,
             p.name as produto_name,
             b.name as marca_name,
             e.name as estabelecimento_name
      FROM icb_clean_data c
      LEFT JOIN product_mappings p ON c.produto = p.id
      LEFT JOIN brand_mappings b ON c.marca = b.id
      LEFT JOIN establishment_mappings e ON c.estabelecimento = e.id
      """

      df = pd.read_sql(query, mysql.engine)
      return df
  ```
- [ ] Update mapping loaders:
  ```python
  @st.cache_data
  def carregar_mapas():
      mysql = DatabaseManager.get_mysql()

      # Load from database instead of JSON
      with mysql.session_scope() as session:
          products = session.query(ProductMapping).all()
          mapa_produto = {p.name: p.id for p in products}
      # Similar for other mappings
  ```

### 5.2 Update Analysis Functions
- [ ] Modify Q1 analysis to load from MongoDB:
  ```python
  def rodar_analise_q1(categoria, n_semanas):
      mongo = DatabaseManager.get_mongodb()

      # Get latest results from MongoDB
      result = MLTrainingResult.objects(
          category=categoria
      ).order_by('-created_at').first()

      predictions = CategoryPrediction.objects(
          category=categoria
      ).order_by('-created_at').first()

      # Format for display
  ```
- [ ] Modify Q2 analysis similarly

### 5.3 Update Caching Strategy
- [ ] Implement database query caching
- [ ] Add TTL to cache decorators
- [ ] Create refresh mechanism

---

## Phase 6: Testing & Validation

### 6.1 Unit Tests
- [ ] Create `tests/test_mysql_models.py`:
  - Test CRUD operations
  - Test relationships
  - Test constraints
- [ ] Create `tests/test_mongodb_models.py`:
  - Test document creation
  - Test queries
  - Test indexes
- [ ] Create `tests/test_database_connection.py`:
  - Test connection pooling
  - Test failover
  - Test transactions

### 6.2 Integration Tests
- [ ] Create `tests/test_ml_pipeline_db.py`:
  - Test complete ML pipeline with databases
  - Test data cleaning and storage
  - Test model training and result storage
- [ ] Create `tests/test_dashboard_db.py`:
  - Test data loading from databases
  - Test analysis functions
  - Test performance

### 6.3 Migration Validation
- [ ] Create validation script:
  ```python
  # tests/validate_migration.py

  def validate_row_counts():
      # Compare Excel vs Database row counts

  def validate_data_integrity():
      # Sample and compare data

  def validate_mappings():
      # Verify all mappings preserved
  ```

---

## Phase 7: Deployment Preparation

### 7.1 Create Deployment Scripts
- [ ] Create `scripts/setup_databases.sh`:
  ```bash
  #!/bin/bash
  # Initialize databases
  docker-compose up -d mysql mongodb
  sleep 10
  python migrations/create_tables.py
  python migrations/setup_mongodb.py
  ```
- [ ] Create `scripts/run_migration.sh`:
  ```bash
  #!/bin/bash
  # Run data migration
  python migrations/migrate_data.py
  ```

### 7.2 Update Docker Files
- [ ] Update `ml_model/Dockerfile.ml`:
  - Add database libraries
  - Copy models folder
  - Set environment variables
- [ ] Update `streamlit/Dockerfile.streamlit`:
  - Add database libraries
  - Copy models folder
  - Set environment variables

### 7.3 Documentation
- [ ] Create `docs/DATABASE_SETUP.md`
- [ ] Update README with database instructions
- [ ] Document environment variables
- [ ] Create troubleshooting guide

---

## Phase 8: Rollback Plan

### 8.1 Backup Strategy
- [ ] Create database backup scripts
- [ ] Document restoration process
- [ ] Test backup/restore cycle

### 8.2 Feature Toggle
- [ ] Implement feature flag for database mode:
  ```python
  USE_DATABASE = os.getenv('USE_DATABASE', 'false').lower() == 'true'

  if USE_DATABASE:
      # Load from database
  else:
      # Load from files (fallback)
  ```
- [ ] Test both modes

---

## Phase 9: Performance Optimization

### 9.1 Database Optimization
- [ ] Add indexes for common queries
- [ ] Implement connection pooling
- [ ] Configure query caching
- [ ] Set up read replicas (if needed)

### 9.2 Application Optimization
- [ ] Implement batch processing for inserts
- [ ] Add pagination for large queries
- [ ] Optimize DataFrame operations
- [ ] Profile and optimize bottlenecks

---

## Phase 10: Monitoring & Maintenance

### 10.1 Monitoring Setup
- [ ] Add database health checks
- [ ] Implement logging for database operations
- [ ] Set up alerts for failures
- [ ] Create performance dashboards

### 10.2 Maintenance Procedures
- [ ] Create cleanup scripts for old data
- [ ] Implement archival strategy
- [ ] Document backup schedule
- [ ] Create maintenance windows

---

## Execution Timeline

### Week 1
- Infrastructure setup (Docker, environment)
- Database initialization
- Model creation and testing

### Week 2
- Data migration scripts
- ML model integration
- Initial testing

### Week 3
- Streamlit dashboard integration
- Integration testing
- Performance optimization

### Week 4
- Deployment preparation
- Documentation
- Final testing and validation

### Week 5
- Production deployment
- Monitoring setup
- Post-deployment validation

---

## Success Criteria

1. ✅ All data successfully migrated from files to databases
2. ✅ ML pipeline runs with database backend
3. ✅ Streamlit dashboard loads data from databases
4. ✅ Performance equal or better than file-based system
5. ✅ All tests passing
6. ✅ Documentation complete
7. ✅ Rollback plan tested

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|-------------------|
| Data loss during migration | Backup all files, implement validation checks |
| Performance degradation | Profile queries, add indexes, implement caching |
| Connection failures | Implement retry logic, connection pooling |
| Incompatible data types | Validate data types, implement converters |
| Docker networking issues | Test container communication, use docker networks |

---

## Notes

- Always test in development environment first
- Keep original files as backup during transition
- Monitor resource usage during initial deployment
- Consider gradual rollout with feature flags
- Document any deviations from plan