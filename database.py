"""
Oracle Database Service for Log Analysis API

Provides secure, pooled access to Oracle database with
comprehensive logging and error handling.
"""

import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from contextlib import contextmanager
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import config

# Try to use modern oracledb, fall back to cx_Oracle if needed
try:
    import oracledb as cx_Oracle
    logger.info("Using python-oracledb (recommended)")
except ImportError:
    try:
        import cx_Oracle
        logger.warning("Using legacy cx_Oracle - consider upgrading to python-oracledb")
    except ImportError:
        logger.error("Neither oracledb nor cx_Oracle is installed!")
        raise ImportError("Please install python-oracledb: pip install oracledb")

class OracleConnectionPool:
    """Manages Oracle database connection pool"""
    
    def __init__(self):
        self.pool = None
        self.initialized = False
        
    def initialize_pool(self):
        """Initialize the Oracle connection pool"""
        try:
            # Create connection pool
            # Note: python-oracledb doesn't need encoding/threaded params
            self.pool = cx_Oracle.create_pool(
                user=config.database.oracle_username,
                password=config.database.oracle_password,
                dsn=config.database.get_dsn(),
                min=config.database.oracle_pool_min,
                max=config.database.oracle_pool_max,
                increment=config.database.oracle_pool_increment
            )
            
            self.initialized = True
            logger.info(f"Oracle connection pool initialized: {config.database.oracle_pool_min}-{config.database.oracle_pool_max} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize Oracle connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with automatic cleanup"""
        if not self.initialized:
            self.initialize_pool()
        
        connection = None
        try:
            connection = self.pool.acquire()
            connection.callTimeout = config.database.db_query_timeout * 1000  # Convert to ms
            yield connection
        finally:
            if connection:
                try:
                    self.pool.release(connection)
                except Exception as e:
                    logger.warning(f"Error releasing connection: {e}")
    
    def close_pool(self):
        """Close the connection pool"""
        if self.pool:
            self.pool.close()
            self.initialized = False
            logger.info("Oracle connection pool closed")

# Global connection pool
connection_pool = OracleConnectionPool()

class DatabaseService:
    """Service for executing Oracle database queries"""
    
    def __init__(self):
        self.log_schema = config.database.oracle_log_schema
        self.plan_schema = config.database.oracle_plan_schema
        self.max_results = config.database.max_query_results
        
        # Predefined safe queries
        self.queries = {
            "order_status": f"""
                SELECT order_id, customer_id, status, total_amount, 
                       created_date, last_updated, order_type, priority
                FROM {self.log_schema}.orders 
                WHERE order_id = :order_id
            """,
            
            "payment_details": f"""
                SELECT payment_id, order_id, status, amount, payment_method,
                       transaction_id, created_date, processed_date, 
                       error_code, error_message, retry_count
                FROM {self.log_schema}.payments 
                WHERE order_id = :order_id
                ORDER BY created_date DESC
            """,
            
            "shipping_info": f"""
                SELECT shipping_id, order_id, status, tracking_number,
                       carrier, service_type, shipped_date, expected_delivery,
                       actual_delivery, shipping_address, special_instructions
                FROM {self.log_schema}.shipping 
                WHERE order_id = :order_id
            """,
            
            "inventory_status": f"""
                SELECT item_id, order_id, product_id, sku, quantity_ordered,
                       quantity_allocated, quantity_shipped, warehouse_location,
                       reservation_status, allocation_date, shipped_date
                FROM {self.log_schema}.inventory_reservations 
                WHERE order_id = :order_id
            """,
            
            "audit_trail": f"""
                SELECT log_id, order_id, action_type, action_details,
                       performed_by, performed_at, system_component,
                       result_status, error_details, session_id
                FROM {self.log_schema}.audit_log 
                WHERE order_id = :order_id
                ORDER BY performed_at DESC
                FETCH FIRST :max_results ROWS ONLY
            """,
            
            "error_log": f"""
                SELECT error_id, order_id, error_code, error_message,
                       error_timestamp, component, severity, stack_trace,
                       user_context, correlation_id
                FROM {self.log_schema}.error_log 
                WHERE order_id = :order_id
                ORDER BY error_timestamp DESC
                FETCH FIRST :max_results ROWS ONLY
            """,
            
            "customer_info": f"""
                SELECT customer_id, customer_type, account_status, tier,
                       created_date, last_login_date, risk_score, 
                       contact_preferences, billing_address, shipping_address
                FROM {self.log_schema}.customers 
                WHERE customer_id = :customer_id
            """,
            
            "system_events": f"""
                SELECT event_id, order_id, event_type, event_data,
                       event_timestamp, source_system, correlation_id,
                       processing_status, retry_count
                FROM {self.log_schema}.system_events 
                WHERE order_id = :order_id
                ORDER BY event_timestamp DESC
                FETCH FIRST :max_results ROWS ONLY
            """,
            
            "order_timeline": f"""
                SELECT 
                    'ORDER' as event_source,
                    created_date as event_timestamp,
                    'Order Created' as event_description,
                    status as event_data
                FROM {self.log_schema}.orders WHERE order_id = :order_id
                UNION ALL
                SELECT 
                    'PAYMENT' as event_source,
                    created_date as event_timestamp,
                    'Payment ' || status as event_description,
                    amount || ' via ' || payment_method as event_data
                FROM {self.log_schema}.payments WHERE order_id = :order_id
                UNION ALL
                SELECT 
                    'SHIPPING' as event_source,
                    shipped_date as event_timestamp,
                    'Shipment ' || status as event_description,
                    tracking_number as event_data
                FROM {self.log_schema}.shipping WHERE order_id = :order_id AND shipped_date IS NOT NULL
                UNION ALL
                SELECT 
                    'AUDIT' as event_source,
                    performed_at as event_timestamp,
                    action_type as event_description,
                    performed_by as event_data
                FROM {self.log_schema}.audit_log WHERE order_id = :order_id
                ORDER BY event_timestamp DESC
            """,
            
            "related_orders": f"""
                SELECT DISTINCT o.order_id, o.status, o.created_date, o.customer_id
                FROM {self.log_schema}.orders o
                WHERE o.customer_id = (
                    SELECT customer_id FROM {self.log_schema}.orders WHERE order_id = :order_id
                )
                AND o.order_id != :order_id
                AND o.created_date >= (
                    SELECT created_date - INTERVAL '30' DAY 
                    FROM {self.log_schema}.orders WHERE order_id = :order_id
                )
                ORDER BY o.created_date DESC
                FETCH FIRST 10 ROWS ONLY
            """,
            
            "performance_metrics": f"""
                SELECT 
                    component_name,
                    avg_response_time_ms,
                    error_rate_percent,
                    last_updated,
                    status
                FROM {self.log_schema}.system_performance
                WHERE last_updated >= SYSTIMESTAMP - INTERVAL '1' HOUR
                ORDER BY error_rate_percent DESC
            """,
            
            "search_orders_by_customer": f"""
                SELECT order_id, status, total_amount, created_date, order_type
                FROM {self.log_schema}.orders
                WHERE customer_id = :customer_id
                ORDER BY created_date DESC
                FETCH FIRST :max_results ROWS ONLY
            """,
            
            "search_orders_by_status": f"""
                SELECT order_id, customer_id, status, total_amount, created_date, last_updated
                FROM {self.log_schema}.orders
                WHERE status = :status
                AND created_date >= :start_date
                ORDER BY created_date DESC
                FETCH FIRST :max_results ROWS ONLY
            """,
            
            "search_message_logs": """
                SELECT 
                    MSGID, VMID, INTER_TYPE, OPERATION, USER_ID,
                    USER_DATA1, USER_DATA2, USER_DATA3,
                    CREATION_TIME, SEND_TIME, RECEIVE_TIME,
                    RECEIVE_CHARSET, SEND_MSG_PRIORITY, RECEIVE_MSG_PRIORITY,
                    SEND_MSG_SEQID, RECEIVE_MSG_SEQID,
                    SEND_MSG_RETRYCOUNT, RECEIVE_MSG_RETRYCOUNT,
                    SEND_MSG_CORRELTIONID, RECEIVE_MSG_CORRELTIONID,
                    ACCOUNT_ID, ORDER_ID, PROCESS_ID, TRANSACTION_ID,
                    ACTIVITY_ID, CUSTOMER_ID, FAILURE, ATTEMPTCOUNT,
                    APP_NAME, SERVICE_PORT
                    {blob_fields}
                FROM {schema}.CWMESSAGELOG
                WHERE 1=1
                {user_data1_filter}
                {user_data2_filter}
                {user_data3_filter}
                {order_id_filter}
                {customer_id_filter}
                {operation_filter}
                {date_filter}
                ORDER BY CREATION_TIME DESC
                FETCH FIRST :max_results ROWS ONLY
            """,
            
            "get_message_log_by_id": """
                SELECT 
                    MSGID, VMID, INTER_TYPE, OPERATION, USER_ID,
                    USER_DATA1, USER_DATA2, USER_DATA3,
                    CREATION_TIME, SEND_TIME, RECEIVE_TIME,
                    RECEIVE_CHARSET, SEND_MSG_PRIORITY, RECEIVE_MSG_PRIORITY,
                    SEND_MSG_SEQID, RECEIVE_MSG_SEQID,
                    SEND_MSG_RETRYCOUNT, RECEIVE_MSG_RETRYCOUNT,
                    SEND_MSG_CORRELTIONID, RECEIVE_MSG_CORRELTIONID,
                    ACCOUNT_ID, ORDER_ID, PROCESS_ID, TRANSACTION_ID,
                    ACTIVITY_ID, CUSTOMER_ID, FAILURE, ATTEMPTCOUNT,
                    APP_NAME, SERVICE_PORT,
                    SEND_DATA, RECEIVE_DATA, SEND_MSG_PROPS, RECEIVE_MSG_PROPS
                FROM {schema}.CWMESSAGELOG
                WHERE MSGID = :msgid
            """
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def execute_query(self, query_name: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a predefined query safely"""
        
        if query_name not in self.queries:
            raise ValueError(f"Unknown query: {query_name}")
        
        # Add default parameters
        if "max_results" not in parameters:
            parameters["max_results"] = self.max_results
        
        with connection_pool.get_connection() as connection:
            cursor = connection.cursor()
            
            try:
                query_sql = self.queries[query_name]
                logger.debug(f"Executing query {query_name} with parameters: {parameters}")
                
                cursor.execute(query_sql, parameters)
                
                # Get column names
                columns = [desc[0].lower() for desc in cursor.description]
                
                # Fetch results and convert to dict
                results = []
                for row in cursor:
                    row_dict = {}
                    for i, value in enumerate(row):
                        # Convert Oracle types to JSON-serializable types
                        if isinstance(value, cx_Oracle.LOB):
                            row_dict[columns[i]] = value.read()
                        elif isinstance(value, datetime):
                            row_dict[columns[i]] = value.isoformat()
                        elif value is None:
                            row_dict[columns[i]] = None
                        else:
                            row_dict[columns[i]] = value
                    
                    results.append(row_dict)
                    
                    # Safety limit
                    if len(results) >= self.max_results:
                        logger.warning(f"Query {query_name} hit result limit")
                        break
                
                logger.info(f"Query {query_name} returned {len(results)} results")
                return results
                
            finally:
                cursor.close()
    
    def get_complete_order_data(self, order_id: str) -> Dict[str, Any]:
        """Get comprehensive order data from all related tables"""
        
        try:
            # Execute all relevant queries
            order_info = self.execute_query("order_status", {"order_id": order_id})
            
            if not order_info:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found",
                    "order_exists": False
                }
            
            order_data = order_info[0]
            customer_id = order_data.get("customer_id")
            
            # Get all related data
            payment_data = self.execute_query("payment_details", {"order_id": order_id})
            shipping_data = self.execute_query("shipping_info", {"order_id": order_id})
            inventory_data = self.execute_query("inventory_status", {"order_id": order_id})
            audit_data = self.execute_query("audit_trail", {"order_id": order_id, "max_results": 50})
            error_data = self.execute_query("error_log", {"order_id": order_id, "max_results": 20})
            system_events = self.execute_query("system_events", {"order_id": order_id, "max_results": 30})
            timeline_data = self.execute_query("order_timeline", {"order_id": order_id})
            
            # Get customer info if available
            customer_data = None
            if customer_id:
                customer_info = self.execute_query("customer_info", {"customer_id": customer_id})
                customer_data = customer_info[0] if customer_info else None
            
            # Get related orders
            related_orders = self.execute_query("related_orders", {"order_id": order_id})
            
            return {
                "success": True,
                "order_exists": True,
                "order_id": order_id,
                "order_info": order_data,
                "customer_info": customer_data,
                "payments": payment_data,
                "shipping": shipping_data,
                "inventory": inventory_data,
                "audit_trail": audit_data,
                "error_log": error_data,
                "system_events": system_events,
                "timeline": timeline_data,
                "related_orders": related_orders,
                "query_timestamp": datetime.now().isoformat(),
                "data_summary": {
                    "total_payments": len(payment_data),
                    "total_shipments": len(shipping_data),
                    "total_inventory_items": len(inventory_data),
                    "total_audit_entries": len(audit_data),
                    "total_errors": len(error_data),
                    "total_events": len(system_events),
                    "timeline_entries": len(timeline_data),
                    "related_orders_count": len(related_orders)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get complete order data for {order_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": order_id,
                "order_exists": False
            }
    
    def search_orders(self, 
                     customer_id: Optional[str] = None,
                     status: Optional[str] = None,
                     start_date: Optional[str] = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """Search orders by various criteria"""
        
        try:
            if customer_id:
                return self.execute_query("search_orders_by_customer", {
                    "customer_id": customer_id,
                    "max_results": limit
                })
            elif status and start_date:
                return self.execute_query("search_orders_by_status", {
                    "status": status,
                    "start_date": start_date,
                    "max_results": limit
                })
            else:
                raise ValueError("Must provide either customer_id or both status and start_date")
                
        except Exception as e:
            logger.error(f"Order search failed: {e}")
            raise
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        
        try:
            metrics = self.execute_query("performance_metrics", {})
            
            return {
                "success": True,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_message_logs(self,
                           user_data1: Optional[str] = None,
                           user_data2: Optional[str] = None,
                           user_data3: Optional[str] = None,
                           order_id: Optional[str] = None,
                           customer_id: Optional[str] = None,
                           operation: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           limit: int = 100,
                           include_blob_data: bool = False) -> List[Dict[str, Any]]:
        """Search CWMESSAGELOG table with flexible criteria"""
        
        try:
            import base64
            
            # Build dynamic query
            query_template = self.queries["search_message_logs"]
            
            # Add BLOB fields if requested
            if include_blob_data:
                blob_fields = ", SEND_DATA, RECEIVE_DATA, SEND_MSG_PROPS, RECEIVE_MSG_PROPS"
            else:
                blob_fields = ""
            
            # Build filters dictionary for proper replacement
            filter_dict = {
                "user_data1_filter": "",
                "user_data2_filter": "",
                "user_data3_filter": "",
                "order_id_filter": "",
                "customer_id_filter": "",
                "operation_filter": "",
                "date_filter": ""
            }
            parameters = {"max_results": limit}
            
            if user_data1:
                filter_dict["user_data1_filter"] = "AND USER_DATA1 = :user_data1"
                parameters["user_data1"] = user_data1
            
            if user_data2:
                filter_dict["user_data2_filter"] = "AND USER_DATA2 = :user_data2"
                parameters["user_data2"] = user_data2
            
            if user_data3:
                filter_dict["user_data3_filter"] = "AND USER_DATA3 = :user_data3"
                parameters["user_data3"] = user_data3
            
            if order_id:
                filter_dict["order_id_filter"] = "AND ORDER_ID = :order_id"
                parameters["order_id"] = order_id
            
            if customer_id:
                filter_dict["customer_id_filter"] = "AND CUSTOMER_ID = :customer_id"
                parameters["customer_id"] = customer_id
            
            if operation:
                filter_dict["operation_filter"] = "AND OPERATION = :operation"
                parameters["operation"] = operation
            
            if start_date and end_date:
                filter_dict["date_filter"] = "AND CREATION_TIME BETWEEN TO_TIMESTAMP(:start_date, 'YYYY-MM-DD\"T\"HH24:MI:SS') AND TO_TIMESTAMP(:end_date, 'YYYY-MM-DD\"T\"HH24:MI:SS')"
                parameters["start_date"] = start_date
                parameters["end_date"] = end_date
            elif start_date:
                filter_dict["date_filter"] = "AND CREATION_TIME >= TO_TIMESTAMP(:start_date, 'YYYY-MM-DD\"T\"HH24:MI:SS')"
                parameters["start_date"] = start_date
            
            # Replace template placeholders
            query_sql = query_template.replace("{blob_fields}", blob_fields)
            query_sql = query_sql.replace("{schema}", self.log_schema)
            query_sql = query_sql.replace("{user_data1_filter}", filter_dict["user_data1_filter"])
            query_sql = query_sql.replace("{user_data2_filter}", filter_dict["user_data2_filter"])
            query_sql = query_sql.replace("{user_data3_filter}", filter_dict["user_data3_filter"])
            query_sql = query_sql.replace("{order_id_filter}", filter_dict["order_id_filter"])
            query_sql = query_sql.replace("{customer_id_filter}", filter_dict["customer_id_filter"])
            query_sql = query_sql.replace("{operation_filter}", filter_dict["operation_filter"])
            query_sql = query_sql.replace("{date_filter}", filter_dict["date_filter"])
            
            # Clean up query
            query_sql = " ".join(query_sql.split())  # Remove extra whitespace
            
            logger.info(f"Executing message log search with SQL: {query_sql[:500]}...")
            logger.info(f"Parameters: {parameters}")
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, parameters)
                    
                    # Get column names
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    # Fetch results
                    results = []
                    for row in cursor:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            
                            # Handle BLOB fields
                            if isinstance(value, cx_Oracle.LOB):
                                blob_data = value.read()
                                # Convert to base64 for JSON serialization
                                row_dict[col_name] = base64.b64encode(blob_data).decode('utf-8') if blob_data else None
                            elif isinstance(value, datetime):
                                row_dict[col_name] = value.isoformat()
                            else:
                                row_dict[col_name] = value
                        
                        results.append(row_dict)
                        
                        if len(results) >= self.max_results:
                            logger.warning(f"Message log search hit result limit")
                            break
                    
                    logger.info(f"Message log search returned {len(results)} results")
                    return results
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Message log search failed: {e}")
            raise
    
    def get_message_log_by_id(self, msgid: int) -> Optional[Dict[str, Any]]:
        """Get a specific message log entry by MSGID"""
        
        try:
            import base64
            
            query_sql = self.queries["get_message_log_by_id"].replace("{schema}", self.log_schema)
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, {"msgid": msgid})
                    
                    # Get column names
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Convert to dict
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i]
                        
                        # Handle BLOB fields
                        if isinstance(value, cx_Oracle.LOB):
                            blob_data = value.read()
                            # Convert to base64 for JSON serialization
                            row_dict[col_name] = base64.b64encode(blob_data).decode('utf-8') if blob_data else None
                        elif isinstance(value, datetime):
                            row_dict[col_name] = value.isoformat()
                        else:
                            row_dict[col_name] = value
                    
                    logger.info(f"Retrieved message log entry: {msgid}")
                    return row_dict
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to get message log {msgid}: {e}")
            raise
    
    def search_orders(self,
                     cworderid: Optional[str] = None,
                     omorderid: Optional[str] = None,
                     quoteid: Optional[str] = None,
                     telephonenumber: Optional[str] = None,
                     universalserviceid: Optional[str] = None,
                     ordertype: Optional[str] = None,
                     stagecode: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     limit: int = 100,
                     include_blob_data: bool = False) -> List[Dict[str, Any]]:
        """
        Search order header records with flexible filtering
        
        Args:
            cworderid: CW Order ID
            omorderid: OM Order ID  
            quoteid: Quote ID
            telephonenumber: Telephone Number
            universalserviceid: Universal Service ID
            ordertype: Order Type
            stagecode: Stage Code
            start_date: Start date for creation date filter (ISO format)
            end_date: End date for creation date filter (ISO format)
            limit: Maximum number of results (default 100, max 1000)
            include_blob_data: Whether to include BLOB fields (BUCKET, etc.)
        """
        
        try:
            import base64
            
            # Build WHERE clause dynamically
            conditions = []
            params = {}
            
            if cworderid:
                conditions.append("CWORDERID = :cworderid")
                params["cworderid"] = cworderid
                
            if omorderid:
                conditions.append("OMORDERID = :omorderid")
                params["omorderid"] = omorderid
                
            if quoteid:
                conditions.append("QUOTEID = :quoteid")
                params["quoteid"] = quoteid
                
            if telephonenumber:
                conditions.append("TELEPHONENUMBER = :telephonenumber")
                params["telephonenumber"] = telephonenumber
                
            if universalserviceid:
                conditions.append("UNIVERSALSERVICEID = :universalserviceid")
                params["universalserviceid"] = universalserviceid
                
            if ordertype:
                conditions.append("ORDERTYPE = :ordertype")
                params["ordertype"] = ordertype
                
            if stagecode:
                conditions.append("STAGECODE = :stagecode")
                params["stagecode"] = stagecode
                
            if start_date:
                conditions.append("CWORDERCREATIONDATE >= TO_TIMESTAMP(:start_date, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
                params["start_date"] = start_date
                
            if end_date:
                conditions.append("CWORDERCREATIONDATE <= TO_TIMESTAMP(:end_date, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
                params["end_date"] = end_date
            
            # Limit maximum results
            limit = min(limit, 1000)
            
            # Select appropriate columns based on include_blob_data flag
            if include_blob_data:
                select_cols = "*"
            else:
                # Exclude NCLOB/BLOB columns for performance
                select_cols = """
                    CWDOCID, CWDOCSTAMP, CWORDERCREATIONDATE, CWORDERID, CWPARENTID, 
                    LASTUPDATEDDATE, DUEDATE, UPDATEDBY, OMORDERID, QUOTEID, QUOTEGUID,
                    ORDERTYPE, SERVICECASEID, ACTION, DPIORDERNUMBER, RESERVATIONID,
                    CUSTOMERORDERTYPE, ORDERHASH, PONR, DPIENVIRONMENT, DPIOPERATIONREQUESTED,
                    CONTROLNUMBER, BILLINGTELEPHONENUMBER, TELEPHONENUMBER, UNIVERSALSERVICEID,
                    COMPANYID, ISHOA, ONTTYPE, ISEQUIPMENTCHANGED, ORDERSEQUENCE,
                    RECORDLOCATORNUMBER, CANCELREASON, CHECKACTIVESERVICES, ONHOLD,
                    INSTALLATIONTYPE, TELEPHONENUMBERNXX, TELEPHONENUMBERNPA, TELEPHONENUMBERSTATION,
                    TELEPHONENUMBEREXTENSION, TRACKINGID, DATETIME, HEARTBEAT, PROVIDERID,
                    PROVIDERNAME, PROVIDERTYPE, PROVIDERVERSIONID, PROVIDERVERSIONDATETIME,
                    PROVIDERDESCRIPTION, PROVIDERLOCATION, PROVIDERTRANSACTIONID, TRACERESULTMESSAGE,
                    TRACERESULTHOSTNAME, TRACESETTINGSTRACEENABLED, TRACESETTINGSTRACELEVEL,
                    TRACESETTINGSCOMPONENT, TRACERESULTCOMPONENT, TRACERESULTDATETIME,
                    CONSUMERTRACKINGID, CONSUMERAPPLICATIONID, CONSUMEREMPLOYEEID, CONSUMERUSERID,
                    CONSUMERTRANSACTIONID, REQUIRESEOCPROVISIONING, TCPROVISIONINGREQUIRED,
                    TRIADPROVISIONINGREQUIRED, SOAPROVISIONINGREQUIRED, SERVICEMANPROVISIONINGREQUIRED,
                    HSIPROVISIONINGREQUIRED, RECORDONLYCHANGE, STAGECODE, TCPROVNOTIFICATIONSTATUS,
                    TRIADPROVNOTIFICATIONSTATUS, SOAPPROVNOTIFICATIONSTATUS, SERMANPROVNOTIFICATIONSTATUS,
                    HSIPROVNOTIFICATIONSTATUS, LASTSTAGECODEMODIFIEDTIMESTAMP, DUEDATEMODIFIED,
                    CWCREATED, LOCKED, ISFUTUREDUEDATE, MAINPROCID, ORDERORIGIN, LEGACYPROCID,
                    ISRINGCENTRAL, RINGCENTRALACCOUNTID, TERMSOFSERVICEENABLED, TRADINGNAME,
                    ACCOUNTUUID, PORTINGSTATUS, PORTINGMILESTONE, ISNEWCUSTOMER, ISDATAONLY,
                    ISLITONT, LOCATIONID, ONTSERIALNUMBER
                """
            
            # Build query
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query_sql = f"""
                SELECT {select_cols}
                FROM {self.log_schema}.ORDER_ORDER_HEADER
                WHERE {where_clause}
                ORDER BY CWORDERCREATIONDATE DESC
                FETCH FIRST {limit} ROWS ONLY
            """
            
            logger.debug(f"Executing order search query with params: {params}")
            logger.debug(f"SQL: {query_sql}")
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, params)
                    
                    # Get column names
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    rows = cursor.fetchall()
                    
                    # Convert to list of dicts
                    results = []
                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            
                            # Handle LOB fields (NCLOB/BLOB)
                            if isinstance(value, cx_Oracle.LOB):
                                lob_data = value.read()
                                # Convert to base64 for JSON serialization
                                row_dict[col_name] = base64.b64encode(lob_data).decode('utf-8') if lob_data else None
                            elif isinstance(value, datetime):
                                row_dict[col_name] = value.isoformat()
                            else:
                                row_dict[col_name] = value
                        
                        results.append(row_dict)
                    
                    logger.info(f"Found {len(results)} order records")
                    return results
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to search orders: {e}")
            raise
    
    def get_order_by_cwdocid(self, cwdocid: str, include_blob_data: bool = True) -> Optional[Dict[str, Any]]:
        """Get a specific order by CWDOCID (primary key), always including BLOB data"""
        
        try:
            import base64
            
            query_sql = f"""
                SELECT * FROM {self.log_schema}.ORDER_ORDER_HEADER
                WHERE CWDOCID = :cwdocid
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, {"cwdocid": cwdocid})
                    
                    # Get column names
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Convert to dict
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i]
                        
                        # Handle LOB fields
                        if isinstance(value, cx_Oracle.LOB):
                            lob_data = value.read()
                            row_dict[col_name] = base64.b64encode(lob_data).decode('utf-8') if lob_data else None
                        elif isinstance(value, datetime):
                            row_dict[col_name] = value.isoformat()
                        else:
                            row_dict[col_name] = value
                    
                    logger.info(f"Retrieved order: {cwdocid}")
                    return row_dict
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to get order {cwdocid}: {e}")
            raise
    
    def search_order_tracking(self,
                             cworderid: Optional[str] = None,
                             orderid: Optional[str] = None,
                             workid: Optional[str] = None,
                             scaseid: Optional[str] = None,
                             icaseid: Optional[str] = None,
                             orderstatus: Optional[str] = None,
                             casestatus: Optional[str] = None,
                             flowstatus: Optional[str] = None,
                             has_errors: Optional[bool] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             limit: int = 100,
                             include_blob_data: bool = False) -> List[Dict[str, Any]]:
        """
        Search order tracking records with flexible filtering
        
        Args:
            cworderid: CW Order ID
            orderid: Order ID
            workid: Work ID
            scaseid: SCASE ID
            icaseid: ICASE ID
            orderstatus: Order Status
            casestatus: Case Status
            flowstatus: Flow Status
            has_errors: Filter for orders with errors (checks multiple error fields)
            start_date: Start date for creation date filter (ISO format)
            end_date: End date for creation date filter (ISO format)
            limit: Maximum number of results (default 100, max 1000)
            include_blob_data: Whether to include NCLOB fields
        """
        
        try:
            import base64
            
            # Build WHERE clause dynamically
            conditions = []
            params = {}
            
            if cworderid:
                conditions.append("CWORDERID = :cworderid")
                params["cworderid"] = cworderid
                
            if orderid:
                conditions.append("ORDERID = :orderid")
                params["orderid"] = orderid
                
            if workid:
                conditions.append("WORKID = :workid")
                params["workid"] = workid
                
            if scaseid:
                conditions.append("SCASEID = :scaseid")
                params["scaseid"] = scaseid
                
            if icaseid:
                conditions.append("ICASEID = :icaseid")
                params["icaseid"] = icaseid
                
            if orderstatus:
                conditions.append("ORDERSTATUS = :orderstatus")
                params["orderstatus"] = orderstatus
                
            if casestatus:
                conditions.append("CASESTATUS = :casestatus")
                params["casestatus"] = casestatus
                
            if flowstatus:
                conditions.append("FLOWSTATUS = :flowstatus")
                params["flowstatus"] = flowstatus
                
            if has_errors is not None:
                # Check if any error fields are populated
                if has_errors:
                    conditions.append("""(
                        WFMERRORID IS NOT NULL OR
                        PREORDERERRORSYSTEMS > 0 OR
                        ERRORSRVCVALIDATION > 0 OR
                        TRIADERRORID_IA IS NOT NULL OR
                        DPIERRORID_DISP IS NOT NULL OR
                        DPIERRORID_IA IS NOT NULL OR
                        DPIUMERRORID_IA IS NOT NULL OR
                        TRIADERRORID_DISP IS NOT NULL OR
                        TCERRORID_IA IS NOT NULL OR
                        TCERRORID_DISP IS NOT NULL OR
                        CUSTOMERNOTIFERRORID_IA IS NOT NULL OR
                        CUSTOMERNOTIFERRORID_DISP IS NOT NULL OR
                        HASDPIEVERERRORED = 1
                    )""")
                else:
                    conditions.append("""(
                        WFMERRORID IS NULL AND
                        (PREORDERERRORSYSTEMS IS NULL OR PREORDERERRORSYSTEMS = 0) AND
                        (ERRORSRVCVALIDATION IS NULL OR ERRORSRVCVALIDATION = 0) AND
                        TRIADERRORID_IA IS NULL AND
                        DPIERRORID_DISP IS NULL AND
                        DPIERRORID_IA IS NULL AND
                        DPIUMERRORID_IA IS NULL AND
                        TRIADERRORID_DISP IS NULL AND
                        TCERRORID_IA IS NULL AND
                        TCERRORID_DISP IS NULL AND
                        CUSTOMERNOTIFERRORID_IA IS NULL AND
                        CUSTOMERNOTIFERRORID_DISP IS NULL AND
                        (HASDPIEVERERRORED IS NULL OR HASDPIEVERERRORED = 0)
                    )""")
                
            if start_date:
                conditions.append("CWORDERCREATIONDATE >= TO_TIMESTAMP(:start_date, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
                params["start_date"] = start_date
                
            if end_date:
                conditions.append("CWORDERCREATIONDATE <= TO_TIMESTAMP(:end_date, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
                params["end_date"] = end_date
            
            # Limit maximum results
            limit = min(limit, 1000)
            
            # Select appropriate columns based on include_blob_data flag
            if include_blob_data:
                select_cols = "*"
            else:
                # Exclude NCLOB columns for performance
                select_cols = """
                    CWDOCID, ORDERINFO, CWDOCSTAMP, CWORDERCREATIONDATE, CWORDERID, CWPARENTID,
                    LASTUPDATEDTIMESTAMP, UPDATEDBY, WFMERRORID, PROCESSWAITINGFORWFM, SCASEID,
                    ICASEID, WORKID, CASESTATUS, EXECUTIONSTATUSMESSAGE, PEGAAPIINFO, PEGAAPISTATUS,
                    ESBAPIINFO, ESBAPISTATUS, CUSTOMERAPIINFO, CUSTOMERAPISTATUS, DPIAPIINFO,
                    DPIAPISTATUS, PREORDERERRORSYSTEMS, ERRORSRVCVALIDATION, TRIADERRORID_IA,
                    TRIADINTFSTATUS, DPIERRORID_DISP, DPIERRORID_IA, DPISBMOSTATUS,
                    TRIADINVOLVEMENTORDERLEVEL, ORDERID, ORDERSTATUS, PREORDERSTATUS, FLOWSTATUS,
                    DPIUMSTATUS, DPIUMERRORID_IA, TRIADERRORID_DISP, TCINTFSTATUS,
                    TCINVOLVEMENTORDERLEVEL, TCERRORID_IA, TCERRORID_DISP, CUSTOMERNOTIFERRORID_IA,
                    CUSTOMERNOTIFERRORID_DISP, CUSTOMERNOTIFSTATUS, EMAILUPDATES, LASTORDERLINENUMBER,
                    ISDISPATCH, WORKUNITCALCULATION, PROCID, NUMBEROFITEMS, LASTTRIADOPERATION,
                    CANPROCID, TRIADCANERRORID_IA, DPIORDERID, RESPONSIBLEPARTY, IGCANDIDATE,
                    HASDPIEVERERRORED, DPISTANDALONEPROCID, NOTIFYCUSTOMERPROCID,
                    NOTSUPPORTEDPROVSYSTEMFOUND, PURGEORDER, ISCANCELLEDBYOC, CANCELREMARK,
                    TRIADRETRY, LASTUPDATEDDATE, ORDERLOCK, BICFSS, BI, NUMBEROFCFSSITEMS,
                    PASSEDHELDSTAGE
                """
            
            # Build query
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query_sql = f"""
                SELECT {select_cols}
                FROM {self.log_schema}.ORDER_TRACKING_INFO
                WHERE {where_clause}
                ORDER BY CWORDERCREATIONDATE DESC
                FETCH FIRST {limit} ROWS ONLY
            """
            
            logger.debug(f"Executing order tracking search query with params: {params}")
            logger.debug(f"SQL: {query_sql}")
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, params)
                    
                    # Get column names
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    rows = cursor.fetchall()
                    
                    # Convert to list of dicts
                    results = []
                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            
                            # Handle LOB fields (NCLOB)
                            if isinstance(value, cx_Oracle.LOB):
                                lob_data = value.read()
                                # Convert to base64 for JSON serialization
                                row_dict[col_name] = base64.b64encode(lob_data).decode('utf-8') if lob_data else None
                            elif isinstance(value, datetime):
                                row_dict[col_name] = value.isoformat()
                            else:
                                row_dict[col_name] = value
                        
                        results.append(row_dict)
                    
                    logger.info(f"Found {len(results)} order tracking records")
                    return results
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to search order tracking: {e}")
            raise
    
    def get_order_tracking_by_cwdocid(self, cwdocid: str, include_blob_data: bool = True) -> Optional[Dict[str, Any]]:
        """Get a specific order tracking record by CWDOCID (primary key)"""
        
        try:
            import base64
            
            query_sql = f"""
                SELECT * FROM {self.log_schema}.ORDER_TRACKING_INFO
                WHERE CWDOCID = :cwdocid
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, {"cwdocid": cwdocid})
                    
                    # Get column names
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Convert to dict
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i]
                        
                        # Handle LOB fields
                        if isinstance(value, cx_Oracle.LOB):
                            lob_data = value.read()
                            row_dict[col_name] = base64.b64encode(lob_data).decode('utf-8') if lob_data else None
                        elif isinstance(value, datetime):
                            row_dict[col_name] = value.isoformat()
                        else:
                            row_dict[col_name] = value
                    
                    logger.info(f"Retrieved order tracking: {cwdocid}")
                    return row_dict
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to get order tracking {cwdocid}: {e}")
            raise
    
    def search_order_instances(self,
                              cwdocid: Optional[str] = None,
                              customerid: Optional[str] = None,
                              accountid: Optional[str] = None,
                              ordertype: Optional[str] = None,
                              ordersubtype: Optional[str] = None,
                              status: Optional[str] = None,
                              state: Optional[str] = None,
                              quoteid: Optional[str] = None,
                              externalorderid: Optional[str] = None,
                              productcode: Optional[str] = None,
                              parentorder: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None,
                              limit: int = 100,
                              include_blob_data: bool = False) -> List[Dict[str, Any]]:
        """
        Search order instances from CWORDERINSTANCE table
        
        Args:
            cwdocid: CW Document ID (primary key)
            customerid: Customer ID
            accountid: Account ID
            ordertype: Order Type
            ordersubtype: Order Subtype
            status: Status (single character)
            state: Order State
            quoteid: Quote ID
            externalorderid: External Order ID
            productcode: Product Code
            parentorder: Parent Order ID
            start_date: Start date for creation date filter (ISO format)
            end_date: End date for creation date filter (ISO format)
            limit: Maximum number of results (default 100, max 1000)
            include_blob_data: Whether to include NCLOB fields
        """
        
        try:
            import base64
            
            # Build WHERE clause dynamically
            conditions = []
            params = {}
            
            if cwdocid:
                conditions.append("CWDOCID = :cwdocid")
                params["cwdocid"] = cwdocid
                
            if customerid:
                conditions.append("CUSTOMERID = :customerid")
                params["customerid"] = customerid
                
            if accountid:
                conditions.append("ACCOUNTID = :accountid")
                params["accountid"] = accountid
                
            if ordertype:
                conditions.append("ORDERTYPE = :ordertype")
                params["ordertype"] = ordertype
                
            if ordersubtype:
                conditions.append("ORDERSUBTYPE = :ordersubtype")
                params["ordersubtype"] = ordersubtype
                
            if status:
                conditions.append("STATUS = :status")
                params["status"] = status
                
            if state:
                conditions.append("STATE = :state")
                params["state"] = state
                
            if quoteid:
                conditions.append("QUOTEID = :quoteid")
                params["quoteid"] = quoteid
                
            if externalorderid:
                conditions.append("EXTERNALORDERID = :externalorderid")
                params["externalorderid"] = externalorderid
                
            if productcode:
                conditions.append("PRODUCTCODE = :productcode")
                params["productcode"] = productcode
                
            if parentorder:
                conditions.append("PARENTORDER = :parentorder")
                params["parentorder"] = parentorder
                
            if start_date:
                conditions.append("CREATIONDATE >= TO_TIMESTAMP(:start_date, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
                params["start_date"] = start_date
                
            if end_date:
                conditions.append("CREATIONDATE <= TO_TIMESTAMP(:end_date, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
                params["end_date"] = end_date
            
            # Limit maximum results
            limit = min(limit, 1000)
            
            # Select appropriate columns based on include_blob_data flag
            if include_blob_data:
                select_cols = "*"
            else:
                # Exclude NCLOB columns for performance
                select_cols = """
                    CWDOCID, METADATATYPE, STATUS, STATE, VISUALKEY, PRODUCTCODE, CREATIONDATE,
                    CREATEDBY, UPDATEDBY, LASTUPDATEDDATE, PARENTORDER, OWNER, STATE2, HASATTACHMENT,
                    METADATATYPE_VER, ORIGINAL_ORDER_ID, SOURCE_ORDER_ID, KIND_OF_ORDER, ORDER_PHASE,
                    PROJECT_ID, PROCESS_ID, CWORDERSTAMP, CWDOCSTAMP, APP_NAME, DUEDATE, BASKETID,
                    CWUSERROLE, OSTATE, CUSTOMERID, ACCOUNTID, ORDERTYPE, ORDERSUBTYPE, RELATEDORDER,
                    ORDERNUM, ORDVER, EFFECTIVEDATE, SUBMITTEDBY, SUBMITTEDDATE, PRICE, ONETIMEPRICE,
                    PRICEDON, CORRELATIONID, QUOTEID, CHANNEL, EXPIRATIONDATE, QUOTEEXPIRATIONDATE,
                    ASSIGNEDPRIORITY, REQUESTEDSTARTDATE, REQUESTEDCOMPLETIONDATE, DESCRIPTION, BITYPE,
                    EXTERNALORDERID, ISBUNDLED, MODE_SC, ISLOCKED, REQUESTER, BISPECIFICATION, QUOTEON,
                    COMPLETIONDATE, EXTENDEDSTATE, ORDERROLE, ORDERIDREF, PREVOSTATE, PMPROJECTID,
                    PMPROJECTTYPE
                """
            
            # Build query
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query_sql = f"""
                SELECT {select_cols}
                FROM {self.log_schema}.CWORDERINSTANCE
                WHERE {where_clause}
                ORDER BY CREATIONDATE DESC
                FETCH FIRST {limit} ROWS ONLY
            """
            
            logger.debug(f"Executing order instance search query with params: {params}")
            logger.debug(f"SQL: {query_sql}")
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, params)
                    
                    # Get column names
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    rows = cursor.fetchall()
                    
                    # Convert to list of dicts
                    results = []
                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            
                            # Handle LOB fields (NCLOB)
                            if isinstance(value, cx_Oracle.LOB):
                                lob_data = value.read()
                                row_dict[col_name] = base64.b64encode(lob_data).decode('utf-8') if lob_data else None
                            elif isinstance(value, datetime):
                                row_dict[col_name] = value.isoformat()
                            else:
                                row_dict[col_name] = value
                        
                        results.append(row_dict)
                    
                    logger.info(f"Found {len(results)} order instance records")
                    return results
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to search order instances: {e}")
            raise
    
    def get_order_instance_by_cwdocid(self, cwdocid: str, include_blob_data: bool = True) -> Optional[Dict[str, Any]]:
        """Get a specific order instance by CWDOCID (primary key)"""
        
        try:
            import base64
            
            query_sql = f"""
                SELECT * FROM {self.log_schema}.CWORDERINSTANCE
                WHERE CWDOCID = :cwdocid
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, {"cwdocid": cwdocid})
                    
                    # Get column names
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Convert to dict
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i]
                        
                        # Handle LOB fields
                        if isinstance(value, cx_Oracle.LOB):
                            lob_data = value.read()
                            row_dict[col_name] = base64.b64encode(lob_data).decode('utf-8') if lob_data else None
                        elif isinstance(value, datetime):
                            row_dict[col_name] = value.isoformat()
                        else:
                            row_dict[col_name] = value
                    
                    logger.info(f"Retrieved order instance: {cwdocid}")
                    return row_dict
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to get order instance {cwdocid}: {e}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection and return status"""
        
        try:
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT 1 FROM dual")
                result = cursor.fetchone()
                cursor.close()
                
                if result and result[0] == 1:
                    return {
                        "success": True,
                        "message": "Database connection successful",
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": "Unexpected test result"
                    }
                    
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========================================================================
    # AI TROUBLESHOOTING PLANS METHODS
    # ========================================================================
    
    def create_plan(self, goal_type: str, order_type: Optional[str], title: str,
                    description: Optional[str], steps: str, expected_outcomes: Optional[str],
                    confidence: float) -> Dict[str, Any]:
        """Create a new troubleshooting plan"""
        
        try:
            import hashlib
            
            # Generate plan_id (MD5 hash of goal_type + order_type)
            key = f"{goal_type}_{order_type or 'default'}"
            plan_id = hashlib.md5(key.encode()).hexdigest()[:12]
            
            insert_sql = f"""
                INSERT INTO {self.log_schema}.AI_TROUBLESHOOTING_PLANS (
                    PLAN_ID, GOAL_TYPE, ORDER_TYPE, TITLE, DESCRIPTION,
                    STEPS, EXPECTED_OUTCOMES, CONFIDENCE
                ) VALUES (
                    :plan_id, :goal_type, :order_type, :title, :description,
                    :steps, :expected_outcomes, :confidence
                )
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(insert_sql, {
                        "plan_id": plan_id,
                        "goal_type": goal_type,
                        "order_type": order_type,
                        "title": title,
                        "description": description,
                        "steps": steps,
                        "expected_outcomes": expected_outcomes,
                        "confidence": confidence
                    })
                    
                    connection.commit()
                    logger.info(f"Created plan: {plan_id}")
                    
                    return {
                        "success": True,
                        "plan_id": plan_id,
                        "message": "Plan created successfully"
                    }
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            raise
    
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a troubleshooting plan by ID"""
        
        try:
            query_sql = f"""
                SELECT * FROM {self.log_schema}.AI_TROUBLESHOOTING_PLANS
                WHERE PLAN_ID = :plan_id
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, {"plan_id": plan_id})
                    columns = [desc[0].lower() for desc in cursor.description]
                    row = cursor.fetchone()
                    
                    if not row:
                        return None
                    
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i]
                        if isinstance(value, datetime):
                            row_dict[col_name] = value.isoformat()
                        elif isinstance(value, cx_Oracle.LOB):
                            # Read CLOB data (description, steps, expected_outcomes)
                            lob_data = value.read()
                            if lob_data:
                                # Check if it's already a string or bytes
                                if isinstance(lob_data, bytes):
                                    row_dict[col_name] = lob_data.decode('utf-8')
                                else:
                                    row_dict[col_name] = lob_data
                            else:
                                row_dict[col_name] = None
                        else:
                            row_dict[col_name] = value
                    
                    logger.info(f"Retrieved plan: {plan_id}")
                    return row_dict
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to get plan {plan_id}: {e}")
            raise
    
    def search_plans(self, goal_type: Optional[str] = None, order_type: Optional[str] = None,
                     is_active: Optional[int] = None, min_success_rate: Optional[float] = None,
                     limit: int = 50) -> List[Dict[str, Any]]:
        """Search troubleshooting plans"""
        
        try:
            # Build query dynamically
            where_clauses = []
            params = {}
            
            if goal_type:
                where_clauses.append("GOAL_TYPE = :goal_type")
                params["goal_type"] = goal_type
            
            if order_type:
                where_clauses.append("ORDER_TYPE = :order_type")
                params["order_type"] = order_type
            
            if is_active is not None:
                where_clauses.append("IS_ACTIVE = :is_active")
                params["is_active"] = is_active
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            query_sql = f"""
                SELECT * FROM {self.log_schema}.AI_TROUBLESHOOTING_PLANS
                {where_sql}
                ORDER BY LAST_USED_DATE DESC NULLS LAST
                FETCH FIRST :limit ROWS ONLY
            """
            
            params["limit"] = limit
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, params)
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    results = []
                    for row in cursor:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            if isinstance(value, datetime):
                                row_dict[col_name] = value.isoformat()
                            elif isinstance(value, cx_Oracle.LOB):
                                # Read CLOB data (description, steps, expected_outcomes)
                                lob_data = value.read()
                                if lob_data:
                                    # Check if it's already a string or bytes
                                    if isinstance(lob_data, bytes):
                                        row_dict[col_name] = lob_data.decode('utf-8')
                                    else:
                                        row_dict[col_name] = lob_data
                                else:
                                    row_dict[col_name] = None
                            else:
                                row_dict[col_name] = value
                        
                        # Apply success rate filter if specified
                        if min_success_rate is not None:
                            total_usage = row_dict.get('total_usage', 0)
                            success_count = row_dict.get('success_count', 0)
                            if total_usage > 0:
                                success_rate = success_count / total_usage
                                if success_rate < min_success_rate:
                                    continue
                            else:
                                continue  # Skip plans with no usage if min_success_rate is set
                        
                        results.append(row_dict)
                    
                    logger.info(f"Found {len(results)} plans")
                    return results
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to search plans: {e}")
            raise
    
    def update_plan(self, plan_id: str, title: Optional[str] = None, description: Optional[str] = None,
                    steps: Optional[str] = None, expected_outcomes: Optional[str] = None,
                    confidence: Optional[float] = None, is_active: Optional[int] = None) -> Dict[str, Any]:
        """Update a troubleshooting plan"""
        
        try:
            # Build update query dynamically
            update_fields = []
            params = {"plan_id": plan_id}
            
            if title is not None:
                update_fields.append("TITLE = :title")
                params["title"] = title
            
            if description is not None:
                update_fields.append("DESCRIPTION = :description")
                params["description"] = description
            
            if steps is not None:
                update_fields.append("STEPS = :steps")
                params["steps"] = steps
            
            if expected_outcomes is not None:
                update_fields.append("EXPECTED_OUTCOMES = :expected_outcomes")
                params["expected_outcomes"] = expected_outcomes
            
            if confidence is not None:
                update_fields.append("CONFIDENCE = :confidence")
                params["confidence"] = confidence
            
            if is_active is not None:
                update_fields.append("IS_ACTIVE = :is_active")
                params["is_active"] = is_active
            
            if not update_fields:
                return {"success": False, "error": "No fields to update"}
            
            update_fields.append("LAST_UPDATED_DATE = SYSTIMESTAMP")
            
            update_sql = f"""
                UPDATE {self.log_schema}.AI_TROUBLESHOOTING_PLANS
                SET {', '.join(update_fields)}
                WHERE PLAN_ID = :plan_id
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(update_sql, params)
                    rows_updated = cursor.rowcount
                    connection.commit()
                    
                    logger.info(f"Updated plan: {plan_id}")
                    return {
                        "success": True,
                        "rows_updated": rows_updated,
                        "message": "Plan updated successfully"
                    }
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to update plan {plan_id}: {e}")
            raise
    
    def update_plan_usage(self, plan_id: str, success: bool) -> Dict[str, Any]:
        """Update plan usage statistics"""
        
        try:
            update_sql = f"""
                UPDATE {self.log_schema}.AI_TROUBLESHOOTING_PLANS
                SET TOTAL_USAGE = TOTAL_USAGE + 1,
                    SUCCESS_COUNT = SUCCESS_COUNT + :success_increment,
                    LAST_USED_DATE = SYSTIMESTAMP
                WHERE PLAN_ID = :plan_id
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(update_sql, {
                        "plan_id": plan_id,
                        "success_increment": 1 if success else 0
                    })
                    
                    rows_updated = cursor.rowcount
                    connection.commit()
                    
                    logger.info(f"Updated plan usage: {plan_id}, success={success}")
                    return {
                        "success": True,
                        "rows_updated": rows_updated,
                        "message": "Plan usage updated"
                    }
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to update plan usage {plan_id}: {e}")
            raise
    
    def delete_plan(self, plan_id: str) -> Dict[str, Any]:
        """Delete a troubleshooting plan (or set to inactive)"""
        
        try:
            # Soft delete: set IS_ACTIVE = 0
            update_sql = f"""
                UPDATE {self.log_schema}.AI_TROUBLESHOOTING_PLANS
                SET IS_ACTIVE = 0,
                    LAST_UPDATED_DATE = SYSTIMESTAMP
                WHERE PLAN_ID = :plan_id
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(update_sql, {"plan_id": plan_id})
                    rows_updated = cursor.rowcount
                    connection.commit()
                    
                    logger.info(f"Deleted (deactivated) plan: {plan_id}")
                    return {
                        "success": True,
                        "rows_updated": rows_updated,
                        "message": "Plan deleted (deactivated)"
                    }
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to delete plan {plan_id}: {e}")
            raise
    
    # ========================================================================
    # PLAN EXECUTION HISTORY METHODS
    # ========================================================================
    
    def create_execution_history(self, plan_id: str, order_id: Optional[str], execution_time_ms: Optional[int],
                                  success: bool, error_message: Optional[str], collected_data_summary: Optional[str],
                                  analysis_result: Optional[str]) -> Dict[str, Any]:
        """Create a plan execution history record"""
        
        try:
            insert_sql = f"""
                INSERT INTO {self.log_schema}.AI_PLAN_EXECUTION_HISTORY (
                    PLAN_ID, ORDER_ID, EXECUTION_TIME_MS, SUCCESS,
                    ERROR_MESSAGE, COLLECTED_DATA_SUMMARY, ANALYSIS_RESULT
                ) VALUES (
                    :plan_id, :order_id, :execution_time_ms, :success,
                    :error_message, :collected_data_summary, :analysis_result
                )
            """
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(insert_sql, {
                        "plan_id": plan_id,
                        "order_id": order_id,
                        "execution_time_ms": execution_time_ms,
                        "success": 1 if success else 0,
                        "error_message": error_message,
                        "collected_data_summary": collected_data_summary,
                        "analysis_result": analysis_result
                    })
                    
                    connection.commit()
                    logger.info(f"Created execution history for plan: {plan_id}")
                    
                    return {
                        "success": True,
                        "message": "Execution history created"
                    }
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to create execution history: {e}")
            raise
    
    def get_execution_history(self, plan_id: Optional[str] = None, order_id: Optional[str] = None,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """Get plan execution history"""
        
        try:
            where_clauses = []
            params = {}
            
            if plan_id:
                where_clauses.append("PLAN_ID = :plan_id")
                params["plan_id"] = plan_id
            
            if order_id:
                where_clauses.append("ORDER_ID = :order_id")
                params["order_id"] = order_id
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            query_sql = f"""
                SELECT * FROM {self.log_schema}.AI_PLAN_EXECUTION_HISTORY
                {where_sql}
                ORDER BY EXECUTION_DATE DESC
                FETCH FIRST :limit ROWS ONLY
            """
            
            params["limit"] = limit
            
            with connection_pool.get_connection() as connection:
                cursor = connection.cursor()
                
                try:
                    cursor.execute(query_sql, params)
                    columns = [desc[0].lower() for desc in cursor.description]
                    
                    results = []
                    for row in cursor:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            if isinstance(value, datetime):
                                row_dict[col_name] = value.isoformat()
                            elif isinstance(value, cx_Oracle.LOB):
                                lob_data = value.read()
                                if lob_data:
                                    # Check if it's already a string or bytes
                                    if isinstance(lob_data, bytes):
                                        row_dict[col_name] = lob_data.decode('utf-8')
                                    else:
                                        row_dict[col_name] = lob_data
                                else:
                                    row_dict[col_name] = None
                            else:
                                row_dict[col_name] = value
                        
                        results.append(row_dict)
                    
                    logger.info(f"Found {len(results)} execution history records")
                    return results
                    
                finally:
                    cursor.close()
                    
        except Exception as e:
            logger.error(f"Failed to get execution history: {e}")
            raise

# Global database service instance
db_service = DatabaseService()
