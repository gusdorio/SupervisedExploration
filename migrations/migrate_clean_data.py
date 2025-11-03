#!/usr/bin/env python3
"""
Migration Script: Clean Excel Data to MySQL
Reads dados_limpos_ICB.xlsx and normalizes into MySQL database structure

This script:
1. Loads cleaned data and JSON mappings
2. Creates normalized master tables (products, brands, establishments)
3. Inserts data with proper foreign key references
4. Preserves original ID mappings for compatibility
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.mysql import Base, Product, Brand, Establishment, ICBData, ProcessingLog
from models.database import DatabaseManager, DatabaseConfig

# Product classification mapping (from ICBDataCleaner)
PRODUCT_CLASSES = {
    'Tomate': 'Vegetais',
    'Banana Prata': 'Vegetais',
    'Banana Nanica': 'Vegetais',
    'Batata': 'Vegetais',
    'Carne Bovina Acém': 'Carnes Vermelhas',
    'Carne Bovina Coxão Mole': 'Carnes Vermelhas',
    'Carne Suína Pernil': 'Carnes Vermelhas',
    'Frango Peito': 'Aves',
    'Frango Sobrecoxa': 'Aves',
    'Manteiga': 'Laticínios',
    'Leite': 'Laticínios',
    'Pão': 'Padaria & Cozinha',
    'Ovo': 'Padaria & Cozinha',
    'Farinha de Trigo': 'Padaria & Cozinha',
    'Café': 'Padaria & Cozinha',
    'Açúcar': 'Padaria & Cozinha',
    'Óleo': 'Padaria & Cozinha',
    'Arroz': 'Grãos & Massas',
    'Feijão': 'Grãos & Massas',
    'Macarrão': 'Grãos & Massas',
}


class CleanDataMigrator:
    """Handles migration of cleaned Excel data to MySQL database"""

    def __init__(self, data_dir='data'):
        """Initialize migrator with data directory path"""
        self.data_dir = Path(data_dir)
        self.clean_file = self.data_dir / 'dados_limpos_ICB.xlsx'
        self.product_map_file = self.data_dir / 'mapa_Produto.json'
        self.brand_map_file = self.data_dir / 'mapa_Marca.json'
        self.establishment_map_file = self.data_dir / 'mapa_Estabelecimento.json'

        # Database setup
        self.db_manager = DatabaseManager.get_mysql()
        self.engine = self.db_manager.engine
        self.Session = sessionmaker(bind=self.engine)

        # Data containers
        self.df_clean = None
        self.product_map = {}
        self.brand_map = {}
        self.establishment_map = {}

        # Track migration progress
        self.batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.stats = {
            'products_created': 0,
            'brands_created': 0,
            'establishments_created': 0,
            'records_inserted': 0,
            'records_failed': 0
        }

    def load_data(self):
        """Load cleaned Excel file and JSON mappings"""
        print("\n" + "="*60)
        print("LOADING DATA FILES")
        print("="*60)

        # Load cleaned Excel
        print(f"Loading cleaned data from: {self.clean_file}")
        self.df_clean = pd.read_excel(self.clean_file)
        print(f"  Loaded {len(self.df_clean)} records")

        # Load JSON mappings (Name -> ID)
        print(f"\nLoading mapping files...")

        with open(self.product_map_file, 'r', encoding='utf-8') as f:
            self.product_map = json.load(f)
            print(f"  Products: {len(self.product_map)} mappings")

        with open(self.brand_map_file, 'r', encoding='utf-8') as f:
            self.brand_map = json.load(f)
            print(f"  Brands: {len(self.brand_map)} mappings")

        with open(self.establishment_map_file, 'r', encoding='utf-8') as f:
            self.establishment_map = json.load(f)
            print(f"  Establishments: {len(self.establishment_map)} mappings")

        # Create reverse mappings (ID -> Name)
        self.product_id_to_name = {v: k for k, v in self.product_map.items()}
        self.brand_id_to_name = {v: k for k, v in self.brand_map.items()}
        self.establishment_id_to_name = {v: k for k, v in self.establishment_map.items()}

        return True

    def create_tables(self):
        """Create database tables if they don't exist"""
        print("\n" + "="*60)
        print("CREATING DATABASE TABLES")
        print("="*60)

        Base.metadata.create_all(self.engine)
        print("Tables created successfully")

    def populate_master_tables(self):
        """Populate normalized master tables preserving original IDs"""
        print("\n" + "="*60)
        print("POPULATING MASTER TABLES")
        print("="*60)

        session = self.Session()
        try:
            # Products table
            print("\n1. Creating products...")
            for name, original_id in self.product_map.items():
                # Check if product exists
                existing = session.query(Product).filter_by(name=name).first()
                if not existing:
                    product = Product(
                        id=original_id + 1,  # Offset by 1 since IDs start from 0
                        name=name,
                        product_class=PRODUCT_CLASSES.get(name, None)
                    )
                    session.add(product)
                    self.stats['products_created'] += 1

            session.commit()
            print(f"  Created {self.stats['products_created']} products")

            # Brands table
            print("\n2. Creating brands...")
            for name, original_id in self.brand_map.items():
                existing = session.query(Brand).filter_by(name=name).first()
                if not existing:
                    brand = Brand(
                        id=original_id + 1,  # Offset by 1
                        name=name
                    )
                    session.add(brand)
                    self.stats['brands_created'] += 1

            session.commit()
            print(f"  Created {self.stats['brands_created']} brands")

            # Establishments table
            print("\n3. Creating establishments...")
            for name, original_id in self.establishment_map.items():
                existing = session.query(Establishment).filter_by(name=name).first()
                if not existing:
                    establishment = Establishment(
                        id=original_id + 1,  # Offset by 1
                        name=name
                    )
                    session.add(establishment)
                    self.stats['establishments_created'] += 1

            session.commit()
            print(f"  Created {self.stats['establishments_created']} establishments")

        except Exception as e:
            session.rollback()
            print(f"Error populating master tables: {e}")
            raise
        finally:
            session.close()

    def migrate_data(self):
        """Migrate cleaned data to icb_data table"""
        print("\n" + "="*60)
        print("MIGRATING DATA RECORDS")
        print("="*60)

        session = self.Session()
        log_entry = ProcessingLog(
            batch_id=self.batch_id,
            process_type='import',
            status='started',
            records_processed=0
        )
        session.add(log_entry)
        session.commit()

        try:
            # Process data in batches
            batch_size = 500
            total_records = len(self.df_clean)

            for i in range(0, total_records, batch_size):
                batch_df = self.df_clean.iloc[i:i+batch_size]
                print(f"\nProcessing batch {i//batch_size + 1} ({i+1} to {min(i+batch_size, total_records)})")

                for _, row in batch_df.iterrows():
                    try:
                        # Get product name from ID
                        product_name = self.product_id_to_name.get(row['Produto'], None)
                        if not product_name:
                            print(f"  Warning: Unknown product ID {row['Produto']}")
                            self.stats['records_failed'] += 1
                            continue

                        # Get brand name from ID (can be null)
                        brand_name = None
                        if pd.notna(row['Marca']):
                            brand_name = self.brand_id_to_name.get(int(row['Marca']), None)

                        # Get establishment name from ID
                        establishment_name = self.establishment_id_to_name.get(row['Estabelecimento'], None)
                        if not establishment_name:
                            print(f"  Warning: Unknown establishment ID {row['Estabelecimento']}")
                            self.stats['records_failed'] += 1
                            continue

                        # Create ICB data record
                        icb_record = ICBData(
                            product_id=row['Produto'] + 1,  # Offset by 1
                            brand_id=int(row['Marca']) + 1 if pd.notna(row['Marca']) else None,
                            establishment_id=row['Estabelecimento'] + 1,  # Offset by 1
                            price=row['Preço'],
                            quantity=row.get('Quantidade', None),
                            price_per_kg=row.get('PPK', None),
                            collection_date=pd.to_datetime(row['Data']).date() if 'Data' in row else pd.to_datetime(row['Data_Coleta']).date(),

                            # Set classification flags
                            is_carnes_vermelhas=bool(row.get('Classe_Carnes Vermelhas', False)),
                            is_graos_massas=bool(row.get('Classe_Grãos & Massas', False)),
                            is_laticinios=bool(row.get('Classe_Laticínios', False)),
                            is_padaria_cozinha=bool(row.get('Classe_Padaria & Cozinha', False)),
                            is_vegetais=bool(row.get('Classe_Vegetais', False)),

                            batch_id=self.batch_id
                        )

                        session.add(icb_record)
                        self.stats['records_inserted'] += 1

                    except Exception as e:
                        print(f"  Error processing record: {e}")
                        self.stats['records_failed'] += 1
                        continue

                # Commit batch
                session.commit()
                print(f"  Inserted {self.stats['records_inserted']} records so far")

            # Update log entry
            log_entry.status = 'completed'
            log_entry.records_processed = total_records
            log_entry.records_inserted = self.stats['records_inserted']
            log_entry.records_failed = self.stats['records_failed']
            log_entry.completed_at = datetime.now()
            session.commit()

            print(f"\nMigration completed successfully!")
            print(f"  Total records processed: {total_records}")
            print(f"  Records inserted: {self.stats['records_inserted']}")
            print(f"  Records failed: {self.stats['records_failed']}")

        except Exception as e:
            session.rollback()
            log_entry.status = 'failed'
            log_entry.error_message = str(e)
            session.commit()
            print(f"Migration failed: {e}")
            raise
        finally:
            session.close()

    def verify_migration(self):
        """Verify the migration was successful"""
        print("\n" + "="*60)
        print("VERIFYING MIGRATION")
        print("="*60)

        session = self.Session()
        try:
            # Count records in each table
            product_count = session.query(Product).count()
            brand_count = session.query(Brand).count()
            establishment_count = session.query(Establishment).count()
            data_count = session.query(ICBData).count()

            print(f"\nDatabase record counts:")
            print(f"  Products: {product_count}")
            print(f"  Brands: {brand_count}")
            print(f"  Establishments: {establishment_count}")
            print(f"  ICB Data Records: {data_count}")

            # Sample query to test the view
            result = session.execute(text("SELECT COUNT(*) FROM icb_analysis_view"))
            view_count = result.scalar()
            print(f"  Analysis View Records: {view_count}")

            # Verify data integrity
            print(f"\nData integrity check:")
            print(f"  Original Excel records: {len(self.df_clean)}")
            print(f"  Database records: {data_count}")
            print(f"  Match: {'✅ Yes' if data_count == self.stats['records_inserted'] else '❌ No'}")

        finally:
            session.close()

    def run(self):
        """Execute the complete migration process"""
        print("\n" + "="*60)
        print(" ICB CLEAN DATA MIGRATION TO MYSQL ")
        print("="*60)
        print(f"Batch ID: {self.batch_id}")

        try:
            # Step 1: Load data files
            self.load_data()

            # Step 2: Create tables
            self.create_tables()

            # Step 3: Populate master tables
            self.populate_master_tables()

            # Step 4: Migrate data
            self.migrate_data()

            # Step 5: Verify migration
            self.verify_migration()

            print("\n" + "="*60)
            print(" MIGRATION COMPLETED SUCCESSFULLY ")
            print("="*60)

            return True

        except Exception as e:
            print(f"\nMIGRATION FAILED: {e}")
            return False


if __name__ == "__main__":
    # Check if databases are running
    print("Checking database connections...")

    try:
        db_manager = DatabaseManager.get_mysql()
        if db_manager.test_connection():
            print("✅ MySQL connection successful")
        else:
            print("❌ MySQL connection failed - please start the database first")
            print("Run: docker-compose -f docker-compose.db.yml up -d mysql")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Could not connect to MySQL: {e}")
        print("Run: docker-compose -f docker-compose.db.yml up -d mysql")
        sys.exit(1)

    # Run migration
    migrator = CleanDataMigrator()
    success = migrator.run()

    sys.exit(0 if success else 1)