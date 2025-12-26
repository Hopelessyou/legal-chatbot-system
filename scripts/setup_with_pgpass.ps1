# Setup database using .pgpass file (no password prompts)

$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$dataDir = "C:\Program Files\PostgreSQL\18\data"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PostgreSQL Database Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .pgpass exists
$pgpassPath = "$env:USERPROFILE\.pgpass"
if (-not (Test-Path $pgpassPath)) {
    Write-Host "ERROR: .pgpass file not found!" -ForegroundColor Red
    Write-Host "Please run 'setup_pgpass.ps1' first to create the .pgpass file." -ForegroundColor Yellow
    exit 1
}

# Check PostgreSQL server
Write-Host "[1/4] Checking PostgreSQL server..." -ForegroundColor Yellow
$pgCtlPath = "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
$status = & $pgCtlPath status -D $dataDir 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  -> Starting server..." -ForegroundColor Yellow
    & $pgCtlPath start -D $dataDir -l "$dataDir\server.log" 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    Write-Host "  -> Server started" -ForegroundColor Green
} else {
    Write-Host "  -> Server is running" -ForegroundColor Green
}

# Create user
Write-Host ""
Write-Host "[2/4] Creating user 'legal_chat_bot'..." -ForegroundColor Yellow
$userCheck = & $psqlPath -U postgres -d postgres -t -c "SELECT 1 FROM pg_user WHERE usename = 'legal_chat_bot';" 2>&1
if ($userCheck -match "1") {
    Write-Host "  -> User already exists" -ForegroundColor Green
} else {
    $result = & $psqlPath -U postgres -d postgres -c "CREATE USER legal_chat_bot WITH PASSWORD '1qazxsw2';" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> User created successfully" -ForegroundColor Green
    } else {
        Write-Host "  -> Error: $result" -ForegroundColor Red
        exit 1
    }
}

# Create database
Write-Host ""
Write-Host "[3/4] Creating database 'legal_chat_info_db'..." -ForegroundColor Yellow
$dbCheck = & $psqlPath -U postgres -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname = 'legal_chat_info_db';" 2>&1
if ($dbCheck -match "1") {
    Write-Host "  -> Database already exists" -ForegroundColor Green
} else {
    $result = & $psqlPath -U postgres -d postgres -c "CREATE DATABASE legal_chat_info_db OWNER legal_chat_bot;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> Database created successfully" -ForegroundColor Green
    } else {
        Write-Host "  -> Error: $result" -ForegroundColor Red
        exit 1
    }
}

# Grant privileges
Write-Host ""
Write-Host "[4/4] Granting privileges..." -ForegroundColor Yellow
& $psqlPath -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON DATABASE legal_chat_info_db TO legal_chat_bot;" 2>&1 | Out-Null
& $psqlPath -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO legal_chat_bot;" 2>&1 | Out-Null
& $psqlPath -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO legal_chat_bot;" 2>&1 | Out-Null
Write-Host "  -> Privileges granted" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database URL:" -ForegroundColor Cyan
Write-Host "postgresql://legal_chat_bot:1qazxsw2@localhost:5432/legal_chat_info_db" -ForegroundColor White
Write-Host ""

