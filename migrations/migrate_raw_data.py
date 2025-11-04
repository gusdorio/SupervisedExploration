#!/usr/bin/env python3
"""
Migration Script: Raw Excel Data to SQLite/MySQL
Reads ICB_2s-2025.xlsx directly and migrates to database
Performs basic cleaning during migration
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.mysql import Base, Product, Brand, Establishment, ICBData, ProcessingLog
from models.database import DatabaseManager

# Product classification mapping
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


class RawDataMigrator:
    """Handles migration of raw Excel data to database with cleaning"""

    def __init__(self, data_dir='data'):
        """Initialize migrator with data directory path"""
        self.data_dir = Path(data_dir)
        self.raw_file = self.data_dir / 'ICB_2s-2025.xlsx'

        # Database setup
        self.db_manager = DatabaseManager.get_mysql()
        self.engine = self.db_manager.engine
        self.Session = sessionmaker(bind=self.engine)

        # Data containers
        self.df_raw = None
        self.product_map = {}  # name -> id
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
        """Load and clean raw Excel file"""
        print("\n" + "="*60)
        print("LOADING RAW DATA")
        print("="*60)

        print(f"Loading raw data from: {self.raw_file}")
        self.df_raw = pd.read_excel(self.raw_file, engine='openpyxl')
        print(f"  Loaded {len(self.df_raw)} records")
        print(f"  Columns: {list(self.df_raw.columns)}")

        # Basic cleaning
        print("\nCleaning data...")

        # Remove duplicates
        initial_rows = len(self.df_raw)
        self.df_raw = self.df_raw.drop_duplicates()
        print(f"  Removed {initial_rows - len(self.df_raw)} duplicates")

        # Handle missing values in critical columns
        # Drop rows with missing Product or Establishment
        self.df_raw = self.df_raw.dropna(subset=['Produto', 'Estabelecimento'])

        # Price cleaning - remove negative or zero prices
        price_col = 'Preco' if 'Preco' in self.df_raw.columns else 'Preço'
        if price_col in self.df_raw.columns:
            self.df_raw = self.df_raw[self.df_raw[price_col] > 0]
            print(f"  Final record count: {len(self.df_raw)}")

        # Create mappings
        print("\nCreating ID mappings...")
        unique_products = sorted([str(p) for p in self.df_raw['Produto'].unique() if pd.notna(p)])
        unique_brands = sorted([str(b) for b in self.df_raw['Marca'].unique() if pd.notna(b)])
        unique_establishments = sorted([str(e) for e in self.df_raw['Estabelecimento'].unique() if pd.notna(e)])

        self.product_map = {name: idx for idx, name in enumerate(unique_products)}
        self.brand_map = {name: idx for idx, name in enumerate(unique_brands)}
        self.establishment_map = {name: idx for idx, name in enumerate(unique_establishments)}

        print(f"  Products: {len(self.product_map)}")
        print(f"  Brands: {len(self.brand_map)}")
        print(f"  Establishments: {len(self.establishment_map)}")

        return True

    def create_tables(self):
        """Create database tables if they don't exist"""
        print("\n" + "="*60)
        print("CREATING DATABASE TABLES")
        print("="*60)

        Base.metadata.create_all(self.engine)
        print("Tables created successfully")

    def populate_master_tables(self):
        """Populate normalized master tables"""
        print("\n" + "="*60)
        print("POPULATING MASTER TABLES")
        print("="*60)

        session = self.Session()
        try:
            # Products table
            print("\n1. Creating products...")
            for name, original_id in self.product_map.items():
                existing = session.query(Product).filter_by(name=name).first()
                if not existing:
                    product = Product(
                        id=original_id + 1,  # Offset by 1
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
                        id=original_id + 1,
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
                        id=original_id + 1,
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
        """Migrate data to icb_data table"""
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
            batch_size = 500
            total_records = len(self.df_raw)

            for i in range(0, total_records, batch_size):
                batch_df = self.df_raw.iloc[i:i+batch_size]
                print(f"\nProcessing batch {i//batch_size + 1} ({i+1} to {min(i+batch_size, total_records)})")

                for _, row in batch_df.iterrows():
                    try:
                        # Get IDs (convert to string for lookup)
                        product_id = self.product_map.get(str(row['Produto']), None)
                        if product_id is None:
                            continue

                        brand_id = None
                        if pd.notna(row['Marca']):
                            brand_id = self.brand_map.get(str(row['Marca']), None)

                        establishment_id = self.establishment_map.get(str(row['Estabelecimento']), None)
                        if establishment_id is None:
                            continue

                        # Get product class for flags
                        product_name = row['Produto']
                        product_class = PRODUCT_CLASSES.get(product_name, None)

                        # Parse date
                        collection_date = pd.to_datetime(row['Data_Coleta']).date()

                        # Get price - handle both column names
                        price = row.get('Preco', row.get('Preço', 0))

                        # Create ICB data record
                        icb_record = ICBData(
                            product_id=product_id + 1,  # Offset by 1
                            brand_id=brand_id + 1 if brand_id is not None else None,
                            establishment_id=establishment_id + 1,  # Offset by 1
                            price=float(price),
                            quantity=float(row['Quantidade']) if pd.notna(row.get('Quantidade')) else None,
                            price_per_kg=float(row['PPK']) if pd.notna(row.get('PPK')) else None,
                            collection_date=collection_date,

                            # Set classification flags based on product class
                            is_carnes_vermelhas=(product_class == 'Carnes Vermelhas'),
                            is_graos_massas=(product_class == 'Grãos & Massas'),
                            is_laticinios=(product_class == 'Laticínios'),
                            is_padaria_cozinha=(product_class == 'Padaria & Cozinha'),
                            is_vegetais=(product_class == 'Vegetais'),

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

            print(f"\nData integrity check:")
            print(f"  Expected records: {self.stats['records_inserted']}")
            print(f"  Database records: {data_count}")
            print(f"  Match: {'✅ Yes' if data_count == self.stats['records_inserted'] else '❌ No'}")

        finally:
            session.close()

    def run(self):
        """Execute the complete migration process"""
        print("\n" + "="*60)
        print(" ICB RAW DATA MIGRATION TO DATABASE ")
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
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    # Check if databases are running
    print("Checking database connections...")

    try:
        db_manager = DatabaseManager.get_mysql()
        if db_manager.test_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Could not connect to database: {e}")
        sys.exit(1)

    # Run migration
    migrator = RawDataMigrator()
    success = migrator.run()

    sys.exit(0 if success else 1)
