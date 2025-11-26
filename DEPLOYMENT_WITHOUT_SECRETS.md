# 🚀 Deploy to Databricks WITHOUT Secret Permissions

**Guide for users who cannot create Databricks secrets**

---

## 🎯 **The Challenge**

You don't have permissions to create/manage Databricks secrets, but you still need to deploy the API with database credentials.

---

## ✅ **Solution: Use Direct Environment Variables**

Instead of using Databricks secrets, we'll put credentials directly in `app.yaml`.

**⚠️ Security Note:** This is less secure than secrets, but workable if:
- You don't commit `app.yaml` with credentials to Git (it's in `.gitignore`)
- You only upload directly to Databricks Workspace
- Repository is private

---

## 📋 **Step-by-Step Deployment**

### **Step 1: Create Local app.yaml with Your Credentials (2 min)**

1. **On your local machine:**
   ```powershell
   cd C:\Code\log-ai\eoc-database-api
   ```

2. **Copy the template:**
   ```powershell
   Copy-Item app.yaml.template app.yaml
   ```

3. **Edit `app.yaml`** and replace these values:
   ```yaml
   env:
     - name: DB_SERVER
       value: "your-actual-sqlserver.database.windows.net"  # ← REPLACE
     - name: DB_NAME
       value: "EOCOrderCare"  # ← REPLACE
     - name: DB_USERNAME
       value: "your-actual-username"  # ← REPLACE
     - name: DB_PASSWORD
       value: "your-actual-password"  # ← REPLACE
   ```

4. **Save the file**

✅ **Now `app.yaml` has your real credentials (NOT committed to Git)**

---

### **Step 2: Create Deployment Zip (1 min)**

**Run the deployment script:**

```powershell
cd C:\Code\log-ai\eoc-database-api
.\create_databricks_zip.ps1
```

**This creates:** `C:\Code\log-ai\eoc-database-api-databricks.zip`

**Contains:**
- ✅ All Python files
- ✅ `requirements.txt`
- ✅ `app.yaml` **WITH YOUR CREDENTIALS** ✨
- ✅ `README.md`

---

### **Step 3: Upload to Databricks Workspace (3 min)**

1. **Open Databricks workspace**
2. **Go to:** "Workspace" (left sidebar)
3. **Navigate to your user folder** (e.g., `/Users/spandan.teegalapalli@ftr.com/`)
4. **Right-click → Import**
5. **Select:** `eoc-database-api-databricks.zip`
6. **Click:** "Import"

**Databricks will extract the zip to:**
```
/Users/your-email/eoc-database-api/
├── main.py
├── database.py
├── models.py
├── config.py
├── requirements.txt
├── app.yaml  ← WITH YOUR CREDENTIALS
└── ... other files
```

---

### **Step 4: Deploy as Databricks App (5 min)**

1. **Go to:** "Apps" (left sidebar)
2. **Click:** "Create App" → "Custom App"
3. **Select:** "From Workspace"
4. **Browse to:** `/Users/your-email/eoc-database-api/`
5. **App file:** `app.yaml` (should auto-detect)
6. **Click:** "Create"

**Wait 3-5 minutes for deployment...**

✅ **Your app will deploy with the credentials from `app.yaml`!**

---

### **Step 5: Get App URL & Test**

Once deployed:

1. **Copy the app URL** (shown in Databricks Apps UI)
2. **Test health check:**
   ```
   https://your-app-url/health
   ```
3. **Should return:** `{"status": "healthy", "database": "connected"}`

---

## 🔐 **Security Considerations**

### **What's Secure:**
- ✅ `app.yaml` is NOT committed to Git (in `.gitignore`)
- ✅ Only exists in Databricks Workspace (not in GitHub)
- ✅ Repository is private
- ✅ Databricks workspace access is controlled

### **What's Less Secure:**
- ⚠️ Credentials in plain text in `app.yaml`
- ⚠️ Anyone with Databricks Workspace access can see it

### **How to Improve Later:**
- Request admin to create secrets
- Migrate to secrets when you get permissions

---

## 📋 **Workflow Diagram**

```
LOCAL MACHINE:
  1. Copy app.yaml.template → app.yaml
  2. Edit app.yaml with real credentials
  3. Run create_databricks_zip.ps1
     ↓
  Creates: eoc-database-api-databricks.zip
  (Contains app.yaml WITH credentials)
     ↓
UPLOAD TO DATABRICKS:
  4. Import zip to Workspace
  5. Extract to /Users/your-email/eoc-database-api/
     ↓
  app.yaml is now in Databricks (WITH credentials)
     ↓
DEPLOY:
  6. Apps → Create App → From Workspace
  7. Select folder with app.yaml
  8. Databricks reads credentials from app.yaml
     ↓
  ✅ App deployed with database access!
```

---

## 🔑 **Alternative: Use Databricks SQL Connection**

If your database is already configured in Databricks SQL, you can reference it:

```yaml
env:
  - name: DB_CONNECTION_NAME
    value: "my-sql-warehouse"  # Reference existing SQL warehouse
```

Then modify your code to use Databricks SQL connector instead of pyodbc.

**This works if:**
- ✅ Database is already connected in Databricks
- ✅ SQL Warehouse exists
- ❌ Requires code changes

---

## 🎯 **Recommended Approach for You:**

**Use Option 2 (Direct Environment Variables)** since:
- ✅ You don't have secret permissions
- ✅ Works immediately
- ✅ No admin approval needed
- ✅ App.yaml not committed to Git (secure enough)

---

## 📝 **Action Items:**

### **Right Now:**

1. **Edit app.yaml with your credentials:**
   ```powershell
   cd C:\Code\log-ai\eoc-database-api
   notepad app.yaml
   ```
   
   Replace:
   - `YOUR_SQL_SERVER_HERE` → Your SQL Server
   - `YOUR_DATABASE_NAME_HERE` → Database name
   - `YOUR_USERNAME_HERE` → Username
   - `YOUR_PASSWORD_HERE` → Password

2. **Create deployment zip:**
   ```powershell
   .\create_databricks_zip.ps1
   ```

3. **Upload to Databricks:**
   - Workspace → Import → Select zip

4. **Create App:**
   - Apps → Create App → Custom App → From Workspace

✅ **You can deploy without admin permissions!**

---

### **Later (When You Get Permissions):**

1. **Ask admin to create `eoc-secrets` scope**
2. **Switch app.yaml to use secrets:**
   ```yaml
   value: "${secrets/eoc-secrets/db_password}"
   ```
3. **Re-deploy**

---

## 🎯 **Summary**

| Method | Pros | Cons | Need Admin? |
|--------|------|------|-------------|
| **Databricks Secrets** | ✅ Most secure | Need permissions | ✅ Yes |
| **Environment Variables** | ✅ Works now | Less secure | ❌ No |
| **Request Admin** | ✅ Best practice | Wait time | ✅ Yes |

**Your path:** Use environment variables now, migrate to secrets later.

---

**Ready to edit `app.yaml` with your credentials and deploy?** 🚀
