# MySQL 연결 테스트 스크립트

Write-Host "MySQL 연결 테스트" -ForegroundColor Cyan
Write-Host ""

# MySQL 경로 찾기
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
        Write-Host "MySQL found at: $path" -ForegroundColor Green
        break
    }
}

# PATH에서 찾기
if (-not $mysqlPath) {
    $pathDirs = $env:PATH -split ';'
    foreach ($dir in $pathDirs) {
        $testPath = Join-Path $dir "mysql.exe"
        if (Test-Path $testPath) {
            $mysqlPath = $testPath
            Write-Host "MySQL found in PATH: $testPath" -ForegroundColor Green
            break
        }
    }
}

if (-not $mysqlPath) {
    Write-Host "MySQL을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "MySQL이 설치되어 있고 PATH에 추가되어 있는지 확인하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "MySQL에 연결을 시도합니다..." -ForegroundColor Yellow
Write-Host ""

# root 비밀번호 입력
$rootPassword = Read-Host "Enter MySQL root password" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($rootPassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# 연결 테스트
Write-Host ""
Write-Host "Testing connection..." -ForegroundColor Yellow
$result = & $mysqlPath -u root -p$plainPassword -e "SELECT VERSION();" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "연결 성공!" -ForegroundColor Green
    Write-Host $result
} else {
    Write-Host "연결 실패!" -ForegroundColor Red
    Write-Host $result
    Write-Host ""
    Write-Host "가능한 원인:" -ForegroundColor Yellow
    Write-Host "1. 비밀번호가 잘못되었습니다" -ForegroundColor White
    Write-Host "2. MySQL 서버가 실행되지 않았습니다" -ForegroundColor White
    Write-Host "3. root 사용자가 다른 호스트에서만 접속 가능하도록 설정되었습니다" -ForegroundColor White
    Write-Host ""
    Write-Host "해결 방법:" -ForegroundColor Yellow
    Write-Host "1. MySQL 서비스 시작: net start MySQL80" -ForegroundColor White
    Write-Host "2. MySQL Workbench 또는 다른 도구로 root 비밀번호 확인" -ForegroundColor White
    Write-Host "3. 다른 사용자로 시도 (예: 관리자 계정)" -ForegroundColor White
}

