# .pgpass file setup script
# This file allows psql to connect without password prompts

Write-Host "Setting up .pgpass file..." -ForegroundColor Yellow
Write-Host ""
Write-Host "This will create a .pgpass file in your home directory." -ForegroundColor Cyan
Write-Host "The file format is: hostname:port:database:username:password" -ForegroundColor Cyan
Write-Host ""

# Get postgres password
$postgresPassword = Read-Host "Enter postgres user password" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($postgresPassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# Create .pgpass file content
$pgpassContent = @"
localhost:5432:*:postgres:$plainPassword
127.0.0.1:5432:*:postgres:$plainPassword
*:5432:*:postgres:$plainPassword
"@

# Write to .pgpass file
$pgpassPath = "$env:USERPROFILE\.pgpass"
$pgpassContent | Out-File -FilePath $pgpassPath -Encoding ASCII -NoNewline

# Set file permissions (Windows doesn't have chmod, but we can set ACL)
$acl = Get-Acl $pgpassPath
$acl.SetAccessRuleProtection($true, $false)
$permission = $env:USERNAME, "Read", "Allow"
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
$acl.SetAccessRule($accessRule)
Set-Acl $pgpassPath $acl

Write-Host ""
Write-Host ".pgpass file created successfully!" -ForegroundColor Green
Write-Host "Location: $pgpassPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now you can run psql commands without password prompts." -ForegroundColor Green
Write-Host ""

