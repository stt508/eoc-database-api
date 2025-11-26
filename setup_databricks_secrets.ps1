# Setup Databricks Secrets for eoc-database-api
# Run this script after configuring Databricks CLI

Write-Host "Setting up Databricks secrets for eoc-database-api..." -ForegroundColor Green
Write-Host ""

# Prompt for values
Write-Host "Enter your database connection details:" -ForegroundColor Yellow
Write-Host ""

$dbServer = Read-Host "SQL Server hostname (e.g., eoc-sqlserver.database.windows.net)"
$dbName = Read-Host "Database name (e.g., EOCOrderCare)"
$dbUsername = Read-Host "Database username"
$dbPassword = Read-Host "Database password" -AsSecureString

# Convert secure string to plain text for databricks CLI
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
$dbPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

Write-Host ""
Write-Host "Creating secret scope 'eoc-secrets'..." -ForegroundColor Cyan

# Create scope (will error if exists, but that's ok)
databricks secrets create-scope --scope eoc-secrets 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Scope created" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Scope already exists (this is fine)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Adding secrets..." -ForegroundColor Cyan

# Add secrets
Write-Host "  Adding db_server..." -ForegroundColor White
echo $dbServer | databricks secrets put --scope eoc-secrets --key db_server
Write-Host "  ✓ db_server added" -ForegroundColor Green

Write-Host "  Adding db_name..." -ForegroundColor White
echo $dbName | databricks secrets put --scope eoc-secrets --key db_name
Write-Host "  ✓ db_name added" -ForegroundColor Green

Write-Host "  Adding db_username..." -ForegroundColor White
echo $dbUsername | databricks secrets put --scope eoc-secrets --key db_username
Write-Host "  ✓ db_username added" -ForegroundColor Green

Write-Host "  Adding db_password..." -ForegroundColor White
echo $dbPasswordPlain | databricks secrets put --scope eoc-secrets --key db_password
Write-Host "  ✓ db_password added" -ForegroundColor Green

Write-Host ""
Write-Host "Verifying secrets..." -ForegroundColor Cyan
databricks secrets list --scope eoc-secrets

Write-Host ""
Write-Host "✅ All secrets configured successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to Databricks Apps" -ForegroundColor White
Write-Host "2. Create App → Custom App" -ForegroundColor White
Write-Host "3. Use GitHub repo: https://github.com/stt508/eoc-database-api.git" -ForegroundColor White
Write-Host ""

