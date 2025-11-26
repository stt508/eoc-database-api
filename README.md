# EOC Database API

FastAPI REST API service for querying EOC Order Care database.

## 🎯 Purpose

Provides REST endpoints for:
- Order header queries
- Order tracking information
- Order instances (cworder)
- Message logs (cwmessage)
- Health checks

## 🚀 Quick Start (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp environment_template.txt .env
# Edit .env with your database credentials

# Run
python -m uvicorn main:app --reload --port 8000
```

## 📦 Deploy to Databricks Apps

### Prerequisites

1. **Databricks workspace** with Apps feature enabled
2. **Secret scope** created with database credentials
3. **SQL Server** accessible from Databricks

### Setup Secrets

```bash
# Create secret scope
databricks secrets create-scope --scope eoc-secrets

# Add credentials
databricks secrets put --scope eoc-secrets --key db_server
databricks secrets put --scope eoc-secrets --key db_name
databricks secrets put --scope eoc-secrets --key db_username
databricks secrets put --scope eoc-secrets --key db_password
```

### Deploy via Workspace Upload

1. **Zip project:**
   ```powershell
   # From C:\Code\log-ai\
   Compress-Archive -Path eoc-database-api -DestinationPath eoc-database-api.zip
   ```

2. **Upload to Databricks:**
   - Go to **Workspace**
   - Right-click → **Import**
   - Select `eoc-database-api.zip`

3. **Create App:**
   - Go to **Apps**
   - Click **Create App**
   - Choose **From Workspace**
   - Select uploaded folder
   - Click **Create**

### Configuration

The `app.yaml` file configures:
- **Command:** `uvicorn main:app --host 0.0.0.0 --port 8000`
- **Secrets:** Database credentials from `eoc-secrets` scope
- **Resources:** 1 CPU, 2GB RAM

## 📚 API Endpoints

### Health Check
```bash
GET /health
```

### Search Orders
```bash
GET /orders/search?dpi_order_number=123456
GET /orders/search?billing_telephone=1234567890
GET /orders/search?om_order_id=OM123
```

### Get Order Tracking
```bash
GET /order-tracking/search?cworderid=12345
```

### Get Order Instance
```bash
GET /order-instances/search?cwdocid=67890
```

### Get Message Logs
```bash
GET /message-logs/search?cworderid=12345
```

## 🔧 Configuration

Environment variables (from Databricks secrets):
- `DB_SERVER`: SQL Server hostname
- `DB_NAME`: Database name
- `DB_USERNAME`: Database user
- `DB_PASSWORD`: Database password
- `DB_DRIVER`: ODBC driver (default: "ODBC Driver 18 for SQL Server")
- `DB_TRUST_CERTIFICATE`: Trust server certificate (default: "yes")

## 🐛 Troubleshooting

### Database Connection Issues

**Problem:** Can't connect to SQL Server

**Solutions:**
1. Check firewall allows Databricks IPs
2. Verify credentials in secrets
3. Check connection string format
4. Enable "Trust Server Certificate" if using self-signed cert

### App Won't Start

**Problem:** App fails to deploy

**Solutions:**
1. Check `app.yaml` syntax
2. Verify `requirements.txt` is complete
3. Check logs in Databricks Apps UI
4. Ensure secrets scope exists and has correct keys

### Missing Dependencies

**Problem:** Import errors

**Solution:**
```bash
# Regenerate requirements
pip freeze > requirements.txt
```

## 📊 Resources

- **CPU:** 1 core
- **Memory:** 2 GB
- **Cost:** ~$150-360/month (24/7 operation)

## 🔗 Integration

Used by:
- **eoc-log-analyzer**: Streamlit UI for order analysis

## 📝 License

Internal use only - Frontier Communications

## 👥 Contact

- **Owner:** stt508@ftr.com
- **GitLab:** https://gitlab.ftr.com/stt508/eoc-database-api

