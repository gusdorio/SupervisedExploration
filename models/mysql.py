"""
Simplified MySQL ORM Models with Normalized Structure
Focus on data normalization for products, brands, and establishments
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Index, UniqueConstraint, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


# ==================== NORMALIZED MASTER TABLES ====================

class Product(Base):
    """
    Master table for products - normalized from the data
    Each product has a standardized name and classification
    """
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # Standardized product name

    # Product classification (from ICBDataCleaner logic)
    product_class = Column(String(50), nullable=True)  # e.g., 'Vegetais', 'Carnes Vermelhas'

    # One-to-many relationship with ICB data
    icb_records = relationship("ICBData", back_populates="product")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', class='{self.product_class}')>"


class Brand(Base):
    """
    Master table for brands - normalized from the data
    """
    __tablename__ = 'brands'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # Standardized brand name

    # One-to-many relationship with ICB data
    icb_records = relationship("ICBData", back_populates="brand")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}')>"


class Establishment(Base):
    """
    Master table for establishments - normalized from the data
    """
    __tablename__ = 'establishments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # Establishment name

    # One-to-many relationship with ICB data
    icb_records = relationship("ICBData", back_populates="establishment")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<Establishment(id={self.id}, name='{self.name}')>"


# ==================== MAIN DATA TABLE ====================

class ICBData(Base):
    """
    Main ICB (Cesta Básica) data table
    Each row represents a price observation with normalized foreign keys
    """
    __tablename__ = 'icb_data'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys to normalized tables
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=True)
    establishment_id = Column(Integer, ForeignKey('establishments.id'), nullable=False)

    # Core data fields
    price = Column(Float, nullable=False)  # Price (Preço)
    quantity = Column(Float, nullable=True)  # Quantity (Quantidade)
    price_per_kg = Column(Float, nullable=True)  # Calculated PPK
    collection_date = Column(Date, nullable=False)  # Data collection date (Data_Coleta)

    # Classification flags (derived from product classification)
    # These are denormalized for query performance
    is_carnes_vermelhas = Column(Boolean, default=False)
    is_graos_massas = Column(Boolean, default=False)
    is_laticinios = Column(Boolean, default=False)
    is_padaria_cozinha = Column(Boolean, default=False)
    is_vegetais = Column(Boolean, default=False)

    # Metadata
    batch_id = Column(String(50), nullable=True)  # For tracking import batches
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="icb_records")
    brand = relationship("Brand", back_populates="icb_records")
    establishment = relationship("Establishment", back_populates="icb_records")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_collection_date', 'collection_date'),
        Index('idx_product_date', 'product_id', 'collection_date'),
        Index('idx_establishment_date', 'establishment_id', 'collection_date'),
        Index('idx_batch_id', 'batch_id'),
        # Ensure no duplicate entries for same product/establishment/date
        UniqueConstraint('product_id', 'brand_id', 'establishment_id', 'collection_date',
                        name='uq_product_brand_establishment_date')
    )

    def __repr__(self):
        return f"<ICBData(product_id={self.product_id}, price={self.price}, date={self.collection_date})>"


# ==================== PROCESSING LOG ====================

class ProcessingLog(Base):
    """
    Track data processing operations and batches
    """
    __tablename__ = 'processing_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(50), unique=True, nullable=False)
    process_type = Column(String(50), nullable=False)  # 'import', 'cleaning', 'ml_training', 'prediction'

    # Statistics
    records_processed = Column(Integer, nullable=True)
    records_inserted = Column(Integer, nullable=True)
    records_updated = Column(Integer, nullable=True)
    records_failed = Column(Integer, nullable=True)

    # Status tracking
    status = Column(String(20), nullable=False)  # 'started', 'completed', 'failed'
    error_message = Column(String(500), nullable=True)

    # Timestamps
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Index for queries
    __table_args__ = (
        Index('idx_process_type', 'process_type'),
        Index('idx_status', 'status'),
        Index('idx_started_at', 'started_at'),
    )

    def __repr__(self):
        return f"<ProcessingLog(batch_id='{self.batch_id}', type='{self.process_type}', status='{self.status}')>"