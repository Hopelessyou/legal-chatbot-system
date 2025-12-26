# Temporarily enable trust mode for localhost connections
# WARNING: This is for development only! Not recommended for production.

$pgHbaPath = "C:\Program Files\PostgreSQL\18\data\pg_hba.conf"
$backupPath = "C:\Program Files\PostgreSQL\18\data\pg_hba.conf.backup"

Write-Host "Setting up trust mode for localhost connections..." -ForegroundColor Yellow
Write-Host "WARNING: This will allow passwordless connections from localhost!" -ForegroundColor Red
Write-Host ""

# Check if file exists
if (-not (Test-Path $pgHbaPath)) {
    Write-Host "ERROR: pg_hba.conf not found at $pgHbaPath" -ForegroundColor Red
    exit 1
}

# Create backup
Write-Host "Creating backup..." -ForegroundColor Yellow
Copy-Item $pgHbaPath $backupPath -Force
Write-Host "Backup created: $backupPath" -ForegroundColor Green

# Read current content
$content = Get-Content $pgHbaPath -Raw

# Check if trust mode already set
if ($content -match "host\s+all\s+all\s+127\.0\.0\.1/32\s+trust") {
    Write-Host "Trust mode is already enabled for localhost" -ForegroundColor Green
} else {
    # Add trust mode for localhost (if not exists)
    $trustLine = "`n# Trust mode for localhost (added by setup script)`nhost    all             all             127.0.0.1/32            trust`nhost    all             all             ::1/128                 trust`n"
    
    # Add before the last line or at the end
    $content = $content + $trustLine
    
    # Write back
    $content | Set-Content $pgHbaPath -Encoding ASCII
    
    Write-Host "Trust mode enabled for localhost" -ForegroundColor Green
    Write-Host "Reloading PostgreSQL configuration..." -ForegroundColor Yellow
    
    # Reload PostgreSQL config
    $psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
    & $psqlPath -U postgres -d postgres -c "SELECT pg_reload_conf();" 2>&1 | Out-Null
    
    Write-Host "Configuration reloaded!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Now you can connect without password:" -ForegroundColor Cyan
Write-Host "  psql -U postgres -d postgres" -ForegroundColor White
Write-Host ""
Write-Host "To restore original settings, run:" -ForegroundColor Yellow
Write-Host "  Copy-Item '$backupPath' '$pgHbaPath' -Force" -ForegroundColor White
Write-Host ""

