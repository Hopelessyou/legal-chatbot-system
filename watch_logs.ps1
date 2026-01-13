# LangGraph 로그 실시간 모니터링 스크립트
# 사용법: .\watch_logs.ps1

$logFile = "logs\app.log"

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "LangGraph 로그 실시간 모니터링" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "로그 파일: $logFile" -ForegroundColor Yellow
Write-Host "종료하려면 Ctrl+C를 누르세요" -ForegroundColor Yellow
Write-Host ""

# 실시간으로 로그 파일 모니터링
Get-Content $logFile -Wait -Tail 50 | Where-Object {
    $_ -match "\[DEBUG\]|체인 실행|VALIDATION.*RE_QUESTION|RE_QUESTION.*노드 실행|missing_fields|State 전이" -or
    $_ -match "sess_" -and ($_ -match "VALIDATION|RE_QUESTION|SUMMARY")
}
