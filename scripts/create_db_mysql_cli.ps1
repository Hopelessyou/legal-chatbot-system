# MySQL Database Setup Script (Using MySQL CLI)
# This script uses MySQL CLI directly to avoid password input issues

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MySQL Database Setup (CLI)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find MySQL path
$mysqlPaths = @(
    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
    "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe",
    "C:\Program Files\MySQL\MySQL Server 8.3\bin\mysql.exe",
    "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe"
)

$mysqlPath = $null
foreach ($path in $mysqlPaths) {
    if (Test-Path $path) {
        $mysqlPath = $path
        break
    }
}

# Search in PATH
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
    Write-Host "Please ensure MySQL is installed and added to PATH." -ForegroundColor Yellow
    exit 1
}

Write-Host "MySQL found: $mysqlPath" -ForegroundColor Green
Write-Host ""

# Read database info from .env file
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

# Parse URL: mysql+pymysql://user:password@host:port/database
if ($dbUrl -match 'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)') {
    $dbUser = $matches[1]
    $dbPassword = $matches[2]
    $dbHost = $matches[3]
    $dbPort = $matches[4]
    $dbName = $matches[5]
} else {
    Write-Host "ERROR: Invalid DATABASE_URL format." -ForegroundColor Red
    Write-Host "Format: mysql+pymysql://user:password@host:port/database" -ForegroundColor Yellow
    exit 1
}

Write-Host "Database: $dbName" -ForegroundColor Cyan
Write-Host "User: $dbUser" -ForegroundColor Cyan
Write-Host "Host: $dbHost" -ForegroundColor Cyan
Write-Host "Port: $dbPort" -ForegroundColor Cyan
Write-Host ""

# Get root password
Write-Host "MySQL root password is required." -ForegroundColor Yellow
$rootPassword = Read-Host "Enter MySQL root password" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($rootPassword)
$plainRootPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

Write-Host ""
Write-Host "[1/4] Checking/creating database..." -ForegroundColor Yellow

# Check if database exists and create if not
$checkDb = & $mysqlPath -u root -p$plainRootPassword -e "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '$dbName';" 2>&1

if ($checkDb -match $dbName) {
    Write-Host "  -> Database '$dbName' already exists" -ForegroundColor Green
} else {
    $result = & $mysqlPath -u root -p$plainRootPassword -e "CREATE DATABASE \`$dbName\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> Database '$dbName' created successfully" -ForegroundColor Green
    } else {
        Write-Host "  -> Error: $result" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[2/4] Checking/creating user..." -ForegroundColor Yellow

# Check if user exists
$checkUser = & $mysqlPath -u root -p$plainRootPassword -e "SELECT User FROM mysql.user WHERE User = '$dbUser' AND Host = 'localhost';" 2>&1

if ($checkUser -match $dbUser) {
    Write-Host "  -> User '$dbUser' already exists" -ForegroundColor Green
} else {
    $result = & $mysqlPath -u root -p$plainRootPassword -e "CREATE USER '$dbUser'@'localhost' IDENTIFIED BY '$dbPassword';" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> User '$dbUser' created successfully" -ForegroundColor Green
    } else {
        Write-Host "  -> Error: $result" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[3/4] Granting privileges..." -ForegroundColor Yellow

$result = & $mysqlPath -u root -p$plainRootPassword -e "GRANT ALL PRIVILEGES ON \`$dbName\`.* TO '$dbUser'@'localhost'; FLUSH PRIVILEGES;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  -> Privileges granted successfully" -ForegroundColor Green
} else {
    Write-Host "  -> Warning: $result" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[4/4] Testing connection..." -ForegroundColor Yellow

$testConn = & $mysqlPath -u $dbUser -p$dbPassword -h $dbHost -P $dbPort -e "SELECT 1;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  -> Connection successful!" -ForegroundColor Green
} else {
    Write-Host "  -> Connection failed: $testConn" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database URL:" -ForegroundColor Cyan
Write-Host "mysql+pymysql://$dbUser`:$dbPassword@$dbHost`:$dbPort/$dbName" -ForegroundColor White
Write-Host ""
