"""
Database Connection Manager
Centralized database configuration for both MySQL and MongoDB
Shared by both ML Model and Streamlit applications
"""

import os
from typing import Optional
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from mongoengine import connect, disconnect
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """
    Database configuration from environment variables
    """
    # MySQL Configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'icb_db')
    MYSQL_USER = os.getenv('MYSQL_USER', 'icb_user')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password')

    # MongoDB Configuration
    MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
    MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
    MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'icb_ml')
    MONGO_USER = os.getenv('MONGO_USER', '')
    MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', '')

    # Connection Pool Settings
    POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 5))
    MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', 10))
    POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', 3600))

    @classmethod
    def get_mysql_url(cls) -> str:
        """Generate MySQL connection URL"""
        if cls.MYSQL_PASSWORD:
            return f"mysql+pymysql://{cls.MYSQL_USER}:{cls.MYSQL_PASSWORD}@{cls.MYSQL_HOST}:{cls.MYSQL_PORT}/{cls.MYSQL_DATABASE}"
        return f"mysql+pymysql://{cls.MYSQL_USER}@{cls.MYSQL_HOST}:{cls.MYSQL_PORT}/{cls.MYSQL_DATABASE}"

    @classmethod
    def get_mongo_url(cls) -> str:
        """Generate MongoDB connection URL"""
        if cls.MONGO_USER and cls.MONGO_PASSWORD:
            return f"mongodb://{cls.MONGO_USER}:{cls.MONGO_PASSWORD}@{cls.MONGO_HOST}:{cls.MONGO_PORT}/{cls.MONGO_DATABASE}"
        return f"mongodb://{cls.MONGO_HOST}:{cls.MONGO_PORT}/{cls.MONGO_DATABASE}"


class MySQLConnection:
    """
    MySQL connection manager using SQLAlchemy
    Implements singleton pattern for connection pooling
    """
    _instance: Optional['MySQLConnection'] = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize MySQL connection engine and session factory"""
        try:
            self._engine = create_engine(
                DatabaseConfig.get_mysql_url(),
                poolclass=QueuePool,
                pool_size=DatabaseConfig.POOL_SIZE,
                max_overflow=DatabaseConfig.MAX_OVERFLOW,
                pool_recycle=DatabaseConfig.POOL_RECYCLE,
                echo=False  # Set to True for SQL debugging
            )
            self._session_factory = sessionmaker(bind=self._engine)
            logger.info("MySQL connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MySQL connection: {e}")
            raise

    @property
    def engine(self):
        """Get SQLAlchemy engine"""
        return self._engine

    def get_session(self) -> Session:
        """Get a new database session"""
        return self._session_factory()

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope for database operations

        Usage:
            with mysql_conn.session_scope() as session:
                session.query(Model).filter(...).all()
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def create_tables(self):
        """Create all tables defined in models"""
        from models.mysql import Base
        Base.metadata.create_all(self._engine)
        logger.info("MySQL tables created successfully")

    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        from models.mysql import Base
        Base.metadata.drop_all(self._engine)
        logger.warning("All MySQL tables dropped")

    def test_connection(self) -> bool:
        """Test MySQL connection"""
        try:
            with self._engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("MySQL connection test successful")
            return True
        except Exception as e:
            logger.error(f"MySQL connection test failed: {e}")
            return False


class MongoDBConnection:
    """
    MongoDB connection manager using MongoEngine and PyMongo
    Implements singleton pattern
    """
    _instance: Optional['MongoDBConnection'] = None
    _client: Optional[MongoClient] = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize MongoDB connection"""
        try:
            # Initialize MongoEngine connection
            connect(
                db=DatabaseConfig.MONGO_DATABASE,
                host=DatabaseConfig.get_mongo_url(),
                alias='default'
            )

            # Also create PyMongo client for direct operations
            self._client = MongoClient(DatabaseConfig.get_mongo_url())
            self._db = self._client[DatabaseConfig.MONGO_DATABASE]

            logger.info("MongoDB connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise

    @property
    def client(self) -> MongoClient:
        """Get PyMongo client"""
        return self._client

    @property
    def db(self):
        """Get MongoDB database instance"""
        return self._db

    def get_collection(self, collection_name: str):
        """Get a specific collection"""
        return self._db[collection_name]

    def test_connection(self) -> bool:
        """Test MongoDB connection"""
        try:
            # Ping the MongoDB server
            self._client.admin.command('ping')
            logger.info("MongoDB connection test successful")
            return True
        except Exception as e:
            logger.error(f"MongoDB connection test failed: {e}")
            return False

    def close_connection(self):
        """Close MongoDB connections"""
        if self._client:
            self._client.close()
        disconnect(alias='default')
        logger.info("MongoDB connections closed")


class DatabaseManager:
    """
    Unified database manager for both MySQL and MongoDB
    Provides simplified interface for both applications
    """
    _mysql: Optional[MySQLConnection] = None
    _mongodb: Optional[MongoDBConnection] = None

    @classmethod
    def get_mysql(cls) -> MySQLConnection:
        """Get MySQL connection instance"""
        if cls._mysql is None:
            cls._mysql = MySQLConnection()
        return cls._mysql

    @classmethod
    def get_mongodb(cls) -> MongoDBConnection:
        """Get MongoDB connection instance"""
        if cls._mongodb is None:
            cls._mongodb = MongoDBConnection()
        return cls._mongodb

    @classmethod
    def initialize_all(cls):
        """Initialize all database connections"""
        logger.info("Initializing all database connections...")
        cls.get_mysql()
        cls.get_mongodb()
        logger.info("All database connections initialized")

    @classmethod
    def test_all_connections(cls) -> dict:
        """Test all database connections"""
        results = {
            'mysql': cls.get_mysql().test_connection(),
            'mongodb': cls.get_mongodb().test_connection()
        }
        return results

    @classmethod
    def close_all(cls):
        """Close all database connections"""
        if cls._mongodb:
            cls._mongodb.close_connection()
        logger.info("All database connections closed")


# Convenience functions for direct import
def get_mysql_session() -> Session:
    """Quick function to get a MySQL session"""
    return DatabaseManager.get_mysql().get_session()


def get_mongo_db():
    """Quick function to get MongoDB database"""
    return DatabaseManager.get_mongodb().db


def get_mongo_collection(collection_name: str):
    """Quick function to get a MongoDB collection"""
    return DatabaseManager.get_mongodb().get_collection(collection_name)


# Initialize connections when module is imported (optional)
# Uncomment if you want auto-initialization
# DatabaseManager.initialize_all()