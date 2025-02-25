# 1. Set environment variables
$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"
$env:PYTHONPATH = (Get-Location).Path

# 2. Clean up
Write-Host "Cleaning up existing files..."
Remove-Item -Path instance/app.db -ErrorAction SilentlyContinue
Remove-Item -Path migrations -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path instance/flask_session -Recurse -ErrorAction SilentlyContinue

# Wait for files to be removed
Start-Sleep -Seconds 1

# 3. Create required directories
$directories = @(
    "instance",
    "instance/logs",
    "instance/flask_session",
    "migrations"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Write-Host "Created directory: $dir"
}

# Create empty database file
$dbPath = "instance/app.db"
if (-not (Test-Path $dbPath)) {
    New-Item -ItemType File -Path $dbPath -Force | Out-Null
    Write-Host "Created database file: $dbPath"
}

# 4. Initialize database
Write-Host "`nInitializing database..."
try {
    Write-Host "Running flask db init..."
    flask db init
    if ($LASTEXITCODE -ne 0) { throw "Database initialization failed" }
    
    Write-Host "Running flask db migrate..."
    flask db migrate -m "initial migration"
    if ($LASTEXITCODE -ne 0) { throw "Migration creation failed" }
    
    Write-Host "Running flask db upgrade..."
    flask db upgrade
    if ($LASTEXITCODE -ne 0) { throw "Migration upgrade failed" }
    
    Write-Host "Database initialization completed successfully"
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
} 