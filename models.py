"""
Pydantic models for Oracle Database API

Defines request and response schemas for all API endpoints.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

# Response Models
class BaseResponse(BaseModel):
    """Base response model"""
    success: bool
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = False
    error: str
    error_code: Optional[str] = None

class HealthResponse(BaseResponse):
    """Health check response"""
    service: str = "Oracle Database API"
    version: str = "1.0.0"
    database_connected: bool
    uptime_seconds: float

# Order Data Models
class OrderInfo(BaseModel):
    """Order information model"""
    order_id: str
    customer_id: Optional[str] = None
    status: str
    total_amount: Optional[float] = None
    created_date: Optional[str] = None
    last_updated: Optional[str] = None
    order_type: Optional[str] = None
    priority: Optional[str] = None

class PaymentInfo(BaseModel):
    """Payment information model"""
    payment_id: str
    order_id: str
    status: str
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    created_date: Optional[str] = None
    processed_date: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None

class ShippingInfo(BaseModel):
    """Shipping information model"""
    shipping_id: str
    order_id: str
    status: str
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    service_type: Optional[str] = None
    shipped_date: Optional[str] = None
    expected_delivery: Optional[str] = None
    actual_delivery: Optional[str] = None
    shipping_address: Optional[str] = None
    special_instructions: Optional[str] = None

class InventoryInfo(BaseModel):
    """Inventory information model"""
    item_id: str
    order_id: str
    product_id: Optional[str] = None
    sku: Optional[str] = None
    quantity_ordered: Optional[int] = None
    quantity_allocated: Optional[int] = None
    quantity_shipped: Optional[int] = None
    warehouse_location: Optional[str] = None
    reservation_status: Optional[str] = None
    allocation_date: Optional[str] = None
    shipped_date: Optional[str] = None

class AuditEntry(BaseModel):
    """Audit log entry model"""
    log_id: str
    order_id: str
    action_type: str
    action_details: Optional[str] = None
    performed_by: Optional[str] = None
    performed_at: Optional[str] = None
    system_component: Optional[str] = None
    result_status: Optional[str] = None
    error_details: Optional[str] = None
    session_id: Optional[str] = None

class ErrorLogEntry(BaseModel):
    """Error log entry model"""
    error_id: str
    order_id: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_timestamp: Optional[str] = None
    component: Optional[str] = None
    severity: Optional[str] = None
    stack_trace: Optional[str] = None
    user_context: Optional[str] = None
    correlation_id: Optional[str] = None

class SystemEvent(BaseModel):
    """System event model"""
    event_id: str
    order_id: str
    event_type: str
    event_data: Optional[str] = None
    event_timestamp: Optional[str] = None
    source_system: Optional[str] = None
    correlation_id: Optional[str] = None
    processing_status: Optional[str] = None
    retry_count: Optional[int] = None

class TimelineEntry(BaseModel):
    """Timeline entry model"""
    event_source: str
    event_timestamp: Optional[str] = None
    event_description: str
    event_data: Optional[str] = None

class CustomerInfo(BaseModel):
    """Customer information model"""
    customer_id: str
    customer_type: Optional[str] = None
    account_status: Optional[str] = None
    tier: Optional[str] = None
    created_date: Optional[str] = None
    last_login_date: Optional[str] = None
    risk_score: Optional[float] = None
    contact_preferences: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None

class DataSummary(BaseModel):
    """Summary of data counts"""
    total_payments: int = 0
    total_shipments: int = 0
    total_inventory_items: int = 0
    total_audit_entries: int = 0
    total_errors: int = 0
    total_events: int = 0
    timeline_entries: int = 0
    related_orders_count: int = 0

# Complete Order Response
class CompleteOrderResponse(BaseResponse):
    """Complete order data response"""
    order_exists: bool
    order_id: str
    order_info: Optional[OrderInfo] = None
    customer_info: Optional[CustomerInfo] = None
    payments: List[PaymentInfo] = []
    shipping: List[ShippingInfo] = []
    inventory: List[InventoryInfo] = []
    audit_trail: List[AuditEntry] = []
    error_log: List[ErrorLogEntry] = []
    system_events: List[SystemEvent] = []
    timeline: List[TimelineEntry] = []
    related_orders: List[OrderInfo] = []
    data_summary: Optional[DataSummary] = None
    query_timestamp: Optional[str] = None

# Individual Data Type Responses
class OrderStatusResponse(BaseResponse):
    """Order status response"""
    order_info: Optional[OrderInfo] = None
    order_exists: bool

class PaymentDetailsResponse(BaseResponse):
    """Payment details response"""
    payments: List[PaymentInfo] = []
    order_id: str

class ShippingDetailsResponse(BaseResponse):
    """Shipping details response"""
    shipping: List[ShippingInfo] = []
    order_id: str

class InventoryStatusResponse(BaseResponse):
    """Inventory status response"""
    inventory: List[InventoryInfo] = []
    order_id: str

class AuditLogResponse(BaseResponse):
    """Audit log response"""
    audit_trail: List[AuditEntry] = []
    order_id: str
    total_entries: int

class ErrorLogResponse(BaseResponse):
    """Error log response"""  
    error_log: List[ErrorLogEntry] = []
    order_id: str
    total_errors: int

class SystemEventsResponse(BaseResponse):
    """System events response"""
    system_events: List[SystemEvent] = []
    order_id: str
    total_events: int

class OrderTimelineResponse(BaseResponse):
    """Order timeline response"""
    timeline: List[TimelineEntry] = []
    order_id: str
    total_entries: int

class RelatedOrdersResponse(BaseResponse):
    """Related orders response"""
    related_orders: List[OrderInfo] = []
    order_id: str
    customer_id: Optional[str] = None
    total_related: int

# Search Request Models
class OrderSearchRequest(BaseModel):
    """Order search request"""
    customer_id: Optional[str] = Field(None, description="Search by customer ID")
    status: Optional[str] = Field(None, description="Search by order status")
    start_date: Optional[str] = Field(None, description="Start date for status search (ISO format)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v

class OrderSearchResponse(BaseResponse):
    """Order search response"""
    orders: List[OrderInfo] = []
    total_found: int
    search_criteria: Dict[str, Any]

# System Health Models
class PerformanceMetric(BaseModel):
    """Performance metric model"""
    component_name: str
    avg_response_time_ms: Optional[float] = None
    error_rate_percent: Optional[float] = None
    last_updated: Optional[str] = None
    status: Optional[str] = None

class SystemHealthResponse(BaseResponse):
    """System health response"""
    metrics: List[PerformanceMetric] = []
    overall_status: str = "unknown"
    timestamp: Optional[str] = None

# Database Test Response
class DatabaseTestResponse(BaseResponse):
    """Database connection test response"""
    message: str
    connection_pool_status: Optional[Dict[str, Any]] = None

# ============================================================================
# CWMESSAGELOG Models
# ============================================================================

class MessageLogEntry(BaseModel):
    """CWMESSAGELOG entry model"""
    msgid: int
    vmid: int
    inter_type: int
    operation: str
    user_id: Optional[str] = None
    user_data1: Optional[str] = None
    user_data2: Optional[str] = None
    user_data3: Optional[str] = None
    creation_time: str
    send_time: Optional[str] = None
    receive_time: Optional[str] = None
    receive_charset: Optional[str] = None
    send_msg_priority: Optional[str] = None
    receive_msg_priority: Optional[str] = None
    send_msg_seqid: Optional[str] = None
    receive_msg_seqid: Optional[str] = None
    send_msg_retrycount: Optional[int] = None
    receive_msg_retrycount: Optional[int] = None
    send_msg_correltionid: Optional[str] = None
    receive_msg_correltionid: Optional[str] = None
    account_id: Optional[str] = None
    order_id: Optional[str] = None
    process_id: Optional[int] = None
    transaction_id: Optional[int] = None
    activity_id: Optional[str] = None
    customer_id: Optional[str] = None
    failure: Optional[int] = None
    attemptcount: Optional[int] = None
    app_name: Optional[str] = None
    service_port: Optional[str] = None
    # BLOB fields stored as base64 strings
    send_data: Optional[str] = None
    receive_data: Optional[str] = None
    send_msg_props: Optional[str] = None
    receive_msg_props: Optional[str] = None

class MessageLogSearchRequest(BaseModel):
    """Message log search request"""
    user_data1: Optional[str] = Field(None, description="Search by user_data1")
    user_data2: Optional[str] = Field(None, description="Search by user_data2")
    user_data3: Optional[str] = Field(None, description="Search by user_data3")
    order_id: Optional[str] = Field(None, description="Search by order_id")
    customer_id: Optional[str] = Field(None, description="Search by customer_id")
    operation: Optional[str] = Field(None, description="Search by operation")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    include_blob_data: bool = Field(default=False, description="Include BLOB data in response (may be large)")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v

class MessageLogResponse(BaseResponse):
    """Message log search response"""
    messages: List[MessageLogEntry] = []
    total_found: int
    search_criteria: Dict[str, Any]
    data_truncated: bool = False

# ============================================================================
# ORDER_ORDER_HEADER Models
# ============================================================================

class OrderHeaderEntry(BaseModel):
    """ORDER_ORDER_HEADER entry model"""
    cwdocid: str
    cwdocstamp: Optional[str] = None
    cwordercreationdate: Optional[str] = None
    cworderid: Optional[str] = None
    cwparentid: Optional[str] = None
    lastupdateddate: Optional[str] = None
    duedate: Optional[str] = None
    updatedby: Optional[str] = None
    omorderid: Optional[str] = None
    quoteid: Optional[str] = None
    quoteguid: Optional[str] = None
    ordertype: Optional[str] = None
    servicecaseid: Optional[str] = None
    action: Optional[str] = None
    dpiordernumber: Optional[str] = None
    reservationid: Optional[str] = None
    customerordertype: Optional[str] = None
    orderhash: Optional[str] = None
    ponr: Optional[int] = None
    dpienvironment: Optional[str] = None
    dpioperationrequested: Optional[str] = None
    controlnumber: Optional[int] = None
    billingtelephonenumber: Optional[str] = None
    telephonenumber: Optional[str] = None
    universalserviceid: Optional[str] = None
    companyid: Optional[str] = None
    ishoa: Optional[int] = None
    onttype: Optional[str] = None
    isequipmentchanged: Optional[int] = None
    ordersequence: Optional[int] = None
    recordlocatornumber: Optional[str] = None
    cancelreason: Optional[str] = None
    checkactiveservices: Optional[int] = None
    onhold: Optional[int] = None
    installationtype: Optional[str] = None
    telephonenumbernxx: Optional[str] = None
    telephonenumbernpa: Optional[str] = None
    telephonenumberstation: Optional[str] = None
    telephonenumberextension: Optional[str] = None
    trackingid: Optional[str] = None
    datetime: Optional[str] = None
    heartbeat: Optional[int] = None
    providerid: Optional[str] = None
    providername: Optional[str] = None
    providertype: Optional[str] = None
    providerversionid: Optional[str] = None
    providerversiondatetime: Optional[str] = None
    providerdescription: Optional[str] = None
    providerlocation: Optional[str] = None
    providertransactionid: Optional[str] = None
    traceresultmessage: Optional[str] = None
    traceresulthostname: Optional[str] = None
    tracesettingstraceenabled: Optional[int] = None
    tracesettingstracelevel: Optional[str] = None
    tracesettingscomponent: Optional[str] = None
    traceresultcomponent: Optional[str] = None
    traceresultdatetime: Optional[str] = None
    consumertrackingid: Optional[str] = None
    consumerapplicationid: Optional[str] = None
    consumeremployeeid: Optional[str] = None
    consumeruserid: Optional[str] = None
    consumertransactionid: Optional[str] = None
    requireseocprovisioning: Optional[int] = None
    tcprovisioningrequired: Optional[int] = None
    triadprovisioningrequired: Optional[int] = None
    soaprovisioningrequired: Optional[int] = None
    servicemanprovisioningrequired: Optional[int] = None
    hsiprovisioningrequired: Optional[int] = None
    recordonlychange: Optional[int] = None
    stagecode: Optional[str] = None
    tcprovnotificationstatus: Optional[str] = None
    triadprovnotificationstatus: Optional[str] = None
    soapprovnotificationstatus: Optional[str] = None
    sermanprovnotificationstatus: Optional[str] = None
    hsiprovnotificationstatus: Optional[str] = None
    laststagecodemodifiedtimestamp: Optional[str] = None
    duedatemodified: Optional[int] = None
    cwcreated: Optional[str] = None
    locked: Optional[int] = None
    isfutureduedate: Optional[int] = None
    mainprocid: Optional[int] = None
    orderorigin: Optional[str] = None
    legacyprocid: Optional[int] = None
    isringcentral: Optional[int] = None
    ringcentralaccountid: Optional[str] = None
    termsofserviceenabled: Optional[int] = None
    tradingname: Optional[str] = None
    accountuuid: Optional[str] = None
    portingstatus: Optional[str] = None
    portingmilestone: Optional[str] = None
    isnewcustomer: Optional[int] = None
    isdataonly: Optional[int] = None
    islitont: Optional[int] = None
    locationid: Optional[str] = None
    ontserialnumber: Optional[str] = None
    # NCLOB fields stored as base64 strings
    bucket: Optional[str] = None
    orderrequestheaderdata: Optional[str] = None
    orderrequestdata: Optional[str] = None
    serializeddpisubmit: Optional[str] = None
    dpiorderlinemappingdata: Optional[str] = None
    confirmorderhttpheader: Optional[str] = None
    canbereachedtelephonenumber: Optional[str] = None
    dropshipordernumber: Optional[str] = None

class OrderHeaderSearchRequest(BaseModel):
    """Order header search request"""
    cworderid: Optional[str] = Field(None, description="Search by CW Order ID")
    omorderid: Optional[str] = Field(None, description="Search by OM Order ID")
    quoteid: Optional[str] = Field(None, description="Search by Quote ID")
    telephonenumber: Optional[str] = Field(None, description="Search by telephone number")
    universalserviceid: Optional[str] = Field(None, description="Search by Universal Service ID")
    ordertype: Optional[str] = Field(None, description="Search by order type")
    stagecode: Optional[str] = Field(None, description="Search by stage code")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    include_blob_data: bool = Field(default=False, description="Include BLOB data in response (may be large)")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v

class OrderHeaderResponse(BaseResponse):
    """Order header search response"""
    orders: List[OrderHeaderEntry] = []
    total_found: int
    search_criteria: Dict[str, Any]
    data_truncated: bool = False

# ============================================================================
# ORDER_TRACKING_INFO Models
# ============================================================================

class OrderTrackingEntry(BaseModel):
    """ORDER_TRACKING_INFO entry model"""
    cwdocid: str
    orderinfo: Optional[str] = None
    cwdocstamp: Optional[str] = None
    cwordercreationdate: Optional[str] = None
    cworderid: Optional[str] = None
    cwparentid: Optional[str] = None
    lastupdatedtimestamp: Optional[str] = None
    updatedby: Optional[str] = None
    wfmerrorid: Optional[str] = None
    processwaitingforwfm: Optional[int] = None
    scaseid: Optional[str] = None
    icaseid: Optional[str] = None
    workid: Optional[str] = None
    casestatus: Optional[str] = None
    executionstatusmessage: Optional[str] = None
    pegaapiinfo: Optional[str] = None
    pegaapistatus: Optional[str] = None
    esbapiinfo: Optional[str] = None
    esbapistatus: Optional[str] = None
    customerapiinfo: Optional[str] = None
    customerapistatus: Optional[str] = None
    dpiapiinfo: Optional[str] = None
    dpiapistatus: Optional[str] = None
    preordererrorsystems: Optional[int] = None
    errorsrvcvalidation: Optional[int] = None
    triaderrorid_ia: Optional[str] = None
    triadintfstatus: Optional[str] = None
    dpierrorid_disp: Optional[str] = None
    dpierrorid_ia: Optional[str] = None
    dpisbmostatus: Optional[str] = None
    triadinvolvementorderlevel: Optional[str] = None
    orderid: Optional[str] = None
    orderstatus: Optional[str] = None
    preorderstatus: Optional[str] = None
    flowstatus: Optional[str] = None
    dpiumstatus: Optional[str] = None
    dpiumerrorid_ia: Optional[str] = None
    triaderrorid_disp: Optional[str] = None
    tcintfstatus: Optional[str] = None
    tcinvolvementorderlevel: Optional[str] = None
    tcerrorid_ia: Optional[str] = None
    tcerrorid_disp: Optional[str] = None
    customernotiferrorid_ia: Optional[str] = None
    customernotiferrorid_disp: Optional[str] = None
    customernotifstatus: Optional[str] = None
    emailupdates: Optional[str] = None
    lastorderlinenumber: Optional[int] = None
    isdispatch: Optional[str] = None
    workunitcalculation: Optional[int] = None
    procid: Optional[str] = None
    numberofitems: Optional[int] = None
    lasttriadoperation: Optional[str] = None
    canprocid: Optional[str] = None
    triadcanerrorid_ia: Optional[str] = None
    dpiorderid: Optional[str] = None
    responsibleparty: Optional[str] = None
    igcandidate: Optional[str] = None
    hasdpievererrored: Optional[int] = None
    dpistandaloneprocid: Optional[str] = None
    notifycustomerprocid: Optional[str] = None
    notsupportedprovsystemfound: Optional[int] = None
    purgeorder: Optional[int] = None
    iscancelledbyoc: Optional[str] = None
    cancelremark: Optional[str] = None
    triadretry: Optional[str] = None
    lastupdateddate: Optional[str] = None
    orderlock: Optional[int] = None
    bicfss: Optional[str] = None
    bi: Optional[str] = None
    numberofcfssitems: Optional[int] = None
    passedheldstage: Optional[int] = None
    # NCLOB fields stored as base64 strings
    wfmerrormessage: Optional[str] = None
    errordescription: Optional[str] = None
    wfmerror: Optional[str] = None
    dpirsperrors: Optional[str] = None
    dropdetails: Optional[str] = None

class OrderTrackingSearchRequest(BaseModel):
    """Order tracking search request"""
    cworderid: Optional[str] = Field(None, description="Search by CW Order ID")
    orderid: Optional[str] = Field(None, description="Search by Order ID")
    workid: Optional[str] = Field(None, description="Search by Work ID")
    scaseid: Optional[str] = Field(None, description="Search by SCASE ID")
    icaseid: Optional[str] = Field(None, description="Search by ICASE ID")
    orderstatus: Optional[str] = Field(None, description="Search by order status")
    casestatus: Optional[str] = Field(None, description="Search by case status")
    flowstatus: Optional[str] = Field(None, description="Search by flow status")
    has_errors: Optional[bool] = Field(None, description="Filter for orders with/without errors")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    include_blob_data: bool = Field(default=False, description="Include NCLOB data in response (may be large)")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v

class OrderTrackingResponse(BaseResponse):
    """Order tracking search response"""
    tracking_records: List[OrderTrackingEntry] = []
    total_found: int
    search_criteria: Dict[str, Any]
    data_truncated: bool = False

# ============================================================================
# CWORDERINSTANCE Models
# ============================================================================

class OrderInstanceEntry(BaseModel):
    """CWORDERINSTANCE entry model"""
    cwdocid: str
    metadatatype: int
    status: Optional[str] = None
    state: str
    visualkey: str
    productcode: Optional[str] = None
    creationdate: str
    createdby: str
    updatedby: str
    lastupdateddate: str
    parentorder: Optional[str] = None
    owner: Optional[str] = None
    state2: Optional[str] = None
    hasattachment: int
    metadatatype_ver: int
    original_order_id: Optional[str] = None
    source_order_id: Optional[str] = None
    kind_of_order: Optional[str] = None
    order_phase: Optional[str] = None
    project_id: Optional[str] = None
    process_id: Optional[int] = None
    cworderstamp: Optional[str] = None
    cwdocstamp: Optional[str] = None
    app_name: Optional[str] = None
    duedate: Optional[str] = None
    basketid: Optional[str] = None
    cwuserrole: Optional[str] = None
    ostate: Optional[str] = None
    customerid: Optional[str] = None
    accountid: Optional[str] = None
    ordertype: Optional[str] = None
    ordersubtype: Optional[str] = None
    relatedorder: Optional[str] = None
    ordernum: Optional[int] = None
    ordver: Optional[int] = None
    effectivedate: Optional[str] = None
    submittedby: Optional[str] = None
    submitteddate: Optional[str] = None
    price: Optional[float] = None
    onetimeprice: Optional[float] = None
    pricedon: Optional[str] = None
    correlationid: Optional[str] = None
    quoteid: Optional[str] = None
    channel: Optional[str] = None
    expirationdate: Optional[str] = None
    quoteexpirationdate: Optional[str] = None
    assignedpriority: Optional[int] = None
    requestedstartdate: Optional[str] = None
    requestedcompletiondate: Optional[str] = None
    description: Optional[str] = None
    bitype: Optional[str] = None
    externalorderid: Optional[str] = None
    isbundled: Optional[int] = None
    mode_sc: Optional[str] = None
    islocked: Optional[int] = None
    requester: Optional[str] = None
    bispecification: Optional[str] = None
    quoteon: Optional[str] = None
    completiondate: Optional[str] = None
    extendedstate: Optional[str] = None
    orderrole: Optional[str] = None
    orderidref: Optional[str] = None
    prevostate: Optional[str] = None
    pmprojectid: Optional[str] = None
    pmprojecttype: Optional[str] = None
    # NCLOB fields stored as base64 strings
    notes: Optional[str] = None
    attrs: Optional[str] = None
    relatedentities: Optional[str] = None
    relatedscs: Optional[str] = None
    relatedorders: Optional[str] = None
    catalogcontextattrs: Optional[str] = None

class OrderInstanceSearchRequest(BaseModel):
    """Order instance search request"""
    cwdocid: Optional[str] = Field(None, description="Search by CW Document ID")
    customerid: Optional[str] = Field(None, description="Search by Customer ID")
    accountid: Optional[str] = Field(None, description="Search by Account ID")
    ordertype: Optional[str] = Field(None, description="Search by order type")
    ordersubtype: Optional[str] = Field(None, description="Search by order subtype")
    status: Optional[str] = Field(None, description="Search by status")
    state: Optional[str] = Field(None, description="Search by state")
    quoteid: Optional[str] = Field(None, description="Search by Quote ID")
    externalorderid: Optional[str] = Field(None, description="Search by External Order ID")
    productcode: Optional[str] = Field(None, description="Search by Product Code")
    parentorder: Optional[str] = Field(None, description="Search by Parent Order")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    include_blob_data: bool = Field(default=False, description="Include NCLOB data in response (may be large)")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v

class OrderInstanceResponse(BaseResponse):
    """Order instance search response"""
    order_instances: List[OrderInstanceEntry] = []
    total_found: int
    search_criteria: Dict[str, Any]
    data_truncated: bool = False


# ============================================================================
# AI TROUBLESHOOTING PLANS MODELS
# ============================================================================

class TroubleshootingPlanEntry(BaseModel):
    """Troubleshooting plan entry model"""
    plan_id: str
    goal_type: str
    order_type: Optional[str] = None
    title: str
    description: Optional[str] = None
    steps: Optional[str] = None  # JSON string
    expected_outcomes: Optional[str] = None  # JSON string
    confidence: Optional[float] = None
    success_count: Optional[int] = None
    total_usage: Optional[int] = None
    created_date: Optional[str] = None
    last_used_date: Optional[str] = None
    last_updated_date: Optional[str] = None
    created_by: Optional[str] = None
    is_active: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "a1b2c3d4e5f6",
                "goal_type": "order_analysis",
                "order_type": "fiber_installation",
                "title": "Comprehensive Order Analysis",
                "confidence": 0.85,
                "success_count": 10,
                "total_usage": 12
            }
        }

class PlanCreateRequest(BaseModel):
    """Request to create a new troubleshooting plan"""
    goal_type: str = Field(..., description="Type of goal (e.g., order_analysis, error_investigation)")
    order_type: Optional[str] = Field(None, description="Specific order type (nullable for generic plans)")
    title: str = Field(..., description="Plan title")
    description: Optional[str] = Field(None, description="Detailed description")
    steps: str = Field(..., description="JSON array of troubleshooting steps")
    expected_outcomes: Optional[str] = Field(None, description="JSON array of expected outcomes")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="AI confidence score (0.0 to 1.0)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "goal_type": "order_analysis",
                "order_type": "fiber_installation",
                "title": "Comprehensive Order Analysis",
                "description": "Detailed workflow-based troubleshooting",
                "steps": '[{"step": 1, "action": "Gather order details"}]',
                "expected_outcomes": '["Identify root cause", "Provide recommendations"]',
                "confidence": 0.85
            }
        }

class PlanUpdateRequest(BaseModel):
    """Request to update a troubleshooting plan"""
    title: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[str] = None
    expected_outcomes: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[int] = Field(None, ge=0, le=1)

class PlanUsageUpdateRequest(BaseModel):
    """Request to update plan usage statistics"""
    success: bool = Field(..., description="Whether the execution was successful")

class PlanSearchRequest(BaseModel):
    """Search request for troubleshooting plans"""
    goal_type: Optional[str] = None
    order_type: Optional[str] = None
    is_active: Optional[int] = Field(None, ge=0, le=1)
    min_success_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    limit: int = Field(50, ge=1, le=500)

class PlanResponse(BaseResponse):
    """Single plan response"""
    plan: Optional[TroubleshootingPlanEntry] = None

class PlanListResponse(BaseResponse):
    """Plan list response"""
    plans: List[TroubleshootingPlanEntry] = []
    total_found: int
    search_criteria: Dict[str, Any]

class PlanExecutionHistoryEntry(BaseModel):
    """Plan execution history entry"""
    execution_id: int
    plan_id: str
    order_id: Optional[str] = None
    execution_date: Optional[str] = None
    execution_time_ms: Optional[int] = None
    success: int
    error_message: Optional[str] = None
    collected_data_summary: Optional[str] = None  # JSON string
    analysis_result: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": 1,
                "plan_id": "a1b2c3d4e5f6",
                "order_id": "12345",
                "execution_time_ms": 5000,
                "success": 1
            }
        }

class ExecutionHistoryCreateRequest(BaseModel):
    """Request to create execution history record"""
    plan_id: str = Field(..., description="Plan ID that was executed")
    order_id: Optional[str] = Field(None, description="Order ID analyzed")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    success: bool = Field(..., description="Whether execution was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    collected_data_summary: Optional[str] = Field(None, description="JSON summary of collected data")
    analysis_result: Optional[str] = Field(None, description="Full analysis result")

class ExecutionHistoryResponse(BaseResponse):
    """Execution history response"""
    history: List[PlanExecutionHistoryEntry] = []
    total_found: int
    search_criteria: Dict[str, Any]