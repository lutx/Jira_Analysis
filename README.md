# Jira Analysis Application

## Wymagania
- Python 3.8+
- Visual Studio Build Tools
- SQLite

## Instalacja

1. Sklonuj repozytorium:
```powershell
git clone <repo_url>
cd jira_analysis_final_version
```

2. Utwórz i aktywuj środowisko wirtualne:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Zainstaluj zależności:
```powershell
pip install -r requirements.txt
```

4. Skonfiguruj zmienne środowiskowe:
- Skopiuj `.env.example` do `.env`
- Uzupełnij wymagane wartości w `.env`

5. Zainicjalizuj bazę danych:
```powershell
.\scripts\init_db.ps1
```

## Uruchamianie

1. Aktywuj środowisko wirtualne:
```powershell
.\venv\Scripts\Activate.ps1
```

2. Uruchom aplikację:
```powershell
flask run
```

Aplikacja będzie dostępna pod adresem: http://localhost:5003

## Testy

```powershell
pytest
```

## Dokumentacja
Szczegółowe instrukcje znajdują się w pliku `komendy.md`

## Struktura Projektu
```
app/
├── __init__.py          # Application factory
├── config.py            # Configuration
├── extensions.py        # Flask extensions
├── middleware/          # Custom middleware
├── models/             # Database models
├── routes/             # Route handlers
├── services/           # Business logic
├── templates/          # Jinja2 templates
├── static/             # Static files
└── utils/              # Utility functions
```

## Komendy
```powershell
# Uruchomienie aplikacji
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
python -m flask run

# Migracje bazy danych
python -m flask db init
python -m flask db migrate -m "Migration message"
python -m flask db upgrade

# Tworzenie superadmina
python -m flask create-superadmin
```

## Dokumentacja API
API documentation is available at `/api/docs` when running in development mode.

## Licencja
MIT License 