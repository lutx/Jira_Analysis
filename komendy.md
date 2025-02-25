# Komendy do zarządzania aplikacją

## Inicjalizacja środowiska
```powershell
# Utwórz i aktywuj środowisko wirtualne
python -m venv venv
.\venv\Scripts\Activate.ps1

# Zainstaluj zależności
pip install -r requirements.txt
```

## Zarządzanie bazą danych
```powershell
# Inicjalizacja bazy danych
flask db init

# Tworzenie migracji
flask db migrate -m "Opis zmian"

# Aplikowanie migracji
flask db upgrade

# Reset bazy danych
.\scripts\init_db.ps1
```

## Uruchamianie aplikacji
```powershell
# Tryb deweloperski
$env:FLASK_ENV = "development"
$env:FLASK_APP = "run.py"
flask run

# Tryb produkcyjny
$env:FLASK_ENV = "production"
$env:FLASK_APP = "run.py"
flask run
```

## Testy
```powershell
# Uruchom wszystkie testy
pytest

# Uruchom testy z pokryciem kodu
pytest --cov=app tests/
```

# Reset całego środowiska
```powershell
# 1. Dezaktywuj środowisko

deactivate
# 2. Dokładne czyszczenie
Remove-Item -Force instance/app.db -ErrorAction SilentlyContinue
Remove-Item -Force app.db -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force migrations/ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force __pycache__/ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force */__pycache__/ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force **/__pycache__/ -ErrorAction SilentlyContinue

# 3. Aktywuj środowisko
.\venv\Scripts\Activate.ps1

# 4. Zainstaluj zależności
pip install -r requirements.txt

# 5. Ustaw zmienne środowiskowe
$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"

# 6. Zainicjalizuj bazę danych
flask db init
flask db migrate -m "Initial migration"
flask db upgrade


# 1. Usuń stare pliki
Remove-Item -Force instance/app.db -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force migrations/ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force __pycache__/ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force */__pycache__/ -ErrorAction SilentlyContinue

# 2. Zainicjalizuj bazę danych
python reset_and_init_db.py

# 3. Uruchom aplikację
flask run


# 1. Usuń wszystko
Remove-Item -Path instance/app.db -ErrorAction SilentlyContinue
Remove-Item -Path migrations -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path instance/flask_session -Recurse -ErrorAction SilentlyContinue

# 2. Utwórz katalogi
New-Item -ItemType Directory -Path instance -Force
New-Item -ItemType Directory -Path instance/logs -Force
New-Item -ItemType Directory -Path instance/flask_session -Force

# 3. Zainicjalizuj migracje
flask db init

# 4. Utwórz pierwszą migrację
flask db migrate -m "initial migration"

# 5. Zastosuj migrację
flask db upgrade

# 6. Utwórz superadmina
flask create-superadmin


# Usuń wszystkie pliki .pyc i __pycache__
Get-ChildItem -Path . -Recurse -Include *.pyc | Remove-Item
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse

# Usuń bazę danych i migracje
Remove-Item -Path instance/app.db -ErrorAction SilentlyContinue
Remove-Item -Path migrations -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path instance/flask_session -Recurse -ErrorAction SilentlyContinue

# Utwórz katalogi
New-Item -ItemType Directory -Path instance -Force
New-Item -ItemType Directory -Path instance/logs -Force
New-Item -ItemType Directory -Path instance/flask_session -Force
New-Item -ItemType Directory -Path migrations -Force

# Zainicjalizuj bazę danych
flask db init
flask db migrate -m "initial migration"
flask db upgrade
flask init-db
flask create-superadmin