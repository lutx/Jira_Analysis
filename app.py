from flask import Flask, render_template, jsonify, request, send_from_directory, make_response, send_file
import sqlite3
import os
from dotenv import load_dotenv  # Poprawiony import
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for
from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError
from jira import JIRA
from flask_apscheduler import APScheduler
import csv
from io import StringIO, BytesIO
import pandas as pd
from werkzeug.utils import secure_filename
import bcrypt
import shutil
import gzip
import random
import string
import uuid
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from werkzeug.exceptions import NotFound
from flask_cors import CORS
import json
from werkzeug.security import generate_password_hash
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

# Na początku pliku dodaj konfigurację logowania
import logging
logging.basicConfig(level=logging.DEBUG)

def verify_token(token):
    """Weryfikuje JWT token"""
    try:
        app.logger.debug(f"Weryfikacja tokena: {token[:20]}...")
        data = decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        app.logger.debug(f"Token zweryfikowany pomyślnie: {data}")
        return data
    except ExpiredSignatureError:
        app.logger.warning("Token wygasł")
        return None
    except InvalidTokenError as e:
        app.logger.warning(f"Nieprawidłowy token: {str(e)}")
        return None
    except Exception as e:
        app.logger.error(f"Błąd weryfikacji tokena: {str(e)}")
        return None

# Załaduj zmienne środowiskowe z pliku .env
load_dotenv()

def auth_required(roles=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.cookies.get('token')
            
            if not token:
                if request.is_json:
                    return jsonify({"error": "No token provided"}), 401
                return redirect(url_for('login'))
            
            user_data = verify_token(token)
            if not user_data:
                if request.is_json:
                    return jsonify({"error": "Invalid token"}), 401
                return redirect(url_for('login'))
            
            if roles and user_data.get('role') not in roles:
                return jsonify({"error": "Unauthorized"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Po inicjalizacji app i CORS, przed DB_NAME
app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static'
)

# Konfiguracja aplikacji
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx'}
app.config['BACKUP_DIR'] = 'backups'

# Inicjalizacja CORS
CORS(app)

def get_jira_client():
    try:
        jira_url = os.environ.get('JIRA_URL')
        jira_user = os.environ.get('JIRA_USER')
        jira_password = os.environ.get('JIRA_PASSWORD')
        
        if not all([jira_url, jira_user, jira_password]):
            app.logger.error("Brak wymaganych danych dostępowych do Jiry")
            return None
            
        options = {
            'server': jira_url,
            'verify': False  # Tylko dla środowiska dev/test
        }
        
        jira = JIRA(
            options=options,
            basic_auth=(jira_user, jira_password)
        )
        
        app.logger.info("Połączono z Jirą pomyślnie")
        return jira
        
    except Exception as e:
        app.logger.error(f"Błąd podczas łączenia z Jirą: {str(e)}")
        return None

# Definicja DB_NAME
DB_NAME = "data/worklogs.db"

# Definicja klasy User
class User:
    def __init__(self, id, user_name, role):
        self.id = id
        self.user_name = user_name
        self.role = role
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

# Inicjalizacja Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_name, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return User(user[0], user[1], user[2])
        return None
    except Exception as e:
        app.logger.error(f"Error loading user: {str(e)}")
        return None

def init_db():
    try:
        # Upewnij się, że katalog data istnieje
        os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Tworzenie tabel z indeksami
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_users_user_name ON users(user_name);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

        CREATE TABLE IF NOT EXISTS worklogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            project TEXT NOT NULL,
            task_key TEXT NOT NULL,
            time_logged INTEGER NOT NULL,
                date DATE NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_name) REFERENCES users (user_name)
            );

            CREATE INDEX IF NOT EXISTS idx_worklogs_user_date 
            ON worklogs (user_name, date);
            
            CREATE INDEX IF NOT EXISTS idx_worklogs_project 
            ON worklogs (project);
            
            -- Dodaj tabelę app_settings
            CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Dodaj tabelę jira_users
            CREATE TABLE IF NOT EXISTS jira_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT UNIQUE,
            user_name TEXT NOT NULL UNIQUE,
                display_name TEXT,
                email TEXT,
                is_active BOOLEAN DEFAULT 1,
                last_sync DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_jira_users_account_id ON jira_users(account_id);
            CREATE INDEX IF NOT EXISTS idx_jira_users_user_name ON jira_users(user_name);
            
            -- Dodaj tabelę jira_sync_history
            CREATE TABLE IF NOT EXISTS jira_sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,
                status TEXT NOT NULL,
                items_processed INTEGER DEFAULT 0,
                error_message TEXT,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            );
            
            -- Dodaj tabelę change_history
            CREATE TABLE IF NOT EXISTS change_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
                change_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_name) REFERENCES users (user_name),
                FOREIGN KEY (changed_by) REFERENCES users (user_name)
            );
        """)

        # Dodaj podstawowe ustawienia aplikacji
        cursor.executescript("""
            INSERT OR IGNORE INTO app_settings (key, value) VALUES 
            ('jira_sync_interval', '3600'),
            ('default_user_role', 'user'),
            ('auto_activate_users', 'true'),
            ('log_retention_days', '30');
        """)

        # Dodaj domyślnego superadmina jeśli nie istnieje
        default_password = "admin123"  # Zmień na bezpieczniejsze hasło
        hashed_password = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())
        
        cursor.execute("""
            INSERT OR IGNORE INTO users (
                user_name, 
                email, 
                password_hash, 
                role, 
                is_active
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            'luszynski@lbpro.pl',
            'luszynski@lbpro.pl',
            hashed_password,
            'superadmin',
            1
        ))

        conn.commit()
        conn.close()
        app.logger.info("Database initialized successfully with default superadmin")
        
    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}")
        raise

def configure_logging():
    logging.basicConfig(level=logging.DEBUG)  # Zmienione na DEBUG dla więcej szczegółów
    app.logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    default_handler.setFormatter(formatter)
    
    # Dodanie logowania do pliku
    file_handler = logging.FileHandler('app.log')
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    # Dodanie logowania do konsoli
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

@app.route('/')
@login_required
def dashboard():
    app.logger.info("Accessing dashboard route")
    try:
        return render_template("dashboard.html")  # Dodano wcięcie
    except Exception as e:
        app.logger.error(f"Error rendering dashboard: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/get_worklogs')
@auth_required()
def get_worklogs():
    try:
        conn = sqlite3.connect(DB_NAME)  # Dodano wcięcie
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                w.user_name,
                w.project,
                w.task_key,
                w.time_logged,
                w.date,
                w.description,
                i.summary as task_summary
            FROM worklogs w
            LEFT JOIN jira_issues i ON w.task_key = i.issue_key
            ORDER BY w.date DESC
        """)
        
        worklogs = [{
            'user_name': row[0],
            'project': row[1],
            'task_key': row[2],
            'time_logged': row[3],
            'date': row[4],
            'description': row[5],
            'task_summary': row[6]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(worklogs)
    except Exception as e:
        app.logger.error(f"Error getting worklogs: {str(e)}")
        return jsonify({'error': str(e)}), 500

def create_required_directories():
    """Create required directories if they don't exist"""
    directories = ['data', 'static', 'templates']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

@app.route('/get_active_users_trend')
@login_required
def get_active_users_trend():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            WITH RECURSIVE dates(date) AS (
                SELECT date('now', '-30 days')
                UNION ALL
                SELECT date(date, '+1 day')
                FROM dates
                WHERE date < date('now')
            ),
            daily_users AS (
                SELECT 
                    date(date) as log_date,
                    COUNT(DISTINCT user_name) as user_count
                FROM worklogs
                WHERE date >= date('now', '-30 days')
                GROUP BY date(date)
            )
            SELECT 
                dates.date,
                COALESCE(daily_users.user_count, 0) as active_users
            FROM dates
            LEFT JOIN daily_users ON dates.date = daily_users.log_date
            ORDER BY dates.date
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'dates': [row[0] for row in results],
            'counts': [row[1] for row in results]
        })
        
    except Exception as e:
        app.logger.error(f"Error in get_active_users_trend: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/assign_user_to_portfolio', methods=['POST'])
def assign_user_to_portfolio():
    data = request.json
    user_name = data.get("user_name")
    portfolio_id = data.get("portfolio_id")
    month = data.get("month")
    assigned_hours = data.get("assigned_hours", 0)

    if not user_name or not portfolio_id or not month:
        return jsonify({"error": "Brak wymaganych danych"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO project_assignments (user_name, project, month, assigned_hours) 
        VALUES (?, ?, ?, ?) 
    """, (user_name, portfolio_id, month, assigned_hours))
    conn.commit()
    conn.close()

    return jsonify({"message": "Przypisanie zapisane"}), 200

@app.route('/update_user_role', methods=['POST'])
def update_user_role():
    data = request.json
    user_name = data.get("user_name")
    new_role = data.get("new_role")

    if not user_name or not new_role:
        return jsonify({"error": "Brak wymaganych danych"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE user_name = ?", (new_role, user_name))
    conn.commit()
    conn.close()

    return jsonify({"message": f"Rola użytkownika {user_name} zmieniona na {new_role}"}), 200

@app.errorhandler(404)
def not_found_error(error):
    if request.is_json:
        return jsonify({"error": "Not found"}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    if request.is_json:
        return jsonify({"error": "Internal server error"}), 500
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Wystąpił błąd serwera"), 500

@app.errorhandler(403)
def forbidden_error(error):
    if request.is_json:
        return jsonify({"error": "Forbidden"}), 403
    return render_template('error.html', 
                         error_code=403, 
                         error_message="Brak dostępu"), 403

@app.errorhandler(405)
def method_not_allowed_error(error):
    return jsonify({
        "error": "Metoda nie jest dozwolona",
        "allowed_methods": error.valid_methods
    }), 405

# Dodaj przykładowe dane do bazy, jeśli jest pusta
def add_sample_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy są jakieś dane
        cursor.execute("SELECT COUNT(*) FROM worklogs")
        count = cursor.fetchone()[0]
        
        if count == 0:
            import_sample_data_from_csv()
            app.logger.info("Added sample data from CSV")
        
        conn.close()
    except Exception as e:
        app.logger.error(f"Error adding sample data: {str(e)}")

@app.route('/worklogs')
def worklogs():
    return render_template("worklogs.html")

@app.route('/users')
def users():
    return render_template("users.html")

@app.route('/portfolios')
def portfolios():
    return render_template("portfolios.html")

@app.route('/settings/<path>')
def settings(path):
    try:
        valid_paths = ['general', 'users', 'import']
        if path not in valid_paths:
            app.logger.warning(f"Attempted to access invalid settings path: {path}")
            return render_template('errors/404.html'), 404
        return render_template(f"settings/{path}.html")
    except Exception as e:
        app.logger.error(f"Error rendering settings page {path}: {str(e)}")
        return render_template('errors/500.html'), 500

# Funkcje pomocnicze do autentykacji
def generate_token(data):
    try:
        return encode(
            {
                **data,
                'exp': datetime.utcnow() + timedelta(days=1)  # Token ważny 1 dzień
            },
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    except Exception as e:
        app.logger.error(f"Błąd generowania tokena: {str(e)}")
        raise

# Endpointy do logowania
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'GET':
            app.logger.debug("Wyświetlanie strony logowania")
            return render_template('login.html')

        app.logger.debug("Próba logowania")
        data = request.get_json()
        user_name = data.get('user_name')
        password = data.get('password')

        app.logger.debug(f"Próba logowania użytkownika: {user_name}")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash, role FROM users WHERE user_name = ?", (user_name,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[1]):
            # Utwórz obiekt User
            user = User(user_data[0], user_name, user_data[2])
            login_user(user)  # Zaloguj użytkownika przez Flask-Login
            
            # Wygeneruj token JWT
            token = generate_token({
                'user_name': user_name,
                'role': user_data[2]
            })
            
            response = jsonify({'success': True, 'role': user_data[2]})
            response.set_cookie('token', token, httponly=True, secure=True)
            return response
        else:
            return jsonify({'success': False, 'error': 'Nieprawidłowy login lub hasło'}), 401

    except Exception as e:
        app.logger.error(f"Błąd podczas logowania: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout')
@login_required
def logout():
    try:
        logout_user()  # Wyloguj użytkownika przez Flask-Login
        response = make_response(redirect(url_for('login')))
        response.delete_cookie('token')
        return response
    except Exception as e:
        app.logger.error(f"Błąd podczas wylogowywania: {str(e)}")
        return redirect(url_for('login'))

# Dodaj funkcję dla nieautoryzowanych użytkowników
@login_manager.unauthorized_handler
def unauthorized():
    if request.is_json:
        return jsonify({"error": "Unauthorized"}), 401
    return redirect(url_for('login'))

# Zabezpiecz istniejące endpointy
@app.route('/api/admin/roles', methods=['POST'])
@auth_required(roles=['superadmin'])
def update_user_roles():
    if session.get('user_name') != 'luszynski@lbpro.pl':
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    user_name = data.get('user_name')
    new_role = data.get('role')
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Zapisz zmianę w historii
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, old_value, new_value, changed_by)
            VALUES (?, 'role_change', ?, ?, ?)
        """, (user_name, data.get('old_role'), new_role, session['user_name']))
        
        # Zaktualizuj rolę
        cursor.execute("UPDATE users SET role = ? WHERE user_name = ?", (new_role, user_name))
        
        conn.commit()
        return jsonify({"message": "Role updated successfully"})
    except Exception as e:  # Dodano brakujący blok except
        app.logger.error(f"Error updating role: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/reports/activity', methods=['GET'])
@auth_required(roles=['admin', 'superadmin', 'PM'])
def get_activity_report():
    report_type = request.args.get('type', 'daily')  # daily, weekly, monthly
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if report_type == 'daily':
            query = """
                SELECT user_name, date, SUM(time_logged) as total_hours
        FROM worklogs
                GROUP BY user_name, date
        ORDER BY date DESC
            """
        elif report_type == 'weekly':
            query = """
                SELECT user_name, 
                       strftime('%Y-%W', date) as week,
                       SUM(time_logged) as total_hours
                FROM worklogs
                GROUP BY user_name, week
                ORDER BY week DESC
            """
        else:  # monthly
            query = """
                SELECT user_name, 
                       strftime('%Y-%m', date) as month,
                       SUM(time_logged) as total_hours
                FROM worklogs
                GROUP BY user_name, month
                ORDER BY month DESC
            """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if report_type == 'daily':
            data = [{"user_name": row[0], "period": row[1], "hours": row[2]} for row in results]
        elif report_type == 'weekly':
            data = [{"user_name": row[0], "period": f"Week {row[1]}", "hours": row[2]} for row in results]
        else:
            data = [{"user_name": row[0], "period": row[1], "hours": row[2]} for row in results]
            
        conn.close()
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error generating activity report: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/reports/shadow-work', methods=['GET'])
@auth_required(roles=['admin', 'superadmin', 'PM'])
def get_shadow_work_report():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        query = """
            SELECT w.user_name, w.project, w.date, w.time_logged
            FROM worklogs w
            LEFT JOIN project_assignments pa 
            ON w.user_name = pa.user_name 
            AND w.project = pa.project
            WHERE pa.id IS NULL
        """
        cursor.execute(query)
        results = cursor.fetchall()
        data = [{
            "user_name": row[0],
            "project": row[1],
            "date": row[2],
            "time_logged": row[3]
        } for row in results]
        conn.close()
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error generating shadow work report: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/auth/status')
def auth_status():
    token = request.cookies.get('token')
    if not token:
        return jsonify({
            "authenticated": False,
            "message": "No token found"
        })
    
    user_data = verify_token(token)
    if not user_data:
        return jsonify({
            "authenticated": False,
            "message": "Invalid or expired token"
        })
    
    return jsonify({
        "authenticated": True,
        "user": {
            "user_name": user_data['user_name'],
            "role": user_data['role']
        }
    })

def setup_jira_client():
    try:
        jira_url = os.getenv('JIRA_URL', 'https://jira-test.lbpro.pl')
        jira_user = os.getenv('JIRA_USER')
        jira_password = os.getenv('JIRA_PASSWORD')
        
        app.logger.info(f"Próba połączenia z Jirą: {jira_url}")
        
        if not all([jira_url, jira_user, jira_password]):
            missing = []
            if not jira_url: missing.append('JIRA_URL')
            if not jira_user: missing.append('JIRA_USER')
            if not jira_password: missing.append('JIRA_PASSWORD')
            error_msg = f"Brak wymaganych zmiennych środowiskowych: {', '.join(missing)}"
            app.logger.error(error_msg)
            raise Exception(error_msg)

        # Konfiguracja sesji z retries
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Konfiguracja autoryzacji i nagłówków
        session.auth = (jira_user, jira_password)
        session.verify = False
        session.headers.update({
            'Host': 'jira-test.lbpro.pl',
            'X-Forwarded-For': '82.139.184.226',
            'X-Real-IP': '82.139.184.226',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Test połączenia
        response = session.get(
            f"{jira_url}/rest/api/2/myself",
            timeout=30
        )
        
        if not response.ok:
            raise Exception(f"Błąd połączenia: {response.status_code} - {response.text}")
            
        myself = response.json()
        app.logger.info(f"Połączono z Jirą jako: {myself['displayName']} ({myself['emailAddress']})")
        
        return session
        
    except Exception as e:
        app.logger.error(f"Błąd podczas tworzenia klienta Jira: {str(e)}")
        raise

def sync_jira_worklogs():
    try:
        jira = setup_jira_client()
        # Pobierz worklogi z ostatnich 7 dni
        jql = 'worklogDate >= -7d'
        issues = jira.search_issues(jql, maxResults=1000)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        for issue in issues:
            worklogs = jira.worklogs(issue.id)
            for worklog in worklogs:
                cursor.execute("""
                    INSERT OR REPLACE INTO worklogs 
                    (user_name, project, task_key, time_logged, date, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    worklog.author.name,
                    issue.fields.project.key,
                    issue.key,
                    worklog.timeSpentSeconds / 3600,  # konwersja na godziny
                    worklog.started[:10],  # tylko data
                    worklog.comment
                ))
        
        conn.commit()
        conn.close()
        app.logger.info("Jira sync completed successfully")
    except Exception as e:
        app.logger.error(f"Jira sync error: {str(e)}")

scheduler = APScheduler()

def init_scheduler():
    scheduler.init_app(app)
    scheduler.start()
    
    # Synchronizuj dane z Jirą co godzinę
    scheduler.add_job(
        id='jira_sync',
        func=sync_jira_worklogs,
        trigger='interval',
        hours=1
    )
    
    # Dodaj automatyczny backup co 24h
    scheduler.add_job(
        id='daily_backup',
        func=lambda: create_backup(),
        trigger='interval',
        hours=24
    )

@app.route('/api/reports/export/<report_type>/<format>')
@auth_required(roles=['admin', 'superadmin', 'PM'])
def export_report(report_type, format):
    try:
        # Pobierz dane raportu
        if report_type == 'activity':
            data = get_activity_report().json
        elif report_type == 'shadow-work':
            data = get_shadow_work_report().json
        else:
            return jsonify({"error": "Invalid report type"}), 400

        if format == 'csv':
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={report_type}.csv'
            return response
            
        elif format == 'pdf':
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            
            # Konwertuj dane do formatu tabeli
            table_data = [[k for k in data[0].keys()]]
            for row in data:
                table_data.append([str(v) for v in row.values()])
            
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(t)
            doc.build(elements)
            
            response = make_response(buffer.getvalue())
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename={report_type}.pdf'
            return response
            
        return jsonify({"error": "Invalid format"}), 400
    except Exception as e:
        app.logger.error(f"Export error: {str(e)}")
        return jsonify({"error": "Export failed"}), 500

@app.route('/api/reports/heatmap')
@auth_required()
def get_activity_heatmap():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Pobierz dane dla heatmapy (godziny pracy w ciągu dnia)
        cursor.execute("""
            SELECT 
                strftime('%H', time_logged) as hour,
                strftime('%w', date) as day_of_week,
                COUNT(*) as count
            FROM worklogs
            WHERE date >= date('now', '-30 days')
            GROUP BY hour, day_of_week
            ORDER BY day_of_week, hour
        """)
        
        results = cursor.fetchall()
        heatmap_data = {
            'hours': list(range(24)),
            'days': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
            'data': [[0] * 24 for _ in range(7)]
        }
        
        for hour, day, count in results:
            heatmap_data['data'][int(day)][int(hour)] = count
            
        return jsonify(heatmap_data)
    except Exception as e:
        app.logger.error(f"Heatmap generation error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/workload-analysis')
@auth_required(roles=['admin', 'superadmin', 'PM'])
def get_workload_analysis():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy tabele istnieją
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name IN ('worklogs', 'user_allocations')
        """)
        existing_tables = {row[0] for row in cursor.fetchall()}
        required_tables = {'worklogs', 'user_allocations'}
        
        if not required_tables.issubset(existing_tables):
            missing_tables = required_tables - existing_tables
            raise Exception(f"Missing required tables: {missing_tables}")

        query = """
            WITH actual_hours AS (
                SELECT 
                    user_name,
                    strftime('%Y-%m', date) as month,
                    SUM(time_logged) / 3600.0 as actual_hours
                FROM worklogs
                GROUP BY user_name, month
            ),
            planned_hours AS (
                SELECT 
                    user_name,
                    month,
                    SUM(planned_hours) as planned_hours
                FROM user_allocations
                GROUP BY user_name, month
            )
            SELECT 
                a.user_name,
                a.month,
                a.actual_hours,
                COALESCE(p.planned_hours, 0) as planned_hours,
                CASE 
                    WHEN p.planned_hours > 0 
                    THEN (a.actual_hours - p.planned_hours) * 100.0 / p.planned_hours 
                    ELSE 0 
                END as overload_percentage
            FROM actual_hours a
            LEFT JOIN planned_hours p 
                ON a.user_name = p.user_name 
                AND a.month = p.month
            ORDER BY a.month DESC, overload_percentage DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        data = [{
            "user_name": row[0],
            "month": row[1],
            "actual_hours": float(row[2]),
            "planned_hours": float(row[3]),
            "overload_percentage": round(float(row[4]), 2)
        } for row in results]
        
        return jsonify(data)  # Popraw wcięcie
    except Exception as e:
        app.logger.error(f"Error in workload analysis: {str(e)}")
        if conn:
            conn.close()
        return jsonify({
            "error": "Internal Server Error",
            "details": str(e) if app.debug else None
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/alerts/missing-worklogs')
@auth_required(roles=['admin', 'superadmin', 'PM'])
def get_missing_worklogs_alerts():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź brakujące worklogi dla dni roboczych
        query = """
            WITH RECURSIVE dates(date) AS (
                SELECT date('now', '-30 days')
                UNION ALL
                SELECT date(date, '+1 day')
                FROM dates
                WHERE date < date('now', '-1 day')
            ),
            working_days AS (
                SELECT date 
                FROM dates 
                WHERE strftime('%w', date) NOT IN ('0', '6')
            ),
            user_days AS (
                SELECT DISTINCT 
                    u.user_name,
                    w.date
                FROM users u
                CROSS JOIN working_days w
                LEFT JOIN user_availability ua 
                    ON u.user_name = ua.user_name 
                    AND w.date = ua.date
                WHERE ua.is_available IS NULL OR ua.is_available = 1
            ),
            logged_days AS (
                SELECT DISTINCT 
                    user_name,
                    date
                FROM worklogs
            )
            SELECT 
                ud.user_name,
                ud.date
            FROM user_days ud
            LEFT JOIN logged_days ld 
                ON ud.user_name = ld.user_name 
                AND ud.date = ld.date
            WHERE ld.user_name IS NULL
            ORDER BY ud.date DESC, ud.user_name
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        alerts = [{
            "user_name": row[0],
            "date": row[1],
            "message": f"Brak worklogów dla {row[0]} w dniu {row[1]}"
        } for row in results]
        
        conn.close()
        return jsonify(alerts)
    except Exception as e:
        app.logger.error(f"Missing worklogs alerts error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

def import_sample_data_from_csv(filename='sample_worklogs.csv'):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        with open(filename, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            # Najpierw dodaj użytkowników
            for row in csv_reader:
                cursor.execute("""
                    INSERT OR IGNORE INTO users (user_name, role, email)
                    VALUES (?, ?, ?)
                """, (
                    row['user_name'],
                    row['role'],
                    f"{row['user_name']}@example.com"
                ))
            
            # Przewiń plik na początek
            file.seek(0)
            next(csv_reader)  # Pomiń nagłówek
            
            # Teraz dodaj worklogi
            for row in csv_reader:
                cursor.execute("""
                    INSERT INTO worklogs (user_name, project, task_key, time_logged, date, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row['user_name'],
                    row['project'],
                    f"{row['project']}-{row['task']}",
                    float(row['hours']),
                    row['date'],
                    row['description']
                ))
        
        conn.commit()
        conn.close()
        app.logger.info("Sample data imported successfully")
    except Exception as e:
        app.logger.error(f"Error importing sample data: {str(e)}")
        raise

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/import/data', methods=['POST'])
@auth_required(roles=['admin', 'superadmin'])
def import_data():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Brak pliku"}), 400
            
        file = request.files['file']
        import_type = request.form.get('type')
        
        if not file or not file.filename:
            return jsonify({"error": "Nie wybrano pliku"}), 400
            
        if not allowed_file(file.filename):
            return jsonify({"error": "Niedozwolony typ pliku"}), 400

        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            # Wczytaj dane z pliku
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:  # xlsx
                df = pd.read_excel(filepath)

            # Walidacja podstawowej struktury
            required_columns = {
                'worklogs': ['user_name', 'project', 'task', 'hours', 'date', 'description'],
                'users': ['user_name', 'role', 'email'],
                'portfolios': ['name']
            }

            if import_type not in required_columns:
                raise ValueError("Nieprawidłowy typ importu")

            missing_columns = set(required_columns[import_type]) - set(df.columns)
            if missing_columns:
                raise ValueError(f"Brakujące kolumny: {', '.join(missing_columns)}")

            # Walidacja danych
            if import_type == 'worklogs':
                df['hours'] = pd.to_numeric(df['hours'], errors='coerce')
                if df['hours'].isna().any():
                    raise ValueError("Nieprawidłowe wartości w kolumnie 'hours'")
                if (df['hours'] <= 0).any():
                    raise ValueError("Godziny muszą być większe od 0")

            # Import do bazy danych
            conn = sqlite3.connect(DB_NAME)
            if import_type == 'worklogs':
                df.to_sql('worklogs_temp', conn, if_exists='replace', index=False)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO worklogs (user_name, project, task_key, time_logged, date, description)
                    SELECT user_name, project, task, hours, date, description
                    FROM worklogs_temp
                """)
            elif import_type == 'users':
                df.to_sql('users', conn, if_exists='append', index=False)
            elif import_type == 'portfolios':
                df.to_sql('portfolios', conn, if_exists='append', index=False)

            conn.commit()
            conn.close()

            return jsonify({
                "message": f"Zaimportowano {len(df)} rekordów",
                "type": import_type
            })

        finally:
            # Usuń plik po przetworzeniu
            if os.path.exists(filepath):
                os.remove(filepath)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Import error: {str(e)}")
        return jsonify({"error": "Błąd podczas importu danych"}), 500

@app.route('/api/change-password', methods=['POST'])
@auth_required()
def change_password():
    try:
        data = request.json
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({"error": "Brak wymaganych danych"}), 400
            
        if len(new_password) < 8:
            return jsonify({"error": "Nowe hasło musi mieć co najmniej 8 znaków"}), 400
            
        token = request.cookies.get('token')
        user_data = verify_token(token)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE user_name = ?", (user_data['user_name'],))
        current_hash = cursor.fetchone()[0]
        
        if not bcrypt.checkpw(old_password.encode('utf-8'), current_hash):
            return jsonify({"error": "Nieprawidłowe obecne hasło"}), 401
            
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("UPDATE users SET password_hash = ? WHERE user_name = ?", 
                      (new_hash, user_data['user_name']))
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Hasło zostało zmienione"})
    except Exception as e:
        app.logger.error(f"Password change error: {str(e)}")
        return jsonify({"error": "Błąd podczas zmiany hasła"}), 500

@app.route('/admin/dashboard')
@auth_required(roles=['admin', 'superadmin'])
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/users')
@auth_required(roles=['admin', 'superadmin'])
def admin_users():
    return render_template('admin/users.html')

@app.route('/admin/portfolios')
@auth_required(roles=['admin', 'superadmin'])
def admin_portfolios():
    return render_template('admin/portfolios.html')

@app.route('/admin/settings')
@auth_required(roles=['superadmin'])
def admin_settings():
    return render_template('admin/settings.html')

@app.route('/api/admin/dashboard/stats')
@auth_required(roles=['superadmin'])
def get_dashboard_stats():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Liczba użytkowników
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        
        # Liczba worklogów dziś
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM worklogs WHERE date(timestamp) = ?", (today,))
        worklogs_count = cursor.fetchone()[0]
        
        # Liczba błędów w ostatnich 24h
        with open('app.log', 'r') as f:
            errors_count = sum(1 for line in f if 'ERROR' in line and 
                             datetime.now() - datetime.strptime(line.split('[')[1].split(']')[0], 
                             '%Y-%m-%d %H:%M:%S,%f') < timedelta(days=1))
        
        # Rozmiar bazy danych
        db_size = os.path.getsize(DB_NAME)
        
        return jsonify({
            'users_count': users_count,
            'worklogs_count': worklogs_count,
            'errors_count': errors_count,
            'db_size': db_size
        })
        
    except Exception as e:
        app.logger.error(f"Error getting dashboard stats: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania statystyk"}), 500

@app.route('/api/admin/users', methods=['GET'])
@auth_required(roles=['superadmin'])
def get_admin_users():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_name, email, role, is_active, last_login
            FROM users
            ORDER BY user_name
        """)
        
        users = [{
            'id': row[0],
            'user_name': row[1],
            'email': row[2],
            'role': row[3],
            'is_active': bool(row[4]),
            'last_login': row[5]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(users)
        
    except Exception as e:
        app.logger.error(f"Error getting users: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania użytkowników"}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['GET'])
@auth_required(roles=['superadmin'])
def get_user(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_name, email, role, is_active
            FROM users
            WHERE id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        user = {
            'id': row[0],
            'user_name': row[1],
            'email': row[2],
            'role': row[3],
            'is_active': bool(row[4])
        }
        
        conn.close()
        return jsonify(user)
        
    except Exception as e:
        app.logger.error(f"Error getting user {user_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania danych użytkownika"}), 500

@app.route('/api/admin/users', methods=['POST'])
@auth_required(roles=['superadmin'])
def create_user():
    try:
        data = request.get_json()
        
        # Walidacja danych
        if not all(key in data for key in ['user_name', 'email', 'password', 'role']):
            return jsonify({"error": "Brak wymaganych pól"}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik już istnieje
        cursor.execute("SELECT 1 FROM users WHERE user_name = ?", (data['user_name'],))
        if cursor.fetchone():
            return jsonify({"error": "Użytkownik o takiej nazwie już istnieje"}), 409
            
        # Hashuj hasło
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        cursor.execute("""
            INSERT INTO users (user_name, email, role, password_hash, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data['user_name'],
            data['email'],
            data['role'],
            password_hash,
            data.get('is_active', True)
        ))
        
        # Zapisz historię zmian
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, changed_by)
            VALUES (?, ?, ?)
        """, (
            data['user_name'],
            'Utworzenie użytkownika',
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Użytkownik został utworzony"})
        
    except Exception as e:
        app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Błąd podczas tworzenia użytkownika"}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@auth_required(roles=['superadmin'])
def update_user(user_id):
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik istnieje
        cursor.execute("SELECT user_name FROM users WHERE id = ?", (user_id,))
        existing_user = cursor.fetchone()
        if not existing_user:
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        # Aktualizuj dane
        cursor.execute("""
            UPDATE users 
            SET email = ?, role = ?, is_active = ?
            WHERE id = ?
        """, (
            data['email'],
            data['role'],
            data.get('is_active', True),
            user_id
        ))
        
        # Zapisz historię zmian
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, changed_by)
            VALUES (?, ?, ?)
        """, (
            existing_user[0],
            'Aktualizacja użytkownika',
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Użytkownik został zaktualizowany"})
        
    except Exception as e:
        app.logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas aktualizacji użytkownika"}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@auth_required(roles=['superadmin'])
def delete_user(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik istnieje
        cursor.execute("SELECT user_name FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        # Usuń użytkownika
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        # Zapisz historię zmian
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, changed_by)
            VALUES (?, ?, ?)
        """, (
            user[0],
            'Usunięcie użytkownika',
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Użytkownik został usunięty"})
        
    except Exception as e:
        app.logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania użytkownika"}), 500

@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@auth_required(roles=['superadmin'])
def reset_user_password(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik istnieje
        cursor.execute("SELECT user_name FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        # Generuj nowe hasło
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Aktualizuj hasło
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        
        # Zapisz historię zmian
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, changed_by)
            VALUES (?, ?, ?)
        """, (
            user[0],
            'Reset hasła',
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Hasło zostało zresetowane",
            "password": new_password
        })
        
    except Exception as e:
        app.logger.error(f"Error resetting password for user {user_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas resetowania hasła"}), 500

@app.route('/get_users', methods=['GET'])
@auth_required()
def get_users():
    try:
        conn = sqlite3.connect(DB_NAME)  # Poprawione wcięcie
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_name, email, role FROM users")
        users = [{"user_name": row[0], "email": row[1], "role": row[2]} for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(users)  # Dodano jsonify
        
    except Exception as e:
        app.logger.error(f"Error getting users: {str(e)}")
        if conn:
            conn.close()
        return jsonify({"error": str(e)}), 500  # Dodano return z błędem

@app.before_request
def check_token_expiration():
    # Pomijamy ścieżki, które nie wymagają autentykacji
    public_paths = ['/login', '/static', '/api/auth/status']
    if any(request.path.startswith(path) for path in public_paths):
        return
        
    token = request.cookies.get('token')
    if token:
        try:
            # Próba dekodowania tokenu
            payload = decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            # Sprawdź czy token nie wygasł
            exp = datetime.fromtimestamp(payload['exp'])
            if exp < datetime.utcnow():
                # Token wygasł
                # Zapisz ostatnią stronę
                if request.method == 'GET' and not request.path.startswith('/api/'):
                    session['last_page'] = request.path
                response = make_response(jsonify({
                    "error": "Token expired",
                    "code": "TOKEN_EXPIRED"
                }), 401)
                response.delete_cookie('token')
                return response
        except ExpiredSignatureError:
            # Token wygasł
            response = make_response(jsonify({
                "error": "Token expired",
                "code": "TOKEN_EXPIRED"
            }), 401)
            response.delete_cookie('token')
            return response
        except InvalidTokenError:
            # Nieprawidłowy token
            response = make_response(jsonify({
                "error": "Invalid token",
                "code": "INVALID_TOKEN"
            }), 401)
            response.delete_cookie('token')
            return response

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    try:
        old_token = request.cookies.get('token')
        if not old_token:
            return jsonify({"error": "No token found"}), 401

        try:
            # Dekoduj stary token
            payload = decode(old_token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Sprawdź czy token nie jest za stary (np. 7 dni)
            token_age = datetime.utcnow() - datetime.fromtimestamp(payload['iat'])
            if token_age > timedelta(days=7):
                return jsonify({"error": "Token too old", "code": "TOKEN_TOO_OLD"}), 401

            # Generuj nowy token z tymi samymi danymi
            user_data = {
                'user_name': payload['user_name'],
                'role': payload['role']
            }
            new_token = generate_token(user_data)
            
            response = make_response(jsonify({
                "message": "Token refreshed successfully",
                "user": user_data
            }))
            response.set_cookie('token', new_token, httponly=True, secure=True, samesite='Strict')
            return response

        except ExpiredSignatureError:
            return jsonify({"error": "Token expired", "code": "TOKEN_EXPIRED"}), 401
        except InvalidTokenError:
            return jsonify({"error": "Invalid token", "code": "INVALID_TOKEN"}), 401

    except Exception as e:
        app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/portfolios', methods=['GET'])
@auth_required()
def get_portfolios():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Pobierz portfolia wraz z liczbą projektów
        cursor.execute("""
            SELECT 
                p.id,
                p.name,
                COUNT(pp.id) as project_count,
                SUM(CASE WHEN pp.is_active = 1 THEN 1 ELSE 0 END) as active_projects
            FROM portfolios p
            LEFT JOIN portfolio_projects pp ON p.id = pp.portfolio_id
            GROUP BY p.id, p.name
            ORDER BY p.name
        """)
        
        portfolios = [{
            'id': row[0],
            'name': row[1],
            'project_count': row[2],
            'active_projects': row[3]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(portfolios)
        
    except Exception as e:
        app.logger.error(f"Error getting portfolios: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania portfoliów"}), 500

@app.route('/api/portfolios/<int:portfolio_id>', methods=['GET'])
@auth_required()
def get_portfolio(portfolio_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Pobierz dane portfolio
        cursor.execute("""
            SELECT id, name
            FROM portfolios
            WHERE id = ?
        """, (portfolio_id,))
        
        portfolio = cursor.fetchone()
        if not portfolio:
            return jsonify({"error": "Portfolio nie istnieje"}), 404
            
        result = {
            'id': portfolio[0],
            'name': portfolio[1],
            'projects': []
        }
        
        # Pobierz projekty w portfolio
        cursor.execute("""
            SELECT 
                id,
                project_key,
                name,
                is_active,
                created_at
            FROM portfolio_projects
            WHERE portfolio_id = ?
            ORDER BY name
        """, (portfolio_id,))
        
        result['projects'] = [{
            'id': row[0],
            'key': row[1],
            'name': row[2],
            'is_active': bool(row[3]),
            'created_at': row[4]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error getting portfolio {portfolio_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania danych portfolio"}), 500

@app.route('/api/portfolios', methods=['POST'])
@auth_required(roles=['admin', 'superadmin'])
def create_portfolio():
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({"error": "Nazwa portfolio jest wymagana"}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy portfolio o takiej nazwie już istnieje
        cursor.execute("SELECT 1 FROM portfolios WHERE name = ?", (data['name'],))
        if cursor.fetchone():
            return jsonify({"error": "Portfolio o takiej nazwie już istnieje"}), 409
            
        # Dodaj nowe portfolio
        cursor.execute("""
            INSERT INTO portfolios (name)
            VALUES (?)
        """, (data['name'],))
        
        portfolio_id = cursor.lastrowid
        
        # Jeśli podano projekty, dodaj je
        if 'projects' in data:
            for project in data['projects']:
                cursor.execute("""
                    INSERT INTO portfolio_projects (portfolio_id, project_key, name, is_active)
                    VALUES (?, ?, ?, ?)
                """, (
                    portfolio_id,
                    project['key'],
                    project['name'],
                    project.get('is_active', True)
                ))
        
        conn.commit()
        conn.close()

        return jsonify({
            "message": "Portfolio zostało utworzone",
            "id": portfolio_id
        })
        
    except Exception as e:
        app.logger.error(f"Error creating portfolio: {str(e)}")
        return jsonify({"error": "Błąd podczas tworzenia portfolio"}), 500

@app.route('/api/portfolios/<int:portfolio_id>', methods=['PUT'])
@auth_required(roles=['admin', 'superadmin'])
def update_portfolio(portfolio_id):
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({"error": "Nazwa portfolio jest wymagana"}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy portfolio istnieje
        cursor.execute("SELECT 1 FROM portfolios WHERE id = ?", (portfolio_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Portfolio nie istnieje"}), 404
            
        # Sprawdź czy nowa nazwa nie koliduje z innym portfolio
        cursor.execute("SELECT 1 FROM portfolios WHERE name = ? AND id != ?", 
                      (data['name'], portfolio_id))
        if cursor.fetchone():
            return jsonify({"error": "Portfolio o takiej nazwie już istnieje"}), 409
            
        # Aktualizuj portfolio
        cursor.execute("""
            UPDATE portfolios 
            SET name = ?
            WHERE id = ?
        """, (data['name'], portfolio_id))
        
        # Jeśli podano projekty, zaktualizuj je
        if 'projects' in data:
            # Usuń wszystkie obecne projekty
            cursor.execute("DELETE FROM portfolio_projects WHERE portfolio_id = ?", 
                         (portfolio_id,))
            
            # Dodaj nowe projekty
            for project in data['projects']:
                cursor.execute("""
                    INSERT INTO portfolio_projects 
                    (portfolio_id, project_key, name, is_active)
                    VALUES (?, ?, ?, ?)
                """, (
                    portfolio_id,
                    project['key'],
                    project['name'],
                    project.get('is_active', True)
                ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Portfolio zostało zaktualizowane"})
        
    except Exception as e:
        app.logger.error(f"Error updating portfolio {portfolio_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas aktualizacji portfolio"}), 500

@app.route('/api/portfolios/<int:portfolio_id>', methods=['DELETE'])
@auth_required(roles=['admin', 'superadmin'])
def delete_portfolio(portfolio_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy portfolio istnieje i pobierz jego dane
        cursor.execute("""
            SELECT p.name, COUNT(pp.id) as project_count
            FROM portfolios p
            LEFT JOIN portfolio_projects pp ON p.id = pp.portfolio_id
            WHERE p.id = ?
            GROUP BY p.id, p.name
        """, (portfolio_id,))
        
        portfolio_data = cursor.fetchone()
        if not portfolio_data:
            return jsonify({"error": "Portfolio nie istnieje"}), 404
            
        portfolio_name, project_count = portfolio_data
            
        # Sprawdź czy użytkownik jest superadminem
        token = request.cookies.get('token')
        user_data = verify_token(token)
        user_name = user_data['user_name']
        is_superadmin = user_data['role'] == 'superadmin'
        
        # Sprawdź czy jest wymagane potwierdzenie
        confirmation = request.args.get('confirm')
        if project_count > 0 and not confirmation:
            return jsonify({
                "error": "Wymagane potwierdzenie",
                "code": "CONFIRMATION_REQUIRED",
                "message": f"Portfolio zawiera {project_count} projektów. Czy na pewno chcesz je usunąć?",
                "project_count": project_count
            }), 409
            
        # Usuń portfolio (kaskadowo usunie też projekty dzięki FOREIGN KEY)
        cursor.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))
        
        # Zapisz w historii zmian
        cursor.execute("""
            INSERT INTO change_history 
            (user_name, change_type, old_value, new_value, changed_by)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_name,
            'Usunięcie portfolio',
            portfolio_name,
            f"Usunięto {project_count} projektów" if is_superadmin else None,
            user_name
        ))
        
        conn.commit()
        conn.close()
        
        response_data = {
            "message": "Portfolio zostało usunięte"
        }
        
        # Dodaj informacje o usuniętych projektach tylko dla superadmina
        if is_superadmin:
            response_data.update({
                "details": {
                    "portfolio_name": portfolio_name,
                    "deleted_projects": project_count
                }
            })
        
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"Error deleting portfolio {portfolio_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania portfolio"}), 500

@app.route('/api/portfolios/<int:portfolio_id>/projects', methods=['POST'])
@auth_required(roles=['admin', 'superadmin'])
def add_project_to_portfolio(portfolio_id):
    try:
        if not portfolio_id:
            return jsonify({"error": "Nie podano ID portfolio"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Brak danych projektu"}), 400
        
        if not all(key in data for key in ['key', 'name']):
            return jsonify({"error": "Brak wymaganych pól projektu (key, name)"}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy portfolio istnieje
        cursor.execute("SELECT 1 FROM portfolios WHERE id = ?", (portfolio_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Portfolio nie istnieje"}), 404
            
        # Sprawdź czy projekt już istnieje w tym portfolio
        cursor.execute("""
            SELECT 1 FROM portfolio_projects 
            WHERE portfolio_id = ? AND project_key = ?
        """, (portfolio_id, data['key']))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Projekt już istnieje w tym portfolio"}), 409
            
        try:
            jira = setup_jira_client()
            project = jira.project(data['key'])
            data['name'] = project.name
        except Exception as e:
            app.logger.warning(f"Could not verify project in Jira: {str(e)}")
            
        try:
            # Dodaj projekt w transakcji
            cursor.execute("""
                INSERT INTO portfolio_projects 
                (portfolio_id, project_key, name, is_active)
                VALUES (?, ?, ?, ?)
            """, (
                portfolio_id,
                data['key'],
                data['name'],
                data.get('is_active', True)
            ))
            
            project_id = cursor.lastrowid
            
            # Zapisz w historii zmian
            cursor.execute("""
                INSERT INTO change_history 
                (user_name, change_type, old_value, new_value, changed_by)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session['user_name'],
                'Dodanie projektu do portfolio',
                None,
                f"{data['key']} ({data['name']})",
                session['user_name']
            ))
            
            conn.commit()
            
            return jsonify({
                "message": "Projekt został dodany do portfolio",
                "id": project_id,
                "project": {
                    "id": project_id,
                    "key": data['key'],
                    "name": data['name'],
                    "is_active": True
                }
            })
            
        except sqlite3.Error as e:
            conn.rollback()
            raise e
            
    except Exception as e:
        app.logger.error(f"Error adding project to portfolio {portfolio_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas dodawania projektu"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/portfolios/<int:portfolio_id>/projects/<int:project_id>', methods=['PUT'])
@auth_required(roles=['admin', 'superadmin'])
def update_portfolio_project(portfolio_id, project_id):
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy projekt istnieje w tym portfolio
        cursor.execute("""
            SELECT 1 FROM portfolio_projects 
            WHERE id = ? AND portfolio_id = ?
        """, (project_id, portfolio_id))
        if not cursor.fetchone():
            return jsonify({"error": "Projekt nie istnieje w tym portfolio"}), 404
            
        # Aktualizuj projekt
        cursor.execute("""
            UPDATE portfolio_projects 
            SET name = ?, is_active = ?
            WHERE id = ?
        """, (
            data.get('name'),
            data.get('is_active', True),
            project_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Projekt został zaktualizowany"})
        
    except Exception as e:
        app.logger.error(f"Error updating project {project_id} in portfolio {portfolio_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas aktualizacji projektu"}), 500

@app.route('/api/portfolios/<int:portfolio_id>/projects/<int:project_id>', methods=['DELETE'])
@auth_required(roles=['admin', 'superadmin'])
def remove_project_from_portfolio(portfolio_id, project_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy projekt istnieje w tym portfolio
        cursor.execute("""
            SELECT name FROM portfolio_projects 
            WHERE id = ? AND portfolio_id = ?
        """, (project_id, portfolio_id))
        project = cursor.fetchone()
        if not project:
            return jsonify({"error": "Projekt nie istnieje w tym portfolio"}), 404
            
        # Usuń projekt
        cursor.execute("DELETE FROM portfolio_projects WHERE id = ?", (project_id,))
        
        # Zapisz w historii zmian
        cursor.execute("""
            INSERT INTO change_history 
            (user_name, change_type, old_value, changed_by)
            VALUES (?, ?, ?, ?)
        """, (
            session['user_name'],
            'Usunięcie projektu z portfolio',
            project[0],
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Projekt został usunięty z portfolio"})
        
    except Exception as e:
        app.logger.error(f"Error removing project {project_id} from portfolio {portfolio_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania projektu"}), 500

@app.route('/api/jira/projects', methods=['GET'])
@auth_required(roles=['admin', 'superadmin'])
def get_jira_projects():
    try:
        jira = setup_jira_client()
        if not jira:
            return jsonify([])  # Zwróć pustą listę zamiast błędu
            
        projects = jira.projects()
        return jsonify([{
            'key': project.key,
            'name': project.name,
            'id': project.id
        } for project in projects])
        
    except Exception as e:
        app.logger.error(f"Error getting Jira projects: {str(e)}")
        return jsonify([])  # Zwróć pustą listę w przypadku błędu

@app.route('/api/jira/projects/search', methods=['GET'])
@auth_required(roles=['admin', 'superadmin'])
def search_jira_projects():
    try:
        query = request.args.get('q', '').upper()
        if not query:
            return jsonify([])
            
        jira = get_jira_client()  # Zmień setup_jira_client na get_jira_client
        if not jira:
            return jsonify({"error": "Nie można połączyć się z Jirą"}), 500
            
        projects = jira.projects()
        # ... (reszta kodu)
        
        # Filtruj projekty, które zawierają query w kluczu lub nazwie
        filtered_projects = [
            {
                'key': project.key,
                'name': project.name,
                'id': project.id
            }
            for project in projects
            if query in project.key.upper() or query in project.name.upper()
        ]
        
        return jsonify(filtered_projects)
        
    except Exception as e:
        app.logger.error(f"Error searching Jira projects: {str(e)}")
        return jsonify({"error": "Błąd podczas wyszukiwania projektów"}), 500

@app.route('/api/portfolios/<int:portfolio_id>/projects', methods=['GET'])
@auth_required()
def get_portfolio_projects(portfolio_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy portfolio istnieje
        cursor.execute("SELECT 1 FROM portfolios WHERE id = ?", (portfolio_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Portfolio nie istnieje"}), 404
            
        # Pobierz projekty
        cursor.execute("""
            SELECT 
                id,
                project_key,
                name,
                is_active,
                created_at
            FROM portfolio_projects
            WHERE portfolio_id = ?
            ORDER BY name
        """, (portfolio_id,))
        
        projects = [{
            'id': row[0],
            'key': row[1],
            'name': row[2],
            'is_active': bool(row[3]),
            'created_at': row[4]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(projects)
        
    except Exception as e:
        app.logger.error(f"Error getting projects for portfolio {portfolio_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania projektów"}), 500

# Dodaj nową funkcję do synchronizacji użytkowników
def sync_jira_users():
    conn = None
    try:
        jira = get_jira_client()
        if not jira:
            raise Exception("Nie można połączyć się z Jirą")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Rozpocznij historię synchronizacji
        cursor.execute("""
            INSERT INTO jira_sync_history (sync_type, status)
            VALUES ('users', 'in_progress')
        """)
        sync_id = cursor.lastrowid
        
        # Parametry paginacji
        start_at = 0
        max_results = 50
        processed = 0
        all_users = []
        
        while True:
            # Użyj bezpośredniego zapytania REST API zamiast search_users
            endpoint = f"/rest/api/2/group/member"
            params = {
                'groupname': 'jira-software-users',
                'includeInactiveUsers': 'false',
                'maxResults': max_results,
                'startAt': start_at
            }
            
            response = jira._session.get(f"{jira._options['server']}{endpoint}", 
                                       params=params, 
                                       verify=False)
            
            if response.status_code != 200:
                raise Exception(f"Błąd API Jira: {response.text}")
                
            data = response.json()
            
            if not data.get('values'):
                break
                
            # Przetwórz użytkowników z aktualnej strony
            for user in data['values']:
                cursor.execute("""
                    INSERT OR REPLACE INTO jira_users 
                    (account_id, user_name, display_name, email, is_active, last_sync)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    user.get('key'),  # Używamy key zamiast accountId
                    user.get('name'),  # Username
                    user.get('displayName'),
                    user.get('emailAddress'),
                    user.get('active', False)
                ))
                processed += 1
            
            # Sprawdź czy są kolejne strony
            if start_at + max_results >= data.get('total', 0):
                break
                
            start_at += max_results
            
        # Zaktualizuj historię synchronizacji
        cursor.execute("""
            UPDATE jira_sync_history 
            SET status = 'completed', 
                items_processed = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (processed, sync_id))
        
        conn.commit()
        
        return {
            "success": True, 
            "users_synced": processed
        }
        
    except Exception as e:
        app.logger.error(f"Error syncing Jira users: {str(e)}")
        if conn:
            try:
                cursor.execute("""
                    UPDATE jira_sync_history 
                    SET status = 'failed',
                        error_message = ?,
                        completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (str(e), sync_id))
                conn.commit()
            except:
                pass
        raise
    finally:
        if conn:
            conn.close()

# Zmodyfikuj endpoint API do pobierania użytkowników z filtrowaniem
@app.route('/api/jira/users', methods=['GET'])
@auth_required(roles=['admin', 'superadmin'])
def get_jira_users():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Parametry filtrowania
        search = request.args.get('search', '').strip()
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        sort_by = request.args.get('sort', 'display_name')
        sort_dir = request.args.get('dir', 'asc').upper()
        
        # Obsługa paginacji
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        # Budowanie zapytania - poprawione nazwy kolumn
        query = """
            SELECT account_id, display_name, user_name, email, is_active, last_sync
            FROM jira_users
            WHERE 1=1
        """
        params = []
        
        if search:
            query += """ 
                AND (
                    display_name LIKE ? 
                    OR user_name LIKE ? 
                    OR email LIKE ?
                )
            """
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if active_only:
            query += " AND is_active = 1"
        
        # Dodaj sortowanie
        valid_sort_columns = {
            'display_name': 'display_name',
            'user_name': 'user_name',
            'email': 'email',
            'last_sync': 'last_sync'
        }
        sort_column = valid_sort_columns.get(sort_by, 'display_name')
        query += f" ORDER BY {sort_column} {'DESC' if sort_dir == 'DESC' else 'ASC'}"
        
        # Pobierz całkowitą liczbę wyników
        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Dodaj limit i offset
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        # Wykonaj główne zapytanie
        cursor.execute(query, params)
        
        users = [{
            'id': row[0],
            'display_name': row[1],
            'user_name': row[2],
            'email': row[3],
            'is_active': bool(row[4]),
            'last_sync': row[5]
        } for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        app.logger.error(f"Error getting Jira users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/jira/users/sync', methods=['POST'])
@auth_required(roles=['admin', 'superadmin'])
def sync_jira_users_endpoint():
    try:
        result = sync_jira_users()
        return jsonify({
            "message": "Synchronizacja użytkowników zakończona pomyślnie",
            "details": {
                "users_synced": result['users_synced']
            }
        })
    except Exception as e:
        app.logger.error(f"Error in sync endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/user-role')
@auth_required()
def get_user_role():
    token = request.cookies.get('token')
    user_data = verify_token(token)
    return jsonify({
        "role": user_data.get('role')
    })

@app.context_processor
def inject_menu_data():
    def get_menu_items():
        token = request.cookies.get('token')
        if not token:
            return []
            
        user_data = verify_token(token)
        if not user_data:
            return []
            
        role = user_data.get('role')
        
        menu_items = []
        
        # Podstawowe menu dla wszystkich
        menu_items.extend([
            {'name': 'Dashboard', 'url': '/dashboard', 'icon': 'bi-speedometer2'},
            {'name': 'Worklogi', 'url': '/worklogs', 'icon': 'bi-clock-history'},
            {'name': 'Portfolia', 'url': '/portfolios', 'icon': 'bi-folder2'}
        ])
        
        # Menu administracyjne
        if role in ['admin', 'superadmin']:
            menu_items.extend([
                {'name': 'Użytkownicy Jira', 'url': '/admin/users', 'icon': 'bi-people-fill'},
                {'name': 'Zarządzanie Portfoliami', 'url': '/admin/portfolios', 'icon': 'bi-folder2-open'}
            ])
            
        if role == 'superadmin':
            menu_items.append({
                'name': 'Ustawienia', 
                'url': '/admin/settings', 
                'icon': 'bi-gear-fill'
            })
            
        return menu_items
        
    return {'get_menu_items': get_menu_items}

@app.route('/api/admin/role-mappings', methods=['GET'])
@auth_required(roles=['superadmin'])
def get_role_mappings():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, jira_group, system_role
            FROM jira_role_mappings
            ORDER BY jira_group
        """)
        
        mappings = [{
            'id': row[0],
            'jira_group': row[1],
            'system_role': row[2]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(mappings)
    except Exception as e:
        app.logger.error(f"Error getting role mappings: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania mapowań ról"}), 500

@app.route('/api/admin/role-mappings', methods=['POST'])
@auth_required(roles=['superadmin'])
def create_role_mapping():
    try:
        data = request.get_json()
        
        if not all(key in data for key in ['jira_group', 'system_role']):
            return jsonify({"error": "Brak wymaganych pól"}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy mapowanie już istnieje
        cursor.execute("""
            SELECT 1 FROM jira_role_mappings 
            WHERE jira_group = ?
        """, (data['jira_group'],))
        
        if cursor.fetchone():
            return jsonify({"error": "Mapowanie dla tej grupy już istnieje"}), 409
            
        cursor.execute("""
            INSERT INTO jira_role_mappings (jira_group, system_role)
            VALUES (?, ?)
        """, (data['jira_group'], data['system_role']))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Mapowanie zostało utworzone"})
    except Exception as e:
        app.logger.error(f"Error creating role mapping: {str(e)}")
        return jsonify({"error": "Błąd podczas tworzenia mapowania"}), 500

@app.route('/api/jira/groups', methods=['GET'])
@auth_required(roles=['admin', 'superadmin'])
def get_jira_groups():
    try:
        jira = setup_jira_client()
        if not jira:
            return jsonify([])
            
        groups = jira.groups()
        return jsonify([{
            'name': group.name,
            'id': group.id
        } for group in groups])
    except Exception as e:
        app.logger.error(f"Error getting Jira groups: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania grup"}), 500

@app.route('/api/jira/test-connection', methods=['GET'])
@auth_required(roles=['admin', 'superadmin'])
def test_jira_connection():
    try:
        jira = setup_jira_client()
        if not jira:
            return jsonify({
                "success": False,
                "error": "Nie można utworzyć klienta Jira"
            }), 500
            
        myself = jira.myself()
        return jsonify({
            "success": True,
            "user": {
                "name": myself['displayName'],
                "email": myself['emailAddress']
            }
        })
        
    except Exception as e:
        app.logger.error(f"Test connection error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/admin/settings', methods=['GET', 'POST'])
@auth_required(roles=['admin', 'superadmin'])
def manage_settings():
    try:
        if request.method == 'GET':
            # Pobierz aktualne ustawienia
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Zmieniono zapytanie, aby nie używało kolumny is_active
            cursor.execute("""
                SELECT key, value FROM app_settings
            """)
            
            settings = dict(cursor.fetchall())
            conn.close()
            
            return jsonify(settings)
            
        elif request.method == 'POST':
            data = request.get_json()
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Uproszczono zapytanie
            for key, value in data.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO app_settings (key, value)
                    VALUES (?, ?)
                """, (key, value))
                
            conn.commit()
            conn.close()
            
            return jsonify({"message": "Ustawienia zostały zaktualizowane"})
            
    except Exception as e:
        app.logger.error(f"Settings error: {str(e)}")
        return jsonify({"error": "Błąd podczas obsługi ustawień"}), 500

# Zarządzanie rolami
@app.route('/api/admin/roles', methods=['GET'])
@auth_required(roles=['admin', 'superadmin'])
def get_roles():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, is_system, created_at
            FROM roles
            ORDER BY name
        """)
        
        roles = [{
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'is_system': bool(row[3]),
            'created_at': row[4]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(roles)
    except Exception as e:
        app.logger.error(f"Error getting roles: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania ról"}), 500

@app.route('/api/admin/roles', methods=['POST'])
@auth_required(roles=['superadmin'])
def create_role():
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({"error": "Nazwa roli jest wymagana"}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO roles (name, description)
            VALUES (?, ?)
        """, (data['name'], data.get('description')))
        
        role_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Rola została utworzona",
            "id": role_id
        })
    except Exception as e:
        app.logger.error(f"Error creating role: {str(e)}")
        return jsonify({"error": "Błąd podczas tworzenia roli"}), 500

@app.route('/api/admin/roles/<int:role_id>', methods=['PUT'])
@auth_required(roles=['superadmin'])
def update_role(role_id):
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy to nie jest rola systemowa
        cursor.execute("SELECT is_system FROM roles WHERE id = ?", (role_id,))
        role = cursor.fetchone()
        
        if not role:
            return jsonify({"error": "Rola nie istnieje"}), 404
            
        if role[0]:
            return jsonify({"error": "Nie można modyfikować roli systemowej"}), 403
        
        cursor.execute("""
            UPDATE roles 
            SET name = ?, description = ?
            WHERE id = ?
        """, (data['name'], data.get('description'), role_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rola została zaktualizowana"})
    except Exception as e:
        app.logger.error(f"Error updating role: {str(e)}")
        return jsonify({"error": "Błąd podczas aktualizacji roli"}), 500

@app.route('/api/admin/roles/<int:role_id>', methods=['DELETE'])
@auth_required(roles=['superadmin'])
def delete_role(role_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy to nie jest rola systemowa
        cursor.execute("SELECT is_system FROM roles WHERE id = ?", (role_id,))
        role = cursor.fetchone()
        
        if not role:
            return jsonify({"error": "Rola nie istnieje"}), 404
            
        if role[0]:
            return jsonify({"error": "Nie można usunąć roli systemowej"}), 403
        
        # Usuń przypisania użytkowników do tej roli
        cursor.execute("DELETE FROM user_roles WHERE role_id = ?", (role_id,))
        
        # Usuń rolę
        cursor.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rola została usunięta"})
    except Exception as e:
        app.logger.error(f"Error deleting role: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania roli"}), 500

@app.route('/api/admin/user-roles', methods=['GET'])
@auth_required(roles=['admin', 'superadmin'])
def get_user_roles():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ur.id,
                ju.user_key,
                ju.display_name,
                ju.email,
                r.id as role_id,
                r.name as role_name,
                ur.assigned_by,
                ur.assigned_at
            FROM user_roles ur
            JOIN jira_users ju ON ur.user_key = ju.user_key
            JOIN roles r ON ur.role_id = r.id
            ORDER BY ju.display_name, r.name
        """)
        
        assignments = [{
            'id': row[0],
            'user_key': row[1],
            'display_name': row[2],
            'email': row[3],
            'role_id': row[4],
            'role_name': row[5],
            'assigned_by': row[6],
            'assigned_at': row[7]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(assignments)
    except Exception as e:
        app.logger.error(f"Error getting user roles: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania przypisań ról"}), 500

@app.route('/api/admin/user-roles', methods=['POST'])
@auth_required(roles=['superadmin'])
def assign_user_role():
    try:
        data = request.get_json()
        token = request.cookies.get('token')
        user_data = verify_token(token)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_roles (user_key, role_id, assigned_by)
            VALUES (?, ?, ?)
        """, (data['user_key'], data['role_id'], user_data['user_name']))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rola została przypisana"})
    except Exception as e:
        app.logger.error(f"Error assigning role: {str(e)}")
        return jsonify({"error": "Błąd podczas przypisywania roli"}), 500

@app.route('/api/admin/user-roles/<int:assignment_id>', methods=['DELETE'])
@auth_required(roles=['superadmin'])
def remove_user_role(assignment_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_roles WHERE id = ?", (assignment_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Przypisanie roli zostało usunięte"})
    except Exception as e:
        app.logger.error(f"Error removing role assignment: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania przypisania roli"}), 500

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            app.logger.debug('No token found')  # Dodaj log debugowania
            return redirect(url_for('login'))
        try:
            verify_token(token)
            app.logger.debug('Token verified')  # Dodaj log debugowania
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f'Token verification failed: {str(e)}')  # Dodaj log błędu
            return redirect(url_for('login'))
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return jsonify({"error": "No token provided"}), 401
        try:
            user_data = verify_token(token)
            if user_data.get('role') not in ['admin', 'superadmin']:
                return jsonify({"error": "Admin privileges required"}), 403
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"Admin verification failed: {str(e)}")
            return jsonify({"error": "Invalid token"}), 401
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard_view():  # Zmiana z admin_dashboard na admin_dashboard_view
    try:
        return render_template('admin/dashboard.html')
    except Exception as e:
        app.logger.error(f"Error in admin_dashboard_view: {str(e)}")
        return render_template('error.html', error_code=500, error_message="Błąd podczas ładowania dashboardu")

@app.route('/admin/users')
@login_required
@admin_required
def admin_users_view():  # Zmiana z admin_users na admin_users_view
    try:
        return render_template('admin/users.html')
    except Exception as e:
        app.logger.error(f"Error in admin_users_view: {str(e)}")
        return render_template('error.html', error_code=500, error_message="Błąd podczas ładowania użytkowników")

@app.route('/admin/roles')
@login_required
@admin_required
def admin_roles_view():  # Zmiana z admin_roles na admin_roles_view
    try:
        return render_template('admin/roles.html')
    except Exception as e:
        app.logger.error(f"Error in admin_roles_view: {str(e)}")
        return render_template('error.html', error_code=500, error_message="Błąd podczas ładowania ról")

@app.route('/admin/settings')
@login_required
@admin_required
def admin_settings_view():  # Zmiana z admin_settings na admin_settings_view
    try:
        return render_template('admin/settings.html')
    except Exception as e:
        app.logger.error(f"Error in admin_settings_view: {str(e)}")
        return render_template('error.html', error_code=500, error_message="Błąd podczas ładowania ustawień")

@app.route('/admin/jira')
@login_required
@admin_required
def admin_jira_view():  # Zmiana z admin_jira na admin_jira_view
    try:
        return render_template('admin/jira.html')
    except Exception as e:
        app.logger.error(f"Error in admin_jira_view: {str(e)}")
        return render_template('error.html', error_code=500, error_message="Błąd podczas ładowania konfiguracji Jira")

@app.route('/admin/backup')
@login_required
@admin_required
def admin_backup_view():  # Zmiana z admin_backup na admin_backup_view
    try:
        return render_template('admin/backup.html')
    except Exception as e:
        app.logger.error(f"Error in admin_backup_view: {str(e)}")
        return render_template('error.html', error_code=500, error_message="Błąd podczas ładowania backupu")

@app.route('/admin/portfolios')
@login_required
@admin_required
def admin_portfolios_view():  # Zmiana z admin_portfolios na admin_portfolios_view
    try:
        return render_template('admin/portfolios.html')
    except Exception as e:
        app.logger.error(f"Error in admin_portfolios_view: {str(e)}")
        return render_template('error.html', error_code=500, error_message="Błąd podczas ładowania portfoliów")

# API endpoints dla panelu admina
@app.route('/api/admin/dashboard/stats')
@login_required
@admin_required
def admin_get_dashboard_stats():  # Zmiana z get_dashboard_stats na admin_get_dashboard_stats
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        stats = {
            'users_count': cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            'worklogs_count': cursor.execute("SELECT COUNT(*) FROM worklogs").fetchone()[0],
            'active_projects': cursor.execute("SELECT COUNT(DISTINCT project) FROM worklogs").fetchone()[0],
            'total_hours': cursor.execute("SELECT SUM(time_logged) FROM worklogs").fetchone()[0] or 0
        }
        
        conn.close()
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"Error in admin_get_dashboard_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/roles', methods=['GET'])
@login_required
@admin_required
def admin_get_roles():  # Zmiana z get_roles na admin_get_roles
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, description FROM roles")
        roles = [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return jsonify(roles)
    except Exception as e:
        app.logger.error(f"Error in admin_get_roles: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/roles', methods=['POST'])
@login_required
@admin_required
def admin_create_role():  # Zmiana z create_role na admin_create_role
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({"error": "Nazwa roli jest wymagana"}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO roles (name, description)
            VALUES (?, ?)
        """, (data['name'], data.get('description')))
        
        role_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Rola została utworzona",
            "id": role_id
        })
    except Exception as e:
        app.logger.error(f"Error creating role: {str(e)}")
        return jsonify({"error": "Błąd podczas tworzenia roli"}), 500

@app.route('/api/admin/roles/<int:role_id>', methods=['PUT'])
@login_required
@admin_required
def admin_update_role(role_id):  # Zmiana z update_role na admin_update_role
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy to nie jest rola systemowa
        cursor.execute("SELECT is_system FROM roles WHERE id = ?", (role_id,))
        role = cursor.fetchone()
        
        if not role:
            return jsonify({"error": "Rola nie istnieje"}), 404
            
        if role[0]:
            return jsonify({"error": "Nie można modyfikować roli systemowej"}), 403
        
        cursor.execute("""
            UPDATE roles 
            SET name = ?, description = ?
            WHERE id = ?
        """, (data['name'], data.get('description'), role_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rola została zaktualizowana"})
    except Exception as e:
        app.logger.error(f"Error updating role: {str(e)}")
        return jsonify({"error": "Błąd podczas aktualizacji roli"}), 500

@app.route('/api/admin/roles/<int:role_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_role(role_id):  # Zmiana z delete_role na admin_delete_role
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy to nie jest rola systemowa
        cursor.execute("SELECT is_system FROM roles WHERE id = ?", (role_id,))
        role = cursor.fetchone()
        
        if not role:
            return jsonify({"error": "Rola nie istnieje"}), 404
            
        if role[0]:
            return jsonify({"error": "Nie można usunąć roli systemowej"}), 403
        
        # Usuń przypisania użytkowników do tej roli
        cursor.execute("DELETE FROM user_roles WHERE role_id = ?", (role_id,))
        
        # Usuń rolę
        cursor.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rola została usunięta"})
    except Exception as e:
        app.logger.error(f"Error deleting role: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania roli"}), 500

@app.route('/api/admin/user-roles', methods=['GET'])
@login_required
@admin_required
def admin_get_user_roles():  # Zmiana z get_user_roles na admin_get_user_roles
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ur.id,
                ju.user_key,
                ju.display_name,
                ju.email,
                r.id as role_id,
                r.name as role_name,
                ur.assigned_by,
                ur.assigned_at
            FROM user_roles ur
            JOIN jira_users ju ON ur.user_key = ju.user_key
            JOIN roles r ON ur.role_id = r.id
            ORDER BY ju.display_name, r.name
        """)
        
        assignments = [{
            'id': row[0],
            'user_key': row[1],
            'display_name': row[2],
            'email': row[3],
            'role_id': row[4],
            'role_name': row[5],
            'assigned_by': row[6],
            'assigned_at': row[7]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(assignments)
    except Exception as e:
        app.logger.error(f"Error getting user roles: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania przypisań ról"}), 500

@app.route('/api/admin/user-roles', methods=['POST'])
@login_required
@admin_required
def admin_assign_role():  # Zmiana z assign_user_role na admin_assign_role
    try:
        data = request.get_json()
        token = request.cookies.get('token')
        user_data = verify_token(token)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_roles (user_key, role_id, assigned_by)
            VALUES (?, ?, ?)
        """, (data['user_key'], data['role_id'], user_data['user_name']))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rola została przypisana"})
    except Exception as e:
        app.logger.error(f"Error assigning role: {str(e)}")
        return jsonify({"error": "Błąd podczas przypisywania roli"}), 500

@app.route('/api/admin/user-roles/<int:assignment_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_remove_role(assignment_id):  # Zmiana z remove_user_role na admin_remove_role
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_roles WHERE id = ?", (assignment_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Przypisanie roli zostało usunięte"})
    except Exception as e:
        app.logger.error(f"Error removing role assignment: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania przypisania roli"}), 500

@app.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_get_users():  # Zmiana z get_admin_users na admin_get_users
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_name, email, role, is_active, last_login
            FROM users
            ORDER BY user_name
        """)
        
        users = [{
            'id': row[0],
            'user_name': row[1],
            'email': row[2],
            'role': row[3],
            'is_active': bool(row[4]),
            'last_login': row[5]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(users)

    except Exception as e:
        app.logger.error(f"Error getting users: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania użytkowników"}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def admin_get_user(user_id):  # Zmiana z get_user na admin_get_user
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_name, email, role, is_active
            FROM users
            WHERE id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        user = {
            'id': row[0],
            'user_name': row[1],
            'email': row[2],
            'role': row[3],
            'is_active': bool(row[4])
        }
        
        conn.close()
        return jsonify(user)
        
    except Exception as e:
        app.logger.error(f"Error getting user {user_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania danych użytkownika"}), 500

@app.route('/api/admin/users', methods=['POST'])
@login_required
@admin_required
def admin_create_user():  # Zmiana z create_user na admin_create_user
    try:
        data = request.get_json()
        
        # Walidacja danych
        if not all(key in data for key in ['user_name', 'email', 'password', 'role']):
            return jsonify({"error": "Brak wymaganych pól"}), 400
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik już istnieje
        cursor.execute("SELECT 1 FROM users WHERE user_name = ?", (data['user_name'],))
        if cursor.fetchone():
            return jsonify({"error": "Użytkownik o takiej nazwie już istnieje"}), 409
            
        # Hashuj hasło
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        cursor.execute("""
            INSERT INTO users (user_name, email, role, password_hash, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data['user_name'],
            data['email'],
            data['role'],
            password_hash,
            data.get('is_active', True)
        ))
        
        # Zapisz historię zmian
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, changed_by)
            VALUES (?, ?, ?)
        """, (
            data['user_name'],
            'Utworzenie użytkownika',
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Użytkownik został utworzony"})
        
    except Exception as e:
        app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Błąd podczas tworzenia użytkownika"}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def admin_update_user(user_id):  # Zmiana z update_user na admin_update_user
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik istnieje
        cursor.execute("SELECT user_name FROM users WHERE id = ?", (user_id,))
        existing_user = cursor.fetchone()
        if not existing_user:
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        # Aktualizuj dane
        cursor.execute("""
            UPDATE users 
            SET email = ?, role = ?, is_active = ?
            WHERE id = ?
        """, (
            data['email'],
            data['role'],
            data.get('is_active', True),
            user_id
        ))
        
        # Zapisz historię zmian
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, changed_by)
            VALUES (?, ?, ?)
        """, (
            existing_user[0],
            'Aktualizacja użytkownika',
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Użytkownik został zaktualizowany"})
        
    except Exception as e:
        app.logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas aktualizacji użytkownika"}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_user(user_id):  # Zmiana z delete_user na admin_delete_user
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik istnieje
        cursor.execute("SELECT user_name FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        # Usuń użytkownika
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        # Zapisz historię zmian
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, changed_by)
            VALUES (?, ?, ?)
        """, (
            user[0],
            'Usunięcie użytkownika',
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Użytkownik został usunięty"})
        
    except Exception as e:
        app.logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania użytkownika"}), 500

@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(user_id):  # Zmiana z reset_user_password na admin_reset_password
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy użytkownik istnieje
        cursor.execute("SELECT user_name FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        # Generuj nowe hasło
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Aktualizuj hasło
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        
        # Zapisz historię zmian
        cursor.execute("""
            INSERT INTO change_history (user_name, change_type, changed_by)
            VALUES (?, ?, ?)
        """, (
            user[0],
            'Reset hasła',
            session['user_name']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Hasło zostało zresetowane",
            "password": new_password
        })
        
    except Exception as e:
        app.logger.error(f"Error resetting password for user {user_id}: {str(e)}")
        return jsonify({"error": "Błąd podczas resetowania hasła"}), 500

@app.route('/api/admin/check-superadmin', methods=['GET'])
def check_superadmin():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_name, role 
            FROM users 
            WHERE user_name = 'luszynski@lbpro.pl'
        """)
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return jsonify({
                "exists": True,
                "user_name": user[0],
                "role": user[1]
            })
        else:
            return jsonify({
                "exists": False
            })
            
    except Exception as e:
        app.logger.error(f"Błąd sprawdzania superadmina: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/check-password', methods=['POST'])
def check_password():
    try:
        data = request.get_json()
        user_name = data.get('user_name')
        password = data.get('password')

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT password_hash 
            FROM users 
            WHERE user_name = ?
        """, (user_name,))
        
        result = cursor.fetchone()
        conn.close()

        if not result:
            return jsonify({
                "exists": False,
                "message": "User not found"
            })

        stored_hash = result[0]
        is_valid = bcrypt.checkpw(password.encode('utf-8'), stored_hash)

        return jsonify({
            "exists": True,
            "is_valid": is_valid,
            "stored_hash": stored_hash.decode('utf-8') if stored_hash else None
        })

    except Exception as e:
        app.logger.error(f"Error checking password: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    """Wyświetla logi systemowe dla administratorów"""
    try:
        return render_template('admin/logs.html')
    except Exception as e:
        app.logger.error(f"Error in admin_logs: {str(e)}")
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Błąd podczas ładowania logów")

@app.route('/api/admin/logs')
@login_required
@admin_required
def get_logs():
    """API endpoint do pobierania logów systemowych"""
    try:
        page = request.args.get('page', 1, type=int)
        level = request.args.get('level', 'ALL')
        date = request.args.get('date')
        search = request.args.get('search', '')
        
        # Buduj zapytanie bazowe
        query = "SELECT timestamp, level, module, message FROM logs"
        params = []
        conditions = []
        
        # Dodaj filtry
        if level != 'ALL':
            conditions.append("level = ?")
            params.append(level)
            
        if date:
            conditions.append("DATE(timestamp) = DATE(?)")
            params.append(date)
            
        if search:
            conditions.append("(message LIKE ? OR module LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%'])
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Dodaj sortowanie i paginację
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        
        # Ustaw limit i offset dla paginacji
        per_page = 50
        params.extend([per_page, (page - 1) * per_page])
        
        # Wykonaj zapytanie
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Pobierz całkowitą liczbę logów (dla paginacji)
        count_query = f"SELECT COUNT(*) FROM logs"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        cursor.execute(count_query, params[:-2] if params else [])
        total_logs = cursor.fetchone()[0]
        
        # Pobierz logi dla bieżącej strony
        cursor.execute(query, params)
        logs = [
            {
                'timestamp': row[0],
                'level': row[1],
                'module': row[2],
                'message': row[3]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return jsonify({
            'logs': logs,
            'total_pages': (total_logs + per_page - 1) // per_page,
            'current_page': page
        })
        
    except Exception as e:
        app.logger.error(f"Error in get_logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Endpointy dla zarządzania rolami niestandardowymi
@app.route('/api/admin/custom-roles', methods=['GET'])
@login_required
@admin_required
def admin_get_custom_roles():
    try:
        app.logger.debug('Fetching custom roles')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, permissions, created_by, created_at, is_active 
            FROM custom_roles 
            ORDER BY name
        """)
        
        roles = cursor.fetchall()
        app.logger.debug(f'Found {len(roles)} roles')
        
        formatted_roles = [{
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'permissions': json.loads(row[3]) if row[3] else {},
            'created_by': row[4],
            'created_at': row[5],
            'is_active': bool(row[6])
        } for row in roles]
        
        conn.close()
        return jsonify(formatted_roles)
    except Exception as e:
        app.logger.error(f"Error in admin_get_custom_roles: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/custom-roles', methods=['POST'])
@login_required
@admin_required
def admin_create_custom_role():
    """Utwórz nową rolę niestandardową"""
    try:
        data = request.get_json()
        if not data.get('name'):
            return jsonify({"error": "Nazwa roli jest wymagana"}), 400

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO custom_roles (name, description, permissions, created_by)
            VALUES (?, ?, ?, ?)
        """, (
            data['name'],
            data.get('description'),
            json.dumps(data.get('permissions', {})),
            session['user_name']
        ))
        
        role_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Rola została utworzona",
            "id": role_id
        })
    except Exception as e:
        app.logger.error(f"Error in admin_create_custom_role: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/custom-roles/<int:role_id>', methods=['PUT'])
@login_required
@admin_required
def admin_update_custom_role(role_id):
    """Aktualizuj istniejącą rolę niestandardową"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE custom_roles 
            SET name = ?, description = ?, permissions = ?
            WHERE id = ?
        """, (
            data['name'],
            data.get('description'),
            json.dumps(data.get('permissions', {})),
            role_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rola została zaktualizowana"})
    except Exception as e:
        app.logger.error(f"Error in admin_update_custom_role: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/assign-custom-role', methods=['POST'])
@login_required
@admin_required
def admin_assign_custom_role():
    """Przypisz rolę niestandardową do użytkownika"""
    try:
        data = request.get_json()
        if not all(key in data for key in ['user_name', 'role_id']):
            return jsonify({"error": "Brak wymaganych danych"}), 400  # Poprawione wcięcie

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_custom_roles (user_name, role_id, assigned_by)
            VALUES (?, ?, ?)
        """, (
            data['user_name'],
            data['role_id'],
            session['user_name']
        ))
        
        conn.commit()
        conn.close()

        return jsonify({"message": "Rola została przypisana"})
    except Exception as e:
        app.logger.error(f"Error in admin_assign_custom_role: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/user-custom-roles/<string:user_name>', methods=['GET'])
@login_required
@admin_required
def admin_get_user_custom_roles(user_name):
    """Pobierz role niestandardowe przypisane do użytkownika"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cr.id, cr.name, cr.description, cr.permissions,
                   ucr.assigned_by, ucr.assigned_at
            FROM user_custom_roles ucr
            JOIN custom_roles cr ON ucr.role_id = cr.id
            WHERE ucr.user_name = ?
        """, (user_name,))
        
        roles = [{
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'permissions': json.loads(row[3]) if row[3] else {},
            'assigned_by': row[4],
            'assigned_at': row[5]
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(roles)
    except Exception as e:
        app.logger.error(f"Error in admin_get_user_custom_roles: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/custom-roles')
@login_required
@admin_required
def admin_custom_roles_view():
    app.logger.debug('Accessing custom roles view')  # Dodaj log
    try:
        return render_template('admin/custom_roles.html')
    except Exception as e:
        app.logger.error(f"Error in admin_custom_roles_view: {str(e)}")
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Błąd podczas ładowania ról niestandardowych")

def has_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.cookies.get('token')
            try:
                user_data = verify_token(token)
                
                # Superadmin ma wszystkie uprawnienia
                if user_data.get('role') == 'superadmin':
                    return f(*args, **kwargs)
                    
                # Admin ma dostęp tylko do określonych funkcji
                if user_data.get('role') == 'admin':
                    admin_permissions = ['view_reports', 'manage_users']
                    if permission in admin_permissions:
                        return f(*args, **kwargs)
                
                # Sprawdź uprawnienia z ról niestandardowych
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT cr.permissions
                    FROM user_custom_roles ucr
                    JOIN custom_roles cr ON ucr.role_id = cr.id
                    WHERE ucr.user_name = ? AND cr.is_active = 1
                """, (user_data['user_name'],))
                
                roles = cursor.fetchall()
                conn.close()
                
                for role in roles:
                    permissions = json.loads(role[0]) if role[0] else {}
                    if permissions.get(permission):
                        return f(*args, **kwargs)
                
                return jsonify({"error": "Brak uprawnień"}), 403
                
            except Exception as e:
                app.logger.error(f"Error checking permissions: {str(e)}")
                return jsonify({"error": "Unauthorized"}), 401
                
        return decorated_function
    return decorator

# Przykład użycia:
@app.route('/api/reports')
@login_required
@has_permission('view_reports')
def get_reports():
    # ... kod endpointu ...
    pass

@app.route('/api/settings/users', methods=['GET'])
@login_required
@admin_required
def get_settings_users():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_name, email, role, is_active
            FROM users
            ORDER BY user_name
        """)
        
        users = [{
            'user_name': row[0],
            'email': row[1],
            'role': row[2],
            'is_active': bool(row[3])
        } for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(users)
    except Exception as e:
        app.logger.error(f"Error in get_settings_users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/debug/database')
@login_required
@admin_required
def debug_database():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź tabele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # Sprawdź zawartość custom_roles
        cursor.execute("SELECT * FROM custom_roles")
        roles = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'tables': [table[0] for table in tables],
            'roles': roles
        })
    except Exception as e:
        app.logger.error(f"Debug database error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def init_custom_roles_table():
    try:
        app.logger.info("Initializing custom_roles table")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy tabela custom_roles istnieje
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='custom_roles'
        """)
        
        if not cursor.fetchone():
            app.logger.info("Creating custom_roles table")
            # Tworzenie tabeli custom_roles
            cursor.execute("""
                CREATE TABLE custom_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    permissions TEXT,
                    created_by TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Dodawanie domyślnych ról
            cursor.execute("""
                INSERT INTO custom_roles (name, description, permissions, created_by)
                VALUES 
                ('Viewer', 'Tylko podgląd', '{"view_reports": true}', 'system'),
                ('Editor', 'Edycja podstawowa', '{"view_reports": true, "edit_reports": true}', 'system')
            """)
            
            # Tworzenie tabeli powiązań użytkowników z rolami
            cursor.execute("""
                CREATE TABLE user_custom_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    role_id INTEGER NOT NULL,
                    assigned_by TEXT NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (role_id) REFERENCES custom_roles (id),
                    UNIQUE (user_name, role_id)
                )
            """)
            
            conn.commit()
            app.logger.info("Custom roles tables created successfully")
        else:
            app.logger.info("Custom roles tables already exist")
            
        conn.close()
    except Exception as e:
        app.logger.error(f"Error initializing custom roles tables: {str(e)}")
        raise

# Dodaj wywołanie inicjalizacji przy starcie aplikacji
if __name__ == "__main__":
    try:
        # Najpierw inicjalizuj bazę danych
        init_db()
        
        # Następnie uruchom aplikację
        port = int(os.environ.get("FLASK_PORT", 5003))
        app.logger.info(f"Starting application on port {port}")
        
        init_scheduler()
        
        app.run(
            debug=True,
            host="0.0.0.0",
            port=port,
            use_reloader=True
        )
    except Exception as e:
        app.logger.error(f"Failed to start application: {str(e)}")
        print(f"Failed to start application: {str(e)}")

@app.route('/api/admin/debug/db-tables')
@login_required
@admin_required
def debug_db_tables():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Lista wszystkich tabel
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Sprawdź strukturę tabeli custom_roles
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='custom_roles'
        """)
        custom_roles_schema = cursor.fetchone()
        
        # Pobierz przykładowe role
        cursor.execute("SELECT * FROM custom_roles LIMIT 5")
        sample_roles = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'tables': tables,
            'custom_roles_schema': custom_roles_schema[0] if custom_roles_schema else None,
            'sample_roles': sample_roles
        })
    except Exception as e:
        app.logger.error(f"Debug DB error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def sync_jira_users():
    try:
        # Przed synchronizacją, zachowaj chronione ustawienia
        cursor.execute("""
            SELECT user_name, role, password_hash 
            FROM permanent_settings 
            WHERE is_protected = 1
        """)
        protected_users = cursor.fetchall()

        # Po synchronizacji, przywróć chronione ustawienia
        for user in protected_users:
            cursor.execute("""
                UPDATE users 
                SET role = ?, password_hash = ? 
                WHERE user_name = ?
            """, (user[1], user[2], user[0]))

        conn.commit()
        
    except Exception as e:
        app.logger.error(f"Error syncing Jira users: {str(e)}")
        raise

def check_database_state():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sprawdź czy istnieją wszystkie wymagane tabele
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name IN ('users', 'worklogs', 'jira_issues')
        """)
        
        existing_tables = {row[0] for row in cursor.fetchall()}
        required_tables = {'users', 'worklogs', 'jira_issues'}
        
        missing_tables = required_tables - existing_tables
        
        if missing_tables:
            app.logger.warning(f"Missing tables detected: {missing_tables}")
            init_db()
            
        conn.close()
        
    except Exception as e:
        app.logger.error(f"Database check failed: {str(e)}")
        raise

# Dodaj wywołanie sprawdzenia przy starcie
if __name__ == "__main__":
    try:
        check_database_state()  # Dodaj tę linię
        # Najpierw inicjalizuj bazę danych
        init_db()
        
        # Następnie uruchom aplikację
        port = int(os.environ.get("FLASK_PORT", 5003))
        app.logger.info(f"Starting application on port {port}")
        
        init_scheduler()
        
        app.run(
            debug=True,
            host="0.0.0.0",
            port=port,
            use_reloader=True
        )
    except Exception as e:
        app.logger.error(f"Failed to start application: {str(e)}")
        print(f"Failed to start application: {str(e)}")

def reset_superadmin_password():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Resetuj hasło superadmina do domyślnego
        password = 'admin123'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?
            WHERE user_name = 'luszynski@lbpro.pl'
        """, (password_hash,))
        
        conn.commit()
        conn.close()
        app.logger.info("Superadmin password reset successfully")
        return True
    except Exception as e:
        app.logger.error(f"Error resetting superadmin password: {str(e)}")
        return False

# Endpoint do resetowania hasła (tylko dla deweloperów)
@app.route('/api/admin/reset-superadmin', methods=['POST'])
def reset_superadmin():
    if app.debug:  # Tylko w trybie debug
        if reset_superadmin_password():
            return jsonify({'success': True, 'message': 'Password reset to: admin123'})
        return jsonify({'success': False, 'error': 'Failed to reset password'}), 500
    return jsonify({'error': 'Not available in production'}), 403

@app.route('/api/admin/check-tables')
@login_required
@admin_required
def check_tables():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Lista wymaganych tabel
        required_tables = ['users', 'worklogs', 'jira_issues', 'custom_roles']
        
        # Sprawdź każdą tabelę
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            app.logger.warning(f"Missing tables: {missing_tables}")
            init_db()  # Reinicjalizuj bazę jeśli brakuje tabel
            return jsonify({'message': 'Database reinitialized', 'missing_tables': missing_tables})
            
        return jsonify({'message': 'All required tables exist', 'tables': existing_tables})
        
    except Exception as e:
        app.logger.error(f"Error checking tables: {str(e)}")
        return jsonify({'error': str(e)}), 500

def add_sample_worklogs():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Dodaj przykładowe wpisy
        cursor.execute("""
            INSERT INTO worklogs (user_name, project, task_key, time_logged, date, description)
            VALUES 
            ('luszynski@lbpro.pl', 'PROJ1', 'PROJ1-1', 3600, date('now'), 'Sample work'),
            ('luszynski@lbpro.pl', 'PROJ1', 'PROJ1-2', 7200, date('now', '-1 day'), 'More work')
        """)
        
        conn.commit()
        conn.close()
        app.logger.info("Sample worklogs added successfully")
        
    except Exception as e:
        app.logger.error(f"Error adding sample worklogs: {str(e)}")
        raise

def create_backup():
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(app.config['BACKUP_DIR'], f'backup_{timestamp}.sql')
        
        # Tworzenie kopii bazy danych
        with sqlite3.connect(DB_NAME) as conn:
            with open(backup_file, 'w') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n')
        
        return backup_file
    except Exception as e:
        app.logger.error(f"Błąd podczas tworzenia kopii zapasowej: {str(e)}")
        raise

def execute_db_query(query, params=None):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.fetchall()
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        raise

# Na końcu pliku, przed if __name__ == '__main__':
def initialize_application():
    try:
        # Tworzenie wymaganych katalogów
        for directory in [app.config['UPLOAD_FOLDER'], 
                         app.config['BACKUP_DIR'], 
                         'data', 
                         'static', 
                         'templates']:
            os.makedirs(directory, exist_ok=True)
            
        # Inicjalizacja bazy danych
        init_db()
        
        # Dodaj przykładowe dane jeśli potrzebne
        add_sample_worklogs()
        
        app.logger.info("Application initialized successfully")
    except Exception as e:
        app.logger.error(f"Error during application initialization: {str(e)}")
        raise

# Na samym końcu pliku
if __name__ == '__main__':
    try:
        port = int(os.environ.get('FLASK_PORT', 5000))
        app.logger.info(f"Starting application on port {port}")
        
        # Inicjalizacja aplikacji
        initialize_application()
        
        app.run(
            debug=True,
            host="0.0.0.0",
            port=port,
            use_reloader=True
        )
    except Exception as e:
        app.logger.error(f"Failed to start application: {str(e)}")
        print(f"Failed to start application: {str(e)}")
