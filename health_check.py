"""
Health Check and Validation Module

Provides comprehensive health checks for the database API service.
"""

from typing import Dict, Any
from datetime import datetime
from loguru import logger

from config import config
from database import connection_pool, db_service


class HealthChecker:
    """Comprehensive health checking for the API service"""
    
    def __init__(self):
        self.service_start_time = datetime.now()
    
    def check_configuration(self) -> Dict[str, Any]:
        """Check if configuration is valid"""
        try:
            is_ready = config.is_ready()
            db_info = config.get_database_info()
            
            return {
                "status": "healthy" if is_ready else "unhealthy",
                "configuration_valid": is_ready,
                "database_info": db_info,
                "api_info": {
                    "host": config.api.api_host,
                    "port": config.api.api_port,
                    "environment": config.api.environment,
                    "api_key_configured": config.api.api_key is not None
                }
            }
        except Exception as e:
            logger.error(f"Configuration health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_database_connection(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            result = db_service.test_connection()
            return {
                "status": "healthy" if result["success"] else "unhealthy",
                "connection_test": result,
                "pool_initialized": connection_pool.initialized
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_database_tables(self) -> Dict[str, Any]:
        """Check if required database tables exist"""
        try:
            with connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for key tables
                required_tables = [
                    'orders',
                    'payments',
                    'shipping',
                    'inventory_reservations',
                    'customers',
                    'audit_log',
                    'error_log'
                ]
                
                table_status = {}
                for table in required_tables:
                    try:
                        # Try to select from each table
                        cursor.execute(f"SELECT 1 FROM {config.database.oracle_log_schema}.{table} WHERE ROWNUM = 1")
                        table_status[table] = "exists"
                    except Exception:
                        table_status[table] = "missing"
                
                cursor.close()
                
                all_exist = all(status == "exists" for status in table_status.values())
                
                return {
                    "status": "healthy" if all_exist else "degraded",
                    "tables": table_status,
                    "all_tables_exist": all_exist
                }
        except Exception as e:
            logger.error(f"Table health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        config_health = self.check_configuration()
        db_health = self.check_database_connection()
        table_health = self.check_database_tables()
        
        uptime = (datetime.now() - self.service_start_time).total_seconds()
        
        # Overall status determination
        statuses = [
            config_health.get("status"),
            db_health.get("status"),
            table_health.get("status")
        ]
        
        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif "unhealthy" in statuses:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "checks": {
                "configuration": config_health,
                "database_connection": db_health,
                "database_tables": table_health
            }
        }


# Global health checker instance
health_checker = HealthChecker()

