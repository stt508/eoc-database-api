# 🚀 Databricks Deployment Guide - eoc-database-api

**Step-by-step guide to deploy eoc-database-api as a Databricks App**

---

## ✅ **Prerequisites Checklist**

Before starting, ensure you have:

- [ ] Databricks workspace access
- [ ] GitHub Personal Access Token created
- [ ] SQL Server connection details (server, database, username, password)
- [ ] Repository pushed to GitHub: https://github.com/stt508/eoc-database-api

---

## 📋 **Part 1: Setup GitHub Credential (5 minutes)**

### **Step 1.1: Create GitHub Personal Access Token**

1. Go to: https://github.com/settings/tokens
2. Click: **"Generate new token"** → **"Generate new token (classic)"**
3. Fill in:
   - **Note:** `Databricks Integration`
   - **Expiration:** 90 days (or 1 year)
   - **Select scopes:** ✅ `repo` (Full control of private repositories)
4. Click: **"Generate token"**
5. **COPY THE TOKEN** (starts with `ghp_...`) - you'll only see it once!

---

### **Step 1.2: Add GitHub Credential to Databricks**

1. Open your **Databricks workspace**
2. Click: **Profile icon** (top-right corner)
3. Select: **"User Settings"**
4. In left sidebar, click: **"Git Integration"**
5. Click: **"Add Git credential"** button
6. Fill in the form:
   - **Git provider:** Select **"GitHub"**
   - **Git provider username or email:** `stt508`
   - **Personal access token:** Paste your token from Step 1.1
7. Click: **"Save"**

✅ **Success message:** "GitHub credential saved successfully"

---

## 🔐 **Part 2: Setup Database Secrets (5 minutes)**

### **Step 2.1: Create Secret Scope**

1. In Databricks, click: **Settings icon** (⚙️ gear, usually bottom-left)
2. Select: **"Secrets"** from the menu
3. Click: **"Create Scope"** button
4. Fill in:
   - **Scope name:** `eoc-secrets`
   - **Manage Principal:** `creators` (or leave default)
5. Click: **"Create"**

✅ **You should see:** The `eoc-secrets` scope in the list

---

### **Step 2.2: Add Database Credentials as Secrets**

**Now add 4 secrets to the `eoc-secrets` scope:**

1. Click on **`eoc-secrets`** to open it
2. For each secret below, click **"Add Secret"**:

| Secret Key | Value | Example |
|------------|-------|---------|
| `db_server` | Your SQL Server hostname | `eoc-sqlserver.database.windows.net` |
| `db_name` | Database name | `EOCOrderCare` |
| `db_username` | Database username | `eoc_reader` |
| `db_password` | Database password | `your-secure-password` |

**For each secret:**
- Click: **"Add Secret"**
- **Key:** Enter the secret name (e.g., `db_server`)
- **Value:** Enter the actual value
- Click: **"Add"**

✅ **Verify:** You should see 4 secrets in the `eoc-secrets` scope

---

## 🚀 **Part 3: Deploy the App (10 minutes)**

### **Step 3.1: Navigate to Apps**

1. In Databricks left sidebar, click: **"Apps"**
2. Click: **"Create App"** button (usually blue, top-right)

---

### **Step 3.2: Choose App Type**

You should see options:
- **Custom app** ← SELECT THIS
- **Streamlit app**
- **Dash app**
- **Other options...**

**Click:** **"Custom app"** or **"Create from custom app"**

---

### **Step 3.3: Configure App Source**

**Select:** **"Git repository"** (should be the default or first option)

**Fill in the form:**

| Field | Value |
|-------|-------|
| **App name** | `eoc-database-api` |
| **Repository URL** | `https://github.com/stt508/eoc-database-api.git` |
| **Git provider** | GitHub |
| **Git credential** | Select your GitHub credential (from Part 1) |
| **Branch** | `main` |
| **Path** | Leave empty or type `/` |

---

### **Step 3.4: Configure App Settings**

Databricks should auto-detect `app.yaml`. You may see:

| Setting | Value |
|---------|-------|
| **Source file** | `app.yaml` ✅ (auto-detected) |
| **Command** | `uvicorn main:app --host 0.0.0.0 --port 8000` ✅ (from app.yaml) |

**If prompted for compute resources:**

| Setting | Recommended Value |
|---------|-------------------|
| **CPU** | 1 core |
| **Memory** | 2 GB |
| **Compute type** | Serverless (if available) |

---

### **Step 3.5: Create the App**

1. **Review all settings**
2. Click: **"Create"** or **"Deploy"** button

---

### **Step 3.6: Wait for Deployment**

You'll see a deployment status screen:

```
⏳ Starting deployment...
   ✓ Cloning repository
   ⏳ Installing dependencies (this takes 2-3 minutes)
   ⏳ Starting application
```

**Total deployment time:** 3-5 minutes

**What's happening:**
1. Databricks clones your GitHub repository
2. Installs Python dependencies from `requirements.txt`
3. Injects database secrets as environment variables
4. Starts FastAPI with uvicorn
5. Creates a public URL

---

### **Step 3.7: Get the App URL**

Once deployment succeeds, you'll see:

- **Status:** `Running` ✅ (green checkmark)
- **URL:** Something like:
  ```
  https://dbc-4ee5e339-1e79.cloud.databricks.com/serving-endpoints/eoc-database-api
  ```

**COPY THIS URL** - you'll need it for eoc-log-analyzer!

---

## 🧪 **Part 4: Test the API (2 minutes)**

### **Step 4.1: Test Health Endpoint**

1. **Copy the app URL from Step 3.7**
2. **Add `/health` to the end:**
   ```
   https://your-databricks-url/serving-endpoints/eoc-database-api/health
   ```
3. **Open in browser or use curl:**
   ```bash
   curl https://your-databricks-url/serving-endpoints/eoc-database-api/health
   ```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-11-26T..."
}
```

✅ **If you see this, the API is working!**

---

### **Step 4.2: Test Order Search**

**Try searching for an order:**

```bash
curl "https://your-databricks-url/serving-endpoints/eoc-database-api/orders/search?dpi_order_number=123456"
```

**Expected:** JSON response with order data

---

## 🔗 **Part 5: Update eoc-log-analyzer (Local)**

### **Step 5.1: Update .env File**

On your local machine:

1. **Open:** `C:\Code\log-ai\eoc-log-analyzer\.env`
2. **Update:**
   ```env
   # Replace with your Databricks App URL
   DATABASE_API_URL=https://your-databricks-url/serving-endpoints/eoc-database-api
   ```
3. **Save the file**

---

### **Step 5.2: Test Locally**

```bash
cd C:\Code\log-ai\eoc-log-analyzer
streamlit run streamlit_app.py
```

**Try analyzing an order** - it should now use the Databricks-hosted API! ✅

---

## 📊 **Deployment Summary**

| Component | Status | Details |
|-----------|--------|---------|
| **GitHub Repo** | ✅ Ready | https://github.com/stt508/eoc-database-api |
| **GitHub Credential** | ✅ Added | User Settings → Git Integration |
| **Database Secrets** | ✅ Created | `eoc-secrets` scope with 4 keys |
| **Databricks App** | ✅ Deployed | Running on Databricks Apps |
| **Public URL** | ✅ Available | Use for eoc-log-analyzer |

---

## ⚠️ **Troubleshooting**

### **Issue 1: "Repository not found"**

**Symptoms:** Error when trying to clone GitHub repo

**Solutions:**
- Verify GitHub token has `repo` scope
- Check repository URL is correct: `https://github.com/stt508/eoc-database-api.git`
- Re-enter GitHub credential in Databricks

---

### **Issue 2: "Failed to install dependencies"**

**Symptoms:** Deployment fails during package installation

**Solutions:**
- Check `requirements.txt` is valid
- Verify all package versions are compatible
- Check Databricks logs for specific error

---

### **Issue 3: "Database connection failed"**

**Symptoms:** App starts but returns database errors

**Solutions:**
- Verify secrets are correct in `eoc-secrets` scope
- Check SQL Server firewall allows Databricks IPs
- Test connection from Databricks notebook first:
  ```python
  import pyodbc
  conn = pyodbc.connect(
      f"DRIVER={{ODBC Driver 18 for SQL Server}};"
      f"SERVER={dbutils.secrets.get('eoc-secrets', 'db_server')};"
      f"DATABASE={dbutils.secrets.get('eoc-secrets', 'db_name')};"
      f"UID={dbutils.secrets.get('eoc-secrets', 'db_username')};"
      f"PWD={dbutils.secrets.get('eoc-secrets', 'db_password')};"
      f"TrustServerCertificate=yes"
  )
  ```

---

### **Issue 4: "App failed to start"**

**Symptoms:** Deployment completes but app shows error

**Solutions:**
- Check app logs in Databricks Apps UI (click on app → Logs)
- Verify `app.yaml` syntax is correct
- Check `main.py` doesn't have syntax errors
- Verify port 8000 is specified correctly

---

### **Issue 5: "Secret not found"**

**Symptoms:** Error about missing secrets

**Solutions:**
- Verify secret scope name is exactly: `eoc-secrets`
- Verify secret keys are exactly: `db_server`, `db_name`, `db_username`, `db_password`
- No spaces in scope or key names
- Grant app permission to read secrets (usually automatic)

---

## 📝 **App Configuration (app.yaml)**

The `app.yaml` file configures your app:

```yaml
name: eoc-database-api
description: FastAPI REST API for EOC Order Care database queries

command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

env:
  - name: DB_DRIVER
    value: "ODBC Driver 18 for SQL Server"
  - name: DB_SERVER
    value: "${secrets/eoc-secrets/db_server}"
  - name: DB_NAME
    value: "${secrets/eoc-secrets/db_name}"
  - name: DB_USERNAME
    value: "${secrets/eoc-secrets/db_username}"
  - name: DB_PASSWORD
    value: "${secrets/eoc-secrets/db_password}"
  - name: DB_TRUST_CERTIFICATE
    value: "yes"

resources:
  cpu: "1"
  memory: "2Gi"
```

---

## 💰 **Cost Estimate**

| Resource | Cost | Notes |
|----------|------|-------|
| **Databricks App** | ~$0.20-0.50/hour | 1 CPU, 2GB RAM |
| **24/7 operation** | ~$150-360/month | Always-on |
| **Network egress** | Minimal | API responses are small |

**Tips to reduce cost:**
- Start with 1 CPU, 2GB RAM
- Scale up only if needed
- Monitor usage in Databricks console

---

## ✅ **Success Checklist**

After deployment, verify:

- [ ] App shows "Running" status in Databricks Apps
- [ ] `/health` endpoint returns healthy status
- [ ] Can search for orders via API
- [ ] eoc-log-analyzer connects successfully
- [ ] Database queries return data

---

## 🎯 **Next Steps**

1. ✅ **eoc-database-api deployed** ← YOU ARE HERE
2. ⏭️ Deploy eoc-vector-embeddings to Databricks Repos
3. ⏭️ Test end-to-end order analysis
4. ⏭️ (Optional) Deploy eoc-log-analyzer to Streamlit Cloud

---

## 📚 **Additional Resources**

- **Databricks Apps Documentation:** https://docs.databricks.com/en/apps/index.html
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **GitHub Repository:** https://github.com/stt508/eoc-database-api

---

## 📞 **Support**

If you encounter issues:
1. Check the troubleshooting section above
2. Review app logs in Databricks Apps UI
3. Test database connection from Databricks notebook
4. Verify all secrets are correctly configured

---

**🎉 Congratulations! Your API is now deployed on Databricks!**

