# PostgreSQL 사용자 및 데이터베이스 설정 스크립트
# 이 스크립트는 legal_chat_bot 사용자를 생성하고 데이터베이스를 생성합니다.

$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$dataDir = "C:\Program Files\PostgreSQL\18\data"

# PostgreSQL 서버 시작 확인
Write-Host "PostgreSQL 서버 상태 확인 중..." -ForegroundColor Yellow
$pgCtlPath = "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
& $pgCtlPath status -D $dataDir 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PostgreSQL 서버를 시작하는 중..." -ForegroundColor Yellow
    & $pgCtlPath start -D $dataDir -l "$dataDir\server.log"
    Start-Sleep -Seconds 3
}

# 사용자 존재 여부 확인
Write-Host "`n사용자 'legal_chat_bot' 확인 중..." -ForegroundColor Yellow
$userCheck = & $psqlPath -U postgres -d postgres -t -c "SELECT 1 FROM pg_user WHERE usename = 'legal_chat_bot';" 2>&1

if ($userCheck -match "1") {
    Write-Host "사용자 'legal_chat_bot'가 이미 존재합니다." -ForegroundColor Green
} else {
    Write-Host "사용자 'legal_chat_bot' 생성 중..." -ForegroundColor Yellow
    & $psqlPath -U postgres -d postgres -c "CREATE USER legal_chat_bot WITH PASSWORD '1qazxsw2';" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "사용자 'legal_chat_bot' 생성 완료!" -ForegroundColor Green
    } else {
        Write-Host "사용자 생성 실패. 오류를 확인하세요." -ForegroundColor Red
        exit 1
    }
}

# 데이터베이스 존재 여부 확인
Write-Host "`n데이터베이스 'legal_chat_info_db' 확인 중..." -ForegroundColor Yellow
$dbCheck = & $psqlPath -U postgres -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname = 'legal_chat_info_db';" 2>&1

if ($dbCheck -match "1") {
    Write-Host "데이터베이스 'legal_chat_info_db'가 이미 존재합니다." -ForegroundColor Green
} else {
    Write-Host "데이터베이스 'legal_chat_info_db' 생성 중..." -ForegroundColor Yellow
    & $psqlPath -U postgres -d postgres -c "CREATE DATABASE legal_chat_info_db OWNER legal_chat_bot;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "데이터베이스 'legal_chat_info_db' 생성 완료!" -ForegroundColor Green
    } else {
        Write-Host "데이터베이스 생성 실패. 오류를 확인하세요." -ForegroundColor Red
        exit 1
    }
}

# 권한 부여
Write-Host "`n권한 부여 중..." -ForegroundColor Yellow
& $psqlPath -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON DATABASE legal_chat_info_db TO legal_chat_bot;" 2>&1
& $psqlPath -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO legal_chat_bot;" 2>&1
& $psqlPath -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO legal_chat_bot;" 2>&1

Write-Host "`n설정 완료!" -ForegroundColor Green
Write-Host "데이터베이스 연결 정보:" -ForegroundColor Cyan
Write-Host "  URL: postgresql://legal_chat_bot:1qazxsw2@localhost:5432/legal_chat_info_db" -ForegroundColor White

