# MySQL 데이터베이스 생성 스크립트 (PowerShell)
# 이 스크립트는 root 사용자로 데이터베이스를 생성합니다

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MySQL Database Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# MySQL root 비밀번호 입력
$rootPassword = Read-Host "Enter MySQL root password" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($rootPassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# 환경 변수 설정
$env:MYSQL_ROOT_PASSWORD = $plainPassword

Write-Host ""
Write-Host "Creating database..." -ForegroundColor Yellow

# Python 스크립트 실행
python scripts/create_db.py

# 환경 변수 정리
$env:MYSQL_ROOT_PASSWORD = $null

Write-Host ""
Write-Host "Done!" -ForegroundColor Green

