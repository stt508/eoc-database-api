# Setup Databricks Secrets for eoc-database-api (Oracle)
# Run this script after configuring Databricks CLI

Write-Host "Setting up Databricks secrets for eoc-database-api (Oracle)..." -ForegroundColor Green
Write-Host ""

# Prompt for values
Write-Host "Enter your Oracle database connection details:" -ForegroundColor Yellow
Write-Host ""

$oracleHost = Read-Host "Oracle hostname (e.g., ocrinfwldtv01.corp.pvt)"
$oraclePort = Read-Host "Oracle port (default: 1521)"
$oracleSid = Read-Host "Oracle SID (e.g., OTEST01)"
$oracleUsername = Read-Host "Oracle username"
$oraclePassword = Read-Host "Oracle password" -AsSecureString

if ([string]::IsNullOrWhiteSpace($oraclePort)) {
    $oraclePort = "1521"
}

# Convert secure string to plain text for databricks CLI
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($oraclePassword)
$oraclePasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

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
Write-Host "Adding Oracle secrets..." -ForegroundColor Cyan

# Add Oracle secrets
Write-Host "  Adding oracle_host..." -ForegroundColor White
echo $oracleHost | databricks secrets put --scope eoc-secrets --key oracle_host
Write-Host "  ✓ oracle_host added" -ForegroundColor Green

Write-Host "  Adding oracle_port..." -ForegroundColor White
echo $oraclePort | databricks secrets put --scope eoc-secrets --key oracle_port
Write-Host "  ✓ oracle_port added" -ForegroundColor Green

Write-Host "  Adding oracle_sid..." -ForegroundColor White
echo $oracleSid | databricks secrets put --scope eoc-secrets --key oracle_sid
Write-Host "  ✓ oracle_sid added" -ForegroundColor Green

Write-Host "  Adding oracle_username..." -ForegroundColor White
echo $oracleUsername | databricks secrets put --scope eoc-secrets --key oracle_username
Write-Host "  ✓ oracle_username added" -ForegroundColor Green

Write-Host "  Adding oracle_password..." -ForegroundColor White
echo $oraclePasswordPlain | databricks secrets put --scope eoc-secrets --key oracle_password
Write-Host "  ✓ oracle_password added" -ForegroundColor Green

Write-Host ""
Write-Host "Verifying secrets..." -ForegroundColor Cyan
databricks secrets list --scope eoc-secrets

Write-Host ""
Write-Host "✅ All Oracle secrets configured successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to Databricks Apps" -ForegroundColor White
Write-Host "2. Create App → Custom App" -ForegroundColor White
Write-Host "3. Use GitHub repo: https://github.com/stt508/eoc-database-api.git" -ForegroundColor White
Write-Host ""
