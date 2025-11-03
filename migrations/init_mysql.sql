-- MySQL Initialization Script for ICB Database
-- This script creates the normalized database structure

-- Ensure we're using the correct database
USE icb_db;

-- Set character encoding
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ==================== NORMALIZED MASTER TABLES ====================

-- Products table (normalized from data)
CREATE TABLE IF NOT EXISTS products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    product_class VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_product_name (name),
    INDEX idx_product_class (product_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Brands table (normalized from data)
CREATE TABLE IF NOT EXISTS brands (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_brand_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Establishments table (normalized from data)
CREATE TABLE IF NOT EXISTS establishments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_establishment_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== MAIN DATA TABLE ====================

-- Main ICB data table with foreign keys
CREATE TABLE IF NOT EXISTS icb_data (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Foreign keys to normalized tables
    product_id INT NOT NULL,
    brand_id INT,
    establishment_id INT NOT NULL,

    -- Core data fields
    price DECIMAL(10, 2) NOT NULL,
    quantity DECIMAL(10, 3),
    price_per_kg DECIMAL(10, 2),
    collection_date DATE NOT NULL,

    -- Classification flags (denormalized for performance)
    is_carnes_vermelhas BOOLEAN DEFAULT FALSE,
    is_graos_massas BOOLEAN DEFAULT FALSE,
    is_laticinios BOOLEAN DEFAULT FALSE,
    is_padaria_cozinha BOOLEAN DEFAULT FALSE,
    is_vegetais BOOLEAN DEFAULT FALSE,

    -- Metadata
    batch_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign key constraints
    CONSTRAINT fk_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_brand FOREIGN KEY (brand_id) REFERENCES brands(id),
    CONSTRAINT fk_establishment FOREIGN KEY (establishment_id) REFERENCES establishments(id),

    -- Indexes for performance
    INDEX idx_collection_date (collection_date),
    INDEX idx_product_date (product_id, collection_date),
    INDEX idx_establishment_date (establishment_id, collection_date),
    INDEX idx_batch_id (batch_id),

    -- Prevent duplicate entries
    UNIQUE KEY uq_product_brand_establishment_date (product_id, brand_id, establishment_id, collection_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== PROCESSING LOG TABLE ====================

CREATE TABLE IF NOT EXISTS processing_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    batch_id VARCHAR(50) UNIQUE NOT NULL,
    process_type VARCHAR(50) NOT NULL,

    -- Statistics
    records_processed INT,
    records_inserted INT,
    records_updated INT,
    records_failed INT,

    -- Status tracking
    status VARCHAR(20) NOT NULL,
    error_message TEXT,

    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,

    -- Indexes
    INDEX idx_process_type (process_type),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== VIEWS FOR COMPATIBILITY ====================

-- Create a view that matches the expected DataFrame format for algorithms
CREATE OR REPLACE VIEW icb_analysis_view AS
SELECT
    p.name AS Produto,
    b.name AS Marca,
    e.name AS Estabelecimento,
    d.price AS Preco,
    d.quantity AS Quantidade,
    d.price_per_kg AS PPK,
    d.collection_date AS Data,
    d.is_carnes_vermelhas AS `Classe_Carnes Vermelhas`,
    d.is_graos_massas AS `Classe_Grãos & Massas`,
    d.is_laticinios AS `Classe_Laticínios`,
    d.is_padaria_cozinha AS `Classe_Padaria & Cozinha`,
    d.is_vegetais AS `Classe_Vegetais`,
    d.batch_id,
    d.product_id,
    d.brand_id,
    d.establishment_id
FROM icb_data d
JOIN products p ON d.product_id = p.id
LEFT JOIN brands b ON d.brand_id = b.id
JOIN establishments e ON d.establishment_id = e.id
ORDER BY d.collection_date DESC, p.name, e.name;