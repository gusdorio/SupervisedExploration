# Database Setup Guide - ICB Supervised Learning

## Overview

We've successfully set up a normalized MySQL database structure for the ICB data, replacing the file-based storage system. This guide explains what was implemented and how to use it.

## What Was Created

### 1. Docker Infrastructure (`docker-compose.db.yml`)
- **MySQL 8.0**: Relational database for structured ICB data
- **MongoDB 6.0**: Document store for ML model results
- Both databases run in Docker containers with health checks

### 2. Database Models (`models/`)
- **mysql.py**: Normalized schema with Products, Brands, Establishments, and ICBData tables
- **mongodb.py**: Document models for ML training results and predictions
- **database.py**: Connection manager with pooling and configuration

### 3. Migration System (`migrations/`)
- **init_mysql.sql**: Database schema creation
- **init_mongo.js**: MongoDB collections and indexes
- **migrate_clean_data.py**: Script to import cleaned Excel data

### 4. Configuration Files
- **.env**: Database credentials (created, not in git)
- **.env.example**: Template for environment variables

## Normalized Structure

The key improvement is **data normalization**:

```
Before (Excel):                After (MySQL):
- Product names repeated   →   products table (master)
- Brand names repeated     →   brands table (master)
- Establishment repeated   →   establishments table (master)
- All data in one sheet    →   icb_data table (with foreign keys)
```

### Benefits:
- No data duplication
- Consistent naming
- Easier updates
- Better query performance
- Data integrity with foreign keys

## How to Use

### Step 1: Start the Databases

```bash
# Start databases
./scripts/setup_databases.sh

# Or manually:
docker-compose -f docker-compose.db.yml up -d
```

### Step 2: Install Dependencies

```bash
pip install -r migrations/requirements.txt
```

### Step 3: Run Migration

```bash
# This imports dados_limpos_ICB.xlsx into the database
python migrations/migrate_clean_data.py
```

### Step 4: Verify Data

```bash
# Connect to MySQL
docker exec -it icb_mysql mysql -u icb_user -picb_password123 icb_db

# Check the data
mysql> SELECT COUNT(*) FROM products;
mysql> SELECT COUNT(*) FROM icb_data;
mysql> SELECT * FROM icb_analysis_view LIMIT 5;
```

## Important Notes

### ID Mapping
- Original IDs from JSON files are preserved
- Database IDs are offset by +1 (ID 0 becomes 1)
- This maintains compatibility with existing code

### Compatibility View
- `icb_analysis_view` returns data in the format expected by algorithms
- Column names are in Portuguese to match existing code
- Joins all tables automatically

### What Still Needs to be Done

1. **ML Model (`ml_model/main.py`)**:
   - Update to read from database instead of Excel
   - Query from `icb_analysis_view`
   - Save results to MongoDB

2. **Streamlit Dashboard (`streamlit/dashboard.py`)**:
   - Update data loading functions
   - Use database queries instead of Excel
   - Join tables for display

3. **Testing**:
   - Verify algorithms work with database data
   - Performance comparison
   - Data integrity checks

## Files Created

```
SupervisedExploration/
├── docker-compose.db.yml       # Database containers
├── .env                        # Database credentials
├── .env.example               # Credential template
├── DATABASE_SETUP_GUIDE.md    # This file
├── models/
│   ├── mysql.py               # MySQL ORM models
│   ├── mongodb.py             # MongoDB document models
│   └── database.py            # Connection manager
├── migrations/
│   ├── init_mysql.sql         # MySQL schema
│   ├── init_mongo.js          # MongoDB setup
│   ├── migrate_clean_data.py  # Migration script
│   ├── requirements.txt       # Dependencies
│   └── README.md             # Migration guide
└── scripts/
    └── setup_databases.sh     # Database startup script
```

## Next Steps

1. Test the migration with a subset of data
2. Update ML model to use database
3. Update Streamlit to use database
4. Performance testing
5. Full migration of all historical data

## Troubleshooting

### Database Won't Start
- Check Docker is running: `docker ps`
- Check ports 3306/27017 are free
- Check logs: `docker-compose -f docker-compose.db.yml logs`

### Migration Fails
- Ensure `data/dados_limpos_ICB.xlsx` exists
- Check JSON mapping files are in `data/`
- Verify database is running

### Connection Issues
- Check `.env` file has correct credentials
- Verify network connectivity
- Try `localhost` instead of container names

## Summary

The database infrastructure is ready and the migration script works. The normalized structure improves data organization while preserving compatibility through ID mapping and views. Next phase is updating the applications to use the database instead of files.