import csv
from io import StringIO, BytesIO
from typing import Dict, Any, List
from datetime import datetime
from flask import send_file, current_app, render_template, make_response
import pdfkit
from jinja2 import Environment, FileSystemLoader
import os
import logging
from app.exceptions import ExportError, ValidationError
from app.utils.helpers import get_activity_level, get_efficiency_level
import io
from app.cache import cache
from app.monitoring import monitor
import gzip

logger = logging.getLogger(__name__)

# Konfiguracja pdfkit
if os.name == 'nt':  # Windows
    WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
else:  # Linux/Unix
    WKHTMLTOPDF_PATH = '/usr/local/bin/wkhtmltopdf'

# Sprawdzamy czy plik istnieje, jeśli nie - używamy domyślnej ścieżki
if not os.path.exists(WKHTMLTOPDF_PATH):
    logger.warning(f"wkhtmltopdf not found at {WKHTMLTOPDF_PATH}, using default path")
    WKHTMLTOPDF_PATH = 'wkhtmltopdf'  # Użyj domyślnej ścieżki z PATH

try:
    pdfkit_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
except Exception as e:
    logger.error(f"Error configuring pdfkit: {str(e)}")
    pdfkit_config = None

# Konfiguracja opcji PDF
PDF_OPTIONS = {
    'page-size': 'A4',
    'margin-top': '0.75in',
    'margin-right': '0.75in',
    'margin-bottom': '0.75in',
    'margin-left': '0.75in',
    'encoding': "UTF-8",
    'no-outline': None
}

WKHTMLTOPDF_PATH = os.getenv('WKHTMLTOPDF_PATH', 'wkhtmltopdf')

def export_csv_report(team, report_type: str, start_date: datetime, end_date: datetime):
    """Eksportuje raport do pliku CSV."""
    try:
        validate_export_params(team, start_date, end_date)
        check_export_dependencies()
        
        if report_type == 'workload':
            return export_workload_csv(team, start_date, end_date)
        elif report_type == 'activity':
            return export_activity_csv(team, start_date, end_date)
        elif report_type == 'efficiency':
            return export_efficiency_csv(team, start_date, end_date)
        else:
            raise ValidationError(f"Nieznany typ raportu: {report_type}")
            
    except Exception as e:
        logger.error(f"Error exporting {report_type} report: {str(e)}")
        raise

def export_pdf_report(team, report_type: str, start_date: datetime, end_date: datetime):
    """Eksportuje raport do pliku CSV (tymczasowo zamiast PDF)."""
    logger.warning("PDF export is disabled, using CSV instead")
    return export_csv_report(team, report_type, start_date, end_date)

def export_workload_csv(team, start_date: datetime, end_date: datetime):
    """Eksportuje raport obciążenia do CSV."""
    workload = team.get_workload(start_date, end_date)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Nagłówki
    writer.writerow(['Użytkownik', 'Godziny', 'Obciążenie (%)', 'Status'])
    
    # Dane użytkowników
    for user, data in sorted(workload['users'].items(), key=lambda x: x[1]['percentage'], reverse=True):
        writer.writerow([
            user,
            f"{data['hours']:.1f}",
            f"{data['percentage']:.1f}",
            data['status']
        ])
    
    # Podsumowanie
    writer.writerow([])
    writer.writerow(['Oczekiwana liczba godzin', f"{workload['expected_hours']:.1f}"])
    writer.writerow(['Średnie obciążenie zespołu', f"{workload['avg_workload']:.1f}%"])
    
    # Przygotuj plik do wysłania
    output.seek(0)
    filename = sanitize_filename(f"workload_report_{start_date.strftime('%Y%m%d')}.csv")
    
    return make_response(output.getvalue(), content_type='text/csv', headers={"Content-Disposition": f"attachment; filename={filename}"})

def export_activity_csv(team, start_date: datetime, end_date: datetime):
    """Eksportuje raport aktywności do CSV."""
    activity = team.get_activity(start_date, end_date)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Nagłówki
    writer.writerow(['Data', 'Godziny', 'Zadania', 'Poziom Aktywności'])
    
    # Dane dzienne
    for date, hours in sorted(activity['daily_activity'].items()):
        level = get_activity_level(hours, activity['avg_daily_hours'])
        writer.writerow([
            date,
            f"{hours:.1f}",
            activity['tasks'].get(date, 0),
            level.upper()
        ])
    
    # Podsumowanie
    writer.writerow([])
    writer.writerow(['Łączna liczba godzin', f"{activity['total_hours']:.1f}"])
    writer.writerow(['Łączna liczba zadań', activity['total_tasks']])
    writer.writerow(['Średnia dzienna aktywność', f"{activity['avg_daily_hours']:.1f}"])
    
    # Przygotuj plik do wysłania
    output.seek(0)
    filename = sanitize_filename(f"activity_report_{start_date.strftime('%Y%m%d')}.csv")
    
    return make_response(output.getvalue(), content_type='text/csv', headers={"Content-Disposition": f"attachment; filename={filename}"})

def export_efficiency_csv(team, start_date: datetime, end_date: datetime):
    """Eksportuje raport efektywności do CSV."""
    efficiency = team.get_efficiency(start_date, end_date)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Nagłówki
    writer.writerow(['Użytkownik', 'Godziny', 'Zadania', 'Efektywność (%)', 'Status'])
    
    # Dane użytkowników
    for user, data in sorted(efficiency['users'].items(), key=lambda x: x[1]['efficiency'], reverse=True):
        writer.writerow([
            user,
            f"{data['hours']:.1f}",
            data['tasks'],
            f"{data['efficiency']:.1f}",
            data['status']
        ])
    
    # Podsumowanie
    writer.writerow([])
    writer.writerow(['Średnia efektywność zespołu', f"{efficiency['avg_efficiency']:.1f}%"])
    
    # Przygotuj plik do wysłania
    output.seek(0)
    filename = sanitize_filename(f"efficiency_report_{start_date.strftime('%Y%m%d')}.csv")
    
    return make_response(output.getvalue(), content_type='text/csv', headers={"Content-Disposition": f"attachment; filename={filename}"})

def export_workload_pdf(team, start_date: datetime, end_date: datetime):
    """Eksportuje raport obciążenia do PDF."""
    try:
        workload = team.get_workload(start_date, end_date)
        
        html = render_template(
            'reports/workload_pdf.html',
            team=team,
            workload=workload,
            start_date=start_date,
            end_date=end_date,
            datetime=datetime
        )
        
        pdf = pdfkit.from_string(html, False, options=PDF_OPTIONS, configuration=pdfkit_config)
        filename = sanitize_filename(f"workload_report_{start_date.strftime('%Y%m%d')}.pdf")
        
        check_file_size(pdf)
        
        return make_response(pdf, content_type='application/pdf', headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        logger.error(f"Error generating workload PDF: {str(e)}")
        raise

def export_activity_pdf(team, start_date: datetime, end_date: datetime):
    """Eksportuje raport aktywności do PDF."""
    try:
        activity = team.get_activity(start_date, end_date)
        
        html = render_template(
            'reports/activity_pdf.html',
            team=team,
            activity=activity,
            start_date=start_date,
            end_date=end_date,
            datetime=datetime
        )
        
        pdf = pdfkit.from_string(html, False, options=PDF_OPTIONS, configuration=pdfkit_config)
        filename = sanitize_filename(f"activity_report_{start_date.strftime('%Y%m%d')}.pdf")
        
        check_file_size(pdf)
        
        return make_response(pdf, content_type='application/pdf', headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        logger.error(f"Error generating activity PDF: {str(e)}")
        raise

def export_efficiency_pdf(team, start_date: datetime, end_date: datetime):
    """Eksportuje raport efektywności do PDF."""
    try:
        efficiency = team.get_efficiency(start_date, end_date)
        
        html = render_template(
            'reports/efficiency_pdf.html',
            team=team,
            efficiency=efficiency,
            start_date=start_date,
            end_date=end_date,
            datetime=datetime
        )
        
        pdf = pdfkit.from_string(html, False, options=PDF_OPTIONS, configuration=pdfkit_config)
        filename = sanitize_filename(f"efficiency_report_{start_date.strftime('%Y%m%d')}.pdf")
        
        check_file_size(pdf)
        
        return make_response(pdf, content_type='application/pdf', headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        logger.error(f"Error generating efficiency PDF: {str(e)}")
        raise

def export_member_stats_csv(team, user_name: str, stats: Dict[str, Any], 
                          start_date: datetime, end_date: datetime):
    """Eksportuje statystyki członka zespołu do CSV."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Nagłówki
    writer.writerow(['Data', 'Godziny', 'Zadania', 'Projekty'])
    
    # Dane dzienne
    for date, data in sorted(stats['daily_stats'].items()):
        writer.writerow([
            date,
            data['hours'],
            data['tasks'],
            ', '.join(data['projects'])
        ])
    
    # Podsumowanie
    writer.writerow([])
    writer.writerow(['Suma godzin', stats['total_hours']])
    writer.writerow(['Suma zadań', stats['total_tasks']])
    writer.writerow(['Średnio godzin dziennie', stats['avg_daily_hours']])
    
    # Przygotuj plik do wysłania
    output.seek(0)
    filename = f"member_stats_{user_name}_{start_date.strftime('%Y%m%d')}.csv"
    
    return make_response(output.getvalue(), content_type='text/csv', headers={"Content-Disposition": f"attachment; filename={filename}"})

def export_member_stats_pdf(team, user_name: str, stats: Dict[str, Any],
                          start_date: datetime, end_date: datetime):
    """Eksportuje statystyki członka zespołu do PDF."""
    try:
        # Renderuj szablon HTML
        html = render_template(
            'reports/member_stats_pdf.html',
            team=team,
            user_name=user_name,
            stats=stats,
            start_date=start_date,
            end_date=end_date,
            datetime=datetime
        )
        
        # Konwertuj HTML do PDF
        pdf = pdfkit.from_string(html, False, options=PDF_OPTIONS, configuration=pdfkit_config)
        
        filename = f"member_stats_{user_name}_{start_date.strftime('%Y%m%d')}.pdf"
        
        check_file_size(pdf)
        
        return make_response(pdf, content_type='application/pdf', headers={"Content-Disposition": f"attachment; filename={filename}"})
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise

def export_project_stats_csv(team, project_key: str, stats: Dict[str, Any],
                           start_date: datetime, end_date: datetime):
    """Eksportuje statystyki projektu do CSV."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Nagłówki
    writer.writerow(['Użytkownik', 'Godziny', 'Zadania', 'Udział (%)'])
    
    # Dane użytkowników
    for user, data in sorted(stats['users'].items()):
        percentage = (data['hours'] / stats['total_hours'] * 100) if stats['total_hours'] > 0 else 0
        writer.writerow([
            user,
            data['hours'],
            data['tasks'],
            f"{percentage:.1f}"
        ])
    
    # Podsumowanie
    writer.writerow([])
    writer.writerow(['Suma godzin', stats['total_hours']])
    writer.writerow(['Suma zadań', stats['total_tasks']])
    writer.writerow(['Średnio godzin na użytkownika', stats['avg_hours_per_user']])
    
    # Przygotuj plik do wysłania
    output.seek(0)
    filename = f"project_stats_{project_key}_{start_date.strftime('%Y%m%d')}.csv"
    
    return make_response(output.getvalue(), content_type='text/csv', headers={"Content-Disposition": f"attachment; filename={filename}"})

def export_project_stats_pdf(team, project_key: str, stats: Dict[str, Any],
                           start_date: datetime, end_date: datetime):
    """Eksportuje statystyki projektu do PDF."""
    try:
        # Renderuj szablon HTML
        html = render_template(
            'reports/project_stats_pdf.html',
            team=team,
            project_key=project_key,
            stats=stats,
            start_date=start_date,
            end_date=end_date,
            datetime=datetime
        )
        
        # Konwertuj HTML do PDF
        pdf = pdfkit.from_string(html, False, options=PDF_OPTIONS, configuration=pdfkit_config)
        
        filename = f"project_stats_{project_key}_{start_date.strftime('%Y%m%d')}.pdf"
        
        check_file_size(pdf)
        
        return make_response(pdf, content_type='application/pdf', headers={"Content-Disposition": f"attachment; filename={filename}"})
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise

def sanitize_filename(filename: str) -> str:
    """Sanityzuje nazwę pliku."""
    # Usuń niedozwolone znaki
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Ogranicz długość
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length-len(ext)] + ext
    
    return filename

def check_export_dependencies():
    """Sprawdza czy wszystkie zależności do eksportu są dostępne."""
    if not os.path.exists(WKHTMLTOPDF_PATH):
        raise ExportError(
            "Nie znaleziono wkhtmltopdf. Zainstaluj wkhtmltopdf lub ustaw prawidłową ścieżkę.",
            {"path": WKHTMLTOPDF_PATH}
        )

def validate_export_params(team, start_date: datetime, end_date: datetime):
    """Waliduje parametry eksportu."""
    if not team:
        raise ValidationError("Nie znaleziono zespołu")
    
    if start_date > end_date:
        raise ValidationError(
            "Data końcowa nie może być wcześniejsza niż początkowa",
            {"start_date": start_date, "end_date": end_date}
        )
    
    if end_date > datetime.now():
        raise ValidationError(
            "Data końcowa nie może być w przyszłości",
            {"end_date": end_date}
        )

def export_large_dataset(team, report_type: str, start_date: datetime, end_date: datetime):
    """Eksportuje duży zestaw danych w tle."""
    from app.tasks import generate_report_async
    
    task = generate_report_async.delay(
        team.id, 
        report_type, 
        start_date.isoformat(), 
        end_date.isoformat()
    )
    
    return {
        'task_id': task.id,
        'status': 'pending',
        'message': 'Raport jest generowany w tle. Sprawdź status używając task_id.'
    }

def get_cached_report(team_id: int, report_type: str, start_date: datetime, end_date: datetime):
    """Pobiera raport z cache'u lub generuje nowy."""
    cache_key = f"report_{team_id}_{report_type}_{start_date.date()}_{end_date.date()}"
    
    # Próba pobrania z cache'u
    cached_report = cache.get(cache_key)
    if cached_report:
        return cached_report
    
    # Generowanie nowego raportu
    report = generate_report(team_id, report_type, start_date, end_date)
    
    # Zapisanie w cache na 1 godzinę
    cache.set(cache_key, report, timeout=3600)
    
    return report

@monitor.measure_time('report_generation')
def generate_report(team_id: int, report_type: str, start_date: datetime, end_date: datetime):
    """Generuje raport z monitorowaniem czasu."""
    # ... implementacja generowania raportu 

def check_file_size(data: bytes, max_size: int = 50 * 1024 * 1024):  # 50MB
    """Sprawdza rozmiar pliku."""
    if len(data) > max_size:
        raise ValidationError(
            "Wygenerowany plik przekracza maksymalny rozmiar",
            {"max_size_mb": max_size / (1024 * 1024), "file_size_mb": len(data) / (1024 * 1024)}
        ) 

def compress_file(data: bytes) -> BytesIO:
    """Kompresuje dane."""
    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='wb') as gz:
        gz.write(data)
    compressed.seek(0)
    return compressed 