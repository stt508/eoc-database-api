-- Oracle Database Schema for EOC Log Analyzer
-- Multi-agent system for order troubleshooting
-- 
-- Run this script as your application database user to create the required tables

-- ============================================================================
-- PLAN STORAGE SCHEMA
-- ============================================================================

-- Troubleshooting Plans Table
CREATE TABLE troubleshooting_plans (
    id VARCHAR2(50) PRIMARY KEY,
    goal_type VARCHAR2(100) NOT NULL,
    order_type VARCHAR2(100),
    plan_data CLOB CHECK (plan_data IS JSON),
    success_rate NUMBER(5,4) DEFAULT 0,
    usage_count NUMBER(10) DEFAULT 0,
    total_success_count NUMBER(10) DEFAULT 0,
    total_failure_count NUMBER(10) DEFAULT 0,
    avg_execution_time_ms NUMBER(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR2(100),
    version NUMBER(5) DEFAULT 1,
    is_active NUMBER(1) DEFAULT 1,
    CONSTRAINT chk_success_rate CHECK (success_rate >= 0 AND success_rate <= 1),
    CONSTRAINT chk_is_active CHECK (is_active IN (0, 1))
);

-- Index for fast plan lookups
CREATE INDEX idx_plans_goal_type ON troubleshooting_plans(goal_type, order_type, is_active);
CREATE INDEX idx_plans_success_rate ON troubleshooting_plans(success_rate DESC) WHERE is_active = 1;
CREATE INDEX idx_plans_created_at ON troubleshooting_plans(created_at DESC);

-- Plan Execution History Table
CREATE TABLE plan_execution_history (
    execution_id VARCHAR2(50) PRIMARY KEY,
    plan_id VARCHAR2(50) REFERENCES troubleshooting_plans(id),
    order_id VARCHAR2(100) NOT NULL,
    goal VARCHAR2(500),
    success NUMBER(1) NOT NULL,
    execution_time_ms NUMBER(10,2),
    error_message CLOB,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_by VARCHAR2(100),
    CONSTRAINT chk_execution_success CHECK (success IN (0, 1))
);

-- Index for execution history queries
CREATE INDEX idx_exec_history_plan ON plan_execution_history(plan_id, executed_at DESC);
CREATE INDEX idx_exec_history_order ON plan_execution_history(order_id, executed_at DESC);

-- ============================================================================
-- SAMPLE LOG DATA SCHEMA (for demonstration)
-- ============================================================================

-- Orders Table
CREATE TABLE orders (
    order_id VARCHAR2(50) PRIMARY KEY,
    customer_id VARCHAR2(50),
    status VARCHAR2(50),
    total_amount NUMBER(12,2),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payments Table  
CREATE TABLE payments (
    payment_id VARCHAR2(50) PRIMARY KEY,
    order_id VARCHAR2(50) REFERENCES orders(order_id),
    status VARCHAR2(50),
    amount NUMBER(12,2),
    payment_method VARCHAR2(50),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_date TIMESTAMP,
    error_message VARCHAR2(1000)
);

-- Shipping Table
CREATE TABLE shipping (
    shipping_id VARCHAR2(50) PRIMARY KEY,
    order_id VARCHAR2(50) REFERENCES orders(order_id),
    status VARCHAR2(50),
    tracking_number VARCHAR2(100),
    shipped_date TIMESTAMP,
    expected_delivery TIMESTAMP,
    carrier VARCHAR2(50)
);

-- Inventory Reservations Table
CREATE TABLE inventory_reservations (
    reservation_id VARCHAR2(50) PRIMARY KEY,
    order_id VARCHAR2(50) REFERENCES orders(order_id),
    product_id VARCHAR2(50),
    item_id VARCHAR2(50),
    quantity_ordered NUMBER(10),
    quantity_available NUMBER(10),
    reservation_status VARCHAR2(50),
    warehouse_location VARCHAR2(100)
);

-- Customers Table
CREATE TABLE customers (
    customer_id VARCHAR2(50) PRIMARY KEY,
    customer_type VARCHAR2(50),
    account_status VARCHAR2(50),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_date TIMESTAMP,
    risk_score NUMBER(3,2) DEFAULT 0
);

-- Audit Log Table
CREATE TABLE audit_log (
    log_id VARCHAR2(50) PRIMARY KEY,
    order_id VARCHAR2(50) REFERENCES orders(order_id),
    action_type VARCHAR2(100),
    action_details CLOB,
    performed_by VARCHAR2(100),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result_status VARCHAR2(50)
);

-- Error Log Table  
CREATE TABLE error_log (
    error_id VARCHAR2(50) PRIMARY KEY,
    order_id VARCHAR2(50) REFERENCES orders(order_id),
    error_code VARCHAR2(50),
    error_message CLOB,
    error_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    component VARCHAR2(100),
    severity VARCHAR2(20)
);

-- System Health Table
CREATE TABLE system_health (
    component_name VARCHAR2(100) PRIMARY KEY,
    status VARCHAR2(50),
    last_check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms NUMBER(10,2),
    error_count_last_hour NUMBER(10) DEFAULT 0
);

-- ============================================================================
-- INDEXES FOR LOG TABLES
-- ============================================================================

CREATE INDEX idx_orders_customer ON orders(customer_id, created_date DESC);
CREATE INDEX idx_payments_order ON payments(order_id, created_date DESC);
CREATE INDEX idx_shipping_order ON shipping(order_id, status);
CREATE INDEX idx_inventory_order ON inventory_reservations(order_id, reservation_status);
CREATE INDEX idx_audit_order ON audit_log(order_id, performed_at DESC);
CREATE INDEX idx_error_order ON error_log(order_id, error_timestamp DESC);
CREATE INDEX idx_system_health_time ON system_health(last_check_time DESC);

-- ============================================================================
-- SAMPLE DATA FOR TESTING
-- ============================================================================

-- Sample Customers
INSERT INTO customers (customer_id, customer_type, account_status, risk_score) VALUES
('CUST001', 'PREMIUM', 'ACTIVE', 0.1),
('CUST002', 'STANDARD', 'ACTIVE', 0.3),
('CUST003', 'ENTERPRISE', 'ACTIVE', 0.0);

-- Sample Orders
INSERT INTO orders (order_id, customer_id, status, total_amount) VALUES
('ORD001', 'CUST001', 'PROCESSING', 299.99),
('ORD002', 'CUST002', 'PAYMENT_FAILED', 149.50),
('ORD003', 'CUST003', 'SHIPPED', 1299.00);

-- Sample Payments
INSERT INTO payments (payment_id, order_id, status, amount, payment_method, error_message) VALUES
('PAY001', 'ORD001', 'COMPLETED', 299.99, 'CREDIT_CARD', NULL),
('PAY002', 'ORD002', 'FAILED', 149.50, 'CREDIT_CARD', 'Insufficient funds'),
('PAY003', 'ORD003', 'COMPLETED', 1299.00, 'WIRE_TRANSFER', NULL);

-- Sample Shipping
INSERT INTO shipping (shipping_id, order_id, status, tracking_number, carrier) VALUES
('SHIP001', 'ORD001', 'PREPARING', NULL, 'UPS'),
('SHIP002', 'ORD002', 'ON_HOLD', NULL, 'FEDEX'),
('SHIP003', 'ORD003', 'IN_TRANSIT', 'TRK123456789', 'UPS');

-- Sample Inventory
INSERT INTO inventory_reservations (reservation_id, order_id, product_id, item_id, quantity_ordered, quantity_available, reservation_status, warehouse_location) VALUES
('INV001', 'ORD001', 'PROD001', 'ITEM001', 1, 5, 'RESERVED', 'WAREHOUSE_A'),
('INV002', 'ORD002', 'PROD002', 'ITEM002', 2, 0, 'BACKORDERED', 'WAREHOUSE_B'),
('INV003', 'ORD003', 'PROD003', 'ITEM003', 1, 3, 'ALLOCATED', 'WAREHOUSE_A');

-- Sample Audit Log
INSERT INTO audit_log (log_id, order_id, action_type, action_details, performed_by, result_status) VALUES
('LOG001', 'ORD001', 'ORDER_CREATED', '{"customer": "CUST001", "amount": 299.99}', 'SYSTEM', 'SUCCESS'),
('LOG002', 'ORD001', 'PAYMENT_PROCESSED', '{"payment_method": "CREDIT_CARD"}', 'PAYMENT_SERVICE', 'SUCCESS'),
('LOG003', 'ORD002', 'ORDER_CREATED', '{"customer": "CUST002", "amount": 149.50}', 'SYSTEM', 'SUCCESS'),
('LOG004', 'ORD002', 'PAYMENT_FAILED', '{"error": "Insufficient funds"}', 'PAYMENT_SERVICE', 'FAILURE');

-- Sample Error Log
INSERT INTO error_log (error_id, order_id, error_code, error_message, component, severity) VALUES
('ERR001', 'ORD002', 'PAY001', 'Payment processing failed: Insufficient funds', 'PAYMENT_SERVICE', 'HIGH'),
('ERR002', 'ORD002', 'INV001', 'Product out of stock during reservation', 'INVENTORY_SERVICE', 'MEDIUM');

-- Sample System Health
INSERT INTO system_health (component_name, status, response_time_ms) VALUES
('PAYMENT_SERVICE', 'HEALTHY', 150.5),
('INVENTORY_SERVICE', 'DEGRADED', 2500.0),
('SHIPPING_SERVICE', 'HEALTHY', 89.3),
('ORDER_SERVICE', 'HEALTHY', 45.2);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMP UPDATES
-- ============================================================================

-- Trigger to update last_updated for orders
CREATE OR REPLACE TRIGGER trg_orders_updated
    BEFORE UPDATE ON orders
    FOR EACH ROW
BEGIN
    :NEW.last_updated := CURRENT_TIMESTAMP;
END;
/

-- Trigger to update updated_at for troubleshooting_plans
CREATE OR REPLACE TRIGGER trg_plans_updated
    BEFORE UPDATE ON troubleshooting_plans
    FOR EACH ROW
BEGIN
    :NEW.updated_at := CURRENT_TIMESTAMP;
END;
/

-- ============================================================================
-- STORED PROCEDURES FOR COMMON OPERATIONS
-- ============================================================================

-- Procedure to update plan success metrics
CREATE OR REPLACE PROCEDURE update_plan_metrics(
    p_plan_id IN VARCHAR2,
    p_success IN NUMBER,
    p_execution_time_ms IN NUMBER
) AS
BEGIN
    UPDATE troubleshooting_plans 
    SET 
        usage_count = usage_count + 1,
        total_success_count = total_success_count + p_success,
        total_failure_count = total_failure_count + (1 - p_success),
        success_rate = (total_success_count + p_success) / (usage_count + 1),
        avg_execution_time_ms = ((avg_execution_time_ms * usage_count) + p_execution_time_ms) / (usage_count + 1),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_plan_id;
    
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE;
END;
/

-- Function to get plan statistics
CREATE OR REPLACE FUNCTION get_plan_statistics
RETURN CLOB
AS
    v_stats CLOB;
BEGIN
    SELECT JSON_OBJECT(
        'total_plans' VALUE COUNT(*),
        'active_plans' VALUE SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END),
        'avg_success_rate' VALUE ROUND(AVG(success_rate), 4),
        'total_executions' VALUE SUM(usage_count),
        'most_used_goal_type' VALUE (
            SELECT goal_type 
            FROM troubleshooting_plans 
            WHERE usage_count = (SELECT MAX(usage_count) FROM troubleshooting_plans)
            AND ROWNUM = 1
        )
    ) INTO v_stats
    FROM troubleshooting_plans;
    
    RETURN v_stats;
END;
/

-- ============================================================================
-- GRANTS (Adjust as needed for your security model)
-- ============================================================================

-- Example grants - adjust based on your security requirements
-- GRANT SELECT, INSERT, UPDATE, DELETE ON troubleshooting_plans TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON plan_execution_history TO app_user;
-- GRANT SELECT ON orders TO app_user;
-- GRANT SELECT ON payments TO app_user;
-- GRANT SELECT ON shipping TO app_user;
-- GRANT SELECT ON inventory_reservations TO app_user;
-- GRANT SELECT ON customers TO app_user;
-- GRANT SELECT ON audit_log TO app_user;
-- GRANT SELECT ON error_log TO app_user;
-- GRANT SELECT ON system_health TO app_user;
-- GRANT EXECUTE ON update_plan_metrics TO app_user;
-- GRANT EXECUTE ON get_plan_statistics TO app_user;

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

PROMPT
PROMPT ===============================================
PROMPT Database schema created successfully!
PROMPT ===============================================
PROMPT
PROMPT Verification:

SELECT 'Orders' as table_name, COUNT(*) as record_count FROM orders
UNION ALL
SELECT 'Payments', COUNT(*) FROM payments
UNION ALL
SELECT 'Customers', COUNT(*) FROM customers
UNION ALL
SELECT 'Troubleshooting Plans', COUNT(*) FROM troubleshooting_plans;

PROMPT
PROMPT Sample plan statistics:
SELECT get_plan_statistics() as plan_stats FROM dual;

PROMPT
PROMPT Setup complete! You can now run your Python application.
PROMPT
