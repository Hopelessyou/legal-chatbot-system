# LangGraph 로그 실시간 모니터링 스크립트 (향상된 버전)
# 사용법: .\watch_logs_enhanced.ps1

$logFile = "logs\app.log"

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "LangGraph 로그 실시간 모니터링 (향상된 버전)" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "로그 파일: $logFile" -ForegroundColor Yellow
Write-Host "종료하려면 Ctrl+C를 누르세요" -ForegroundColor Yellow
Write-Host ""

# 실시간으로 로그 파일 모니터링 (더 넓은 패턴)
Get-Content $logFile -Wait -Tail 100 | Where-Object {
    $_ -match "CRITICAL DEBUG|DEBUG|체인 실행|VALIDATION.*RE_QUESTION|RE_QUESTION.*노드 실행|missing_fields|State 전이|State 변경|노드 실행" -or
    ($_ -match "sess_" -and ($_ -match "VALIDATION|RE_QUESTION|SUMMARY|FACT_COLLECTION"))
}
