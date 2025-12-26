# PostgreSQL Database Setup Commands
# Run these commands in PowerShell one by one
# Replace 'YOUR_POSTGRES_PASSWORD' with your actual postgres user password

# Set postgres password as environment variable
# Replace 'YOUR_POSTGRES_PASSWORD' with your actual password
$env:PGPASSWORD = 'YOUR_POSTGRES_PASSWORD'

# Navigate to PostgreSQL bin directory
cd "C:\Program Files\PostgreSQL\18\bin"

# 1. Create user (if not exists)
Write-Host "Creating user legal_chat_bot..." -ForegroundColor Yellow
.\psql.exe -U postgres -d postgres -c "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'legal_chat_bot') THEN CREATE USER legal_chat_bot WITH PASSWORD '1qazxsw2'; END IF; END `$`$;"

# 2. Create database (if not exists)
Write-Host "Creating database legal_chat_info_db..." -ForegroundColor Yellow
.\psql.exe -U postgres -d postgres -c "SELECT 'CREATE DATABASE legal_chat_info_db OWNER legal_chat_bot' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'legal_chat_info_db')\gexec"

# 3. Grant privileges
Write-Host "Granting privileges..." -ForegroundColor Yellow
.\psql.exe -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON DATABASE legal_chat_info_db TO legal_chat_bot;"
.\psql.exe -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO legal_chat_bot;"
.\psql.exe -U postgres -d legal_chat_info_db -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO legal_chat_bot;"

# Clear password from environment
$env:PGPASSWORD = $null

Write-Host "Setup complete!" -ForegroundColor Green

