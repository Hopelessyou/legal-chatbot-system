# MySQL Users Check Script
# Check available MySQL users and their hosts

Write-Host "MySQL Users Check" -ForegroundColor Cyan
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
Write-Host "Try connecting without password (if MySQL allows it):" -ForegroundColor Yellow
Write-Host "  $mysqlPath -u root" -ForegroundColor White
Write-Host ""
Write-Host "Or try with different hosts:" -ForegroundColor Yellow
Write-Host "  $mysqlPath -u root -h 127.0.0.1 -p" -ForegroundColor White
Write-Host "  $mysqlPath -u root -h ::1 -p" -ForegroundColor White
Write-Host ""
Write-Host "If you can connect, run this SQL to check users:" -ForegroundColor Yellow
Write-Host "  SELECT User, Host FROM mysql.user WHERE User = 'root';" -ForegroundColor White
Write-Host ""

