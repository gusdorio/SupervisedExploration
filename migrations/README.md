# ICB Database Migration Setup

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies for migration
pip install -r migrations/requirements.txt
```

### 2. Start Databases

```bash
# Start MySQL and MongoDB containers
./scripts/setup_databases.sh

# Or manually:
docker-compose -f docker-compose.db.yml up -d
```

### 3. Run Migration

```bash
# Migrate cleaned Excel data to MySQL
python migrations/migrate_clean_data.py
```

## What This Migration Does

### Data Flow
```
dados_limpos_ICB.xlsx + JSON mappings
            ↓
     migrate_clean_data.py
            ↓
    Normalized MySQL Tables:
    - products (master table)
    - brands (master table)
    - establishments (master table)
    - icb_data (main data with FKs)
```

### Key Features

1. **Preserves Original IDs**: The migration maintains the original numeric IDs from the JSON mapping files (with +1 offset for database compatibility)

2. **Normalization**: Data is properly normalized into separate tables for:
   - Products (with classification)
   - Brands
   - Establishments

3. **Compatibility View**: Creates `icb_analysis_view` that returns data in the format expected by existing algorithms

4. **Classification Flags**: Boolean columns for each product class are preserved in the main data table

## Database Schema

### Master Tables
- `products`: id, name, product_class
- `brands`: id, name
- `establishments`: id, name

### Main Data Table
- `icb_data`: Contains price observations with foreign keys to master tables

### Compatibility View
- `icb_analysis_view`: Joins all tables and returns Portuguese column names

## Files Structure

```
migrations/
├── init_mysql.sql           # MySQL schema creation
├── init_mongo.js           # MongoDB collections setup
├── migrate_clean_data.py   # Main migration script
├── requirements.txt        # Python dependencies
└── README.md              # This file

data/
├── dados_limpos_ICB.xlsx  # Cleaned data (input)
├── mapa_Produto.json      # Product ID mappings
├── mapa_Marca.json        # Brand ID mappings
└── mapa_Estabelecimento.json # Establishment ID mappings
```

## Connection Details

### MySQL
- Host: localhost
- Port: 3306
- Database: icb_db
- User: icb_user
- Password: icb_password123

### MongoDB
- Host: localhost
- Port: 27017
- Database: icb_ml
- User: root
- Password: root_password123

## Useful Commands

```bash
# Check database status
docker ps | grep icb

# Connect to MySQL
docker exec -it icb_mysql mysql -u icb_user -picb_password123 icb_db

# Connect to MongoDB
docker exec -it icb_mongodb mongosh -u root -p root_password123

# View logs
docker-compose -f docker-compose.db.yml logs -f

# Stop databases
docker-compose -f docker-compose.db.yml down

# Remove data and start fresh
docker-compose -f docker-compose.db.yml down -v
docker-compose -f docker-compose.db.yml up -d
```

## Troubleshooting

### Connection Failed
- Ensure Docker is running
- Check if containers are up: `docker ps`
- Verify ports 3306 and 27017 are not in use

### Migration Failed
- Check if cleaned data exists: `data/dados_limpos_ICB.xlsx`
- Verify JSON mappings exist in data folder
- Check database logs: `docker-compose -f docker-compose.db.yml logs`

### Data Integrity
The migration script includes verification that:
- All master records are created
- Foreign key relationships are valid
- Record counts match between Excel and database