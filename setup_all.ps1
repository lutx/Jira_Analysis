# 1. Set environment variables
$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"
$env:PYTHONPATH = (Get-Location).Path

# 2. Remove existing files
Write-Host "Cleaning up existing files..."
Remove-Item -Path "instance/app.db" -ErrorAction SilentlyContinue
Remove-Item -Path "migrations" -Recurse -ErrorAction SilentlyContinue

# Wait a moment to ensure files are removed
Start-Sleep -Seconds 1

# 3. Create and configure instance directory
Write-Host "`nConfiguring instance directory..."
$instancePath = Join-Path (Get-Location) "instance"
New-Item -ItemType Directory -Force -Path $instancePath | Out-Null

# 4. Run Python setup script
Write-Host "`nRunning database setup..."
python setup_db.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Database setup failed!"
    exit 1
}

# 5. Initialize Flask-Migrate
Write-Host "`nInitializing Flask-Migrate..."
$env:FLASK_APP = "run.py"
flask db init
if ($LASTEXITCODE -ne 0) {
    Write-Host "Flask-Migrate initialization failed!"
    exit 1
}

# Wait a moment before continuing
Start-Sleep -Seconds 2

# 6. Create initial migration
Write-Host "`nCreating initial migration..."
flask db migrate -m "initial migration"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Migration creation failed!"
    exit 1
}

# Wait a moment before continuing
Start-Sleep -Seconds 2

# 7. Apply migration
Write-Host "`nApplying migration..."
flask db upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Host "Migration failed!"
    exit 1
}

# 8. Verify setup
Write-Host "`nVerifying setup..."
$dbPath = Join-Path $instancePath "app.db"
$dbExists = Test-Path $dbPath
$migrationsExist = Test-Path "migrations"

Write-Host "Database file exists: $dbExists"
Write-Host "Migrations directory exists: $migrationsExist"

if (-not $dbExists -or -not $migrationsExist) {
    Write-Host "Setup verification failed!"
    exit 1
}

# 9. Test database connection
Write-Host "`nTesting database connection..."
$testScript = @"
from app import create_app, db
from app.config import Config

app = create_app(Config)
with app.app_context():
    try:
        db.session.execute('SELECT 1')
        print('Database connection successful!')
    except Exception as e:
        print(f'Database connection failed: {e}')
        exit(1)
"@

python -c "$testScript"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Database connection test failed!"
    exit 1
}

Write-Host "`nSetup completed successfully!" 