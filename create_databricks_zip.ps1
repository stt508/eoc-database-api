# Create zip file for Databricks Apps deployment
# Run this from: C:\Code\log-ai\eoc-database-api\

Write-Host "Creating Databricks Apps deployment package..." -ForegroundColor Green

# Files to include
$files = @(
    "main.py",
    "database.py",
    "models.py",
    "config.py",
    "health_check.py",
    "__init__.py",
    "requirements.txt",
    "app.yaml",
    "README.md"
)

# Create temp directory
$tempDir = ".\databricks_app_temp"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Copy files
foreach ($file in $files) {
    if (Test-Path $file) {
        Copy-Item $file $tempDir\
        Write-Host "  ✓ Copied: $file" -ForegroundColor Cyan
    } else {
        Write-Host "  ⚠ Missing: $file" -ForegroundColor Yellow
    }
}

# Create zip
$zipPath = "..\eoc-database-api-databricks.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath

# Cleanup
Remove-Item $tempDir -Recurse -Force

Write-Host ""
Write-Host "✅ Deployment package created: $zipPath" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to Databricks Workspace" -ForegroundColor White
Write-Host "2. Right-click → Import" -ForegroundColor White
Write-Host "3. Select: eoc-database-api-databricks.zip" -ForegroundColor White
Write-Host "4. Go to Apps → Create App → From Workspace" -ForegroundColor White
Write-Host ""

