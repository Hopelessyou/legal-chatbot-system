# Simple MySQL Database Creation Script
# This script creates database using the user from .env file directly

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MySQL Database Setup (Simple)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find MySQL path
$mysqlPaths = @(
    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
    "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe",
    "C:\Program Files\MySQL\MySQL Server 8.3\bin\mysql.exe"
)

$mysqlPath = $null
foreach ($path in $mysqlPaths) {
    if (Test-Path $path) {
        $mysqlPath = $path
        break
    }
}

if (-not $mysqlPath) {
    $pathDirs = $env:PATH -split ';'
    foreach ($dir in $pathDirs) {
        $testPath = Join-Path $dir "mysql.exe"
        if (Test-Path $testPath) {
            $mysqlPath = $testPath
            break
        }
    }
}

if (-not $mysqlPath) {
    Write-Host "ERROR: MySQL not found." -ForegroundColor Red
    exit 1
}

Write-Host "MySQL found: $mysqlPath" -ForegroundColor Green
Write-Host ""

# Read .env file
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $scriptDir "..\.env"

if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: .env file not found." -ForegroundColor Red
    Write-Host "Please copy env.example to .env first." -ForegroundColor Yellow
    exit 1
}

# Parse DATABASE_URL
$dbUrl = ""
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^DATABASE_URL=(.+)') {
        $dbUrl = $matches[1]
    }
}

if (-not $dbUrl) {
    Write-Host "ERROR: DATABASE_URL not found in .env file." -ForegroundColor Red
    exit 1
}

# Parse URL
if ($dbUrl -match 'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)') {
    $dbUser = $matches[1]
    $dbPassword = $matches[2]
    $dbHost = $matches[3]
    $dbPort = $matches[4]
    $dbName = $matches[5]
} else {
    Write-Host "ERROR: Invalid DATABASE_URL format." -ForegroundColor Red
    exit 1
}

Write-Host "Database: $dbName" -ForegroundColor Cyan
Write-Host "User: $dbUser" -ForegroundColor Cyan
Write-Host "Host: $dbHost" -ForegroundColor Cyan
Write-Host ""

Write-Host "This script will use the user from .env file to create the database." -ForegroundColor Yellow
Write-Host "If the user doesn't have CREATE DATABASE privilege, you need to use root." -ForegroundColor Yellow
Write-Host ""

# Get password for the user
Write-Host "Enter password for user '$dbUser':" -ForegroundColor Yellow
$userPassword = Read-Host "Password" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($userPassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

Write-Host ""
Write-Host "Creating database..." -ForegroundColor Yellow

# Try to create database with the user
$result = & $mysqlPath -u $dbUser -p$plainPassword -h $dbHost -P $dbPort -e "CREATE DATABASE IF NOT EXISTS \`$dbName\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  -> Database '$dbName' created successfully" -ForegroundColor Green
} else {
    Write-Host "  -> Error: $result" -ForegroundColor Red
    Write-Host ""
    Write-Host "The user may not have CREATE DATABASE privilege." -ForegroundColor Yellow
    Write-Host "Please use root user or grant privileges first." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Cyan
    Write-Host "1. Connect to MySQL as root:" -ForegroundColor White
    Write-Host "   $mysqlPath -u root -p" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Run these SQL commands:" -ForegroundColor White
    Write-Host "   CREATE DATABASE IF NOT EXISTS $dbName CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" -ForegroundColor Gray
    if ($dbUser -ne "root") {
        Write-Host "   CREATE USER IF NOT EXISTS '$dbUser'@'localhost' IDENTIFIED BY '$dbPassword';" -ForegroundColor Gray
        Write-Host "   GRANT ALL PRIVILEGES ON $dbName.* TO '$dbUser'@'localhost';" -ForegroundColor Gray
        Write-Host "   FLUSH PRIVILEGES;" -ForegroundColor Gray
    }
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

