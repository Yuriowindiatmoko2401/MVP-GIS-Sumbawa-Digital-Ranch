"""
Database configuration for Sumbawa Digital Ranch MVP
Handles PostgreSQL connection with PostGIS extension using SQLAlchemy
"""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from geoalchemy2 import Geometry

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/sumbawa_gis")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=ENVIRONMENT == "development",  # Log SQL queries in development
    pool_pre_ping=True,  # Check connection validity
    pool_recycle=3600,   # Recycle connections every hour
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base model for declarative ORM
Base = declarative_base()

# Import all models to ensure they are registered with SQLAlchemy
# These imports are required for Base.metadata.create_all() to work properly
# Import after Base is defined to avoid circular imports
import app.models.cattle
import app.models.cattle_history
import app.models.resource
import app.models.geofence

# Metadata for PostGIS
metadata = MetaData()


def get_db() -> Session:
    """
    Dependency function to get database session
    Used in FastAPI endpoint dependencies
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    """
    Test database connection and PostGIS extension
    Returns True if connection successful and PostGIS available
    """
    try:
        db = SessionLocal()
        # Test basic connection
        result = db.execute("SELECT 1").scalar()
        if result != 1:
            return False

        # Test PostGIS extension
        postgis_check = db.execute("""
            SELECT 1 FROM pg_extension WHERE extname = 'postgis'
        """).scalar()

        if postgis_check != 1:
            # Try to create PostGIS extension
            try:
                db.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                db.commit()
            except Exception as e:
                print(f"Warning: Could not create PostGIS extension: {e}")
                return False

        db.close()
        return True

    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Test connection when run directly
    print(f"Testing connection to: {DATABASE_URL}")
    print(f"Environment: {ENVIRONMENT}")
    print(f"PostGIS available: {test_connection()}")