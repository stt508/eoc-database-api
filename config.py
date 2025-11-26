"""
Configuration for EOC Database API Service (Oracle)

Handles environment variables and database connection settings
for the FastAPI service that provides database access to AI agents.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from loguru import logger

# Import Oracle driver for DSN creation
try:
    import oracledb as cx_Oracle
    logger.info("Using python-oracledb (recommended)")
except ImportError:
    try:
        import cx_Oracle
        logger.warning("Using legacy cx_Oracle")
    except ImportError:
        logger.error("Neither oracledb nor cx_Oracle is installed!")


class DatabaseConfig(BaseSettings):
    """Oracle Database Configuration"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Oracle Connection Settings
    oracle_host: str = Field(..., env="ORACLE_HOST", description="Oracle database hostname")
    oracle_port: int = Field(default=1521, env="ORACLE_PORT", description="Oracle database port") 
    oracle_service_name: Optional[str] = Field(default=None, env="ORACLE_SERVICE_NAME", description="Oracle service name (use this OR sid)")
    oracle_sid: Optional[str] = Field(default=None, env="ORACLE_SID", description="Oracle SID (use this OR service_name)")
    oracle_username: str = Field(..., env="ORACLE_USERNAME", description="Oracle database username")
    oracle_password: str = Field(..., env="ORACLE_PASSWORD", description="Oracle database password")
    
    # Schema Configuration
    oracle_log_schema: str = Field(default="logs", env="ORACLE_LOG_SCHEMA")
    oracle_plan_schema: str = Field(default="ai_plans", env="ORACLE_PLAN_SCHEMA")
    
    # Connection Pool Settings
    oracle_pool_min: int = Field(default=2, env="ORACLE_POOL_MIN")
    oracle_pool_max: int = Field(default=20, env="ORACLE_POOL_MAX")
    oracle_pool_increment: int = Field(default=2, env="ORACLE_POOL_INCREMENT")
    
    # Security and Performance
    db_connection_timeout: int = Field(default=30, env="DB_CONNECTION_TIMEOUT")
    db_query_timeout: int = Field(default=300, env="DB_QUERY_TIMEOUT")
    max_query_results: int = Field(default=5000, env="MAX_QUERY_RESULTS")
    
    def get_dsn(self) -> str:
        """Get Oracle DSN connection string
        
        Supports both SID and Service Name:
        - If ORACLE_SID is set, uses SID format
        - Otherwise uses Service Name format
        """
        if self.oracle_sid:
            # Using SID (legacy format)
            return cx_Oracle.makedsn(self.oracle_host, self.oracle_port, sid=self.oracle_sid)
        elif self.oracle_service_name:
            # Using Service Name (recommended)
            return cx_Oracle.makedsn(self.oracle_host, self.oracle_port, service_name=self.oracle_service_name)
        else:
            raise ValueError("Either ORACLE_SERVICE_NAME or ORACLE_SID must be provided")
    
    def get_connection_string(self) -> str:
        """Get full Oracle connection string"""
        return f"{self.oracle_username}/{self.oracle_password}@{self.get_dsn()}"


class APIConfig(BaseSettings):
    """API Service Configuration"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Server Settings
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_title: str = Field(default="EOC Database API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Security
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=1000, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour


class Config:
    """Main configuration combining all settings"""
    
    def __init__(self):
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        try:
            self.database = DatabaseConfig()
            self.api = APIConfig()
            logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            logger.error("Please ensure environment variables are set")
            raise
    
    def is_ready(self) -> bool:
        """Check if configuration is ready"""
        try:
            # Check required fields
            required_fields = [
                self.database.oracle_host,
                self.database.oracle_username, 
                self.database.oracle_password
            ]
            # Must have either service_name OR sid
            has_connection_id = bool(self.database.oracle_service_name or self.database.oracle_sid)
            
            is_valid = all(required_fields) and has_connection_id
            
            if is_valid:
                conn_type = "SID" if self.database.oracle_sid else "Service Name"
                logger.info(f"✅ Configuration validated (using {conn_type})")
            else:
                logger.warning("❌ Configuration validation failed")
            
            return is_valid
        except Exception as e:
            logger.error(f"❌ Configuration validation error: {e}")
            return False
    
    def get_database_info(self) -> dict:
        """Get safe database connection info (without password)"""
        return {
            "host": self.database.oracle_host,
            "port": self.database.oracle_port,
            "service_name": self.database.oracle_service_name,
            "sid": self.database.oracle_sid,
            "connection_type": "SID" if self.database.oracle_sid else "Service Name",
            "username": self.database.oracle_username,
            "log_schema": self.database.oracle_log_schema,
            "plan_schema": self.database.oracle_plan_schema,
            "pool_size": f"{self.database.oracle_pool_min}-{self.database.oracle_pool_max}"
        }


# Global configuration instance
config = Config()
