"""
Oracle Database API Service

FastAPI service that provides secure access to Oracle database
for AI agents to retrieve order logs and troubleshooting data.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys

from config import config
from database import db_service, connection_pool
from models import (
    BaseResponse, ErrorResponse, HealthResponse, DatabaseTestResponse,
    MessageLogEntry, MessageLogSearchRequest, MessageLogResponse,
    OrderHeaderEntry, OrderHeaderSearchRequest, OrderHeaderResponse,
    OrderTrackingEntry, OrderTrackingSearchRequest, OrderTrackingResponse,
    OrderInstanceEntry, OrderInstanceSearchRequest, OrderInstanceResponse,
    TroubleshootingPlanEntry, PlanCreateRequest, PlanUpdateRequest, PlanUsageUpdateRequest,
    PlanSearchRequest, PlanResponse, PlanListResponse,
    PlanExecutionHistoryEntry, ExecutionHistoryCreateRequest, ExecutionHistoryResponse
)
from health_check import health_checker
from datetime import datetime

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    level=config.api.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Application startup time for uptime calculation
start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown logic"""
    
    # Startup
    logger.info(f"Starting {config.api.api_title} v{config.api.api_version}")
    
    # Initialize database connection pool
    try:
        connection_pool.initialize_pool()
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't exit - let health checks show the status
    
    # Test database connection
    test_result = db_service.test_connection()
    if test_result["success"]:
        logger.info("Database connection test passed")
    else:
        logger.error(f"Database connection test failed: {test_result.get('error')}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down database API service")
    connection_pool.close_pool()

# Initialize FastAPI app
app = FastAPI(
    title=config.api.api_title,
    version=config.api.api_version,
    description="Oracle Database API for AI-powered log analysis and troubleshooting",
    lifespan=lifespan
)

# CORS middleware
if config.api.cors_origins:
    origins = [origin.strip() for origin in config.api.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# No authentication required for internal application
# All endpoints are accessible without API keys

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": time.time()
        }
    )

# Debug endpoint to check headers
@app.get("/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint to see all received headers"""
    return {
        "headers": dict(request.headers),
        "x_api_key_received": request.headers.get("x-api-key"),
        "api_key_uppercase": request.headers.get("X-API-Key"),
    }

# Health check endpoint (public - no auth required)
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Quick health check endpoint (no authentication required)"""
    
    # Test database connection
    db_test = db_service.test_connection()
    
    return HealthResponse(
        success=True,
        service=config.api.api_title,
        version=config.api.api_version,
        database_connected=db_test["success"],
        uptime_seconds=time.time() - start_time
    )

# Comprehensive health check endpoint
@app.get("/health/comprehensive")
async def comprehensive_health_check():
    """Comprehensive health check with detailed diagnostics (requires authentication)"""
    
    health_status = health_checker.get_comprehensive_health()
    return JSONResponse(content=health_status)

# Database test endpoint
@app.get("/test-db", response_model=DatabaseTestResponse)
async def test_database():
    """Test database connection and return detailed status"""
    
    test_result = db_service.test_connection()
    
    return DatabaseTestResponse(
        success=test_result["success"],
        message=test_result.get("message", test_result.get("error", "Unknown")),
        connection_pool_status={
            "initialized": connection_pool.initialized,
            "pool_exists": connection_pool.pool is not None
        }
    )


# ============================================================================
# CWMESSAGELOG Endpoints
# ============================================================================

@app.post("/message-logs/search", response_model=MessageLogResponse)
async def search_message_logs(request: MessageLogSearchRequest):
    """Search CWMESSAGELOG by user_data1, user_data2, user_data3, and other criteria"""
    
    try:
        logger.info(f"Searching message logs with criteria: {request.dict(exclude_none=True)}")
        
        # Execute search
        results = db_service.search_message_logs(
            user_data1=request.user_data1,
            user_data2=request.user_data2,
            user_data3=request.user_data3,
            order_id=request.order_id,
            customer_id=request.customer_id,
            operation=request.operation,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            include_blob_data=request.include_blob_data
        )
        
        # Convert to response models
        messages = [MessageLogEntry(**msg) for msg in results]
        
        # Check if data was truncated
        data_truncated = len(results) >= request.limit
        
        return MessageLogResponse(
            success=True,
            messages=messages,
            total_found=len(messages),
            search_criteria=request.dict(exclude_none=True),
            data_truncated=data_truncated
        )
        
    except Exception as e:
        logger.error(f"Message log search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Message log search failed: {str(e)}"
        )

@app.get("/message-logs/{msgid}")
async def get_message_log_by_id(msgid: int):
    """Get a specific message log entry by MSGID (includes BLOB data)"""
    
    try:
        logger.info(f"Retrieving message log entry: {msgid}")
        
        result = db_service.get_message_log_by_id(msgid)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Message log entry {msgid} not found"
            )
        
        return JSONResponse(content={
            "success": True,
            "message": MessageLogEntry(**result).dict(),
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving message log {msgid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve message log: {str(e)}"
        )

@app.get("/message-logs/by-user-data/user-data1/{user_data1}")
async def get_message_logs_by_user_data1(user_data1: str, limit: int = Query(default=100, ge=1, le=1000)):
    """Quick search by user_data1 only"""
    
    try:
        results = db_service.search_message_logs(user_data1=user_data1, limit=limit)
        messages = [MessageLogEntry(**msg) for msg in results]
        
        return JSONResponse(content={
            "success": True,
            "messages": [msg.dict() for msg in messages],
            "total_found": len(messages),
            "user_data1": user_data1
        })
        
    except Exception as e:
        logger.error(f"Error searching by user_data1: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/message-logs/by-user-data/user-data2/{user_data2}")
async def get_message_logs_by_user_data2(user_data2: str, limit: int = Query(default=100, ge=1, le=1000)):
    """Quick search by user_data2 only"""
    
    try:
        results = db_service.search_message_logs(user_data2=user_data2, limit=limit)
        messages = [MessageLogEntry(**msg) for msg in results]
        
        return JSONResponse(content={
            "success": True,
            "messages": [msg.dict() for msg in messages],
            "total_found": len(messages),
            "user_data2": user_data2
        })
        
    except Exception as e:
        logger.error(f"Error searching by user_data2: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/message-logs/by-user-data/user-data3/{user_data3}")
async def get_message_logs_by_user_data3(user_data3: str, limit: int = Query(default=100, ge=1, le=1000)):
    """Quick search by user_data3 only"""
    
    try:
        results = db_service.search_message_logs(user_data3=user_data3, limit=limit)
        messages = [MessageLogEntry(**msg) for msg in results]
        
        return JSONResponse(content={
            "success": True,
            "messages": [msg.dict() for msg in messages],
            "total_found": len(messages),
            "user_data3": user_data3
        })
        
    except Exception as e:
        logger.error(f"Error searching by user_data3: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# ============================================================================
# ORDER_ORDER_HEADER Endpoints
# ============================================================================

@app.post("/orders/search", response_model=OrderHeaderResponse)
async def search_orders(request: OrderHeaderSearchRequest):
    """Search ORDER_ORDER_HEADER by various criteria"""
    
    try:
        logger.info(f"Searching orders with criteria: {request.dict(exclude_none=True)}")
        
        # Execute search
        results = db_service.search_orders(
            cworderid=request.cworderid,
            omorderid=request.omorderid,
            quoteid=request.quoteid,
            telephonenumber=request.telephonenumber,
            universalserviceid=request.universalserviceid,
            ordertype=request.ordertype,
            stagecode=request.stagecode,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            include_blob_data=request.include_blob_data
        )
        
        # Convert to response models
        orders = [OrderHeaderEntry(**order) for order in results]
        
        # Check if data was truncated
        data_truncated = len(results) >= request.limit
        
        return OrderHeaderResponse(
            success=True,
            orders=orders,
            total_found=len(orders),
            search_criteria=request.dict(exclude_none=True),
            data_truncated=data_truncated
        )
        
    except Exception as e:
        logger.error(f"Order search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Order search failed: {str(e)}"
        )

@app.get("/orders/{cwdocid}")
async def get_order_by_cwdocid(cwdocid: str, include_blob_data: bool = Query(default=True)):
    """Get a specific order by CWDOCID (primary key)"""
    
    try:
        logger.info(f"Retrieving order: {cwdocid}")
        
        result = db_service.get_order_by_cwdocid(cwdocid, include_blob_data=include_blob_data)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Order {cwdocid} not found"
            )
        
        return JSONResponse(content={
            "success": True,
            "order": OrderHeaderEntry(**result).dict(),
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving order {cwdocid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve order: {str(e)}"
        )

@app.get("/orders/by-cworderid/{cworderid}")
async def get_order_by_cworderid(
    cworderid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by CWORDERID"""
    
    try:
        results = db_service.search_orders(cworderid=cworderid, limit=limit, include_blob_data=include_blob_data)
        orders = [OrderHeaderEntry(**order) for order in results]
        
        return JSONResponse(content={
            "success": True,
            "orders": [order.dict() for order in orders],
            "total_found": len(orders),
            "cworderid": cworderid
        })
        
    except Exception as e:
        logger.error(f"Error searching by cworderid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/orders/by-omorderid/{omorderid}")
async def get_order_by_omorderid(
    omorderid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by OMORDERID"""
    
    try:
        results = db_service.search_orders(omorderid=omorderid, limit=limit, include_blob_data=include_blob_data)
        orders = [OrderHeaderEntry(**order) for order in results]
        
        return JSONResponse(content={
            "success": True,
            "orders": [order.dict() for order in orders],
            "total_found": len(orders),
            "omorderid": omorderid
        })
        
    except Exception as e:
        logger.error(f"Error searching by omorderid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/orders/by-telephone/{telephonenumber}")
async def get_order_by_telephone(
    telephonenumber: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by telephone number"""
    
    try:
        results = db_service.search_orders(telephonenumber=telephonenumber, limit=limit, include_blob_data=include_blob_data)
        orders = [OrderHeaderEntry(**order) for order in results]
        
        return JSONResponse(content={
            "success": True,
            "orders": [order.dict() for order in orders],
            "total_found": len(orders),
            "telephonenumber": telephonenumber
        })
        
    except Exception as e:
        logger.error(f"Error searching by telephone: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/orders/by-quoteid/{quoteid}")
async def get_order_by_quoteid(
    quoteid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by Quote ID"""
    
    try:
        results = db_service.search_orders(quoteid=quoteid, limit=limit, include_blob_data=include_blob_data)
        orders = [OrderHeaderEntry(**order) for order in results]
        
        return JSONResponse(content={
            "success": True,
            "orders": [order.dict() for order in orders],
            "total_found": len(orders),
            "quoteid": quoteid
        })
        
    except Exception as e:
        logger.error(f"Error searching by quoteid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# ============================================================================
# ORDER_TRACKING_INFO Endpoints
# ============================================================================

@app.post("/order-tracking/search", response_model=OrderTrackingResponse)
async def search_order_tracking(request: OrderTrackingSearchRequest):
    """Search ORDER_TRACKING_INFO by various criteria including error status"""
    
    try:
        logger.info(f"Searching order tracking with criteria: {request.dict(exclude_none=True)}")
        
        # Execute search
        results = db_service.search_order_tracking(
            cworderid=request.cworderid,
            orderid=request.orderid,
            workid=request.workid,
            scaseid=request.scaseid,
            icaseid=request.icaseid,
            orderstatus=request.orderstatus,
            casestatus=request.casestatus,
            flowstatus=request.flowstatus,
            has_errors=request.has_errors,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            include_blob_data=request.include_blob_data
        )
        
        # Convert to response models
        tracking_records = [OrderTrackingEntry(**record) for record in results]
        
        # Check if data was truncated
        data_truncated = len(results) >= request.limit
        
        return OrderTrackingResponse(
            success=True,
            tracking_records=tracking_records,
            total_found=len(tracking_records),
            search_criteria=request.dict(exclude_none=True),
            data_truncated=data_truncated
        )
        
    except Exception as e:
        logger.error(f"Order tracking search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Order tracking search failed: {str(e)}"
        )

@app.get("/order-tracking/{cwdocid}")
async def get_order_tracking_by_cwdocid(cwdocid: str, include_blob_data: bool = Query(default=True)):
    """Get a specific order tracking record by CWDOCID (primary key)"""
    
    try:
        logger.info(f"Retrieving order tracking: {cwdocid}")
        
        result = db_service.get_order_tracking_by_cwdocid(cwdocid, include_blob_data=include_blob_data)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Order tracking record {cwdocid} not found"
            )
        
        return JSONResponse(content={
            "success": True,
            "tracking": OrderTrackingEntry(**result).dict(),
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving order tracking {cwdocid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve order tracking: {str(e)}"
        )

@app.get("/order-tracking/by-cworderid/{cworderid}")
async def get_order_tracking_by_cworderid(
    cworderid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by CWORDERID"""
    
    try:
        results = db_service.search_order_tracking(cworderid=cworderid, limit=limit, include_blob_data=include_blob_data)
        tracking_records = [OrderTrackingEntry(**record) for record in results]
        
        return JSONResponse(content={
            "success": True,
            "tracking_records": [record.dict() for record in tracking_records],
            "total_found": len(tracking_records),
            "cworderid": cworderid
        })
        
    except Exception as e:
        logger.error(f"Error searching by cworderid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/order-tracking/by-orderid/{orderid}")
async def get_order_tracking_by_orderid(
    orderid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by ORDERID"""
    
    try:
        results = db_service.search_order_tracking(orderid=orderid, limit=limit, include_blob_data=include_blob_data)
        tracking_records = [OrderTrackingEntry(**record) for record in results]
        
        return JSONResponse(content={
            "success": True,
            "tracking_records": [record.dict() for record in tracking_records],
            "total_found": len(tracking_records),
            "orderid": orderid
        })
        
    except Exception as e:
        logger.error(f"Error searching by orderid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/order-tracking/by-workid/{workid}")
async def get_order_tracking_by_workid(
    workid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by Work ID"""
    
    try:
        results = db_service.search_order_tracking(workid=workid, limit=limit, include_blob_data=include_blob_data)
        tracking_records = [OrderTrackingEntry(**record) for record in results]
        
        return JSONResponse(content={
            "success": True,
            "tracking_records": [record.dict() for record in tracking_records],
            "total_found": len(tracking_records),
            "workid": workid
        })
        
    except Exception as e:
        logger.error(f"Error searching by workid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/order-tracking/by-scaseid/{scaseid}")
async def get_order_tracking_by_scaseid(
    scaseid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by SCASE ID"""
    
    try:
        results = db_service.search_order_tracking(scaseid=scaseid, limit=limit, include_blob_data=include_blob_data)
        tracking_records = [OrderTrackingEntry(**record) for record in results]
        
        return JSONResponse(content={
            "success": True,
            "tracking_records": [record.dict() for record in tracking_records],
            "total_found": len(tracking_records),
            "scaseid": scaseid
        })
        
    except Exception as e:
        logger.error(f"Error searching by scaseid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/order-tracking/by-status/{orderstatus}")
async def get_order_tracking_by_status(
    orderstatus: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by order status"""
    
    try:
        results = db_service.search_order_tracking(orderstatus=orderstatus, limit=limit, include_blob_data=include_blob_data)
        tracking_records = [OrderTrackingEntry(**record) for record in results]
        
        return JSONResponse(content={
            "success": True,
            "tracking_records": [record.dict() for record in tracking_records],
            "total_found": len(tracking_records),
            "orderstatus": orderstatus
        })
        
    except Exception as e:
        logger.error(f"Error searching by status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/order-tracking/with-errors")
async def get_order_tracking_with_errors(
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Get all order tracking records that have errors"""
    
    try:
        results = db_service.search_order_tracking(has_errors=True, limit=limit, include_blob_data=include_blob_data)
        tracking_records = [OrderTrackingEntry(**record) for record in results]
        
        return JSONResponse(content={
            "success": True,
            "tracking_records": [record.dict() for record in tracking_records],
            "total_found": len(tracking_records),
            "has_errors": True
        })
        
    except Exception as e:
        logger.error(f"Error searching for orders with errors: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# ============================================================================
# CWORDERINSTANCE Endpoints
# ============================================================================

@app.post("/order-instances/search", response_model=OrderInstanceResponse)
async def search_order_instances(request: OrderInstanceSearchRequest):
    """Search CWORDERINSTANCE by various criteria"""
    
    try:
        logger.info(f"Searching order instances with criteria: {request.dict(exclude_none=True)}")
        
        # Execute search
        results = db_service.search_order_instances(
            cwdocid=request.cwdocid,
            customerid=request.customerid,
            accountid=request.accountid,
            ordertype=request.ordertype,
            ordersubtype=request.ordersubtype,
            status=request.status,
            state=request.state,
            quoteid=request.quoteid,
            externalorderid=request.externalorderid,
            productcode=request.productcode,
            parentorder=request.parentorder,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            include_blob_data=request.include_blob_data
        )
        
        # Convert to response models
        order_instances = [OrderInstanceEntry(**instance) for instance in results]
        
        # Check if data was truncated
        data_truncated = len(results) >= request.limit
        
        return OrderInstanceResponse(
            success=True,
            order_instances=order_instances,
            total_found=len(order_instances),
            search_criteria=request.dict(exclude_none=True),
            data_truncated=data_truncated
        )
        
    except Exception as e:
        logger.error(f"Order instance search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Order instance search failed: {str(e)}"
        )

@app.get("/order-instances/{cwdocid}")
async def get_order_instance_by_cwdocid(cwdocid: str, include_blob_data: bool = Query(default=True)):
    """Get a specific order instance by CWDOCID (primary key)"""
    
    try:
        logger.info(f"Retrieving order instance: {cwdocid}")
        
        result = db_service.get_order_instance_by_cwdocid(cwdocid, include_blob_data=include_blob_data)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Order instance {cwdocid} not found"
            )
        
        return JSONResponse(content={
            "success": True,
            "order_instance": OrderInstanceEntry(**result).dict(),
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving order instance {cwdocid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve order instance: {str(e)}"
        )

@app.get("/order-instances/by-customerid/{customerid}")
async def get_order_instances_by_customerid(
    customerid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by Customer ID"""
    
    try:
        results = db_service.search_order_instances(customerid=customerid, limit=limit, include_blob_data=include_blob_data)
        order_instances = [OrderInstanceEntry(**instance) for instance in results]
        
        return JSONResponse(content={
            "success": True,
            "order_instances": [instance.dict() for instance in order_instances],
            "total_found": len(order_instances),
            "customerid": customerid
        })
        
    except Exception as e:
        logger.error(f"Error searching by customerid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/order-instances/by-quoteid/{quoteid}")
async def get_order_instances_by_quoteid(
    quoteid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by Quote ID"""
    
    try:
        results = db_service.search_order_instances(quoteid=quoteid, limit=limit, include_blob_data=include_blob_data)
        order_instances = [OrderInstanceEntry(**instance) for instance in results]
        
        return JSONResponse(content={
            "success": True,
            "order_instances": [instance.dict() for instance in order_instances],
            "total_found": len(order_instances),
            "quoteid": quoteid
        })
        
    except Exception as e:
        logger.error(f"Error searching by quoteid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/order-instances/by-externalorderid/{externalorderid}")
async def get_order_instances_by_externalorderid(
    externalorderid: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    include_blob_data: bool = Query(default=False)
):
    """Quick search by External Order ID"""
    
    try:
        results = db_service.search_order_instances(externalorderid=externalorderid, limit=limit, include_blob_data=include_blob_data)
        order_instances = [OrderInstanceEntry(**instance) for instance in results]
        
        return JSONResponse(content={
            "success": True,
            "order_instances": [instance.dict() for instance in order_instances],
            "total_found": len(order_instances),
            "externalorderid": externalorderid
        })
        
    except Exception as e:
        logger.error(f"Error searching by externalorderid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# ============================================================================
# AI TROUBLESHOOTING PLANS ENDPOINTS
# ============================================================================

@app.post("/plans", status_code=status.HTTP_201_CREATED)
async def create_plan(request: PlanCreateRequest):
    """Create a new troubleshooting plan"""
    
    try:
        result = db_service.create_plan(
            goal_type=request.goal_type,
            order_type=request.order_type,
            title=request.title,
            description=request.description,
            steps=request.steps,
            expected_outcomes=request.expected_outcomes,
            confidence=request.confidence
        )
        
        return JSONResponse(content={
            "success": True,
            "plan_id": result["plan_id"],
            "message": result["message"]
        }, status_code=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create plan: {str(e)}"
        )

@app.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get a specific troubleshooting plan by ID"""
    
    try:
        plan = db_service.get_plan(plan_id)
        
        if not plan:
            raise HTTPException(
                status_code=404,
                detail=f"Plan not found: {plan_id}"
            )
        
        plan_entry = TroubleshootingPlanEntry(**plan)
        
        return JSONResponse(content={
            "success": True,
            "plan": plan_entry.dict()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get plan: {str(e)}"
        )

@app.post("/plans/search")
async def search_plans(request: PlanSearchRequest):
    """Search troubleshooting plans"""
    
    try:
        results = db_service.search_plans(
            goal_type=request.goal_type,
            order_type=request.order_type,
            is_active=request.is_active,
            min_success_rate=request.min_success_rate,
            limit=request.limit
        )
        
        plans = [TroubleshootingPlanEntry(**plan) for plan in results]
        
        return JSONResponse(content={
            "success": True,
            "plans": [plan.dict() for plan in plans],
            "total_found": len(plans),
            "search_criteria": request.dict(exclude_none=True)
        })
        
    except Exception as e:
        logger.error(f"Error searching plans: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.put("/plans/{plan_id}")
async def update_plan(plan_id: str, request: PlanUpdateRequest):
    """Update a troubleshooting plan"""
    
    try:
        result = db_service.update_plan(
            plan_id=plan_id,
            title=request.title,
            description=request.description,
            steps=request.steps,
            expected_outcomes=request.expected_outcomes,
            confidence=request.confidence,
            is_active=request.is_active
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Update failed")
            )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update plan: {str(e)}"
        )

@app.post("/plans/{plan_id}/usage")
async def update_plan_usage(plan_id: str, request: PlanUsageUpdateRequest):
    """Update plan usage statistics after execution"""
    
    try:
        result = db_service.update_plan_usage(
            plan_id=plan_id,
            success=request.success
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error updating plan usage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update plan usage: {str(e)}"
        )

@app.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str):
    """Delete (deactivate) a troubleshooting plan"""
    
    try:
        result = db_service.delete_plan(plan_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error deleting plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete plan: {str(e)}"
        )

@app.get("/plans/by-goal-type/{goal_type}")
async def get_plans_by_goal_type(
    goal_type: str,
    order_type: Optional[str] = Query(None),
    is_active: int = Query(1, ge=0, le=1),
    limit: int = Query(50, ge=1, le=500)
):
    """Quick search plans by goal type"""
    
    try:
        results = db_service.search_plans(
            goal_type=goal_type,
            order_type=order_type,
            is_active=is_active,
            limit=limit
        )
        
        plans = [TroubleshootingPlanEntry(**plan) for plan in results]
        
        return JSONResponse(content={
            "success": True,
            "plans": [plan.dict() for plan in plans],
            "total_found": len(plans),
            "goal_type": goal_type
        })
        
    except Exception as e:
        logger.error(f"Error searching by goal_type: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# ============================================================================
# PLAN EXECUTION HISTORY ENDPOINTS
# ============================================================================

@app.post("/execution-history", status_code=status.HTTP_201_CREATED)
async def create_execution_history(request: ExecutionHistoryCreateRequest):
    """Create a plan execution history record"""
    
    try:
        result = db_service.create_execution_history(
            plan_id=request.plan_id,
            order_id=request.order_id,
            execution_time_ms=request.execution_time_ms,
            success=request.success,
            error_message=request.error_message,
            collected_data_summary=request.collected_data_summary,
            analysis_result=request.analysis_result
        )
        
        return JSONResponse(content=result, status_code=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating execution history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create execution history: {str(e)}"
        )

@app.get("/execution-history")
async def get_execution_history(
    plan_id: Optional[str] = Query(None),
    order_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """Get plan execution history"""
    
    try:
        results = db_service.get_execution_history(
            plan_id=plan_id,
            order_id=order_id,
            limit=limit
        )
        
        history = [PlanExecutionHistoryEntry(**record) for record in results]
        
        return JSONResponse(content={
            "success": True,
            "history": [record.dict() for record in history],
            "total_found": len(history),
            "search_criteria": {
                "plan_id": plan_id,
                "order_id": order_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting execution history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution history: {str(e)}"
        )

@app.get("/execution-history/by-plan/{plan_id}")
async def get_execution_history_by_plan(
    plan_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """Get execution history for a specific plan"""
    
    try:
        results = db_service.get_execution_history(
            plan_id=plan_id,
            limit=limit
        )
        
        history = [PlanExecutionHistoryEntry(**record) for record in results]
        
        return JSONResponse(content={
            "success": True,
            "history": [record.dict() for record in history],
            "total_found": len(history),
            "plan_id": plan_id
        })
        
    except Exception as e:
        logger.error(f"Error getting execution history by plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution history: {str(e)}"
        )


# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {config.api.api_title} server...")
    
    # Check configuration
    if not config.is_ready():
        logger.error("Configuration not ready - missing required Oracle database settings")
        sys.exit(1)
    
    uvicorn.run(
        "main:app",
        host=config.api.api_host,
        port=config.api.api_port,
        log_level=config.api.log_level.lower(),
        reload=config.api.environment == "development"
    )

